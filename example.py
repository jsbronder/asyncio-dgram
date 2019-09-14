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
