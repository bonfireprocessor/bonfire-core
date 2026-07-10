from __future__ import annotations

import pytest
from myhdl import ResetSignal, Signal

from rtl import config
from rtl.debug import DmiBundle, Ecp5JtaggClient, Ecp5JtaggInputBundle, Ecp5JtaggOutputBundle
from rtl.debug.jtag_dtm import JtagDTM
from tests.conversion.helpers import analyze_with_ghdl, assert_vhdl_file, conversion_output_dir

pytestmark = pytest.mark.filterwarnings("ignore::myhdl.ToVHDLWarning")


def test_jtag_dtm_vhdl_conversion(repo_root):
    name = "jtag_dtm"
    output_dir = conversion_output_dir(repo_root, name)

    conf = config.BonfireConfig()
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    tck = Signal(bool(0))
    trstn = Signal(bool(1))
    tms = Signal(bool(0))
    tdi = Signal(bool(0))
    tdo = Signal(bool(0))
    dtm = DmiBundle(conf)

    dut = JtagDTM(conf).createInstance(clock, reset, tck, tms, tdi, trstn, tdo, dtm)
    dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    assert_vhdl_file(output_dir, name)


def test_ecp5_jtagg_client_vhdl_conversion(repo_root):
    name = "ecp5_jtagg_client"
    output_dir = conversion_output_dir(repo_root, name)

    conf = config.BonfireConfig()
    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    dtm = DmiBundle(conf)
    jtagg_i = Ecp5JtaggInputBundle()
    jtagg_o = Ecp5JtaggOutputBundle()

    dut = Ecp5JtaggClient(conf, clock, reset, jtagg_i, jtagg_o, dtm)
    dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = assert_vhdl_file(output_dir, name)
    analyze_with_ghdl(output_dir, vhdl_file)
