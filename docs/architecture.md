# Architecture

## Overview

The Network Performance Analyzer & HTTP Load Testing Framework is composed of
four cooperating subsystems that share common utility and reporting layers:

```
                     ┌─────────────┐
                     │     CLI     │  main.py (argparse subcommands)
                     └──────┬──────┘
             ┌──────────────┼──────────────┬───────────────┐
             ▼               ▼              ▼               ▼
     ┌───────────────┐ ┌───────────┐ ┌─────────────┐ ┌─────────────┐
     │    Capture     │ │   Load    │ │  Dashboard  │ │   Sockets   │
     │    (Scapy)     │ │  Testing  │ │   (Flask)   │ │ (TCP/UDP)   │
     └───────┬───────┘ └─────┬─────┘ └──────┬──────┘ └─────────────┘
             │               │              │
             ▼               ▼              │
     ┌───────────────┐ ┌───────────┐        │
     │   Analysis     │ │  Metrics  │◄───────┘ (reads live MetricsEngine)
     │ (Bottlenecks)  │ │  Engine   │
     └───────┬───────┘ └─────┬─────┘
             └───────┬───────┘
                     ▼
             ┌───────────────┐
             │   Reporting    │  JSON / HTML / CSV
             └───────────────┘
```

## Module Responsibilities

### `capture/`
- `packet_capture.py` — Scapy-backed live sniffing and PCAP file I/O.
- `packet_parser.py` — Dispatches each raw packet to the correct
  protocol parser and returns a normalized record.
- `tcp_parser.py`, `udp_parser.py`, `dns_parser.py`, `http_parser.py` —
  Protocol-specific field extraction, plus stateful trackers
  (`TcpStreamTracker`, `DnsLatencyTracker`, `HttpExchangeTracker`) that
  correlate related packets (e.g. request/response, retransmissions).
- `filters.py` — BPF filter string builders and presets.

### `load_testing/`
- `http_client.py` — Times a single HTTP call via `requests` and
  normalizes success/failure into an `HttpResult`.
- `worker.py` — One simulated user's request loop, run in its own thread.
- `scheduler.py` — Ramps up N workers via `ThreadPoolExecutor`, manages
  graceful shutdown, and owns the shared `MetricsEngine`.
- `metrics.py` — Thread-safe aggregation of raw results into latency
  percentiles, throughput, and error counts (a `MetricsSnapshot`).
- `statistics.py` — Periodically snapshots the `MetricsEngine` on a
  background thread to build a time series for charts/dashboards.

### `analysis/`
- `bottleneck_detector.py` — Applies configurable thresholds to
  `MetricsSnapshot`s, TCP retransmission records, and DNS timing to
  produce categorized findings with actionable recommendations.

### `reports/`
- `json_report.py`, `csv_report.py`, `html_report.py` — Render the
  final report artifacts. The HTML report embeds matplotlib charts
  (`charts.py`) as base64 PNGs so it is fully self-contained.

### `dashboard/`
- `app.py` — Flask app exposing `/api/metrics`, `/api/timeline`, and
  `/api/dns` for a live-updating dashboard page (`templates/dashboard.html`)
  built with Chart.js.

### `sockets/`
- `tcp_udp.py` — Minimal raw TCP/UDP echo client and server
  implementations for measuring connection and round-trip timing
  independent of the HTTP stack.

### `utils/`
- `config.py` — Dataclass-based configuration for capture, load
  testing, and reporting, loadable from JSON.
- `logger.py` — Centralized logging setup.
- `helpers.py` — Percentile/statistics helpers, a `Timer` context
  manager, and misc utilities shared across modules.

## Data Flow: Load Test

1. `main.py loadtest <url> ...` builds a `LoadTestConfig`.
2. `LoadTestScheduler.run()` spins up a `ThreadPoolExecutor`, ramping up
   `Worker` threads at the configured rate.
3. Each `Worker` loops, calling `HttpClient.execute()` and pushing an
   `HttpResult` dict into the shared `MetricsEngine`.
4. A background `StatisticsRecorder` snapshots the engine every second,
   building a timeline for the throughput/latency charts.
5. Once all workers finish, `BottleneckDetector` analyzes the final
   `MetricsSnapshot` for latency, error-rate, and timeout issues.
6. `reports/*` render JSON, HTML, and CSV artifacts from the snapshot,
   raw results, timeline, and bottleneck summary.

If `--dashboard` is passed, the Flask app is started on a background
thread and attached to the same live `LoadTestScheduler`, so `/api/metrics`
and `/api/timeline` reflect the in-progress test in real time.

## Data Flow: Packet Capture

1. `main.py capture --interface eth0 ...` (or `--pcap-in file.pcap`)
   builds a `PacketCapture` and captures/reads packets.
2. Each raw packet is passed to `PacketParser.parse()`, which dispatches
   to DNS/HTTP/TCP/UDP parsers and returns a normalized record.
3. Protocol-specific trackers (`DnsLatencyTracker`, `HttpExchangeTracker`,
   `TcpStreamTracker`) accumulate cross-packet state (response times,
   retransmissions).
4. `BottleneckDetector.analyze_tcp_retransmissions()` /
   `.analyze_dns()` flag issues found in the capture.

## Extensibility

The parser dispatch in `PacketParser.parse()` and the load-testing
`Worker`/`HttpClient` pair are intentionally decoupled from the CLI, so
new protocol parsers or new load-generation strategies (e.g. WebSocket,
gRPC) can be added as new modules without changing existing ones —
matching the "modular architecture with plugin support" requirement.
