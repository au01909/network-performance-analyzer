"""Aggregate statistics storage: keeps a rolling time series of metrics
snapshots so reports/dashboards can show trends over the test duration,
not just a final summary.
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict
from typing import Dict, List

from load_testing.metrics import MetricsEngine, MetricsSnapshot


class StatisticsRecorder:
    """Periodically snapshots a MetricsEngine on a background thread so a
    time series of throughput/latency is available for charts.
    """

    def __init__(self, metrics_engine: MetricsEngine, interval_seconds: float = 1.0) -> None:
        self.metrics_engine = metrics_engine
        self.interval_seconds = interval_seconds
        self._timeline: List[Dict] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval_seconds * 2)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._record_point()
            self._stop_event.wait(self.interval_seconds)
        self._record_point()  # final point

    def _record_point(self) -> None:
        snap: MetricsSnapshot = self.metrics_engine.snapshot()
        point = {"time": time.time(), **asdict(snap)}
        with self._lock:
            self._timeline.append(point)

    @property
    def timeline(self) -> List[Dict]:
        with self._lock:
            return list(self._timeline)
