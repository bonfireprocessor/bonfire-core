"""
Test VHDL conversion of BonfireCoreTop with and without debug support.
"""

from __future__ import annotations

import shutil
import subprocess
import warnings
from pathlib import Path

import pytest
from myhdl import ResetSignal, Signal, ToVHDLWarning

from rtl import bonfire_core_top, bonfire_interfaces, config
from rtl.debugModule import AbstractDebugTransportBundle

pytestmark = pytest.mark.filterwarnings("ignore::myhdl.ToVHDLWarning")


@pytest.mark.parametrize(
    ("enable_debug", "name"),
    [
        (False, "bonfire_core_top_plain"),
        (True, "bonfire_core_top_debug"),
    ],
)
def test_core_vhdl_conversion(enable_debug: bool, name: str, repo_root: Path):
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

    output_dir = repo_root / "vhdl_gen"
    output_dir.mkdir(exist_ok=True)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = output_dir / f"{name}.vhd"
    assert vhdl_file.exists(), f"VHDL file not created: {vhdl_file}"
    assert vhdl_file.stat().st_size > 0, f"VHDL file is empty: {vhdl_file}"

    content = vhdl_file.read_text()
    assert "entity" in content.lower(), "VHDL file missing 'entity' keyword"
    assert "architecture" in content.lower(), "VHDL file missing 'architecture' keyword"

    ghdl = shutil.which("ghdl")
    if ghdl is None:
        pytest.skip("ghdl not available; skipping VHDL syntax analysis")

    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    assert vhdl_inputs, "No VHDL files found for GHDL analysis"

    result = subprocess.run(
        [ghdl, "-a", "--std=08", *[str(path) for path in vhdl_inputs]],
        check=False,
        cwd=output_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        error_text = (result.stderr or result.stdout).strip()
        pytest.fail(f"ghdl -a failed for {name}\n{error_text}", pytrace=False)
