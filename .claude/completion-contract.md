# Completion Contract

프로젝트 개발 완료 판정을 위한 계약을 정의한다.
기본 정책은 non-blocking(report)이며, 미설정/실패 항목은 최종 보고서에 남긴다.

## Contract

- done_enforcement: report
- artifact_definition: release artifact generated
- artifact_check_cmd: unset
- run_smoke_cmd: echo "run smoke is not configured"
- acceptance_test_cmd: unset
- release_readiness_cmd: find .claude/hooks -type f -name "*.sh" -print0 | xargs -0 -I{} bash -n "{}" && .claude/hooks/validate-project-profile.sh && .claude/hooks/validate-project-approvals.sh && .claude/hooks/validate-project-automation.sh && .claude/hooks/validate-completion-contract.sh
- interface_contract_check: interface contract check is not configured
- compatibility_check: compatibility check is not configured
- failure_mode_check: failure mode check is not configured
- operability_check: operability check is not configured
