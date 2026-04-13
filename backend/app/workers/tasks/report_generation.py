"""Report generation task."""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.db.session import session_scope
from app.models.domain import Finding, Job, Report
from app.reporters.generator import ReportGenerator
from app.schemas.enums import ReportStatus
from app.workers.celery_app import celery_app

log = get_logger(__name__)


async def _run(job_id: str) -> None:
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

        gen = ReportGenerator()
        report.summary = gen.summary(findings)
        report.markdown = gen.to_markdown(job, findings)
        report.html = gen.to_html(job, findings)
        report.status = ReportStatus.READY


@celery_app.task(name="app.workers.tasks.report_generation.generate_report")
def generate_report(job_id: str) -> None:
    try:
        asyncio.run(_run(job_id))
    except Exception as exc:
        log.error("report_generation_failed", job_id=job_id, error=str(exc))
        raise
