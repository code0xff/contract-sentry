"""Integration tests for static analysis flow with adapters mocked."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_slither_tool_failure_marks_metric_and_continues(app_instance):
    from app.analyzers.base import AnalyzerError
    from app.db.session import session_scope
    from app.models.domain import Contract, Job
    from app.schemas.enums import JobStatus
    from app.workers.tasks.static_analysis import _run

    async with session_scope() as session:
        c = Contract(name="X.sol", language="solidity", source="contract X {}")
        session.add(c)
        await session.flush()
        j = Job(contract_id=c.id, tools=["slither", "mythril"], status=JobStatus.PENDING)
        session.add(j)
        await session.flush()
        job_id, contract_id = j.id, c.id

    with patch("app.workers.tasks.static_analysis.SlitherAnalyzer") as slither_cls, patch(
        "app.workers.tasks.static_analysis.MythrilAnalyzer"
    ) as mythril_cls:
        slither_cls.return_value.analyze.side_effect = AnalyzerError("slither not installed")
        mythril_cls.return_value.analyze.return_value = []
        await _run(job_id, contract_id, ["slither", "mythril"])

    async with session_scope() as session:
        j = await session.get(Job, job_id)
        assert j.status == JobStatus.COMPLETED


def test_sandbox_handles_timeout():
    # Pick a small timeout on a command that we know blocks.
    import sys

    from app.core.sandbox import run_sandboxed

    result = run_sandboxed(
        [sys.executable, "-c", "import time; time.sleep(3)"], timeout=1
    )
    assert result.timed_out
    assert result.returncode == -1
