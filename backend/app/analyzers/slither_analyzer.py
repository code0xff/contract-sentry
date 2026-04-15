"""Slither analyzer adapter.

Writes the source to a temporary file, invokes `slither <file> --json -`,
parses the JSON output and normalizes detectors into ``FindingCreate``.
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from app.analyzers.base import AnalyzerError, BaseAnalyzer, build_solc_remappings, resolve_npm_deps
from app.config import get_settings
from app.core.sandbox import SandboxError, run_sandboxed
from app.schemas.enums import Severity, ToolName, VulnerabilityType
from app.schemas.finding import FindingCreate

log = logging.getLogger(__name__)


def _ensure_solc(source: str) -> None:
    """Auto-install the solc version required by pragma, using py-solc-x."""
    try:
        import solcx  # type: ignore[import]
    except ImportError:
        return
    match = re.search(r'pragma\s+solidity\s+([^;]+)', source)
    if not match:
        return
    pragma = match.group(1).strip()
    try:
        installed = solcx.install_solc_pragma(pragma, show_progress=False)
        solcx.set_solc_version(installed, silent=True)
    except Exception as exc:
        log.warning("solc auto-install failed for pragma '%s': %s", pragma, exc)

SLITHER_SEVERITY_MAP = {
    "High": Severity.HIGH,
    "Medium": Severity.MEDIUM,
    "Low": Severity.LOW,
    "Informational": Severity.INFO,
    "Optimization": Severity.INFO,
}

SLITHER_CHECK_MAP = {
    "reentrancy-eth": VulnerabilityType.REENTRANCY,
    "reentrancy-no-eth": VulnerabilityType.REENTRANCY,
    "reentrancy-events": VulnerabilityType.REENTRANCY,
    "tx-origin": VulnerabilityType.ACCESS_CONTROL,
    "arbitrary-send": VulnerabilityType.ACCESS_CONTROL,
    "unchecked-transfer": VulnerabilityType.UNCHECKED_RETURN,
    "unchecked-send": VulnerabilityType.UNCHECKED_RETURN,
    "unchecked-lowlevel": VulnerabilityType.UNCHECKED_RETURN,
    "timestamp": VulnerabilityType.TIMESTAMP_DEPENDENCY,
    "block-timestamp": VulnerabilityType.TIMESTAMP_DEPENDENCY,
    "delegatecall-loop": VulnerabilityType.DELEGATECALL,
    "controlled-delegatecall": VulnerabilityType.DELEGATECALL,
    "suicidal": VulnerabilityType.SELF_DESTRUCT,
    "integer-overflow": VulnerabilityType.INTEGER_OVERFLOW,
}


_OZ_PATH = os.environ.get(
    "OZ_CONTRACTS_PATH", "/usr/local/lib/node_modules/@openzeppelin"
)

SOLC_REMAPPINGS = f"@openzeppelin={_OZ_PATH}"


class SlitherAnalyzer(BaseAnalyzer):
    tool_name = "slither"

    def __init__(self, binary: str | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.binary = binary or settings.slither_bin
        self.timeout = timeout or settings.static_analysis_timeout_s

    def analyze_files(self, files: dict[str, str], entry_files: list[str] | None = None) -> list[FindingCreate]:
        if not files:
            return []

        # Auto-install required solc version from any file's pragma
        for content in files.values():
            _ensure_solc(content)
            break

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for rel_path, content in files.items():
                dest = tmp / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")

            # Auto-install missing npm packages detected from imports
            resolve_npm_deps(tmp, files)

            # Build remappings from globally installed + locally installed packages
            remappings = build_solc_remappings(tmp)

            # Target the common ancestor directory of user-owned (or entry) files,
            # excluding @scope/ dependency dirs so slither doesn't try to
            # analyse pure interface-only packages ("No contract was analyzed").
            import os as _os
            if entry_files:
                candidate_keys = [p for p in entry_files if p.endswith(".sol") and not p.startswith("@")]
            else:
                candidate_keys = [p for p in files if p.endswith(".sol") and not p.startswith("@")]
            if candidate_keys:
                common = _os.path.commonpath(candidate_keys)
                common_path = Path(common)
                # commonpath may return a file path when there's only one entry
                if common_path.suffix:
                    common_path = common_path.parent
                target_dir = tmp / common_path if str(common_path) != "." else tmp
            else:
                target_dir = tmp
            cmd = [self.binary, str(target_dir), "--json", "-"]
            if remappings:
                cmd += ["--solc-remaps", " ".join(remappings)]

            try:
                result = run_sandboxed(cmd, timeout=self.timeout, cwd=str(tmp))
            except SandboxError as exc:
                raise AnalyzerError(f"slither not available: {exc}") from exc

            if result.timed_out:
                raise AnalyzerError(f"slither timed out after {self.timeout}s")

            if not result.stdout.strip():
                if result.returncode != 0:
                    raise AnalyzerError(f"slither failed: {result.stderr[:500]}")
                return []

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise AnalyzerError(f"slither emitted invalid JSON: {exc}") from exc

            return self._normalize(data)

    def analyze(self, source: str) -> list[FindingCreate]:
        if not source:
            return []

        _ensure_solc(source)

        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / "Contract.sol"
            src_path.write_text(source, encoding="utf-8")

            try:
                result = run_sandboxed(
                    [
                        self.binary, str(src_path),
                        "--json", "-",
                        "--solc-remaps", SOLC_REMAPPINGS,
                    ],
                    timeout=self.timeout,
                )
            except SandboxError as exc:
                raise AnalyzerError(f"slither not available: {exc}") from exc

            if result.timed_out:
                raise AnalyzerError(f"slither timed out after {self.timeout}s")

            if not result.stdout.strip():
                # slither returns non-zero on findings; inspect stderr
                if result.returncode != 0:
                    raise AnalyzerError(f"slither failed: {result.stderr[:500]}")
                return []

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise AnalyzerError(f"slither emitted invalid JSON: {exc}") from exc

            return self._normalize(data)

    def _normalize(self, data: dict[str, Any]) -> list[FindingCreate]:
        out: list[FindingCreate] = []
        results = data.get("results", {}).get("detectors", []) if isinstance(data, dict) else []
        for det in results:
            severity = SLITHER_SEVERITY_MAP.get(det.get("impact", "Informational"), Severity.INFO)
            vuln_type = SLITHER_CHECK_MAP.get(det.get("check", ""), VulnerabilityType.OTHER)
            elements = det.get("elements", [])
            location = None
            if elements:
                src = elements[0].get("source_mapping", {})
                filename = src.get("filename_short") or src.get("filename_absolute") or ""
                lines = src.get("lines") or []
                if filename and lines:
                    location = f"{filename}:{lines[0]}"
            out.append(
                FindingCreate(
                    tool=ToolName.SLITHER,
                    vulnerability_type=vuln_type,
                    severity=severity,
                    title=det.get("check", "slither finding"),
                    description=det.get("description", ""),
                    location=location,
                    confidence=_confidence(det.get("confidence", "Medium")),
                    evidence=[{"kind": "raw_output", "tool": "slither", "detector": det}],
                )
            )
        return out


def _confidence(value: str) -> float:
    return {"High": 0.9, "Medium": 0.6, "Low": 0.3}.get(value, 0.5)
