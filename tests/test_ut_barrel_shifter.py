from __future__ import annotations

from tb import tb_barrel_shifter

from .conftest import run_sim


def test_barrel_left_shift_comb(sim_env):
    run_sim(tb_barrel_shifter.tb_barrel_left_shift_comb(), waveforms_dir=sim_env["waveforms_dir"])


def test_barrel_left_shift_pipelined(sim_env):
    run_sim(tb_barrel_shifter.tb_barrel_left_shift_pipelined(), trace=False, waveforms_dir=sim_env["waveforms_dir"])


def test_barrel_shift_pipelined(sim_env):
    run_sim(tb_barrel_shifter.tb_barrel_shift_pipelined(), trace=False, waveforms_dir=sim_env["waveforms_dir"])
