"""Unit tests for finding diff logic."""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingDiff, FindingOut


def _utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _mk(
    fid: str,
    job_id: str,
    vuln_type: VulnerabilityType,
    location: str | None,
    severity: Severity = Severity.MEDIUM,
) -> FindingOut:
    return FindingOut(
        id=fid,
        job_id=job_id,
        tool=ToolName.SLITHER,
        vulnerability_type=vuln_type,
        severity=severity,
        title=f"{vuln_type.value}",
        description="test finding",
        location=location,
        confidence=0.5,
        created_at=_utc(),
        evidences=[],
    )


def _diff(findings_a: list[FindingOut], findings_b: list[FindingOut]) -> FindingDiff:
    """Pure diff logic extracted from the endpoint (mirrors jobs.py:134 key logic)."""
    keys_a = {(f.vulnerability_type, f.location or "", f.title): f for f in findings_a}
    keys_b = {(f.vulnerability_type, f.location or "", f.title): f for f in findings_b}

    new_findings = [f for k, f in keys_b.items() if k not in keys_a]
    fixed_findings = [f for k, f in keys_a.items() if k not in keys_b]
    persisting_findings = [f for k, f in keys_b.items() if k in keys_a]

    return FindingDiff(
        new=new_findings,
        fixed=fixed_findings,
        persisting=persisting_findings,
        summary={
            "new": len(new_findings),
            "fixed": len(fixed_findings),
            "persisting": len(persisting_findings),
        },
    )


def test_diff_empty_jobs():
    result = _diff([], [])
    assert result.new == []
    assert result.fixed == []
    assert result.persisting == []
    assert result.summary == {"new": 0, "fixed": 0, "persisting": 0}


def test_diff_new_finding():
    """job_b has a finding not in job_a — it appears in new."""
    b = _mk("b1", "job-b", VulnerabilityType.REENTRANCY, "A.sol:10")
    result = _diff([], [b])
    assert len(result.new) == 1
    assert result.new[0].id == "b1"
    assert len(result.fixed) == 0
    assert len(result.persisting) == 0
    assert result.summary["new"] == 1
    assert result.summary["fixed"] == 0
    assert result.summary["persisting"] == 0


def test_diff_fixed_finding():
    """job_a has a finding not in job_b — it appears in fixed."""
    a = _mk("a1", "job-a", VulnerabilityType.INTEGER_OVERFLOW, "B.sol:5")
    result = _diff([a], [])
    assert len(result.fixed) == 1
    assert result.fixed[0].id == "a1"
    assert len(result.new) == 0
    assert len(result.persisting) == 0
    assert result.summary["fixed"] == 1
    assert result.summary["new"] == 0
    assert result.summary["persisting"] == 0


def test_diff_persisting():
    """Same (vulnerability_type, location, title) in both jobs — appears in persisting."""
    a = _mk("a1", "job-a", VulnerabilityType.REENTRANCY, "C.sol:20")
    b = _mk("b1", "job-b", VulnerabilityType.REENTRANCY, "C.sol:20")
    result = _diff([a], [b])
    assert len(result.persisting) == 1
    assert result.persisting[0].id == "b1"
    assert len(result.new) == 0
    assert len(result.fixed) == 0
    assert result.summary["persisting"] == 1
    assert result.summary["new"] == 0
    assert result.summary["fixed"] == 0
