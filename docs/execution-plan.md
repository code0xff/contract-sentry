# Execution Plan

## Global Plan

- WS1에서 모든 인터페이스 계약을 확정한 후 구현 시작 (contract-first)
- acceptance-criteria.md를 기준으로 각 WS의 exit criteria를 검증
- roadmap 순서대로 workstream을 순차 실행
- 각 인터페이스 변경 전 하위 호환성 영향 범위 확인
- verify는 acceptance-criteria.md 기준으로 수행
- QA에서 누락 요구사항 발견 시 remediation workstream 등록 후 다음 cycle
- 시스템 경계 또는 인터페이스 계약 변경 시에만 /plan 재실행

## Workstream 1 Plan — 프로젝트 기반 및 컴포넌트 골격

1. Docker Compose 파일 작성 (FastAPI, Redis, Celery Worker, Next.js 서비스 정의)
2. FastAPI 앱 골격 구현 (라우터 구조, `GET /api/v1/health` 엔드포인트)
3. Celery 워커 골격 구현 (task 등록, 상태 추적 패턴)
4. `POST /api/v1/analysis` → 작업 큐 등록 → `GET /api/v1/analysis/{job_id}` 상태 조회 기본 흐름 구현
5. 컨트랙트 제출 페이로드 스키마 확정 (소스코드/바이트코드)
6. Docker 샌드박스 격리 실행 유틸리티 구현 (컨테이너 생성/소멸, 리소스 제한, 타임아웃)

## Workstream 2 Plan — 정적 분석 파이프라인

1. Static Analysis Worker 구현 (Slither Docker 이미지 통합)
2. Slither 결과 파싱 및 findings 스키마 정규화
3. Mythril Docker 이미지 통합 및 결과 정규화
4. findings severity 매핑 (Critical/High/Medium/Low/Info)
5. 기본 JSON 리포트 생성
6. 취약한 샘플 컨트랙트(Reentrancy, Integer Overflow)로 integration test 작성

## Workstream 3 Plan — 동적 분석 / 퍼징

1. Fuzzing Worker 구현 (Echidna Docker 이미지 통합)
2. Echidna 결과 파싱 및 findings 정규화
3. Medusa 통합 및 결과 정규화
4. 퍼징 설정 API 파라미터 구현 (시간 제한, 시드, 반복 횟수)
5. 속성 위반 컨트랙트로 integration test 작성

## Workstream 4 Plan — 익스플로잇 시뮬레이션

1. Foundry anvil 포크 관리 모듈 구현 (생성/소멸/TTL)
2. Exploit Simulation Worker 구현
3. findings → 공격 스크립트 자동 생성 로직 구현
4. Foundry fork에서 공격 트랜잭션 실행 및 결과 기록
5. 알려진 취약점 컨트랙트(Reentrancy, Flash Loan 등)에 대한 시뮬레이션 integration test

## Workstream 5 Plan — 리포트 시스템 및 Web UI

1. Report Generator 구현 (static + fuzzing + exploit findings 통합)
2. HTML 리포트 템플릿 구현
3. `GET /api/v1/reports/{job_id}` 엔드포인트 (JSON/HTML 포맷 선택)
4. Next.js 프로젝트 초기화 및 라우터 구성
5. 컨트랙트 업로드 페이지 구현
6. 작업 상태 모니터링 페이지 (폴링 기반)
7. 리포트 뷰어 페이지 (findings 목록, 심각도별 필터)

## Workstream 6 Plan — 운영성 강화 및 보안 하드닝

1. 구조화 JSON 로그 적용 (모든 서비스, job_id 상관관계 키 포함)
2. 헬스체크 엔드포인트 강화 (Redis, 워커 연결 상태 포함)
3. 컨테이너 네트워크 격리 정책 강화 (외부 네트워크 차단)
4. 장애 시나리오 테스트 (타임아웃, OOM, fork 실패, Redis 재연결)
5. `docker compose up` smoke test 자동화
6. 최종 acceptance-criteria.md 기준 전체 검증
