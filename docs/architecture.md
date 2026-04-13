# Architecture

## System Boundary

Contract-Centry는 EVM 기반 스마트 컨트랙트의 보안 취약점 분석, 퍼징, 익스플로잇 시뮬레이션, 리포트 생성을 담당하는 플랫폼이다.

이 시스템이 소유하지 않는 것:
- 실제 온체인 트랜잭션 전송 (시뮬레이션 전용)
- 컨트랙트 배포/운영 관리
- 블록체인 노드 직접 운영 (Foundry anvil 포크 활용)

## Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.x (async), Pydantic v2
- **Workers**: Celery + Redis
- **Analysis**: Slither, Mythril, Echidna (subprocess, sandboxed)
- **Simulation**: Foundry (forge, anvil), web3.py
- **Storage**: PostgreSQL (metadata/findings), Redis (queue/cache)
- **Frontend**: Next.js 14 (App Router) + TypeScript
- **Infra**: Docker Compose (로컬), non-root sandbox containers
- **Observability**: Prometheus metrics, structlog JSON 로그

## Major Components

### API Server (FastAPI)
- REST API: 컨트랙트 업로드, 분석 작업 등록, 작업 상태 조회, 리포트 반환
- 분석 작업을 Celery 큐에 등록하고 Job 엔티티로 상태 추적
- `/health/live`, `/health/ready`, `/metrics` 제공

### Analysis Orchestrator
- API와 워커 사이의 작업 라우팅
- Job 상태 머신 관리 (pending → running → completed/failed/cancelled)
- Finding aggregator로 결과 정규화

### Static Analysis Worker (queue=`static_analysis`)
- Slither, Mythril 실행을 독립 Docker 샌드박스에서 수행
- JSON 출력 파싱 후 Finding 스키마로 정규화

### Dynamic Analysis / Fuzzing Worker (queue=`dynamic_analysis`)
- Echidna 퍼징 실행
- 카운터 예제와 커버리지 데이터를 Evidence로 수집

### Exploit Simulator (queue=`simulation`)
- 취약점 타입 → Foundry test 템플릿 매핑
- `forge test` 및 forked network (anvil) 시뮬레이션
- 트레이스/로그 캡처

### Report Generator (queue=`report`)
- Finding 집계, 중복 제거, 복합 severity 계산
- JSON, Markdown, HTML 리포트 렌더링

### Result Store
- PostgreSQL: Contract, Job, Finding, Evidence, SimulationRun, Report
- Redis: Celery broker, 일시 캐시

### Web UI (Next.js)
- 업로드, 작업 상태, 취약점 리스트, 리포트 뷰어, 시뮬레이션 패널

### Isolated Sandbox
- 각 도구는 전용 Docker 이미지에서 non-root(uid 1000)로 실행
- 네트워크 비활성 (fork simulator는 예외)
- 읽기 전용 FS + `/tmp/analysis` writable
- CPU 2 cores, Memory 4GB, 정적 300s / 동적 600s / fork 900s 타임아웃

## Domain Model

### State Machines

```
Job: pending → running → completed
                       ↘ failed
                       ↘ cancelled

SimulationRun: queued → running → succeeded | failed | timed_out

Report: draft → ready
```

### Entities

- `Contract`: 업로드된 소스/바이트코드, 메타데이터
- `Job`: 분석 실행 단위, 여러 도구를 fan-out
- `Finding`: 취약점 단위 (severity, vuln_type, location, tool, confidence)
- `Evidence`: Finding 원본 근거 (raw output, trace, tx)
- `SimulationRun`: 익스플로잇 실행 결과 (status, trace, PoC)
- `Report`: Job에 연결된 최종 집계 결과

## API Contract (v1)

```
POST   /api/v1/contracts                     Upload contract (source or bytecode)
GET    /api/v1/contracts                     List contracts
GET    /api/v1/contracts/{id}                Contract detail
POST   /api/v1/contracts/{id}/analyze        Trigger analysis job
GET    /api/v1/jobs/{id}                     Job status + progress
GET    /api/v1/jobs/{id}/findings            Findings for job
POST   /api/v1/jobs/{id}/simulate            Run exploit simulation
GET    /api/v1/simulations/{id}              Simulation status
POST   /api/v1/simulations/{id}/fork-run     Fork network simulation
GET    /api/v1/reports/{id}                  Report JSON
GET    /api/v1/reports/{id}/markdown         Report Markdown
GET    /api/v1/reports/{id}/html             Report HTML
GET    /health/live                          Liveness
GET    /health/ready                         Readiness
GET    /metrics                              Prometheus metrics
```

## Async Task Contract

Queues: `static_analysis`, `dynamic_analysis`, `simulation`, `report`

Policy:
- Retry 최대 3회, 30s initial backoff (transient 오류)
- Timeout: static 300s, dynamic 600s, simulation 900s
- Idempotency: `job_id` 키로 Redis lock, 동일 Job 중복 enqueue 방지
- 실패 시 Job을 FAILED로 전이, error context 기록

## Security Isolation Contract

- 모든 분석 컨테이너: `--network=none`; fork simulator만 내부 RPC 허용
- `--read-only` + `tmpfs=/tmp/analysis`
- `--cpus=2`, `--memory=4g`, `--pids-limit=256`
- `--user=1000:1000`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`
- 업로드된 컨트랙트 소스는 정규화 후 최대 512KB까지 허용
- 시스템 경계(업로드, RPC URL, 외부 입력)에서 검증

## Runtime Topology

```
  user  ─▶  Next.js UI  ─▶  FastAPI API  ─▶  Celery enqueue
                                                │
                ┌──────────────┬────────────────┼─────────────────┐
                ▼              ▼                ▼                 ▼
          static_analysis  dynamic_analysis  simulation        report
             worker            worker          worker          worker
                │              │                │                 │
                ▼              ▼                ▼                 ▼
        Docker sandbox (non-root, no-net, cpu/mem-limit, read-only FS)

              Redis (broker + result)   ↔   Postgres (domain store)
```

## Observability Baseline

- 구조화 로그(JSON, `job_id`, `correlation_id`, `tool`)
- Prometheus: `job_total`, `job_duration_seconds`, `tool_failure_total`
- `/health/live`(프로세스 alive), `/health/ready`(DB+Redis probe)

## Failure Mode And Recovery

| 실패 | 복구 |
|------|------|
| 분석 도구 타임아웃 | 컨테이너 강제 종료, Job FAILED, 에러 기록 |
| Redis 단절 | Celery 3회 재연결, 실패 시 Job FAILED |
| 컨테이너 OOM | 샌드박스 종료, Job FAILED |
| Fork 실패 | static-only로 진행, 사용자 알림 |
| 악성 코드 실행 | 네트워크/FS/리소스 격리로 호스트 보호 |

## Future Notes

AuthN/AuthZ, 멀티테넌시, GitHub 연동, 배치 스캔, 요금제 등은 `docs/roadmap.md`의 future backlog에서 관리한다.
