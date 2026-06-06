"""
OpenOCD remote_bitbang adapter helpers for simulation.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from __future__ import annotations

import socket
from collections.abc import Generator
from threading import Event
from typing import Any

from myhdl import *

from rtl.type_aliases import BitSignal


def _is_pin_write(command: str) -> bool:
    return "0" <= command <= "7"


def _is_reset_write(command: str) -> bool:
    return "r" <= command <= "u"


@block
def remote_bitbang_server(
    clock: BitSignal,
    tck: BitSignal,
    tms: BitSignal,
    tdi: BitSignal,
    trstn: BitSignal,
    tdo: BitSignal,
    server_socket: socket.socket,
    sysclk_settle_cycles: int = 3,
    verbose: bool = False,
    client_quit_event: Event | None = None,
) -> Any:
    """Serve OpenOCD's remote_bitbang protocol against simulated JTAG pins."""

    server_socket.setblocking(False)

    def log(message: str) -> None:
        if verbose:
            print("@{}ns [remote-bitbang] {}".format(now(), message))

    def wait_sysclk(cycles: int) -> Generator[Any, None, None]:
        for _ in range(cycles):
            yield clock.posedge
            yield delay(0)

    @instance
    def server() -> Generator[Any, None, None]:
        client: socket.socket | None = None

        while True:
            if client is None:
                try:
                    client, address = server_socket.accept()
                    client.setblocking(False)
                    log("client connected from {}".format(address))
                except BlockingIOError:
                    yield clock.posedge
                    continue

            try:
                data = client.recv(1)
            except BlockingIOError:
                yield clock.posedge
                continue

            if not data:
                log("client disconnected")
                client.close()
                client = None
                continue

            command = chr(data[0])

            if _is_pin_write(command):
                value = ord(command) - ord("0")
                tck.next = bool(value & 0x4)
                tms.next = bool(value & 0x2)
                tdi.next = bool(value & 0x1)
                yield delay(0)
                yield wait_sysclk(sysclk_settle_cycles)
            elif command == "R":
                client.sendall(b"1" if bool(tdo) else b"0")
            elif _is_reset_write(command):
                value = ord(command) - ord("r")
                trstn.next = not bool(value & 0x2)
                yield delay(0)
                yield wait_sysclk(sysclk_settle_cycles)
            elif command in ("B", "b", "Z", "z", "O", "o"):
                yield wait_sysclk(1)
            elif command == "Q":
                log("quit")
                client.close()
                client = None
                if client_quit_event is not None:
                    client_quit_event.set()
            else:
                log("ignoring unsupported command {!r}".format(command))
                yield wait_sysclk(1)

    return instances()
