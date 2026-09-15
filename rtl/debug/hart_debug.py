"""Hart halt, resume, EBREAK, and single-step control."""

from __future__ import annotations

from typing import Any

from myhdl import Signal, always, always_comb, block, enum, instances, modbv

from rtl.debug.pipeline_adapter import DebugPipelineEventBundle, DebugPipelineRequestBundle
from rtl.debug.types import t_debug_hart_state


t_hart_debug_state = enum(
    'running', 'halt_pending', 'halted', 'step_issue', 'step_wait',
    'halt_exception', 'step_exception',
)


@block
def HartDebugController(
    config: Any,
    clock: Any,
    debug_regs: Any,
    debug_csrs: Any,
    debug_csr_update: Any,
    request: DebugPipelineRequestBundle,
    events: DebugPipelineEventBundle,
) -> Any:
    """Own the architectural debug-mode state of one hart."""

    state = Signal(t_hart_debug_state.running)
    redirect_valid = Signal(bool(0))
    redirect_pc = Signal(modbv(0)[config.xlen:])

    @always_comb
    def outputs():
        request.allow_fetch.next = state == t_hart_debug_state.running or state == t_hart_debug_state.step_issue
        if state == t_hart_debug_state.running and debug_regs.haltreq:
            request.allow_fetch.next = False
        # Execute kills a faulting instruction locally.  Feeding a Program
        # Buffer exception back into the same stage as a combinational debug
        # flush creates a trap -> debug -> decode timing loop.
        request.flush.next = events.ebreak or redirect_valid
        request.redirect_valid.next = redirect_valid
        request.redirect_pc.next = redirect_pc

        if state == t_hart_debug_state.halted:
            debug_regs.hart_state.next = t_debug_hart_state.halted
        else:
            debug_regs.hart_state.next = t_debug_hart_state.running

    @always(clock.posedge)
    def state_machine():
        debug_regs.req_ack.next = False
        redirect_valid.next = False
        debug_csr_update.we_dpc.next = False
        debug_csr_update.we_cause.next = False

        if not debug_regs.dmactive and state == t_hart_debug_state.halt_pending:
            state.next = t_hart_debug_state.running

        elif events.ebreak and state != t_hart_debug_state.halted:
            debug_csr_update.dpc.next = events.ebreak_pc[config.xlen:config.ip_low]
            debug_csr_update.cause.next = 1
            debug_csr_update.we_dpc.next = True
            debug_csr_update.we_cause.next = True
            state.next = t_hart_debug_state.halted

        elif state == t_hart_debug_state.running:
            if debug_regs.haltreq:
                state.next = t_hart_debug_state.halt_pending

        elif state == t_hart_debug_state.halt_pending:
            if events.instruction_exception:
                state.next = t_hart_debug_state.halt_exception
            elif events.pipeline_empty:
                debug_regs.req_ack.next = True
                debug_csr_update.dpc.next = events.next_pc[config.xlen:config.ip_low]
                debug_csr_update.cause.next = 3
                debug_csr_update.we_dpc.next = True
                debug_csr_update.we_cause.next = True
                state.next = t_hart_debug_state.halted

        elif state == t_hart_debug_state.halt_exception:
            debug_regs.req_ack.next = True
            debug_csr_update.dpc.next = \
                events.exception_next_pc[config.xlen:config.ip_low]
            debug_csr_update.cause.next = 3
            debug_csr_update.we_dpc.next = True
            debug_csr_update.we_cause.next = True
            state.next = t_hart_debug_state.halted

        elif state == t_hart_debug_state.halted:
            if debug_regs.resumereq:
                debug_regs.req_ack.next = True
                redirect_valid.next = True
                redirect_pc.next = debug_regs.dpc << config.ip_low
                if debug_csrs.step:
                    state.next = t_hart_debug_state.step_issue
                else:
                    state.next = t_hart_debug_state.running

        elif state == t_hart_debug_state.step_issue:
            if events.instruction_accepted:
                state.next = t_hart_debug_state.step_wait

        elif state == t_hart_debug_state.step_wait:
            if events.instruction_complete:
                debug_csr_update.dpc.next = events.next_pc[config.xlen:config.ip_low]
                debug_csr_update.cause.next = 4
                debug_csr_update.we_dpc.next = True
                debug_csr_update.we_cause.next = True
                state.next = t_hart_debug_state.halted
            elif events.instruction_exception:
                # Cross a state-register boundary before writing DPC.  The
                # architectural next PC is registered to MTVEC concurrently
                # with the exception, so no Execute trap cone reaches DPC.
                state.next = t_hart_debug_state.step_exception

        elif state == t_hart_debug_state.step_exception:
            debug_csr_update.dpc.next = \
                events.exception_next_pc[config.xlen:config.ip_low]
            debug_csr_update.cause.next = 4
            debug_csr_update.we_dpc.next = True
            debug_csr_update.we_cause.next = True
            state.next = t_hart_debug_state.halted

    return instances()
