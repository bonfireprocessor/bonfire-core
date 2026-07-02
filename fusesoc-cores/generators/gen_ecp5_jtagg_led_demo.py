#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from myhdl import Signal, ToVHDLWarning, modbv

from rtl.debug.ecp5_jtagg_client import Ecp5JtaggInputBundle, Ecp5JtaggOutputBundle
from rtl.debug.ecp5_jtagg_led_demo import Ecp5JtaggLedDemo
from util.diagnostics import Diagnostics, diagnostics_context


CORE_TEMPLATE = """CAPI=2:
name: {vlnv}

filesets:
    rtl:
        file_type: vhdlSource-2008
        files: [ pck_myhdl_011.vhd,ecp5_jtagg_led_demo.vhd ]

targets:
    default:
        filesets:
        - rtl

"""


def _load_generator_input(path: Path):
    import yaml

    with path.open(mode="r", encoding="utf-8") as f:
        return yaml.load(f, Loader=yaml.Loader)


def _resolve_quiet_level(parameters):
    quiet_level = parameters.get("diagnostics_quiet", 0)
    env_quiet = os.environ.get("BONFIRE_GENERATOR_QUIET")
    if env_quiet is not None:
        quiet_level = env_quiet
    return int(quiet_level)


def _generate_vhdl(gen_path: Path, num_leds: int, conversion_warnings: str) -> None:
    import warnings

    led = Signal(modbv(0)[num_leds:])
    jtagg_i = Ecp5JtaggInputBundle()
    jtagg_o = Ecp5JtaggOutputBundle()
    dut = Ecp5JtaggLedDemo(led, jtagg_i, jtagg_o)

    with warnings.catch_warnings():
        warnings.filterwarnings(conversion_warnings, category=ToVHDLWarning)
        dut.convert(
            hdl="VHDL",
            std_logic_ports=True,
            initial_values=True,
            path=str(gen_path),
            name="ecp5_jtagg_led_demo",
        )


def _write_core(gen_path: Path, vlnv: str) -> None:
    core_path = gen_path / "ecp5_jtagg_led_demo.core"
    core_path.write_text(CORE_TEMPLATE.format(vlnv=vlnv), encoding="utf-8")


def generate_from_fusesoc(argv: list[str]) -> bool:
    if len(argv) < 2:
        return False

    input_path = Path(argv[1])
    if str(input_path).startswith("-"):
        return False

    generator_input = _load_generator_input(input_path)
    parameters = generator_input["parameters"]
    vlnv = generator_input["vlnv"]
    gen_path = Path.cwd()
    diagnostics = Diagnostics(_resolve_quiet_level(parameters))

    with diagnostics_context(diagnostics):
        diagnostics.summary("input: {}".format(input_path))
        diagnostics.summary("output: {}".format(gen_path))
        diagnostics.summary("vlnv: {}".format(vlnv))

        num_leds = int(parameters.get("num_leds", 5))
        conversion_warnings = parameters.get("conversion_warnings", "ignore")
        diagnostics.summary("num_leds: {}".format(num_leds))

        _generate_vhdl(gen_path, num_leds, conversion_warnings)
        _write_core(gen_path, vlnv)

    return True


if __name__ == "__main__":
    if not generate_from_fusesoc(sys.argv):
        raise SystemExit("This generator must be invoked by FuseSoC.")
