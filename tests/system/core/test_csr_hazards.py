from __future__ import annotations

from pathlib import Path

import pytest

from rtl.config import BonfireConfig
from tb import tb_core
from tests.conftest import assert_monitor_pass, run_sim


@pytest.mark.parametrize(
    ("pipeline_length", "writeback_bypass", "jump_bypass"),
    (
        (3, False, True),
        (3, False, False),
        (4, False, True),
        (4, False, False),
        (4, True, True),
        (4, True, False),
    ),
    ids=(
        "3-stage",
        "3-stage-registered-redirect",
        "4-stage",
        "4-stage-registered-redirect",
        "4-stage-bypass",
        "4-stage-bypass-registered-redirect",
    ),
)
@pytest.mark.parametrize(
    "enable_debug_module",
    (False, True),
    ids=("debug-off", "debug-on"),
)
def test_csr_dependencies(
    sim_env,
    capsys: pytest.CaptureFixture[str],
    repo_root: Path,
    pipeline_length: int,
    writeback_bypass: bool,
    jump_bypass: bool,
    enable_debug_module: bool,
):
    config = BonfireConfig()
    config.pipeline_length = pipeline_length
    config.writeback_bypass = writeback_bypass
    config.jump_bypass = jump_bypass
    config.enableDebugModule = enable_debug_module

    testbench = tb_core.tb(
        config=config,
        hexFile=str(repo_root / "code/build/core-tests/csr_hazards.hex"),
        ramsize=16384,
    )
    run_sim(
        testbench,
        duration=20_000,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    assert_monitor_pass(capsys.readouterr().out)
