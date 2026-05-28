"""
Bonfire Core simulation GDB server runner
(c) 2019-2026 The Bonfire Project
License: See LICENSE
"""

from __future__ import annotations

import argparse
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Any

from myhdl import *

from gdbserver.gdb_rsp import RSPHandler
from tb.debug_api import DebugAPISim

DEFAULT_GDBSERVER_PORT_BASE = 5500
DEFAULT_GDBSERVER_PORT_SPAN = 51
DEFAULT_HEX_PATH = Path("code/build/debug-tests/endless.hex")


@dataclass
class ServerControl:
    host: str = "localhost"
    port: int | None = None
    memory_size_bytes: int | None = None
    ready_event: Event = field(default_factory=Event)
    stop_event: Event = field(default_factory=Event)


def _bind_server_socket(host: str, port: int | None) -> socket.socket:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    if port is None:
        last_error: OSError | None = None
        for candidate in range(DEFAULT_GDBSERVER_PORT_BASE, DEFAULT_GDBSERVER_PORT_BASE + DEFAULT_GDBSERVER_PORT_SPAN):
            try:
                server_socket.bind((host, candidate))
                return server_socket
            except OSError as exc:
                last_error = exc
        server_socket.close()
        raise OSError(
            f"could not bind any GDB server port in range "
            f"{DEFAULT_GDBSERVER_PORT_BASE}-{DEFAULT_GDBSERVER_PORT_BASE + DEFAULT_GDBSERVER_PORT_SPAN - 1}"
        ) from last_error

    server_socket.bind((host, port))
    return server_socket


@block
def tcp_server(dtm_bundle: Any, clock: Any, control: ServerControl | None = None):
    """Expose a simulated Bonfire core over the GDB remote serial protocol."""

    import select

    control = control or ServerControl()

    @instance
    def server():
        ready_signal = Signal(bool(0))
        api = DebugAPISim(dtm_bundle=dtm_bundle, clock=clock)
        api.memory_size_bytes = control.memory_size_bytes

        server_socket = _bind_server_socket(control.host, control.port)
        server_socket.listen(5)
        control.port = server_socket.getsockname()[1]
        control.ready_event.set()

        print(f"GDB server listening on {control.host}:{control.port}")

        poll_object = select.poll()
        poll_object.register(server_socket, select.POLLIN)

        fd_to_socket: dict[int, socket.socket] = {server_socket.fileno(): server_socket}
        client_handler: RSPHandler | None = None

        try:
            while True:
                if control.stop_event.is_set():
                    raise StopSimulation

                yield clock.posedge
                events = poll_object.poll(0)

                for fd, event in events:
                    if fd == server_socket.fileno():
                        if not client_handler:
                            client_socket, client_address = server_socket.accept()
                            print(f"Connection from {client_address}")
                            poll_object.register(client_socket, select.POLLIN)
                            fd_to_socket[client_socket.fileno()] = client_socket
                            client_handler = RSPHandler(
                                clientsocket=client_socket,
                                debugAPI=api,
                                readySignal=ready_signal,
                            )
                        else:
                            print("Server already busy")

                    elif event & select.POLLIN:
                        client_socket = fd_to_socket[fd]
                        data = client_socket.recv(1024)
                        if not data:
                            poll_object.unregister(client_socket)
                            client_socket.close()
                            del fd_to_socket[fd]
                            client_handler = None
                            continue

                        print(f"@{now()} Received: {data.decode(encoding='ASCII', errors='ignore')}")
                        ready_signal.next = False
                        yield clock.posedge
                        assert client_handler is not None
                        yield client_handler.run_cmd(data)
                        yield ready_signal
                        print(f"@{now()} run_cmd done")
        finally:
            for sock in list(fd_to_socket.values()):
                try:
                    poll_object.unregister(sock)
                except Exception:
                    pass
                try:
                    sock.close()
                except Exception:
                    pass

    return instances()


def serve_gdb(hexfile: Path, host: str = "127.0.0.1", port: int | None = None, ramsize: int = 16384) -> int:
    from gdbserver.sim_testbench import GDBServerTestbench
    from rtl import config

    control = ServerControl(host=host, port=port)
    tb = GDBServerTestbench(
        config.BonfireConfig(),
        hexfile=str(hexfile),
        ramsize=ramsize,
        server_control=control,
    ).testbench()
    sim_error: list[BaseException] = []

    def run_server() -> None:
        try:
            tb.config_sim(trace=False, filename=None)
            tb.run_sim()
        except BaseException as exc:  # pragma: no cover - surfaced in main thread
            sim_error.append(exc)
        finally:
            try:
                tb.quit_sim()
            except Exception:
                pass

    thread = threading.Thread(target=run_server, name="gdbserver-sim", daemon=True)
    thread.start()

    try:
        if not control.ready_event.wait(timeout=5.0):
            raise RuntimeError("gdbserver did not become ready in time")

        while thread.is_alive():
            thread.join(timeout=0.2)
    except KeyboardInterrupt:
        print("Stopping gdbserver...")
        control.stop_event.set()
        thread.join(timeout=5.0)
    finally:
        control.stop_event.set()

    if thread.is_alive():
        raise RuntimeError("gdbserver simulation thread did not stop cleanly")

    if sim_error:
        raise sim_error[0]

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Bonfire simulated GDB server")
    parser.add_argument("--hex", type=Path, default=DEFAULT_HEX_PATH, help="HEX image to load")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"TCP port to bind (default: first free port in {DEFAULT_GDBSERVER_PORT_BASE}-{DEFAULT_GDBSERVER_PORT_BASE + DEFAULT_GDBSERVER_PORT_SPAN - 1})",
    )
    parser.add_argument("--ramsize", type=int, default=16384, help="RAM size in 32-bit words")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    hexfile = args.hex
    if not hexfile.is_absolute():
        hexfile = Path.cwd() / hexfile
    if not hexfile.is_file():
        raise FileNotFoundError(f"GDB server HEX file not found: {hexfile}")
    return serve_gdb(hexfile=hexfile, host=args.host, port=args.port, ramsize=args.ramsize)


if __name__ == "__main__":
    raise SystemExit(main())
