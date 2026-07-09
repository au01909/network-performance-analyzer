"""Chart generation for HTML reports.

Uses matplotlib to render static PNG charts (base64-embedded so the HTML
report is a single self-contained file with no external asset files).
"""
from __future__ import annotations

import base64
import io
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")  # headless rendering, no display server required
import matplotlib.pyplot as plt


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def latency_distribution_chart(latencies_ms: List[float]) -> str:
    """Histogram of request latencies (ms). Returns a base64 PNG string."""
    fig, ax = plt.subplots(figsize=(7, 4))
    if latencies_ms:
        ax.hist(latencies_ms, bins=min(30, max(5, len(latencies_ms) // 5 or 1)),
                color="#4C6EF5", edgecolor="white")
    ax.set_title("Latency Distribution")
    ax.set_xlabel("Response Time (ms)")
    ax.set_ylabel("Request Count")
    fig.tight_layout()
    return _fig_to_base64(fig)


def throughput_over_time_chart(timeline: List[Dict]) -> str:
    """Line chart of requests/sec over the test duration."""
    fig, ax = plt.subplots(figsize=(7, 4))
    if timeline:
        t0 = timeline[0]["time"]
        xs = [p["time"] - t0 for p in timeline]
        ys = [p["requests_per_sec"] for p in timeline]
        ax.plot(xs, ys, color="#12B886", linewidth=2)
        ax.fill_between(xs, ys, color="#12B886", alpha=0.15)
    ax.set_title("Throughput Over Time")
    ax.set_xlabel("Elapsed (s)")
    ax.set_ylabel("Requests / sec")
    fig.tight_layout()
    return _fig_to_base64(fig)


def latency_percentile_bar_chart(p50: float, p90: float, p95: float, p99: float) -> str:
    fig, ax = plt.subplots(figsize=(5, 4))
    labels = ["P50", "P90", "P95", "P99"]
    values = [p50 * 1000, p90 * 1000, p95 * 1000, p99 * 1000]
    colors = ["#4C6EF5", "#82C91E", "#F59F00", "#E03131"]
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("Response Time (ms)")
    ax.set_title("Latency Percentiles")
    fig.tight_layout()
    return _fig_to_base64(fig)


def error_breakdown_pie_chart(successful: int, failed: int) -> str:
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    if successful + failed > 0:
        ax.pie(
            [successful, failed],
            labels=["Success", "Failed"],
            colors=["#12B886", "#E03131"],
            autopct="%1.1f%%",
            startangle=90,
        )
    ax.set_title("Success vs Failure")
    fig.tight_layout()
    return _fig_to_base64(fig)
