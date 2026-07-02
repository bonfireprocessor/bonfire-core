from __future__ import annotations

from myhdl import Signal, StopSimulation, always, block, delay, instance, instances, modbv

from rtl import config
from rtl.debug.debug_csrs import DebugCSRBundle, DebugCSRUpdateBundle
from rtl.debug.debug_module import DebugHartControlBundle, DebugHartViewBundle, DebugModuleController
from rtl.debug.dm_registers import DebugModuleRegisterBundle
from rtl.debug.types import t_abstract_command_state

from .conftest import run_sim


@block
def debug_module_controller_testbench():
    conf = config.BonfireConfig()
    clock = Signal(bool(0))
    debug_regs = DebugModuleRegisterBundle(conf)
    debug_csrs = DebugCSRBundle(conf)
    debug_csr_update = DebugCSRUpdateBundle(conf)
    decode_view = DebugHartViewBundle(conf)
    debug_control = DebugHartControlBundle(conf)
    progbuf_pointer = Signal(modbv(0)[1:])
    progbuf_last = Signal(bool(1))

    dut = DebugModuleController(
        conf,
        clock,
        debug_regs,
        debug_csrs,
        debug_csr_update,
        decode_view,
        debug_control,
        progbuf_pointer,
        progbuf_last,
    )

    @always(delay(5))
    def clock_driver():
        clock.next = not clock

    @instance
    def stimulus():
        decode_view.en_i.next = True
        decode_view.current_ip_i.next = 0x40
        yield delay(1)

        # A newly accepted halt does not start an abstract command until the
        # following cycle because sequential logic observes the old halt state.
        debug_regs.haltreq.next = True
        debug_regs.abstract_command_new.next = True
        debug_regs.transfer.next = True
        debug_regs.write.next = True
        yield clock.posedge
        yield delay(1)
        assert debug_control.halt
        assert debug_regs.req_ack
        assert debug_regs.abstract_command_state == t_abstract_command_state.none

        debug_regs.haltreq.next = False
        yield clock.posedge
        yield delay(1)
        assert not debug_regs.req_ack
        assert debug_regs.abstract_command_state == t_abstract_command_state.taken

        debug_regs.abstract_command_new.next = False
        yield clock.posedge
        yield delay(1)
        assert debug_regs.abstract_command_state == t_abstract_command_state.none

        # Resume normally so EBREAK can be observed in the running state.
        debug_regs.resumereq.next = True
        yield clock.posedge
        yield delay(1)
        assert debug_regs.req_ack
        assert not debug_control.halt

        debug_regs.resumereq.next = False
        yield clock.posedge
        yield delay(1)
        assert not debug_regs.req_ack
        yield clock.posedge
        yield delay(1)
        assert not debug_regs.dpc_jump

        # EBREAK has priority over a simultaneous external halt request.
        debug_regs.haltreq.next = True
        debug_csrs.ebreakm.next = True
        decode_view.ebreak_i.next = True
        decode_view.current_ip_i.next = 0x80
        yield delay(1)
        yield clock.posedge
        yield delay(1)
        assert debug_control.halt
        assert not debug_regs.req_ack
        assert debug_csr_update.we_dpc
        assert debug_csr_update.dpc == 0x20
        assert debug_csr_update.cause == 1

        # Resume with step enabled. Arming waits for dpc_jump/kill to clear and
        # for decode to accept the first post-resume instruction.
        debug_regs.haltreq.next = False
        debug_regs.resumereq.next = True
        decode_view.ebreak_i.next = False
        debug_csrs.step.next = True
        yield delay(1)
        yield clock.posedge
        yield delay(1)
        assert debug_regs.req_ack
        assert not debug_control.halt
        assert debug_regs.dpc_jump
        assert not debug_control.step_halt_pending

        debug_regs.resumereq.next = False
        yield clock.posedge
        yield delay(1)
        assert not debug_regs.req_ack
        assert not debug_regs.dpc_jump
        assert not debug_control.step_halt_pending

        yield clock.posedge
        yield delay(1)
        assert debug_control.step_halt_pending

        # While a step is pending, an external halt request remains blocked.
        debug_regs.haltreq.next = True
        yield clock.posedge
        yield delay(1)
        assert not debug_regs.req_ack
        assert not debug_control.halt

        # Retire completes the step and wins over the simultaneous halt request.
        debug_regs.instr_retired.next = True
        debug_regs.instr_retire_dpc.next = 0x31
        yield clock.posedge
        yield delay(1)
        assert debug_control.halt
        assert not debug_control.step_halt_pending
        assert not debug_regs.req_ack
        assert debug_csr_update.we_dpc
        assert debug_csr_update.dpc == 0x31
        assert debug_csr_update.cause == 4

        # The still-active halt request is acknowledged on the next cycle, and
        # req_ack is forced low for one cycle before another request is handled.
        debug_regs.instr_retired.next = False
        yield clock.posedge
        yield delay(1)
        assert debug_regs.req_ack
        yield clock.posedge
        yield delay(1)
        assert not debug_regs.req_ack

        raise StopSimulation

    return instances()


def test_debug_module_controller_event_priority(sim_env):
    run_sim(
        debug_module_controller_testbench(),
        trace=False,
        duration=500,
        waveforms_dir=sim_env["waveforms_dir"],
    )
