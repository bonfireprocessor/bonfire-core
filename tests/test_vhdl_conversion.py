"""
Test VHDL conversion of selected MyHDL blocks.
"""

from __future__ import annotations

import subprocess
import warnings
from pathlib import Path

import pytest
from myhdl import ResetSignal, Signal, ToVHDLWarning, always_comb, block, instances, intbv

from rtl import bonfire_core_top, bonfire_interfaces, config
from rtl.debugModule import AbstractDebugTransportBundle
from rtl.divider import DividerBundle
from rtl.soc.bonfire_core_soc import BonfireCoreSoC
from rtl.soc.bonfire_core_soc_generator import (
    BonfireCoreSoCInstanceGenerator,
    BonfireCoreSoCTestbenchGenerator,
)
from tests.toolchain import ghdl_command

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
    dtm = AbstractDebugTransportBundle(conf) if enable_debug else None

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


def test_soc_top_vhdl_conversion(repo_root: Path):
    hex_path = repo_root / "code" / "build" / "soc" / "sim" / "led.hex"
    if not hex_path.is_file():
        pytest.skip(f"SoC HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False
    soc = BonfireCoreSoC(conf, hexfile=str(hex_path), soc_config={"numLeds": 4})

    name = "bonfire_core_soc_top"
    output_dir = _conversion_output_dir(repo_root, name)
    BonfireCoreSoCInstanceGenerator(soc).convert("VHDL", name, str(output_dir), handleWarnings="ignore")

    vhdl_file = _assert_vhdl_file(output_dir, name)
    _analyze_with_ghdl(output_dir, vhdl_file)


def test_soc_testbench_vhdl_conversion(repo_root: Path):
    hex_path = repo_root / "code" / "build" / "soc" / "sim" / "led.hex"
    if not hex_path.is_file():
        pytest.skip(f"SoC HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False
    soc = BonfireCoreSoC(conf, hexfile=str(hex_path), soc_config={"numLeds": 4})

    name = "tb_bonfire_core_soc"
    output_dir = _conversion_output_dir(repo_root, name)
    BonfireCoreSoCTestbenchGenerator(soc).convert("VHDL", name, str(output_dir), handleWarnings="ignore")

    vhdl_file = _assert_vhdl_file(output_dir, name)
    _analyze_with_ghdl(output_dir, vhdl_file)
