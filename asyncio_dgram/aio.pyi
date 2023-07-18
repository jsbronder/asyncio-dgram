import asyncio
import pathlib
import socket
import sys
from socket import _Address
from typing import Any, Optional, Tuple, Union

class DatagramStream:
    def __init__(
        self,
        transport: asyncio.DatagramProtocol,
        recvq: asyncio.Queue,
        excq: asyncio.Queue,
        drained: asyncio.Event,
    ) -> None: ...
    def exception(self) -> None: ...
    def sockname(self) -> str: ...
    def peername(self) -> str: ...

    # TODO: If upstream ever does better then Any, do so here. It's
    # socket.socket in <3.8 and asyncio.TransportSocket thereafter.
    def socket(self) -> Any: ...

    def close(self) -> None: ...
    async def _send(self, data: bytes, addr: Optional[_Address]) -> None: ...
    async def recv(self) -> Tuple[bytes, _Address]: ...

class DatagramServer(DatagramStream):
    async def send(self, data: bytes, addr: _Address) -> None: ...

class DatagramClient(DatagramStream):
    async def send(self, data: bytes) -> None: ...

class Protocol(asyncio.DatagramProtocol):
    def __init__(
        self, recvq: asyncio.Queue, excq: asyncio.Queue, drained: asyncio.Event
    ) -> None: ...
    def connection_made(self, transport: asyncio.BaseTransport) -> None: ...
    def connection_lost(self, exc: Optional[Exception]) -> None: ...
    def datagram_received(self, data: bytes, addr: _Address) -> None: ...
    def error_received(self, exc: Exception) -> None: ...
    def pause_writing(self) -> None: ...
    def resume_writing(self) -> None: ...

async def bind(addr: Union[_Address, pathlib.Path, str], reuse_port: Optional[bool] = None) -> DatagramServer: ...
async def connect(addr: Union[_Address, pathlib.Path, str]) -> DatagramClient: ...
async def from_socket(sock: socket.socket) -> Union[DatagramServer, DatagramClient]: ...

