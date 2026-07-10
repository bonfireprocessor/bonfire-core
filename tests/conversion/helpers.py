from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.toolchain import ghdl_command

pytestmark = pytest.mark.filterwarnings("ignore::myhdl.ToVHDLWarning")


def conversion_output_dir(repo_root: Path, name: str) -> Path:
    output_dir = repo_root / "vhdl_gen" / name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def assert_vhdl_file(output_dir: Path, name: str) -> Path:
    vhdl_file = output_dir / f"{name}.vhd"
    assert vhdl_file.exists(), f"VHDL file not created: {vhdl_file}"
    assert vhdl_file.stat().st_size > 0, f"VHDL file is empty: {vhdl_file}"

    content = vhdl_file.read_text()
    assert "entity" in content.lower(), "VHDL file missing 'entity' keyword"
    assert "architecture" in content.lower(), "VHDL file missing 'architecture' keyword"
    return vhdl_file


def analyze_with_ghdl(output_dir: Path, vhdl_file: Path) -> None:
    vhdl_inputs = sorted(output_dir.glob("pck_myhdl_*.vhd")) + [vhdl_file]
    assert vhdl_inputs, "No VHDL files found for GHDL analysis"
    invocation = ghdl_command(
        "-a",
        "--std=08",
        "--ieee=synopsys",
        "-frelaxed-rules",
        *[str(path.relative_to(output_dir)) for path in vhdl_inputs],
    )

    result = subprocess.run(
        invocation.command,
        check=False,
        cwd=output_dir,
        env=invocation.env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        error_text = (result.stderr or result.stdout).strip()
        pytest.fail(f"ghdl -a failed for {vhdl_file.name}\n{error_text}", pytrace=False)
