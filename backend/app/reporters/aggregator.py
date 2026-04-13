"""Finding aggregator: deduplicates and computes composite severity."""
from __future__ import annotations

from collections import defaultdict

from app.schemas.enums import SEVERITY_ORDER, Severity
from app.schemas.finding import FindingCreate


def aggregate_findings(findings: list[FindingCreate]) -> list[FindingCreate]:
    """Deduplicate findings by (vulnerability_type, location) keeping the
    highest severity, highest confidence and merging evidence payloads.
    Tool attribution is preserved via evidence.
    """
    if not findings:
        return []

    bucket: dict[tuple[str, str | None], FindingCreate] = {}
    evidence_bucket: dict[tuple[str, str | None], list[dict]] = defaultdict(list)
    tool_bucket: dict[tuple[str, str | None], set[str]] = defaultdict(set)

    for f in findings:
        key = (f.vulnerability_type.value, f.location)
        tool_bucket[key].add(f.tool.value)
        evidence_bucket[key].extend(f.evidence)

        if key not in bucket:
            bucket[key] = f
            continue

        current = bucket[key]
        # pick higher severity
        if SEVERITY_ORDER[f.severity] > SEVERITY_ORDER[current.severity]:
            bucket[key] = f.model_copy()
        # bump confidence if additional tool confirms
        bucket[key] = bucket[key].model_copy(
            update={"confidence": min(1.0, max(current.confidence, f.confidence) + 0.1)}
        )

    out: list[FindingCreate] = []
    for key, base in bucket.items():
        merged = base.model_copy(update={"evidence": evidence_bucket[key]})
        out.append(merged)
    # sort by severity desc
    out.sort(key=lambda x: -SEVERITY_ORDER[x.severity])
    return out


def composite_severity(findings: list[FindingCreate]) -> Severity:
    if not findings:
        return Severity.INFO
    return max(findings, key=lambda f: SEVERITY_ORDER[f.severity]).severity
