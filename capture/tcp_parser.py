"""Parses TCP-layer fields from a Scapy packet into a plain dict."""
from __future__ import annotations

from typing import Any, Dict, Optional

# TCP flag bit -> mnemonic
_TCP_FLAG_BITS = (
    ("FIN", 0x01),
    ("SYN", 0x02),
    ("RST", 0x04),
    ("PSH", 0x08),
    ("ACK", 0x10),
    ("URG", 0x20),
    ("ECE", 0x40),
    ("CWR", 0x80),
)


def decode_flags(flag_value: int) -> str:
    """Convert a numeric TCP flags field into a mnemonic string, e.g. 'SYN,ACK'."""
    names = [name for name, bit in _TCP_FLAG_BITS if flag_value & bit]
    return ",".join(names) if names else "-"


def parse_tcp(packet: Any) -> Optional[Dict]:
    """Extract TCP fields from a Scapy packet. Returns None if no TCP layer."""
    if not packet.haslayer("TCP"):
        return None

    tcp = packet["TCP"]
    ip = packet["IP"] if packet.haslayer("IP") else None

    flags_raw = int(tcp.flags)
    return {
        "protocol": "TCP",
        "src_ip": ip.src if ip else None,
        "dst_ip": ip.dst if ip else None,
        "src_port": int(tcp.sport),
        "dst_port": int(tcp.dport),
        "flags": decode_flags(flags_raw),
        "flags_raw": flags_raw,
        "seq": int(tcp.seq),
        "ack": int(tcp.ack),
        "window": int(tcp.window),
        "is_retransmission": False,  # set by higher-level stateful analysis
    }


class TcpStreamTracker:
    """Tracks per-connection sequence numbers to flag likely retransmissions."""

    def __init__(self) -> None:
        self._seen_seqs: Dict[tuple, set] = {}

    def _key(self, fields: Dict) -> tuple:
        return (fields["src_ip"], fields["src_port"], fields["dst_ip"], fields["dst_port"])

    def observe(self, fields: Dict) -> Dict:
        key = self._key(fields)
        seqs = self._seen_seqs.setdefault(key, set())

        fields["is_retransmission"] = (
            fields["seq"] in seqs
            and fields.get("flags") not in ("SYN", "SYN,ACK")
        )

        seqs.add(fields["seq"])
        return fields
