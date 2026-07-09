"""Configuration model for the Network Performance Analyzer.

Config can be constructed from CLI arguments, a JSON file, or defaults.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CaptureConfig:
    interface: Optional[str] = None
    bpf_filter: str = ""
    packet_count: int = 0            # 0 = unlimited
    timeout: Optional[int] = None
    pcap_out: Optional[str] = None
    pcap_in: Optional[str] = None


@dataclass
class LoadTestConfig:
    url: str = ""
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    auth_token: Optional[str] = None
    users: int = 10
    ramp_up_seconds: float = 0.0
    duration_seconds: float = 10.0
    request_timeout: float = 10.0
    think_time: float = 0.0


@dataclass
class ReportConfig:
    output_dir: str = "./reports_output"
    formats: List[str] = field(default_factory=lambda: ["json", "html", "csv"])


@dataclass
class AppConfig:
    log_level: str = "INFO"
    log_file: Optional[str] = None
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    load_test: LoadTestConfig = field(default_factory=LoadTestConfig)
    report: ReportConfig = field(default_factory=ReportConfig)

    @classmethod
    def from_file(cls, path: str) -> "AppConfig":
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        cfg = cls()
        if "log_level" in data:
            cfg.log_level = data["log_level"]
        if "log_file" in data:
            cfg.log_file = data["log_file"]
        if "capture" in data:
            cfg.capture = CaptureConfig(**data["capture"])
        if "load_test" in data:
            cfg.load_test = LoadTestConfig(**data["load_test"])
        if "report" in data:
            cfg.report = ReportConfig(**data["report"])
        return cfg

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))
