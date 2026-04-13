"""Unit tests for PoC generator."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingOut


def _utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _mk_finding() -> FindingOut:
    return FindingOut(
        id="test-id",
        job_id="test-job",
        tool=ToolName.SLITHER,
        vulnerability_type=VulnerabilityType.REENTRANCY,
        severity=Severity.HIGH,
        title="Reentrancy in withdraw()",
        description="The withdraw function is vulnerable to reentrancy.",
        location="Vault.sol:42",
        confidence=0.9,
        created_at=datetime.now(tz=timezone.utc),
        evidences=[],
    )


def test_poc_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ANTHROPIC_API_KEY is None, returns a comment string mentioning ANTHROPIC_API_KEY."""
    from app import config as cfg

    monkeypatch.setattr(cfg.settings, "ANTHROPIC_API_KEY", None)

    from app.core import poc_generator

    finding = _mk_finding()
    result = asyncio.run(poc_generator.generate_poc(finding))

    assert "ANTHROPIC_API_KEY" in result
    assert result.startswith("//")
