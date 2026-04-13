from __future__ import annotations

from unittest.mock import patch

from app.analyzers.echidna_analyzer import EchidnaAnalyzer
from app.core.sandbox import SandboxResult
from app.schemas.enums import Severity


def test_echidna_parses_failed_property():
    output = "echidna_balance_never_zero: failed!💥\n"
    with patch("app.analyzers.echidna_analyzer.run_sandboxed") as run:
        run.return_value = SandboxResult(returncode=1, stdout=output, stderr="")
        out = EchidnaAnalyzer().analyze("contract T {}")
        assert len(out) >= 1
        assert out[0].severity == Severity.HIGH
        assert "echidna_balance_never_zero" in out[0].title


def test_echidna_no_failures():
    with patch("app.analyzers.echidna_analyzer.run_sandboxed") as run:
        run.return_value = SandboxResult(returncode=0, stdout="All tests passed", stderr="")
        out = EchidnaAnalyzer().analyze("contract T {}")
        assert out == []
