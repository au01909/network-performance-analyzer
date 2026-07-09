"""Parses DNS query/response fields from a Scapy packet."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_RCODE_NAMES = {
    0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN",
    4: "NOTIMP", 5: "REFUSED",
}

_QTYPE_NAMES = {
    1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR",
    15: "MX", 16: "TXT", 28: "AAAA", 33: "SRV",
}


def parse_dns(packet: Any) -> Optional[Dict]:
    """Extract DNS fields from a Scapy packet. Returns None if no DNS layer."""
    if not packet.haslayer("DNS"):
        return None

    dns = packet["DNS"]
    is_response = bool(dns.qr == 1)

    query_name = None
    query_type = None
    if dns.qd is not None and dns.qdcount:
        try:
            query_name = dns.qd.qname.decode(errors="ignore").rstrip(".")
            query_type = _QTYPE_NAMES.get(int(dns.qd.qtype), str(dns.qd.qtype))
        except Exception:
            pass

    answers: List[str] = []
    if is_response and dns.an:
        for i in range(dns.ancount):
            try:
                rr = dns.an[i]
                answers.append(str(rr.rdata))
            except Exception:
                continue

    return {
        "protocol": "DNS",
        "is_response": is_response,
        "transaction_id": int(dns.id),
        "query_name": query_name,
        "query_type": query_type,
        "response_code": _RCODE_NAMES.get(int(dns.rcode), str(dns.rcode)) if is_response else None,
        "answers": answers,
        "capture_time": time.time(),
    }


class DnsLatencyTracker:
    """Pairs DNS queries with their responses (by transaction id) to
    compute per-lookup response time and aggregate stats."""

    def __init__(self) -> None:
        self._pending: Dict[int, float] = {}
        self.completed: List[Dict] = []

    def observe(self, dns_fields: Dict, timestamp: float) -> None:
        txid = dns_fields["transaction_id"]
        if not dns_fields["is_response"]:
            self._pending[txid] = timestamp
            return

        start = self._pending.pop(txid, None)
        response_time = (timestamp - start) if start is not None else None
        self.completed.append({
            **dns_fields,
            "response_time": response_time,
        })

    def most_requested_domains(self, top_n: int = 10) -> List[Dict]:
        counts: Dict[str, int] = {}
        for entry in self.completed:
            name = entry.get("query_name")
            if name:
                counts[name] = counts.get(name, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        return [{"domain": d, "count": c} for d, c in ranked[:top_n]]

    def slowest_lookups(self, top_n: int = 10) -> List[Dict]:
        timed = [e for e in self.completed if e.get("response_time") is not None]
        ranked = sorted(timed, key=lambda e: e["response_time"], reverse=True)
        return ranked[:top_n]
