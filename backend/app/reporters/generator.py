"""Report generator: JSON/Markdown/HTML renderers."""
from __future__ import annotations

import html as html_module
from collections import Counter
from typing import Any

from app.models.domain import Finding, Job
from app.schemas.enums import SEVERITY_ORDER, Severity

REMEDIATION = {
    "reentrancy": "Use checks-effects-interactions and `ReentrancyGuard` from OpenZeppelin.",
    "integer_overflow": "Use Solidity >=0.8.0 or `SafeMath` and validate all arithmetic bounds.",
    "access_control": "Add explicit modifiers (e.g. `onlyOwner`) and avoid `tx.origin` for auth.",
    "unchecked_return": "Check low-level call return values and revert on failure.",
    "timestamp_dependency": "Avoid relying on `block.timestamp` for critical logic.",
    "delegatecall": "Validate delegatecall targets; never forward untrusted data.",
    "self_destruct": "Remove or guard `selfdestruct` with strict access controls.",
    "front_running": "Use commit-reveal schemes or per-tx nonces to mitigate MEV.",
    "denial_of_service": "Avoid unbounded loops and external calls within loops.",
    "flash_loan": "Use oracles with TWAP and enforce invariants on flash-loan attack vectors.",
    "other": "Review manually; apply defense-in-depth.",
}

# Severity display order (highest to lowest)
_SEVERITY_DISPLAY_ORDER = sorted(Severity, key=lambda s: -SEVERITY_ORDER[s])


class ReportGenerator:
    def summary(self, findings: list[Finding]) -> dict[str, Any]:
        counter = Counter(f.severity.value for f in findings)
        return {
            "total": len(findings),
            "by_severity": dict(counter),
            "composite_severity": _composite(findings).value if findings else Severity.INFO.value,
        }

    def to_markdown(self, job: Job, findings: list[Finding]) -> str:
        lines = [f"# Security Report — Job `{job.id}`", ""]
        summary = self.summary(findings)
        lines.append(f"**Composite severity**: `{summary['composite_severity']}`  ")
        lines.append(f"**Total findings**: {summary['total']}")
        lines.append("")
        lines.append("## Severity breakdown")
        for sev in _SEVERITY_DISPLAY_ORDER:
            lines.append(f"- {sev.value}: {summary['by_severity'].get(sev.value, 0)}")
        lines.append("")
        lines.append("## Findings")
        for i, f in enumerate(findings, start=1):
            lines.append(f"### {i}. {f.title} (`{f.severity.value}`)")
            lines.append(f"- Tool: `{f.tool.value}`")
            lines.append(f"- Vulnerability: `{f.vulnerability_type.value}`")
            if f.location:
                lines.append(f"- Location: `{f.location}`")
            lines.append(f"- Confidence: {f.confidence:.2f}")
            lines.append("")
            lines.append(f.description)
            lines.append("")
            lines.append(
                f"**Remediation**: {REMEDIATION.get(f.vulnerability_type.value, REMEDIATION['other'])}"
            )
            lines.append("")
        return "\n".join(lines)

    def to_html(self, job: Job, findings: list[Finding]) -> str:
        md = self.to_markdown(job, findings)
        # Escape all content — findings may contain attacker-controlled strings
        body = html_module.escape(md).replace("\n", "<br/>\n")
        return (
            f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>Report {html_module.escape(job.id)}</title></head>"
            f"<body><pre>{body}</pre></body></html>"
        )

    def to_json(self, job: Job, findings: list[Finding]) -> dict[str, Any]:
        return {
            "job_id": job.id,
            "summary": self.summary(findings),
            "findings": [
                {
                    "id": f.id,
                    "tool": f.tool.value,
                    "vulnerability_type": f.vulnerability_type.value,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "location": f.location,
                    "confidence": f.confidence,
                    "remediation": REMEDIATION.get(
                        f.vulnerability_type.value, REMEDIATION["other"]
                    ),
                }
                for f in findings
            ],
        }


def _composite(findings: list[Finding]) -> Severity:
    return max(findings, key=lambda f: SEVERITY_ORDER[f.severity]).severity
