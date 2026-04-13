"""LLM-based PoC generation via Claude CLI subprocess."""
from __future__ import annotations

import asyncio
import logging
import shutil

from app.config import settings
from app.schemas.finding import FindingOut

logger = logging.getLogger(__name__)

POC_PROMPT_TEMPLATE = """You are a smart contract security expert. Generate a minimal Solidity PoC (proof of concept) exploit for the following vulnerability.

Vulnerability: {title}
Type: {vuln_type}
Severity: {severity}
Description: {description}
Location: {location}

Requirements:
- Write minimal, working Solidity code (Foundry test format preferred)
- Include comments explaining the attack steps
- Keep it under 60 lines
- Use SPDX-License-Identifier: MIT and pragma solidity ^0.8.20

Return ONLY the Solidity code, no explanations outside the code."""


async def generate_poc(finding: FindingOut) -> str:
    """Generate PoC exploit code by invoking the Claude CLI.

    Calls: claude -p "<prompt>"
    Returns the CLI stdout as the PoC code string.
    Falls back to a comment stub if the CLI is not installed or fails.
    """
    if not shutil.which(settings.claude_bin):
        return (
            f"// PoC generation requires the Claude CLI ('{settings.claude_bin}') to be installed.\n"
            f"// Finding: {finding.title} ({finding.vulnerability_type})\n"
            "// Install Claude CLI and ensure it is on PATH to enable AI-generated PoCs.\n"
        )

    prompt = POC_PROMPT_TEMPLATE.format(
        title=finding.title,
        vuln_type=finding.vulnerability_type,
        severity=finding.severity,
        description=finding.description,
        location=finding.location or "unknown",
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            settings.claude_bin,
            "-p",
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            logger.warning("claude cli exited %d: %s", proc.returncode, err)
            return f"// PoC generation failed (exit {proc.returncode}).\n// {err[:200]}\n"
        return stdout.decode(errors="replace").strip()
    except TimeoutError:
        logger.warning("claude cli timed out for finding %s", finding.id)
        return f"// PoC generation timed out for: {finding.title}\n"
    except Exception:
        logger.warning("PoC generation error", exc_info=True)
        return f"// PoC generation failed for: {finding.title}\n// Check logs for details.\n"
