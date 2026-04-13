# Contract-Centry

EVM smart contract security testing platform.

## What it does

- Upload Solidity source or bytecode
- Run Slither, Mythril, Echidna as sandboxed workers
- Aggregate findings, dedup, compute composite severity
- Generate JSON / Markdown / HTML reports
- Run exploit simulations with Foundry (forge test, optional mainnet fork)

## Stack

Python 3.11, FastAPI, SQLAlchemy 2.x async, Pydantic v2, Celery + Redis, Postgres, Next.js 14, Docker Compose.

## Quick start (local)

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- UI: http://localhost:3000
- OpenAPI: http://localhost:8000/docs

## CLI

```bash
cd backend
python -m app.cli analyze ../samples/Vuln.sol
python -m app.cli status <job-id>
python -m app.cli report <job-id> --format markdown
```

## Running tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## Layout

- `backend/app/` — FastAPI + workers + analyzers + simulators + reporters
- `backend/tests/` — contract, integration, unit tests
- `frontend/src/` — Next.js UI (App Router)
- `docs/` — architecture, execution plan, acceptance criteria, security, roadmap

See `docs/architecture.md` for the full design.
