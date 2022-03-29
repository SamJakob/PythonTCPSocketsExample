import sys
from multiprocessing import Process
from typing import Optional

from socket import socket, MSG_PEEK, AF_INET, SOCK_STREAM

# Import Queue from our utilities package.
# This should probably only be necessary on macOS, but is probably worth keeping for
# cross-compatability.
from utils import Queue

# Import our protocol specification.
# This is shared between the client and the server to ensure the values stay consistent.
import scuffed_protocol


class ConsoleInputDelegate(Process):
    """
    A delegate is simply something that performs something on behalf of something else.
    Hence, this class is called 'UserInputDelegate'; it is a delegate that handles User
    Input for whatever class called it.

    When a user enters input, it places the line into the input queue. This allows the
    main process to fetch the user input when it is ready – and allows us the main
    process to check if there is, indeed, some input to actually process.

    We make this process a daemon to stop it from preventing the main program from
    exiting.
    """

    # Class constructor.
    def __init__(self, queue):
        # Store the provided queue.
        self.queue: Queue = queue
        """The queue to write input into when it is ready."""

        # Initialize the thread by making the call to the superclass constructor.
        super().__init__(daemon=True)

    def run(self) -> None:
        # Open the standard input stream from the main process.
        # We need to do this explicitly, because it is not shared with additional
        # processes by default.
        sys.stdin = open(0)

        # For the lifetime of the thread, we'll continuously wait for entered data.
        while True:
            # Wait for user input and then execute the provided callback.
            self.queue.put(input())


class MyClient:

    # Class constructor.
    # Here, we initialize our socket value to 'None' (Python's version of null)
    # and initialize the UserInputThread.
    def __init__(self):
        self.socket: Optional[socket] = None
        """The client socket that gets connected to the server."""

        self.console_input_queue = Queue()
        """The queue of lines that the user has entered into the console, that have yet to be processed."""

        self.console_input_delegate = ConsoleInputDelegate(queue=self.console_input_queue)
        """The delegate class that waits for user input."""

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

        # If we're here, it means an exception wasn't raised, so we can
        # continue to read data from the socket, knowing data is there
        # for us to read.

        # TODO: We simply assume that this packet starts with an integer
        #   indicating the number of bytes. If it didn't, this program
        #   would break.
        #   - How can your program handle this gracefully?
        #   ...
        #   This is also an important consideration for your protocol –
        #   how should incorrect messages be handled?

        # Read the number of bytes for the string length. This is simply
        # the inverse of what we do in send_message, so you can refer to
        # that for details (below).
        str_length = int.from_bytes(read_bytes(2, self.socket.recv), byteorder='big')

        # Now, we receive that many bytes and UTF-8 decode them into a
        # string.
        return read_bytes(str_length, self.socket.recv).decode('utf-8')

    def send_message(self, message: str) -> None:
        """
        Sends the specified message to the server if the socket is not equal to
        None (i.e., if the socket is connected).

        :param message: The message to send.
        """

        # Raise an exception if the string is too long.
        if len(message) > 65535:
            raise ValueError("The specified message is too long. It must be at most 65535 bytes.")

        # TODO: It might be worth Google-ing 'endianness'.
        #   Endianness is the order in which binary numbers are stored and processed
        #   by the CPU and it is therefore an important thing in Computer Networking.
        #   ...
        #   You should take care to ensure that this is consistent, either with
        #   your protocol or with your systems or programming languages.
        #   ...
        #   Intel systems are little-endian.
        #   Networking systems, non-Intel systems and specifically the Java programming
        #   language are big-endian and for this reason 'big-endianness' has been
        #   selected here to maintain compatability with the Java example.

        self.socket.send(
            # Send the length of the message (which may be up to 65535 – or
            # the size of a 16-bit integer, a.k.a., 2 bytes). We use 'big-endian' byte order.
            len(message).to_bytes(2, byteorder='big') +

            # Then, send the encoded message itself.
            message.encode(encoding='utf-8')
        )

    def start(self) -> None:
        """
        Starts our client by opening a connection to the server on the
        protocol port and accepting user input to send to the server.
        """

        try:
            # Initialize our socket and connect to the server.
            self.socket = socket(AF_INET, SOCK_STREAM)
            self.socket.connect(('localhost', scuffed_protocol.PORT))

            # We set our socket to non-blocking to allow us to 'poll' the socket
            # for available bytes. You could consider this a bit of a hack, and
            # perhaps better practice would be to buffer input lines like we do
            # for console input, though this one depends more on your protocol
            # and what kind of data you expect from the user as well as when you
            # expect it.
            self.socket.setblocking(False)

            # We use 'sys.stdout.write' instead of 'print' to avoid printing a
            # newline at the end of the string. We then use 'flush' to ensure
            # it gets printed.
            # (Python sometimes buffers output until a newline is encountered.)
            sys.stdout.write("> ")
            sys.stdout.flush()

            # Now, start the input thread that waits for user input. When we
            # initialized the input thread in our constructor, we passed in the
            # 'send_message' function which the input thread will call whenever
            # a line of input is entered. In this case, it will deliver that
            # line of input to the server.
            self.console_input_delegate.start()

            # Keep looping until the loop is ended with a 'break' statement. There's
            # no convenient way to check if a socket is closed in Python because TCP
            # doesn't include this functionality.

            # There's no convenient way, in Python, to check if we've closed a socket,
            # so we keep looping until socket is set to None, which is our way of
            # indicating that it's been closed.

            # TODO: How could you include a feature in your protocol that checks if the
            #   server's connection has dropped unexpectedly?

            while self.socket is not None:
                try:

                    # TODO: when should a user be able to send messages?
                    #   Should every outgoing message expect a response before another
                    #   message can be sent?

                    # If we have some entries ready in our input queue, (i.e., someone
                    # has typed something into the console), then we read and process
                    # the input.
                    if self.console_input_queue.qsize() > 0:
                        message = self.console_input_queue.get()
                        self.send_message(message)

                        # If the message was 'exit', clean up and exit.
                        if message == "exit":
                            # Close the socket and set it to None to 'signal' to our program that
                            # the socket is now closed.
                            self.socket.close()
                            self.socket = None

                            # We now break out of the loop.
                            break

                    # Next, if our socket has some bytes available, we read and process
                    # them. (In this case, we just print them out and re-print the prompt
                    # to show we're ready for user input.)

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
                    try:
                        # Attempt to peek the first byte from the socket.
                        self.socket.recv(1, MSG_PEEK)

                        message = self.receive_message()

                        # ...and now we print the message. (We print a newline before to
                        # ensure we don't print after the prompt.)
                        print(message)

                        # Finally, we re-print the prompt to indicate to the user that
                        # we're ready for user input again.
                        sys.stdout.write('> ')
                        sys.stdout.flush()
                    except BlockingIOError:
                        # Simply do nothing. 'pass' in Python is a no-op (meaning it is
                        # an instruction that does nothing.)
                        # It is equivalent to having empty braces in Java or other C-like
                        # languages.
                        pass

                except ConnectionError:
                    print("A communication error occurred with the server.")

            print("\nConnection closed.")

        except ConnectionError as connectionError:
            # Print a message to the standard error stream.
            # This is equivalent to System.error.println in Java.
            print("Failed to connect to the server. Is it running?", file=sys.stderr)
            print(connectionError, file=sys.stderr)


# Check if the currently running module is the __main__ module
# (This is essentially Python's version of a main method.)
if __name__ == '__main__':
    my_client = MyClient()
    my_client.start()
