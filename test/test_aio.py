import asyncio
import contextlib
import os
import pathlib
import socket
import sys
import typing
import unittest.mock

import pytest

import asyncio_dgram

if typing.TYPE_CHECKING:
    from socket import _Address
else:
    _Address = None

if sys.version_info < (3, 9):
    from typing import Generator
else:
    from collections.abc import Generator


if sys.version_info < (3, 7):
    asyncio.create_task = asyncio.ensure_future


@contextlib.contextmanager
def loop_exception_handler() -> Generator["asyncio.base_events._Context", None, None]:
    """
    Replace the current event loop exception handler with one that
    simply stores exceptions in the returned dictionary.

    @return - dictionary that is updated with the last loop exception
    """
    context = {}

    def handler(
        loop: asyncio.AbstractEventLoop, c: "asyncio.base_events._Context"
    ) -> None:
        context.update(c)

    loop = asyncio.get_event_loop()
    orig_handler = loop.get_exception_handler()
    loop.set_exception_handler(handler)
    yield context

    loop.set_exception_handler(orig_handler)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr,family",
    [
        (("127.0.0.1", 0), socket.AF_INET),
        (("::1", 0), socket.AF_INET6),
        ("socket", socket.AF_UNIX),
    ],
    ids=["INET", "INET6", "UNIX"],
)
async def test_connect_sync(
    addr: typing.Union[_Address, str],
    family: socket.AddressFamily,
    tmp_path: pathlib.Path,
) -> None:
    # Bind a regular socket, asyncio_dgram connect, then check asyncio send and
    # receive.

    if family == socket.AF_UNIX:
        assert isinstance(addr, str)
        if sys.version_info < (3, 7):
            pytest.skip()
        addr = str(tmp_path / addr)

    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.bind(addr)
        dest = addr if family == socket.AF_UNIX else sock.getsockname()[:2]
        client = await asyncio_dgram.connect(dest)

        assert client.peername == sock.getsockname()

        await client.send(b"hi")
        got, client_addr = sock.recvfrom(4)
        assert got == b"hi"
        assert client.peername == sock.getsockname()

        if family == socket.AF_UNIX:
            assert isinstance(addr, str)
            # AF_UNIX doesn't automatically bind
            assert client_addr is None
            os.unlink(addr)
        else:
            assert client_addr == client.sockname

            sock.sendto(b"bye", client.sockname)
            got, server_addr = await client.recv()
            assert got == b"bye"
            assert server_addr == sock.getsockname()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(client.recv(), 0.05)

        client.close()

    # Same as above but reversing the flow. Bind a regular socket, asyncio_dgram
    # connect, then check asyncio receive and send.
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.bind(addr)
        dest = addr if family == socket.AF_UNIX else sock.getsockname()[:2]
        client = await asyncio_dgram.connect(dest)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(client.recv(), 0.05)

        assert client.peername == sock.getsockname()

        if family != socket.AF_UNIX:
            # AF_UNIX doesn't automatically bind
            sock.sendto(b"hi", client.sockname)
            got, server_addr = await client.recv()
            assert got == b"hi"
            assert server_addr == sock.getsockname()

        await client.send(b"bye")
        got, client_addr = sock.recvfrom(4)
        assert got == b"bye"
        assert client_addr == client.sockname

        client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr,family",
    [
        (("127.0.0.1", 0), socket.AF_INET),
        (("::1", 0), socket.AF_INET6),
        ("socket", socket.AF_UNIX),
    ],
    ids=["INET", "INET6", "UNIX"],
)
async def test_bind_sync(
    addr: typing.Union[_Address, str],
    family: socket.AddressFamily,
    tmp_path: pathlib.Path,
) -> None:
    # Bind an asyncio_dgram, regular socket connect, then check asyncio send and
    # receive.

    if family == socket.AF_UNIX:
        assert isinstance(addr, str)
        if sys.version_info < (3, 7):
            pytest.skip()
        addr = str(tmp_path / addr)

    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        server = await asyncio_dgram.bind(addr)
        sock.connect(server.sockname)

        assert server.peername is None

        if family != socket.AF_UNIX:
            await server.send(b"hi", sock.getsockname())
            got, server_addr = sock.recvfrom(4)
            assert got == b"hi"
            assert server_addr == server.sockname

        sock.sendto(b"bye", server.sockname)
        got, client_addr = await server.recv()
        assert got == b"bye"

        if family == socket.AF_UNIX:
            assert client_addr is None
            os.unlink(addr)
        else:
            assert client_addr == sock.getsockname()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(server.recv(), 0.05)

        server.close()

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

        if family == socket.AF_UNIX:
            # AF_UNIX doesn't automatically bind
            assert client_addr is None
        else:
            assert client_addr == sock.getsockname()

            await server.send(b"bye", sock.getsockname())
            got, server_addr = sock.recvfrom(4)
            assert got == b"bye"
            assert server_addr == server.sockname

        server.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr,family",
    [
        (("127.0.0.1", 0), socket.AF_INET),
        (("::1", 0), socket.AF_INET6),
        ("socket", socket.AF_UNIX),
    ],
    ids=["INET", "INET6", "UNIX"],
)
async def test_from_socket_streamtype(
    addr: typing.Union[_Address, str],
    family: socket.AddressFamily,
    tmp_path: pathlib.Path,
) -> None:
    if family == socket.AF_UNIX:
        assert isinstance(addr, str)
        if sys.version_info < (3, 7):
            pytest.skip()
        addr = str(tmp_path / addr)

    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.bind(addr)
        stream = await asyncio_dgram.from_socket(sock)

        assert stream.sockname is not None
        assert sock.getsockname() == stream.sockname
        assert stream.peername is None
        assert stream.socket.fileno() == sock.fileno()
        assert isinstance(stream, asyncio_dgram.aio.DatagramServer)

    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        if family == socket.AF_UNIX:
            assert isinstance(addr, str)
            os.unlink(addr)

        sock.bind(addr)

        with socket.socket(family, socket.SOCK_DGRAM) as tsock:
            tsock.connect(sock.getsockname())
            stream = await asyncio_dgram.from_socket(tsock)

            if family == socket.AF_UNIX:
                assert stream.sockname is None
                assert tsock.getsockname() == ""
            else:
                assert stream.sockname is not None
                assert stream.sockname == tsock.getsockname()

            assert isinstance(stream, asyncio_dgram.aio.DatagramClient)
            assert stream.peername == sock.getsockname()
            assert stream.socket.fileno() == tsock.fileno()

            # Make sure that the transport stored the peername
            with loop_exception_handler() as context:
                await stream.send(b"abc")
                assert context == {}


@pytest.mark.asyncio
async def test_from_socket_bad_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockSocket:
        family = socket.AF_PACKET

    with monkeypatch.context() as m:
        m.setattr(socket, "socket", lambda _, __: MockSocket())
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        with pytest.raises(TypeError, match="socket family not one of"):
            await asyncio_dgram.from_socket(sock)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sys.version_info < (3, 11):
            msg = "must be SocketKind.SOCK_DGRAM"
        else:
            msg = "socket type must be 2"

        with pytest.raises(TypeError, match=msg):
            await asyncio_dgram.from_socket(sock)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr,family",
    [(("127.0.0.1", 0), socket.AF_INET), (("::1", 0), socket.AF_INET6)],
    ids=["INET", "INET6"],
)
async def test_no_server(addr: _Address, family: socket.AddressFamily) -> None:
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
async def test_echo(addr: _Address) -> None:
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

    server.close()
    client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr,family",
    [
        (("127.0.0.1", 0), socket.AF_INET),
        (("::1", 0), socket.AF_INET6),
        (None, socket.AF_UNIX),
    ],
    ids=["INET", "INET6", "UNIX"],
)
async def test_echo_bind(
    addr: typing.Optional[_Address],
    family: socket.AddressFamily,
    tmp_path: pathlib.Path,
) -> None:
    if family == socket.AF_UNIX:
        if sys.version_info < (3, 7):
            pytest.skip()
        server = await asyncio_dgram.bind(tmp_path / "socket1")
        client = await asyncio_dgram.bind(tmp_path / "socket2")
    else:
        assert addr is not None
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

    server.close()
    client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("addr", [("127.0.0.1", 0), ("::1", 0)], ids=["INET", "INET6"])
async def test_unconnected_sender(addr: _Address) -> None:
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

    ep1.close()
    ep2.close()
    connected.close()


@pytest.mark.asyncio
async def test_protocol_pause_resume(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    # This is a little involved, but necessary to make sure that the Protocol
    # is correctly noticing when writing as been paused and resumed.  In
    # summary:
    #
    # - Mock the Protocol with one that sets the write buffer limits to 0 and
    # records when pause and resume writing are called.
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

        def __init__(self, *args, **kwds) -> None:  # type: ignore
            TestableProtocol.instance = self
            super().__init__(*args, **kwds)

        def connection_made(self, transport: asyncio.BaseTransport) -> None:
            assert isinstance(transport, asyncio.WriteTransport)
            transport.set_write_buffer_limits(low=0, high=0)
            super().connection_made(transport)

        def pause_writing(self) -> None:
            self.pause_writing_called += 1
            super().pause_writing()

        def resume_writing(self) -> None:
            self.resume_writing_called += 1
            super().resume_writing()

    async def passthrough() -> None:
        """
        Used to mock the wait method on the asyncio.Event tracking if the write
        buffer is past the high water mark or not.  Given we're testing how
        that case is handled, we know it's safe locally to mock it.
        """
        pass

    mock_socket = unittest.mock.create_autospec(socket.socket)
    mock_socket.family = socket.AF_INET
    mock_socket.type = socket.SOCK_DGRAM

    with monkeypatch.context() as ctx:
        ctx.setattr(asyncio_dgram.aio, "Protocol", TestableProtocol)

        client = await asyncio_dgram.from_socket(mock_socket)
        assert isinstance(client, asyncio_dgram.aio.DatagramClient)
        assert TestableProtocol.instance is not None

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


@pytest.mark.asyncio
async def test_transport_closed() -> None:
    stream = await asyncio_dgram.bind(("127.0.0.1", 0))

    # Two tasks, both receiving.  This is a bit weird and we don't handle it at
    # this level on purpose.  The test is here to make that clear.  If having
    # multiple recv() calls racing against each other on a single event loop is
    # desired, one can wrap the DatagramStream with some sort of
    # dispatcher/adapter.
    recv = asyncio.create_task(stream.recv())
    recv_hung = asyncio.create_task(stream.recv())

    # Make sure both tasks get past the initial check for
    # transport.is_closing()
    await asyncio.sleep(0.1)

    stream.close()

    # Recv scheduled before transport closed
    with pytest.raises(asyncio_dgram.TransportClosed):
        await recv

    # This task isn't going to finish.
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(recv_hung, timeout=0.01)

    if sys.version_info >= (3, 7):
        assert recv_hung.cancelled()

    # No recv after transport closed
    with pytest.raises(asyncio_dgram.TransportClosed):
        await stream.recv()

    # No send after transport closed
    with pytest.raises(asyncio_dgram.TransportClosed):
        await stream.send(b"junk", ("127.0.0.1", 0))


@pytest.mark.asyncio
async def test_bind_reuse_port() -> None:
    async def use_socket(
        addr: _Address, reuse_port: typing.Optional[bool] = None
    ) -> None:
        sock = await asyncio_dgram.bind(addr, reuse_port=reuse_port)
        # give gather time to move to the other uses after the bind
        await asyncio.sleep(0.1)
        sock.close()

    addr = ("127.0.0.1", 53001)
    clients_count = 10
    with pytest.raises(OSError, match="Address already in use"):
        await asyncio.gather(*[use_socket(addr) for _ in range(clients_count)])

    # We use another port in case the prev socket is still active (/ is still closing)
    addr_2 = ("127.0.0.1", 53002)
    await asyncio.gather(
        *[use_socket(addr_2, reuse_port=True) for _ in range(clients_count)]
    )
