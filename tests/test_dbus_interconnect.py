from __future__ import annotations

import subprocess
import warnings
from pathlib import Path

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
from tests.toolchain import ghdl_command


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

    ic = DbusInterConnects.Master3SlavesViaSignalArrays(
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
def dbus_interconnect_signal_array_vhdl_tb():
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
def tb_dbus_interconnect(scenario: str):
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
            yield write_word(SLAVE0_BASE, 0x11112222)
            yield read_word(SLAVE0_BASE, value)
            assert value[0] == 0x11112222
            yield read_word(SLAVE1_BASE, value)
            assert value[0] == 0x000000B1
        elif scenario == "slave1":
            yield write_word(SLAVE1_BASE, 0x33334444)
            yield read_word(SLAVE1_BASE, value)
            assert value[0] == 0x33334444
            yield read_word(SLAVE0_BASE, value)
            assert value[0] == 0x000000A0
        elif scenario == "unmatched":
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


def test_dbus_interconnect_signal_array_routes_slave0(sim_env):
    _run_interconnect_scenario(sim_env, "slave0")


def test_dbus_interconnect_signal_array_routes_slave1(sim_env):
    _run_interconnect_scenario(sim_env, "slave1")


def test_dbus_interconnect_signal_array_unmatched_errors(sim_env):
    _run_interconnect_scenario(sim_env, "unmatched")


def test_dbus_interconnect_signal_array_vhdl_conversion(repo_root: Path):
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


def test_dbus_interconnect_master3_vhdl_conversion(repo_root: Path):
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


def _dbus_tb_log_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        marker = "DBUS_TB:"
        if marker in line:
            lines.append(line[line.index(marker):].strip())
    return lines


def test_dbus_interconnect_signal_array_vhdl_testbench(repo_root: Path, sim_env: dict, request, capsys):
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_signal_array_tb"
    output_dir.mkdir(parents=True, exist_ok=True)
    name = "dbus_interconnect_signal_array_tb"

    myhdl_tb = dbus_interconnect_signal_array_vhdl_tb()
    trace, filename = waveform_config(request, sim_env, "dbus_interconnect_signal_array_tb")
    run_sim(
        myhdl_tb,
        trace=trace,
        filename=filename,
        duration=500,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    myhdl_output = capsys.readouterr().out
    myhdl_lines = _dbus_tb_log_lines(myhdl_output)
    assert myhdl_lines

    dut = dbus_interconnect_signal_array_vhdl_tb()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = output_dir / f"{name}.vhd"
    assert vhdl_file.exists()
    assert vhdl_file.stat().st_size > 0

    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    analyze_invocation = ghdl_command(
        "-a",
        "--std=08",
        "--ieee=synopsys",
        "-frelaxed-rules",
        *[str(path.relative_to(output_dir)) for path in vhdl_inputs],
    )
    analyze_result = subprocess.run(
        analyze_invocation.command,
        check=False,
        cwd=output_dir,
        env=analyze_invocation.env,
        capture_output=True,
        text=True,
    )
    assert analyze_result.returncode == 0, (analyze_result.stderr or analyze_result.stdout)

    elaborate_invocation = ghdl_command(
        "-e",
        "--std=08",
        "--ieee=synopsys",
        "-frelaxed-rules",
        name,
    )
    elaborate_result = subprocess.run(
        elaborate_invocation.command,
        check=False,
        cwd=output_dir,
        env=elaborate_invocation.env,
        capture_output=True,
        text=True,
    )
    assert elaborate_result.returncode == 0, (elaborate_result.stderr or elaborate_result.stdout)

    run_invocation = ghdl_command(
        "-r",
        "--std=08",
        "--ieee=synopsys",
        "-frelaxed-rules",
        name,
        "--stop-time=500ns",
    )
    run_result = subprocess.run(
        run_invocation.command,
        check=False,
        cwd=output_dir,
        env=run_invocation.env,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, (run_result.stderr or run_result.stdout)
    ghdl_lines = _dbus_tb_log_lines((run_result.stdout or "") + "\n" + (run_result.stderr or ""))
    assert ghdl_lines == myhdl_lines
    print("DBUS_TB_COMPARE: MyHDL output")
    for line in myhdl_lines:
        print(line)
    print("DBUS_TB_COMPARE: GHDL output")
    for line in ghdl_lines:
        print(line)
