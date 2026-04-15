"""Echidna fuzzer adapter."""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from app.analyzers.base import (
    AnalyzerError,
    BaseAnalyzer,
    analyzer_error_from_sandbox,
    build_solc_remappings,
    choose_fuzz_entry_file,
    resolve_npm_deps,
)
from app.config import get_settings
from app.core.sandbox import SandboxError, format_cmd, run_sandboxed
from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate

FAIL_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):?\s+(failed|FAILED|❌)", re.MULTILINE)
_COMPILE_ERROR_MARKERS = (
    "source ",
    "parsererror",
    "declarationerror",
    "typeerror",
    "file not found",
)


def _build_crytic_compile_config(tmpdir: Path, remappings: list[str]) -> Path:
    allow_paths = [str(tmpdir)]
    for remapping in remappings:
        _, _, target = remapping.partition("=")
        if target and target not in allow_paths:
            allow_paths.append(target)

    config_path = tmpdir / "crytic_compile.config.json"
    config_path.write_text(
        json.dumps(
            {
                "solc_remaps": " ".join(remappings) if remappings else None,
                "solc_args": f"--allow-paths {','.join(allow_paths)}",
            }
        ),
        encoding="utf-8",
    )
    return config_path


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

            resolve_npm_deps(tmp, files)
            remappings = build_solc_remappings(tmp)
            entry_key = choose_fuzz_entry_file(files, entry_files=entry_files)
            if entry_key is None:
                raise AnalyzerError(
                    "echidna failed",
                    tool=self.tool_name,
                    stage="preflight",
                    detail="No suitable fuzz target found in the selected entry files. Excluded interface-only files and dependency-style paths.",
                )
            entry = str(tmp / entry_key)
            crytic_config = _build_crytic_compile_config(tmp, remappings)
            cmd = [
                self.binary,
                entry,
                "--format",
                "text",
                "--crytic-args",
                f"--config-file {crytic_config}",
            ]

            try:
                result = run_sandboxed(cmd, timeout=self.timeout, cwd=str(tmp))
            except SandboxError as exc:
                raise AnalyzerError(
                    "echidna not available",
                    tool=self.tool_name,
                    stage="spawn",
                    detail=str(exc),
                    command=format_cmd(cmd),
                ) from exc

            if result.timed_out:
                raise analyzer_error_from_sandbox(
                    self.tool_name,
                    "execute",
                    f"echidna timed out after {self.timeout}s",
                    cmd=cmd,
                    result=result,
                )

            findings = self._parse(result.stdout + "\n" + result.stderr)
            if result.returncode != 0 and not findings:
                raw_output = "\n".join(part for part in (result.stderr, result.stdout) if part).strip()
                lowered = raw_output.lower()
                if any(marker in lowered for marker in _COMPILE_ERROR_MARKERS):
                    raise AnalyzerError(
                        "echidna compilation failed",
                        tool=self.tool_name,
                        stage="compile",
                        detail=raw_output[:400],
                        command=format_cmd(cmd),
                        returncode=result.returncode,
                        stdout_tail=result.stdout,
                        stderr_tail=result.stderr,
                    )
                if "No tests found in ABI" in raw_output:
                    raise AnalyzerError(
                        "echidna found no fuzzable properties",
                        tool=self.tool_name,
                        stage="execute",
                        detail=f"Selected entry file `{entry_key}` does not expose Echidna test properties or assertion-mode tests.",
                        command=format_cmd(cmd),
                        returncode=result.returncode,
                        stdout_tail=result.stdout,
                        stderr_tail=result.stderr,
                    )
                raise analyzer_error_from_sandbox(
                    self.tool_name,
                    "execute",
                    "echidna failed",
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
            cmd = [self.binary, str(src_path), "--format", "text"]

            try:
                result = run_sandboxed(cmd, timeout=self.timeout)
            except SandboxError as exc:
                raise AnalyzerError(
                    "echidna not available",
                    tool=self.tool_name,
                    stage="spawn",
                    detail=str(exc),
                    command=format_cmd(cmd),
                ) from exc

            if result.timed_out:
                raise analyzer_error_from_sandbox(
                    self.tool_name,
                    "execute",
                    f"echidna timed out after {self.timeout}s",
                    cmd=cmd,
                    result=result,
                )

            findings = self._parse(result.stdout + "\n" + result.stderr)
            if result.returncode != 0 and not findings:
                raise analyzer_error_from_sandbox(
                    self.tool_name,
                    "execute",
                    "echidna failed",
                    cmd=cmd,
                    result=result,
                )
            return findings

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
