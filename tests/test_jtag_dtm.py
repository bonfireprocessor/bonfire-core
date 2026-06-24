"""
JTAG DTM pytest tests.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

import pytest

from tb.tb_ecp5_jtagg import ecp5_jtagg_testbench
from tb.tb_jtag_dtm import jtag_dtm_testbench

from .conftest import run_sim, waveform_config


def test_jtag_dtm(sim_env, request: pytest.FixtureRequest):
    trace, filename = waveform_config(request, sim_env, "jtag_dtm")
    tb = jtag_dtm_testbench()
    run_sim(tb, trace=trace, filename=filename, duration=250_000, waveforms_dir=sim_env["waveforms_dir"])


def test_ecp5_jtagg_transport(sim_env, request: pytest.FixtureRequest):
    trace, filename = waveform_config(request, sim_env, "ecp5_jtagg_transport")
    tb = ecp5_jtagg_testbench()
    run_sim(tb, trace=trace, filename=filename, duration=250_000, waveforms_dir=sim_env["waveforms_dir"])
