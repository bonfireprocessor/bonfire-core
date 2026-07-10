from __future__ import annotations

import warnings

import pytest
from myhdl import ResetSignal, Signal, ToVHDLWarning, always_comb, block, instances, intbv

from rtl import bonfire_core_top, bonfire_interfaces, config
from rtl.debug import DmiBundle
from rtl.divider import DividerBundle
from tests.conversion.helpers import analyze_with_ghdl, assert_vhdl_file, conversion_output_dir

pytestmark = pytest.mark.filterwarnings("ignore::myhdl.ToVHDLWarning")


@pytest.mark.parametrize(
    ("enable_debug", "name"),
    [
        (False, "bonfire_core_top_plain"),
        (True, "bonfire_core_top_debug"),
    ],
)
def test_core_vhdl_conversion(enable_debug: bool, name: str, repo_root):
    output_dir = conversion_output_dir(repo_root, name)
    conf = config.BonfireConfig()
    conf.enableDebugModule = enable_debug

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    ibus = bonfire_interfaces.DbusBundle(conf, readOnly=True)
    dbus = bonfire_interfaces.DbusBundle(conf)
    control = bonfire_interfaces.ControlBundle(conf)
    debug = bonfire_interfaces.DebugOutputBundle(conf)
    dtm = DmiBundle(conf) if enable_debug else None

    core = bonfire_core_top.BonfireCoreTop(conf)
    dut = core.createInstance(ibus, dbus, control, clock, reset, debug, debugTransportBundle=dtm)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = assert_vhdl_file(output_dir, name)
    analyze_with_ghdl(output_dir, vhdl_file)


def test_divider_vhdl_conversion(repo_root):
    name = "divider"
    output_dir = conversion_output_dir(repo_root, name)

    clk = Signal(bool(0))
    rst = ResetSignal(0, active=1, isasync=False)
    ce_i = Signal(bool(0))
    op1_i = Signal(intbv(0)[32:])
    op2_i = Signal(intbv(0)[32:])
    signed_i = Signal(bool(0))
    rem_i = Signal(bool(0))
    ce_o = Signal(bool(0))
    result_o = Signal(intbv(0)[32:])

    @block
    def divider_wrapper(clk, rst, ce_i, op1_i, op2_i, signed_i, rem_i, ce_o, result_o):
        divider_bundle = DividerBundle(xlen=32)

        @always_comb
        def connect_inputs():
            divider_bundle.ce_i.next = ce_i
            divider_bundle.op1_i.next = op1_i
            divider_bundle.op2_i.next = op2_i
            divider_bundle.signed_i.next = signed_i
            divider_bundle.rem_i.next = rem_i

        @always_comb
        def connect_outputs():
            ce_o.next = divider_bundle.ce_o
            result_o.next = divider_bundle.result_o

        div_inst = divider_bundle.divider(clk, rst)

        return instances()

    inst = divider_wrapper(clk, rst, ce_i, op1_i, op2_i, signed_i, rem_i, ce_o, result_o)
    inst.convert(hdl="VHDL", path=str(output_dir), name=name)

    assert_vhdl_file(output_dir, name)
