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
        for key in ("enableUart1", "enableSpi", "enableGpio", "debug", "instUartOnly"):
            config[key] = self._bool_vhdl(config[key])
        return config

    def _bool_vhdl(self, value):
        return "true" if bool(value) else "false"
