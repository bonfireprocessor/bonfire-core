from __future__ import annotations

import os
from pathlib import Path

import pytest

from rtl import config
from soc.bonfire_core_soc_tb import BonfireCoreSoCTestbench

from .conftest import run_sim


def _opt_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


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
    hex_path = Path(_opt_env("BONFIRE_SOC_HEX") or hex_default)
    if not hex_path.is_absolute():
        hex_path = repo_root / hex_path

    if not hex_path.is_file():
        pytest.skip(f"SoC HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False

    soc_tb = BonfireCoreSoCTestbench(conf, hexfile=str(hex_path), soc_config={"numLeds": 4}, expose_wishbone=expose_wishbone)
    tb = soc_tb.testbench()

    vcd = _opt_env("BONFIRE_SOC_VCD")
    if vcd:
        vcd_path = Path(vcd)
        if not vcd_path.is_absolute():
            vcd_path = sim_env["waveforms_dir"] / vcd_path
        filename = str(vcd_path.resolve())
        trace = True
    else:
        filename = None
        trace = False

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
