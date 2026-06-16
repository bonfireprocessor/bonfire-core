"""
Simulation-only UART TX capture helpers.

The capture block follows the behavior of the VHDL
``tb_uart_capture_tx`` helper from bonfire-util: it waits for UART idle,
captures 8N1 frames, writes/echoes the received characters, and raises the
``stop`` signal when the stop marker byte is seen.  Time values are plain
MyHDL simulation units; the Bonfire convention is ns, so ``delay(10)`` means
10 ns.
"""

from __future__ import annotations

import sys
from typing import Any

from myhdl import Signal, block, delay, instance, instances

from rtl.type_aliases import BitSignal


class UartCaptureResult:
    def __init__(self) -> None:
        self.bytes: list[int] = []
        self.text: str = ""
        self.framing_errors: int = 0
        self.total_count: int = 0
        self.signature_ok: bool | None = None


def _format_charbyte(value: int) -> str:
    if 32 <= value <= 126 or value in (10, 13):
        return chr(value)
    return "\\0x{:02X}".format(value)


@block
def uart_tx_capture(
    tx: BitSignal,
    bit_time: int,
    result: UartCaptureResult,
    stop: BitSignal,
    stop_mark: int = 0x1A,
    echo_output: bool = True,
    log_file: str | None = None,
    expected_signature: bytes | list[int] | tuple[int, ...] | None = None,
) -> Any:
    @instance
    def capture():
        log = open(log_file, "w") if log_file else None
        signature = None
        if expected_signature is not None:
            signature = [int(b) & 0xFF for b in expected_signature]

        while tx == 0:
            yield tx.posedge

        while True:
            yield tx.negedge
            yield delay(bit_time + bit_time // 2)

            value = 0
            for bit in range(8):
                if tx:
                    value |= 1 << bit
                yield delay(bit_time)

            if tx != 1:
                result.framing_errors += 1
                print("Framing error encountered")

            text = _format_charbyte(value)
            result.bytes.append(value)
            result.text += text
            result.total_count += 1

            if log is not None:
                log.write(text)
                log.flush()
            if echo_output:
                sys.stdout.write(text)
                sys.stdout.flush()

            if value == stop_mark:
                if log is not None:
                    log.close()
                if signature is not None:
                    result.signature_ok = result.bytes == signature
                    assert result.signature_ok, "UART capture signature mismatch"
                stop.next = True
                break

    return instances()
