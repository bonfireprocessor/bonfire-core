from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest


@dataclass
class SimRunResult:
    stdout: str


class SimFailure(AssertionError):
    pass


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def run_sim(inst, *, trace: bool = False, filename: Optional[str] = None, duration: int = 10_000, waveforms_dir: Path) -> SimRunResult:
    """Run a myhdl simulation instance and always attempt cleanup.

    Captures printed output by relying on pytest's capsys in the calling test.
    This function is mainly for consistent setup + converting AssertionError into SimFailure.
    """

    _ensure_dir(waveforms_dir)
    if filename:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

    inst.config_sim(directory=str(waveforms_dir), trace=trace, filename=filename)

    try:
        inst.run_sim(duration=duration)
    except AssertionError as e:
        raise SimFailure(" ".join(str(a) for a in e.args) or "AssertionError") from e
    finally:
        try:
            inst.quit_sim()
        except Exception:
            pass

    return SimRunResult(stdout="")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="function")
def sim_env(tmp_path: Path, repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Prepare environment / working dirs expected by some legacy TBs."""

    monkeypatch.chdir(repo_root)

    # Some TBs convert to VHDL into ./vhdl_gen
    (repo_root / "vhdl_gen").mkdir(exist_ok=True)

    waveforms_dir = repo_root / "waveforms"
    waveforms_dir.mkdir(parents=True, exist_ok=True)

    return {"waveforms_dir": waveforms_dir}


_MONITOR_BASE_RE = re.compile(r"Monitor write: .* 10000000: ([0-9a-fA-F]{8})")


def assert_monitor_pass(stdout: str) -> None:
    """Assert that the last write to monitor base address indicates success."""

    matches = _MONITOR_BASE_RE.findall(stdout)
    if not matches:
        raise AssertionError("No monitor base write (0x10000000) found in output")

    last = matches[-1].lower()
    if last != "00000001":
        raise AssertionError(f"Monitor base indicates failure: 0x{last}")
