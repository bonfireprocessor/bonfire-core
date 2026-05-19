from __future__ import annotations

from rtl import config
from tb import tb_fetch, tb_simple_pipeline

from .conftest import run_sim


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


def test_fetch_unit(sim_env):
    run_sim(tb_fetch.tb(test_conversion=False), trace=False, filename="tb_fetch", waveforms_dir=sim_env["waveforms_dir"])
