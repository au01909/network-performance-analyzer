"""Flask dashboard: exposes live load-test metrics over HTTP and renders
a simple auto-refreshing dashboard page with live graphs.

The dashboard reads from whatever LoadTestScheduler / MetricsEngine
instance is registered via `register_scheduler()`. When run standalone
(e.g. `python -m dashboard.app`) without a live test attached, it starts
a demo scheduler that hits httpbin-style local loopback data instead so
the UI can still be exercised.
"""
from __future__ import annotations

import time
from dataclasses import asdict
from typing import Optional

import psutil  # optional dependency for CPU/memory; degrades gracefully
from flask import Flask, jsonify, render_template

from load_testing.scheduler import LoadTestScheduler
from utils.logger import get_logger

log = get_logger(__name__)

app = Flask(__name__)

_scheduler: Optional[LoadTestScheduler] = None
_dns_tracker = None
_start_time = time.time()


def register_scheduler(scheduler: LoadTestScheduler) -> None:
    """Attach a running LoadTestScheduler so the dashboard can report its
    live metrics. Call this before starting the Flask app.
    """
    global _scheduler
    _scheduler = scheduler


def register_dns_tracker(tracker) -> None:
    global _dns_tracker
    _dns_tracker = tracker


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/metrics")
def api_metrics():
    if _scheduler is None:
        return jsonify({"error": "no active load test"}), 404

    snapshot = _scheduler.metrics.snapshot()
    payload = asdict(snapshot)

    try:
        payload["cpu_percent"] = psutil.cpu_percent(interval=None)
        payload["memory_percent"] = psutil.virtual_memory().percent
    except Exception:
        payload["cpu_percent"] = None
        payload["memory_percent"] = None

    payload["uptime_seconds"] = time.time() - _start_time
    return jsonify(payload)


@app.route("/api/timeline")
def api_timeline():
    if _scheduler is None:
        return jsonify([])
    return jsonify(_scheduler.stats.timeline)


@app.route("/api/dns")
def api_dns():
    if _dns_tracker is None:
        return jsonify({"most_requested": [], "slowest": []})
    return jsonify({
        "most_requested": _dns_tracker.most_requested_domains(),
        "slowest": _dns_tracker.slowest_lookups(),
    })


def run_dashboard(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    log.info("Starting dashboard on http://%s:%d", host, port)
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    run_dashboard(debug=True)
