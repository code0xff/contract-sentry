"""Orchestrates static analysis run for a Job."""
from __future__ import annotations

import asyncio
import json as _json
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


async def _run(job_id: str, contract_id: str, tools: list[str], entry_files: list[str] | None = None) -> None:
    from app.models.domain import Contract  # local import for tests

    # Capture source inside the session block to avoid detached-instance access
    source: str = ""
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
        bytecode: str | None = contract.bytecode
        source = contract.source or bytecode or ""
        bytecode_only = not contract.source and bool(bytecode)
        project_files: dict[str, str] | None = None
        if contract.project_files:
            try:
                project_files = _json.loads(contract.project_files)
                from app.analyzers.base import auto_alias_by_basename
                project_files = auto_alias_by_basename(project_files)
            except Exception:
                log.warning("invalid_project_files_json", contract_id=contract_id)

    try:
        collected_findings = []
        tool_errors: dict[str, str] = {}
        for tool in tools:
            try:
                if tool == ToolName.SLITHER.value:
                    analyzer_s = SlitherAnalyzer()
                    findings = analyzer_s.analyze_files(project_files, entry_files=entry_files) if project_files else analyzer_s.analyze(source)
                elif tool == ToolName.MYTHRIL.value:
                    analyzer_m = MythrilAnalyzer()
                    findings = analyzer_m.analyze_files(project_files, entry_files=entry_files) if project_files else analyzer_m.analyze(source)
                elif tool == ToolName.ECHIDNA.value:
                    if bytecode_only:
                        log.info("echidna_skipped_bytecode_only", job_id=job_id)
                        findings = []
                    else:
                        from app.analyzers.echidna_analyzer import EchidnaAnalyzer

                        analyzer_e = EchidnaAnalyzer()
                        findings = analyzer_e.analyze_files(project_files, entry_files=entry_files) if project_files else analyzer_e.analyze(source)
                elif tool == ToolName.MEDUSA.value:
                    if bytecode_only:
                        log.info("medusa_skipped_bytecode_only", job_id=job_id)
                        findings = []
                    else:
                        from app.analyzers.medusa_analyzer import MedusaAnalyzer

                        analyzer_med = MedusaAnalyzer()
                        findings = analyzer_med.analyze_files(project_files, entry_files=entry_files) if project_files else analyzer_med.analyze(source)
                else:
                    findings = []
                JOB_TOTAL.labels(tool=tool, status="ok").inc()
                collected_findings.extend(findings)
            except Exception as exc:
                err_msg = str(exc)
                log.error("tool_failed", tool=tool, error=err_msg)
                TOOL_FAILURE.labels(tool=tool, reason=type(exc).__name__).inc()
                tool_errors[tool] = err_msg

        # dedup + persist
        aggregated = aggregate_findings(collected_findings)

        async with session_scope() as session:
            job = await session.get(Job, job_id)
            if job is None:
                log.error("job_disappeared", job_id=job_id)
                return
            job.tool_errors = tool_errors if tool_errors else None
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
            # Cache result by bytecode hash after successful completion
            if bytecode:
                from app.core.cache import set_cached_job_id
                await set_cached_job_id(bytecode, tools, job_id)

    except Exception as exc:
        log.error("analysis_orchestrator_failed", job_id=job_id, error=str(exc))
        async with session_scope() as session:
            job = await session.get(Job, job_id)
            if job is not None:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                job.finished_at = datetime.now(tz=timezone.utc)
        raise

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
def run_analysis_job(self, job_id: str, contract_id: str, tools: list[str], entry_files: list[str] | None = None) -> None:
    start = datetime.now(tz=timezone.utc)
    try:
        asyncio.run(_run(job_id, contract_id, tools, entry_files))
    except Exception as exc:
        log.error("analysis_job_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)
    finally:
        duration = (datetime.now(tz=timezone.utc) - start).total_seconds()
        JOB_DURATION.labels(tool="composite").observe(duration)
