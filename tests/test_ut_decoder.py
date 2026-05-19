from __future__ import annotations

from tb import tb_decode

from .conftest import run_sim


def test_decoder(sim_env):
    run_sim(tb_decode.tb(), trace=False, waveforms_dir=sim_env["waveforms_dir"])
