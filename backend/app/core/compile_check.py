"""Compile-check: try to compile uploaded .sol files and report missing imports."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from app.analyzers.base import build_solc_remappings, resolve_npm_deps

_MISSING_RE = re.compile(r'Source "([^"]+)" not found')
_PRAGMA_RE = re.compile(r'pragma\s+solidity\s+([^;]+)')


def _detect_pragma(files: dict[str, str]) -> str | None:
    for content in files.values():
        m = _PRAGMA_RE.search(content)
        if m:
            return m.group(1).strip()
    return None


def check_compilation(files: dict[str, str]) -> dict[str, object]:
    """Compile the project files and return what's missing.

    Returns::

        {
            "success": bool,
            "missing": list[str],   # unresolved import paths
            "errors":  list[str],   # first 20 non-import error lines
        }
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for rel_path, content in files.items():
            dest = tmp / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        resolve_npm_deps(tmp, files)
        remappings = build_solc_remappings(tmp)

        sol_files = sorted(str(tmp / p) for p in files if p.endswith(".sol"))
        if not sol_files:
            return {"success": True, "missing": [], "errors": []}

        pragma = _detect_pragma(files)
        output = _run_via_solcx(tmp, remappings, sol_files, pragma)
        if output is None:
            output = _run_system_solc(tmp, remappings, sol_files)
        if output is None:
            return {"success": False, "missing": [], "errors": ["solc not available — install py-solc-x or solc"]}

        missing = sorted({m.group(1) for m in _MISSING_RE.finditer(output)})
        errors = [
            line.strip()
            for line in output.splitlines()
            if "Error:" in line and "not found" not in line.lower()
        ][:20]
        success = not missing and not any("Error:" in e for e in errors)
        return {"success": success, "missing": missing, "errors": errors}


def _run_via_solcx(
    tmp: Path,
    remappings: list[str],
    sol_files: list[str],
    pragma: str | None,
) -> str | None:
    """Try compilation via py-solc-x. Returns combined output or None if unavailable."""
    try:
        import solcx  # type: ignore[import]
    except ImportError:
        return None

    try:
        # Install / select the right solc version for this pragma
        if pragma:
            try:
                version = solcx.install_solc_pragma(pragma, show_progress=False)
                solcx.set_solc_version(version, silent=True)
            except Exception:
                versions = solcx.get_installed_solc_versions()
                if versions:
                    solcx.set_solc_version(versions[0], silent=True)
                else:
                    solcx.install_solc("latest", show_progress=False)
        else:
            versions = solcx.get_installed_solc_versions()
            if not versions:
                solcx.install_solc("latest", show_progress=False)

        solcx.compile_files(
            sol_files,
            remappings=remappings or None,
            allow_paths=[str(tmp)],
            output_values=["abi"],
        )
        return ""  # success — no output means no errors
    except Exception as exc:
        return str(exc)


def _run_system_solc(tmp: Path, remappings: list[str], sol_files: list[str]) -> str | None:
    """Try the system `solc` binary. Returns combined output or None if not found."""
    cmd = ["solc", "--no-optimize"] + remappings + sol_files + ["--allow-paths", str(tmp)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(tmp))
        return result.stdout + "\n" + result.stderr
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return "Error: compilation timed out"
