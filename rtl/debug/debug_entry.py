"""Decode-stage debug entry and single-step control."""

from myhdl import Signal, block, always, always_comb, enum, instances


t_debug_entry_state = enum(
    'idle',
    'step_first',
    'step_resolve',
    'step_next',
)


class DebugEntryOutputs:
    def __init__(self):
        self.pipeline_hold = Signal(bool(0))
        self.step_resolve = Signal(bool(0))
        self.halt_event = Signal(bool(0))


@block
def DebugEntryController(
    config,
    clock,
    debug_registers,
    debug_csrs,
    debug_csr_update,
    debug_control,
    decode_ip,
    execute_ip,
    decode_enable,
    downstream_busy,
    decode_kill,
    execute_redirect,
    fetch_redirect_pending,
    execute_ebreak,
    outputs,
):
    """Control halt entry without adding latency to normal instruction flow."""

    state = Signal(t_debug_entry_state.idle)
    instruction_ready = Signal(bool(0))
    step_halt_event = Signal(bool(0))
    haltreq_event = Signal(bool(0))

    @always_comb
    def debug_event_comb():
        outputs.pipeline_hold.next = state == t_debug_entry_state.step_resolve
        outputs.step_resolve.next = state == t_debug_entry_state.step_resolve

        instruction_ready.next = decode_enable and not downstream_busy and \
            not decode_kill and not debug_control.kill and \
            not execute_redirect and not fetch_redirect_pending

        step_halt_event.next = not debug_control.halt and \
            state == t_debug_entry_state.step_next and instruction_ready

        haltreq_event.next = not debug_control.halt and debug_registers.haltreq and \
            instruction_ready and not debug_registers.req_ack

        outputs.halt_event.next = execute_ebreak or ( \
            not debug_control.halt and decode_enable and \
            not decode_kill and not debug_control.kill and \
            not execute_redirect and not fetch_redirect_pending and ( \
            state == t_debug_entry_state.step_next or \
            (debug_registers.haltreq and not debug_registers.req_ack)))

    @always(clock.posedge)
    def debug_entry_seq():
        debug_registers.req_ack.next = False
        debug_csr_update.we_dpc.next = False
        debug_csr_update.we_cause.next = False

        if debug_registers.dpc_jump:
            debug_registers.dpc_jump.next = False

        if debug_control.halt:
            if debug_registers.resumereq and not downstream_busy and \
               not debug_registers.req_ack:
                debug_registers.req_ack.next = True
                debug_control.halt.next = False
                debug_registers.dpc_jump.next = True
                if debug_csrs.step:
                    state.next = t_debug_entry_state.step_first
                else:
                    state.next = t_debug_entry_state.idle

        elif execute_ebreak:
            debug_csr_update.dpc.next = execute_ip[config.xlen:config.ip_low]
            debug_csr_update.we_dpc.next = True
            debug_csr_update.cause.next = 1
            debug_csr_update.we_cause.next = True
            debug_control.halt.next = True
            state.next = t_debug_entry_state.idle

        elif step_halt_event:
            debug_csr_update.dpc.next = decode_ip[config.xlen:config.ip_low]
            debug_csr_update.we_dpc.next = True
            debug_csr_update.cause.next = 4
            debug_csr_update.we_cause.next = True
            debug_control.halt.next = True
            state.next = t_debug_entry_state.idle

        elif haltreq_event:
            debug_registers.req_ack.next = True
            debug_csr_update.dpc.next = decode_ip[config.xlen:config.ip_low]
            debug_csr_update.we_dpc.next = True
            debug_csr_update.cause.next = 3
            debug_csr_update.we_cause.next = True
            debug_control.halt.next = True
            state.next = t_debug_entry_state.idle

        elif state == t_debug_entry_state.step_first:
            if instruction_ready:
                state.next = t_debug_entry_state.step_resolve

        elif state == t_debug_entry_state.step_resolve:
            if not downstream_busy:
                state.next = t_debug_entry_state.step_next

    return instances()
