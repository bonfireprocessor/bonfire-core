"""
RISC-V debug module — decode-stage pipeline injection and control
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import print_function

from myhdl import Signal, modbv, block, always, always_comb, instances

from rtl.debug.types import (
    t_abstract_command_state,
    t_abstract_command_type,
    t_debug_hart_state,
)
from rtl.instructions import Opcodes as op
from rtl.instructions import PrivFunct12, SystemFunct3
from util.diagnostics import get_diagnostics


class DebugHartViewBundle:
    """Signals observed by the debug controller from the decode stage.

    The controller only reads these signals. Signals such as dm_break are
    produced by instruction decode and reported back here so the controller can
    finish program-buffer execution.
    """
    def __init__(self, config):
        xlen = config.xlen

        self.current_ip_i = Signal(modbv(0)[xlen:])
        self.word_i = Signal(modbv(0)[xlen:])
        self.en_i = Signal(bool(0))
        self.kill_i = Signal(bool(0))
        self.rs1_data_i = Signal(modbv(0)[xlen:])
        self.valid_o = Signal(bool(0))
        self.stall_i = Signal(bool(0))
        self.downstream_busy = Signal(bool(0))
        self.dm_break = Signal(bool(0))


class DebugHartControlBundle:
    """Signals driven by the debug controller into the decode stage.

    These are the controller outputs used to halt, kill, inject program-buffer
    execution, and write register-file data during abstract commands.
    """
    def __init__(self, config):
        self.halt = Signal(bool(0))
        self.kill = Signal(bool(0))
        self.regwrite = Signal(bool(0))
        self.regno = Signal(modbv(0)[5:])
        self.data0 = Signal(modbv(0)[32:])
        self.exec = Signal(bool(0))
        self.ebreak_halt_req = Signal(bool(0))
        self.step_armed = Signal(bool(0))
        self.step_halt_pending = Signal(bool(0))


@block
def DebugModuleController(
    config,
    clock,
    debugRegisterBundle,
    debugCSRBundle,
    debugCSRUpdateBundle,
    decode_view,
    debug_control,
    progbuf_pointer,
    progbuf_last,
):
    get_diagnostics().detail("DebugModuleController: xlen={} ip_low={} progbuf_size={}".format(
        config.xlen,
        config.ip_low,
        config.progbuf_size,
    ))

    @always_comb
    def debug_event_comb():
        debug_control.regwrite.next = False
        debug_control.regno.next = debugRegisterBundle.regno
        debug_control.data0.next = debugRegisterBundle.data_regs[0]
        debug_control.ebreak_halt_req.next = False

        if debugRegisterBundle.abstract_command_new and \
           debugRegisterBundle.abstract_command_state == t_abstract_command_state.none and \
           debugRegisterBundle.command_type == t_abstract_command_type.access_reg:
            debug_control.regwrite.next = debugRegisterBundle.write

        if not debug_control.halt and not decode_view.downstream_busy and decode_view.en_i and not decode_view.kill_i:
            if debugCSRBundle.ebreakm and decode_view.word_i[7:2] == op.RV32_SYSTEM and \
               decode_view.word_i[15:12] == SystemFunct3.RV32_F3_PRIV and \
               decode_view.word_i[32:20] == PrivFunct12.RV32_F12_EBREAK:
                debug_control.ebreak_halt_req.next = True

    @always(clock.posedge)
    def debug_module_seq():
        debugRegisterBundle.req_ack.next = False
        debugCSRUpdateBundle.we_dpc.next = False
        debugCSRUpdateBundle.we_cause.next = False

        if debugRegisterBundle.dpc_jump:
            debugRegisterBundle.dpc_jump.next = False

        if debug_control.ebreak_halt_req:
            debugCSRUpdateBundle.dpc.next = decode_view.current_ip_i[config.xlen:config.ip_low]
            debugCSRUpdateBundle.we_dpc.next = True
            debugCSRUpdateBundle.cause.next = 1
            debugCSRUpdateBundle.we_cause.next = True
            debug_control.halt.next = True
            debug_control.step_armed.next = False
            debug_control.step_halt_pending.next = False

        elif debug_control.step_halt_pending and debugRegisterBundle.instr_retired:
            debugCSRUpdateBundle.dpc.next = debugRegisterBundle.instr_retire_dpc
            debugCSRUpdateBundle.we_dpc.next = True
            debugCSRUpdateBundle.cause.next = 4
            debugCSRUpdateBundle.we_cause.next = True
            debug_control.halt.next = True
            debug_control.step_armed.next = False
            debug_control.step_halt_pending.next = False

        if not debug_control.ebreak_halt_req and not debug_control.step_halt_pending and \
           not decode_view.downstream_busy and not debugRegisterBundle.req_ack:
            if debugRegisterBundle.haltreq and decode_view.en_i and not decode_view.kill_i:
                debugRegisterBundle.req_ack.next = True
                debugCSRUpdateBundle.dpc.next = decode_view.current_ip_i[config.xlen:config.ip_low]
                debugCSRUpdateBundle.we_dpc.next = True
                debugCSRUpdateBundle.cause.next = 3
                debugCSRUpdateBundle.we_cause.next = True
                debug_control.halt.next = True
                debug_control.step_armed.next = False
            elif debugRegisterBundle.resumereq:
                debugRegisterBundle.req_ack.next = True
                debug_control.halt.next = False
                debugRegisterBundle.dpc_jump.next = True
                debug_control.step_armed.next = debugCSRBundle.step

        if debug_control.step_armed and not debug_control.step_halt_pending and not debug_control.halt and \
           not debug_control.kill and not decode_view.downstream_busy and decode_view.en_i and not decode_view.kill_i and \
           not debug_control.ebreak_halt_req:
            debug_control.step_halt_pending.next = True

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
