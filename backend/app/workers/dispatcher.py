"""Dispatch helpers that enqueue Celery tasks.

Kept separate from celery_app so the API layer can import it without
forcing Celery workers to import FastAPI dependencies. When Celery is
not configured (e.g. tests), dispatches become no-ops.
"""
from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)


def dispatch_job(job_id: str, contract_id: str, tools: list[str]) -> None:
    try:
        from app.workers.tasks.static_analysis import run_analysis_job

        run_analysis_job.apply_async(
            args=[job_id, contract_id, tools],
            expires=3600,
            retry=True,
            retry_policy={"max_retries": 3, "interval_start": 30},
        )
    except Exception as exc:  # pragma: no cover — broker unavailable in tests
        log.warning("dispatch_job_failed", job_id=job_id, error=str(exc))


def dispatch_simulation(simulation_id: str, use_fork: bool) -> None:
    try:
        from app.workers.tasks.simulation import run_simulation

        run_simulation.apply_async(
            args=[simulation_id, use_fork],
            expires=3600,
            retry=True,
            retry_policy={"max_retries": 3, "interval_start": 30},
        )
    except Exception as exc:  # pragma: no cover
        log.warning("dispatch_simulation_failed", simulation_id=simulation_id, error=str(exc))
