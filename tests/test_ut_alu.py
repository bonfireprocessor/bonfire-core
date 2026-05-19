from __future__ import annotations

from tb import tb_alu

from .conftest import run_sim


def test_alu_behavioral(sim_env):
    run_sim(tb_alu.tb(c_shifter_mode="behavioral"), trace=False, waveforms_dir=sim_env["waveforms_dir"])


def test_alu_comb(sim_env):
    run_sim(tb_alu.tb(c_shifter_mode="comb"), trace=False, waveforms_dir=sim_env["waveforms_dir"])


def test_alu_pipelined(sim_env):
    run_sim(tb_alu.tb(c_shifter_mode="pipelined"), trace=False, waveforms_dir=sim_env["waveforms_dir"])
