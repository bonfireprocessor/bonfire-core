from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tests.toolchain import fusesoc_command


def _contains_ordered_text(actual: str, expected: list[str]) -> bool:
    position = 0

    for item in expected:
        position = actual.find(item, position)
        if position < 0:
            return False
        position += len(item)

    return True


def test_extended_soc_hello_io_fusesoc(repo_root: Path):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "hello_io.hex"
    if not hexfile.is_file():
        pytest.skip(f"Extended SoC hello HEX file not found: {hexfile}")

    invocation = fusesoc_command("run", "--target=sim_extended", "::bonfire-core-soc:0")
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
    assert "Hello from Bonfire Core!" in result.stdout
    assert "sysclk=25000000" in result.stdout
    assert "baud=115200" in result.stdout
    assert "GPIO test: OK" in result.stdout
    assert "SPI loopback test: OK" in result.stdout
    assert "Extended SoC IO test: OK" in result.stdout
    gpio_block = [
        "IO Pads:00000000(00)",
        "IO Pads:00000001(01)",
        "IO Pads:00000010(02)",
        "IO Pads:00000100(04)",
        "IO Pads:00001000(08)",
        "IO Pads:00010000(10)",
        "IO Pads:00100000(20)",
        "IO Pads:01000000(40)",
        "IO Pads:10000000(80)",
        "IO Pads:01010101(55)",
        "IO Pads:10101010(AA)",
        "IO Pads:11111111(FF)",
    ]
    assert _contains_ordered_text(result.stdout, gpio_block), "Expected GPIO output block not found"
    gpio_values = re.findall(r"IO Pads:([^\s(]+)\(", result.stdout)
    assert gpio_values, "GPIO capture output not found"
    assert all("X" not in value and "U" not in value for value in gpio_values)

    uart_capture = re.search(r"UART0 Test captured bytes:\s*(\d+) framing errors:\s*(\d+)", result.stdout)
    assert uart_capture is not None, "UART capture summary not found"
    assert int(uart_capture.group(1)) > 0
    assert uart_capture.group(2) == "0"
