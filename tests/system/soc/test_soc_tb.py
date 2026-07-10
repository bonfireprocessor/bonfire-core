from __future__ import annotations

from pathlib import Path

import pytest
from myhdl import ResetSignal, Signal, Simulation, StopSimulation, delay, instance

from rtl import bonfire_interfaces, config
from rtl.soc.bonfire_core_soc import BonfireCoreSoC
from rtl.uncore.dbus_interconnect import DbusInterConnects
from tb.soc.bonfire_core_soc_tb import BonfireCoreSoCTestbench

from tests.conftest import run_sim, waveform_config


def test_soc_native_io_address_map():
    soc = BonfireCoreSoC(config.BonfireConfig())

    assert soc.ledMask.mapped_range() == (0x80000000, 0x8000FFFF)
    assert soc.uartMask.mapped_range() == (0x80010000, 0x8001FFFF)
    assert not DbusInterConnects._adrmasks_overlap(soc.ledMask, soc.uartMask, 32)

    unmapped_address = 0x80020000
    for address_mask in (soc.ledMask, soc.uartMask):
        assert unmapped_address & address_mask.address_mask() != address_mask.base_address()


def test_wishbone_dummy_acks_writes_and_returns_fixed_signature():
    soc = BonfireCoreSoC(config.BonfireConfig())
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    wishbone = bonfire_interfaces.Wishbone_master_bundle()
    dut = soc.wishbone_dummy(clock, reset, wishbone)

    @instance
    def stimulus():
        wishbone.wbm_cyc_o.next = True
        wishbone.wbm_stb_o.next = True
        wishbone.wbm_we_o.next = True
        wishbone.wbm_db_o.next = 0xA5A55A5A
        yield delay(1)

        assert wishbone.wbm_ack_i
        assert int(wishbone.wbm_db_i) == soc.WISHBONE_DUMMY_SIGNATURE

        wishbone.wbm_we_o.next = False
        wishbone.wbm_adr_o.next = 0x1234567
        yield delay(1)

        assert wishbone.wbm_ack_i
        assert int(wishbone.wbm_db_i) == soc.WISHBONE_DUMMY_SIGNATURE
        raise StopSimulation

    Simulation(dut, stimulus).run()


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


def test_myhdl_soc_uart_echo(sim_env, request: pytest.FixtureRequest, repo_root: Path):
    hex_path = repo_root / "code" / "build" / "soc" / "sim" / "uart_echo.hex"
    if not hex_path.is_file():
        pytest.skip(f"SoC UART echo HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False
    soc = BonfireCoreSoC(conf, hexfile=str(hex_path), soc_config={
        "numLeds": 4,
        "ledActiveLow": False,
        "uartLoopback": True,
        "uartCapture": True,
        "uartCaptureBitTime": 80,
        "uartCaptureExpected": (0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x1A),
        "uartCaptureRequireLedSuccess": True,
    })
    tb = BonfireCoreSoCTestbench(soc).testbench()
    trace, filename = waveform_config(request, sim_env, "soc_uart_echo")

    run_sim(
        tb,
        trace=trace,
        filename=filename,
        duration=50_000,
        waveforms_dir=sim_env["waveforms_dir"],
    )
