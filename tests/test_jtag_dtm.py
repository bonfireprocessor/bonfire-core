"""
JTAG DTM pytest tests.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

import os
from pathlib import Path

from tb.tb_jtag_dtm import jtag_dtm_testbench

from .conftest import run_sim


def test_jtag_dtm(sim_env):
    vcd = os.environ.get("BONFIRE_JTAG_VCD", "").strip()
    if vcd:
        vcd_path = Path(vcd)
        if not vcd_path.is_absolute():
            vcd_path = sim_env["waveforms_dir"] / vcd_path
        filename = str(vcd_path.resolve())
        trace = True
    else:
        filename = None
        trace = False

    tb = jtag_dtm_testbench()
    run_sim(tb, trace=trace, filename=filename, duration=250_000, waveforms_dir=sim_env["waveforms_dir"])
