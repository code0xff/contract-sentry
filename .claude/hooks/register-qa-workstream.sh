#!/bin/bash

set -euo pipefail

QA_REPORT=".claude/state/qa-report.md"
ROADMAP_FILE="docs/roadmap.md"
PLAN_FILE="docs/execution-plan.md"
WORKSTREAM_DIR="docs/workstreams"
REGISTRY_FILE=".claude/state/qa-registry.json"
AUTOMATION_FILE=".claude/project-automation.md"
STATE_HOOK=".claude/hooks/autopilot-state.sh"
GOAL="${1:-autopilot-goal}"

get_automation_value() {
  local key="$1"
  grep -E "^- ${key}:" "$AUTOMATION_FILE" | head -n 1 | sed -E "s/^- ${key}:[[:space:]]*//" || true
}

if [ ! -f "$QA_REPORT" ]; then
  echo "register-qa-workstream 실패: QA report가 없습니다." >&2
  exit 2
fi

mkdir -p "$WORKSTREAM_DIR"

findings="$(awk '
  /^## Findings$/ { in_section=1; next }
  /^## / && in_section==1 { exit }
  in_section==1 && /^- / { print }
' "$QA_REPORT")"

if [ -z "$findings" ] || echo "$findings" | grep -Fxq -- "- none"; then
  echo "register-qa-workstream: 등록할 QA finding이 없습니다."
  exit 0
fi

if command -v shasum >/dev/null 2>&1; then
  slug="$(printf '%s\n' "$findings" | shasum | awk '{print substr($1,1,10)}')"
else
  slug="$(printf '%s\n' "$findings" | sha1sum | awk '{print substr($1,1,10)}')"
fi
workstream_file="${WORKSTREAM_DIR}/ws-qa-${slug}.md"
max_reopens="$(get_automation_value qa_max_reopen_attempts)"
[ -z "$max_reopens" ] && max_reopens="3"

mkdir -p "$(dirname "$REGISTRY_FILE")"
if [ ! -f "$REGISTRY_FILE" ]; then
  echo '{}' > "$REGISTRY_FILE"
fi

current_reopens="$(jq -r --arg slug "$slug" '.[$slug] // 0' "$REGISTRY_FILE")"
if [ "$current_reopens" -ge "$max_reopens" ]; then
  if [ -x "$STATE_HOOK" ]; then
    "$STATE_HOOK" defer manual_followups "qa remediation capped for ${slug}: reopen limit ${max_reopens}" >/dev/null 2>&1 || true
  fi
  echo "register-qa-workstream 실패: QA remediation 재등록 한도를 초과했습니다. slug=${slug}" >&2
  exit 2
fi

tmp_registry="$(mktemp)"
jq --arg slug "$slug" '.[$slug] = ((.[$slug] // 0) + 1)' "$REGISTRY_FILE" > "$tmp_registry"
mv "$tmp_registry" "$REGISTRY_FILE"

if [ -f "$workstream_file" ]; then
  echo "register-qa-workstream: 기존 QA workstream 재사용 ${workstream_file}"
else
  cat > "$workstream_file" <<EOF
# QA Remediation Workstream ${slug}

## Goal

- Resolve QA findings discovered after implementing goal: ${GOAL}

## Trigger

- Source report: ${QA_REPORT}

## Findings

${findings}

## Deliverables

- Code or document changes that address each QA finding
- Updated tests or validation where required
- QA report updated to pass on the next cycle

## Exit Criteria

- The linked QA findings are resolved or explicitly deferred with rationale
- Relevant validation passes after remediation

## Out Of Scope

- New feature expansion unrelated to QA findings
EOF
fi

if [ -f "$ROADMAP_FILE" ] && ! grep -Fq "$workstream_file" "$ROADMAP_FILE"; then
  cat >> "$ROADMAP_FILE" <<EOF

## QA Remediation ${slug}

- Goal: resolve QA findings discovered after initial implementation
- Deliverables: see ${workstream_file}
- Exit Criteria: QA report passes without unresolved blocking findings
- Workstream File: ${workstream_file}
EOF
fi

if [ -f "$PLAN_FILE" ] && ! grep -Fq "QA Remediation ${slug}" "$PLAN_FILE"; then
  cat >> "$PLAN_FILE" <<EOF

## QA Remediation ${slug} Plan

- Inspect findings from ${QA_REPORT}
- Implement only the fixes required to resolve those findings
- Re-run validation and QA until this remediation workstream closes
EOF
fi

if [ -x "$STATE_HOOK" ]; then
  "$STATE_HOOK" defer manual_followups "qa workstream registered: ${workstream_file}" >/dev/null 2>&1 || true
  "$STATE_HOOK" qa-remediation "$slug" "$workstream_file" >/dev/null 2>&1 || true
fi

echo "register-qa-workstream 완료: ${workstream_file}"
exit 0
