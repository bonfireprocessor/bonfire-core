from __future__ import annotations

import pytest

from rtl import config
from tb import tb_fetch, tb_simple_pipeline

from tests.conftest import run_sim


def test_simple_pipeline_comb_shifter(sim_env):
    conf = config.BonfireConfig()
    conf.shifter_mode = "comb"
    run_sim(
        tb_simple_pipeline.tb(config=conf),
        trace=False,
        filename="tb_simple_pipeline_comb_shift",
        waveforms_dir=sim_env["waveforms_dir"],
    )


def test_simple_pipeline_staged(sim_env):
    run_sim(tb_simple_pipeline.tb(test_conversion=False), trace=False, filename="tb_simple_pipeline", waveforms_dir=sim_env["waveforms_dir"])


@pytest.mark.parametrize(
    "writeback_bypass",
    [False, True],
)
def test_pipelined_backend(sim_env, writeback_bypass):
    conf = config.BonfireConfig()
    conf.pipeline_length = 4
    conf.writeback_bypass = writeback_bypass
    run_sim(
        tb_simple_pipeline.tb(config=conf, test_conversion=False),
        trace=False,
        filename="tb_pipeline_4_bypass_{}".format(int(writeback_bypass)),
        waveforms_dir=sim_env["waveforms_dir"],
    )


def test_fetch_unit(sim_env):
    run_sim(tb_fetch.tb(test_conversion=False), trace=False, filename="tb_fetch", waveforms_dir=sim_env["waveforms_dir"])
