from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import pytest


def _contains_ordered_text(actual: str, expected: list[str]) -> bool:
    position = 0
    for item in expected:
        position = actual.find(item, position)
        if position < 0:
            return False
        position += len(item)
    return True


def test_basic_soc_uart_echo_fusesoc(repo_root: Path, run_fusesoc: Callable[..., str]):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "uart_echo.hex"
    if not hexfile.is_file():
        pytest.skip(f"SoC UART echo HEX file not found: {hexfile}")

    output = run_fusesoc("run", "--target=sim", "::bonfire-core-soc:0")
    assert "enableDebugModule: True" in output
    assert "enableDebugNdmreset: True" in output
    assert "BonfireUart: DBus UART" in output
    assert "Hellox1A" in output
    assert "UART capture total bytes: 6" in output
    assert "UART capture framing errors: 0" in output
    assert "UART loopback LED value: F" in output


def test_basic_soc_converted_testbench_fusesoc(
    repo_root: Path,
    run_fusesoc: Callable[..., str],
):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "led.hex"
    if not hexfile.is_file():
        pytest.skip(f"SoC LED HEX file not found: {hexfile}")

    output = run_fusesoc("run", "--target=sim_converted", "::bonfire-core-soc:0")
    assert "enableDebugModule: True" in output
    assert "enableDebugNdmreset: True" in output
    assert "LED status" in output


def test_extended_soc_hello_io_fusesoc(repo_root: Path, run_fusesoc: Callable[..., str]):
    hexfile = repo_root / "code" / "build" / "soc" / "sim" / "hello_io.hex"
    if not hexfile.is_file():
        pytest.skip(f"Extended SoC hello HEX file not found: {hexfile}")

    output = run_fusesoc("run", "--target=sim_extended", "::bonfire-core-soc:0")
    assert "Hello from Bonfire Core!" in output
    assert "sysclk=25000000" in output
    assert "baud=115200" in output
    assert "GPIO test: OK" in output
    assert "SPI loopback test: OK" in output
    assert "Extended SoC IO test: OK" in output

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
    assert _contains_ordered_text(output, gpio_block), "Expected GPIO output block not found"
    gpio_values = re.findall(r"IO Pads:([^\s(]+)\(", output)
    assert gpio_values, "GPIO capture output not found"
    assert all("X" not in value and "U" not in value for value in gpio_values)

    uart_capture = re.search(
        r"UART0 Test captured bytes:\s*(\d+) framing errors:\s*(\d+)", output
    )
    assert uart_capture is not None, "UART capture summary not found"
    assert int(uart_capture.group(1)) > 0
    assert uart_capture.group(2) == "0"
