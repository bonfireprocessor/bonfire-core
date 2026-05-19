from __future__ import annotations

import pytest

from rtl import config
from tb import tb_loadstore

from .conftest import run_sim


@pytest.mark.parametrize(
    "registered_read_stage,outstanding",
    [
        (False, 1),
        (False, 2),
        (True, 1),
        (True, 2),
        (True, 3),
    ],
)
def test_loadstore_variants(sim_env, registered_read_stage: bool, outstanding: int):
    conf = config.BonfireConfig()
    conf.registered_read_stage = registered_read_stage
    conf.loadstore_outstanding = outstanding

    run_sim(tb_loadstore.tb(config=conf, test_conversion=False), trace=False, waveforms_dir=sim_env["waveforms_dir"])
