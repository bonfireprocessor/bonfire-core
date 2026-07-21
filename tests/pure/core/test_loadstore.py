from __future__ import annotations

import pytest

from rtl import config
from tb import tb_loadstore

from tests.conftest import run_sim


@pytest.mark.parametrize(
    "registered_read_stage,outstanding,registered_dbus_feedback",
    [
        (False, 1, False),
        (False, 2, False),
        (True, 1, False),
        (True, 1, True),
        (True, 2, False),
        (True, 3, False),
    ],
)
def test_loadstore_variants(
    sim_env,
    registered_read_stage: bool,
    outstanding: int,
    registered_dbus_feedback: bool,
):
    conf = config.BonfireConfig()
    conf.registered_read_stage = registered_read_stage
    conf.registered_dbus_feedback = registered_dbus_feedback
    conf.loadstore_outstanding = outstanding

    run_sim(tb_loadstore.tb(config=conf, test_conversion=False), trace=False, waveforms_dir=sim_env["waveforms_dir"])
