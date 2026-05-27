"""
Bonfire Core simulation GDB server runner
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from dataclasses import dataclass, field
from threading import Event
from typing import Any

from myhdl import *

from gdbserver.server import GDBClientHandler
from tb.debug_api import DebugAPISim


@dataclass
class ServerControl:
    host: str = "localhost"
    port: int = 0
    ready_event: Event = field(default_factory=Event)
    stop_event: Event = field(default_factory=Event)


@block
def tcp_server(dtm_bundle, clock, control: ServerControl | None = None):
    """Expose a simulated Bonfire core over the GDB remote serial protocol."""

    import select
    import socket
    from random import randrange

    control = control or ServerControl(port=5500 + randrange(0, 51))

    @instance
    def server():
        readySignal = Signal(bool(0))
        api = DebugAPISim(dtm_bundle=dtm_bundle, clock=clock)

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((control.host, control.port))
        server_socket.listen(5)
        control.port = server_socket.getsockname()[1]
        control.ready_event.set()

        print(f"Server is listening on port {control.port}...")

        poll_object = select.poll()
        poll_object.register(server_socket, select.POLLIN)

        fd_to_socket: dict[int, socket.socket] = {server_socket.fileno(): server_socket}
        client_handler: GDBClientHandler | None = None

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
                            client_handler = GDBClientHandler(clientsocket=client_socket, debugAPI=api, readySignal=readySignal)
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
                        readySignal.next = False
                        yield clock.posedge
                        assert client_handler is not None
                        yield client_handler.run_cmd(data)
                        yield readySignal
                        print(f"@{now()} run_cmd done")
        finally:
            for fd, sock in list(fd_to_socket.items()):
                try:
                    poll_object.unregister(sock)
                except Exception:
                    pass
                try:
                    sock.close()
                except Exception:
                    pass

    return instances()
