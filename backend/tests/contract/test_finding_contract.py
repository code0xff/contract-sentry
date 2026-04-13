"""Finding/Evidence schema contract."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate


def test_finding_minimum_fields():
    f = FindingCreate(
        tool=ToolName.SLITHER,
        vulnerability_type=VulnerabilityType.REENTRANCY,
        severity=Severity.HIGH,
        title="reentrancy",
        description="desc",
    )
    assert f.confidence == 0.5
    assert f.evidence == []


def test_finding_confidence_bounds():
    with pytest.raises(ValidationError):
        FindingCreate(
            tool=ToolName.SLITHER,
            vulnerability_type=VulnerabilityType.OTHER,
            severity=Severity.LOW,
            title="t",
            description="d",
            confidence=2.0,
        )


def test_finding_accepts_evidence_payload():
    f = FindingCreate(
        tool=ToolName.ECHIDNA,
        vulnerability_type=VulnerabilityType.OTHER,
        severity=Severity.HIGH,
        title="property violated",
        description="d",
        evidence=[{"kind": "counter_example", "property": "invariant"}],
    )
    assert f.evidence[0]["kind"] == "counter_example"
