"""Orchestrates static analysis run for a Job."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.analyzers.mythril_analyzer import MythrilAnalyzer
from app.analyzers.slither_analyzer import SlitherAnalyzer
from app.core.logging import get_logger
from app.core.metrics import JOB_DURATION, JOB_TOTAL, TOOL_FAILURE
from app.db.session import session_scope
from app.models.domain import Evidence, Finding, Job
from app.reporters.aggregator import aggregate_findings
from app.schemas.enums import JobStatus, ToolName, is_allowed_transition
from app.workers.celery_app import celery_app

log = get_logger(__name__)


async def _run(job_id: str, contract_id: str, tools: list[str]) -> None:
    from app.models.domain import Contract  # local import for tests

    async with session_scope() as session:
        job = await session.get(Job, job_id)
        contract = await session.get(Contract, contract_id)
        if job is None or contract is None:
            log.error("job_or_contract_missing", job_id=job_id)
            return

        if not is_allowed_transition(job.status, JobStatus.RUNNING):
            log.warning("invalid_transition", current=job.status)
            return
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(tz=timezone.utc)

    collected_findings = []
    for tool in tools:
        try:
            if tool == ToolName.SLITHER.value:
                findings = SlitherAnalyzer().analyze(contract.source or contract.bytecode or "")
            elif tool == ToolName.MYTHRIL.value:
                findings = MythrilAnalyzer().analyze(contract.source or contract.bytecode or "")
            elif tool == ToolName.ECHIDNA.value:
                from app.analyzers.echidna_analyzer import EchidnaAnalyzer

                findings = EchidnaAnalyzer().analyze(contract.source or "")
            else:
                findings = []
            JOB_TOTAL.labels(tool=tool, status="ok").inc()
            collected_findings.extend(findings)
        except Exception as exc:
            log.error("tool_failed", tool=tool, error=str(exc))
            TOOL_FAILURE.labels(tool=tool, reason=type(exc).__name__).inc()

    # dedup + persist
    aggregated = aggregate_findings(collected_findings)

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
        job.finished_at = datetime.now(tz=timezone.utc)

    # Trigger report generation
    try:
        from app.workers.tasks.report_generation import generate_report

        generate_report.apply_async(args=[job_id])
    except Exception as exc:  # pragma: no cover
        log.warning("report_dispatch_failed", error=str(exc))


@celery_app.task(
    name="app.workers.tasks.static_analysis.run_analysis_job",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run_analysis_job(self, job_id: str, contract_id: str, tools: list[str]) -> None:
    start = datetime.now(tz=timezone.utc)
    try:
        asyncio.run(_run(job_id, contract_id, tools))
    except Exception as exc:
        log.error("analysis_job_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)
    finally:
        duration = (datetime.now(tz=timezone.utc) - start).total_seconds()
        JOB_DURATION.labels(tool="composite").observe(duration)
