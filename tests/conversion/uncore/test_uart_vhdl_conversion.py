from __future__ import annotations

import warnings

from myhdl import ResetSignal, Signal, ToVHDLWarning

from rtl import config
from rtl.bonfire_interfaces import DbusBundle
from rtl.uncore.uart import BonfireUart


def test_uart_vhdl_conversion(repo_root):
    output_dir = repo_root / "vhdl_gen" / "uart"
    output_dir.mkdir(parents=True, exist_ok=True)

    conf = config.BonfireConfig()
    dbus = DbusBundle(conf)
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    tx = Signal(bool(1))
    rx = Signal(bool(1))
    irq = Signal(bool(0))
    enabled = Signal(bool(0))

    uart = BonfireUart(fifo_bits=5)
    dut = uart.createInstance(dbus, clock, reset, tx, rx, irq, enabled)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name="bonfire_uart")

    vhdl_file = output_dir / "bonfire_uart.vhd"
    assert vhdl_file.exists()
    assert vhdl_file.stat().st_size > 0
