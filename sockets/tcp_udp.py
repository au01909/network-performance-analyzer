"""Raw socket-programming module: minimal TCP/UDP echo client and server
implementations used to demonstrate and measure basic connection timing
and data-transfer throughput, independent of the HTTP load generator.
"""
from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)

BUFFER_SIZE = 4096


@dataclass
class TransferStats:
    bytes_sent: int
    bytes_received: int
    connect_time: float
    round_trip_time: float


class TcpEchoServer:
    """A minimal threaded TCP echo server."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9001) -> None:
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(128)
        self._sock.settimeout(0.5)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        log.info("TCP echo server listening on %s:%d", self.host, self.port)

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: socket.socket) -> None:
        with conn:
            while True:
                try:
                    data = conn.recv(BUFFER_SIZE)
                except OSError:
                    break
                if not data:
                    break
                conn.sendall(data)

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            self._sock.close()
        if self._thread:
            self._thread.join(timeout=2)


class UdpEchoServer:
    """A minimal UDP echo server."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9002) -> None:
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((self.host, self.port))
        self._sock.settimeout(0.5)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        log.info("UDP echo server listening on %s:%d", self.host, self.port)

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                self._sock.sendto(data, addr)
            except OSError:
                break

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            self._sock.close()
        if self._thread:
            self._thread.join(timeout=2)


def tcp_client_echo(host: str, port: int, payload: bytes, timeout: float = 5.0) -> TransferStats:
    """Connect to a TCP echo server, send payload, measure connect + RTT."""
    start_connect = time.perf_counter()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        connect_time = time.perf_counter() - start_connect

        start_rtt = time.perf_counter()
        sock.sendall(payload)
        received = b""
        while len(received) < len(payload):
            chunk = sock.recv(BUFFER_SIZE)
            if not chunk:
                break
            received += chunk
        rtt = time.perf_counter() - start_rtt

    return TransferStats(
        bytes_sent=len(payload),
        bytes_received=len(received),
        connect_time=connect_time,
        round_trip_time=rtt,
    )


def udp_client_echo(host: str, port: int, payload: bytes, timeout: float = 5.0) -> TransferStats:
    """Send a UDP datagram to an echo server and measure round-trip time."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        start = time.perf_counter()
        sock.sendto(payload, (host, port))
        received, _ = sock.recvfrom(BUFFER_SIZE)
        rtt = time.perf_counter() - start
    finally:
        sock.close()

    return TransferStats(
        bytes_sent=len(payload),
        bytes_received=len(received),
        connect_time=0.0,
        round_trip_time=rtt,
    )
