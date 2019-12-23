import asyncio
import contextlib
import os
import socket
import unittest.mock

import pytest

import asyncio_dgram


@pytest.fixture
def mock_socket():
    s = unittest.mock.create_autospec(socket.socket)
    s.family = socket.AF_INET
    s.type = socket.SOCK_DGRAM

    return s


@contextlib.contextmanager
def loop_exception_handler():
    """
    Replace the current event loop exception handler with one that
    simply stores exceptions in the returned dictionary.

    @return - dictionary that is updated with the last loop exception
    """
    context = {}

    def handler(self, c):
        context.update(c)

    loop = asyncio.get_event_loop()
    orig_handler = loop.get_exception_handler()
    loop.set_exception_handler(handler)
    yield context

    loop.set_exception_handler(orig_handler)


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
async def test_from_socket_streamtype(addr, family):
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.bind(addr)
        stream = await asyncio_dgram.from_socket(sock)

        assert stream.sockname is not None
        assert sock.getsockname() == stream.sockname
        assert stream.peername is None
        assert stream.socket.fileno() == sock.fileno()
        assert isinstance(stream, asyncio_dgram.aio.DatagramServer)

    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.bind(addr)

        with socket.socket(family, socket.SOCK_DGRAM) as tsock:
            tsock.connect(sock.getsockname())
            stream = await asyncio_dgram.from_socket(tsock)

            assert stream.sockname is not None
            assert tsock.getsockname() == stream.sockname
            assert isinstance(stream, asyncio_dgram.aio.DatagramClient)
            assert stream.peername == sock.getsockname()
            assert stream.socket.fileno() == tsock.fileno()

            # Make sure that the transport stored the peername
            with loop_exception_handler() as context:
                await stream.send(b"abc")
                assert context == {}


@pytest.mark.asyncio
async def test_from_socket_bad_socket():
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        with pytest.raises(TypeError, match="either AddressFamily.AF"):
            await asyncio_dgram.from_socket(sock)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(TypeError, match="must be SocketKind.SOCK_DGRAM"):
            await asyncio_dgram.from_socket(sock)


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


@pytest.mark.asyncio
async def test_protocol_pause_resume(monkeypatch, mock_socket, tmp_path):
    # This is a little involved, but necessary to make sure that the Protocol
    # is correctly noticing when writing as been paused and resumed.  In
    # summary:
    #
    # - Mock the Protocol with one that sets the write buffer limits to 0 and
    # records when pause and recume writing are called.
    #
    # - Use a mock socket so that we can inject a BlockingIOError on send.
    # Ideally we'd mock method itself, but it's read-only the entire object
    # needs to be mocked.  Due to this, we need to use a temporary file that we
    # can write to in order to kick the event loop to consider it ready for
    # writing.

    class TestableProtocol(asyncio_dgram.aio.Protocol):
        pause_writing_called = 0
        resume_writing_called = 0
        instance = None

        def __init__(self, *args, **kwds):
            TestableProtocol.instance = self
            super().__init__(*args, **kwds)

        def connection_made(self, transport):
            transport.set_write_buffer_limits(low=0, high=0)
            super().connection_made(transport)

        def pause_writing(self):
            self.pause_writing_called += 1
            super().pause_writing()

        def resume_writing(self):
            self.resume_writing_called += 1
            super().resume_writing()

    async def passthrough():
        """
        Used to mock the wait method on the asyncio.Event tracking if the write
        buffer is past the high water mark or not.  Given we're testing how
        that case is handled, we know it's safe locally to mock it.
        """
        pass

    with monkeypatch.context() as ctx:
        ctx.setattr(asyncio_dgram.aio, "Protocol", TestableProtocol)

        client = await asyncio_dgram.from_socket(mock_socket)
        mock_socket.send.side_effect = BlockingIOError
        mock_socket.fileno.return_value = os.open(
            tmp_path / "socket", os.O_RDONLY | os.O_CREAT
        )

        with monkeypatch.context() as ctx2:
            ctx2.setattr(client._drained, "wait", passthrough)
            await client.send(b"foo")

        assert TestableProtocol.instance.pause_writing_called == 1
        assert TestableProtocol.instance.resume_writing_called == 0
        assert not TestableProtocol.instance._drained.is_set()

        mock_socket.send.side_effect = None
        fd = os.open(tmp_path / "socket", os.O_WRONLY)
        os.write(fd, b"\n")
        os.close(fd)

        with monkeypatch.context() as ctx2:
            ctx2.setattr(client._drained, "wait", passthrough)
            await client.send(b"foo")
        await asyncio.sleep(0.1)

        assert TestableProtocol.instance.pause_writing_called == 1
        assert TestableProtocol.instance.resume_writing_called == 1
        assert TestableProtocol.instance._drained.is_set()

        os.close(mock_socket.fileno.return_value)
