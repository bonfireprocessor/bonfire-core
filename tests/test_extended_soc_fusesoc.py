from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tests.toolchain import fusesoc_command


def _contains_ordered_lines(actual_lines: list[str], expected_lines: list[str]) -> bool:
    if not expected_lines:
        return True

    expected_index = 0

    for line in actual_lines:
        if line.strip().startswith(expected_lines[expected_index]):
            expected_index += 1
            if expected_index == len(expected_lines):
                return True

    return False


def test_extended_soc_hello_fusesoc(repo_root: Path):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "hello.hex"
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
        line.strip() for line in result.stdout.splitlines()
        if line.strip().startswith("LEDs:") or line.strip().startswith("IO Pads:")
    ]
    assert _contains_ordered_lines(gpio_lines, gpio_block), "Expected GPIO/LED output block not found"

    uart_capture = re.search(r"UART0 Test captured bytes:\s*(\d+) framing errors:\s*(\d+)", result.stdout)
    assert uart_capture is not None, "UART capture summary not found"
    assert uart_capture.groups() == ("97", "0")
