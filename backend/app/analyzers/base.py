"""Abstract analyzer base."""
from __future__ import annotations

import abc
import logging
import re
import subprocess
from pathlib import Path

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

    to_install = [
        pkg for pkg in packages
        if not (_GLOBAL_NODE_MODULES / pkg).exists()
        and not (tmpdir / "node_modules" / pkg).exists()
    ]

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


def _has_sol_files(path: Path) -> bool:
    """Return True if the directory contains at least one .sol file (non-recursive check)."""
    try:
        return any(True for _ in path.rglob("*.sol"))
    except (OSError, PermissionError):
        return False


class AnalyzerError(RuntimeError):
    """Raised when an analyzer encounters an unrecoverable error."""


class BaseAnalyzer(abc.ABC):
    tool_name: str

    @abc.abstractmethod
    def analyze(self, source: str) -> list[FindingCreate]:
        """Run the analyzer on a single source string and return normalized findings."""

    @abc.abstractmethod
    def analyze_files(self, files: dict[str, str]) -> list[FindingCreate]:
        """Run the analyzer on a multi-file project.

        Args:
            files: Mapping of relative path → source content,
                   e.g. {"contracts/Token.sol": "...", "lib/Ownable.sol": "..."}.
        """
