"""
Bonfire Core simulation GDB server runner
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""

from __future__ import print_function

from myhdl import *

from gdbserver.server import GDBClientHandler
from tb.debug_api import DebugAPISim


@block
def tcp_server(dtm_bundle, clock):
    """Expose a simulated Bonfire core over the GDB remote serial protocol."""

    import select
    import socket
    from random import randrange

    @instance
    def server():
        host = 'localhost'
        port = 5500 + randrange(0, 51)
        readySignal = Signal(bool(0))
        api = DebugAPISim(dtm_bundle=dtm_bundle, clock=clock)

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(5)

        print(f"Server is listening on port {port}...")

        poll_object = select.poll()
        poll_object.register(server_socket, select.POLLIN)

        fd_to_socket = {server_socket.fileno(): server_socket}
        client_handler = None

        while True:
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
                    print(f"@{now()} Received: {data.decode(encoding='ASCII')}")
                    readySignal.next = False
                    yield clock.posedge
                    yield client_handler.run_cmd(data)
                    yield readySignal
                    print(f"@{now()} run_cmd done")

    return instances()
