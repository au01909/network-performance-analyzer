"""Integration test: runs a real small load test against a local
http.server instance and validates the metrics/report pipeline end-to-end.
"""
import http.server
import socketserver
import threading
import time

import pytest

from load_testing.scheduler import LoadTestScheduler
from utils.config import LoadTestConfig
from analysis.bottleneck_detector import BottleneckDetector
from reports.json_report import build_json_report, write_json_report
from reports.csv_report import write_csv_report


@pytest.fixture(scope="module")
def local_server():
    handler = http.server.SimpleHTTPRequestHandler
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)
    yield f"http://127.0.0.1:{port}/"
    server.shutdown()


def test_full_load_test_and_report_pipeline(local_server, tmp_path):
    config = LoadTestConfig(url=local_server, users=3, duration_seconds=1.0)
    scheduler = LoadTestScheduler(config, stats_interval=0.2)

    metrics_engine = scheduler.run()
    snapshot = metrics_engine.snapshot()

    assert snapshot.total_requests > 0
    assert snapshot.error_rate == 0.0

    detector = BottleneckDetector()
    detector.analyze_http_metrics(snapshot)
    summary = detector.summary()

    report = build_json_report(snapshot, metrics_engine.raw_results,
                                scheduler.stats.timeline, summary, {"target": local_server})
    json_path = write_json_report(str(tmp_path / "report.json"), report)
    csv_path = write_csv_report(str(tmp_path / "report.csv"), metrics_engine.raw_results)

    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.csv").exists()
