from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest


def test_vhdl_core_fusesoc(repo_root: Path, run_fusesoc: Callable[..., str]):
    testfile = repo_root / "code" / "build" / "core-tests" / "loop.hex"
    if not testfile.is_file():
        pytest.skip(f"Core loop test HEX file not found: {testfile}")

    run_fusesoc(
        "run",
        "--target=sim",
        "bonfire-core",
        f"--testfile={testfile}",
    )
