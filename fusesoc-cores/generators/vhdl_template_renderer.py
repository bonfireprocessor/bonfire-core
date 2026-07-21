from __future__ import print_function

import datetime
import sys
from string import Formatter

from util.diagnostics import get_diagnostics


class VhdlTemplateRenderer:
    def __init__(self, files_root, gen_path, wrapper_template_path=None):
        self.files_root = files_root
        self.gen_path = gen_path
        self.wrapper_template_path = wrapper_template_path

    def render_extended_wrapper(self, names, soc_config):
        template_path = self.wrapper_template_path or self.files_root / "templates" / "soc_top.vhd"
        output_file = "{}.vhd".format(names.top_entity_name)
        self._render_template(template_path, self.gen_path / output_file, soc_config)
        return output_file

    def render_basic_jtagg_wrapper(self, names, soc_config):
        output_file = "{}.vhd".format(names.top_entity_name)
        self._render_template(
            self.files_root / "templates" / "soc_basic_jtagg_top.vhd",
            self.gen_path / output_file,
            soc_config,
        )
        return output_file

    def copy_ecp5_jtagg_bridge(self):
        output_file = "ecp5_jtagg_bridge.vhd"
        source = self.files_root / "vhdl" / output_file
        destination = self.gen_path / output_file
        destination.write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        get_diagnostics().summary("generated VHDL: {}".format(destination))
        return output_file

    def render_extended_testbench(self, names, soc_config):
        output_file = names.extended_testbench_file
        self._render_template(
            self.files_root / "templates" / "tb_soc.vhd",
            self.gen_path / output_file,
            soc_config,
        )
        return output_file

    def _render_template(self, template_path, output_path, soc_config):
        template = template_path.read_text()
        render_config = self._prepare_template_config(soc_config)
        try:
            output_path.write_text(template.format(**render_config))
        except KeyError as err:
            keys_in_template = [
                field_name
                for _, field_name, _, _ in Formatter().parse(template)
                if field_name
            ]
            missing_keys = [
                key for key in keys_in_template
                if key not in render_config
            ]
            get_diagnostics().error(
                "missing keys in soc_config: {}".format(
                    ", ".join(missing_keys or [str(err)])
                )
            )
            sys.exit(1)
        get_diagnostics().summary("generated VHDL: {}".format(output_path))

    def _prepare_template_config(self, soc_config):
        config = dict(soc_config)
        config["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config["numLeds_minus_one"] = int(config["numLeds"]) - 1
        config.update(self._extended_jtagg_template_config(config))
        for key in ("enableUart1", "enableSpi", "enableGpio", "debug", "instUartOnly"):
            config[key] = self._bool_vhdl(config[key])
        return config

    def _extended_jtagg_template_config(self, config):
        enabled = (
            bool(config["enableJtagDebug"])
            and config["debugJtagTransport"] == "ecp5_jtagg"
        )
        if not enabled:
            return {
                "jtaggComponentPorts": "",
                "jtaggSignals": "",
                "jtaggBridge": "",
                "jtaggPortMap": "",
            }

        return {
            "jtaggComponentPorts": """;
        jtagg_i_jtck    : in  std_logic;
        jtagg_i_jtdi    : in  std_logic;
        jtagg_i_jshift  : in  std_logic;
        jtagg_i_jupdate : in  std_logic;
        jtagg_i_jrstn   : in  std_logic;
        jtagg_i_jce1    : in  std_logic;
        jtagg_i_jce2    : in  std_logic;
        jtagg_i_jrt1    : in  std_logic;
        jtagg_i_jrt2    : in  std_logic;
        jtagg_o_jtdo1   : out std_logic;
        jtagg_o_jtdo2   : out std_logic""",
            "jtaggSignals": """
signal jtck    : std_logic;
signal jtdi    : std_logic;
signal jshift  : std_logic;
signal jupdate : std_logic;
signal jrstn   : std_logic;
signal jce1    : std_logic;
signal jce2    : std_logic;
signal jrt1    : std_logic;
signal jrt2    : std_logic;
signal jtdo1   : std_logic;
signal jtdo2   : std_logic;
""",
            "jtaggBridge": """
jtagg_bridge_inst: entity work.ecp5_jtagg_bridge
    port map (
        jtck    => jtck,
        jtdi    => jtdi,
        jshift  => jshift,
        jupdate => jupdate,
        jrstn   => jrstn,
        jce1    => jce1,
        jce2    => jce2,
        jrt1    => jrt1,
        jrt2    => jrt2,
        jtdo1   => jtdo1,
        jtdo2   => jtdo2
    );
""",
            "jtaggPortMap": """
        jtagg_i_jtck    => jtck,
        jtagg_i_jtdi    => jtdi,
        jtagg_i_jshift  => jshift,
        jtagg_i_jupdate => jupdate,
        jtagg_i_jrstn   => jrstn,
        jtagg_i_jce1    => jce1,
        jtagg_i_jce2    => jce2,
        jtagg_i_jrt1    => jrt1,
        jtagg_i_jrt2    => jrt2,
        jtagg_o_jtdo1   => jtdo1,
        jtagg_o_jtdo2   => jtdo2,""",
        }

    def _bool_vhdl(self, value):
        return "true" if bool(value) else "false"
