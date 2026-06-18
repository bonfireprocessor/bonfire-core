from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.toolchain import fusesoc_command


def _run_soc_fusesoc(repo_root: Path, target: str) -> str:
    invocation = fusesoc_command("run", f"--target={target}", "::bonfire-core-soc:0")
    result = subprocess.run(
        invocation.command,
        cwd=repo_root,
        env=invocation.env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )
    print(result.stdout, end="")
    assert result.returncode == 0, result.stdout
    return result.stdout


def test_basic_soc_uart_echo_fusesoc(repo_root: Path):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "uart_echo.hex"
    if not hexfile.is_file():
        pytest.skip(f"SoC UART echo HEX file not found: {hexfile}")

    output = _run_soc_fusesoc(repo_root, "sim")

    assert "enableDebugModule: True" in output
    assert "enableDebugNdmreset: True" in output
    assert "BonfireUart: DBus UART" in output
    assert "Hellox1A" in output
    assert "UART capture total bytes: 6" in output
    assert "UART capture framing errors: 0" in output
    assert "UART loopback LED value: F" in output


def test_basic_soc_converted_testbench_fusesoc(repo_root: Path):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "led.hex"
    if not hexfile.is_file():
        pytest.skip(f"SoC LED HEX file not found: {hexfile}")

    output = _run_soc_fusesoc(repo_root, "sim_converted")

    assert "enableDebugModule: True" in output
    assert "enableDebugNdmreset: True" in output
    assert "LED status" in output
