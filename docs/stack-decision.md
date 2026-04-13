# Stack Decision

## Candidate Options

### 안 1 — Python-first (선택됨)
`Python + FastAPI + Slither/Mythril/Echidna/Medusa + Foundry/web3.py + Celery/Redis + Next.js + Docker`

- 장점: 핵심 보안 도구(Slither, Mythril, Echidna)가 Python 네이티브 — 언어 브릿지 불필요
- 장점: GIL 문제는 Docker 격리 실행 + Celery 멀티프로세스로 해소
- 장점: 단일 언어 런타임 — 운영 복잡도 낮음
- 리스크: Python 단독 고성능 동시 처리 한계 (분석 병목은 도구 실행 시간이므로 무관)

### 안 2 — TypeScript + Python 하이브리드
`Node.js + NestJS + Python 분석 워커 + viem/ethers.js + BullMQ/Redis + Next.js + Docker`

- 장점: Web3 JS 생태계 강점, viem/ethers.js 통합 자연스러움
- 리스크: Python 워커를 결국 써야 해 이중 런타임 단점만 얻음

### 안 3 — Go 백엔드 + Python 분석 워커
`Go + Gin/Echo + Python gRPC 마이크로서비스 + go-ethereum + Redis Streams + Next.js + Docker`

- 장점: 동시 처리 성능 최고, go-ethereum 통합 탁월
- 리스크: 초기 단계에 불필요한 복잡도 (gRPC, 서비스 메시)

## Selected

**안 1 — Python-first**

선택 근거:
- 분석 병목은 API 레이어가 아니라 Slither/Mythril/Echidna 실행 시간이므로 Python 성능 한계는 비문제
- 단일 언어 런타임으로 유지보수 단순화
- 보안 도구 생태계와의 통합 마찰 최소화

## Open Questions

- 없음 (모두 확정)
