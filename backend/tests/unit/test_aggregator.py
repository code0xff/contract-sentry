from __future__ import annotations

from app.reporters.aggregator import aggregate_findings, composite_severity
from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate


def _mk(vt: VulnerabilityType, sev: Severity, tool: ToolName, loc: str | None = None, conf: float = 0.5):
    return FindingCreate(
        tool=tool,
        vulnerability_type=vt,
        severity=sev,
        title=f"{vt.value}-{tool.value}",
        description="d",
        location=loc,
        confidence=conf,
        evidence=[{"kind": "raw_output", "tool": tool.value}],
    )


def test_aggregate_dedup_same_type_and_location():
    a = _mk(VulnerabilityType.REENTRANCY, Severity.MEDIUM, ToolName.SLITHER, "A.sol:10", 0.5)
    b = _mk(VulnerabilityType.REENTRANCY, Severity.HIGH, ToolName.MYTHRIL, "A.sol:10", 0.7)
    out = aggregate_findings([a, b])
    assert len(out) == 1
    # highest severity kept
    assert out[0].severity == Severity.HIGH
    # evidence merged
    assert len(out[0].evidence) == 2
    # confidence boosted but clamped to 1.0
    assert out[0].confidence <= 1.0
    assert out[0].confidence >= 0.7


def test_aggregate_distinct_locations_kept():
    a = _mk(VulnerabilityType.REENTRANCY, Severity.MEDIUM, ToolName.SLITHER, "A.sol:10")
    b = _mk(VulnerabilityType.REENTRANCY, Severity.HIGH, ToolName.SLITHER, "B.sol:5")
    out = aggregate_findings([a, b])
    assert len(out) == 2


def test_aggregate_sorted_by_severity():
    low = _mk(VulnerabilityType.OTHER, Severity.LOW, ToolName.SLITHER, "x")
    crit = _mk(VulnerabilityType.REENTRANCY, Severity.CRITICAL, ToolName.MYTHRIL, "y")
    out = aggregate_findings([low, crit])
    assert out[0].severity == Severity.CRITICAL


def test_composite_severity_empty():
    assert composite_severity([]) == Severity.INFO


def test_composite_severity_picks_max():
    items = [
        _mk(VulnerabilityType.OTHER, Severity.LOW, ToolName.SLITHER, "1"),
        _mk(VulnerabilityType.REENTRANCY, Severity.HIGH, ToolName.MYTHRIL, "2"),
    ]
    assert composite_severity(items) == Severity.HIGH
