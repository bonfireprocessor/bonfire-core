from myhdl import Signal, Simulation, StopSimulation, delay, instance, modbv

from rtl.config import BonfireConfig
from rtl.control_flow import ControlFlowBundle
from rtl.instructions import BranchFunct3


def test_control_flow_all_branch_conditions_and_not_taken():
    config = BonfireConfig()
    flow = ControlFlowBundle(config)
    branch = Signal(bool(0))
    jump = Signal(bool(0))
    jumpr = Signal(bool(0))
    funct3 = Signal(modbv(0)[3:])
    branch_target = Signal(modbv(0)[config.xlen:])
    jumpr_target = Signal(modbv(0)[config.xlen:])
    equal = Signal(bool(0))
    ge = Signal(bool(0))
    uge = Signal(bool(0))
    dut = flow.controller(branch, jump, jumpr, funct3, branch_target,
                          jumpr_target, equal, ge, uge)

    @instance
    def stimulus():
        branch.next = True
        branch_target.next = 0x104
        cases = (
            (BranchFunct3.RV32_F3_BEQ, True, False, False, True),
            (BranchFunct3.RV32_F3_BNE, False, False, False, True),
            (BranchFunct3.RV32_F3_BLT, False, False, False, True),
            (BranchFunct3.RV32_F3_BGE, False, True, False, True),
            (BranchFunct3.RV32_F3_BLTU, False, False, False, True),
            (BranchFunct3.RV32_F3_BGEU, False, False, True, True),
            (BranchFunct3.RV32_F3_BEQ, False, False, False, False),
        )
        for branch_funct3, eq, signed_ge, unsigned_ge, taken in cases:
            funct3.next = branch_funct3
            equal.next = eq
            ge.next = signed_ge
            uge.next = unsigned_ge
            yield delay(1)
            assert bool(flow.branch_taken_o) == taken
            assert bool(flow.redirect_o) == taken
            assert not flow.link_write_o
        raise StopSimulation

    Simulation(dut, stimulus).run()


def test_control_flow_jumps_clear_jalr_bit_zero_and_fault_on_alignment():
    config = BonfireConfig()
    flow = ControlFlowBundle(config)
    branch = Signal(bool(0))
    jump = Signal(bool(0))
    jumpr = Signal(bool(0))
    funct3 = Signal(modbv(0)[3:])
    branch_target = Signal(modbv(0)[config.xlen:])
    jumpr_target = Signal(modbv(0)[config.xlen:])
    equal = Signal(bool(0))
    ge = Signal(bool(0))
    uge = Signal(bool(0))
    dut = flow.controller(branch, jump, jumpr, funct3, branch_target,
                          jumpr_target, equal, ge, uge)

    @instance
    def stimulus():
        jump.next = True
        branch_target.next = 0x200
        yield delay(1)
        assert flow.redirect_o and flow.link_write_o
        assert not flow.misaligned_o

        jump.next = False
        jumpr.next = True
        jumpr_target.next = 0x301
        yield delay(1)
        assert flow.target_o == 0x300
        assert flow.redirect_o and flow.link_write_o

        jumpr_target.next = 0x302
        yield delay(1)
        assert flow.target_o == 0x302
        assert flow.misaligned_o
        assert not flow.redirect_o and not flow.link_write_o
        assert flow.tval_o == 0x302
        raise StopSimulation

    Simulation(dut, stimulus).run()
