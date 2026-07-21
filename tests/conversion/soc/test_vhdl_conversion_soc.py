from __future__ import annotations

import os

import pytest

from rtl import config
from rtl.soc.bonfire_core_soc import BonfireCoreSoC
from rtl.soc.bonfire_core_soc_generator import (
    BonfireCoreSoCInstanceGenerator,
    BonfireCoreSoCTestbenchGenerator,
)
from tests.conversion.helpers import analyze_with_ghdl, assert_vhdl_file, conversion_output_dir

pytestmark = pytest.mark.filterwarnings("ignore::myhdl.ToVHDLWarning")


def _soc_conversion_hex_path(repo_root, tmp_path):
    hex_override = os.environ.get("BONFIRE_SOC_CONVERSION_HEX", "").strip()
    if hex_override:
        return repo_root / hex_override

    hex_path = tmp_path / "dummy.hex"
    hex_path.write_text("0000006f\n", encoding="utf-8")
    return hex_path


@pytest.mark.parametrize(
    ("enable_jtag_debug", "debug_jtag_transport", "name"),
    [
        (False, "native", "bonfire_core_soc_top"),
        (True, "native", "bonfire_core_soc_top_jtag"),
        (True, "ecp5_jtagg", "bonfire_core_soc_top_jtagg"),
    ],
)
def test_soc_top_vhdl_conversion(
    enable_jtag_debug: bool,
    debug_jtag_transport: str,
    name: str,
    repo_root,
    tmp_path,
):
    hex_path = _soc_conversion_hex_path(repo_root, tmp_path)
    if not hex_path.is_file():
        pytest.skip(f"SoC HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False
    conf.enableDebugModule = enable_jtag_debug
    soc = BonfireCoreSoC(
        conf,
        hexfile=str(hex_path),
        soc_config={
            "numLeds": 4,
            "registerWishboneDbus": True,
            "enableJtagDebug": enable_jtag_debug,
            "debugJtagTransport": debug_jtag_transport,
        },
    )

    output_dir = conversion_output_dir(repo_root, name)
    BonfireCoreSoCInstanceGenerator(soc).convert("VHDL", name, str(output_dir), handleWarnings="ignore")

    vhdl_file = assert_vhdl_file(output_dir, name)
    content = vhdl_file.read_text()
    if debug_jtag_transport == "native" and enable_jtag_debug:
        assert "jtag_tck" in content
        assert "JTAGG" not in content
        analyze_with_ghdl(output_dir, vhdl_file)
    elif debug_jtag_transport == "ecp5_jtagg":
        assert "jtag_tck" not in content
        assert "jtagg_i_jtck" in content
        assert "jtagg_i_jrt1" in content
        assert "jtagg_i_jrt2" in content
        assert "jtagg_o_jtdo1" in content
        assert "jtagg_o_jtdo2" in content
        assert "JTAGG" not in content
        analyze_with_ghdl(output_dir, vhdl_file)
    else:
        assert "jtag_tck" not in content
        assert "JTAGG" not in content
        analyze_with_ghdl(output_dir, vhdl_file)


@pytest.mark.parametrize(
    ("enable_jtag_debug", "name"),
    [
        (False, "tb_bonfire_core_soc"),
        (True, "tb_bonfire_core_soc_jtag"),
    ],
)
def test_soc_testbench_vhdl_conversion(enable_jtag_debug: bool, name: str, repo_root, tmp_path):
    hex_path = _soc_conversion_hex_path(repo_root, tmp_path)
    if not hex_path.is_file():
        pytest.skip(f"SoC HEX file not found: {hex_path}")

    conf = config.BonfireConfig()
    conf.jump_bypass = False
    conf.enableDebugModule = enable_jtag_debug
    soc = BonfireCoreSoC(
        conf,
        hexfile=str(hex_path),
        soc_config={"numLeds": 4, "enableJtagDebug": enable_jtag_debug},
    )

    output_dir = conversion_output_dir(repo_root, name)
    BonfireCoreSoCTestbenchGenerator(soc).convert("VHDL", name, str(output_dir), handleWarnings="ignore")

    vhdl_file = assert_vhdl_file(output_dir, name)
    analyze_with_ghdl(output_dir, vhdl_file)
