from __future__ import annotations

import os
from pathlib import Path

import pytest

from tb import tb_core

from .conftest import assert_monitor_pass, run_sim


def _hex_files(repo_root: Path) -> list[str]:
    files = sorted((repo_root / "code" / "build").glob("*.hex"))
    # wb_test is a special case, not runnable with the normal tb.
    files = [p for p in files if p.name != "wb_test.hex"]
    return [str(p.relative_to(repo_root)) for p in files]


def _paths_for_hex(repo_root: Path, hex_path: str) -> tuple[str, str, str]:
    """Compute hex/elf/sig paths.

    The wrapper script can provide:
      BONFIRE_ELF_DIR: directory containing <stem>.elf
      BONFIRE_SIG_DIR: directory for writing <stem>.sig

    All returned paths are relative to repo_root when possible.
    """

    hex_rel = hex_path
    stem = Path(hex_path).stem

    elf_dir = os.environ.get("BONFIRE_ELF_DIR", "").strip()
    sig_dir = os.environ.get("BONFIRE_SIG_DIR", "").strip()

    elf_rel = ""
    if elf_dir:
        elf_path = (Path(elf_dir) / f"{stem}.elf")
        elf_rel = str(elf_path) if elf_path.is_absolute() else str(elf_path)

    sig_rel = ""
    if sig_dir:
        sig_path = (Path(sig_dir) / f"{stem}.sig")
        sig_rel = str(sig_path) if sig_path.is_absolute() else str(sig_path)

    return hex_rel, elf_rel, sig_rel


@pytest.mark.parametrize("hex_path", _hex_files(Path(__file__).resolve().parents[1]))
def test_core(sim_env, capsys: pytest.CaptureFixture[str], request: pytest.FixtureRequest, hex_path: str):
    repo_root = Path(__file__).resolve().parents[1]
    hex_file, elf_file, sig_file = _paths_for_hex(repo_root, hex_path)

    tb = tb_core.tb(hexFile=hex_file, elfFile=elf_file, sigFile=sig_file, ramsize=16384, verbose=False)
    run_sim(tb, trace=False, filename=None, duration=20_000, waveforms_dir=sim_env["waveforms_dir"])

    out = capsys.readouterr().out

    # If capture is disabled (pytest -s), mirror tb_run-style output by printing
    # the captured transcript.
    if request.config.getoption("capture") == "no":
        print(out, end="")

    assert_monitor_pass(out)
