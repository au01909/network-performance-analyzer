"""Integration test: verifies the Flask dashboard serves metrics from a
live-attached scheduler's MetricsEngine.
"""
import time

from dashboard.app import app, register_scheduler
from load_testing.metrics import MetricsEngine
from load_testing.statistics import StatisticsRecorder


class _FakeScheduler:
    def __init__(self):
        self.metrics = MetricsEngine()
        self.stats = StatisticsRecorder(self.metrics, interval_seconds=0.1)


def test_dashboard_endpoints_serve_live_metrics():
    fake = _FakeScheduler()
    fake.metrics.record({"success": True, "status_code": 200, "response_time": 0.05,
                          "error": None, "bytes_received": 200})
    fake.stats.start()
    time.sleep(0.3)
    register_scheduler(fake)

    client = app.test_client()
    assert client.get("/").status_code == 200

    metrics_resp = client.get("/api/metrics")
    assert metrics_resp.status_code == 200
    data = metrics_resp.get_json()
    assert data["total_requests"] == 1

    timeline_resp = client.get("/api/timeline")
    assert timeline_resp.status_code == 200
    assert len(timeline_resp.get_json()) > 0

    fake.stats.stop()
