from capture.tcp_parser import decode_flags, TcpStreamTracker


def test_decode_flags():
    assert decode_flags(0x02) == "SYN"
    assert decode_flags(0x12) == "SYN,ACK"
    assert decode_flags(0) == "-"


def test_stream_tracker_flags_retransmission():
    tracker = TcpStreamTracker()
    base = {"src_ip": "1.1.1.1", "src_port": 1000, "dst_ip": "2.2.2.2",
            "dst_port": 80, "seq": 100, "flags": "PSH,ACK"}
    first = tracker.observe(dict(base))
    second = tracker.observe(dict(base))
    assert first["is_retransmission"] is False
    assert second["is_retransmission"] is True
