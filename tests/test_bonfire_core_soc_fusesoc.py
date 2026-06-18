from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.toolchain import fusesoc_command


def test_basic_soc_uart_echo_fusesoc(repo_root: Path):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "uart_echo.hex"
    if not hexfile.is_file():
        pytest.skip(f"SoC UART echo HEX file not found: {hexfile}")

    invocation = fusesoc_command("run", "--target=sim", "::bonfire-core-soc:0")
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
    assert "BonfireUart: DBus UART" in result.stdout
    assert "Hellox1A" in result.stdout
    assert "UART capture total bytes: 6" in result.stdout
    assert "UART capture framing errors: 0" in result.stdout
    assert "UART loopback LED value: F" in result.stdout
