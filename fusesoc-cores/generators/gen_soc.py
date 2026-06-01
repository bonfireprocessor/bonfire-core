#!/usr/bin/env python3
from __future__ import print_function

import getopt
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soc_generator import SoCGenerator


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

    print(input_path)
    try:
        generator_input = load_generator_input(input_path)
        print(generator_input)
    except FileNotFoundError as err:
        print("Error: {}".format(err))
        return False

    files_root = Path(generator_input["files_root"])
    parameters = generator_input["parameters"]
    vlnv = generator_input["vlnv"]
    gen_path = Path.cwd()

    print("Generating into: {}".format(gen_path))

    try:
        SoCGenerator().generate(parameters, files_root, gen_path, vlnv=vlnv)
    except (FileNotFoundError, ValueError) as err:
        print("Error: {}".format(err))
        sys.exit(1)

    return True


def generate_from_cli(argv):
    try:
        opts, _ = getopt.getopt(
            argv[1:],
            "n",
            [
                "hdl=",
                "name=",
                "gentb",
                "laned_memory=",
                "path=",
                "bram_adr_width=",
                "num_leds=",
                "hexfile=",
                "expose_wishbone_master",
                "extended_soc",
                "vhdl_template_path=",
            ],
        )
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    parameters = {
        "language": "VHDL",
        "laned_memory": True,
        "bram_adr_width": 11,
        "num_leds": 4,
        "enable_uart1": True,
        "enable_spi": True,
    }
    gen_path = Path("vhdl_gen")
    gentb = False
    extended_soc = False
    vhdl_template_path = REPO_ROOT / "fusesoc-cores" / "templates" / "soc_top.vhd"
    name_override = ""

    for option, value in opts:
        print(option, value)
        if option in ("-n", "--name"):
            name_override = value
        elif option == "--hdl":
            parameters["language"] = value
        elif option == "--laned_memory":
            parameters["laned_memory"] = value not in ("0", "false", "False")
        elif option == "--bram_adr_width":
            parameters["bram_adr_width"] = int(value, 0)
        elif option == "--num_leds":
            parameters["num_leds"] = int(value, 0)
        elif option == "--path":
            gen_path = Path(value)
        elif option == "--hexfile":
            parameters["hexfile"] = value
        elif option == "--gentb":
            gentb = True
            parameters["gentb"] = True
        elif option == "--expose_wishbone_master":
            parameters["expose_wishbone_master"] = True
        elif option == "--extended_soc":
            extended_soc = True
            parameters["extended_soc"] = True
            parameters["expose_wishbone_master"] = True
        elif option == "--vhdl_template_path":
            vhdl_template_path = Path(value)

    if extended_soc:
        parameters["top_entity_name"] = "bonfire_core_soc_top"
        parameters["myhdl_entity_name"] = name_override or "bonfire_core_myhdl_top"
    elif name_override:
        parameters["top_entity_name"] = name_override
    elif gentb:
        parameters["top_entity_name"] = "bonfire_core_soc_tb"
    else:
        parameters["top_entity_name"] = "bonfire_core_soc_top"

    if parameters.get("hexfile", ""):
        files_root = REPO_ROOT
    else:
        files_root = Path.cwd()

    parameters["conversion_warnings"] = "ignore"
    SoCGenerator().generate(
        parameters,
        files_root,
        gen_path,
        write_core=False,
        wrapper_template_path=vhdl_template_path,
        include_extended_testbench=False,
    )


if __name__ == "__main__":
    if not generate_from_fusesoc(sys.argv):
        generate_from_cli(sys.argv)
