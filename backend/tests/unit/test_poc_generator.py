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


def test_poc_cli_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """When claude CLI is not on PATH, returns a comment stub mentioning the binary name."""
    monkeypatch.setattr("shutil.which", lambda _: None)

    import importlib

    from app.core import poc_generator
    importlib.reload(poc_generator)

    finding = _mk_finding()
    result = asyncio.run(poc_generator.generate_poc(finding))

    assert result.startswith("//")
    assert "Claude CLI" in result


def test_poc_cli_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """When claude CLI exits non-zero, returns a comment stub."""
    import shutil as _shutil
    monkeypatch.setattr(_shutil, "which", lambda _: "/usr/bin/claude")

    async def _fake_exec(*args, **kwargs):
        class _FakeProc:
            returncode = 1
            async def communicate(self):
                return b"", b"auth error"
        return _FakeProc()

    monkeypatch.setattr("asyncio.create_subprocess_exec", _fake_exec)

    import importlib

    from app.core import poc_generator
    importlib.reload(poc_generator)

    finding = _mk_finding()
    result = asyncio.run(poc_generator.generate_poc(finding))

    assert result.startswith("//")
