from __future__ import annotations

import shutil
import subprocess
import warnings
from pathlib import Path

import pytest


def _fusesoc_command() -> str:
    if shutil.which("ghdl") is not None:
        return "fusesoc run --target=sim_extended ::bonfire-core-soc:0"

    env_script = Path.home() / "opt" / "oss-cad-new" / "oss-cad-suite" / "environment"
    if env_script.is_file():
        return f"source {env_script} && fusesoc run --target=sim_extended ::bonfire-core-soc:0"

    warnings.warn("Skipping Extended SoC test: neither global ghdl nor OSS CAD Suite environment was found")
    pytest.skip("ghdl not found and OSS CAD Suite environment not available")


def test_extended_soc_hello_fusesoc(repo_root: Path):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "hello.hex"
    if not hexfile.is_file():
        pytest.skip(f"Extended SoC hello HEX file not found: {hexfile}")

    result = subprocess.run(
        ["bash", "-lc", _fusesoc_command()],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )
    print(result.stdout, end="")

    assert result.returncode == 0, result.stdout
    assert "Hello from Bonfire Core!" in result.stdout
    assert "sysclk=25000000" in result.stdout
    assert "baud=115200" in result.stdout
    gpio_block = [
        "LEDs:00000011(03)",
        "IO Pads:00000000(00)",
        "IO Pads:00000001(01)",
        "IO Pads:00000010(02)",
        "IO Pads:00000100(04)",
        "IO Pads:00001000(08)",
        "IO Pads:00010000(10)",
        "IO Pads:00100000(20)",
        "IO Pads:01000000(40)",
        "IO Pads:10000000(80)",
        "LEDs:00000100(04)",
    ]
    gpio_lines = [
        line for line in result.stdout.splitlines()
        if line.startswith("LEDs:") or line.startswith("IO Pads:")
    ]
    for offset in range(len(gpio_lines) - len(gpio_block) + 1):
        if gpio_lines[offset:offset + len(gpio_block)] == gpio_block:
            break
    else:
        pytest.fail("Expected GPIO/LED output block not found")
    assert result.stdout.rstrip().endswith("UART0 Test captured bytes: 97 framing errors: 0")
