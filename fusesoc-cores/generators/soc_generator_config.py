from __future__ import print_function

from dataclasses import dataclass
from pathlib import Path

from util.diagnostics import get_diagnostics


class GenerationKind:
    BASIC_SOC_TOP = "basic_soc_top"
    BASIC_SOC_TESTBENCH = "basic_soc_testbench"
    EXTENDED_SOC_TOP = "extended_soc_top"

    ALL = {
        BASIC_SOC_TOP,
        BASIC_SOC_TESTBENCH,
        EXTENDED_SOC_TOP,
    }


@dataclass(frozen=True)
class GeneratedNames:
    top_entity_name: str
    myhdl_entity_name: str

    @property
    def extended_testbench_file(self):
        return "tb_{}.vhd".format(self.top_entity_name)


@dataclass(frozen=True)
class SoCGenerationConfig:
    hdl: str
    generation_kind: str
    names: GeneratedNames
    soc_config: dict
    hexfile: str
    conversion_warnings: str
    diagnostics_quiet: int

    @property
    def is_extended(self):
        return self.generation_kind == GenerationKind.EXTENDED_SOC_TOP

    @property
    def is_testbench(self):
        return self.generation_kind == GenerationKind.BASIC_SOC_TESTBENCH


def param(parameters, key, default):
    return parameters.get(key, default)


def snake_to_lower_camel(name):
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def is_extended_generation(generation_kind):
    return generation_kind == GenerationKind.EXTENDED_SOC_TOP


def is_testbench_generation(generation_kind):
    return generation_kind == GenerationKind.BASIC_SOC_TESTBENCH


class SoCGenerationConfigBuilder:
    CONTROL_PARAMETERS = {
        "language",
        "generation_kind",
        "gentb",
        "extended_soc",
        "conversion_warnings",
        "hexfile",
        "jump_bypass",
        "top_entity_name",
        "myhdl_entity_name",
        "entity_name",
        "diagnostics_quiet",
    }

    SOC_PARAMETER_DEFAULTS = {
        "bram_adr_width": 11,
        "laned_memory": True,
        "num_leds": 4,
        "led_active_low": True,
        "expose_wishbone_master": False,
        "num_gpio": 8,
        "enable_uart1": False,
        "enable_spi": False,
        "num_spi": 1,
        "enable_gpio": True,
        "debug": False,
        "enable_jtag_debug": False,
        "enable_debug_ndmreset": False,
        "inst_uart_only": False,
        "uart_fifo_depth": 6,
    }

    ALLOWED_PARAMETERS = CONTROL_PARAMETERS | set(SOC_PARAMETER_DEFAULTS)

    def build(self, parameters, files_root):
        self._validate_parameters(parameters)
        hdl = param(parameters, "language", "VHDL")
        generation_kind = self._select_generation_kind(parameters)
        names = self._build_generated_names(parameters, generation_kind)
        soc_config = self._build_soc_config(parameters, names, generation_kind)
        hexfile = self._resolve_hexfile(parameters, files_root)
        conversion_warnings = param(parameters, "conversion_warnings", "default")
        diagnostics_quiet = int(param(parameters, "diagnostics_quiet", 0))

        return SoCGenerationConfig(
            hdl=hdl,
            generation_kind=generation_kind,
            names=names,
            soc_config=soc_config,
            hexfile=hexfile,
            conversion_warnings=conversion_warnings,
            diagnostics_quiet=diagnostics_quiet,
        )

    def _validate_parameters(self, parameters):
        unknown = sorted(set(parameters) - self.ALLOWED_PARAMETERS)
        if unknown:
            raise ValueError(
                "Unknown generator parameter(s): {}".format(", ".join(unknown))
            )

    def _select_generation_kind(self, parameters):
        generation_kind = param(parameters, "generation_kind", None)
        if generation_kind:
            if generation_kind not in GenerationKind.ALL:
                raise ValueError(
                    "Invalid generation_kind '{}'. Expected one of: {}".format(
                        generation_kind,
                        ", ".join(sorted(GenerationKind.ALL)),
                    )
                )
            return generation_kind

        gentb = param(parameters, "gentb", False)
        extended_soc = param(parameters, "extended_soc", False)
        if gentb and not extended_soc:
            return GenerationKind.BASIC_SOC_TESTBENCH
        if extended_soc:
            return GenerationKind.EXTENDED_SOC_TOP
        return GenerationKind.BASIC_SOC_TOP

    def _build_generated_names(self, parameters, generation_kind):
        if is_testbench_generation(generation_kind):
            default_top_entity_name = "tb_bonfire_core_soc"
        else:
            default_top_entity_name = "bonfire_core_soc_top"

        top_entity_name = param(parameters, "top_entity_name", None)
        if top_entity_name is None:
            top_entity_name = param(parameters, "entity_name", default_top_entity_name)
            if "entity_name" in parameters:
                get_diagnostics().warning(
                    "'entity_name' parameter is deprecated; use 'top_entity_name'"
                )
        elif "entity_name" in parameters and parameters["entity_name"] != top_entity_name:
            raise ValueError(
                "'entity_name' and 'top_entity_name' parameters are both set with different values"
            )

        if is_extended_generation(generation_kind):
            myhdl_entity_name = param(parameters, "myhdl_entity_name", "bonfire_core_myhdl_top")
            return GeneratedNames(
                top_entity_name=top_entity_name,
                myhdl_entity_name=myhdl_entity_name,
            )

        myhdl_entity_name = param(parameters, "myhdl_entity_name", top_entity_name)
        if myhdl_entity_name != top_entity_name:
            raise ValueError(
                "'top_entity_name' and 'myhdl_entity_name' must match for non-extended SoC generation"
            )
        return GeneratedNames(
            top_entity_name=top_entity_name,
            myhdl_entity_name=myhdl_entity_name,
        )

    def _build_soc_config(self, parameters, names, generation_kind):
        soc_config = self._build_lower_camel_config(parameters, self.SOC_PARAMETER_DEFAULTS)

        expose_wishbone_master = soc_config["exposeWishboneMaster"]
        if is_extended_generation(generation_kind):
            expose_wishbone_master = True

        soc_config["exposeWishboneMaster"] = expose_wishbone_master
        soc_config.update(
            self._build_lower_camel_config(
                {
                    "top_entity_name": names.top_entity_name,
                    "myhdl_entity_name": names.myhdl_entity_name,
                }
            )
        )
        return soc_config

    def _build_lower_camel_config(self, parameters, defaults=None):
        if defaults is None:
            return {
                snake_to_lower_camel(key): value
                for key, value in parameters.items()
            }

        return {
            snake_to_lower_camel(key): param(parameters, key, default)
            for key, default in defaults.items()
        }

    def _resolve_hexfile(self, parameters, files_root):
        hexfile = self._resolve_single_hexfile_value(param(parameters, "hexfile", ""))
        if not hexfile:
            return ""

        hexfile_path = Path(files_root, hexfile).resolve()
        get_diagnostics().detail("checking hexfile: {}".format(hexfile_path))
        if not hexfile_path.is_file():
            raise FileNotFoundError("Hex file '{}' does not exist.".format(hexfile_path))
        return str(hexfile_path)

    def _resolve_single_hexfile_value(self, hexfile):
        if not isinstance(hexfile, list):
            return hexfile

        selected_hexfiles = [
            entry
            for entry in hexfile
            if entry is not None and entry != ""
        ]
        if len(selected_hexfiles) != 1:
            raise ValueError(
                "'hexfile' list must resolve to exactly one entry, got {}".format(
                    len(selected_hexfiles)
                )
            )
        return selected_hexfiles[0]
