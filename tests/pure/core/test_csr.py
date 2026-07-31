from __future__ import annotations

from myhdl import (
    ResetSignal,
    Signal,
    StopSimulation,
    always,
    block,
    delay,
    instance,
    instances,
)

from rtl.config import BonfireConfig
from rtl.csr import CSRUnitBundle
from rtl.trap import TrapCSRBundle, TrapCSRUpdateBundle
from tests.conftest import run_sim


CSR_MCYCLE = 0xB00
CSR_MCYCLEH = 0xB80
CSR_MBONFIRECFG = 0xFC0

CSR_F3_CSRRW = 0b001
CSR_F3_CSRRS = 0b010


@block
def csr_testbench():
    config = BonfireConfig()
    config.pipeline_length = 4
    config.writeback_bypass = True
    config.enableDebugModule = True
    config.jump_predictor = True
    config.mem_write_early_term = True

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    csr = CSRUnitBundle(config)
    trap_csrs = TrapCSRBundle(config)
    trap_update = TrapCSRUpdateBundle(config)
    dut = csr.CSRUnit(trap_csrs, trap_update, clock, reset)

    observed = {"result": 0, "invalid": False, "valid": False}

    @always(delay(5))
    def clock_gen():
        clock.next = not clock

    def access(address, funct3, source, operand=0):
        csr.csr_adr.next = address
        csr.funct3_i.next = funct3
        csr.source_i.next = source
        csr.op1_i.next = operand
        csr.en_i.next = True
        yield delay(1)

        observed["result"] = int(csr.result_o)
        observed["invalid"] = bool(csr.invalid_op_o)
        observed["valid"] = bool(csr.valid_o)

        yield clock.posedge
        csr.en_i.next = False
        yield delay(1)

    @instance
    def stimulus():
        reset.next = True
        yield clock.posedge
        yield delay(1)
        reset.next = False

        yield access(CSR_MBONFIRECFG, CSR_F3_CSRRS, 0)
        assert observed["valid"]
        assert not observed["invalid"]
        assert observed["result"] == 0x1F
        assert observed["result"] >> 5 == 0

        yield access(CSR_MBONFIRECFG, CSR_F3_CSRRW, 1, 0)
        assert observed["invalid"]
        assert not observed["valid"]

        yield access(CSR_MCYCLE, CSR_F3_CSRRS, 0)
        first_cycle = observed["result"]
        yield access(CSR_MCYCLE, CSR_F3_CSRRS, 0)
        assert observed["result"] == (first_cycle + 1) & 0xFFFFFFFF

        yield access(CSR_MCYCLEH, CSR_F3_CSRRW, 1, 0x12345678)
        assert not observed["invalid"]
        yield access(CSR_MCYCLE, CSR_F3_CSRRW, 1, 0x9ABCDEF0)
        assert not observed["invalid"]
        yield access(CSR_MCYCLE, CSR_F3_CSRRS, 0)
        assert observed["result"] == 0x9ABCDEF0
        yield access(CSR_MCYCLEH, CSR_F3_CSRRS, 0)
        assert observed["result"] == 0x12345678

        yield access(CSR_MCYCLE, CSR_F3_CSRRW, 1, 0x12345678)
        yield access(CSR_MCYCLEH, CSR_F3_CSRRW, 1, 0x9ABCDEF0)
        yield access(CSR_MCYCLE, CSR_F3_CSRRS, 0)
        assert observed["result"] == 0x12345678

        yield access(CSR_MCYCLEH, CSR_F3_CSRRW, 1, 0)
        yield access(CSR_MCYCLE, CSR_F3_CSRRW, 1, 0xFFFFFFFE)
        yield clock.posedge
        yield clock.posedge
        yield delay(1)

        yield access(CSR_MCYCLEH, CSR_F3_CSRRS, 0)
        assert observed["result"] == 1
        yield access(CSR_MCYCLE, CSR_F3_CSRRS, 0)
        assert observed["result"] == 1

        raise StopSimulation

    return instances()


def test_machine_cycle_and_bonfire_config_csrs(sim_env):
    tb = csr_testbench()
    run_sim(
        tb,
        duration=1000,
        waveforms_dir=sim_env["waveforms_dir"],
    )
