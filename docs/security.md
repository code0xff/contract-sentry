# Security Guardrails

이 문서는 Contract-Centry 플랫폼의 보안 가드레일을 정의한다.

## Trust Boundaries

1. **Untrusted**: 사용자가 제출한 컨트랙트 소스/바이트코드, 외부 RPC URL
2. **Semi-trusted**: 분석 도구가 생성한 JSON/텍스트 출력
3. **Trusted**: 플랫폼 내부 DB 스키마, Celery task payload

모든 외부 입력은 시스템 경계에서 Pydantic validators로 검증한다.

## Sandbox Policy

- 분석 컨테이너는 `--network=none`, `--read-only`, `--cap-drop=ALL`, `--user=1000:1000`
- `--cpus=2`, `--memory=4g`, `--pids-limit=256`
- `/tmp/analysis` 만 tmpfs로 write 허용
- 하드 timeout: 정적 300s / 동적 600s / 포크 시뮬레이션 900s
- `no-new-privileges`로 특권 상승 차단

## Network

- fork simulator만 outbound RPC 허용. 내부 allowlist 또는 호출 전 URL 검증
- FastAPI, workers, DB, Redis 간 통신은 Compose 내부 네트워크로 격리

## Secrets

- DB 자격증명, RPC API 키는 환경변수 또는 `.env`로 주입
- `.env`는 `.gitignore` 대상 (저장소는 `.env.example`만 제공)
- 로그의 RPC URL 쿼리 파라미터는 토큰을 마스킹

## Input Limits

- `source` / `bytecode`: 각각 최대 512KB
- `bytecode` 필드는 `0x` prefix 강제
- 업로드된 소스는 분석 전 임시 파일로만 전달, 실행되지 않음

## Logging

- 구조화 JSON, `job_id` / `correlation_id` / `tool` 포함
- 민감 필드(Private key, Authorization header 등) 마스킹

## Dependency Hygiene

- Python/Node 의존성은 CVE 데이터베이스로 주기적으로 점검
- `requirements.txt` 업데이트는 변경점과 breaking change를 확인 후 반영

## Incident Response

- 치명적 오류(OOM, escape, unexpected egress) 발생 시 Job을 FAILED 처리 후 운영자에게 알림
- 재현 샘플을 보존 (단, 민감 payload는 제외)
