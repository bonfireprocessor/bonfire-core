"""
Bonfire Core Simulation Debug Server
(c) 2019,2020 The Bonfire Project
License: See LICENSE
"""


from __future__ import print_function

from myhdl import *

@block
def tcpserver(dtm_bundle,clock):
    """
    dtm_bundle: AbstractDebugTransportBundle
    clock: clock
    """

    import socket
    import select
    import sys
    from tb.gdbserver import GDBClientHandler


    @instance
    def server():
     # Define host and port
        host = 'localhost'
        port = 5500
        
        # Create a socket object
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Bind the socket to the host and port
        server_socket.bind((host, port))
        
        # Listen for incoming connections
        server_socket.listen(5)
        
        print(f"Server is listening on port {port}...")
        
        # Create a poll object
        poll_object = select.poll()
        
        # Register the server socket for polling
        poll_object.register(server_socket, select.POLLIN)
        
        # Dictionary to map file descriptors to their corresponding socket objects
        fd_to_socket = {server_socket.fileno(): server_socket}

        client_handler=None
        
        while True:
            yield clock.posedge
       
            # Poll for events
            events = poll_object.poll(0)
            
            for fd, event in events:
                # If the event is on the server socket, accept the connection
                if fd == server_socket.fileno():
                    if not client_handler:
                        client_socket, client_address = server_socket.accept()
                        print(f"Connection from {client_address}")
                        
                        # Register the client socket for polling
                        poll_object.register(client_socket, select.POLLIN)
                        
                        # Add the client socket to the dictionary
                        fd_to_socket[client_socket.fileno()] = client_socket

                        client_handler = GDBClientHandler(clientsocket=client_socket)
                    else:
                        print("Server already busy")
                    
                
                # If the event is on a client socket, receive and echo back data
                elif event & select.POLLIN:
                    print("run_cmd")
                    data = client_socket.recv(1024)
                    print(f"Received: {data.decode(encoding='ASCII')}")
                    client_handler.run_cmd(data)
                    print("run_cmd return")
                    # client_socket = fd_to_socket[fd]
                    # data = client_socket.recv(1024).decode('utf-8')
                    # print(f"Received: {data} from {client_socket.getpeername()}")
                    
                    # if data:
                    #     client_socket.sendall(data.encode('utf-8'))
                    # else:
                    #     # If no data is received, close the connection
                    #     print(f"Closing connection with {client_socket.getpeername()}")
                    #     poll_object.unregister(client_socket)
                    #     client_socket.close()
                    #     del fd_to_socket[fd]

    return instances()