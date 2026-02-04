from __future__ import annotations

from tb import tb_regfile

from .conftest import run_sim


def test_regfile(sim_env):
    run_sim(tb_regfile.tb(), trace=False, waveforms_dir=sim_env["waveforms_dir"])
