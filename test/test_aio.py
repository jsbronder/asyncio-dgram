import asyncio
import socket

import pytest

import asyncio_dgram


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr,family",
    [(("127.0.0.1", 0), socket.AF_INET), (("::1", 0), socket.AF_INET6)],
    ids=["INET", "INET6"],
)
async def test_connect_sync(addr, family):
    # Bind a regular socket, asyncio_dgram connect, then check asyncio send and
    # receive.
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.bind(addr)
        client = await asyncio_dgram.connect(sock.getsockname()[:2])

        assert client.peername == sock.getsockname()

        await client.send(b"hi")
        got, client_addr = sock.recvfrom(4)
        assert got == b"hi"
        assert client_addr == client.sockname
        assert client.peername == sock.getsockname()

        sock.sendto(b"bye", client.sockname)
        got, server_addr = await client.recv()
        assert got == b"bye"
        assert server_addr == sock.getsockname()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(client.recv(), 0.05)

    # Same as above but reversing the flow. Bind a regular socket, asyncio_dgram
    # connect, then check asyncio receive and send.
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.bind(addr)
        client = await asyncio_dgram.connect(sock.getsockname()[:2])

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(client.recv(), 0.05)

        assert client.peername == sock.getsockname()

        sock.sendto(b"hi", client.sockname)
        got, server_addr = await client.recv()
        assert got == b"hi"
        assert server_addr == sock.getsockname()

        await client.send(b"bye")
        got, client_addr = sock.recvfrom(4)
        assert got == b"bye"
        assert client_addr == client.sockname


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr,family",
    [(("127.0.0.1", 0), socket.AF_INET), (("::1", 0), socket.AF_INET6)],
    ids=["INET", "INET6"],
)
async def test_bind_sync(addr, family):
    # Bind an asyncio_dgram, regular socket connect, then check asyncio send and
    # receive.
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        server = await asyncio_dgram.bind(addr)
        sock.connect(server.sockname)

        assert server.peername is None

        await server.send(b"hi", sock.getsockname())
        got, server_addr = sock.recvfrom(4)
        assert got == b"hi"
        assert server_addr == server.sockname

        sock.sendto(b"bye", server.sockname)
        got, client_addr = await server.recv()
        assert got == b"bye"
        assert client_addr == sock.getsockname()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(server.recv(), 0.05)

    # Same as above but reversing the flow.  Bind an asyncio_dgram, regular
    # socket connect, then check asyncio receive and send.
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        server = await asyncio_dgram.bind(addr)
        sock.connect(server.sockname)

        assert server.peername is None

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(server.recv(), 0.05)

        sock.sendto(b"hi", server.sockname)
        got, client_addr = await server.recv()
        assert got == b"hi"
        assert client_addr == sock.getsockname()

        await server.send(b"bye", sock.getsockname())
        got, server_addr = sock.recvfrom(4)
        assert got == b"bye"
        assert server_addr == server.sockname


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr,family",
    [(("127.0.0.1", 0), socket.AF_INET), (("::1", 0), socket.AF_INET6)],
    ids=["INET", "INET6"],
)
async def test_no_server(addr, family):
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.bind(addr)
        free_addr = sock.getsockname()

    client = await asyncio_dgram.connect(free_addr[:2])
    await client.send(b"hi")

    for _ in range(20):
        try:
            await client.send(b"hi")
        except ConnectionRefusedError:
            break
        await asyncio.sleep(0.01)
    else:
        pytest.fail("ConnectionRefusedError not raised")

    assert client.peername == free_addr
    client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("addr", [("127.0.0.1", 0), ("::1", 0)], ids=["INET", "INET6"])
async def test_echo(addr):
    server = await asyncio_dgram.bind(addr)
    client = await asyncio_dgram.connect(server.sockname[:2])

    await client.send(b"hi")
    data, client_addr = await server.recv()
    assert data == b"hi"
    assert client_addr == client.sockname

    await server.send(b"bye", client_addr)
    data, server_addr = await client.recv()
    assert data == b"bye"
    assert server_addr == server.sockname

    assert server.peername is None
    assert client.peername == server.sockname


@pytest.mark.asyncio
@pytest.mark.parametrize("addr", [("127.0.0.1", 0), ("::1", 0)], ids=["INET", "INET6"])
async def test_echo_bind(addr):
    server = await asyncio_dgram.bind(addr)
    client = await asyncio_dgram.bind(addr)

    await client.send(b"hi", server.sockname)
    data, client_addr = await server.recv()
    assert data == b"hi"
    assert client_addr == client.sockname

    await server.send(b"bye", client_addr)
    data, server_addr = await client.recv()
    assert data == b"bye"
    assert server_addr == server.sockname

    assert server.peername is None
    assert client.peername is None


@pytest.mark.asyncio
@pytest.mark.parametrize("addr", [("127.0.0.1", 0), ("::1", 0)], ids=["INET", "INET6"])
async def test_unconnected_sender(addr):
    # Bind two endpoints and connect to one.  Ensure that only the endpoint
    # that was connected to can send.
    ep1 = await asyncio_dgram.bind(addr)
    ep2 = await asyncio_dgram.bind(addr)
    connected = await asyncio_dgram.connect(ep1.sockname[:2])

    await ep1.send(b"from-ep1", connected.sockname)
    await ep2.send(b"from-ep2", connected.sockname)
    data, server_addr = await connected.recv()
    assert data == b"from-ep1"
    assert server_addr == ep1.sockname

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(connected.recv(), 0.05)
