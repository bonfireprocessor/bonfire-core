from __future__ import annotations

import warnings

import pytest
from myhdl import ResetSignal, Signal, ToVHDLWarning, always_comb, block, instances, intbv

from rtl import bonfire_core_top, bonfire_interfaces, config
from rtl.debug import DmiBundle
from rtl.divider import DividerBundle
from rtl.multiplier import MultiplierBundle
from tests.conversion.helpers import analyze_with_ghdl, assert_vhdl_file, conversion_output_dir

pytestmark = pytest.mark.filterwarnings("ignore::myhdl.ToVHDLWarning")


@pytest.mark.parametrize(
    ("enable_debug", "pipeline_length", "writeback_bypass", "enable_m", "name"),
    [
        (False, 3, False, False, "bonfire_core_top_plain"),
        (True, 3, False, False, "bonfire_core_top_debug"),
        (False, 4, False, False, "bonfire_core_top_pipeline4"),
        (True, 4, False, False, "bonfire_core_top_pipeline4_debug"),
        (False, 4, True, False, "bonfire_core_top_pipeline4_bypass"),
        (True, 4, True, False, "bonfire_core_top_pipeline4_bypass_debug"),
        (True, 4, True, True, "bonfire_core_top_rv32m"),
    ],
)
def test_core_vhdl_conversion(
    enable_debug: bool,
    pipeline_length: int,
    writeback_bypass: bool,
    enable_m: bool,
    name: str,
    repo_root,
):
    output_dir = conversion_output_dir(repo_root, name)
    conf = config.BonfireConfig()
    conf.enableDebugModule = enable_debug
    conf.pipeline_length = pipeline_length
    conf.writeback_bypass = writeback_bypass
    conf.enable_m_extension = enable_m

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


def test_multiplier_vhdl_conversion(repo_root):
    name = "multiplier"
    output_dir = conversion_output_dir(repo_root, name)

    clock = Signal(bool(0))
    reset = ResetSignal(0, active=1, isasync=False)
    ce_i = Signal(bool(0))
    op1_i = Signal(intbv(0)[32:])
    op2_i = Signal(intbv(0)[32:])
    signed_a_i = Signal(bool(0))
    signed_b_i = Signal(bool(0))
    high_i = Signal(bool(0))
    ce_o = Signal(bool(0))
    result_o = Signal(intbv(0)[32:])

    @block
    def multiplier_wrapper(
        clock, reset, ce_i, op1_i, op2_i, signed_a_i, signed_b_i, high_i,
        ce_o, result_o,
    ):
        multiplier = MultiplierBundle()

        @always_comb
        def connect_inputs():
            multiplier.ce_i.next = ce_i
            multiplier.op1_i.next = op1_i
            multiplier.op2_i.next = op2_i
            multiplier.signed_a_i.next = signed_a_i
            multiplier.signed_b_i.next = signed_b_i
            multiplier.high_i.next = high_i

        @always_comb
        def connect_outputs():
            ce_o.next = multiplier.ce_o
            result_o.next = multiplier.result_o

        multiplier_inst = multiplier.multiplier(clock, reset)
        return instances()

    dut = multiplier_wrapper(
        clock, reset, ce_i, op1_i, op2_i, signed_a_i, signed_b_i, high_i,
        ce_o, result_o,
    )

    dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = assert_vhdl_file(output_dir, name)
    analyze_with_ghdl(output_dir, vhdl_file)
