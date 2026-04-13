# Acceptance Criteria

## Functional

| # | Requirement | Verification |
|---|---|---|
| F1 | 사용자는 소스 또는 바이트코드를 업로드할 수 있다 | `POST /api/v1/contracts` 201 응답, `tests/contract/test_api_contract.py` |
| F2 | 분석 작업은 큐에 등록되고 Job으로 추적된다 | `POST /api/v1/contracts/{id}/analyze` 202 + Job entity |
| F3 | Slither/Mythril/Echidna 어댑터는 JSON/텍스트 출력을 Finding으로 정규화한다 | `tests/unit/test_*_adapter.py` |
| F4 | Aggregator는 동일 (vuln_type, location) 중복을 제거한다 | `tests/unit/test_aggregator.py` |
| F5 | Report Generator는 JSON/Markdown/HTML을 생성한다 | `tests/integration/test_report_generation.py`, `/api/v1/reports/{id}/{markdown,html}` |
| F6 | Exploit Simulator는 취약점 타입별 템플릿을 Foundry test로 실행한다 | `SimulationRun` + forge 실행 경로 |
| F7 | Fork simulator는 지정된 RPC URL과 블록 번호로 시뮬레이션한다 | `POST /api/v1/simulations/{id}/fork-run` |
| F8 | CLI(`python -m app.cli`)로 업로드/상태/리포트를 조회할 수 있다 | `app/cli.py` |
| F9 | Web UI에서 업로드, Job 상태, 리포트를 확인할 수 있다 | `frontend/src/app/**` |

## Non-Functional

| # | Requirement | Verification |
|---|---|---|
| N1 | 모든 분석 컨테이너는 non-root, no-network로 실행된다 | `docs/security.md`, Dockerfile 확인 |
| N2 | Job은 허용된 상태 전이만 수행한다 | `tests/contract/test_job_contract.py` |
| N3 | `/health/live`는 항상 200, `/health/ready`는 DB 문제 시 503 | `tests/contract/test_api_contract.py` |
| N4 | 구조화 JSON 로깅 (`job_id`, `correlation_id`) | `app/core/logging.py` |
| N5 | Prometheus 메트릭(`job_total`, `job_duration_seconds`, `tool_failure_total`) 노출 | `GET /metrics` |
| N6 | 분석 도구 subprocess 실패/타임아웃은 명시적 예외로 전파 | `tests/unit/*_adapter.py` |
| N7 | 업로드 페이로드는 최대 512KB, bytecode는 0x prefix | `tests/contract/test_api_contract.py` |

## Traceability Matrix

| Step | Spec | Tests |
|---|---|---|
| 3 Domain model | `app/schemas/enums.py` | `test_job_contract.py`, `test_finding_contract.py` |
| 4 API contract | `app/api/v1/**` | `test_api_contract.py` |
| 5 Async tasks | `app/workers/**` | `test_analysis_flow.py` |
| 6 Security isolation | `app/core/sandbox.py` | `test_static_analysis.py` (timeout) |
| 12 Slither adapter | `app/analyzers/slither_analyzer.py` | `test_slither_adapter.py` |
| 12 Mythril adapter | `app/analyzers/mythril_analyzer.py` | `test_mythril_adapter.py` |
| 13 Echidna adapter | `app/analyzers/echidna_analyzer.py` | `test_echidna_adapter.py` |
| 14 Aggregator | `app/reporters/aggregator.py` | `test_aggregator.py` |
| 15 Report generator | `app/reporters/generator.py` | `test_report_generation.py` |
| 16 Simulator | `app/simulators/foundry_simulator.py` | `app/workers/tasks/simulation.py` |
| 17 Fork simulator | `app/simulators/fork_simulator.py` | manual integration |
| 21 Observability | `app/core/metrics.py`, `app/main.py` | `test_api_contract.py` (readiness) |
