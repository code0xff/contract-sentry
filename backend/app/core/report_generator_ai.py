"""Claude-powered security audit report generator.

Priority:
  1. Anthropic SDK (ANTHROPIC_API_KEY env var)
  2. Host claude CLI via http://host.docker.internal:CLAUDE_PROXY_PORT
  3. Return error stub
"""
from __future__ import annotations

import logging
import os

from app.schemas.finding import FindingOut
from app.schemas.job import JobOut

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
CLAUDE_PROXY_PORT = int(os.environ.get("CLAUDE_PROXY_PORT", "9876"))

REPORT_PROMPT = """You are a senior smart contract security auditor. Generate a professional security audit report in Markdown format.

Contract: {contract_name}
Analysis Tools: {tools}
Total Findings: {total} ({high} High, {medium} Medium, {low} Low, {info} Info)

Findings:
{findings_text}

Write a professional audit report with these sections:
1. Executive Summary
2. Scope
3. Findings (one subsection per finding with: severity badge, description, recommendation)
4. Summary Table
5. Conclusion

Use markdown formatting. Be concise but thorough. For recommendations, be specific."""


def _build_prompt(job: JobOut, findings: list[FindingOut], contract_name: str) -> str:
    from collections import Counter
    severity_counts = Counter(f.severity for f in findings)

    findings_text = ""
    for i, f in enumerate(findings, 1):
        findings_text += f"\n### {i}. [{f.severity.upper()}] {f.title}\n"
        findings_text += f"- **Type**: {f.vulnerability_type}\n"
        findings_text += f"- **Location**: {f.location or 'N/A'}\n"
        findings_text += f"- **Description**: {f.description}\n"
        if f.confidence:
            findings_text += f"- **Confidence**: {f.confidence}\n"

    return REPORT_PROMPT.format(
        contract_name=contract_name,
        tools=", ".join(job.tools),
        total=len(findings),
        high=severity_counts.get("high", 0),
        medium=severity_counts.get("medium", 0),
        low=severity_counts.get("low", 0),
        info=severity_counts.get("info", 0),
        findings_text=findings_text or "No findings.",
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
        logger.warning("SDK report generation failed: %s", exc)
        return None


async def _via_host_proxy(prompt: str) -> str | None:
    import aiohttp
    url = f"http://host.docker.internal:{CLAUDE_PROXY_PORT}/generate"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json={"prompt": prompt}, timeout=aiohttp.ClientTimeout(total=180)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("poc") or None
    except Exception as exc:
        logger.debug("Host proxy not available: %s", exc)
    return None


async def generate_ai_report(job: JobOut, findings: list[FindingOut], contract_name: str) -> str:
    prompt = _build_prompt(job, findings, contract_name)

    # 1. Try Anthropic SDK
    result = await _via_sdk(prompt)
    if result:
        return result

    # 2. Try host claude CLI proxy
    result = await _via_host_proxy(prompt)
    if result:
        return result

    # 3. Neither available
    logger.info("AI report generation skipped — no SDK key and no host proxy available")
    return (
        "# AI Report\n\n"
        "Report generation skipped: set `ANTHROPIC_API_KEY` or run "
        "`scripts/claude-proxy.py` on the host.\n"
    )
