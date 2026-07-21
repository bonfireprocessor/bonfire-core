from __future__ import annotations

import os
from pathlib import Path

import pytest

from rtl import config
from tb import tb_core

from tests.conftest import assert_monitor_pass, run_sim, waveform_config


_PIPELINE_CASES = (
    (3, False, "pipe3"),
    (4, False, "pipe4"),
    (4, True, "pipe4_bypass"),
)
_MONITOR_SUCCESS = "Monitor write:"
_MONITOR_SUCCESS_SUFFIX = "10000000: 00000001 (1)"


def _opt_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def _sim_duration() -> int:
    return int(os.environ.get("BONFIRE_CORE_DURATION", "20000"))


def _hex_files(repo_root: Path, single: str | None = None) -> list[str]:
    """List HEX programs for core integration tests.

    If --bonfire-hex is set, run exactly that one program (single-run mode).
    Otherwise, collect all HEX files from BONFIRE_CORE_HEX_DIR
    (default: code/build/core-tests, excluding wb_test.hex).
    """

    if single:
        p = Path(single)
        # Normalize to a repo-root relative string when possible (helps pytest id output).
        try:
            return [str(p.resolve().relative_to(repo_root))]
        except Exception:
            return [str(p)]

    hex_dir = Path(os.environ.get("BONFIRE_CORE_HEX_DIR", "code/build/core-tests"))
    if not hex_dir.is_absolute():
        hex_dir = repo_root / hex_dir

    files = sorted(hex_dir.glob("*.hex"))
    # wb_test is a special case, not runnable with the normal tb.
    files = [p for p in files if p.name != "wb_test.hex"]
    result = []
    for p in files:
        try:
            result.append(str(p.relative_to(repo_root)))
        except ValueError:
            result.append(str(p))
    return result


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "test_case" not in metafunc.fixturenames:
        return

    repo_root = Path(__file__).resolve().parents[3]
    selected_hex = metafunc.config.getoption("--bonfire-hex")
    cases = []
    ids = []
    for pipeline_length, writeback_bypass, pipeline_id in _PIPELINE_CASES:
        for hex_path in _hex_files(repo_root, selected_hex):
            for enable_debug_module, debug_id in ((False, "debug_off"), (True, "debug_on")):
                cases.append((
                    hex_path,
                    pipeline_length,
                    writeback_bypass,
                    enable_debug_module,
                ))
                ids.append("{}-{}-{}".format(
                    pipeline_id,
                    Path(hex_path).stem,
                    debug_id,
                ))
    metafunc.parametrize("test_case", cases, ids=ids)


def _paths_for_hex(repo_root: Path, request: pytest.FixtureRequest, hex_path: str) -> tuple[str, str, str]:
    """Compute hex/elf/sig paths.

    The test runner can provide:
      BONFIRE_ELF_DIR: directory containing <stem>.elf
      BONFIRE_SIG_DIR: directory for writing <stem>.sig

    All returned paths are relative to repo_root when possible.
    """

    hex_rel = hex_path
    stem = Path(hex_path).stem

    elf_dir = os.environ.get("BONFIRE_ELF_DIR", "").strip()
    sig_dir = os.environ.get("BONFIRE_SIG_DIR", "").strip()

    # Single-run mode can pass exact ELF/SIG paths.
    elf_override = request.config.getoption("--bonfire-elf")
    sig_override = request.config.getoption("--bonfire-sig")

    elf_rel = ""
    if elf_override:
        elf_rel = elf_override
    elif elf_dir:
        elf_path = (Path(elf_dir) / f"{stem}.elf")
        elf_rel = str(elf_path)

    sig_rel = ""
    if sig_override:
        sig_rel = sig_override
    elif sig_dir:
        sig_path = (Path(sig_dir) / f"{stem}.sig")
        sig_rel = str(sig_path)

    return hex_rel, elf_rel, sig_rel


def test_core(
    sim_env,
    capsys: pytest.CaptureFixture[str],
    request: pytest.FixtureRequest,
    test_case: tuple[str, int, bool, bool],
):
    hex_path, pipeline_length, writeback_bypass, enable_debug_module = test_case
    repo_root = Path(__file__).resolve().parents[3]
    hex_file, elf_file, sig_file = _paths_for_hex(repo_root, request, hex_path)

    verbose = _opt_env("BONFIRE_CORE_VERBOSE") in ("1", "true", "yes", "on")
    debug_suffix = "debug_on" if enable_debug_module else "debug_off"
    pipeline_suffix = "pipe{}_{}".format(
        pipeline_length,
        "bypass" if writeback_bypass else "interlocked",
    )
    trace, filename = waveform_config(
        request,
        sim_env,
        "core_{}_{}_{}".format(Path(hex_path).stem, debug_suffix, pipeline_suffix),
    )

    conf = config.BonfireConfig()
    conf.enableDebugModule = enable_debug_module
    conf.pipeline_length = pipeline_length
    conf.writeback_bypass = writeback_bypass
    conf.registered_dbus_feedback = pipeline_length == 5

    tb = tb_core.tb(
        config=conf,
        hexFile=hex_file,
        elfFile=elf_file,
        sigFile=sig_file,
        ramsize=16384,
        verbose=verbose,
    )
    run_sim(
        tb,
        trace=trace,
        filename=filename,
        duration=_sim_duration(),
        waveforms_dir=sim_env["waveforms_dir"],
    )
    out = capsys.readouterr().out

    # If capture is disabled (pytest -s), mirror tb_run-style output by printing
    # the captured transcript.
    if request.config.getoption("capture") == "no":
        print(out, end="")

    # For compliance tests (sig_file set), skip monitor assertion.
    # The compliance suite decides pass/fail via signature comparison.
    if not sig_file:
        assert_monitor_pass(out)
        monitor_lines = [line for line in out.splitlines() if line.startswith(_MONITOR_SUCCESS)]
        assert monitor_lines, "No monitor writes found in output"
        assert monitor_lines[-1].endswith(_MONITOR_SUCCESS_SUFFIX), \
            "Final monitor write must be 0x10000000 <- 1"
