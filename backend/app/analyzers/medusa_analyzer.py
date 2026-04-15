"""Medusa fuzzer adapter."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from app.analyzers.base import (
    AnalyzerError,
    BaseAnalyzer,
    analyzer_error_from_sandbox,
    choose_fuzz_entry_file,
)
from app.config import get_settings
from app.core.sandbox import SandboxError, format_cmd, run_sandboxed
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

            entry_key = choose_fuzz_entry_file(files, entry_files=entry_files)
            if entry_key is None:
                raise AnalyzerError(
                    "medusa failed",
                    tool=self.tool_name,
                    stage="preflight",
                    detail="No suitable fuzz target found in the selected entry files. Excluded interface-only files and dependency-style paths.",
                )
            entry = str(tmp / entry_key)
            cmd = [self.binary, "fuzz", "--target", entry, "--timeout", str(self.timeout)]

            try:
                result = run_sandboxed(cmd, timeout=self.timeout, cwd=str(tmp))
            except SandboxError as exc:
                raise AnalyzerError(
                    "medusa not available",
                    tool=self.tool_name,
                    stage="spawn",
                    detail=str(exc),
                    command=format_cmd(cmd),
                ) from exc

            if result.timed_out:
                raise analyzer_error_from_sandbox(
                    self.tool_name,
                    "execute",
                    f"medusa timed out after {self.timeout}s",
                    cmd=cmd,
                    result=result,
                )

            findings = self._parse(result.stdout + "\n" + result.stderr)
            if result.returncode != 0 and not findings:
                raise analyzer_error_from_sandbox(
                    self.tool_name,
                    "execute",
                    "medusa failed",
                    cmd=cmd,
                    result=result,
                )
            return findings

    def analyze(self, source: str) -> list[FindingCreate]:
        if not source:
            return []

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / "Contract.sol"
            src_path.write_text(source, encoding="utf-8")
            cmd = [self.binary, "fuzz", "--target", str(src_path), "--timeout", str(self.timeout)]

            try:
                result = run_sandboxed(cmd, timeout=self.timeout)
            except SandboxError as exc:
                raise AnalyzerError(
                    "medusa not available",
                    tool=self.tool_name,
                    stage="spawn",
                    detail=str(exc),
                    command=format_cmd(cmd),
                ) from exc

            if result.timed_out:
                raise analyzer_error_from_sandbox(
                    self.tool_name,
                    "execute",
                    f"medusa timed out after {self.timeout}s",
                    cmd=cmd,
                    result=result,
                )

            findings = self._parse(result.stdout + "\n" + result.stderr)
            if result.returncode != 0 and not findings:
                raise analyzer_error_from_sandbox(
                    self.tool_name,
                    "execute",
                    "medusa failed",
                    cmd=cmd,
                    result=result,
                )
            return findings

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
