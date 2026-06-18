from __future__ import annotations

import subprocess
import warnings
from pathlib import Path

import pytest
from myhdl import (
    ResetSignal,
    Signal,
    StopSimulation,
    ToVHDLWarning,
    always,
    always_comb,
    always_seq,
    block,
    delay,
    instance,
    instances,
    modbv,
)

from rtl import config
from rtl.bonfire_interfaces import DbusBundle
from rtl.uncore.dbus_interconnect import AdrMask, DbusInterConnects
from tb.ClkDriver import ClkDriver
from tests.conftest import run_sim, waveform_config
from tests.toolchain import fusesoc_command, ghdl_command


CLK_PERIOD = 10
SLAVE0_BASE = 0x80000000
SLAVE1_BASE = 0x90000000
SLAVE2_BASE = 0xA0000000
UNMATCHED_BASE = 0xB0000000


@block
def dbus_dummy_slave(dbus: DbusBundle, clock, reset, reset_value: int, ack_delay_cycles: int = 0):
    reg = Signal(modbv(reset_value)[32:])
    ack = Signal(bool(0))
    delay_count = Signal(modbv(0)[4:])
    active = Signal(bool(0))

    @always_seq(clock.posedge, reset=reset)
    def seq():
        if dbus.en_o and dbus.we_o != 0:
            reg.next = dbus.db_wr
        if ack_delay_cycles == 0:
            ack.next = dbus.en_o
            delay_count.next = 0
            active.next = False
        else:
            ack.next = False
            if not dbus.en_o:
                delay_count.next = 0
                active.next = False
            elif not active:
                active.next = True
                delay_count.next = ack_delay_cycles
            elif delay_count == 0:
                ack.next = True
            else:
                delay_count.next = delay_count - 1

    @always_comb
    def comb():
        if ack_delay_cycles == 0:
            dbus.ack_i.next = dbus.en_o
        else:
            dbus.ack_i.next = ack
        dbus.stall_i.next = False
        dbus.error_i.next = False
        dbus.db_rd.next = reg

    return instances()


@block
def dbus_interconnect_signal_array_wrapper(clock, reset, adr_i, db_wr_i, we_i, en_i, ack_o, error_o, stall_o, db_rd_o):
    conf = config.BonfireConfig()
    master = DbusBundle(conf)
    slave0 = DbusBundle(conf)
    slave1 = DbusBundle(conf)
    slave2 = DbusBundle(conf)

    @always_comb
    def master_inputs():
        master.adr_o.next = adr_i
        master.db_wr.next = db_wr_i
        master.we_o.next = we_i
        master.en_o.next = en_i

    @always_comb
    def master_outputs():
        ack_o.next = master.ack_i
        error_o.next = master.error_i
        stall_o.next = master.stall_i
        db_rd_o.next = master.db_rd

    ic = DbusInterConnects.Master3Slaves(
        master, slave0, slave1, slave2, clock, reset,
        AdrMask(32, 28, 0x8), AdrMask(32, 28, 0x9), AdrMask(32, 28, 0xA))
    slave0_i = dbus_dummy_slave(slave0, clock, reset, 0x000000A0)
    slave1_i = dbus_dummy_slave(slave1, clock, reset, 0x000000B1, ack_delay_cycles=2)
    slave2_i = dbus_dummy_slave(slave2, clock, reset, 0x000000C2)

    return instances()


@block
def dbus_interconnect_master3_wrapper(clock, reset, adr_i, db_wr_i, we_i, en_i, ack_o, error_o, stall_o, db_rd_o):
    conf = config.BonfireConfig()
    master = DbusBundle(conf)
    slave0 = DbusBundle(conf)
    slave1 = DbusBundle(conf)
    slave2 = DbusBundle(conf)

    @always_comb
    def master_inputs():
        master.adr_o.next = adr_i
        master.db_wr.next = db_wr_i
        master.we_o.next = we_i
        master.en_o.next = en_i

    @always_comb
    def master_outputs():
        ack_o.next = master.ack_i
        error_o.next = master.error_i
        stall_o.next = master.stall_i
        db_rd_o.next = master.db_rd

    ic = DbusInterConnects.Master3Slaves(
        master, slave0, slave1, slave2, clock, reset,
        AdrMask(32, 28, 0x8), AdrMask(32, 28, 0x9), AdrMask(32, 28, 0xA))
    slave0_i = dbus_dummy_slave(slave0, clock, reset, 0x000000A0)
    slave1_i = dbus_dummy_slave(slave1, clock, reset, 0x000000B1, ack_delay_cycles=2)
    slave2_i = dbus_dummy_slave(slave2, clock, reset, 0x000000C2)

    return instances()


@block
def dbus_interconnect_master8_wrapper(clock, reset, adr_i, db_wr_i, we_i, en_i, ack_o, error_o, stall_o, db_rd_o):
    conf = config.BonfireConfig()
    master = DbusBundle(conf)
    slave0 = DbusBundle(conf)
    slave3 = DbusBundle(conf)
    slave7 = DbusBundle(conf)

    @always_comb
    def master_inputs():
        master.adr_o.next = adr_i
        master.db_wr.next = db_wr_i
        master.we_o.next = we_i
        master.en_o.next = en_i

    @always_comb
    def master_outputs():
        ack_o.next = master.ack_i
        error_o.next = master.error_i
        stall_o.next = master.stall_i
        db_rd_o.next = master.db_rd

    ic = DbusInterConnects.Master8Slaves(
        master, clock, reset,
        slave0=slave0,
        slave3=slave3,
        slave7=slave7,
        adrmask0=AdrMask(16, 12, 0x8),
        adrmask3=AdrMask(16, 12, 0xA),
        adrmask7=AdrMask(16, 12, 0xF))
    slave0_i = dbus_dummy_slave(slave0, clock, reset, 0x000000A0)
    slave3_i = dbus_dummy_slave(slave3, clock, reset, 0x000000D3, ack_delay_cycles=2)
    slave7_i = dbus_dummy_slave(slave7, clock, reset, 0x000000F7)

    return instances()


@block
def dbus_interconnect_master8_empty_wrapper(clock, reset, adr_i, db_wr_i, we_i, en_i, ack_o, error_o, stall_o, db_rd_o):
    conf = config.BonfireConfig()
    master = DbusBundle(conf)

    @always_comb
    def master_inputs():
        master.adr_o.next = adr_i
        master.db_wr.next = db_wr_i
        master.we_o.next = we_i
        master.en_o.next = en_i

    @always_comb
    def master_outputs():
        ack_o.next = master.ack_i
        error_o.next = master.error_i
        stall_o.next = master.stall_i
        db_rd_o.next = master.db_rd

    ic = DbusInterConnects.Master8Slaves(master, clock, reset)

    return instances()


@block
def dbus_interconnect_master8_two_slave_wrapper(clock, reset, adr_i, db_wr_i, we_i, en_i, ack_o, error_o, stall_o, db_rd_o):
    conf = config.BonfireConfig()
    master = DbusBundle(conf)
    slave0 = DbusBundle(conf)
    slave5 = DbusBundle(conf)

    @always_comb
    def master_inputs():
        master.adr_o.next = adr_i
        master.db_wr.next = db_wr_i
        master.we_o.next = we_i
        master.en_o.next = en_i

    @always_comb
    def master_outputs():
        ack_o.next = master.ack_i
        error_o.next = master.error_i
        stall_o.next = master.stall_i
        db_rd_o.next = master.db_rd

    ic = DbusInterConnects.Master8Slaves(
        master, clock, reset,
        slave0=slave0,
        slave5=slave5,
        adrmask0=AdrMask(16, 12, 0x1),
        adrmask5=AdrMask(16, 12, 0x5))
    slave0_i = dbus_dummy_slave(slave0, clock, reset, 0x00000010)
    slave5_i = dbus_dummy_slave(slave5, clock, reset, 0x00000050, ack_delay_cycles=2)

    return instances()


@block
def dbus_interconnect_signal_array_vhdl_tb():
    # Convertible reference testbench for the 3-slave interconnect path.
    # The printed markers are compared against the converted GHDL run.
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    adr = Signal(modbv(0)[32:])
    db_wr = Signal(modbv(0)[32:])
    we = Signal(modbv(0)[4:])
    en = Signal(bool(0))
    ack = Signal(bool(0))
    err = Signal(bool(0))
    stall = Signal(bool(0))
    db_rd = Signal(modbv(0)[32:])

    dut = dbus_interconnect_signal_array_wrapper(clock, reset, adr, db_wr, we, en, ack, err, stall, db_rd)

    @instance
    def clock_driver():
        while True:
            yield delay(CLK_PERIOD // 2)
            clock.next = not clock

    @instance
    def stimulus():
        print("DBUS_TB: start")
        adr.next = 0
        db_wr.next = 0
        we.next = 0
        en.next = False
        reset.next = True
        print("DBUS_TB: reset assert")
        yield clock.posedge
        yield clock.posedge
        reset.next = False
        print("DBUS_TB: reset release")
        yield clock.posedge

        # Verify that an immediate-ack slave accepts a write and stores the data.
        print("DBUS_TB: write slave0 start")
        adr.next = SLAVE0_BASE
        db_wr.next = modbv(0x11112222)[32:]
        we.next = 0xF
        en.next = True
        yield delay(10)
        assert ack
        assert not err
        assert not stall
        print("DBUS_TB: write slave0 ack")
        yield clock.posedge
        adr.next = 0
        db_wr.next = 0
        we.next = 0
        en.next = False
        yield clock.posedge
        print("DBUS_TB: write slave0 done")

        # Read the written word back through the same decode path.
        print("DBUS_TB: read slave0 start")
        adr.next = SLAVE0_BASE
        we.next = 0
        en.next = True
        yield delay(10)
        assert ack
        assert not err
        assert not stall
        assert db_rd == 0x11112222
        print("DBUS_TB: read slave0 matched")
        yield clock.posedge
        adr.next = 0
        en.next = False
        yield clock.posedge
        print("DBUS_TB: read slave0 done")

        # Verify that a delayed-ack slave holds ack low before completing.
        print("DBUS_TB: read slave1 default start")
        adr.next = SLAVE1_BASE
        we.next = 0
        en.next = True
        yield delay(10)
        assert not ack
        assert not err
        print("DBUS_TB: read slave1 waitstate observed")
        timeout = 0
        while not ack:
            assert timeout < 8
            yield clock.posedge
            yield delay(1)
            timeout = timeout + 1
        assert ack
        assert not err
        assert not stall
        assert db_rd == 0x000000B1
        print("DBUS_TB: read slave1 default matched")
        yield clock.posedge
        adr.next = 0
        en.next = False
        yield clock.posedge
        print("DBUS_TB: read slave1 default done")

        # An address with no matching slave must report an interconnect error.
        print("DBUS_TB: unmatched read start")
        adr.next = UNMATCHED_BASE
        we.next = 0
        en.next = True
        yield delay(10)
        assert not ack
        assert err
        print("DBUS_TB: unmatched read error")
        yield clock.posedge
        adr.next = 0
        en.next = False
        yield clock.posedge
        print("DBUS_TB: done")

        while True:
            yield clock.posedge

    return instances()


@block
def dbus_interconnect_master8_vhdl_tb():
    # Convertible Master8Slaves testbench with two active slots and six None slots.
    # This checks that the sparse wrapper behaves the same in MyHDL and GHDL.
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    adr = Signal(modbv(0)[32:])
    db_wr = Signal(modbv(0)[32:])
    we = Signal(modbv(0)[4:])
    en = Signal(bool(0))
    ack = Signal(bool(0))
    err = Signal(bool(0))
    stall = Signal(bool(0))
    db_rd = Signal(modbv(0)[32:])

    dut = dbus_interconnect_master8_two_slave_wrapper(clock, reset, adr, db_wr, we, en, ack, err, stall, db_rd)

    @instance
    def clock_driver():
        while True:
            yield delay(CLK_PERIOD // 2)
            clock.next = not clock

    @instance
    def stimulus():
        print("DBUS8_TB: start")
        adr.next = 0
        db_wr.next = 0
        we.next = 0
        en.next = False
        reset.next = True
        print("DBUS8_TB: reset assert")
        yield clock.posedge
        yield clock.posedge
        reset.next = False
        print("DBUS8_TB: reset release")
        yield clock.posedge

        # Slot 0 uses an immediate-ack slave and must store a write.
        print("DBUS8_TB: write slave0 start")
        adr.next = 0x00001000
        db_wr.next = modbv(0x12345678)[32:]
        we.next = 0xF
        en.next = True
        yield delay(10)
        assert ack
        assert not err
        assert not stall
        print("DBUS8_TB: write slave0 ack")
        yield clock.posedge
        adr.next = 0
        db_wr.next = 0
        we.next = 0
        en.next = False
        yield clock.posedge

        # Read back the slot 0 register value through the Master8 decode logic.
        print("DBUS8_TB: read slave0 start")
        adr.next = 0x00001000
        we.next = 0
        en.next = True
        yield delay(10)
        assert ack
        assert not err
        assert not stall
        assert db_rd == 0x12345678
        print("DBUS8_TB: read slave0 matched")
        yield clock.posedge
        adr.next = 0
        en.next = False
        yield clock.posedge

        # Slot 5 is delayed to prove that wait states survive VHDL conversion.
        print("DBUS8_TB: read slave5 start")
        adr.next = 0x00005000
        we.next = 0
        en.next = True
        yield delay(10)
        assert not ack
        assert not err
        print("DBUS8_TB: read slave5 waitstate observed")
        timeout = 0
        while not ack:
            assert timeout < 8
            yield clock.posedge
            yield delay(1)
            timeout = timeout + 1
        assert ack
        assert not err
        assert not stall
        assert db_rd == 0x00000050
        print("DBUS8_TB: read slave5 matched")
        yield clock.posedge
        adr.next = 0
        en.next = False
        yield clock.posedge

        # A decoded hole between the active slots must raise error without ack.
        print("DBUS8_TB: unmatched read start")
        adr.next = 0x00002000
        we.next = 0
        en.next = True
        yield delay(10)
        assert not ack
        assert err
        print("DBUS8_TB: unmatched read error")
        yield clock.posedge
        adr.next = 0
        en.next = False
        yield clock.posedge
        print("DBUS8_TB: done")

        while True:
            yield clock.posedge

    return instances()


@block
def tb_dbus_interconnect(scenario: str):
    # MyHDL-only scenario testbench used for focused route and error checks.
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    adr = Signal(modbv(0)[32:])
    db_wr = Signal(modbv(0)[32:])
    we = Signal(modbv(0)[4:])
    en = Signal(bool(0))
    ack = Signal(bool(0))
    error = Signal(bool(0))
    stall = Signal(bool(0))
    db_rd = Signal(modbv(0)[32:])

    clk_driver = ClkDriver(clock, period=CLK_PERIOD)
    dut = dbus_interconnect_signal_array_wrapper(clock, reset, adr, db_wr, we, en, ack, error, stall, db_rd)

    def drive_idle():
        adr.next = 0
        db_wr.next = 0
        we.next = 0
        en.next = False

    def wait_for_ack(expect_error: bool = False):
        timeout = 0
        yield delay(10)
        while not ack and not error:
            assert timeout < 8
            yield clock.posedge
            yield delay(10)
            timeout += 1
        if expect_error:
            assert not ack
            assert error
        else:
            assert ack
            assert not error
            assert not stall

    def write_word(address: int, data: int):
        adr.next = address
        db_wr.next = modbv(data)[32:]
        we.next = 0xF
        en.next = True
        yield wait_for_ack()
        yield clock.posedge
        drive_idle()
        yield clock.posedge

    def read_word(address: int, target: list[int]):
        adr.next = address
        db_wr.next = 0
        we.next = 0
        en.next = True
        yield wait_for_ack()
        target[0] = int(db_rd)
        yield clock.posedge
        drive_idle()
        yield clock.posedge

    def read_unmatched(address: int):
        adr.next = address
        db_wr.next = 0
        we.next = 0
        en.next = True
        yield wait_for_ack(expect_error=True)
        yield clock.posedge
        drive_idle()
        yield clock.posedge

    @instance
    def stimulus():
        drive_idle()
        reset.next = True
        yield clock.posedge
        reset.next = False
        yield clock.posedge

        value = [0]

        if scenario == "slave0":
            # Route a write/read transaction to slave0, then ensure slave1 is unaffected.
            yield write_word(SLAVE0_BASE, 0x11112222)
            yield read_word(SLAVE0_BASE, value)
            assert value[0] == 0x11112222
            yield read_word(SLAVE1_BASE, value)
            assert value[0] == 0x000000B1
        elif scenario == "slave1":
            # Route a write/read transaction to the delayed slave1 path.
            yield write_word(SLAVE1_BASE, 0x33334444)
            yield read_word(SLAVE1_BASE, value)
            assert value[0] == 0x33334444
            yield read_word(SLAVE0_BASE, value)
            assert value[0] == 0x000000A0
        elif scenario == "unmatched":
            # Check the no-match error path, then confirm normal routing still works.
            yield read_unmatched(UNMATCHED_BASE)
            yield write_word(SLAVE2_BASE, 0x55556666)
            yield read_word(SLAVE2_BASE, value)
            assert value[0] == 0x55556666
        else:
            raise AssertionError("unknown scenario: {}".format(scenario))

        raise StopSimulation

    return instances()


def _run_interconnect_scenario(sim_env: dict, scenario: str):
    tb = tb_dbus_interconnect(scenario)
    run_sim(tb, duration=2_000, waveforms_dir=sim_env["waveforms_dir"])


@block
def tb_dbus_interconnect_master8(scenario: str):
    # MyHDL-only Master8Slaves testbench for sparse and empty-slot behavior.
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    adr = Signal(modbv(0)[32:])
    db_wr = Signal(modbv(0)[32:])
    we = Signal(modbv(0)[4:])
    en = Signal(bool(0))
    ack = Signal(bool(0))
    error = Signal(bool(0))
    stall = Signal(bool(0))
    db_rd = Signal(modbv(0)[32:])

    clk_driver = ClkDriver(clock, period=CLK_PERIOD)
    if scenario == "empty":
        dut = dbus_interconnect_master8_empty_wrapper(clock, reset, adr, db_wr, we, en, ack, error, stall, db_rd)
    else:
        dut = dbus_interconnect_master8_wrapper(clock, reset, adr, db_wr, we, en, ack, error, stall, db_rd)

    def drive_idle():
        adr.next = 0
        db_wr.next = 0
        we.next = 0
        en.next = False

    def wait_for_ack(expect_error: bool = False):
        timeout = 0
        yield delay(10)
        while not ack and not error:
            assert timeout < 8
            yield clock.posedge
            yield delay(10)
            timeout += 1
        if expect_error:
            assert not ack
            assert error
        else:
            assert ack
            assert not error
            assert not stall

    def read_word(address: int, target: list[int]):
        adr.next = address
        db_wr.next = 0
        we.next = 0
        en.next = True
        yield wait_for_ack()
        target[0] = int(db_rd)
        yield clock.posedge
        drive_idle()
        yield clock.posedge

    def read_error(address: int):
        adr.next = address
        db_wr.next = 0
        we.next = 0
        en.next = True
        yield wait_for_ack(expect_error=True)
        yield clock.posedge
        drive_idle()
        yield clock.posedge

    @instance
    def stimulus():
        drive_idle()
        reset.next = True
        yield clock.posedge
        reset.next = False
        yield clock.posedge

        value = [0]
        if scenario == "route":
            # Active slots 0, 3, and 7 must decode while inactive slots remain holes.
            yield read_word(0x00008000, value)
            assert value[0] == 0x000000A0
            yield read_word(0x0000A000, value)
            assert value[0] == 0x000000D3
            yield read_word(0x0000F000, value)
            assert value[0] == 0x000000F7
            yield read_error(0x0000B000)
        elif scenario == "empty":
            # With all slaves disabled, every access must return an error.
            yield read_error(0x80000000)
            yield read_error(0x00000000)
        else:
            raise AssertionError("unknown scenario: {}".format(scenario))

        raise StopSimulation

    return instances()


def _run_master8_scenario(sim_env: dict, scenario: str):
    tb = tb_dbus_interconnect_master8(scenario)
    run_sim(tb, duration=2_000, waveforms_dir=sim_env["waveforms_dir"])


def test_dbus_interconnect_signal_array_routes_slave0(sim_env):
    # Basic MyHDL simulation: route writes and reads through slave0.
    _run_interconnect_scenario(sim_env, "slave0")


def test_dbus_interconnect_signal_array_routes_slave1(sim_env):
    # Basic MyHDL simulation: route writes and reads through delayed slave1.
    _run_interconnect_scenario(sim_env, "slave1")


def test_dbus_interconnect_signal_array_unmatched_errors(sim_env):
    # Basic MyHDL simulation: unmatched access must signal error.
    _run_interconnect_scenario(sim_env, "unmatched")


def test_dbus_interconnect_master8_routes_sparse_slots(sim_env):
    # Master8Slaves MyHDL simulation: active sparse slots decode correctly.
    _run_master8_scenario(sim_env, "route")


def test_dbus_interconnect_master8_all_none_errors(sim_env):
    # Master8Slaves MyHDL simulation: an all-None interconnect rejects all accesses.
    _run_master8_scenario(sim_env, "empty")


def test_dbus_interconnect_master8_logs_resolved_address_map(capsys):
    # Construction-time diagnostics must show the resolved 32-bit mappings.
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    adr = Signal(modbv(0)[32:])
    db_wr = Signal(modbv(0)[32:])
    we = Signal(modbv(0)[4:])
    en = Signal(bool(0))
    ack = Signal(bool(0))
    error = Signal(bool(0))
    stall = Signal(bool(0))
    db_rd = Signal(modbv(0)[32:])

    dbus_interconnect_master8_wrapper(clock, reset, adr, db_wr, we, en, ack, error, stall, db_rd)

    out = capsys.readouterr().out
    assert "Master8Slaves: DBUS address map" in out
    assert "slot 0 slave0 active" in out
    assert "base=0x00008000" in out
    assert "slot 3 slave3 active" in out
    assert "base=0x0000a000" in out
    assert "slot 7 slave7 active" in out
    assert "base=0x0000f000" in out
    assert "slot 1 slave1 disabled" in out


def test_dbus_interconnect_master8_rejects_missing_mask():
    # A present slave without an address mask is an invalid mapping.
    conf = config.BonfireConfig()
    master = DbusBundle(conf)
    slave0 = DbusBundle(conf)
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    with pytest.raises(AssertionError, match="has a slave but no address mask"):
        DbusInterConnects.Master8Slaves(master, clock, reset, slave0=slave0)


def test_dbus_interconnect_master8_rejects_mask_on_disabled_slot():
    # A disabled slot must not carry an address mask.
    conf = config.BonfireConfig()
    master = DbusBundle(conf)
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    with pytest.raises(AssertionError, match="disabled but has an address mask"):
        DbusInterConnects.Master8Slaves(
            master, clock, reset, adrmask0=AdrMask(32, 28, 0x8))


def test_dbus_interconnect_master8_rejects_overlapping_masks():
    # Overlapping decode regions must be rejected before conversion/simulation.
    conf = config.BonfireConfig()
    master = DbusBundle(conf)
    slave0 = DbusBundle(conf)
    slave1 = DbusBundle(conf)
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)

    with pytest.raises(AssertionError, match="overlapping address decode"):
        DbusInterConnects.Master8Slaves(
            master,
            clock,
            reset,
            slave0=slave0,
            slave1=slave1,
            adrmask0=AdrMask(32, 28, 0x8),
            adrmask1=AdrMask(31, 28, 0x0))


def test_dbus_interconnect_signal_array_vhdl_conversion(repo_root: Path):
    # Conversion smoke test: MyHDL must emit VHDL that GHDL can analyze.
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_signal_array"
    output_dir.mkdir(parents=True, exist_ok=True)

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    adr = Signal(modbv(0)[32:])
    db_wr = Signal(modbv(0)[32:])
    we = Signal(modbv(0)[4:])
    en = Signal(bool(0))
    ack = Signal(bool(0))
    error = Signal(bool(0))
    stall = Signal(bool(0))
    db_rd = Signal(modbv(0)[32:])

    dut = dbus_interconnect_signal_array_wrapper(clock, reset, adr, db_wr, we, en, ack, error, stall, db_rd)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name="dbus_interconnect_signal_array")

    vhdl_file = output_dir / "dbus_interconnect_signal_array.vhd"
    assert vhdl_file.exists()
    assert vhdl_file.stat().st_size > 0

    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    invocation = ghdl_command(
        "-a",
        "--std=08",
        "--ieee=synopsys",
        "-frelaxed-rules",
        *[str(path.relative_to(output_dir)) for path in vhdl_inputs],
    )
    result = subprocess.run(
        invocation.command,
        check=False,
        cwd=output_dir,
        env=invocation.env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stderr or result.stdout)

def test_dbus_interconnect_master8_vhdl_conversion(repo_root: Path):
    # Conversion smoke test for Master8Slaves with sparse active slots.
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_master8"
    output_dir.mkdir(parents=True, exist_ok=True)

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    adr = Signal(modbv(0)[32:])
    db_wr = Signal(modbv(0)[32:])
    we = Signal(modbv(0)[4:])
    en = Signal(bool(0))
    ack = Signal(bool(0))
    error = Signal(bool(0))
    stall = Signal(bool(0))
    db_rd = Signal(modbv(0)[32:])

    dut = dbus_interconnect_master8_wrapper(clock, reset, adr, db_wr, we, en, ack, error, stall, db_rd)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name="dbus_interconnect_master8")

    vhdl_file = output_dir / "dbus_interconnect_master8.vhd"
    assert vhdl_file.exists()
    assert vhdl_file.stat().st_size > 0

    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    invocation = ghdl_command(
        "-a",
        "--std=08",
        "--ieee=synopsys",
        "-frelaxed-rules",
        *[str(path.relative_to(output_dir)) for path in vhdl_inputs],
    )
    result = subprocess.run(
        invocation.command,
        check=False,
        cwd=output_dir,
        env=invocation.env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stderr or result.stdout)


def test_dbus_interconnect_master3_vhdl_conversion(repo_root: Path):
    # Conversion smoke test for the public Master3Slaves wrapper.
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_master3"
    output_dir.mkdir(parents=True, exist_ok=True)

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    adr = Signal(modbv(0)[32:])
    db_wr = Signal(modbv(0)[32:])
    we = Signal(modbv(0)[4:])
    en = Signal(bool(0))
    ack = Signal(bool(0))
    error = Signal(bool(0))
    stall = Signal(bool(0))
    db_rd = Signal(modbv(0)[32:])

    dut = dbus_interconnect_master3_wrapper(clock, reset, adr, db_wr, we, en, ack, error, stall, db_rd)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name="dbus_interconnect_master3")

    vhdl_file = output_dir / "dbus_interconnect_master3.vhd"
    assert vhdl_file.exists()
    assert vhdl_file.stat().st_size > 0

    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    invocation = ghdl_command(
        "-a",
        "--std=08",
        "--ieee=synopsys",
        "-frelaxed-rules",
        *[str(path.relative_to(output_dir)) for path in vhdl_inputs],
    )
    result = subprocess.run(
        invocation.command,
        check=False,
        cwd=output_dir,
        env=invocation.env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stderr or result.stdout)


def _dbus_tb_log_lines(text: str, marker: str = "DBUS_TB:") -> list[str]:
    lines = []
    for line in text.splitlines():
        if marker in line:
            lines.append(line[line.index(marker):].strip())
    return lines


def _run_converted_vhdl_testbench(dut, name: str, output_dir: Path) -> str:
    """Convert a testbench and run its GHDL simulation through FuseSoC."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = output_dir / f"{name}.vhd"
    assert vhdl_file.exists()
    assert vhdl_file.stat().st_size > 0

    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    core_file = output_dir / f"{name}.core"
    core_file.write_text(
        "CAPI=2:\n"
        f"name: ::{name}:0\n"
        "filesets:\n"
        "  rtl:\n"
        "    file_type: vhdlSource-2008\n"
        "    files:\n"
        + "".join(f"      - {path.name}\n" for path in vhdl_inputs)
        + "targets:\n"
        "  sim:\n"
        "    default_tool: ghdl\n"
        "    filesets: [rtl]\n"
        "    tools:\n"
        "      ghdl:\n"
        "        analyze_options: [--ieee=synopsys, -frelaxed-rules]\n"
        "        run_options: [--stop-time=500ns]\n"
        f"    toplevel: {name}\n"
    )

    invocation = fusesoc_command(
        "--cores-root", str(output_dir), "run", "--target=sim", f"::{name}:0")
    result = subprocess.run(
        invocation.command,
        check=False,
        cwd=output_dir,
        env=invocation.env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (result.stderr or result.stdout)
    return (result.stdout or "") + "\n" + (result.stderr or "")


def test_dbus_interconnect_signal_array_vhdl_testbench(repo_root: Path, sim_env: dict, request, capsys):
    # Compare the convertible 3-slave testbench logs from MyHDL and GHDL.
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_signal_array_tb"
    name = "dbus_interconnect_signal_array_tb"

    myhdl_tb = dbus_interconnect_signal_array_vhdl_tb()
    trace, filename = waveform_config(request, sim_env, name)
    run_sim(
        myhdl_tb,
        trace=trace,
        filename=filename,
        duration=500,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    myhdl_lines = _dbus_tb_log_lines(capsys.readouterr().out)
    assert myhdl_lines

    ghdl_output = _run_converted_vhdl_testbench(
        dbus_interconnect_signal_array_vhdl_tb(), name, output_dir)
    ghdl_lines = _dbus_tb_log_lines(ghdl_output)
    assert ghdl_lines == myhdl_lines


def test_dbus_interconnect_master8_vhdl_testbench(repo_root: Path, sim_env: dict, request, capsys):
    # Compare the convertible two-slave Master8 testbench logs from MyHDL and GHDL.
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_master8_tb"
    name = "dbus_interconnect_master8_tb"

    myhdl_tb = dbus_interconnect_master8_vhdl_tb()
    trace, filename = waveform_config(request, sim_env, name)
    run_sim(
        myhdl_tb,
        trace=trace,
        filename=filename,
        duration=500,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    myhdl_lines = _dbus_tb_log_lines(capsys.readouterr().out, marker="DBUS8_TB:")
    assert myhdl_lines

    ghdl_output = _run_converted_vhdl_testbench(
        dbus_interconnect_master8_vhdl_tb(), name, output_dir)
    ghdl_lines = _dbus_tb_log_lines(ghdl_output, marker="DBUS8_TB:")
    assert ghdl_lines == myhdl_lines
