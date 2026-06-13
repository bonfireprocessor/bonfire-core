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
        self.ebreak_seen = Signal(bool(0))
        self.ebreak_current_ip = Signal(modbv(0)[xlen:])


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

    pending_dpc_update = Signal(bool(0))
    pending_dpc = Signal(modbv(0)[config.xlen:config.ip_low])
    pending_cause = Signal(modbv(0)[3:])
    step_arm_delay = Signal(modbv(0)[2:])

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

        if not debug_control.halt and debugCSRBundle.ebreakm and decode_view.ebreak_seen:
            debug_control.ebreak_halt_req.next = True

    @always(clock.posedge)
    def debug_module_seq():
        debugRegisterBundle.req_ack.next = False
        debugCSRUpdateBundle.we_dpc.next = False
        debugCSRUpdateBundle.we_cause.next = False

        if pending_dpc_update:
            debugCSRUpdateBundle.dpc.next = pending_dpc
            debugCSRUpdateBundle.we_dpc.next = True
            debugCSRUpdateBundle.cause.next = pending_cause
            debugCSRUpdateBundle.we_cause.next = True
            pending_dpc_update.next = False

        if debugRegisterBundle.dpc_jump:
            debugRegisterBundle.dpc_jump.next = False

        if step_arm_delay != 0:
            step_arm_delay.next = step_arm_delay - 1
            if step_arm_delay == 1:
                debug_control.step_armed.next = True

        if debug_control.ebreak_halt_req:
            pending_dpc.next = decode_view.ebreak_current_ip[config.xlen:config.ip_low]
            pending_cause.next = 1
            pending_dpc_update.next = True
            debug_control.halt.next = True
            debug_control.step_armed.next = False
            step_arm_delay.next = 0
            debug_control.step_halt_pending.next = False

        elif debug_control.step_halt_pending and debugRegisterBundle.instr_retired:
            pending_dpc.next = debugRegisterBundle.instr_retire_dpc
            pending_cause.next = 4
            pending_dpc_update.next = True
            debug_control.halt.next = True
            debug_control.step_armed.next = False
            step_arm_delay.next = 0
            debug_control.step_halt_pending.next = False

        if not debug_control.ebreak_halt_req and not debug_control.step_halt_pending and \
           not decode_view.downstream_busy and not debugRegisterBundle.req_ack:
            if debugRegisterBundle.haltreq and decode_view.en_i and not decode_view.kill_i:
                debugRegisterBundle.req_ack.next = True
                pending_dpc.next = decode_view.current_ip_i[config.xlen:config.ip_low]
                pending_cause.next = 3
                pending_dpc_update.next = True
                debug_control.halt.next = True
                debug_control.step_armed.next = False
                step_arm_delay.next = 0
            elif debugRegisterBundle.resumereq:
                debugRegisterBundle.req_ack.next = True
                debug_control.halt.next = False
                debugRegisterBundle.dpc_jump.next = True
                debug_control.step_armed.next = False
                if debugCSRBundle.step:
                    step_arm_delay.next = 2

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
