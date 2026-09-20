"""Pipeline-protocol tests for the RV32M controller."""

from __future__ import annotations

from myhdl import ResetSignal, Signal, StopSimulation, always, block, delay, instance

from rtl.config import BonfireConfig
from rtl.muldiv import MulDivControllerBundle
from tests.conftest import run_sim


@block
def muldiv_controller_testbench():
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    config = BonfireConfig()
    config.enable_m_extension = True
    controller = MulDivControllerBundle(config)
    dut = controller.controller(clock, reset)

    @always(delay(5))
    def clock_gen():
        clock.next = not clock

    @instance
    def stimulus():
        controller.port.request_i.next = False
        controller.consume_i.next = False
        controller.port.cancel_i.next = False
        reset.next = True
        yield clock.posedge
        reset.next = False

        controller.port.op1_i.next = 6
        controller.port.op2_i.next = 7
        controller.port.operation_i.next = 0
        controller.rd_i.next = 9
        controller.port.request_i.next = True

        completions = 0
        for _ in range(10):
            yield clock.posedge
            yield delay(1)
            if controller.port.valid_o:
                completions += 1
                assert int(controller.port.result_o) == 42
                break
        else:
            raise AssertionError("multiply request did not complete")

        # Decode keeps the request asserted until the release cycle is
        # consumed.  Holding consume_i low must not trigger a second request.
        for _ in range(3):
            yield clock.posedge
            yield delay(1)
            assert not controller.port.busy_o
            assert not controller.port.valid_o

        # The pipeline consumes the held instruction while Decode replaces it.
        controller.port.request_i.next = False
        controller.consume_i.next = True
        yield clock.posedge
        yield delay(1)
        controller.consume_i.next = False

        for _ in range(8):
            yield clock.posedge
            yield delay(1)
            assert not controller.port.valid_o
        assert completions == 1

        # Cancel an in-flight divide and ensure its late completion is hidden.
        controller.port.op1_i.next = 100
        controller.port.op2_i.next = 7
        controller.port.operation_i.next = 4
        controller.port.request_i.next = True
        yield clock.posedge
        yield delay(1)
        assert controller.port.busy_o

        for _ in range(3):
            yield clock.posedge

        controller.port.cancel_i.next = True
        controller.port.request_i.next = False
        yield clock.posedge
        yield delay(1)
        controller.port.cancel_i.next = False
        assert not controller.port.busy_o

        for _ in range(45):
            yield clock.posedge
            yield delay(1)
            assert not controller.port.valid_o

        raise StopSimulation

    return dut, clock_gen, stimulus


def test_muldiv_controller_request_release_and_cancel(sim_env):
    run_sim(
        muldiv_controller_testbench(),
        trace=False,
        waveforms_dir=sim_env["waveforms_dir"],
        duration=2_000,
        filename="muldiv_controller",
    )
