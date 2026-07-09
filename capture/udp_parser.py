"""Parses UDP-layer fields from a Scapy packet into a plain dict."""
from __future__ import annotations

from typing import Any, Dict, Optional


def parse_udp(packet: Any) -> Optional[Dict]:
    """Extract UDP fields from a Scapy packet. Returns None if no UDP layer."""
    if not packet.haslayer("UDP"):
        return None

    udp = packet["UDP"]
    ip = packet["IP"] if packet.haslayer("IP") else None

    return {
        "protocol": "UDP",
        "src_ip": ip.src if ip else None,
        "dst_ip": ip.dst if ip else None,
        "src_port": int(udp.sport),
        "dst_port": int(udp.dport),
        "length": int(udp.len),
    }
