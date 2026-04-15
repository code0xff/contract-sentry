"""Echidna fuzzer adapter."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from app.analyzers.base import AnalyzerError, BaseAnalyzer
from app.config import get_settings
from app.core.sandbox import SandboxError, run_sandboxed
from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate

FAIL_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):?\s+(failed|FAILED|❌)", re.MULTILINE)


class EchidnaAnalyzer(BaseAnalyzer):
    tool_name = "echidna"

    def __init__(self, binary: str | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.binary = binary or settings.echidna_bin
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
                    [self.binary, entry, "--format", "text"],
                    timeout=self.timeout,
                    cwd=str(tmp),
                )
            except SandboxError as exc:
                raise AnalyzerError(f"echidna not available: {exc}") from exc

            if result.timed_out:
                raise AnalyzerError(f"echidna timed out after {self.timeout}s")

            return self._parse(result.stdout + "\n" + result.stderr)

    def analyze(self, source: str) -> list[FindingCreate]:
        if not source:
            return []

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / "Contract.sol"
            src_path.write_text(source, encoding="utf-8")

            try:
                result = run_sandboxed(
                    [self.binary, str(src_path), "--format", "text"],
                    timeout=self.timeout,
                )
            except SandboxError as exc:
                raise AnalyzerError(f"echidna not available: {exc}") from exc

            if result.timed_out:
                raise AnalyzerError(f"echidna timed out after {self.timeout}s")

            return self._parse(result.stdout + "\n" + result.stderr)

    def _parse(self, text: str) -> list[FindingCreate]:
        out: list[FindingCreate] = []
        for match in FAIL_LINE_RE.finditer(text):
            prop = match.group(1)
            out.append(
                FindingCreate(
                    tool=ToolName.ECHIDNA,
                    vulnerability_type=VulnerabilityType.OTHER,
                    severity=Severity.HIGH,
                    title=f"Property violation: {prop}",
                    description=f"Echidna found a counter-example for property `{prop}`.",
                    confidence=0.85,
                    evidence=[
                        {
                            "kind": "counter_example",
                            "tool": "echidna",
                            "property": prop,
                            "raw": text[max(0, match.start() - 200) : match.end() + 200],
                        }
                    ],
                )
            )
        return out
