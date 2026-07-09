"""Thin wrapper around `requests` that times each HTTP call and normalizes
the result (or failure) into a plain dict suitable for metrics aggregation.
"""
from __future__ import annotations

import time
from typing import Dict, Optional

import requests

from utils.logger import get_logger

log = get_logger(__name__)


class HttpResult:
    __slots__ = (
        "success", "status_code", "response_time", "error", "bytes_received",
        "url", "method", "timestamp",
    )

    def __init__(self, success, status_code, response_time, error, bytes_received, url, method, timestamp):
        self.success = success
        self.status_code = status_code
        self.response_time = response_time
        self.error = error
        self.bytes_received = bytes_received
        self.url = url
        self.method = method
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        return {slot: getattr(self, slot) for slot in self.__slots__}


class HttpClient:
    """Executes a single configured HTTP request and returns timing/result info.

    A fresh `requests.Session` is created per-thread by the caller (see
    load_testing.worker) to avoid cross-thread session contention.
    """

    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.url = url
        self.method = method.upper()
        self.headers = dict(headers or {})
        if auth_token:
            self.headers.setdefault("Authorization", f"Bearer {auth_token}")
        self.body = body
        self.timeout = timeout
        self.session = session or requests.Session()

    def execute(self) -> HttpResult:
        start = time.perf_counter()
        timestamp = time.time()
        try:
            response = self.session.request(
                method=self.method,
                url=self.url,
                headers=self.headers,
                data=self.body,
                timeout=self.timeout,
            )
            elapsed = time.perf_counter() - start
            return HttpResult(
                success=response.status_code < 400,
                status_code=response.status_code,
                response_time=elapsed,
                error=None,
                bytes_received=len(response.content or b""),
                url=self.url,
                method=self.method,
                timestamp=timestamp,
            )
        except requests.exceptions.Timeout as exc:
            elapsed = time.perf_counter() - start
            return HttpResult(False, None, elapsed, f"timeout: {exc}", 0, self.url, self.method, timestamp)
        except requests.exceptions.ConnectionError as exc:
            elapsed = time.perf_counter() - start
            return HttpResult(False, None, elapsed, f"connection_error: {exc}", 0, self.url, self.method, timestamp)
        except requests.exceptions.RequestException as exc:
            elapsed = time.perf_counter() - start
            return HttpResult(False, None, elapsed, f"request_error: {exc}", 0, self.url, self.method, timestamp)
