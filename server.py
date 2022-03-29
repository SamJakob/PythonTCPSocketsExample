from socket import socket, MSG_PEEK
from socketserver import TCPServer, BaseRequestHandler, ThreadingTCPServer
from typing import Optional

# Import our protocol specification.
# This is shared between the client and the server to ensure the values stay consistent.
import scuffed_protocol


class MyServerDelegate(BaseRequestHandler):
    """
    A delegate is simply something that performs something on behalf of something else.
    Hence, this class is called 'MyServerDelegate'; it is a delegate that handles communicating
    with a client that has connected to the server class.

    For every client socket connected to the server, there will be a 'MyServerDelegate' that
    communicates with that client socket. This allows the server to handle communications with
    many clients at once without locking up or hanging.
    """

    request: socket

    # When a new connection is made, a new MyServerDelegate gets constructed,
    # then this method is called to perform set up and initialization tasks before
    # any requests are made.
    def setup(self) -> None:
        self.request.setblocking(False)
        print(f'Accepted connection from: /{self.client_address[0]}:{self.client_address[1]}')

    # When the request gets made, this method is called.
    def handle(self) -> None:

        # TODO: should you 'ping' the client occasionally to ensure the connection
        #   hasn't dropped unexpectedly? ...and if so:
        #   - What should this ping message look like?
        #   - How can you make sure the ping message isn't confused for
        #   a real message?

        # If our socket has some bytes available, we read and process them.
        # (In this case, we just print them out and re-print the prompt to
        # show we're ready for user input.)

        # Python does not allow you to determine how many bytes are available
        # from the input stream, however because we set our socket to
        # non-blocking above, we can peek the first byte and see if a
        # BlockingIOError is raised. If that error is raised it means there are
        # no bytes available.

        # Again, this is a bit of a hack, depending on your protocol (e.g.,
        # whether it receives messages a line at time) it may be better to
        # rewrite this into something resembling the way the console input
        # works (e.g., in other thread buffer input from the socket, then
        # add it to a queue.)

        while True:
            try:
                # Attempt to peek the first byte from the socket.
                self.request.recv(1, MSG_PEEK)

                # TODO: We simply assume that this packet starts with a message
                #   If it didn't, this program would break.
                #   - How can your program handle this gracefully?
                #   ...
                #   This is also an important consideration for your protocol –
                #   how should incorrect messages be handled?

                # Read the incoming message from the client.
                message = self.receive_message()

                # If the message is exit, the client is disconnecting, so close the
                # connection and break out of the loop.
                if message == 'exit':
                    self.request.close()
                    break

                # Write the outgoing message back to the client.
                self.send_message(message.upper())

            except BlockingIOError:
                # Simply do nothing. 'pass' in Python is a no-op (meaning it is
                # an instruction that does nothing.)
                # It is equivalent to having empty braces in Java or other C-like
                # languages.
                pass

    # When the connection is being closed, this method is called to allow the
    # delegate to clean up.
    def finish(self) -> None:
        print(f'Connection closed: /{self.client_address[0]}:{self.client_address[1]}')

    # These methods are the same as the client implementation. For details on them, please
    # refer to client.py.

    def receive_message(self) -> str:
        """
        Attempts to receive a message by first reading the number of bytes in the string
        and then the string itself by reading in that many bytes and UTF-8 decoding them.
        :return: The received message.
        """

        def read_bytes(num_bytes: int, read_function):
            """
            Ensure the entire number of bytes is read. 'read_function' is the function that
            should be used to read up to a certain number of bytes from your socket.
            (Usually the 'recv' function on your socket.)
            """

            # Initialize an empty bytes object to store the received bytes.
            data = bytes()
            # Initialize a counter for the number of bytes we need to receive.
            waiting_for_bytes = num_bytes

            while waiting_for_bytes > 0:
                # Attempt to read up to 'waiting_for_bytes' bytes.
                received_bytes: bytes = read_function(waiting_for_bytes)
                # Add the received bytes to our data object.
                data += received_bytes
                # Subtract the number of bytes received from the number of bytes
                # we're waiting for.
                waiting_for_bytes -= len(received_bytes)

            # Finally, return the collected bytes.
            return data

        str_length = int.from_bytes(read_bytes(2, self.request.recv), byteorder='big')
        return read_bytes(str_length, self.request.recv).decode('utf-8')

    def send_message(self, message: str):
        """
        Sends the specified message to the client.
        :param message: The message to send.
        """

        # Raise an exception if the string is too long.
        if len(message) > 65535:
            raise ValueError("The specified message is too long. It must be at most 65535 bytes.")

        self.request.send(
            # Send the length of the message (which may be up to 65535 – or
            # the size of a 16-bit integer, a.k.a., 2 bytes). We use 'big-endian' byte order.
            len(message).to_bytes(2, byteorder='big') +

            # Then, send the encoded message itself.
            message.encode(encoding='utf-8')
        )


class MyServer:

    # Class constructor.
    def __init__(self):
        self.server_socket: Optional[TCPServer] = None
        """The server socket that accepts connections from clients."""

    def start(self) -> None:
        """
        Starts our server by binding the server socket to our protocol's port
        and activates the server socket, so it starts listening for connections.
        """

        # Initialize the server, which starts listening automatically on our specified
        # port.
        self.server_socket = ThreadingTCPServer(
            ('localhost', scuffed_protocol.PORT),
            MyServerDelegate
        )

        print(f'Now listening on port {scuffed_protocol.PORT}!')
        try:
            self.server_socket.serve_forever()
        except KeyboardInterrupt:
            print("Closing server.")
            self.server_socket.server_close()


# Check if the currently running module is the __main__ module
# (This is essentially Python's version of a main method.)
if __name__ == '__main__':
    my_server = MyServer()
    my_server.start()
