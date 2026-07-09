#!/usr/bin/env python3
"""Command-line entry point for the Network Performance Analyzer &
HTTP Load Testing Framework.

Subcommands:
    capture     Capture live packets or analyze an existing PCAP file.
    loadtest    Run a configurable concurrent HTTP load test.
    dashboard   Launch a Flask dashboard attached to a live load test.
    sockets     Run TCP/UDP echo-server demos and client timing tests.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from datetime import datetime, timezone

from analysis.bottleneck_detector import BottleneckDetector
from capture.dns_parser import DnsLatencyTracker
from capture.http_parser import HttpExchangeTracker
from capture.packet_capture import PacketCapture, PacketCaptureError
from capture.packet_parser import PacketParser
from load_testing.scheduler import LoadTestScheduler
from reports.csv_report import write_csv_report
from reports.html_report import render_html_report, write_html_report
from reports.json_report import build_json_report, write_json_report
from sockets.tcp_udp import (
    TcpEchoServer, UdpEchoServer, tcp_client_echo, udp_client_echo,
)
from utils.config import AppConfig, CaptureConfig, LoadTestConfig
from utils.logger import get_logger, setup_logging

log = get_logger("cli")


def cmd_capture(args: argparse.Namespace) -> None:
    parser = PacketParser()
    dns_tracker = DnsLatencyTracker()
    http_tracker = HttpExchangeTracker()
    bottleneck = BottleneckDetector()

    tcp_records = []
    protocol_counts = {}

    def handle_record(record: dict) -> None:
        proto = record.get("protocol", "OTHER")
        protocol_counts[proto] = protocol_counts.get(proto, 0) + 1
        if proto == "DNS":
            dns_tracker.observe(record["details"], record["timestamp"])
        elif proto == "HTTP":
            http_tracker.observe(record["details"])
        elif proto == "TCP":
            tcp_records.append(record["details"])

    capture = PacketCapture(
        interface=args.interface,
        bpf_filter=args.filter or "",
        packet_count=args.count,
        timeout=args.duration,
    )

    try:
        if args.pcap_in:
            packets = capture.capture_from_file(args.pcap_in)
        else:
            packets = capture.capture_live()
        for pkt in packets:
            handle_record(parser.parse(pkt))
    except PacketCaptureError as exc:
        log.error(str(exc))
        sys.exit(1)

    if args.pcap_out:
        capture.save_to_pcap(args.pcap_out)

    bottleneck.analyze_tcp_retransmissions(tcp_records)
    bottleneck.analyze_dns(dns_tracker.completed)

    print("\n=== Capture Summary ===")
    print(f"Total packets:      {len(packets)}")
    print(f"Protocol counts:    {json.dumps(protocol_counts, indent=2)}")
    print(f"HTTP summary:       {json.dumps(http_tracker.summary(), indent=2)}")
    print(f"Top domains:        {dns_tracker.most_requested_domains(5)}")
    print(f"Bottleneck findings: {bottleneck.summary()['total_findings']}")
    for f in bottleneck.findings:
        print(f"  [{f.severity.upper()}] {f.category}: {f.message}")


def cmd_loadtest(args: argparse.Namespace) -> None:
    config = LoadTestConfig(
        url=args.url,
        method=args.method,
        headers=dict(h.split(":", 1) for h in (args.header or [])),
        body=args.body,
        auth_token=args.auth_token,
        users=args.users,
        ramp_up_seconds=args.ramp_up,
        duration_seconds=args.duration,
        request_timeout=args.timeout,
        think_time=args.think_time,
    )

    scheduler = LoadTestScheduler(config)

    if args.dashboard:
        from dashboard.app import register_scheduler, run_dashboard
        register_scheduler(scheduler)
        threading.Thread(
            target=run_dashboard,
            kwargs={"host": args.dashboard_host, "port": args.dashboard_port},
            daemon=True,
        ).start()
        log.info("Dashboard available at http://%s:%d", args.dashboard_host, args.dashboard_port)
        time.sleep(0.5)

    metrics_engine = scheduler.run()
    snapshot = metrics_engine.snapshot()

    bottleneck = BottleneckDetector()
    bottleneck.analyze_http_metrics(snapshot)

    print("\n=== Load Test Summary ===")
    print(f"Total Requests:     {snapshot.total_requests}")
    print(f"Successful:         {snapshot.successful_requests}")
    print(f"Failed:              {snapshot.failed_requests}")
    print(f"Requests/sec:       {snapshot.requests_per_sec:.2f}")
    print(f"Latency avg/p50/p95/p99 (ms): "
          f"{snapshot.latency_avg*1000:.1f} / {snapshot.p50*1000:.1f} / "
          f"{snapshot.p95*1000:.1f} / {snapshot.p99*1000:.1f}")
    print(f"Error rate:         {snapshot.error_rate:.2%}")

    for f in bottleneck.findings:
        print(f"  [{f.severity.upper()}] {f.category}: {f.message}")
        print(f"      -> {f.recommendation}")

    _write_reports(args, snapshot, metrics_engine.raw_results, scheduler.stats.timeline,
                    bottleneck.summary(), {"target": args.url})


def _write_reports(args, snapshot, raw_results, timeline, bottleneck_summary, metadata) -> None:
    out_dir = args.output_dir
    formats = args.formats or ["json", "html", "csv"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if "json" in formats:
        report = build_json_report(snapshot, raw_results, timeline, bottleneck_summary, metadata)
        path = write_json_report(f"{out_dir}/report_{ts}.json", report)
        print(f"JSON report written to {path}")

    if "html" in formats:
        html = render_html_report(snapshot, raw_results, timeline, bottleneck_summary, metadata,
                                   generated_at=datetime.now(timezone.utc).isoformat())
        path = write_html_report(f"{out_dir}/report_{ts}.html", html)
        print(f"HTML report written to {path}")

    if "csv" in formats:
        path = write_csv_report(f"{out_dir}/report_{ts}.csv", raw_results)
        print(f"CSV report written to {path}")


def cmd_dashboard(args: argparse.Namespace) -> None:
    from dashboard.app import run_dashboard
    run_dashboard(host=args.host, port=args.port, debug=args.debug)


def cmd_sockets(args: argparse.Namespace) -> None:
    if args.role == "tcp-server":
        server = TcpEchoServer(host=args.host, port=args.port)
        server.start()
        print(f"TCP echo server running on {args.host}:{args.port}. Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
    elif args.role == "udp-server":
        server = UdpEchoServer(host=args.host, port=args.port)
        server.start()
        print(f"UDP echo server running on {args.host}:{args.port}. Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
    elif args.role == "tcp-client":
        stats = tcp_client_echo(args.host, args.port, args.payload.encode())
        print(stats)
    elif args.role == "udp-client":
        stats = udp_client_echo(args.host, args.port, args.payload.encode())
        print(stats)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netperf",
        description="Network Performance Analyzer & HTTP Load Testing Framework",
    )
    parser.add_argument("--log-level", default="INFO")
    sub = parser.add_subparsers(dest="command", required=True)

    # capture
    p_capture = sub.add_parser("capture", help="Capture and analyze network traffic")
    p_capture.add_argument("--interface", help="Network interface to sniff on")
    p_capture.add_argument("--filter", help="BPF capture filter")
    p_capture.add_argument("--count", type=int, default=0, help="Number of packets to capture (0=unlimited)")
    p_capture.add_argument("--duration", type=int, default=None, help="Capture timeout in seconds")
    p_capture.add_argument("--pcap-in", help="Read packets from an existing PCAP file instead of live capture")
    p_capture.add_argument("--pcap-out", help="Save captured packets to this PCAP file")
    p_capture.set_defaults(func=cmd_capture)

    # loadtest
    p_load = sub.add_parser("loadtest", help="Run an HTTP load test")
    p_load.add_argument("url")
    p_load.add_argument("--method", default="GET")
    p_load.add_argument("--header", action="append", help="Header as 'Key: Value', repeatable")
    p_load.add_argument("--body", default=None)
    p_load.add_argument("--auth-token", default=None)
    p_load.add_argument("--users", type=int, default=10)
    p_load.add_argument("--ramp-up", type=float, default=0.0)
    p_load.add_argument("--duration", type=float, default=10.0)
    p_load.add_argument("--timeout", type=float, default=10.0)
    p_load.add_argument("--think-time", type=float, default=0.0)
    p_load.add_argument("--output-dir", default="./reports_output")
    p_load.add_argument("--formats", nargs="*", default=["json", "html", "csv"])
    p_load.add_argument("--dashboard", action="store_true", help="Launch live dashboard during the test")
    p_load.add_argument("--dashboard-host", default="127.0.0.1")
    p_load.add_argument("--dashboard-port", type=int, default=5000)
    p_load.set_defaults(func=cmd_loadtest)

    # dashboard
    p_dash = sub.add_parser("dashboard", help="Launch the standalone dashboard")
    p_dash.add_argument("--host", default="127.0.0.1")
    p_dash.add_argument("--port", type=int, default=5000)
    p_dash.add_argument("--debug", action="store_true")
    p_dash.set_defaults(func=cmd_dashboard)

    # sockets
    p_sock = sub.add_parser("sockets", help="TCP/UDP socket echo demos")
    p_sock.add_argument("role", choices=["tcp-server", "udp-server", "tcp-client", "udp-client"])
    p_sock.add_argument("--host", default="127.0.0.1")
    p_sock.add_argument("--port", type=int, default=9001)
    p_sock.add_argument("--payload", default="hello from netperf")
    p_sock.set_defaults(func=cmd_sockets)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(level=args.log_level)
    args.func(args)


if __name__ == "__main__":
    main()