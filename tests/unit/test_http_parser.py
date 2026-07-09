from capture.http_parser import HttpExchangeTracker


def test_http_exchange_pairing_and_summary():
    tracker = HttpExchangeTracker(slow_threshold_seconds=0.5)

    request = {
        "type": "request", "method": "GET", "url": "/api",
        "src_ip": "10.0.0.1", "src_port": 5000, "dst_ip": "10.0.0.2", "dst_port": 80,
        "headers": {}, "content_length": 0, "capture_time": 1.0,
    }
    response = {
        "type": "response", "status_code": 200,
        "src_ip": "10.0.0.2", "src_port": 80, "dst_ip": "10.0.0.1", "dst_port": 5000,
        "headers": {}, "content_length": 123, "capture_time": 1.2,
    }

    assert tracker.observe(request) is None
    exchange = tracker.observe(response)
    assert exchange["status_code"] == 200
    assert abs(exchange["response_time"] - 0.2) < 1e-6

    summary = tracker.summary()
    assert summary["total_requests"] == 1
    assert summary["error_rate"] == 0.0
