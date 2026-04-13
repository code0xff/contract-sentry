# Scope

## In Scope

- Solidity 소스코드 및 EVM 바이트코드 제출 및 분석
- 정적 분석: Slither, Mythril 통합
- 동적 분석/퍼징: Echidna, Medusa 통합
- 익스플로잇 자동 생성 및 Foundry 포크 네트워크에서 시뮬레이션
- 취약점 리포트 생성 (JSON, HTML)
- 비동기 작업 큐 기반 분석 파이프라인 (Celery + Redis)
- Docker 샌드박스 격리 실행
- Web UI (컨트랙트 업로드, 작업 모니터링, 리포트 조회)
- REST API (CLI 및 Web UI 공용)
- 로컬 Docker Compose 기반 실행 환경

## Out Of Scope

- 실제 온체인 트랜잭션 전송 및 컨트랙트 배포
- 블록체인 노드 직접 운영 (Foundry anvil 포크 활용)
- Vyper 등 비-Solidity 언어 지원 (초기 범위 외)
- 클라우드 배포 인프라 구성 (WS6 이후 전략으로 분리)
- CI/CD 파이프라인 통합 플러그인
- 고급 관측성 도구 (Grafana, Prometheus 등) — WS6 이후

## Constraints

- 로컬 실행 우선 (Docker Compose 기반, 이후 클라우드 배포 가능 구조)
- 오픈소스 분석 도구만 통합 (Slither, Mythril, Echidna, Medusa, Foundry)
- 비동기 큐 기반 (장시간 실행 분석 작업 대응)
- API-first 설계 (CLI + Web UI 모두 동일 API 사용)
- 컨트랙트 실행은 반드시 격리된 Docker 샌드박스에서만 수행

## Compatibility And Operability Constraints

- REST API v1 인터페이스는 WS1에서 확정 후 WS2~6에서 변경 금지
- 각 인터페이스 변경 전 하위 호환성 영향 범위 확인 필수
- 관측성 기반 (로그, 헬스체크) — WS6에서 완성, 그 전에 기본 헬스체크는 WS1에서 구현
