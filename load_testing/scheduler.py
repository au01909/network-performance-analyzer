"""Load test scheduler: ramps up simulated users over time using a
ThreadPoolExecutor, then waits for the configured test duration before
signalling a graceful shutdown.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import List

from load_testing.metrics import MetricsEngine
from load_testing.statistics import StatisticsRecorder
from load_testing.worker import Worker
from utils.config import LoadTestConfig
from utils.logger import get_logger

log = get_logger(__name__)


class LoadTestScheduler:
    """Coordinates worker ramp-up, execution, and graceful shutdown.

    Usage:
        scheduler = LoadTestScheduler(config)
        result_metrics = scheduler.run()
    """

    def __init__(self, config: LoadTestConfig, stats_interval: float = 1.0) -> None:
        self.config = config
        self.metrics = MetricsEngine()
        self.stats = StatisticsRecorder(self.metrics, interval_seconds=stats_interval)
        self._stop_event = threading.Event()
        self._executor: ThreadPoolExecutor = None
        self._futures: List[Future] = []
        self._workers: List[Worker] = []

    def _spawn_worker(self, worker_id: int, end_time: float) -> None:
        worker = Worker(worker_id, self.config, self.metrics, self._stop_event, end_time)
        self._workers.append(worker)
        future = self._executor.submit(worker.run)
        self._futures.append(future)

    def run(self) -> MetricsEngine:
        """Run the full ramp-up + steady-state load test, blocking until
        complete. Returns the MetricsEngine holding all recorded results.
        """
        cfg = self.config
        if not cfg.url:
            raise ValueError("LoadTestConfig.url must be set before running a load test")

        self.metrics.reset()
        self._stop_event.clear()
        self.stats.start()

        start_time = time.time()
        end_time = start_time + cfg.ramp_up_seconds + cfg.duration_seconds

        log.info(
            "Starting load test: users=%d ramp_up=%.1fs duration=%.1fs target=%s",
            cfg.users, cfg.ramp_up_seconds, cfg.duration_seconds, cfg.url,
        )

        self._executor = ThreadPoolExecutor(max_workers=cfg.users, thread_name_prefix="vuser")
        try:
            if cfg.ramp_up_seconds > 0 and cfg.users > 1:
                delay = cfg.ramp_up_seconds / cfg.users
                for i in range(cfg.users):
                    self._spawn_worker(i, end_time)
                    time.sleep(delay)
            else:
                for i in range(cfg.users):
                    self._spawn_worker(i, end_time)

            # Wait until all workers finish naturally (they self-terminate
            # at end_time) or the whole run is cancelled.
            for future in self._futures:
                future.result()
        except KeyboardInterrupt:
            log.warning("Load test interrupted by user; shutting down workers gracefully")
            self._stop_event.set()
        finally:
            self.stats.stop()
            self._executor.shutdown(wait=True)

        total_sent = sum(w.requests_sent for w in self._workers)
        log.info("Load test complete: %d total requests sent", total_sent)
        return self.metrics

    def stop(self) -> None:
        """Signal all workers to stop early (graceful shutdown)."""
        self._stop_event.set()
