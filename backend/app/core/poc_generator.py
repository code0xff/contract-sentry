"""LLM-based PoC generation.

Priority:
  1. Anthropic SDK (ANTHROPIC_API_KEY env var)
  2. Host claude CLI via http://host.docker.internal:CLAUDE_PROXY_PORT
  3. Skip (return stub comment)
"""
from __future__ import annotations

import logging
import os

from app.schemas.finding import FindingOut

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-6"
MAX_TOKENS = 1024
CLAUDE_PROXY_PORT = int(os.environ.get("CLAUDE_PROXY_PORT", "9876"))

POC_PROMPT_TEMPLATE = """You are a smart contract security expert. Generate a minimal Solidity PoC (proof of concept) exploit for the following vulnerability.

Vulnerability: {title}
Type: {vuln_type}
Severity: {severity}
Description: {description}
Location: {location}

{contract_section}

Requirements:
- Write minimal, working Solidity code (Foundry test format preferred)
- Include comments explaining the attack steps
- Keep it under 80 lines
- Use SPDX-License-Identifier: MIT and pragma solidity ^0.8.20

Return ONLY the Solidity code, no explanations outside the code."""


def _contract_section(contract_source: str | None) -> str:
    if not contract_source:
        return ""
    truncated = contract_source[:8000]
    note = "\n// ... (truncated)" if len(contract_source) > 8000 else ""
    return f"Contract source:\n```solidity\n{truncated}{note}\n```"


def _build_prompt(finding: FindingOut, contract_source: str | None) -> str:
    return POC_PROMPT_TEMPLATE.format(
        title=finding.title,
        vuln_type=finding.vulnerability_type,
        severity=finding.severity,
        description=finding.description,
        location=finding.location or "unknown",
        contract_section=_contract_section(contract_source),
    )


async def _via_sdk(prompt: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic  # type: ignore[import]
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except ImportError:
        logger.warning("anthropic SDK not installed")
        return None
    except Exception as exc:
        logger.warning("SDK PoC generation failed: %s", exc)
        return None


async def _via_host_proxy(prompt: str) -> str | None:
    import aiohttp  # already a transitive dep via numerous packages
    url = f"http://host.docker.internal:{CLAUDE_PROXY_PORT}/generate"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"prompt": prompt}, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("poc") or None
    except Exception as exc:
        logger.debug("Host proxy not available: %s", exc)
    return None


async def generate_poc(finding: FindingOut, contract_source: str | None = None) -> str:
    prompt = _build_prompt(finding, contract_source)

    # 1. Try Anthropic SDK
    result = await _via_sdk(prompt)
    if result:
        return result

    # 2. Try host claude CLI proxy
    result = await _via_host_proxy(prompt)
    if result:
        return result

    # 3. Skip
    logger.info("PoC generation skipped — no SDK key and no host proxy available")
    return (
        f"// PoC generation skipped: set ANTHROPIC_API_KEY or run scripts/claude-proxy.py on the host.\n"
        f"// Finding: {finding.title} ({finding.vulnerability_type})\n"
    )
