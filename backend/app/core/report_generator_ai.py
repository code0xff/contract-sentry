"""Claude-powered security audit report generator."""
from __future__ import annotations

import logging
import os

from app.schemas.finding import FindingOut
from app.schemas.job import JobOut

logger = logging.getLogger(__name__)
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

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


async def generate_ai_report(job: JobOut, findings: list[FindingOut], contract_name: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "# AI Report\n\nANTHROPIC_API_KEY not configured."

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

    prompt = REPORT_PROMPT.format(
        contract_name=contract_name,
        tools=", ".join(job.tools),
        total=len(findings),
        high=severity_counts.get("high", 0),
        medium=severity_counts.get("medium", 0),
        low=severity_counts.get("low", 0),
        info=severity_counts.get("info", 0),
        findings_text=findings_text or "No findings.",
    )

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        logger.warning("AI report generation failed: %s", exc)
        return f"# Report Generation Failed\n\n{exc}"
