"""Small stateless helper functions shared across modules."""
from __future__ import annotations

import math
import statistics
import time
from typing import Iterable, List


def percentile(values: Iterable[float], pct: float) -> float:
    """Compute the pct-th percentile (0-100) using linear interpolation
    between closest ranks (equivalent to numpy's default 'linear' method).
    """
    data = sorted(values)
    if not data:
        return 0.0
    if pct <= 0:
        return data[0]
    if pct >= 100:
        return data[-1]

    k = (len(data) - 1) * (pct / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return d0 + d1


def mean(values: Iterable[float]) -> float:
    data = list(values)
    return statistics.mean(data) if data else 0.0


def median(values: Iterable[float]) -> float:
    data = list(values)
    return statistics.median(data) if data else 0.0


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


class Timer:
    """Simple context-manager stopwatch returning elapsed seconds."""

    def __enter__(self):
        self._start = time.perf_counter()
        self.elapsed = 0.0
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self._start
        return False


def human_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}PB"


def chunk(lst: List, size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]
