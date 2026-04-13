"""Analyzer unit tests.

All subprocess calls are mocked — no actual tools (slither/mythril/echidna)
need to be installed for these tests to pass.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.analyzers.base import AnalyzerError
from app.analyzers.echidna_analyzer import EchidnaAnalyzer
from app.analyzers.mythril_analyzer import MythrilAnalyzer
from app.analyzers.slither_analyzer import SlitherAnalyzer
from app.core.sandbox import SandboxError, SandboxResult
from app.schemas.enums import Severity, VulnerabilityType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SLITHER_REENTRANCY_OUTPUT = json.dumps(
    {
        "success": True,
        "error": None,
        "results": {
            "detectors": [
                {
                    "check": "reentrancy-eth",
                    "impact": "High",
                    "confidence": "Medium",
                    "description": "Reentrancy in withdraw()",
                    "elements": [
                        {
                            "source_mapping": {
                                "filename_short": "Contract.sol",
                                "lines": [42],
                            }
                        }
                    ],
                }
            ]
        },
    }
)

SLITHER_MULTI_OUTPUT = json.dumps(
    {
        "success": True,
        "error": None,
        "results": {
            "detectors": [
                {
                    "check": "reentrancy-eth",
                    "impact": "High",
                    "confidence": "High",
                    "description": "Reentrancy in withdraw()",
                    "elements": [
                        {"source_mapping": {"filename_short": "C.sol", "lines": [10]}}
                    ],
                },
                {
                    "check": "timestamp",
                    "impact": "Medium",
                    "confidence": "Low",
                    "description": "Block timestamp dependency.",
                    "elements": [
                        {"source_mapping": {"filename_short": "C.sol", "lines": [20]}}
                    ],
                },
            ]
        },
    }
)

MYTHRIL_REENTRANCY_OUTPUT = json.dumps(
    {
        "success": True,
        "issues": [
            {
                "swc-id": "107",
                "title": "Reentrancy",
                "description": "External call followed by state change.",
                "severity": "High",
                "filename": "Contract.sol",
                "lineno": 15,
            }
        ],
    }
)

MYTHRIL_OVERFLOW_OUTPUT = json.dumps(
    {
        "success": True,
        "issues": [
            {
                "swc-id": "101",
                "title": "Integer Overflow",
                "description": "Integer overflow in add().",
                "severity": "Medium",
                "filename": "Contract.sol",
                "lineno": 30,
            }
        ],
    }
)


def _ok(stdout: str, returncode: int = 0) -> SandboxResult:
    return SandboxResult(returncode=returncode, stdout=stdout, stderr="", timed_out=False)


def _timeout() -> SandboxResult:
    return SandboxResult(returncode=-1, stdout="", stderr="timed out", timed_out=True)


# ---------------------------------------------------------------------------
# SlitherAnalyzer
# ---------------------------------------------------------------------------


class TestSlitherAnalyzer:
    def test_empty_source_skips_execution(self) -> None:
        result = SlitherAnalyzer().analyze("")
        assert result == []

    def test_parses_reentrancy_finding(self) -> None:
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed",
            return_value=_ok(SLITHER_REENTRANCY_OUTPUT),
        ):
            findings = SlitherAnalyzer().analyze("contract Vault {}")

        assert len(findings) == 1
        f = findings[0]
        assert f.vulnerability_type == VulnerabilityType.REENTRANCY
        assert f.severity == Severity.HIGH
        assert f.location == "Contract.sol:42"
        assert f.confidence == pytest.approx(0.6)  # Medium → 0.6

    def test_parses_multiple_findings(self) -> None:
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed",
            return_value=_ok(SLITHER_MULTI_OUTPUT),
        ):
            findings = SlitherAnalyzer().analyze("contract C {}")

        assert len(findings) == 2
        types = {f.vulnerability_type for f in findings}
        assert VulnerabilityType.REENTRANCY in types
        assert VulnerabilityType.TIMESTAMP_DEPENDENCY in types

    def test_unknown_check_maps_to_other(self) -> None:
        data = json.dumps(
            {
                "success": True,
                "error": None,
                "results": {
                    "detectors": [
                        {
                            "check": "some-unknown-check",
                            "impact": "Low",
                            "confidence": "Low",
                            "description": "Unknown issue.",
                            "elements": [],
                        }
                    ]
                },
            }
        )
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed", return_value=_ok(data)
        ):
            findings = SlitherAnalyzer().analyze("contract C {}")

        assert findings[0].vulnerability_type == VulnerabilityType.OTHER

    def test_timed_out_raises_analyzer_error(self) -> None:
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed", return_value=_timeout()
        ):
            with pytest.raises(AnalyzerError, match="timed out"):
                SlitherAnalyzer().analyze("contract C {}")

    def test_binary_not_found_raises_analyzer_error(self) -> None:
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed",
            side_effect=SandboxError("executable not found"),
        ):
            with pytest.raises(AnalyzerError, match="not available"):
                SlitherAnalyzer().analyze("contract C {}")

    def test_invalid_json_raises_analyzer_error(self) -> None:
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed",
            return_value=_ok("not-valid-json"),
        ):
            with pytest.raises(AnalyzerError, match="invalid JSON"):
                SlitherAnalyzer().analyze("contract C {}")

    def test_nonzero_exit_with_empty_stdout_raises(self) -> None:
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed",
            return_value=SandboxResult(
                returncode=1, stdout="", stderr="compilation failed", timed_out=False
            ),
        ):
            with pytest.raises(AnalyzerError, match="slither failed"):
                SlitherAnalyzer().analyze("contract C {}")

    def test_empty_detectors_list_returns_no_findings(self) -> None:
        data = json.dumps({"success": True, "error": None, "results": {"detectors": []}})
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed", return_value=_ok(data)
        ):
            findings = SlitherAnalyzer().analyze("contract C {}")
        assert findings == []

    def test_evidence_payload_contains_raw_output(self) -> None:
        with patch(
            "app.analyzers.slither_analyzer.run_sandboxed",
            return_value=_ok(SLITHER_REENTRANCY_OUTPUT),
        ):
            findings = SlitherAnalyzer().analyze("contract C {}")
        assert findings[0].evidence[0]["kind"] == "raw_output"
        assert findings[0].evidence[0]["tool"] == "slither"


# ---------------------------------------------------------------------------
# MythrilAnalyzer
# ---------------------------------------------------------------------------


class TestMythrilAnalyzer:
    def test_empty_source_skips_execution(self) -> None:
        assert MythrilAnalyzer().analyze("") == []

    def test_parses_reentrancy_finding(self) -> None:
        with patch(
            "app.analyzers.mythril_analyzer.run_sandboxed",
            return_value=_ok(MYTHRIL_REENTRANCY_OUTPUT),
        ):
            findings = MythrilAnalyzer().analyze("contract C {}")

        assert len(findings) == 1
        f = findings[0]
        assert f.vulnerability_type == VulnerabilityType.REENTRANCY
        assert f.severity == Severity.HIGH
        assert f.location == "Contract.sol:15"

    def test_parses_overflow_finding(self) -> None:
        with patch(
            "app.analyzers.mythril_analyzer.run_sandboxed",
            return_value=_ok(MYTHRIL_OVERFLOW_OUTPUT),
        ):
            findings = MythrilAnalyzer().analyze("contract C {}")

        assert findings[0].vulnerability_type == VulnerabilityType.INTEGER_OVERFLOW
        assert findings[0].severity == Severity.MEDIUM

    def test_empty_stdout_returns_no_findings(self) -> None:
        with patch(
            "app.analyzers.mythril_analyzer.run_sandboxed", return_value=_ok("")
        ):
            assert MythrilAnalyzer().analyze("contract C {}") == []

    def test_unknown_swc_maps_to_other(self) -> None:
        data = json.dumps(
            {
                "issues": [
                    {
                        "swc-id": "999",
                        "title": "Unknown",
                        "description": "Unknown issue.",
                        "severity": "Low",
                    }
                ]
            }
        )
        with patch(
            "app.analyzers.mythril_analyzer.run_sandboxed", return_value=_ok(data)
        ):
            findings = MythrilAnalyzer().analyze("contract C {}")
        assert findings[0].vulnerability_type == VulnerabilityType.OTHER

    def test_timed_out_raises_analyzer_error(self) -> None:
        with patch(
            "app.analyzers.mythril_analyzer.run_sandboxed", return_value=_timeout()
        ):
            with pytest.raises(AnalyzerError, match="timed out"):
                MythrilAnalyzer().analyze("contract C {}")

    def test_binary_not_found_raises_analyzer_error(self) -> None:
        with patch(
            "app.analyzers.mythril_analyzer.run_sandboxed",
            side_effect=SandboxError("not found"),
        ):
            with pytest.raises(AnalyzerError, match="not available"):
                MythrilAnalyzer().analyze("contract C {}")

    def test_invalid_json_raises_analyzer_error(self) -> None:
        with patch(
            "app.analyzers.mythril_analyzer.run_sandboxed",
            return_value=_ok("not-json"),
        ):
            with pytest.raises(AnalyzerError, match="invalid JSON"):
                MythrilAnalyzer().analyze("contract C {}")

    def test_confidence_fixed_at_0_7(self) -> None:
        with patch(
            "app.analyzers.mythril_analyzer.run_sandboxed",
            return_value=_ok(MYTHRIL_REENTRANCY_OUTPUT),
        ):
            findings = MythrilAnalyzer().analyze("contract C {}")
        assert findings[0].confidence == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# EchidnaAnalyzer
# ---------------------------------------------------------------------------


class TestEchidnaAnalyzer:
    def test_empty_source_skips_execution(self) -> None:
        assert EchidnaAnalyzer().analyze("") == []

    def test_parses_single_property_violation(self) -> None:
        output = "echidna_no_overflow: failed\nechidna_invariant: passed"
        with patch(
            "app.analyzers.echidna_analyzer.run_sandboxed", return_value=_ok(output)
        ):
            findings = EchidnaAnalyzer().analyze("contract C {}")

        assert len(findings) == 1
        f = findings[0]
        assert "echidna_no_overflow" in f.title
        assert f.severity == Severity.HIGH
        assert f.evidence[0]["kind"] == "counter_example"

    def test_parses_multiple_property_violations(self) -> None:
        output = "prop_a: FAILED\nprop_b: FAILED\nprop_c: passed"
        with patch(
            "app.analyzers.echidna_analyzer.run_sandboxed", return_value=_ok(output)
        ):
            findings = EchidnaAnalyzer().analyze("contract C {}")

        assert len(findings) == 2

    def test_no_violations_returns_empty(self) -> None:
        output = "prop_a: passed\nprop_b: passed"
        with patch(
            "app.analyzers.echidna_analyzer.run_sandboxed", return_value=_ok(output)
        ):
            assert EchidnaAnalyzer().analyze("contract C {}") == []

    def test_timed_out_raises_analyzer_error(self) -> None:
        with patch(
            "app.analyzers.echidna_analyzer.run_sandboxed", return_value=_timeout()
        ):
            with pytest.raises(AnalyzerError, match="timed out"):
                EchidnaAnalyzer().analyze("contract C {}")

    def test_binary_not_found_raises_analyzer_error(self) -> None:
        with patch(
            "app.analyzers.echidna_analyzer.run_sandboxed",
            side_effect=SandboxError("not found"),
        ):
            with pytest.raises(AnalyzerError, match="not available"):
                EchidnaAnalyzer().analyze("contract C {}")

    def test_confidence_fixed_at_0_85(self) -> None:
        output = "echidna_prop: failed"
        with patch(
            "app.analyzers.echidna_analyzer.run_sandboxed", return_value=_ok(output)
        ):
            findings = EchidnaAnalyzer().analyze("contract C {}")
        assert findings[0].confidence == pytest.approx(0.85)
