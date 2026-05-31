#!/usr/bin/env python3
from __future__ import print_function

import datetime
import getopt
import sys
from pathlib import Path
from string import Formatter


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rtl.soc.bonfire_core_soc import BonfireCoreSoC
from rtl.soc.bonfire_core_soc_generator import (
    BonfireCoreSoCInstanceGenerator,
    BonfireCoreSoCTestbenchGenerator,
)


CORE_TEMPLATE = """CAPI=2:
name: {vlnv}

filesets:
    rtl:
        file_type: {filetype}
        files: [ {files} ]

    {testbench}

targets:
    default:
        filesets:
        - rtl
        - "simulation_target ? (tb)"


"""

TEST_BENCH_TEMPLATE = """
    tb:
        file_type: {filetype}
        files: [ {files} ]
"""


def param(parameters, key, default):
    return parameters.get(key, default)


def load_generator_input(path):
    import yaml

    with open(path, mode="r") as f:
        return yaml.load(f, Loader=yaml.Loader)


def resolve_input_path(files_root, relative_path):
    return Path(files_root, relative_path).resolve()


def select_myhdl_entity_name(parameters, entity_name, extended_soc):
    if extended_soc:
        return param(parameters, "myhdl_entity_name", "bonfire_core_myhdl_top")
    if "myhdl_entity_name" in parameters:
        print("Warning: 'myhdl_entity_name' parameter is ignored because 'extended_soc' is False")
    return entity_name


def build_soc_config(parameters, entity_name, myhdl_entity_name, extended_soc):
    expose_wishbone_master = param(parameters, "expose_wishbone_master", False)
    if extended_soc:
        expose_wishbone_master = True

    return {
        "bramAdrWidth": param(parameters, "bram_adr_width", 11),
        "LanedMemory": param(parameters, "laned_memory", True),
        "numLeds": param(parameters, "num_leds", 4),
        "ledActiveLow": param(parameters, "led_active_low", True),
        "exposeWishboneMaster": expose_wishbone_master,
        "entity_name": entity_name,
        "gen_core_name": myhdl_entity_name,
        "numGpio": param(parameters, "num_gpio", 8),
        "enableUart1": param(parameters, "enable_uart1", False),
        "enableSPI": param(parameters, "enable_spi", False),
        "numSPI": param(parameters, "num_spi", 1),
        "enableGpio": param(parameters, "enable_gpio", True),
        "debug": param(parameters, "debug", False),
        "instUartOnly": param(parameters, "inst_uart_only", False),
        "uartFifoDepth": param(parameters, "uart_fifo_depth", 6),
    }


def bool_vhdl(value):
    return "true" if bool(value) else "false"


def prepare_template_config(soc_config):
    config = dict(soc_config)
    config["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for key in ("enableUart1", "enableSPI", "enableGpio", "debug", "instUartOnly"):
        config[key] = bool_vhdl(config[key])
    return config


def render_template(template_path, output_path, soc_config):
    template = template_path.read_text()
    render_config = prepare_template_config(soc_config)
    try:
        output_path.write_text(template.format(**render_config))
    except KeyError as e:
        keys_in_template = [fname for _, fname, _, _ in Formatter().parse(template) if fname]
        missing_keys = [key for key in keys_in_template if key not in render_config]
        print("Error: Missing keys in soc_config: {}".format(", ".join(missing_keys or [str(e)])))
        sys.exit(1)
    print("Generated VHDL file: {}".format(output_path))


def cleanup_generated_outputs(gen_path, entity_name, myhdl_entity_name, extended_soc):
    names = {
        "pck_myhdl_011.vhd",
        "{}.vhd".format(myhdl_entity_name),
        "{}.v".format(myhdl_entity_name),
        "{}.core".format(entity_name),
    }
    if extended_soc:
        names.add("{}.vhd".format(entity_name))
        names.add("tb_{}.vhd".format(entity_name))

    for name in names:
        path = gen_path / name
        if path.exists():
            path.unlink()


def write_generated_core(gen_path, vlnv, entity_name, filelist, testbench):
    core_path = gen_path / "{}.core".format(entity_name)
    core_path.write_text(
        CORE_TEMPLATE.format(
            vlnv=vlnv,
            filetype="vhdlSource-2008",
            files=",".join(filelist),
            testbench=testbench,
        )
    )
    print("Generated {}".format(core_path.name))


def generate_from_fusesoc(argv):
    from rtl import config

    if len(argv) < 2:
        return False

    input_path = Path(argv[1])
    print(input_path)
    try:
        generator_input = load_generator_input(input_path)
        print(generator_input)

        files_root = Path(generator_input["files_root"])
        parameters = generator_input["parameters"]
        vlnv = generator_input["vlnv"]
        gen_path = Path.cwd()

        print("Generating into: {}".format(gen_path))

        hdl = param(parameters, "language", "VHDL")
        entity_name = param(parameters, "entity_name", "bonfire_core_soc_top")
        extended_soc = param(parameters, "extended_soc", False)
        myhdl_entity_name = select_myhdl_entity_name(parameters, entity_name, extended_soc)
        soc_config = build_soc_config(parameters, entity_name, myhdl_entity_name, extended_soc)

        cleanup_generated_outputs(gen_path, entity_name, myhdl_entity_name, extended_soc)

        hexfile = param(parameters, "hexfile", "")
        hexfile_path = resolve_input_path(files_root, hexfile)
        print("Checking existence of hex file: {}".format(hexfile_path))
        if not hexfile_path.is_file():
            raise FileNotFoundError("Hex file '{}' does not exist.".format(hexfile_path))

        conf = config.BonfireConfig()
        conf.jump_bypass = param(parameters, "jump_bypass", False)
        print("jump_bypass {}".format(conf.jump_bypass))

        conversion_warnings = param(parameters, "conversion_warnings", "default")
        gentb = param(parameters, "gentb", False)
        print("Gentb {}".format(gentb))

        soc = BonfireCoreSoC(conf, hexfile=str(hexfile_path), soc_config=soc_config)
        if gentb and not extended_soc:
            generator = BonfireCoreSoCTestbenchGenerator(soc)
        else:
            generator = BonfireCoreSoCInstanceGenerator(soc)
        generator.convert(hdl, myhdl_entity_name, str(gen_path), handleWarnings=conversion_warnings)

        filelist = ["pck_myhdl_011.vhd", "{}.vhd".format(myhdl_entity_name)]
        testbench = ""

        if extended_soc:
            templates_dir = files_root / "templates"
            render_template(templates_dir / "soc_top.vhd", gen_path / "{}.vhd".format(entity_name), soc_config)
            filelist.append("{}.vhd".format(entity_name))

            tb_file = "tb_{}.vhd".format(entity_name)
            render_template(templates_dir / "tb_soc.vhd", gen_path / tb_file, soc_config)
            testbench = TEST_BENCH_TEMPLATE.format(filetype="vhdlSource-2008", files=tb_file)

        write_generated_core(gen_path, vlnv, entity_name, filelist, testbench)
        return True
    except FileNotFoundError as err:
        print("Error: {}".format(err))
        return False


def generate_from_cli(argv):
    from rtl import config

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

    name_override = ""
    hdl = "VHDL"
    laned_memory = True
    bram_adr_width = 11
    num_leds = 4
    gen_path = Path("vhdl_gen")
    hexfile = ""
    gentb = False
    expose_wishbone_master = False
    extended_soc = False
    vhdl_template_path = REPO_ROOT / "fusesoc-cores" / "templates" / "soc_top.vhd"

    for option, value in opts:
        print(option, value)
        if option in ("-n", "--name"):
            name_override = value
        elif option == "--hdl":
            hdl = value
        elif option == "--laned_memory":
            laned_memory = value not in ("0", "false", "False")
        elif option == "--bram_adr_width":
            bram_adr_width = int(value, 0)
        elif option == "--num_leds":
            num_leds = int(value, 0)
        elif option == "--path":
            gen_path = Path(value)
        elif option == "--hexfile":
            hexfile = value
        elif option == "--gentb":
            gentb = True
        elif option == "--expose_wishbone_master":
            expose_wishbone_master = True
        elif option == "--extended_soc":
            extended_soc = True
            expose_wishbone_master = True
        elif option == "--vhdl_template_path":
            vhdl_template_path = Path(value)

    if name_override:
        name = name_override
    elif gentb:
        name = "bonfire_core_soc_tb"
    elif extended_soc:
        name = "bonfire_core_myhdl_top"
    else:
        name = "bonfire_core_soc_top"

    soc_config = {
        "bramAdrWidth": bram_adr_width,
        "LanedMemory": laned_memory,
        "numLeds": num_leds,
        "exposeWishboneMaster": expose_wishbone_master,
        "numGpio": 8,
        "enableUart1": True,
        "enableSPI": True,
        "entity_name": "bonfire_core_soc_top",
        "gen_core_name": name,
        "numSPI": 1,
        "enableGpio": True,
        "debug": False,
        "instUartOnly": False,
        "uartFifoDepth": 6,
    }

    conf = config.BonfireConfig()
    conf.jump_bypass = False

    soc = BonfireCoreSoC(conf, hexfile=hexfile, soc_config=soc_config)
    if gentb:
        generator = BonfireCoreSoCTestbenchGenerator(soc)
    else:
        generator = BonfireCoreSoCInstanceGenerator(soc)
    generator.convert(hdl, name, str(gen_path), handleWarnings="ignore")
    if extended_soc:
        render_template(vhdl_template_path, gen_path / "bonfire_core_soc_top.vhd", soc_config)


if __name__ == "__main__":
    if not generate_from_fusesoc(sys.argv):
        generate_from_cli(sys.argv)
