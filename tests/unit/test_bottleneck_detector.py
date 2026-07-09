from analysis.bottleneck_detector import BottleneckDetector
from load_testing.metrics import MetricsEngine


def test_no_findings_for_healthy_metrics():
    engine = MetricsEngine()
    for _ in range(50):
        engine.record({"success": True, "status_code": 200, "response_time": 0.05,
                        "error": None, "bytes_received": 100})
    snap = engine.snapshot()
    detector = BottleneckDetector()
    findings = detector.analyze_http_metrics(snap)
    assert findings == []


def test_findings_for_high_error_rate():
    engine = MetricsEngine()
    for i in range(50):
        success = i % 2 == 0  # 50% errors
        engine.record({"success": success, "status_code": 200 if success else 500,
                        "response_time": 0.05, "error": None if success else "server_error",
                        "bytes_received": 100})
    snap = engine.snapshot()
    detector = BottleneckDetector()
    findings = detector.analyze_http_metrics(snap)
    assert any(f.category == "errors" and f.severity == "critical" for f in findings)


def test_tcp_retransmission_detection():
    detector = BottleneckDetector()
    tcp_records = [{"is_retransmission": i % 5 == 0} for i in range(100)]
    findings = detector.analyze_tcp_retransmissions(tcp_records)
    assert len(findings) == 1
    assert findings[0].category == "packet_loss"
