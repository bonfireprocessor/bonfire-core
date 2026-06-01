from __future__ import print_function

from rtl.soc.bonfire_core_soc import BonfireCoreSoC
from rtl.soc.bonfire_core_soc_generator import (
    BonfireCoreSoCInstanceGenerator,
    BonfireCoreSoCTestbenchGenerator,
)

from generated_core_writer import GeneratedCoreWriter
from soc_generator_config import SoCGenerationConfigBuilder
from vhdl_template_renderer import VhdlTemplateRenderer


class SoCGenerator:
    def __init__(self, config_builder=None):
        self.config_builder = config_builder or SoCGenerationConfigBuilder()

    def generate(self, parameters, files_root, gen_path, vlnv=None,
                 write_core=True,
                 wrapper_template_path=None,
                 include_extended_testbench=True):
        from rtl import config

        gen_path.mkdir(parents=True, exist_ok=True)
        generation_config = self.config_builder.build(parameters, files_root)

        self._cleanup_generated_outputs(gen_path, generation_config)

        conf = config.BonfireConfig()
        conf.jump_bypass = parameters.get("jump_bypass", False)
        print("jump_bypass {}".format(conf.jump_bypass))
        print("Generation kind {}".format(generation_config.generation_kind))

        soc = BonfireCoreSoC(
            conf,
            hexfile=generation_config.hexfile,
            soc_config=generation_config.soc_config,
        )
        self._convert_myhdl(soc, generation_config, gen_path)

        filelist = [
            "pck_myhdl_011.vhd",
            "{}.vhd".format(generation_config.names.myhdl_entity_name),
        ]
        testbench_files = []

        if generation_config.is_extended:
            extra_files, testbench_files = self._generate_extended_templates(
                files_root,
                gen_path,
                generation_config,
                wrapper_template_path=wrapper_template_path,
                include_testbench=include_extended_testbench,
            )
            filelist.extend(extra_files)

        if write_core:
            GeneratedCoreWriter(gen_path).write(
                vlnv,
                generation_config.names.top_entity_name,
                filelist,
                testbench_files=testbench_files,
            )

    def _convert_myhdl(self, soc, generation_config, gen_path):
        if generation_config.is_testbench:
            generator = BonfireCoreSoCTestbenchGenerator(soc)
        else:
            generator = BonfireCoreSoCInstanceGenerator(soc)

        generator.convert(
            generation_config.hdl,
            generation_config.names.myhdl_entity_name,
            str(gen_path),
            handleWarnings=generation_config.conversion_warnings,
        )

    def _generate_extended_templates(self, files_root, gen_path, generation_config,
                                     wrapper_template_path=None,
                                     include_testbench=True):
        renderer = VhdlTemplateRenderer(
            files_root,
            gen_path,
            wrapper_template_path=wrapper_template_path,
        )
        files = [
            renderer.render_extended_wrapper(
                generation_config.names,
                generation_config.soc_config,
            )
        ]
        testbench_files = []

        if include_testbench:
            testbench_files.append(
                renderer.render_extended_testbench(
                    generation_config.names,
                    generation_config.soc_config,
                )
            )

        return files, testbench_files

    def _cleanup_generated_outputs(self, gen_path, generation_config):
        names = {
            "pck_myhdl_011.vhd",
            "{}.vhd".format(generation_config.names.myhdl_entity_name),
            "{}.v".format(generation_config.names.myhdl_entity_name),
            "{}.core".format(generation_config.names.top_entity_name),
        }
        if generation_config.is_extended:
            names.add("{}.vhd".format(generation_config.names.top_entity_name))
            names.add(generation_config.names.extended_testbench_file)

        for name in names:
            path = gen_path / name
            if path.exists():
                path.unlink()
