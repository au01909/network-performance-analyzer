"""CSV report generator: exports raw per-request metrics as a flat CSV
for import into spreadsheets or other analysis tools.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

FIELDNAMES = ["timestamp", "method", "url", "status_code", "success",
              "response_time", "bytes_received", "error"]


def write_csv_report(path: str, raw_results: List[Dict]) -> str:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in raw_results:
            writer.writerow({k: row.get(k) for k in FIELDNAMES})

    return str(out_path)
