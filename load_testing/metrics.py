"""Metrics engine: aggregates raw HttpResult records into latency,
throughput, and error statistics used for reporting and the dashboard.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List

from utils.helpers import percentile, mean, median, safe_div


@dataclass
class MetricsSnapshot:
    total_requests: int
    successful_requests: int
    failed_requests: int
    latency_min: float
    latency_max: float
    latency_avg: float
    latency_median: float
    p50: float
    p90: float
    p95: float
    p99: float
    requests_per_sec: float
    bytes_per_sec: float
    error_rate: float
    timeout_count: int
    connection_failures: int
    dns_failures: int
    elapsed_seconds: float


class MetricsEngine:
    """Thread-safe accumulator for load-test results.

    Workers call `record()` as results come in; the dashboard/report code
    calls `snapshot()` at any time to get a consistent point-in-time view.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._results: List[Dict] = []
        self._start_time = time.perf_counter()

    def record(self, result: Dict) -> None:
        with self._lock:
            self._results.append(result)

    def reset(self) -> None:
        with self._lock:
            self._results = []
            self._start_time = time.perf_counter()

    @property
    def raw_results(self) -> List[Dict]:
        with self._lock:
            return list(self._results)

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            results = list(self._results)
            elapsed = max(time.perf_counter() - self._start_time, 1e-9)

        total = len(results)
        successes = [r for r in results if r.get("success")]
        failures = [r for r in results if not r.get("success")]
        latencies = [r["response_time"] for r in results if r.get("response_time") is not None]
        total_bytes = sum(r.get("bytes_received") or 0 for r in results)

        timeouts = sum(1 for r in failures if (r.get("error") or "").startswith("timeout"))
        conn_failures = sum(1 for r in failures if (r.get("error") or "").startswith("connection_error"))
        dns_failures = sum(1 for r in failures if "name resolution" in (r.get("error") or "").lower()
                            or "dns" in (r.get("error") or "").lower())

        return MetricsSnapshot(
            total_requests=total,
            successful_requests=len(successes),
            failed_requests=len(failures),
            latency_min=min(latencies) if latencies else 0.0,
            latency_max=max(latencies) if latencies else 0.0,
            latency_avg=mean(latencies),
            latency_median=median(latencies),
            p50=percentile(latencies, 50),
            p90=percentile(latencies, 90),
            p95=percentile(latencies, 95),
            p99=percentile(latencies, 99),
            requests_per_sec=safe_div(total, elapsed),
            bytes_per_sec=safe_div(total_bytes, elapsed),
            error_rate=safe_div(len(failures), total),
            timeout_count=timeouts,
            connection_failures=conn_failures,
            dns_failures=dns_failures,
            elapsed_seconds=elapsed,
        )
