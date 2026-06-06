"""
OpenOCD remote_bitbang probe helpers.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class ScanResult:
    bits: int
    value: int

    @property
    def low32(self) -> int:
        return self.value & 0xFFFFFFFF

    def bit(self, index: int) -> int:
        return (self.value >> index) & 1

    def lsb_first(self) -> str:
        return "".join(str(self.bit(index)) for index in range(self.bits))

    def summary(self) -> str:
        if self.bits <= 64:
            return "bits={} lsb_first={} value=0x{:x}".format(self.bits, self.lsb_first(), self.value)
        bits = self.lsb_first()
        return "bits={} low32=0x{:08x} lsb_first_head={}...tail={}".format(
            self.bits,
            self.low32,
            bits[:64],
            bits[-16:],
        )


class RemoteBitbangClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)

    def close(self) -> None:
        self.sock.close()

    def write_pins(self, tck: int, tms: int, tdi: int) -> None:
        value = (0x4 if tck else 0) | (0x2 if tms else 0) | (0x1 if tdi else 0)
        self.sock.sendall(bytes([ord("0") + value]))

    def read_tdo(self) -> int:
        self.sock.sendall(b"R")
        data = self.sock.recv(1)
        if data not in (b"0", b"1"):
            raise AssertionError("Unexpected remote_bitbang TDO response: {!r}".format(data))
        return 1 if data == b"1" else 0

    def cycle(self, tms: int, tdi: int = 0) -> int:
        self.write_pins(0, tms, tdi)
        tdo = self.read_tdo()
        self.write_pins(1, tms, tdi)
        self.write_pins(0, tms, tdi)
        return tdo

    def reset_tap(self) -> None:
        for _ in range(6):
            self.cycle(1)
        self.cycle(0)

    def scan_dr(self, value: int, width: int) -> ScanResult:
        result = 0
        self.cycle(1)
        self.cycle(0)
        self.cycle(0)
        for index in range(width):
            bit = (value >> index) & 1
            tdo = self.cycle(1 if index == width - 1 else 0, bit)
            result |= tdo << index
        self.cycle(1)
        self.cycle(0)
        return ScanResult(width, result)

    def scan_ir(self, value: int, width: int) -> ScanResult:
        result = 0
        self.cycle(1)
        self.cycle(1)
        self.cycle(0)
        self.cycle(0)
        for index in range(width):
            bit = (value >> index) & 1
            tdo = self.cycle(1 if index == width - 1 else 0, bit)
            result |= tdo << index
        self.cycle(1)
        self.cycle(0)
        return ScanResult(width, result)

    def quit(self) -> None:
        self.sock.sendall(b"Q")

