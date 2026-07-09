"""Live packet capture and PCAP file I/O, built on Scapy.

Scapy sniffing requires elevated privileges (root/administrator or a
capabilities grant on Linux) on most platforms. This module fails
gracefully with a clear error message when it isn't available, and
always supports offline analysis by reading existing PCAP files.
"""
from __future__ import annotations

from typing import Callable, Iterable, List, Optional

from utils.logger import get_logger

log = get_logger(__name__)

try:
    from scapy.all import sniff, wrpcap, rdpcap, get_if_list
    _SCAPY_AVAILABLE = True
except Exception as exc:  # pragma: no cover - environment dependent
    _SCAPY_AVAILABLE = False
    _SCAPY_IMPORT_ERROR = exc


class PacketCaptureError(RuntimeError):
    pass


class PacketCapture:
    """Wraps Scapy's sniff/rdpcap/wrpcap with sane defaults and error
    handling suited for the analyzer's CLI and dashboard.
    """

    def __init__(
        self,
        interface: Optional[str] = None,
        bpf_filter: str = "",
        packet_count: int = 0,
        timeout: Optional[int] = None,
    ) -> None:
        self.interface = interface
        self.bpf_filter = bpf_filter
        self.packet_count = packet_count
        self.timeout = timeout
        self._packets: List = []

    @staticmethod
    def list_interfaces() -> List[str]:
        if not _SCAPY_AVAILABLE:
            raise PacketCaptureError(
                f"Scapy is unavailable: {_SCAPY_IMPORT_ERROR}"
            )
        return get_if_list()

    def capture_live(self, on_packet: Optional[Callable] = None) -> List:
        """Capture packets from the configured interface.

        Args:
            on_packet: Optional callback invoked with each raw packet as
                it's captured, useful for streaming to a parser/dashboard.

        Returns:
            The list of captured raw Scapy packets.
        """
        if not _SCAPY_AVAILABLE:
            raise PacketCaptureError(
                "Scapy is unavailable or lacks capture privileges "
                f"({_SCAPY_IMPORT_ERROR}). Run with sufficient privileges "
                "(e.g. sudo) or use capture_from_file() for offline analysis."
            )

        self._packets = []

        def _handler(pkt):
            self._packets.append(pkt)
            if on_packet:
                on_packet(pkt)

        log.info(
            "Starting live capture on interface=%s filter=%r count=%s timeout=%s",
            self.interface, self.bpf_filter, self.packet_count, self.timeout,
        )

        try:
            sniff(
                iface=self.interface,
                filter=self.bpf_filter or None,
                prn=_handler,
                count=self.packet_count or 0,
                timeout=self.timeout,
                store=False,
            )
        except PermissionError as exc:
            raise PacketCaptureError(
                "Insufficient privileges to capture packets. "
                "Try running with sudo/administrator rights."
            ) from exc
        except OSError as exc:
            raise PacketCaptureError(f"Capture failed: {exc}") from exc

        log.info("Capture finished: %d packets captured", len(self._packets))
        return self._packets

    def capture_from_file(self, pcap_path: str) -> List:
        """Read packets from an existing PCAP file for offline analysis."""
        if not _SCAPY_AVAILABLE:
            raise PacketCaptureError(
                f"Scapy is unavailable: {_SCAPY_IMPORT_ERROR}"
            )
        log.info("Reading packets from PCAP file: %s", pcap_path)
        self._packets = list(rdpcap(pcap_path))
        log.info("Loaded %d packets from %s", len(self._packets), pcap_path)
        return self._packets

    def save_to_pcap(self, path: str, packets: Optional[Iterable] = None) -> None:
        """Persist captured (or provided) packets to a PCAP file."""
        if not _SCAPY_AVAILABLE:
            raise PacketCaptureError(
                f"Scapy is unavailable: {_SCAPY_IMPORT_ERROR}"
            )
        pkts = list(packets) if packets is not None else self._packets
        wrpcap(path, pkts)
        log.info("Saved %d packets to %s", len(pkts), path)

    @property
    def packets(self) -> List:
        return self._packets
