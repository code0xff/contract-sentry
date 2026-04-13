"""Dynamic / fuzzing analysis task."""
from __future__ import annotations

import asyncio

from app.analyzers.echidna_analyzer import EchidnaAnalyzer
from app.core.logging import get_logger
from app.db.session import session_scope
from app.models.domain import Contract, Evidence, Finding, Job
from app.reporters.aggregator import aggregate_findings
from app.schemas.enums import JobStatus
from app.workers.celery_app import celery_app

log = get_logger(__name__)


async def _run(job_id: str, contract_id: str) -> None:
    async with session_scope() as session:
        job = await session.get(Job, job_id)
        contract = await session.get(Contract, contract_id)
        if job is None or contract is None:
            return
        job.status = JobStatus.RUNNING

    findings = EchidnaAnalyzer().analyze(contract.source or "")
    aggregated = aggregate_findings(findings)

    async with session_scope() as session:
        job = await session.get(Job, job_id)
        assert job is not None
        for fc in aggregated:
            finding = Finding(
                job_id=job.id,
                tool=fc.tool,
                vulnerability_type=fc.vulnerability_type,
                severity=fc.severity,
                title=fc.title,
                description=fc.description,
                location=fc.location,
                confidence=fc.confidence,
            )
            session.add(finding)
            await session.flush()
            for ev in fc.evidence:
                session.add(Evidence(finding_id=finding.id, kind=ev.get("kind", "raw_output"), payload=ev))
        job.status = JobStatus.COMPLETED
        job.progress = 100


@celery_app.task(
    name="app.workers.tasks.dynamic_analysis.run_dynamic_analysis",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run_dynamic_analysis(self, job_id: str, contract_id: str) -> None:
    try:
        asyncio.run(_run(job_id, contract_id))
    except Exception as exc:
        log.error("dynamic_analysis_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)
