from __future__ import annotations

from unittest.mock import patch

from app.analyzers.medusa_analyzer import MedusaAnalyzer
from app.core.sandbox import SandboxResult


def test_medusa_timeout_raises():
    from app.analyzers.base import AnalyzerError

    with patch("app.analyzers.medusa_analyzer.run_sandboxed") as mock_run:
        mock_run.return_value = SandboxResult(
            returncode=-1, stdout="", stderr="", timed_out=True
        )
        analyzer = MedusaAnalyzer(binary="medusa-test", timeout=1)
        try:
            analyzer.analyze("contract T {}")
        except AnalyzerError as exc:
            assert "timed out" in str(exc)
        else:
            raise AssertionError("expected AnalyzerError")
