"""
Test VHDL conversion of selected MyHDL blocks.
"""

from __future__ import annotations

import subprocess
import warnings
from pathlib import Path

import pytest
from myhdl import ResetSignal, Signal, ToVHDLWarning, always_comb, block, instances, intbv, modbv

from rtl import bonfire_core_top, bonfire_interfaces, config
from rtl.debug import (
    DmiBundle,
    Ecp5JtaggClient,
    Ecp5JtaggInputBundle,
    Ecp5JtaggLedDemo,
    Ecp5JtaggOutputBundle,
)
from rtl.divider import DividerBundle
from rtl.debug.jtag_dtm import JtagDTM
from rtl.soc.bonfire_core_soc import BonfireCoreSoC
from rtl.soc.bonfire_core_soc_generator import (
    BonfireCoreSoCInstanceGenerator,
    BonfireCoreSoCTestbenchGenerator,
)
from tests.toolchain import ghdl_command, yosys_command

pytestmark = pytest.mark.filterwarnings("ignore::myhdl.ToVHDLWarning")


def _conversion_output_dir(repo_root: Path, name: str) -> Path:
    output_dir = repo_root / "vhdl_gen" / name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _assert_vhdl_file(output_dir: Path, name: str) -> Path:
    vhdl_file = output_dir / f"{name}.vhd"
    assert vhdl_file.exists(), f"VHDL file not created: {vhdl_file}"
    assert vhdl_file.stat().st_size > 0, f"VHDL file is empty: {vhdl_file}"

    content = vhdl_file.read_text()
    assert "entity" in content.lower(), "VHDL file missing 'entity' keyword"
    assert "architecture" in content.lower(), "VHDL file missing 'architecture' keyword"
    return vhdl_file


def _analyze_with_ghdl(output_dir: Path, vhdl_file: Path) -> None:
    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    assert vhdl_inputs, "No VHDL files found for GHDL analysis"
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
    if result.returncode != 0:
        error_text = (result.stderr or result.stdout).strip()
        pytest.fail(f"ghdl -a failed for {vhdl_file.name}\n{error_text}", pytrace=False)


def _synthesize_ecp5_with_yosys(output_dir: Path, name: str, extra_vhdl_files: list[Path] | None = None) -> Path:
    json_file = output_dir / f"{name}.json"
    log_file = output_dir / "yosys.log"
    vhdl_files = (
        sorted(output_dir.glob("pck_myhdl_*.vhd"))
        + (extra_vhdl_files or [])
        + [output_dir / f"{name}.vhd"]
    )
    script = (
        "plugin -i ghdl; "
        "ghdl --std=08 --ieee=synopsys -frelaxed-rules "
        + " ".join(str(path.name) for path in vhdl_files)
        + " -e "
        + name
        + "; synth_ecp5 -top "
        + name
        + " -json "
        + json_file.name
    )
    invocation = yosys_command(script)
    result = subprocess.run(
        invocation.command,
        check=False,
        cwd=output_dir,
        env=invocation.env,
        capture_output=True,
        text=True,
    )
    log_file.write_text(
        (result.stdout or "") + (result.stderr or ""),
        encoding="utf-8",
    )
    if result.returncode != 0:
        error_text = (result.stderr or result.stdout).strip()
        pytest.fail(f"yosys synth_ecp5 failed for {name}\n{error_text}", pytrace=False)
    return json_file


@pytest.mark.parametrize(
    ("enable_debug", "name"),
    [
        (False, "bonfire_core_top_plain"),
        (True, "bonfire_core_top_debug"),
    ],
)
def test_core_vhdl_conversion(enable_debug: bool, name: str, repo_root: Path):
    output_dir = _conversion_output_dir(repo_root, name)
    conf = config.BonfireConfig()
    conf.enableDebugModule = enable_debug

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    ibus = bonfire_interfaces.DbusBundle(conf, readOnly=True)
    dbus = bonfire_interfaces.DbusBundle(conf)
    control = bonfire_interfaces.ControlBundle(conf)
    debug = bonfire_interfaces.DebugOutputBundle(conf)
    dtm = DmiBundle(conf) if enable_debug else None

    core = bonfire_core_top.BonfireCoreTop(conf)
    dut = core.createInstance(ibus, dbus, control, clock, reset, debug, debugTransportBundle=dtm)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = _assert_vhdl_file(output_dir, name)
    _analyze_with_ghdl(output_dir, vhdl_file)

def test_divider_vhdl_conversion(repo_root: Path):
    name = "divider"
    output_dir = _conversion_output_dir(repo_root, name)

    clk = Signal(bool(0))
    rst = ResetSignal(0, active=1, isasync=False)
    ce_i = Signal(bool(0))
    op1_i = Signal(intbv(0)[32:])
    op2_i = Signal(intbv(0)[32:])
    signed_i = Signal(bool(0))
    rem_i = Signal(bool(0))
    ce_o = Signal(bool(0))
    result_o = Signal(intbv(0)[32:])

    @block
    def divider_wrapper(clk, rst, ce_i, op1_i, op2_i, signed_i, rem_i, ce_o, result_o):
        divider_bundle = DividerBundle(xlen=32)

        @always_comb
        def connect_inputs():
            divider_bundle.ce_i.next = ce_i
            divider_bundle.op1_i.next = op1_i
            divider_bundle.op2_i.next = op2_i
            divider_bundle.signed_i.next = signed_i
            divider_bundle.rem_i.next = rem_i

        @always_comb
        def connect_outputs():
            ce_o.next = divider_bundle.ce_o
            result_o.next = divider_bundle.result_o

        div_inst = divider_bundle.divider(clk, rst)

        return instances()

    inst = divider_wrapper(clk, rst, ce_i, op1_i, op2_i, signed_i, rem_i, ce_o, result_o)
    inst.convert(hdl="VHDL", path=str(output_dir), name=name)

    _assert_vhdl_file(output_dir, name)


def test_jtag_dtm_vhdl_conversion(repo_root: Path):
    name = "jtag_dtm"
    output_dir = _conversion_output_dir(repo_root, name)

    conf = config.BonfireConfig()
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    tck = Signal(bool(0))
    trstn = Signal(bool(1))
    tms = Signal(bool(0))
    tdi = Signal(bool(0))
    tdo = Signal(bool(0))
    dtm = DmiBundle(conf)

    dut = JtagDTM(conf).createInstance(clock, reset, tck, tms, tdi, trstn, tdo, dtm)
    dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    _assert_vhdl_file(output_dir, name)


def test_ecp5_jtagg_client_vhdl_conversion(repo_root: Path):
    name = "ecp5_jtagg_client"
    output_dir = _conversion_output_dir(repo_root, name)

    conf = config.BonfireConfig()
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    dtm = DmiBundle(conf)
    jtagg_i = Ecp5JtaggInputBundle()
    jtagg_o = Ecp5JtaggOutputBundle()

    dut = Ecp5JtaggClient(conf, clock, reset, jtagg_i, jtagg_o, dtm)
    dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = _assert_vhdl_file(output_dir, name)
    _analyze_with_ghdl(output_dir, vhdl_file)


def test_ecp5_jtagg_led_demo_vhdl_conversion(repo_root: Path):
    name = "ecp5_jtagg_led_demo"
    output_dir = _conversion_output_dir(repo_root, name)

    led = Signal(modbv(0)[5:])
    jtagg_i = Ecp5JtaggInputBundle()
    jtagg_o = Ecp5JtaggOutputBundle()
    dut = Ecp5JtaggLedDemo(led, jtagg_i, jtagg_o)
    dut.convert(hdl="VHDL", path=str(output_dir), name=name)

def test_ecp5_jtagg_led_demo_yosys_synthesis(repo_root: Path):
    name = "ecp5_jtagg_led_demo_synth"
    output_dir = _conversion_output_dir(repo_root, name)

    led = Signal(modbv(0)[5:])
    jtagg_i = Ecp5JtaggInputBundle()
    jtagg_o = Ecp5JtaggOutputBundle()
    dut = Ecp5JtaggLedDemo(led, jtagg_i, jtagg_o)
    dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    json_file = _synthesize_ecp5_with_yosys(output_dir, name)
    assert json_file.exists()
    assert json_file.stat().st_size > 0


@pytest.mark.parametrize(
    ("enable_jtag_debug", "debug_jtag_transport", "name"),
    [
        (False, "native", "bonfire_core_soc_top"),
        (True, "native", "bonfire_core_soc_top_jtag"),
        (True, "ecp5_jtagg", "bonfire_core_soc_top_jtagg"),
    ],
)
def test_soc_top_vhdl_conversion(
    enable_jtag_debug: bool,
    debug_jtag_transport: str,
    name: str,
    repo_root: Path,
):
    hex_path = repo_root / "code" / "build" / "soc" / "sim" / "led.hex"
    if not hex_path.is_file():
        pytest.skip(f"SoC HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False
    conf.enableDebugModule = enable_jtag_debug
    soc = BonfireCoreSoC(
        conf,
        hexfile=str(hex_path),
        soc_config={
            "numLeds": 4,
            "enableJtagDebug": enable_jtag_debug,
            "debugJtagTransport": debug_jtag_transport,
        },
    )

    output_dir = _conversion_output_dir(repo_root, name)
    BonfireCoreSoCInstanceGenerator(soc).convert("VHDL", name, str(output_dir), handleWarnings="ignore")

    vhdl_file = _assert_vhdl_file(output_dir, name)
    content = vhdl_file.read_text()
    if debug_jtag_transport == "native" and enable_jtag_debug:
        assert "jtag_tck" in content
        assert "JTAGG" not in content
        _analyze_with_ghdl(output_dir, vhdl_file)
    elif debug_jtag_transport == "ecp5_jtagg":
        assert "jtag_tck" not in content
        assert "u_jtagg: entity work.JTAGG" in content
        assert "JRT1" in content
        assert "JRT2" in content
    else:
        assert "jtag_tck" not in content
        assert "JTAGG" not in content
        _analyze_with_ghdl(output_dir, vhdl_file)


@pytest.mark.parametrize(
    ("enable_jtag_debug", "name"),
    [
        (False, "tb_bonfire_core_soc"),
        (True, "tb_bonfire_core_soc_jtag"),
    ],
)
def test_soc_testbench_vhdl_conversion(enable_jtag_debug: bool, name: str, repo_root: Path):
    hex_path = repo_root / "code" / "build" / "soc" / "sim" / "led.hex"
    if not hex_path.is_file():
        pytest.skip(f"SoC HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False
    conf.enableDebugModule = enable_jtag_debug
    soc = BonfireCoreSoC(
        conf,
        hexfile=str(hex_path),
        soc_config={"numLeds": 4, "enableJtagDebug": enable_jtag_debug},
    )

    output_dir = _conversion_output_dir(repo_root, name)
    BonfireCoreSoCTestbenchGenerator(soc).convert("VHDL", name, str(output_dir), handleWarnings="ignore")

    vhdl_file = _assert_vhdl_file(output_dir, name)
    _analyze_with_ghdl(output_dir, vhdl_file)
