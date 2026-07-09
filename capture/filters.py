"""Helpers for building BPF (Berkeley Packet Filter) capture filter strings."""
from __future__ import annotations

from typing import List, Optional


def build_bpf_filter(
    protocols: Optional[List[str]] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    extra: Optional[str] = None,
) -> str:
    """Compose a BPF filter string from common building blocks.

    Example:
        build_bpf_filter(protocols=["tcp", "udp"], host="10.0.0.5", port=443)
        -> "(tcp or udp) and host 10.0.0.5 and port 443"
    """
    clauses = []

    if protocols:
        proto_clause = " or ".join(protocols)
        clauses.append(f"({proto_clause})" if len(protocols) > 1 else proto_clause)

    if host:
        clauses.append(f"host {host}")

    if port:
        clauses.append(f"port {port}")

    if extra:
        clauses.append(extra)

    return " and ".join(clauses)


PRESET_FILTERS = {
    "http": "tcp port 80",
    "https": "tcp port 443",
    "dns": "udp port 53 or tcp port 53",
    "web": "tcp port 80 or tcp port 443",
    "icmp": "icmp",
    "arp": "arp",
}
