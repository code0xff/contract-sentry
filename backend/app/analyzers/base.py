"""Abstract analyzer base."""
from __future__ import annotations

import abc
import dataclasses
import logging
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.core.sandbox import SandboxResult, format_cmd
from app.schemas.finding import FindingCreate

log = logging.getLogger(__name__)

# Packages pre-installed globally in the worker image — skip npm install for these.
_GLOBAL_NODE_MODULES = Path("/usr/local/lib/node_modules")

# Matches bare import paths that start with an npm scope or package name,
# e.g. "@openzeppelin/contracts/...", "@universal/interfaces/..."
_SCOPED_IMPORT_RE = re.compile(r"""['"]((@[^/"']+/[^/"']+)|([^./@"'][^/"']*))""")


def resolve_npm_deps(tmpdir: Path, files: dict[str, str]) -> None:
    """Auto-install npm dependencies into *tmpdir* before running analysis.

    Strategy (in order):
    1. If ``package.json`` is present in the uploaded files, run ``npm install``.
    2. Otherwise, parse all ``import`` statements for ``@scope/package`` patterns
       and install any that are not already available globally.
    """
    # --- strategy 1: package.json present ---
    if "package.json" in files:
        log.info("npm_install_from_package_json dir=%s", tmpdir)
        try:
            result = subprocess.run(
                ["npm", "install", "--prefix", str(tmpdir), "--prefer-offline"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                log.warning("npm_install_failed: %s", result.stderr[:300])
        except Exception as exc:
            log.warning("npm_install_error: %s", exc)
        return

    # --- strategy 2: scan imports ---
    packages: set[str] = set()
    for content in files.values():
        for m in _SCOPED_IMPORT_RE.finditer(content):
            raw = m.group(1)
            # Only handle scoped packages (@org/pkg) — plain names are too ambiguous
            if raw.startswith("@"):
                # Take just the first two segments: @scope/package
                parts = raw.lstrip("@").split("/")
                if len(parts) >= 2:
                    packages.add(f"@{parts[0]}/{parts[1]}")

    if not packages:
        return

    def _already_available(pkg: str) -> bool:
        if (_GLOBAL_NODE_MODULES / pkg).exists():
            return True
        if (tmpdir / "node_modules" / pkg).exists():
            return True
        if (tmpdir / pkg).exists():
            return True
        # Files uploaded directly with the scope path (e.g. "universal/interfaces/ISemver.sol"
        # satisfies "@universal/interfaces" — check both with and without leading "@")
        bare = pkg.lstrip("@")
        if any(k.startswith(bare + "/") or k.startswith(pkg + "/") for k in files):
            return True
        return False

    to_install = [pkg for pkg in packages if not _already_available(pkg)]

    if not to_install:
        return

    log.info("npm_install_packages packages=%s dir=%s", to_install, tmpdir)
    try:
        result = subprocess.run(
            ["npm", "install", "--prefix", str(tmpdir), "--prefer-offline"] + to_install,
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            log.warning("npm_install_partial_failure: %s", result.stderr[:300])
    except Exception as exc:
        log.warning("npm_install_error: %s", exc)


def build_solc_remappings(tmpdir: Path) -> list[str]:
    """Build ``@pkg=path`` remapping strings for slither/solc from available node_modules
    and user-uploaded files stored under scoped paths (e.g. ``@universal/interfaces/``).

    Only includes packages that actually contain .sol files to avoid passing
    unrelated npm packages (e.g. CLI tools) to the Solidity compiler.
    """
    remappings: list[str] = []
    seen: set[str] = set()

    for search_root in (tmpdir / "node_modules", _GLOBAL_NODE_MODULES):
        if not search_root.exists():
            continue
        for entry in search_root.iterdir():
            if entry.name.startswith("@"):
                for sub in entry.iterdir():
                    key = f"@{entry.name[1:]}/{sub.name}"
                    if key not in seen and _has_sol_files(sub):
                        remappings.append(f"{key}={sub}")
                        seen.add(key)
            else:
                key = entry.name
                if key not in seen and _has_sol_files(entry):
                    remappings.append(f"{key}={entry}")
                    seen.add(key)

    # Also map user-uploaded files stored directly under @scope/pkg in tmpdir.
    # e.g. tmpdir/@universal/interfaces/ISemver.sol → "@universal/interfaces=<path>"
    try:
        for scope_dir in tmpdir.iterdir():
            if not scope_dir.name.startswith("@") or not scope_dir.is_dir():
                continue
            for pkg_dir in scope_dir.iterdir():
                if not pkg_dir.is_dir():
                    continue
                key = f"@{scope_dir.name[1:]}/{pkg_dir.name}"
                if key not in seen and _has_sol_files(pkg_dir):
                    remappings.append(f"{key}={pkg_dir}")
                    seen.add(key)
    except (OSError, PermissionError):
        pass

    return remappings


_IMPORT_RE = re.compile(r"""import\s+(?:[^"']*?\s+)?["']([^"']+)["']""")
_CONTRACT_RE = re.compile(r"\b(?:abstract\s+)?contract\s+[A-Za-z_][A-Za-z0-9_]*")
_LIBRARY_RE = re.compile(r"\blibrary\s+[A-Za-z_][A-Za-z0-9_]*")
_INTERFACE_RE = re.compile(r"\binterface\s+[A-Za-z_][A-Za-z0-9_]*")
_OUTPUT_TAIL_LIMIT = 1200
_NON_ENTRY_DIR_NAMES = {
    "interface",
    "interfaces",
    "lib",
    "libs",
    "node_modules",
    "spec",
    "specs",
    "test",
    "tests",
    "vendor",
    "vendors",
}


def auto_alias_by_basename(files: dict[str, str]) -> dict[str, str]:
    """Add path aliases so that import paths whose basename matches an existing
    file are resolvable even when the upload created broken path prefixes.

    Example: uploaded files {"universal/interfaces/ISemver.sol": "..."} but
    imports reference "@universal/interfaces/ISemver.sol" → adds that key.
    """
    # Build a basename → existing_path map (last writer wins for duplicates)
    basename_map: dict[str, str] = {p.rsplit("/", 1)[-1]: p for p in files}

    aliases: dict[str, str] = {}
    for content in list(files.values()):
        for m in _IMPORT_RE.finditer(content):
            raw = m.group(1)
            if raw in files or raw in aliases:
                continue
            basename = raw.rsplit("/", 1)[-1]
            if basename in basename_map:
                aliases[raw] = files[basename_map[basename]]

    if aliases:
        result = dict(files)
        result.update(aliases)
        return result
    return files


def _has_sol_files(path: Path) -> bool:
    """Return True if the directory contains at least one .sol file (non-recursive check)."""
    try:
        return any(True for _ in path.rglob("*.sol"))
    except (OSError, PermissionError):
        return False


class AnalyzerError(RuntimeError):
    """Raised when an analyzer encounters an unrecoverable error."""

    def __init__(
        self,
        summary: str,
        *,
        tool: str | None = None,
        stage: str | None = None,
        detail: str | None = None,
        command: str | None = None,
        returncode: int | None = None,
        stdout_tail: str | None = None,
        stderr_tail: str | None = None,
        timed_out: bool = False,
        retryable: bool = False,
    ) -> None:
        self.summary = summary
        self.tool = tool
        self.stage = stage
        self.detail = detail
        self.command = command
        self.returncode = returncode
        self.stdout_tail = _trim_output(stdout_tail)
        self.stderr_tail = _trim_output(stderr_tail)
        self.timed_out = timed_out
        self.retryable = retryable
        super().__init__(self.display_message)

    @property
    def display_message(self) -> str:
        if self.detail:
            return f"{self.summary}: {self.detail}"
        return self.summary

    def to_status(self) -> dict[str, Any]:
        return {
            "status": "failed",
            "summary": self.summary,
            "detail": self.detail,
            "stage": self.stage,
            "command": self.command,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
        }


@dataclasses.dataclass(frozen=True)
class ToolStatus:
    status: str
    summary: str
    detail: str | None = None
    stage: str | None = None
    command: str | None = None
    returncode: int | None = None
    timed_out: bool = False
    stdout_tail: str | None = None
    stderr_tail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "detail": self.detail,
            "stage": self.stage,
            "command": self.command,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "stdout_tail": _trim_output(self.stdout_tail),
            "stderr_tail": _trim_output(self.stderr_tail),
        }


def build_tool_success_status(tool: str, summary: str = "Tool completed successfully") -> dict[str, Any]:
    return ToolStatus(status="ok", summary=summary).to_dict()


def build_tool_skipped_status(tool: str, summary: str, detail: str | None = None) -> dict[str, Any]:
    return ToolStatus(status="skipped", summary=summary, detail=detail, stage="preflight").to_dict()


def analyzer_error_from_sandbox(
    tool: str,
    stage: str,
    summary: str,
    *,
    cmd: Sequence[str] | None = None,
    result: SandboxResult | None = None,
    detail: str | None = None,
) -> AnalyzerError:
    stderr_tail = result.stderr if result is not None else None
    stdout_tail = result.stdout if result is not None else None
    if detail is None:
        detail = _preferred_detail(stderr_tail, stdout_tail)
    return AnalyzerError(
        summary,
        tool=tool,
        stage=stage,
        detail=detail,
        command=format_cmd(cmd) if cmd else None,
        returncode=result.returncode if result is not None else None,
        stdout_tail=stdout_tail,
        stderr_tail=stderr_tail,
        timed_out=result.timed_out if result is not None else False,
    )


def build_unknown_tool_status(tool: str) -> dict[str, Any]:
    return ToolStatus(
        status="failed",
        summary=f"Unsupported analysis tool: {tool}",
        stage="dispatch",
    ).to_dict()


def _preferred_detail(stderr_tail: str | None, stdout_tail: str | None) -> str | None:
    for value in (stderr_tail, stdout_tail):
        trimmed = _trim_output(value)
        if trimmed:
            return trimmed
    return None


def _trim_output(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) <= _OUTPUT_TAIL_LIMIT:
        return text
    return text[-_OUTPUT_TAIL_LIMIT:]


def is_interface_only_source(source: str) -> bool:
    if _CONTRACT_RE.search(source) or _LIBRARY_RE.search(source):
        return False
    return bool(_INTERFACE_RE.search(source))


def is_non_entry_solidity_path(path: str) -> bool:
    parts = [part.lower() for part in Path(path).parts]
    return any(part in _NON_ENTRY_DIR_NAMES for part in parts)


def choose_fuzz_entry_file(
    files: dict[str, str],
    entry_files: list[str] | None = None,
) -> str | None:
    ordered_candidates = entry_files if entry_files else sorted(files.keys())
    candidates = [
        path
        for path in ordered_candidates
        if path.endswith(".sol") and not path.startswith("@") and path in files
    ]
    if not candidates:
        return None

    preferred = [
        path for path in candidates
        if not is_non_entry_solidity_path(path) and not is_interface_only_source(files[path])
    ]
    if preferred:
        return preferred[0]

    fallback = [path for path in candidates if not is_interface_only_source(files[path])]
    if fallback:
        return fallback[0]

    return None


class BaseAnalyzer(abc.ABC):
    tool_name: str

    @abc.abstractmethod
    def analyze(self, source: str) -> list[FindingCreate]:
        """Run the analyzer on a single source string and return normalized findings."""

    @abc.abstractmethod
    def analyze_files(self, files: dict[str, str], entry_files: list[str] | None = None) -> list[FindingCreate]:
        """Run the analyzer on a multi-file project.

        Args:
            files: Mapping of relative path → source content,
                   e.g. {"contracts/Token.sol": "...", "lib/Ownable.sol": "..."}.
            entry_files: Optional list of relative paths to use as analysis entry points.
                         When provided, only these files are used to determine the analysis
                         target (common ancestor dir or entry point file). Defaults to all
                         user-owned (non-@scope) files.
        """
