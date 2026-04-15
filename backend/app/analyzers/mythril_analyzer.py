"""Mythril analyzer adapter."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.analyzers.base import AnalyzerError, BaseAnalyzer, build_solc_remappings, resolve_npm_deps
from app.config import get_settings
from app.core.sandbox import SandboxError, run_sandboxed
from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate

MYTHRIL_SWC_MAP = {
    "107": VulnerabilityType.REENTRANCY,
    "101": VulnerabilityType.INTEGER_OVERFLOW,
    "105": VulnerabilityType.ACCESS_CONTROL,
    "104": VulnerabilityType.UNCHECKED_RETURN,
    "106": VulnerabilityType.SELF_DESTRUCT,
    "112": VulnerabilityType.DELEGATECALL,
    "116": VulnerabilityType.TIMESTAMP_DEPENDENCY,
}

MYTHRIL_SEVERITY_MAP = {
    "High": Severity.HIGH,
    "Medium": Severity.MEDIUM,
    "Low": Severity.LOW,
}


_OZ_PATH = os.environ.get(
    "OZ_CONTRACTS_PATH", "/usr/local/lib/node_modules/@openzeppelin"
)

SOLC_REMAPPINGS = f"@openzeppelin={_OZ_PATH}"


class MythrilAnalyzer(BaseAnalyzer):
    tool_name = "mythril"

    def __init__(self, binary: str | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.binary = binary or settings.mythril_bin
        self.timeout = timeout or settings.static_analysis_timeout_s

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

            # Use first entry_file when provided; otherwise first user-owned .sol file
            if entry_files:
                candidate_keys = [p for p in entry_files if p.endswith(".sol") and not p.startswith("@")]
            else:
                candidate_keys = [p for p in sorted(files.keys()) if p.endswith(".sol") and not p.startswith("@")]
            entry_key = candidate_keys[0] if candidate_keys else sorted(files.keys())[0]
            entry = str(tmp / entry_key)

            cmd = [self.binary, "analyze", entry, "-o", "json"]
            all_remaps = ([SOLC_REMAPPINGS] if SOLC_REMAPPINGS else []) + remappings
            if all_remaps:
                # --solc-remaps is not valid; use --solc-json with remappings array
                remap_json = json.dumps({"remappings": all_remaps})
                cmd += ["--solc-json", remap_json]
            # Allow solc to resolve imports from anywhere inside tmpdir
            cmd += ["--solc-args", f"--allow-paths {tmpdir}"]

            try:
                result = run_sandboxed(cmd, timeout=self.timeout, cwd=str(tmp))
            except SandboxError as exc:
                raise AnalyzerError(f"mythril not available: {exc}") from exc

            if result.timed_out:
                raise AnalyzerError(f"mythril timed out after {self.timeout}s")

            # Mythril exits 0 even when solc compilation fails — detect via stderr
            stderr = result.stderr or ""
            if any(kw in stderr.lower() for kw in ("fatal error", "file not found", "cannot find", "solc experienced")):
                raise AnalyzerError(f"mythril compilation failed: {stderr[:400]}")

            stdout = result.stdout.strip()
            if not stdout:
                return []

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as exc:
                raise AnalyzerError(f"mythril emitted invalid JSON: {exc}") from exc

            return self._normalize(data)

    def analyze(self, source: str) -> list[FindingCreate]:
        if not source:
            return []

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / "Contract.sol"
            src_path.write_text(source, encoding="utf-8")

            try:
                remap_json = json.dumps({"remappings": [SOLC_REMAPPINGS]})
                result = run_sandboxed(
                    [
                        self.binary, "analyze", str(src_path),
                        "-o", "json",
                        "--solc-json", remap_json,
                    ],
                    timeout=self.timeout,
                )
            except SandboxError as exc:
                raise AnalyzerError(f"mythril not available: {exc}") from exc

            if result.timed_out:
                raise AnalyzerError(f"mythril timed out after {self.timeout}s")

            stdout = result.stdout.strip()
            if not stdout:
                return []

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as exc:
                raise AnalyzerError(f"mythril emitted invalid JSON: {exc}") from exc

            return self._normalize(data)

    def _normalize(self, data: dict[str, Any]) -> list[FindingCreate]:
        out: list[FindingCreate] = []
        issues = data.get("issues", []) if isinstance(data, dict) else []
        for issue in issues:
            swc = str(issue.get("swc-id", "")) or ""
            vuln_type = MYTHRIL_SWC_MAP.get(swc, VulnerabilityType.OTHER)
            severity = MYTHRIL_SEVERITY_MAP.get(issue.get("severity", "Low"), Severity.LOW)
            location = None
            if issue.get("filename"):
                location = f"{issue['filename']}:{issue.get('lineno', '?')}"
            out.append(
                FindingCreate(
                    tool=ToolName.MYTHRIL,
                    vulnerability_type=vuln_type,
                    severity=severity,
                    title=issue.get("title", "mythril finding"),
                    description=issue.get("description", ""),
                    location=location,
                    confidence=0.7,
                    evidence=[{"kind": "raw_output", "tool": "mythril", "issue": issue}],
                )
            )
        return out
