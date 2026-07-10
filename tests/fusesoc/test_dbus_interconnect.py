from __future__ import annotations

import warnings
from pathlib import Path
from textwrap import dedent, indent
from typing import Callable

from myhdl import ToVHDLWarning

from tests.conftest import run_sim, waveform_config
from tests.pure.uncore.test_dbus_interconnect import (
    dbus_interconnect_master8_vhdl_tb,
    dbus_interconnect_signal_array_vhdl_tb,
)


def _dbus_tb_log_lines(text: str, marker: str = "DBUS_TB:") -> list[str]:
    return [
        line[line.index(marker):].strip()
        for line in text.splitlines()
        if marker in line
    ]


def _render_fusesoc_core(name: str, vhdl_inputs: list[Path]) -> str:
    files = indent("\n".join(f"- {path.name}" for path in vhdl_inputs), "      ")
    return dedent(
        """\
        CAPI=2:
        name: ::{name}:0
        filesets:
          rtl:
            file_type: vhdlSource-2008
            files:
        {files}
        targets:
          sim:
            default_tool: ghdl
            filesets: [rtl]
            tools:
              ghdl:
                analyze_options: [--ieee=synopsys, -frelaxed-rules]
                run_options: [--stop-time=500ns]
            toplevel: {name}
        """
    ).format(name=name, files=files)


def _run_converted_vhdl_testbench(
    dut,
    name: str,
    output_dir: Path,
    run_fusesoc: Callable[..., str],
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ToVHDLWarning)
        dut.convert(hdl="VHDL", path=str(output_dir), name=name)

    vhdl_file = output_dir / f"{name}.vhd"
    assert vhdl_file.stat().st_size > 0
    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    (output_dir / f"{name}.core").write_text(
        _render_fusesoc_core(name, vhdl_inputs), encoding="utf-8"
    )
    return run_fusesoc(
        "--cores-root",
        str(output_dir),
        "run",
        "--target=sim",
        f"::{name}:0",
        cwd=output_dir,
        timeout=30,
    )


def test_dbus_interconnect_signal_array_vhdl_testbench(
    repo_root: Path,
    sim_env: dict,
    request,
    capsys,
    run_fusesoc: Callable[..., str],
):
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_signal_array_tb"
    name = "dbus_interconnect_signal_array_tb"

    myhdl_tb = dbus_interconnect_signal_array_vhdl_tb()
    trace, filename = waveform_config(request, sim_env, name)
    run_sim(
        myhdl_tb,
        trace=trace,
        filename=filename,
        duration=500,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    myhdl_lines = _dbus_tb_log_lines(capsys.readouterr().out)
    assert myhdl_lines

    ghdl_output = _run_converted_vhdl_testbench(
        dbus_interconnect_signal_array_vhdl_tb(), name, output_dir, run_fusesoc
    )
    assert _dbus_tb_log_lines(ghdl_output) == myhdl_lines


def test_dbus_interconnect_master8_vhdl_testbench(
    repo_root: Path,
    sim_env: dict,
    request,
    capsys,
    run_fusesoc: Callable[..., str],
):
    output_dir = repo_root / "vhdl_gen" / "dbus_interconnect_master8_tb"
    name = "dbus_interconnect_master8_tb"

    myhdl_tb = dbus_interconnect_master8_vhdl_tb()
    trace, filename = waveform_config(request, sim_env, name)
    run_sim(
        myhdl_tb,
        trace=trace,
        filename=filename,
        duration=500,
        waveforms_dir=sim_env["waveforms_dir"],
    )
    myhdl_lines = _dbus_tb_log_lines(
        capsys.readouterr().out, marker="DBUS8_TB:"
    )
    assert myhdl_lines

    ghdl_output = _run_converted_vhdl_testbench(
        dbus_interconnect_master8_vhdl_tb(), name, output_dir, run_fusesoc
    )
    assert _dbus_tb_log_lines(ghdl_output, marker="DBUS8_TB:") == myhdl_lines
