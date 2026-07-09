from capture.dns_parser import DnsLatencyTracker


def test_dns_latency_pairing():
    tracker = DnsLatencyTracker()
    tracker.observe({"transaction_id": 1, "is_response": False, "query_name": "example.com",
                      "query_type": "A"}, timestamp=1.0)
    tracker.observe({"transaction_id": 1, "is_response": True, "query_name": "example.com",
                      "query_type": "A", "response_code": "NOERROR", "answers": ["1.2.3.4"]},
                     timestamp=1.25)
    assert len(tracker.completed) == 1
    entry = tracker.completed[0]
    assert abs(entry["response_time"] - 0.25) < 1e-6


def test_most_requested_domains():
    tracker = DnsLatencyTracker()
    for i in range(3):
        tracker.observe({"transaction_id": i, "is_response": False, "query_name": "a.com",
                          "query_type": "A"}, timestamp=0)
        tracker.observe({"transaction_id": i, "is_response": True, "query_name": "a.com",
                          "query_type": "A", "response_code": "NOERROR", "answers": []},
                         timestamp=0.1)
    top = tracker.most_requested_domains(5)
    assert top[0]["domain"] == "a.com"
    assert top[0]["count"] == 3
