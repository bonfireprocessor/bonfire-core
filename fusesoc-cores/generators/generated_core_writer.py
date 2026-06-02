from __future__ import print_function

from util.diagnostics import get_diagnostics


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


class GeneratedCoreWriter:
    def __init__(self, gen_path):
        self.gen_path = gen_path

    def write(self, vlnv, top_entity_name, filelist, testbench_files=None):
        core_path = self.gen_path / "{}.core".format(top_entity_name)
        core_path.write_text(
            CORE_TEMPLATE.format(
                vlnv=vlnv,
                filetype="vhdlSource-2008",
                files=",".join(filelist),
                testbench=self._testbench_section(testbench_files or []),
            )
        )
        get_diagnostics().summary("generated core: {}".format(core_path.name))

    def _testbench_section(self, testbench_files):
        if not testbench_files:
            return ""

        return TEST_BENCH_TEMPLATE.format(
            filetype="vhdlSource-2008",
            files=",".join(testbench_files),
        )
