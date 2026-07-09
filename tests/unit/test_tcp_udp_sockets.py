import time
from sockets.tcp_udp import TcpEchoServer, UdpEchoServer, tcp_client_echo, udp_client_echo


def test_tcp_echo_roundtrip():
    server = TcpEchoServer(host="127.0.0.1", port=19101)
    server.start()
    time.sleep(0.2)
    try:
        stats = tcp_client_echo("127.0.0.1", 19101, b"unit-test-payload")
        assert stats.bytes_sent == stats.bytes_received
        assert stats.round_trip_time >= 0
    finally:
        server.stop()


def test_udp_echo_roundtrip():
    server = UdpEchoServer(host="127.0.0.1", port=19102)
    server.start()
    time.sleep(0.2)
    try:
        stats = udp_client_echo("127.0.0.1", 19102, b"unit-test-udp")
        assert stats.bytes_sent == stats.bytes_received
    finally:
        server.stop()
