"""A single virtual-user worker loop: repeatedly issues HTTP requests
against the target for the duration of the test, recording each result
into the shared metrics engine.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import requests

from load_testing.http_client import HttpClient
from load_testing.metrics import MetricsEngine
from utils.config import LoadTestConfig
from utils.logger import get_logger

log = get_logger(__name__)


class Worker:
    """Represents one simulated user. Runs in its own thread until the
    shared stop_event is set or the test duration elapses.
    """

    def __init__(
        self,
        worker_id: int,
        config: LoadTestConfig,
        metrics: MetricsEngine,
        stop_event: threading.Event,
        end_time: float,
    ) -> None:
        self.worker_id = worker_id
        self.config = config
        self.metrics = metrics
        self.stop_event = stop_event
        self.end_time = end_time
        self.requests_sent = 0

    def run(self) -> None:
        session = requests.Session()
        client = HttpClient(
            url=self.config.url,
            method=self.config.method,
            headers=self.config.headers,
            body=self.config.body,
            auth_token=self.config.auth_token,
            timeout=self.config.request_timeout,
            session=session,
        )

        log.debug("Worker %d starting", self.worker_id)
        while not self.stop_event.is_set() and time.time() < self.end_time:
            result = client.execute()
            self.metrics.record(result.to_dict())
            self.requests_sent += 1

            if self.config.think_time > 0:
                time.sleep(self.config.think_time)

        session.close()
        log.debug("Worker %d finished: %d requests sent", self.worker_id, self.requests_sent)
