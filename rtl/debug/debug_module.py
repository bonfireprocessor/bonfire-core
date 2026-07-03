"""
RISC-V debug module — decode-stage pipeline injection and control
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations
from __future__ import print_function

from typing import Any

from myhdl import Signal, modbv, block, always, always_comb, instances

from rtl.debug.dm_registers import DebugModuleRegisterBundle
from rtl.debug.types import (
    t_abstract_command_state,
    t_abstract_command_type,
    t_debug_hart_state,
)
from rtl.type_aliases import BitSignal
from util.diagnostics import get_diagnostics


class DebugHartViewBundle:
    """Signals observed by the debug controller from the decode stage.

    The controller only reads these signals. Signals such as dm_break are
    produced by instruction decode and reported back here so the controller can
    finish program-buffer execution.
    """
    def __init__(self, config: Any) -> None:
        xlen = config.xlen

        self.rs1_data_i = Signal(modbv(0)[xlen:])
        self.valid_o = Signal(bool(0))
        self.stall_i = Signal(bool(0))
        self.dm_break = Signal(bool(0))


class DebugHartControlBundle:
    """Signals driven by the debug controller into the decode stage.

    These are the controller outputs used to halt, kill, inject program-buffer
    execution, and write register-file data during abstract commands.
    """
    def __init__(self, config: Any) -> None:
        self.halt = Signal(bool(0))
        self.kill = Signal(bool(0))
        self.regwrite = Signal(bool(0))
        self.regno = Signal(modbv(0)[5:])
        self.data0 = Signal(modbv(0)[32:])
        self.exec = Signal(bool(0))


@block
def DebugModuleController(
    config: Any,
    clock: BitSignal,
    debugRegisterBundle: DebugModuleRegisterBundle,
    decode_view: DebugHartViewBundle,
    debug_control: DebugHartControlBundle,
    progbuf_pointer: Any,
    progbuf_last: BitSignal,
) -> Any:
    get_diagnostics().detail("DebugModuleController: xlen={} ip_low={} progbuf_size={}".format(
        config.xlen,
        config.ip_low,
        config.progbuf_size,
    ))

    @always_comb
    def debug_event_comb():
      
        debug_control.regno.next = debugRegisterBundle.regno
        debug_control.data0.next = debugRegisterBundle.data_regs[0]
       
        if debugRegisterBundle.abstract_command_new and \
           debugRegisterBundle.abstract_command_state == t_abstract_command_state.none and \
           debugRegisterBundle.command_type == t_abstract_command_type.access_reg:
            debug_control.regwrite.next = debugRegisterBundle.write
        else:
            debug_control.regwrite.next = False

    @always(clock.posedge)
    def debug_module_seq():
        if debug_control.halt:
            if debugRegisterBundle.abstract_command_state == t_abstract_command_state.none:
                if debugRegisterBundle.abstract_command_new and \
                   debugRegisterBundle.command_type == t_abstract_command_type.access_reg and \
                   (debugRegisterBundle.transfer or debugRegisterBundle.postexec):
                    debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.taken

            elif debugRegisterBundle.abstract_command_state == t_abstract_command_state.taken:
                if debugRegisterBundle.transfer and debugRegisterBundle.write:
                    if debugRegisterBundle.postexec:
                        debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.exec
                    else:
                        debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.none

                elif debugRegisterBundle.transfer:
                    debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.regvalid
                    debugRegisterBundle.abstract_command_result.next = decode_view.rs1_data_i

                elif debugRegisterBundle.postexec:
                    debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.exec

            elif debugRegisterBundle.abstract_command_state == t_abstract_command_state.regvalid:
                if debugRegisterBundle.postexec:
                    debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.exec
                else:
                    debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.none
            elif debugRegisterBundle.abstract_command_state == t_abstract_command_state.exec or \
                 debugRegisterBundle.abstract_command_state == t_abstract_command_state.exec2:
                debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.wait_retire
            elif debugRegisterBundle.abstract_command_state == t_abstract_command_state.wait_retire:
                if not (decode_view.valid_o or decode_view.stall_i):
                    if not progbuf_last and not decode_view.dm_break:
                        progbuf_pointer.next = 1
                        debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.exec2
                    else:
                        debugRegisterBundle.abstract_command_state.next = t_abstract_command_state.none
                        progbuf_pointer.next = 0

    @always_comb
    def dm_state():
        debug_control.kill.next = debugRegisterBundle.dpc_jump
        debug_control.exec.next = debugRegisterBundle.abstract_command_state == t_abstract_command_state.exec or \
                       debugRegisterBundle.abstract_command_state == t_abstract_command_state.exec2

        if debug_control.halt:
            debugRegisterBundle.hart_state.next = t_debug_hart_state.halted
        else:
            debugRegisterBundle.hart_state.next = t_debug_hart_state.running

    return instances()
