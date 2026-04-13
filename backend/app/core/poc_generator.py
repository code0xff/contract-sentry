"""LLM-based PoC generation for smart contract vulnerabilities."""
from __future__ import annotations

import logging

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
    """Generate PoC exploit code using Claude. Returns code string or error message."""
    if not settings.ANTHROPIC_API_KEY:
        return (
            "// PoC generation requires ANTHROPIC_API_KEY to be configured.\n"
            f"// Finding: {finding.title} ({finding.vulnerability_type})\n"
            "// Set ANTHROPIC_API_KEY environment variable to enable AI-generated PoCs.\n"
        )
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = await client.messages.create(
            model=settings.POC_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": POC_PROMPT_TEMPLATE.format(
                    title=finding.title,
                    vuln_type=finding.vulnerability_type,
                    severity=finding.severity,
                    description=finding.description,
                    location=finding.location or "unknown",
                ),
            }],
        )
        return message.content[0].text
    except Exception:
        logger.warning("PoC generation failed", exc_info=True)
        return f"// PoC generation failed for: {finding.title}\n// Check logs for details.\n"
