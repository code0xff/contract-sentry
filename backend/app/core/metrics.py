"""Prometheus metrics registry."""
from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram

REGISTRY = CollectorRegistry()

JOB_TOTAL = Counter(
    "job_total",
    "Total number of analysis jobs processed",
    labelnames=("tool", "status"),
    registry=REGISTRY,
)

JOB_DURATION = Histogram(
    "job_duration_seconds",
    "Duration of analysis job execution",
    labelnames=("tool",),
    registry=REGISTRY,
)

TOOL_FAILURE = Counter(
    "tool_failure_total",
    "Total number of tool failures",
    labelnames=("tool", "reason"),
    registry=REGISTRY,
)
