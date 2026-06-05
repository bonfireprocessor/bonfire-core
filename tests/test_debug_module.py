from __future__ import annotations

import os
from pathlib import Path

import pytest

from rtl import config
from tb.tb_debug_module import BonfireCoreDebugTestbench

from .conftest import SimFailure, assert_monitor_pass, run_sim


def _opt_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def _output_tail(stdout: str, max_lines: int = 80) -> str:
    lines = stdout.splitlines()
    tail = lines[-max_lines:]
    prefix = ""
    if len(lines) > max_lines:
        prefix = f"... output truncated to last {max_lines} of {len(lines)} lines ...\n"
    return prefix + "\n".join(tail)


def _fail_with_output(message: str, stdout: str) -> None:
    pytest.fail(f"{message}\n\nCaptured simulation output:\n{_output_tail(stdout)}", pytrace=False)


def _run_debug_module_test(
    sim_env,
    capsys: pytest.CaptureFixture[str],
    request: pytest.FixtureRequest,
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
    debug_tb = BonfireCoreDebugTestbench(
        conf,
        hexfile=str(hex_path),
        ramsize=16384,
        verbose=verbose,
        debug_transport=debug_transport,
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
        out = capsys.readouterr().out
        if request.config.getoption("capture") == "no":
            print(out, end="")
        _fail_with_output(f"MyHDL simulation assertion failed: {e}", out)

    out = capsys.readouterr().out
    if request.config.getoption("capture") == "no":
        print(out, end="")

    if "[debug-tb]" not in out:
        _fail_with_output("Debug testbench did not print any [debug-tb] markers", out)
    if "halt" not in out.lower():
        _fail_with_output("Debug testbench did not reach a halt-related checkpoint", out)
    try:
        assert_monitor_pass(out)
    except AssertionError as e:
        _fail_with_output(str(e), out)


def test_debug_module(sim_env, capsys: pytest.CaptureFixture[str], request: pytest.FixtureRequest, repo_root: Path):
    _run_debug_module_test(
        sim_env,
        capsys,
        request,
        repo_root,
        debug_transport="dmi",
        vcd_env="BONFIRE_DEBUG_VCD",
        duration=20_000,
    )


def test_debug_module_jtag(sim_env, capsys: pytest.CaptureFixture[str], request: pytest.FixtureRequest, repo_root: Path):
    _run_debug_module_test(
        sim_env,
        capsys,
        request,
        repo_root,
        debug_transport="jtag",
        vcd_env="BONFIRE_DEBUG_JTAG_VCD",
        duration=500_000,
    )
