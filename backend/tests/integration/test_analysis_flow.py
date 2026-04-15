"""End-to-end integration test with analyzers mocked.

Exercises the static-analysis worker coroutine directly so we don't depend
on a running Celery broker. Verifies that a Pending job transitions to
Completed and that Findings are persisted.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.models.domain import Contract, Finding, Job
from app.schemas.enums import JobStatus, Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate
from app.workers.tasks.static_analysis import _run as run_job_async


@pytest.mark.asyncio
async def test_full_flow_mocked(app_instance):
    # Use the app-backed session
    from app.db.session import session_scope

    async with session_scope() as session:
        contract = Contract(
            name="Vuln.sol",
            language="solidity",
            source="contract V { function withdraw() public { msg.sender.call{value:1}(''); } }",
        )
        session.add(contract)
        await session.flush()
        job = Job(contract_id=contract.id, tools=["slither"], status=JobStatus.PENDING)
        session.add(job)
        await session.flush()
        job_id = job.id
        contract_id = contract.id

    fake_findings = [
        FindingCreate(
            tool=ToolName.SLITHER,
            vulnerability_type=VulnerabilityType.REENTRANCY,
            severity=Severity.HIGH,
            title="reentrancy-eth",
            description="external call before state update",
            location="Vuln.sol:3",
            confidence=0.9,
        )
    ]

    with patch("app.workers.tasks.static_analysis.SlitherAnalyzer") as slither_cls, patch(
        "app.workers.tasks.static_analysis.MythrilAnalyzer"
    ) as mythril_cls:
        slither_cls.return_value.analyze.return_value = fake_findings
        mythril_cls.return_value.analyze.return_value = []
        await run_job_async(job_id, contract_id, ["slither"])

    from sqlalchemy import select

    async with session_scope() as session:
        refreshed = await session.get(Job, job_id)
        assert refreshed is not None
        assert refreshed.status == JobStatus.COMPLETED
        assert refreshed.progress == 100
        findings_res = await session.execute(select(Finding).where(Finding.job_id == job_id))
        findings = list(findings_res.scalars().all())
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH


@pytest.mark.asyncio
async def test_analysis_persists_auto_resolved_project_files(app_instance):
    from app.db.session import session_scope

    original_files = {
        "src/Main.sol": 'pragma solidity ^0.8.20;\nimport "@vendor/Dep.sol";\ncontract Main {}',
        "deps/Dep.sol": "pragma solidity ^0.8.20;\ncontract Dep {}",
    }
    resolved_files = {
        **original_files,
        "@vendor/Dep.sol": "pragma solidity ^0.8.20;\ncontract Dep {}",
    }

    async with session_scope() as session:
        contract = Contract(
            name="Main.sol",
            language="solidity",
            source=original_files["src/Main.sol"],
            project_files=json.dumps(original_files),
        )
        session.add(contract)
        await session.flush()
        job = Job(contract_id=contract.id, tools=["slither"], status=JobStatus.PENDING)
        session.add(job)
        await session.flush()
        job_id = job.id
        contract_id = contract.id

    with patch(
        "app.core.compile_check.check_compilation_with_fallback",
        return_value={
            "success": True,
            "missing": [],
            "errors": [],
            "auto_resolved": [
                {
                    "missing_path": "@vendor/Dep.sol",
                    "matched_path": "deps/Dep.sol",
                }
            ],
            "ambiguous": [],
            "files": resolved_files,
        },
    ), patch("app.workers.tasks.static_analysis.SlitherAnalyzer") as slither_cls:
        slither_cls.return_value.analyze_files.return_value = []
        await run_job_async(job_id, contract_id, ["slither"])

    slither_cls.return_value.analyze_files.assert_called_once_with(resolved_files, entry_files=None)

    async with session_scope() as session:
        refreshed_contract = await session.get(Contract, contract_id)
        assert refreshed_contract is not None
        assert json.loads(refreshed_contract.project_files) == resolved_files
