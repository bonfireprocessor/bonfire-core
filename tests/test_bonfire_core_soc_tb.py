from __future__ import annotations

from pathlib import Path

import pytest

from rtl import config
from rtl.soc.bonfire_core_soc import BonfireCoreSoC
from tb.soc.bonfire_core_soc_tb import BonfireCoreSoCTestbench

from .conftest import run_sim, waveform_config


@pytest.mark.parametrize(
    "hex_default,expose_wishbone",
    [
        ("code/build/soc/sim/led.hex", False),
        ("code/build/soc/sim/wishbone.hex", True),
    ],
    ids=["led", "wishbone"],
)
def test_myhdl_soc(
    sim_env,
    capsys: pytest.CaptureFixture[str],
    request: pytest.FixtureRequest,
    repo_root: Path,
    hex_default: str,
    expose_wishbone: bool,
):
    hex_path = Path(request.config.getoption("--bonfire-hex") or hex_default)
    if not hex_path.is_absolute():
        hex_path = repo_root / hex_path

    if not hex_path.is_file():
        pytest.skip(f"SoC HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False

    soc = BonfireCoreSoC(conf, hexfile=str(hex_path), soc_config={
        "numLeds": 4,
        "exposeWishboneMaster": expose_wishbone,
    })
    soc_tb = BonfireCoreSoCTestbench(soc)
    tb = soc_tb.testbench()

    trace, filename = waveform_config(request, sim_env, "soc_{}".format("wishbone" if expose_wishbone else "led"))

    duration = 80_000 if expose_wishbone else 20_000
    run_sim(tb, trace=trace, filename=filename, duration=duration, waveforms_dir=sim_env["waveforms_dir"])

    out = capsys.readouterr().out
    if request.config.getoption("capture") == "no":
        print(out, end="")

    assert "LED status" in out
    assert "led status" in out.lower()
    assert ": f" in out.lower()
    if expose_wishbone:
        assert "wb cyc. trm." in out.lower()
