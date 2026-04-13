"""Report generation task."""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.core.notifications import send_job_notification
from app.db.session import session_scope
from app.models.domain import Finding, Job, Report
from app.reporters.generator import ReportGenerator
from app.schemas.enums import ReportStatus
from app.workers.celery_app import celery_app

log = get_logger(__name__)


async def _run(job_id: str) -> None:
    findings_count = 0
    report_id: str | None = None

    async with session_scope() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        result = await session.execute(
            select(Finding)
            .where(Finding.job_id == job_id)
            .options(selectinload(Finding.evidences))
        )
        findings = list(result.scalars().all())

        existing = await session.execute(select(Report).where(Report.job_id == job_id))
        report = existing.scalar_one_or_none()
        if report is None:
            report = Report(job_id=job_id)
            session.add(report)
            # Flush early to catch concurrent-insert IntegrityError before we
            # do expensive report generation work. The caller retries on this.
            await session.flush()

        gen = ReportGenerator()
        report.summary = gen.summary(findings)
        report.markdown = gen.to_markdown(job, findings)
        report.html = gen.to_html(job, findings)
        report.status = ReportStatus.READY

        findings_count = len(findings)
        report_id = report.id
    # session committed — now safe to send external notification
    await send_job_notification(
        job_id=job_id,
        status="completed",
        findings_count=findings_count,
        report_id=report_id,
    )


@celery_app.task(
    name="app.workers.tasks.report_generation.generate_report",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def generate_report(self, job_id: str) -> None:
    try:
        asyncio.run(_run(job_id))
    except IntegrityError as exc:
        # Concurrent task already inserted the Report row; retry to update it.
        log.warning("report_concurrent_insert_retry", job_id=job_id)
        raise self.retry(exc=exc, countdown=1)
    except Exception as exc:
        log.error("report_generation_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)
