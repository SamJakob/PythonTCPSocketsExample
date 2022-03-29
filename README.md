# PythonTCPSocketsExample
This is an example project demonstrating how to communicate between a Python
server and client with a TCP socket.

This example is compatible with my [JavaTCPSocketsExample](https://github.com/SamJakob/JavaTCPSocketsExample).

This is written and tested with Python 3.9, however if you're using an older
Python version (specifically, one less than Python 3.7), you may need to remove
the `import typings` and the type definitions in the files.

Additionally, [`utils/queue.py`](./utils/queue.py) was needed to polyfill some
functionality in Python Queues on macOS systems. To use this polyfill,
simply import `Queue` from `utils` instead of from `multiprocessing`.

- [`scuffed_protocol.py`](./scuffed_protocol.py): is a stub class that simply has
    a constant for the port number of the protocol.
- [`client.py`](./client.py): is a runnable Python file that contains a simple client
    implementation that allows a user to send to a server and prints any received
    messages from the server.
- [`server.py`](./server.py): is a runnable Python file that contains a simple server
    implementation that converts any received messages to CAPITALS and sends the updated
    message back to the client.
