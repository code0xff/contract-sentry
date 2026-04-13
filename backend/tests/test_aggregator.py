"""Aggregator unit tests."""
from __future__ import annotations

from app.reporters.aggregator import aggregate_findings, composite_severity
from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _f(
    vuln: VulnerabilityType = VulnerabilityType.REENTRANCY,
    severity: Severity = Severity.HIGH,
    location: str | None = "Contract.sol:10",
    tool: ToolName = ToolName.SLITHER,
    confidence: float = 0.7,
) -> FindingCreate:
    return FindingCreate(
        tool=tool,
        vulnerability_type=vuln,
        severity=severity,
        title="finding",
        description="desc",
        location=location,
        confidence=confidence,
        evidence=[{"kind": "raw_output", "tool": tool.value}],
    )


# ---------------------------------------------------------------------------
# aggregate_findings
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty() -> None:
    assert aggregate_findings([]) == []


def test_single_finding_passes_through() -> None:
    result = aggregate_findings([_f()])
    assert len(result) == 1
    assert result[0].vulnerability_type == VulnerabilityType.REENTRANCY


def test_deduplicates_same_vuln_and_location() -> None:
    f1 = _f(tool=ToolName.SLITHER)
    f2 = _f(tool=ToolName.MYTHRIL)
    result = aggregate_findings([f1, f2])
    assert len(result) == 1


def test_keeps_distinct_locations() -> None:
    f1 = _f(location="Contract.sol:10")
    f2 = _f(location="Contract.sol:20")
    result = aggregate_findings([f1, f2])
    assert len(result) == 2


def test_keeps_distinct_vuln_types() -> None:
    f1 = _f(vuln=VulnerabilityType.REENTRANCY)
    f2 = _f(vuln=VulnerabilityType.INTEGER_OVERFLOW)
    result = aggregate_findings([f1, f2])
    assert len(result) == 2


def test_upgrades_to_higher_severity() -> None:
    low = _f(severity=Severity.LOW)
    high = _f(severity=Severity.HIGH)
    result = aggregate_findings([low, high])
    assert result[0].severity == Severity.HIGH


def test_severity_not_downgraded() -> None:
    high = _f(severity=Severity.HIGH)
    critical = _f(severity=Severity.CRITICAL)
    result = aggregate_findings([critical, high])
    assert result[0].severity == Severity.CRITICAL


def test_sorted_descending_by_severity() -> None:
    findings = [
        _f(severity=Severity.LOW, location="a"),
        _f(severity=Severity.CRITICAL, location="b"),
        _f(severity=Severity.MEDIUM, location="c"),
        _f(severity=Severity.HIGH, location="d"),
    ]
    result = aggregate_findings(findings)
    severities = [f.severity for f in result]
    assert severities == sorted(
        severities, key=lambda s: -[Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL].index(s)
    )
    assert severities[0] == Severity.CRITICAL
    assert severities[-1] == Severity.LOW


def test_confidence_bumped_on_multi_tool_confirmation() -> None:
    f1 = _f(tool=ToolName.SLITHER, confidence=0.6)
    f2 = _f(tool=ToolName.MYTHRIL, confidence=0.6)
    result = aggregate_findings([f1, f2])
    assert result[0].confidence > 0.6


def test_confidence_capped_at_1_0() -> None:
    f1 = _f(tool=ToolName.SLITHER, confidence=0.99)
    f2 = _f(tool=ToolName.MYTHRIL, confidence=0.99)
    result = aggregate_findings([f1, f2])
    assert result[0].confidence <= 1.0


def test_evidence_merged_from_multiple_tools() -> None:
    f1 = _f(tool=ToolName.SLITHER)
    f2 = _f(tool=ToolName.MYTHRIL)
    result = aggregate_findings([f1, f2])
    assert len(result[0].evidence) == 2


def test_null_location_deduplication() -> None:
    f1 = _f(location=None, tool=ToolName.SLITHER)
    f2 = _f(location=None, tool=ToolName.MYTHRIL)
    result = aggregate_findings([f1, f2])
    assert len(result) == 1


def test_null_and_non_null_location_are_distinct() -> None:
    f1 = _f(location=None)
    f2 = _f(location="Contract.sol:10")
    result = aggregate_findings([f1, f2])
    assert len(result) == 2


# ---------------------------------------------------------------------------
# composite_severity
# ---------------------------------------------------------------------------


def test_composite_severity_empty_returns_info() -> None:
    assert composite_severity([]) == Severity.INFO


def test_composite_severity_single() -> None:
    assert composite_severity([_f(severity=Severity.MEDIUM)]) == Severity.MEDIUM


def test_composite_severity_picks_highest() -> None:
    findings = [
        _f(severity=Severity.LOW, location="a"),
        _f(severity=Severity.CRITICAL, location="b"),
        _f(severity=Severity.MEDIUM, location="c"),
    ]
    assert composite_severity(findings) == Severity.CRITICAL
