"""Medusa fuzzer adapter."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from app.analyzers.base import AnalyzerError, BaseAnalyzer
from app.config import get_settings
from app.core.sandbox import SandboxError, run_sandboxed
from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate

VIOLATION_LINE_RE = re.compile(
    r"(FAILED|violation|property\s+\w)",
    re.MULTILINE | re.IGNORECASE,
)


class MedusaAnalyzer(BaseAnalyzer):
    tool_name = "medusa"

    def __init__(self, binary: str | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.binary = binary or "medusa"
        self.timeout = timeout or settings.dynamic_analysis_timeout_s

    def analyze_files(self, files: dict[str, str], entry_files: list[str] | None = None) -> list[FindingCreate]:
        if not files:
            return []

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for rel_path, content in files.items():
                dest = tmp / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")

            entry = str(tmp / sorted(files.keys())[0])

            try:
                result = run_sandboxed(
                    [self.binary, "fuzz", "--target", entry, "--timeout", str(self.timeout)],
                    timeout=self.timeout,
                    cwd=str(tmp),
                )
            except SandboxError as exc:
                raise AnalyzerError(f"medusa not available: {exc}") from exc

            if result.timed_out:
                raise AnalyzerError(f"medusa timed out after {self.timeout}s")

            return self._parse(result.stdout + "\n" + result.stderr)

    def analyze(self, source: str) -> list[FindingCreate]:
        if not source:
            return []

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / "Contract.sol"
            src_path.write_text(source, encoding="utf-8")

            try:
                result = run_sandboxed(
                    [self.binary, "fuzz", "--target", str(src_path), "--timeout", str(self.timeout)],
                    timeout=self.timeout,
                )
            except SandboxError as exc:
                raise AnalyzerError(f"medusa not available: {exc}") from exc

            if result.timed_out:
                raise AnalyzerError(f"medusa timed out after {self.timeout}s")

            return self._parse(result.stdout + "\n" + result.stderr)

    def _parse(self, text: str) -> list[FindingCreate]:
        out: list[FindingCreate] = []
        for match in VIOLATION_LINE_RE.finditer(text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end].strip()
            out.append(
                FindingCreate(
                    tool=ToolName.MEDUSA,
                    vulnerability_type=VulnerabilityType.OTHER,
                    severity=Severity.MEDIUM,
                    title=f"Medusa violation: {line[:120]}",
                    description=f"Medusa found a property violation: {line}",
                    confidence=0.80,
                    evidence=[
                        {
                            "kind": "violation",
                            "tool": "medusa",
                            "line": line,
                            "raw": text[max(0, match.start() - 200) : match.end() + 200],
                        }
                    ],
                )
            )
        return out
