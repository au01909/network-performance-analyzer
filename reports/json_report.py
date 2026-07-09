"""JSON report generator: dumps metrics, raw results, and detected
bottleneck findings into a single structured JSON file.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from load_testing.metrics import MetricsSnapshot


def build_json_report(
    snapshot: MetricsSnapshot,
    raw_results: List[Dict],
    timeline: Optional[List[Dict]] = None,
    bottleneck_summary: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
        "metrics": asdict(snapshot),
        "timeline": timeline or [],
        "bottlenecks": bottleneck_summary or {},
        "raw_result_count": len(raw_results),
        "raw_results_sample": raw_results[:200],  # avoid huge files by default
    }


def write_json_report(path: str, report: Dict) -> str:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str))
    return str(out_path)
