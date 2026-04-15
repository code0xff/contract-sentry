"""Celery application with queue separation and retry policies."""
from __future__ import annotations

from celery import Celery
from celery.signals import worker_process_init

from app.config import get_settings

settings = get_settings()


@worker_process_init.connect
def _reset_db_pool(**kwargs: object) -> None:
    """Dispose the inherited connection pool after fork so each worker
    process creates its own connections on a fresh event loop."""
    import asyncio

    from app.db.session import engine

    asyncio.run(engine.dispose())


STATIC_ANALYSIS_QUEUE = "static_analysis"
DYNAMIC_ANALYSIS_QUEUE = "dynamic_analysis"
SIMULATION_QUEUE = "simulation"
REPORT_QUEUE = "report"

celery_app = Celery(
    "contract_centry",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.static_analysis",
        "app.workers.tasks.dynamic_analysis",
        "app.workers.tasks.simulation",
        "app.workers.tasks.report_generation",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.static_analysis.*": {"queue": STATIC_ANALYSIS_QUEUE},
        "app.workers.tasks.dynamic_analysis.*": {"queue": DYNAMIC_ANALYSIS_QUEUE},
        "app.workers.tasks.simulation.*": {"queue": SIMULATION_QUEUE},
        "app.workers.tasks.report_generation.*": {"queue": REPORT_QUEUE},
    },
    task_default_retry_delay=30,
    task_publish_retry=True,
    task_publish_retry_policy={"max_retries": 3, "interval_start": 30},
)
