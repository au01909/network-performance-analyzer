import math
from utils.helpers import percentile, mean, median, safe_div, human_bytes


def test_percentile_basic():
    data = [1, 2, 3, 4, 5]
    assert percentile(data, 0) == 1
    assert percentile(data, 100) == 5
    assert percentile(data, 50) == 3


def test_percentile_empty():
    assert percentile([], 90) == 0.0


def test_mean_median():
    data = [1, 2, 3, 4, 5]
    assert mean(data) == 3
    assert median(data) == 3


def test_safe_div():
    assert safe_div(10, 2) == 5
    assert safe_div(10, 0) == 0.0


def test_human_bytes():
    assert human_bytes(500).endswith("B")
    assert "KB" in human_bytes(2048)
