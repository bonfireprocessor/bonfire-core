from myhdl import Signal, Simulation, StopSimulation, delay, instance, modbv

from rtl.config import BonfireConfig
from rtl.instructions import LoadFunct3, StoreFunct3
from rtl.lsu_issue import LoadStoreIssueBundle
from rtl.static_data_access import DataAccessFaultMode, DataAccessRegion


def test_lsu_issue_checker_classifies_format_alignment_and_address():
    config = BonfireConfig()
    issue = LoadStoreIssueBundle(config)
    access = Signal(bool(0))
    store = Signal(bool(0))
    funct3 = Signal(modbv(0)[3:])
    op1 = Signal(modbv(0)[config.xlen:])
    displacement = Signal(modbv(0)[12:])
    dut = issue.checker(access, store, funct3, op1, displacement)

    @instance
    def stimulus():
        access.next = True
        funct3.next = LoadFunct3.RV32_F3_LW
        op1.next = 0x1000
        displacement.next = 4
        yield delay(1)
        assert issue.effective_address_o == 0x1004
        assert issue.word_mode_o
        assert not issue.invalid_o
        assert not issue.misaligned_o

        funct3.next = LoadFunct3.RV32_F3_LH
        displacement.next = 1
        yield delay(1)
        assert issue.hword_mode_o
        assert issue.misaligned_o

        store.next = True
        funct3.next = LoadFunct3.RV32_F3_LBU
        displacement.next = 0
        yield delay(1)
        assert issue.invalid_o
        assert not issue.misaligned_o
        raise StopSimulation

    Simulation(dut, stimulus).run()


def test_lsu_issue_checker_applies_static_permissions():
    config = BonfireConfig()
    config.data_access_fault_mode = DataAccessFaultMode.STATIC_MAP
    config.data_access_regions = (
        DataAccessRegion(0x80000000, 0xfffff000, readable=True,
                         writable=False),
    )
    issue = LoadStoreIssueBundle(config)
    access = Signal(bool(0))
    store = Signal(bool(0))
    funct3 = Signal(modbv(0)[3:])
    op1 = Signal(modbv(0)[config.xlen:])
    displacement = Signal(modbv(0)[12:])
    dut = issue.checker(access, store, funct3, op1, displacement)

    @instance
    def stimulus():
        access.next = True
        funct3.next = LoadFunct3.RV32_F3_LW
        op1.next = 0x80001000
        displacement.next = 0xffc
        yield delay(1)
        assert issue.effective_address_o == 0x80000ffc
        assert not issue.access_fault_o

        store.next = True
        funct3.next = StoreFunct3.RV32_F3_SW
        yield delay(1)
        assert issue.access_fault_o

        store.next = False
        op1.next = 0x80001004
        yield delay(1)
        assert issue.access_fault_o
        raise StopSimulation

    Simulation(dut, stimulus).run()
