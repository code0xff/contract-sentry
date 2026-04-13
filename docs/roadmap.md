# Roadmap

## Current Status

v0.1 — MVP: static/dynamic analyzers, aggregation, JSON/Markdown/HTML report, template-based exploit simulator with fork support, basic UI + CLI.

## Workstreams (delivered)

- **WS1 — 프로젝트 기반 및 컴포넌트 골격**
- **WS2 — 정적 분석 파이프라인** (Slither, Mythril)
- **WS3 — 동적 분석 / 퍼징** (Echidna)
- **WS4 — 익스플로잇 시뮬레이션** (Foundry forge + fork)
- **WS5 — 리포트 시스템 및 Web UI**
- **WS6 — 운영성 강화 및 보안 하드닝**

## Future Backlog

- AuthN / AuthZ (JWT, 멀티테넌시)
- GitHub/GitLab 연동 및 배치 스캔
- Medusa 추가 퍼저 지원
- Certora / Kontrol 등 formal verification 통합 (선택)
- DeFi flash-loan 전용 시뮬레이션 템플릿
- 분석 결과의 diff view (연속 업로드 간 취약점 변화)
- SIEM 연동용 syslog / webhook 알림
- 캐시: 동일 bytecode 해시 재사용
- horizontal scaling: Kubernetes 배포 매니페스트
- 모델 기반 자동 PoC 생성 (LLM + 정적 분석 결합)

## Deprecations

현재 없음.
