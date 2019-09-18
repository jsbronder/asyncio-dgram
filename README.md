[![Build Status](https://travis-ci.org/jsbronder/asyncio-dgram.svg?branch=master)](https://travis-ci.org/jsbronder/asyncio-dgram)

# Higher level Datagram support for Asyncio
Simple wrappers that allow you to `await read()` from datagrams as suggested
by Guido van Rossum
[here](https://github.com/python/asyncio/pull/321#issuecomment-187022351).  I
frequently found myself having to inherit from `asyncio.DatagramProtocol` and
implement this over and over.

# Design
The goal of this package is to make implementing common patterns that use datagrams
simple and straight-forward while still supporting more esoteric options.  This is done
by taking an opinionated stance on the API that differs from parts of asyncio.  For instance,
rather than exposing a function like
[create\_datagram\_endpoint](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint)
which supports many use-cases and has conflicting parameters, `asyncio_dgram`
only provides three functions for creating a stream:

- `connect((host, port))`: Creates a datagram endpoint which can only
  communicate with the endpoint it connected to.
- `bind((host, port))`: Creates a datagram endpoint that can communicate
  with anyone, but must specified the destination address every time it
  sends.
- `from_socket(sock)`: If the above two functions are not sufficient, then
  `asyncio_dgram` simply lets the caller setup the socket as they see fit.


# Example UDP echo client and server
Following the example of asyncio documentation, here's what a UDP echo client
and server would look like.
```python
import asyncio

import asyncio_dgram


async def udp_echo_client():
    stream = await asyncio_dgram.connect(("127.0.0.1", 8888))

    await stream.send(b"Hello World!")
    data, remote_addr = await stream.recv()
    print(f"Client received: {data.decode()!r}")

    stream.close()


async def udp_echo_server():
    stream = await asyncio_dgram.bind(("127.0.0.1", 8888))

    print(f"Serving on {stream.sockname}")

    data, remote_addr = await stream.recv()
    print(f"Echoing {data.decode()!r}")
    await stream.send(data, remote_addr)

    await asyncio.sleep(0.5)
    print(f"Shutting down server")


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(udp_echo_server(), udp_echo_client()))


if __name__ == "__main__":
    main()
```
