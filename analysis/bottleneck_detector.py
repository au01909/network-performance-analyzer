"""Network bottleneck detection.

Consumes the outputs of the capture/parsing layer (packet records, TCP
retransmissions, DNS latency) and the load-testing layer (HTTP metrics)
to flag likely bottlenecks and produce human-readable recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from load_testing.metrics import MetricsSnapshot


@dataclass
class Finding:
    category: str
    severity: str          # "info" | "warning" | "critical"
    message: str
    recommendation: str


# Tunable thresholds; exposed as module constants so they can be
# overridden without touching detector logic.
THRESHOLDS = {
    "high_latency_p95_seconds": 1.0,
    "high_latency_p99_seconds": 2.5,
    "error_rate_warning": 0.02,     # 2%
    "error_rate_critical": 0.10,    # 10%
    "retransmission_rate_warning": 0.02,
    "dns_slow_seconds": 0.3,
    "timeout_rate_warning": 0.01,
}


class BottleneckDetector:
    def __init__(self, thresholds: Dict = None) -> None:
        self.thresholds = {**THRESHOLDS, **(thresholds or {})}
        self.findings: List[Finding] = []

    def reset(self) -> None:
        self.findings = []

    def analyze_http_metrics(self, snapshot: MetricsSnapshot) -> List[Finding]:
        t = self.thresholds
        findings: List[Finding] = []

        if snapshot.p95 > t["high_latency_p95_seconds"]:
            findings.append(Finding(
                category="latency",
                severity="warning",
                message=f"P95 latency is {snapshot.p95:.2f}s, above the "
                        f"{t['high_latency_p95_seconds']}s threshold.",
                recommendation="Investigate slow endpoints, database query "
                                "plans, or downstream service latency.",
            ))

        if snapshot.p99 > t["high_latency_p99_seconds"]:
            findings.append(Finding(
                category="latency",
                severity="critical",
                message=f"P99 latency is {snapshot.p99:.2f}s, above the "
                        f"{t['high_latency_p99_seconds']}s threshold.",
                recommendation="Tail latency this high usually points to "
                                "resource contention, GC pauses, or a slow "
                                "dependency on a subset of requests.",
            ))

        if snapshot.error_rate >= t["error_rate_critical"]:
            findings.append(Finding(
                category="errors",
                severity="critical",
                message=f"Error rate is {snapshot.error_rate:.1%}, at or above "
                        f"the critical threshold of {t['error_rate_critical']:.0%}.",
                recommendation="Check server logs for 5xx errors and verify "
                                "the target can handle the configured concurrency.",
            ))
        elif snapshot.error_rate >= t["error_rate_warning"]:
            findings.append(Finding(
                category="errors",
                severity="warning",
                message=f"Error rate is {snapshot.error_rate:.1%}, above the "
                        f"warning threshold of {t['error_rate_warning']:.0%}.",
                recommendation="Monitor error trends; consider reducing "
                                "concurrency or investigating intermittent failures.",
            ))

        if snapshot.total_requests > 0:
            timeout_rate = snapshot.timeout_count / snapshot.total_requests
            if timeout_rate >= t["timeout_rate_warning"]:
                findings.append(Finding(
                    category="timeouts",
                    severity="warning",
                    message=f"{snapshot.timeout_count} requests timed out "
                            f"({timeout_rate:.1%} of total).",
                    recommendation="Increase client timeout only if the "
                                    "server is expected to be slow; otherwise "
                                    "investigate server-side stalls.",
                ))

            if snapshot.connection_failures > 0:
                findings.append(Finding(
                    category="connections",
                    severity="warning",
                    message=f"{snapshot.connection_failures} connection "
                            f"failures observed.",
                    recommendation="Check for exhausted server connection "
                                    "pools, firewall rules, or DNS issues.",
                ))

            if snapshot.dns_failures > 0:
                findings.append(Finding(
                    category="dns",
                    severity="warning",
                    message=f"{snapshot.dns_failures} DNS resolution "
                            f"failures observed.",
                    recommendation="Verify the target hostname resolves "
                                    "reliably; consider a local DNS cache.",
                ))

        self.findings.extend(findings)
        return findings

    def analyze_tcp_retransmissions(self, tcp_records: List[Dict]) -> List[Finding]:
        if not tcp_records:
            return []
        retrans = sum(1 for r in tcp_records if r.get("is_retransmission"))
        rate = retrans / len(tcp_records)
        findings: List[Finding] = []
        if rate >= self.thresholds["retransmission_rate_warning"]:
            findings.append(Finding(
                category="packet_loss",
                severity="warning" if rate < 0.10 else "critical",
                message=f"TCP retransmission rate is {rate:.1%} "
                        f"({retrans}/{len(tcp_records)} segments).",
                recommendation="High retransmission rates usually indicate "
                                "packet loss, network congestion, or an "
                                "overloaded receiver.",
            ))
        self.findings.extend(findings)
        return findings

    def analyze_dns(self, dns_entries: List[Dict]) -> List[Finding]:
        timed = [e for e in dns_entries if e.get("response_time") is not None]
        if not timed:
            return []
        slow = [e for e in timed if e["response_time"] > self.thresholds["dns_slow_seconds"]]
        findings: List[Finding] = []
        if slow:
            findings.append(Finding(
                category="dns",
                severity="warning",
                message=f"{len(slow)} DNS lookups exceeded "
                        f"{self.thresholds['dns_slow_seconds']}s.",
                recommendation="Consider a faster or local DNS resolver, or "
                                "caching frequently resolved hostnames.",
            ))
        self.findings.extend(findings)
        return findings

    def summary(self) -> Dict:
        by_severity = {"critical": 0, "warning": 0, "info": 0}
        for f in self.findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        return {
            "total_findings": len(self.findings),
            "by_severity": by_severity,
            "findings": [f.__dict__ for f in self.findings],
        }
