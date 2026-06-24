from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from rtl import config
from tb.tb_debug_module import BonfireCoreDebugTestbench

from .conftest import SimFailure, run_sim, waveform_config


def _run_debug_module_test(
    sim_env,
    repo_root: Path,
    debug_transport: str,
    waveform_name: str,
    duration: int,
    request: pytest.FixtureRequest,
    configure_debug: Callable[[config.BonfireConfig], None] | None = None,
):
    hex_path = Path(request.config.getoption("--bonfire-hex") or "code/build/debug-tests/debug.hex")
    if not hex_path.is_absolute():
        hex_path = repo_root / hex_path

    if not hex_path.is_file():
        pytest.skip(f"Debug test HEX file not found: {hex_path}")

    verbose = request.config.getoption("verbose") > 0

    conf = config.BonfireConfig()
    if configure_debug is not None:
        configure_debug(conf)
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

    trace, filename = waveform_config(request, sim_env, waveform_name)

    try:
        run_sim(tb, trace=trace, filename=filename, duration=duration, waveforms_dir=sim_env["waveforms_dir"])
    except SimFailure as e:
        pytest.fail(f"MyHDL simulation assertion failed: {e}", pytrace=False)

    if not monitor_result["seen"]:
        pytest.fail("No monitor base write (0x10000000) observed", pytrace=False)
    if monitor_result["value"] != 1:
        pytest.fail("Monitor base indicates failure: 0x{:08x}".format(monitor_result["value"]), pytrace=False)


def test_debug_module(sim_env, repo_root: Path, request: pytest.FixtureRequest):
    _run_debug_module_test(
        sim_env,
        repo_root,
        debug_transport="dmi",
        waveform_name="debug_module",
        duration=30_000,
        request=request,
    )


def test_debug_module_jtag(sim_env, repo_root: Path, request: pytest.FixtureRequest):
    _run_debug_module_test(
        sim_env,
        repo_root,
        debug_transport="jtag",
        waveform_name="debug_module_jtag",
        duration=15_000_000,
        request=request,
    )


def test_debug_module_jtagg(sim_env, repo_root: Path, request: pytest.FixtureRequest):
    _run_debug_module_test(
        sim_env,
        repo_root,
        debug_transport="jtagg",
        waveform_name="debug_module_jtagg",
        duration=15_000_000,
        request=request,
    )


def _run_ndmreset_test(
    sim_env,
    repo_root: Path,
    debug_transport: str,
    enable_ndmreset: bool,
    waveform_name: str,
    duration: int,
    request: pytest.FixtureRequest,
):
    hex_path = Path(request.config.getoption("--bonfire-hex") or "code/build/debug-tests/debug.hex")
    if not hex_path.is_absolute():
        hex_path = repo_root / hex_path

    if not hex_path.is_file():
        pytest.skip(f"Debug test HEX file not found: {hex_path}")

    verbose = request.config.getoption("verbose") > 0

    conf = config.BonfireConfig()
    conf.enableDebugNdmreset = enable_ndmreset
    debug_tb = BonfireCoreDebugTestbench(
        conf,
        hexfile=str(hex_path),
        ramsize=16384,
        verbose=verbose,
        debug_transport=debug_transport,
        stimulus_mode="ndmreset",
    )
    tb = debug_tb.testbench()

    trace, filename = waveform_config(request, sim_env, waveform_name)

    try:
        run_sim(tb, trace=trace, filename=filename, duration=duration, waveforms_dir=sim_env["waveforms_dir"])
    except SimFailure as e:
        pytest.fail(f"MyHDL simulation assertion failed: {e}", pytrace=False)


def test_debug_module_ndmreset_disabled(sim_env, repo_root: Path, request: pytest.FixtureRequest):
    _run_ndmreset_test(
        sim_env,
        repo_root,
        debug_transport="dmi",
        enable_ndmreset=False,
        waveform_name="debug_module_ndmreset_disabled",
        duration=5_000,
        request=request,
    )


def test_debug_module_ndmreset_dmi(sim_env, repo_root: Path, request: pytest.FixtureRequest):
    _run_ndmreset_test(
        sim_env,
        repo_root,
        debug_transport="dmi",
        enable_ndmreset=True,
        waveform_name="debug_module_ndmreset_dmi",
        duration=20_000,
        request=request,
    )


def test_debug_module_ndmreset_jtag(sim_env, repo_root: Path, request: pytest.FixtureRequest):
    _run_ndmreset_test(
        sim_env,
        repo_root,
        debug_transport="jtag",
        enable_ndmreset=True,
        waveform_name="debug_module_ndmreset_jtag",
        duration=6_000_000,
        request=request,
    )
