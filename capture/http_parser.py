"""Parses HTTP request/response fields out of raw TCP payloads.

Scapy does not fully decode HTTP by default (it depends on layers not
always loaded), so this module works directly on the raw TCP payload
bytes using a lightweight manual parse of the HTTP/1.x wire format.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

_REQUEST_LINE_RE = re.compile(rb"^([A-Z]+) (\S+) HTTP/(\d\.\d)")
_RESPONSE_LINE_RE = re.compile(rb"^HTTP/(\d\.\d) (\d{3}) ")


def _parse_headers(raw_headers: bytes) -> Dict[str, str]:
    headers = {}
    for line in raw_headers.split(b"\r\n"):
        if b":" not in line:
            continue
        key, _, value = line.partition(b":")
        headers[key.decode(errors="ignore").strip()] = value.decode(errors="ignore").strip()
    return headers


def parse_http(packet: Any) -> Optional[Dict]:
    """Attempt to extract an HTTP request or response from a packet's raw
    TCP payload. Returns None if the payload isn't recognizable HTTP.
    """
    if not packet.haslayer("TCP") or not packet.haslayer("Raw"):
        return None

    payload: bytes = bytes(packet["Raw"].load)
    head, _, rest = payload.partition(b"\r\n")

    req_match = _REQUEST_LINE_RE.match(head)
    resp_match = _RESPONSE_LINE_RE.match(head)

    if not req_match and not resp_match:
        return None

    header_block, _, _body = rest.partition(b"\r\n\r\n")
    headers = _parse_headers(header_block)

    ip = packet["IP"] if packet.haslayer("IP") else None
    tcp = packet["TCP"]

    base = {
        "src_ip": ip.src if ip else None,
        "dst_ip": ip.dst if ip else None,
        "src_port": int(tcp.sport),
        "dst_port": int(tcp.dport),
        "headers": headers,
        "content_length": int(headers.get("Content-Length", 0) or 0),
        "capture_time": time.time(),
    }

    if req_match:
        method, url, version = req_match.groups()
        base.update({
            "protocol": "HTTP",
            "type": "request",
            "method": method.decode(),
            "url": url.decode(),
            "http_version": version.decode(),
        })
    else:
        version, status_code = resp_match.groups()
        base.update({
            "protocol": "HTTP",
            "type": "response",
            "http_version": version.decode(),
            "status_code": int(status_code),
        })

    return base


class HttpExchangeTracker:
    """Correlates HTTP requests with responses on the same TCP connection
    to compute response times, error rates, and slow-request lists.
    """

    def __init__(self, slow_threshold_seconds: float = 1.0) -> None:
        self._pending: Dict[tuple, Dict] = {}
        self.exchanges: List[Dict] = []
        self.slow_threshold_seconds = slow_threshold_seconds

    def _key(self, fields: Dict) -> tuple:
        # Requests go src->dst; responses come back dst->src on same ports.
        if fields["type"] == "request":
            return (fields["src_ip"], fields["src_port"], fields["dst_ip"], fields["dst_port"])
        return (fields["dst_ip"], fields["dst_port"], fields["src_ip"], fields["src_port"])

    def observe(self, fields: Dict) -> Optional[Dict]:
        key = self._key(fields)
        if fields["type"] == "request":
            self._pending[key] = fields
            return None

        request = self._pending.pop(key, None)
        response_time = None
        if request is not None:
            response_time = fields["capture_time"] - request["capture_time"]

        exchange = {
            "method": request.get("method") if request else None,
            "url": request.get("url") if request else None,
            "status_code": fields.get("status_code"),
            "content_length": fields.get("content_length"),
            "response_time": response_time,
            "is_slow": bool(response_time and response_time > self.slow_threshold_seconds),
            "is_error": bool(fields.get("status_code", 0) >= 400),
        }
        self.exchanges.append(exchange)
        return exchange

    def summary(self) -> Dict:
        total = len(self.exchanges)
        if total == 0:
            return {"total_requests": 0, "avg_response_time": 0.0, "success_rate": 0.0,
                    "error_rate": 0.0, "slow_requests": 0}

        errors = sum(1 for e in self.exchanges if e["is_error"])
        times = [e["response_time"] for e in self.exchanges if e["response_time"] is not None]
        avg_time = sum(times) / len(times) if times else 0.0

        return {
            "total_requests": total,
            "avg_response_time": avg_time,
            "success_rate": (total - errors) / total,
            "error_rate": errors / total,
            "slow_requests": sum(1 for e in self.exchanges if e["is_slow"]),
        }
