#!/bin/bash

set -e

echo "===================================="
echo "Network Performance Analyzer Demo"
echo "===================================="

mkdir -p reports_output

###############################################
# TCP Demo
###############################################

echo ""
echo "Starting TCP Echo Server..."

python main.py sockets tcp-server --port 9001 &
TCP_PID=$!

sleep 2

echo "Running TCP Client..."

python main.py sockets tcp-client \
    --host 127.0.0.1 \
    --port 9001 \
    --payload "Hello TCP"

kill $TCP_PID || true

###############################################
# UDP Demo
###############################################

echo ""
echo "Starting UDP Echo Server..."

python main.py sockets udp-server --port 9002 &
UDP_PID=$!

sleep 2

echo "Running UDP Client..."

python main.py sockets udp-client \
    --host 127.0.0.1 \
    --port 9002 \
    --payload "Hello UDP"

kill $UDP_PID || true

###############################################
# HTTP Load Test + Dashboard
###############################################

echo ""
echo "Starting HTTP Load Test..."

python main.py loadtest \
    https://example.com \
    --users 20 \
    --ramp-up 5 \
    --duration 30 \
    --dashboard \
    --dashboard-host 0.0.0.0 \
    --output-dir reports_output

echo ""
echo "===================================="
echo "Demo Finished"
echo "===================================="

echo ""
echo "Generated Reports"

ls -lh reports_output