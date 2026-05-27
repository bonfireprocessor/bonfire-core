from __future__ import annotations

import os
from pathlib import Path

import pytest

from rtl import config
from tb.tb_debug_module import BonfireCoreDebugTestbench

from .conftest import assert_monitor_pass, run_sim


def _opt_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def test_debug_module(sim_env, capsys: pytest.CaptureFixture[str], request: pytest.FixtureRequest, repo_root: Path):
    hex_path = Path(_opt_env("BONFIRE_DEBUG_HEX") or "code/build/debug-tests/debug.hex")
    if not hex_path.is_absolute():
        hex_path = repo_root / hex_path

    if not hex_path.is_file():
        pytest.skip(f"Debug test HEX file not found: {hex_path}")

    verbose = _opt_env("BONFIRE_DEBUG_VERBOSE") in ("1", "true", "yes", "on")
    vcd = _opt_env("BONFIRE_DEBUG_VCD")

    conf = config.BonfireConfig()
    debug_tb = BonfireCoreDebugTestbench(conf, hexfile=str(hex_path), ramsize=16384, verbose=verbose)
    tb = debug_tb.testbench()

    if vcd:
        vcd_path = Path(vcd)
        if not vcd_path.is_absolute():
            vcd_path = sim_env["waveforms_dir"] / vcd_path
        filename = str(vcd_path.resolve())
        trace = True
    else:
        filename = None
        trace = False

    run_sim(tb, trace=trace, filename=filename, duration=20_000, waveforms_dir=sim_env["waveforms_dir"])

    out = capsys.readouterr().out
    if request.config.getoption("capture") == "no":
        print(out, end="")

    assert "[debug-tb]" in out
    assert "halt" in out.lower()
    assert_monitor_pass(out)
