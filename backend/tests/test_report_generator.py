"""Report generator unit tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.reporters.generator import REMEDIATION, ReportGenerator
from app.schemas.enums import Severity, ToolName, VulnerabilityType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding(
    severity: Severity = Severity.HIGH,
    vuln_type: VulnerabilityType = VulnerabilityType.REENTRANCY,
    tool: ToolName = ToolName.SLITHER,
    title: str = "Reentrancy detected",
    location: str | None = "Contract.sol:42",
    confidence: float = 0.9,
) -> MagicMock:
    f = MagicMock()
    f.id = "f-test-1"
    f.tool = tool
    f.vulnerability_type = vuln_type
    f.severity = severity
    f.title = title
    f.description = "Reentrancy vulnerability found in withdraw()"
    f.location = location
    f.confidence = confidence
    return f


def _job(job_id: str = "job-abc-123") -> MagicMock:
    j = MagicMock()
    j.id = job_id
    return j


# ---------------------------------------------------------------------------
# summary()
# ---------------------------------------------------------------------------


class TestSummary:
    def setup_method(self) -> None:
        self.gen = ReportGenerator()

    def test_empty_findings_returns_zero_total(self) -> None:
        s = self.gen.summary([])
        assert s["total"] == 0

    def test_empty_findings_composite_is_info(self) -> None:
        s = self.gen.summary([])
        assert s["composite_severity"] == "info"

    def test_single_finding_total(self) -> None:
        s = self.gen.summary([_finding()])
        assert s["total"] == 1

    def test_by_severity_counts(self) -> None:
        findings = [
            _finding(severity=Severity.HIGH),
            _finding(severity=Severity.HIGH),
            _finding(severity=Severity.LOW),
        ]
        s = self.gen.summary(findings)
        assert s["by_severity"]["high"] == 2
        assert s["by_severity"]["low"] == 1

    def test_composite_severity_is_highest(self) -> None:
        findings = [
            _finding(severity=Severity.LOW),
            _finding(severity=Severity.CRITICAL),
            _finding(severity=Severity.MEDIUM),
        ]
        s = self.gen.summary(findings)
        assert s["composite_severity"] == "critical"

    def test_missing_severity_not_in_by_severity(self) -> None:
        s = self.gen.summary([_finding(severity=Severity.HIGH)])
        assert "critical" not in s["by_severity"]
        assert "low" not in s["by_severity"]


# ---------------------------------------------------------------------------
# to_json()
# ---------------------------------------------------------------------------


class TestToJson:
    def setup_method(self) -> None:
        self.gen = ReportGenerator()
        self.job = _job()

    def test_structure_has_required_keys(self) -> None:
        result = self.gen.to_json(self.job, [_finding()])
        assert "job_id" in result
        assert "summary" in result
        assert "findings" in result

    def test_job_id_matches(self) -> None:
        result = self.gen.to_json(self.job, [_finding()])
        assert result["job_id"] == "job-abc-123"

    def test_findings_list_length(self) -> None:
        result = self.gen.to_json(self.job, [_finding(), _finding()])
        assert len(result["findings"]) == 2

    def test_finding_entry_has_remediation(self) -> None:
        result = self.gen.to_json(self.job, [_finding(vuln_type=VulnerabilityType.REENTRANCY)])
        assert result["findings"][0]["remediation"] == REMEDIATION["reentrancy"]

    def test_finding_entry_fields(self) -> None:
        result = self.gen.to_json(self.job, [_finding()])
        f = result["findings"][0]
        assert f["severity"] == "high"
        assert f["vulnerability_type"] == "reentrancy"
        assert f["tool"] == "slither"
        assert f["confidence"] == pytest.approx(0.9)

    def test_empty_findings(self) -> None:
        result = self.gen.to_json(self.job, [])
        assert result["findings"] == []
        assert result["summary"]["total"] == 0

    def test_unknown_vuln_type_uses_other_remediation(self) -> None:
        result = self.gen.to_json(self.job, [_finding(vuln_type=VulnerabilityType.OTHER)])
        assert result["findings"][0]["remediation"] == REMEDIATION["other"]


# ---------------------------------------------------------------------------
# to_markdown()
# ---------------------------------------------------------------------------


class TestToMarkdown:
    def setup_method(self) -> None:
        self.gen = ReportGenerator()
        self.job = _job()

    def test_contains_job_id(self) -> None:
        md = self.gen.to_markdown(self.job, [_finding()])
        assert "job-abc-123" in md

    def test_contains_finding_title(self) -> None:
        md = self.gen.to_markdown(self.job, [_finding(title="Critical Reentrancy")])
        assert "Critical Reentrancy" in md

    def test_contains_severity(self) -> None:
        md = self.gen.to_markdown(self.job, [_finding(severity=Severity.CRITICAL)])
        assert "critical" in md

    def test_contains_remediation(self) -> None:
        md = self.gen.to_markdown(self.job, [_finding(vuln_type=VulnerabilityType.REENTRANCY)])
        assert "ReentrancyGuard" in md

    def test_contains_location(self) -> None:
        md = self.gen.to_markdown(self.job, [_finding(location="Vault.sol:100")])
        assert "Vault.sol:100" in md

    def test_severity_breakdown_section(self) -> None:
        md = self.gen.to_markdown(self.job, [_finding(severity=Severity.HIGH)])
        assert "Severity breakdown" in md

    def test_empty_findings_still_renders(self) -> None:
        md = self.gen.to_markdown(self.job, [])
        assert "job-abc-123" in md


# ---------------------------------------------------------------------------
# to_html()
# ---------------------------------------------------------------------------


class TestToHtml:
    def setup_method(self) -> None:
        self.gen = ReportGenerator()
        self.job = _job()

    def test_starts_with_doctype(self) -> None:
        html = self.gen.to_html(self.job, [])
        assert html.startswith("<!doctype html>")

    def test_contains_job_id(self) -> None:
        html = self.gen.to_html(self.job, [_finding()])
        assert "job-abc-123" in html

    def test_contains_title_tag(self) -> None:
        html = self.gen.to_html(self.job, [])
        assert "<title>" in html

    def test_contains_finding_content(self) -> None:
        html = self.gen.to_html(self.job, [_finding(title="Overflow Bug")])
        assert "Overflow Bug" in html
