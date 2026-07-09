"""HTML report generator: renders a self-contained HTML performance
report (summary table, findings, and embedded charts) using Jinja2.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, BaseLoader, select_autoescape

from load_testing.metrics import MetricsSnapshot
from reports.charts import (
    latency_distribution_chart,
    throughput_over_time_chart,
    latency_percentile_bar_chart,
    error_breakdown_pie_chart,
)

_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Network Performance Report</title>
<style>
  :root { --accent:#4C6EF5; --bg:#0f1117; --card:#171a23; --text:#e7e9ee; --muted:#9aa1b1; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
         background: var(--bg); color: var(--text); }
  header { padding: 32px 40px; border-bottom: 1px solid #262a35; }
  header h1 { margin: 0 0 4px; font-size: 26px; }
  header p { margin: 0; color: var(--muted); font-size: 14px; }
  .container { padding: 32px 40px; max-width: 1200px; margin: 0 auto; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 16px; margin-bottom: 32px; }
  .card { background: var(--card); border-radius: 10px; padding: 18px 20px;
          border: 1px solid #262a35; }
  .card .label { color: var(--muted); font-size: 12px; text-transform: uppercase;
                 letter-spacing: .04em; margin-bottom: 6px; }
  .card .value { font-size: 26px; font-weight: 600; }
  .value.ok { color: #40c057; }
  .value.warn { color: #f59f00; }
  .value.bad { color: #fa5252; }
  section { margin-bottom: 40px; }
  section h2 { font-size: 18px; border-left: 4px solid var(--accent); padding-left: 10px; }
  .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; }
  .charts img { width: 100%; border-radius: 8px; background: white; padding: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #262a35; }
  th { color: var(--muted); font-weight: 500; }
  .badge { display:inline-block; padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight:600; }
  .badge.critical { background: #fa525233; color: #fa5252; }
  .badge.warning { background: #f59f0033; color: #f59f00; }
  .badge.info { background: #4c6ef533; color: #4c6ef5; }
  footer { text-align:center; color: var(--muted); font-size: 12px; padding: 24px; }
</style>
</head>
<body>
<header>
  <h1>Network Performance Analyzer Report</h1>
  <p>Generated {{ generated_at }} &middot; Target: {{ metadata.get('target', 'N/A') }}</p>
</header>
<div class="container">

  <div class="grid">
    <div class="card"><div class="label">Total Requests</div><div class="value">{{ metrics.total_requests }}</div></div>
    <div class="card"><div class="label">Success Rate</div>
      <div class="value {{ 'ok' if metrics.error_rate < 0.02 else ('warn' if metrics.error_rate < 0.1 else 'bad') }}">
        {{ '%.2f' | format((1 - metrics.error_rate) * 100) }}%
      </div>
    </div>
    <div class="card"><div class="label">Requests / sec</div><div class="value">{{ '%.1f' | format(metrics.requests_per_sec) }}</div></div>
    <div class="card"><div class="label">P95 Latency</div><div class="value">{{ '%.0f' | format(metrics.p95 * 1000) }} ms</div></div>
    <div class="card"><div class="label">P99 Latency</div><div class="value">{{ '%.0f' | format(metrics.p99 * 1000) }} ms</div></div>
    <div class="card"><div class="label">Errors</div><div class="value">{{ metrics.failed_requests }}</div></div>
  </div>

  <section>
    <h2>Charts</h2>
    <div class="charts">
      <div><img src="data:image/png;base64,{{ chart_latency_dist }}"></div>
      <div><img src="data:image/png;base64,{{ chart_percentiles }}"></div>
      <div><img src="data:image/png;base64,{{ chart_throughput }}"></div>
      <div><img src="data:image/png;base64,{{ chart_errors }}"></div>
    </div>
  </section>

  <section>
    <h2>Latency Summary</h2>
    <table>
      <tr><th>Min</th><th>Avg</th><th>Median</th><th>Max</th><th>P50</th><th>P90</th><th>P95</th><th>P99</th></tr>
      <tr>
        <td>{{ '%.1f' | format(metrics.latency_min*1000) }} ms</td>
        <td>{{ '%.1f' | format(metrics.latency_avg*1000) }} ms</td>
        <td>{{ '%.1f' | format(metrics.latency_median*1000) }} ms</td>
        <td>{{ '%.1f' | format(metrics.latency_max*1000) }} ms</td>
        <td>{{ '%.1f' | format(metrics.p50*1000) }} ms</td>
        <td>{{ '%.1f' | format(metrics.p90*1000) }} ms</td>
        <td>{{ '%.1f' | format(metrics.p95*1000) }} ms</td>
        <td>{{ '%.1f' | format(metrics.p99*1000) }} ms</td>
      </tr>
    </table>
  </section>

  <section>
    <h2>Bottleneck Findings ({{ bottlenecks.get('total_findings', 0) }})</h2>
    {% if bottlenecks.get('findings') %}
    <table>
      <tr><th>Severity</th><th>Category</th><th>Message</th><th>Recommendation</th></tr>
      {% for f in bottlenecks['findings'] %}
      <tr>
        <td><span class="badge {{ f['severity'] }}">{{ f['severity'] }}</span></td>
        <td>{{ f['category'] }}</td>
        <td>{{ f['message'] }}</td>
        <td>{{ f['recommendation'] }}</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <p style="color: var(--muted)">No bottlenecks detected.</p>
    {% endif %}
  </section>

</div>
<footer>Network Performance Analyzer &amp; HTTP Load Testing Framework</footer>
</body>
</html>
"""


def render_html_report(
    snapshot: MetricsSnapshot,
    raw_results: List[Dict],
    timeline: Optional[List[Dict]] = None,
    bottleneck_summary: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    generated_at: str = "",
) -> str:
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html"]))
    template = env.from_string(_TEMPLATE)

    latencies_ms = [r["response_time"] * 1000 for r in raw_results if r.get("response_time") is not None]

    return template.render(
        generated_at=generated_at,
        metadata=metadata or {},
        metrics=snapshot,
        bottlenecks=bottleneck_summary or {},
        chart_latency_dist=latency_distribution_chart(latencies_ms),
        chart_percentiles=latency_percentile_bar_chart(snapshot.p50, snapshot.p90, snapshot.p95, snapshot.p99),
        chart_throughput=throughput_over_time_chart(timeline or []),
        chart_errors=error_breakdown_pie_chart(snapshot.successful_requests, snapshot.failed_requests),
    )


def write_html_report(path: str, html: str) -> str:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return str(out_path)
