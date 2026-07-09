"""Top-level packet parser: dispatches a raw Scapy packet to the correct
protocol-specific parser and returns a normalized dict of fields common
to every packet, plus protocol-specific details nested under 'details'.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from capture.tcp_parser import parse_tcp, TcpStreamTracker
from capture.udp_parser import parse_udp
from capture.dns_parser import parse_dns
from capture.http_parser import parse_http
from utils.logger import get_logger

log = get_logger(__name__)


class PacketParser:
    """Stateful packet parser: maintains TCP stream tracking across calls
    while parsing packets into a normalized record structure.
    """

    def __init__(self) -> None:
        self._tcp_tracker = TcpStreamTracker()

    def parse(self, packet: Any) -> Dict[str, Any]:
        """Parse a single Scapy packet into a normalized record dict.

        Always returns a base record; unparsable/unsupported packets
        still get IP/size/timestamp info with protocol='OTHER'.
        """
        record: Dict[str, Any] = {
            "timestamp": getattr(packet, "time", time.time()),
            "size": len(packet),
            "protocol": "OTHER",
        }

        if packet.haslayer("IP"):
            ip = packet["IP"]
            record["src_ip"] = ip.src
            record["dst_ip"] = ip.dst
            record["ttl"] = int(ip.ttl)
        elif packet.haslayer("ARP"):
            arp = packet["ARP"]
            record["protocol"] = "ARP"
            record["src_ip"] = arp.psrc
            record["dst_ip"] = arp.pdst
            return record
        else:
            return record

        try:
            dns_fields = parse_dns(packet)
            if dns_fields:
                record["protocol"] = "DNS"
                record["details"] = dns_fields
                return record
        except Exception as exc:
            log.debug("DNS parse failed: %s", exc)

        try:
            http_fields = parse_http(packet)
            if http_fields:
                record["protocol"] = "HTTP"
                record["details"] = http_fields
                return record
        except Exception as exc:
            log.debug("HTTP parse failed: %s", exc)

        try:
            tcp_fields = parse_tcp(packet)
            if tcp_fields:
                tcp_fields = self._tcp_tracker.observe(tcp_fields)
                record["protocol"] = "TCP"
                record["details"] = tcp_fields
                return record
        except Exception as exc:
            log.debug("TCP parse failed: %s", exc)

        try:
            udp_fields = parse_udp(packet)
            if udp_fields:
                record["protocol"] = "UDP"
                record["details"] = udp_fields
                return record
        except Exception as exc:
            log.debug("UDP parse failed: %s", exc)

        if packet.haslayer("ICMP"):
            record["protocol"] = "ICMP"

        return record
