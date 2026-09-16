# Copyright (c) 2026 The Bonfire Project
# License: See LICENSE

"""Compact RV32M integration test across the supported pipeline backends."""

from pathlib import Path

import pytest

from rtl import config
from tb import tb_core
from tests.conftest import assert_monitor_pass, run_sim


@pytest.mark.parametrize(
    ("pipeline_length", "writeback_bypass"),
    [(3, False), (4, False), (4, True)],
    ids=["pipeline3", "pipeline4-interlocked", "pipeline4-bypass"],
)
def test_rv32m_program(
    sim_env, capsys, pipeline_length: int, writeback_bypass: bool,
):
    conf = config.BonfireConfig()
    conf.enable_m_extension = True
    conf.pipeline_length = pipeline_length
    conf.writeback_bypass = writeback_bypass

    hex_file = "code/build/core-tests/rv32m.hex"
    assert Path(hex_file).exists(), "build the RV32M test program first"
    run_sim(
        tb_core.tb(
            config=conf,
            hexFile=hex_file,
            ramsize=16384,
        ),
        trace=False,
        filename="rv32m_pipe{}_bypass{}".format(
            pipeline_length, int(writeback_bypass)),
        duration=80000,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    assert_monitor_pass(capsys.readouterr().out)
