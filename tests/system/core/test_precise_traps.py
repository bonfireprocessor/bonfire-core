from __future__ import annotations

from pathlib import Path

import pytest

from rtl.config import BonfireConfig
from rtl.static_data_access import DataAccessFaultMode, DataAccessRegion
from rtl.uncore.dbus_interconnect import AdrMask
from tb import tb_core
from tests.conftest import assert_monitor_pass, run_sim


@pytest.mark.parametrize(
    (
        "pipeline_length",
        "writeback_bypass",
        "jump_bypass",
        "enable_debug_module",
    ),
    (
        (3, False, True, False),
        (3, False, True, True),
        (4, False, True, False),
        (4, False, True, True),
        (4, True, True, False),
        (4, True, True, True),
        (4, True, False, False),
        (4, True, False, True),
    ),
    ids=(
        "3-stage-debug-off",
        "3-stage-debug-on",
        "4-stage-debug-off",
        "4-stage-debug-on",
        "4-stage-bypass-debug-off",
        "4-stage-bypass-debug-on",
        "4-stage-bypass-registered-redirect-debug-off",
        "4-stage-bypass-registered-redirect-debug-on",
    ),
)
def test_precise_machine_traps(
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
        hexFile=str(repo_root / "code/build/core-tests/precise_traps.hex"),
        ramsize=16384,
        dbus_error_address=0x20000000,
    )
    run_sim(
        testbench,
        duration=50_000,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    assert_monitor_pass(capsys.readouterr().out)


def test_precise_machine_traps_with_static_data_access_map(
    sim_env,
    capsys: pytest.CaptureFixture[str],
    repo_root: Path,
):
    config = BonfireConfig()
    config.pipeline_length = 4
    config.writeback_bypass = True
    config.jump_bypass = False
    config.data_access_fault_mode = DataAccessFaultMode.STATIC_MAP
    config.data_access_regions = (
        DataAccessRegion.from_adrmask(AdrMask(32, 16, 0)),
        DataAccessRegion.from_adrmask(AdrMask(32, 28, 0x1)),
    )

    testbench = tb_core.tb(
        config=config,
        hexFile=str(repo_root / "code/build/core-tests/precise_traps.hex"),
        ramsize=16384,
    )
    run_sim(
        testbench,
        duration=50_000,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    assert_monitor_pass(capsys.readouterr().out)
