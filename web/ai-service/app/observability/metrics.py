"""In-process metrics — lightweight counters and histograms.

Designed to be zero-dependency in development; in production these
values can be scraped by Prometheus via a /metrics endpoint.

Usage::

    metrics = get_metrics()
    metrics.increment("chat_requests_total", tags={"agent": "hr"})
    metrics.observe("latency_ms", 312.4, tags={"agent": "hr"})
    metrics.snapshot()   # → dict of current values
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

_log = get_logger()
_lock = threading.Lock()
_instance: "MetricsRegistry | None" = None


@dataclass
class HistogramBucket:
    count: int = 0
    total: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        if value < self.min_val:
            self.min_val = value
        if value > self.max_val:
            self.max_val = value

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "total": round(self.total, 2),
            "mean": round(self.mean, 2),
            "min": round(self.min_val, 2) if self.count else 0,
            "max": round(self.max_val, 2) if self.count else 0,
        }


class MetricsRegistry:
    """Thread-safe registry for counters and histograms."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._histograms: dict[str, HistogramBucket] = defaultdict(HistogramBucket)
        self._lock = threading.Lock()
        self._started_at = time.time()

    def increment(self, name: str, amount: int = 1, tags: dict | None = None) -> None:
        key = self._key(name, tags)
        with self._lock:
            self._counters[key] += amount

    def observe(self, name: str, value: float, tags: dict | None = None) -> None:
        key = self._key(name, tags)
        with self._lock:
            self._histograms[key].observe(value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "uptime_seconds": round(time.time() - self._started_at, 1),
                "counters": dict(self._counters),
                "histograms": {k: v.to_dict() for k, v in self._histograms.items()},
            }

    @staticmethod
    def _key(name: str, tags: dict | None) -> str:
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"


def get_metrics() -> MetricsRegistry:
    """Return the process-level singleton MetricsRegistry."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = MetricsRegistry()
    return _instance


def record_chat_metrics(state: dict, latency_ms: float) -> None:
    """Convenience function — records standard chat metrics from a GraphState."""
    m = get_metrics()
    agent = state.get("selected_agent", "unknown")
    tags = {"agent": agent}
    m.increment("chat_requests_total", tags=tags)
    m.observe("latency_ms", latency_ms, tags=tags)
    m.observe("prompt_tokens", state.get("prompt_tokens", 0), tags=tags)
    m.observe("completion_tokens", state.get("completion_tokens", 0), tags=tags)
    if state.get("errors"):
        m.increment("chat_errors_total", tags=tags)
