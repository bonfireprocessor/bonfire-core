from __future__ import annotations

import os
from pathlib import Path

import pytest

from rtl import config
from tb.tb_debug_module import BonfireCoreDebugTestbench

from .conftest import SimFailure, run_sim


def _opt_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def _run_debug_module_test(
    sim_env,
    repo_root: Path,
    debug_transport: str,
    vcd_env: str,
    duration: int,
):
    hex_path = Path(_opt_env("BONFIRE_DEBUG_HEX") or "code/build/debug-tests/debug.hex")
    if not hex_path.is_absolute():
        hex_path = repo_root / hex_path

    if not hex_path.is_file():
        pytest.skip(f"Debug test HEX file not found: {hex_path}")

    verbose = _opt_env("BONFIRE_DEBUG_VERBOSE") in ("1", "true", "yes", "on")
    vcd = _opt_env(vcd_env)

    conf = config.BonfireConfig()
    monitor_result = {"seen": False, "time": None, "address": None, "value": None}
    debug_tb = BonfireCoreDebugTestbench(
        conf,
        hexfile=str(hex_path),
        ramsize=16384,
        verbose=verbose,
        debug_transport=debug_transport,
        monitor_result=monitor_result,
    )
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

    try:
        run_sim(tb, trace=trace, filename=filename, duration=duration, waveforms_dir=sim_env["waveforms_dir"])
    except SimFailure as e:
        pytest.fail(f"MyHDL simulation assertion failed: {e}", pytrace=False)

    if not monitor_result["seen"]:
        pytest.fail("No monitor base write (0x10000000) observed", pytrace=False)
    if monitor_result["value"] != 1:
        pytest.fail("Monitor base indicates failure: 0x{:08x}".format(monitor_result["value"]), pytrace=False)


def test_debug_module(sim_env, repo_root: Path):
    _run_debug_module_test(
        sim_env,
        repo_root,
        debug_transport="dmi",
        vcd_env="BONFIRE_DEBUG_VCD",
        duration=20_000,
    )


def test_debug_module_jtag(sim_env, repo_root: Path):
    _run_debug_module_test(
        sim_env,
        repo_root,
        debug_transport="jtag",
        vcd_env="BONFIRE_DEBUG_JTAG_VCD",
        duration=15_000_000,
    )
