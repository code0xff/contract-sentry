from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.analyzers.base import AnalyzerError
from app.analyzers.mythril_analyzer import MythrilAnalyzer
from app.core.sandbox import SandboxResult
from app.schemas.enums import Severity, VulnerabilityType

SAMPLE = {
    "issues": [
        {
            "swc-id": "107",
            "severity": "High",
            "title": "External Call",
            "description": "reentrancy",
            "filename": "A.sol",
            "lineno": 10,
        }
    ]
}


def test_mythril_parses_findings():
    with patch("app.analyzers.mythril_analyzer.run_sandboxed") as run:
        run.return_value = SandboxResult(returncode=0, stdout=json.dumps(SAMPLE), stderr="")
        out = MythrilAnalyzer().analyze("contract A {}")
        assert len(out) == 1
        assert out[0].severity == Severity.HIGH
        assert out[0].vulnerability_type == VulnerabilityType.REENTRANCY
        assert out[0].location == "A.sol:10"


def test_mythril_empty_output():
    with patch("app.analyzers.mythril_analyzer.run_sandboxed") as run:
        run.return_value = SandboxResult(returncode=0, stdout="", stderr="")
        assert MythrilAnalyzer().analyze("contract A {}") == []


def test_mythril_timeout():
    with patch("app.analyzers.mythril_analyzer.run_sandboxed") as run:
        run.return_value = SandboxResult(returncode=-1, stdout="", stderr="", timed_out=True)
        with pytest.raises(AnalyzerError):
            MythrilAnalyzer().analyze("contract A {}")
