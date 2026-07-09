# Network Performance Analyzer & HTTP Load Testing Framework

A modular Python framework for **network traffic analysis**, **HTTP load testing**, **performance monitoring**, and **automated bottleneck detection**. The project combines live packet capture, protocol inspection, concurrent HTTP load generation, a real-time Flask dashboard, and HTML/JSON/CSV reporting behind a single command-line interface.

---

# Features

### Network Packet Analysis

* Live packet capture using Scapy
* Offline PCAP analysis
* TCP, UDP, DNS, HTTP, ICMP and ARP parsing
* TCP retransmission detection
* DNS latency tracking
* HTTP request/response correlation

### HTTP Load Testing

* Configurable concurrent virtual users
* Ramp-up control
* Request timeout configuration
* Think-time simulation
* Custom headers
* Request body support
* Authentication token support

### Performance Metrics

* Total requests
* Successful / Failed requests
* Requests per second
* Bytes per second
* Average latency
* Median latency
* P50 / P90 / P95 / P99 latency
* Error rate
* Connection failures
* DNS failures
* Timeout statistics

### Automated Bottleneck Detection

The framework automatically detects:

* High request latency
* High HTTP error rate
* TCP retransmissions
* Slow DNS lookups
* Connection failures
* Request timeouts

Each finding includes a severity level and recommendation.

### Reports

Automatically generates:

* HTML Performance Report
* JSON Report
* CSV Report

### Live Dashboard

Real-time dashboard displaying:

* Requests/sec
* Total Requests
* Error Rate
* Latency Charts
* CPU Usage
* Memory Usage
* Timeline Graphs

### Socket Programming

Includes:

* TCP Echo Server
* TCP Echo Client
* UDP Echo Server
* UDP Echo Client

---

# Project Structure

```
network-performance-analyzer/

capture/
    packet_capture.py
    packet_parser.py
    tcp_parser.py
    udp_parser.py
    dns_parser.py
    http_parser.py

load_testing/
    http_client.py
    worker.py
    scheduler.py
    metrics.py
    statistics.py

analysis/
    bottleneck_detector.py

dashboard/
    app.py
    templates/

reports/
    html_report.py
    json_report.py
    csv_report.py

sockets/
    tcp_udp.py

tests/
    unit/
    integration/

utils/

main.py
requirements.txt
Dockerfile
README.md
```

---

# Installation

```bash
git clone <repository>

cd network-performance-analyzer

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```

---

# How the Project Works

Everything starts from:

```
main.py
```

`main.py` acts as the CLI entry point.

Depending on the command, it calls different modules.

---

## Packet Capture

Command

```bash
sudo python main.py capture --interface en0 --duration 15
```

Execution Flow

```
main.py
    ↓
cmd_capture()
    ↓
PacketCapture
    ↓
PacketParser
    ↓
TCP/DNS/HTTP Parsers
    ↓
BottleneckDetector
    ↓
Capture Summary
```

Output

* Protocol counts
* HTTP statistics
* DNS statistics
* TCP retransmission analysis
* Bottleneck findings

---

## HTTP Load Test

Command

```bash
python main.py loadtest https://example.com \
    --users 20 \
    --ramp-up 5 \
    --duration 20 \
    --dashboard
```

Execution Flow

```
main.py
      ↓
LoadTestScheduler
      ↓
Workers
      ↓
HttpClient
      ↓
MetricsEngine
      ↓
StatisticsRecorder
      ↓
Dashboard
      ↓
Report Generator
```

The scheduler creates multiple worker threads.

Each worker continuously sends HTTP requests.

Every request is recorded inside the Metrics Engine.

The dashboard reads live metrics while the load test is running.

When the test completes:

* HTML Report
* JSON Report
* CSV Report

are automatically generated.

---

## Dashboard

Command

```bash
python main.py loadtest https://example.com --dashboard
```

Open

```
http://127.0.0.1:5000
```

Dashboard displays

* Requests/sec
* Total Requests
* Error Rate
* CPU Usage
* Memory Usage
* P50/P95/P99 Latency
* Timeline Graph

---

## Socket Programming

Start TCP Server

```bash
python main.py sockets tcp-server --port 9001
```

Start TCP Client

```bash
python main.py sockets tcp-client \
    --host 127.0.0.1 \
    --port 9001 \
    --payload "hello"
```

UDP Server

```bash
python main.py sockets udp-server --port 9002
```

UDP Client

```bash
python main.py sockets udp-client \
    --host 127.0.0.1 \
    --port 9002 \
    --payload "hello"
```

---

# Running Tests

Run all tests

```bash
python -m pytest -v
```

Run only unit tests

```bash
python -m pytest tests/unit -v
```

Run only integration tests

```bash
python -m pytest tests/integration -v
```

Run Bottleneck Detector tests

```bash
python -m pytest tests/unit/test_bottleneck_detector.py -v
```

Run Metrics tests

```bash
python -m pytest tests/unit/test_metrics.py -v
```

Run Socket tests

```bash
python -m pytest tests/unit/test_tcp_udp_sockets.py -v
```

---

# Viewing Reports

Every load test automatically creates:

```
reports_output/

report_*.html
report_*.json
report_*.csv
```

Open HTML Report

macOS

```bash
open reports_output/report_*.html
```

Linux

```bash
xdg-open reports_output/report_*.html
```

Windows

```bash
start reports_output/report_*.html
```

JSON report contains structured metrics.

CSV contains request-by-request performance data.

---

# Packet Capture Examples

List interfaces

```bash
python -c "from capture.packet_capture import PacketCapture; print(PacketCapture.list_interfaces())"
```

Capture traffic

```bash
sudo python main.py capture \
    --interface en0 \
    --duration 15
```

Analyze a PCAP file

```bash
python main.py capture --pcap-in capture.pcap
```

Save captured packets

```bash
sudo python main.py capture \
    --interface en0 \
    --duration 20 \
    --pcap-out capture.pcap
```

---

# Example Bottleneck Output

```
=== Load Test Summary ===

Total Requests: 160

Successful: 120

Failed: 40

Requests/sec: 12.9

Error Rate: 25%

[CRITICAL] errors:
Error rate is 25%

Recommendation:
Check server logs for 5xx errors and verify the target can handle the configured concurrency.
```

Packet Capture Example

```
=== Capture Summary ===

TCP Retransmission Rate

33.8%

[CRITICAL] packet_loss

TCP retransmission rate is 33.8% (22/65 segments)
```

---

# Technologies Used

* Python
* Scapy
* Flask
* Requests
* ThreadPoolExecutor
* TCP/UDP Sockets
* Chart.js
* HTML/CSS/JavaScript
* Pytest
* Docker

---

# Future Improvements

* HTTPS packet inspection
* HTTP/2 support
* WebSocket performance analysis
* Distributed load generation
* Prometheus & Grafana integration
* Live bottleneck panel in dashboard
* Advanced TCP retransmission analysis