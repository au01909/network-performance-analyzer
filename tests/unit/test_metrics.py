from load_testing.metrics import MetricsEngine


def test_metrics_engine_empty_snapshot():
    engine = MetricsEngine()
    snap = engine.snapshot()
    assert snap.total_requests == 0
    assert snap.error_rate == 0.0


def test_metrics_engine_records_and_computes():
    engine = MetricsEngine()
    for i in range(10):
        engine.record({
            "success": i < 8,
            "status_code": 200 if i < 8 else 500,
            "response_time": 0.1 + i * 0.01,
            "error": None if i < 8 else "server_error",
            "bytes_received": 100,
        })
    snap = engine.snapshot()
    assert snap.total_requests == 10
    assert snap.successful_requests == 8
    assert snap.failed_requests == 2
    assert 0.0 < snap.error_rate < 1.0
    assert snap.latency_min <= snap.latency_avg <= snap.latency_max
