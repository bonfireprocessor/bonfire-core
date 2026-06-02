#!/usr/bin/env python3
from __future__ import print_function

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soc_generator import SoCGenerator
from util.diagnostics import Diagnostics, diagnostics_context


def str_to_bool(value):
    return str(value).lower() not in ("0", "false", "no", "off")


def load_generator_input(path):
    import yaml

    with open(path, mode="r") as f:
        return yaml.load(f, Loader=yaml.Loader)


def generate_from_fusesoc(argv):
    if len(argv) < 2:
        return False

    input_path = Path(argv[1])
    if str(input_path).startswith("-"):
        return False

    try:
        generator_input = load_generator_input(input_path)
    except FileNotFoundError as err:
        Diagnostics().error(err)
        sys.exit(1)

    files_root = Path(generator_input["files_root"])
    parameters = generator_input["parameters"]
    vlnv = generator_input["vlnv"]
    gen_path = Path.cwd()
    diagnostics = Diagnostics(_resolve_quiet_level(parameters))

    with diagnostics_context(diagnostics):
        diagnostics.summary("input: {}".format(input_path))
        diagnostics.detail("vlnv: {}".format(vlnv))
        diagnostics.detail("files root: {}".format(files_root))
        diagnostics.summary("output: {}".format(gen_path))

        try:
            SoCGenerator().generate(parameters, files_root, gen_path, vlnv=vlnv)
        except (FileNotFoundError, ValueError) as err:
            diagnostics.error(err)
            sys.exit(1)

    return True


def generate_from_cli(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", default="")
    parser.add_argument("--hdl", dest="language", default="VHDL")
    parser.add_argument("--gentb", action="store_true")
    parser.add_argument("--laned_memory", type=str_to_bool, default=True)
    parser.add_argument("--path", default="vhdl_gen")
    parser.add_argument("--bram_adr_width", type=lambda value: int(value, 0), default=11)
    parser.add_argument("--num_leds", type=lambda value: int(value, 0), default=4)
    parser.add_argument("--hexfile", default="")
    parser.add_argument("--expose_wishbone_master", action="store_true")
    parser.add_argument("--extended_soc", action="store_true")
    parser.add_argument("--diagnostics-quiet", type=int, default=0)
    parser.add_argument(
        "--vhdl_template_path",
        default=str(REPO_ROOT / "fusesoc-cores" / "templates" / "soc_top.vhd"),
    )
    args = parser.parse_args(argv[1:])

    parameters = {
        "language": args.language,
        "laned_memory": args.laned_memory,
        "bram_adr_width": args.bram_adr_width,
        "num_leds": args.num_leds,
        "enable_uart1": True,
        "enable_spi": True,
        "conversion_warnings": "ignore",
        "diagnostics_quiet": args.diagnostics_quiet,
    }

    if args.hexfile:
        parameters["hexfile"] = args.hexfile
    if args.gentb:
        parameters["gentb"] = True
    if args.expose_wishbone_master:
        parameters["expose_wishbone_master"] = True
    if args.extended_soc:
        parameters["extended_soc"] = True
        parameters["expose_wishbone_master"] = True

    if args.extended_soc:
        parameters["top_entity_name"] = "bonfire_core_soc_top"
        parameters["myhdl_entity_name"] = args.name or "bonfire_core_myhdl_top"
    elif args.name:
        parameters["top_entity_name"] = args.name
    elif args.gentb:
        parameters["top_entity_name"] = "bonfire_core_soc_tb"
    else:
        parameters["top_entity_name"] = "bonfire_core_soc_top"

    if args.hexfile:
        files_root = REPO_ROOT
    else:
        files_root = Path.cwd()

    diagnostics = Diagnostics(_resolve_quiet_level(parameters))
    with diagnostics_context(diagnostics):
        SoCGenerator().generate(
            parameters,
            files_root,
            Path(args.path),
            write_core=False,
            wrapper_template_path=Path(args.vhdl_template_path),
            include_extended_testbench=False,
        )


def _resolve_quiet_level(parameters):
    quiet_level = parameters.get("diagnostics_quiet", 0)
    env_quiet = os.environ.get("BONFIRE_GENERATOR_QUIET")
    if env_quiet is not None:
        quiet_level = env_quiet
    return int(quiet_level)


if __name__ == "__main__":
    if not generate_from_fusesoc(sys.argv):
        generate_from_cli(sys.argv)
