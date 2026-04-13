"""Sandbox execution helpers.

Wraps subprocess invocation with timeout and reports a unified result
structure. In production these commands would be launched inside
locked-down Docker containers; the helper keeps the call signature
identical so the worker code does not change between environments.
"""
from __future__ import annotations

import asyncio
import dataclasses
import shlex
import subprocess
from collections.abc import Sequence


@dataclasses.dataclass(frozen=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class SandboxError(RuntimeError):
    """Raised when sandbox execution could not produce a result."""


def run_sandboxed(
    cmd: Sequence[str],
    *,
    timeout: int,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> SandboxResult:
    """Run a command synchronously with a hard timeout."""
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return SandboxResult(
            returncode=-1,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\n[sandbox] timed out after {timeout}s",
            timed_out=True,
        )
    except FileNotFoundError as exc:
        raise SandboxError(f"Executable not found: {cmd[0]}") from exc

    return SandboxResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


async def run_sandboxed_async(
    cmd: Sequence[str],
    *,
    timeout: int,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> SandboxResult:
    """Async variant for use in coroutines."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: run_sandboxed(cmd, timeout=timeout, cwd=cwd, env=env),
    )


def format_cmd(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(c) for c in cmd)
