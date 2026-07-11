from __future__ import annotations

import warnings
from pathlib import Path

from myhdl import ToVHDLWarning

from tests.dbus_interconnect.test_myhdl import (
    dbus_interconnect_master8_vhdl_tb,
    dbus_interconnect_signal_array_vhdl_tb,
)


def _convert_testbench(dut, output_dir: Path, name: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = output_dir / f"{name}.vhd"
    assert vhdl_file.exists()
    assert vhdl_file.stat().st_size > 0

    package_files = sorted(output_dir.glob("pck_myhdl_*.vhd"))
    assert package_files
    assert all(path.stat().st_size > 0 for path in package_files)


def test_dbus_interconnect_signal_array_vhdl_conversion(repo_root):
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_signal_array_tb"
    _convert_testbench(
        dbus_interconnect_signal_array_vhdl_tb(),
        output_dir,
        "dbus_interconnect_signal_array_tb",
    )


def test_dbus_interconnect_master8_vhdl_conversion(repo_root):
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_master8_tb"
    _convert_testbench(
        dbus_interconnect_master8_vhdl_tb(),
        output_dir,
        "dbus_interconnect_master8_tb",
    )
