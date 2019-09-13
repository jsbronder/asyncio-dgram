import asyncio
import warnings

__all__ = ("bind", "connect")


class DatagramStream:
    """
    Representation of a Datagram socket attached via either bind() or
    connect() returned to consumers of this module.  Provides simple
    wrappers around sending and receiving bytes.

    Due to the stateless nature of datagram protocols, errors are not
    immediately available to this class at the point an action was performed
    that will generate it.  Rather, successive calls will raise exceptions if
    there are any.  Checking for exceptions can be done explicitly by using the
    exception property.

    For instance, failure to connect to a remote endpoint will not be noticed
    until some point in time later, at which point ConnectionRefused will be
    raised.
    """

    def __init__(self, transport, recvq, excq):
        """
        @param transport    - asyncio transport
        @param recvq        - asyncio queue that gets populated by the
                              DatagramProtocol with received datagrams.
        @param excq         - asyncio queue that gets populated with any errors
                              detected by the DatagramProtocol.
        """
        self._transport = transport
        self._recvq = recvq
        self._excq = excq

    def __del__(self):
        self._transport.close()

    @property
    def exception(self):
        """
        If the underlying protocol detected an error, raise the first
        unconsumed exception it noticed, otherwise returns None.
        """
        try:
            exc = self._excq.get_nowait()
            raise exc
        except asyncio.queues.QueueEmpty:
            pass

    @property
    def sockname(self):
        """
        The associated socket's own address
        """
        return self._transport.get_extra_info("sockname")

    @property
    def peername(self):
        """
        The address the associated socket is connected to
        """
        return self._transport.get_extra_info("peername")

    def close(self):
        """
        Close the underlying transport.
        """
        self._transport.close()

    async def send(self, data, addr=None):
        """
        @param data - bytes to send
        @param addr - remote address to send data to, if unspecified then the
                      underlying socket has to have been been connected to a
                      remote address previously.
        """
        _ = self.exception
        self._transport.sendto(data, addr)

    async def recv(self):
        """
        Receive data on the local socket.

        @return - tuple of the bytes received and the address (ip, port) that
                  the data was received from.
        """
        _ = self.exception
        data, addr = await self._recvq.get()
        return data, addr


class DatagramServer(DatagramStream):
    """
    Datagram socket bound to an address on the local machine.
    """

    async def send(self, data, addr):
        """
        @param data - bytes to send
        @param addr - remote address to send data to.
        """
        await super().send(data, addr)


class DatagramClient(DatagramStream):
    """
    Datagram socket connected to a remote address.
    """

    async def send(self, data):
        """
        @param data - bytes to send
        """
        await super().send(data)


class Protocol(asyncio.DatagramProtocol):
    """
    asyncio.DatagramProtocol for feeding received packets into the
    Datagram{Client,Server} which handles converting the lower level callback
    based asyncio into higher level coroutines.
    """

    def __init__(self, recvq, excq):
        """
        @param recvq    - asyncio.Queue for new datagrams
        @param excq     - asyncio.Queue for exceptions
        """
        self._recvq = recvq
        self._excq = excq

        # Transports are connected at the time a connection is made.
        self._transport = None

    def connection_made(self, transport):
        if self._transport is not None:
            old_peer = self._transport.get_extra_info("peername")
            new_peer = transport.get_extra_info("peername")
            warnings.warn(
                "Reinitializing transport connection from %s to %s", old_peer, new_peer
            )

        self._transport = transport

    def connection_lost(self, exc):
        if exc is not None:
            self._excq.put_nowait(exc)

        if self._transport is not None:
            self._transport.close()
            self._transport = None

    def datagram_received(self, data, addr):
        self._recvq.put_nowait((data, addr))

    def error_received(self, exc):
        self._excq.put_nowait(exc)


async def bind(addr):
    """
    Bind a socket to a local address for datagrams.  The socket will be either
    AF_INET or AF_INET6 depending upon the type of address specified.  The
    socket will be reusable (SO_REUSEADDR) once it enters TIME_WAIT.

    @param addr - For AF_INET or AF_INET6, a tuple with the the host and port to
                  to bind; port may be set to 0 to get any free port.
    @return     - A DatagramServer instance
    """
    loop = asyncio.get_event_loop()
    recvq = asyncio.Queue()
    excq = asyncio.Queue()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: Protocol(recvq, excq), local_addr=addr, reuse_address=True
    )

    return DatagramServer(transport, recvq, excq)


async def connect(addr):
    """
    Connect a socket to a remote address for datagrams.  The socket will be
    either AF_INET or AF_INET6 depending upon the type of host specified.

    @param addr - For AF_INET or AF_INET6, a tuple with the the host and port to
                  to connect to.
    @return     - A DatagramClient instance
    """
    loop = asyncio.get_event_loop()
    recvq = asyncio.Queue()
    excq = asyncio.Queue()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: Protocol(recvq, excq), remote_addr=addr
    )

    return DatagramClient(transport, recvq, excq)