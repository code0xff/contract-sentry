"""Finding aggregator: deduplicates and computes composite severity."""
from __future__ import annotations

from collections import defaultdict

from app.schemas.enums import SEVERITY_ORDER, Severity
from app.schemas.finding import FindingCreate

MAX_EVIDENCE_PER_FINDING = 20


def aggregate_findings(findings: list[FindingCreate]) -> list[FindingCreate]:
    """Deduplicate findings by (vulnerability_type, location) keeping the
    highest severity, confidence boosted by number of distinct confirming tools,
    and evidence capped at MAX_EVIDENCE_PER_FINDING entries.
    """
    if not findings:
        return []

    bucket: dict[tuple[str, str | None], FindingCreate] = {}
    evidence_bucket: dict[tuple[str, str | None], list[dict]] = defaultdict(list)
    tool_bucket: dict[tuple[str, str | None], set[str]] = defaultdict(set)

    for f in findings:
        key = (f.vulnerability_type.value, f.location)
        tool_bucket[key].add(f.tool.value)
        # Cap evidence accumulation to avoid unbounded DB row growth
        evidence_bucket[key] = (evidence_bucket[key] + f.evidence)[:MAX_EVIDENCE_PER_FINDING]

        if key not in bucket:
            bucket[key] = f
            continue

        current = bucket[key]
        # Promote to higher severity if this finding is more severe
        if SEVERITY_ORDER[f.severity] > SEVERITY_ORDER[current.severity]:
            bucket[key] = f.model_copy()

    out: list[FindingCreate] = []
    for key, base in bucket.items():
        # Confidence boost based on number of distinct tools that confirmed this finding,
        # not cumulative duplicate count — prevents inflation from repeated detections.
        n_distinct = len(tool_bucket[key])
        boosted = min(1.0, base.confidence + 0.1 * max(0, n_distinct - 1))
        merged = base.model_copy(update={"evidence": evidence_bucket[key], "confidence": boosted})
        out.append(merged)
    # sort by severity desc
    out.sort(key=lambda x: -SEVERITY_ORDER[x.severity])
    return out


def composite_severity(findings: list[FindingCreate]) -> Severity:
    if not findings:
        return Severity.INFO
    return max(findings, key=lambda f: SEVERITY_ORDER[f.severity]).severity
