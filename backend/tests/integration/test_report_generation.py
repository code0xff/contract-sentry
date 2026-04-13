from __future__ import annotations

import pytest

from app.db.session import session_scope
from app.models.domain import Contract, Finding, Job
from app.schemas.enums import JobStatus, Severity, ToolName, VulnerabilityType
from app.workers.tasks.report_generation import _run as gen_report


@pytest.mark.asyncio
async def test_report_generation(app_instance):
    async with session_scope() as session:
        c = Contract(name="R.sol", language="solidity", source="contract R {}")
        session.add(c)
        await session.flush()
        j = Job(contract_id=c.id, tools=["slither"], status=JobStatus.COMPLETED)
        session.add(j)
        await session.flush()
        job_id = j.id
        session.add(
            Finding(
                job_id=j.id,
                tool=ToolName.SLITHER,
                vulnerability_type=VulnerabilityType.REENTRANCY,
                severity=Severity.HIGH,
                title="reentrancy",
                description="Bad pattern",
                confidence=0.8,
            )
        )

    await gen_report(job_id)

    from sqlalchemy import select

    from app.models.domain import Report

    async with session_scope() as session:
        res = await session.execute(select(Report).where(Report.job_id == job_id))
        report = res.scalar_one()
        assert report.status.value == "ready"
        assert "reentrancy" in (report.markdown or "").lower()
        assert report.summary["total"] == 1
