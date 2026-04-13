from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.analyzers.base import AnalyzerError
from app.analyzers.slither_analyzer import SlitherAnalyzer
from app.core.sandbox import SandboxResult
from app.schemas.enums import Severity, VulnerabilityType

SAMPLE = {
    "results": {
        "detectors": [
            {
                "check": "reentrancy-eth",
                "impact": "High",
                "confidence": "High",
                "description": "reentrancy",
                "elements": [
                    {"source_mapping": {"filename_short": "A.sol", "lines": [12]}}
                ],
            }
        ]
    }
}


def test_slither_empty_source_returns_empty():
    assert SlitherAnalyzer().analyze("") == []


def test_slither_parses_findings():
    with patch("app.analyzers.slither_analyzer.run_sandboxed") as run:
        run.return_value = SandboxResult(returncode=0, stdout=json.dumps(SAMPLE), stderr="")
        out = SlitherAnalyzer().analyze("contract A {}")
        assert len(out) == 1
        assert out[0].severity == Severity.HIGH
        assert out[0].vulnerability_type == VulnerabilityType.REENTRANCY
        assert out[0].location == "A.sol:12"


def test_slither_timeout_raises():
    with patch("app.analyzers.slither_analyzer.run_sandboxed") as run:
        run.return_value = SandboxResult(returncode=-1, stdout="", stderr="", timed_out=True)
        with pytest.raises(AnalyzerError):
            SlitherAnalyzer().analyze("contract A {}")


def test_slither_invalid_json_raises():
    with patch("app.analyzers.slither_analyzer.run_sandboxed") as run:
        run.return_value = SandboxResult(returncode=0, stdout="not-json", stderr="")
        with pytest.raises(AnalyzerError):
            SlitherAnalyzer().analyze("contract A {}")


def test_slither_missing_binary_raises():
    from app.core.sandbox import SandboxError

    with patch("app.analyzers.slither_analyzer.run_sandboxed") as run:
        run.side_effect = SandboxError("no slither")
        with pytest.raises(AnalyzerError):
            SlitherAnalyzer().analyze("contract A {}")
