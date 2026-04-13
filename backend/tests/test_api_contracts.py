"""API contract integration tests.

These tests verify the request/response contracts for all v1 endpoints.
They run against an in-memory SQLite database and skip Celery dispatch.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient) -> None:
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_health_ready_returns_json(client: AsyncClient) -> None:
    resp = await client.get("/health/ready")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data
    assert "checks" in data


# ---------------------------------------------------------------------------
# Contracts — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_contract_solidity(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/contracts",
        json={
            "name": "VaultContract",
            "language": "solidity",
            "source": "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Vault {}",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["name"] == "VaultContract"
    assert data["language"] == "solidity"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_contract_bytecode(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/contracts",
        json={
            "name": "BytecodeContract",
            "language": "bytecode",
            "bytecode": "0x6080604052",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["language"] == "bytecode"


@pytest.mark.asyncio
async def test_create_contract_missing_source_and_bytecode(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/contracts",
        json={"name": "Empty", "language": "solidity"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_contract_bytecode_must_start_with_0x(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/contracts",
        json={"name": "Bad", "language": "bytecode", "bytecode": "deadbeef"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_contract_bytecode_language_requires_bytecode_field(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/v1/contracts",
        json={
            "name": "MissingBytecode",
            "language": "bytecode",
            "source": "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract X {}",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Contracts — list / get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_contracts_returns_list(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/contracts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_contracts_includes_created(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/contracts",
        json={"name": "ListMe", "language": "solidity", "source": "contract X {}"},
    )
    resp = await client.get("/api/v1/contracts")
    names = [c["name"] for c in resp.json()]
    assert "ListMe" in names


@pytest.mark.asyncio
async def test_get_contract_by_id(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/contracts",
        json={"name": "Fetchable", "language": "solidity", "source": "contract X {}"},
    )
    contract_id = create.json()["id"]
    resp = await client.get(f"/api/v1/contracts/{contract_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == contract_id


@pytest.mark.asyncio
async def test_get_contract_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/contracts/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Contracts — analyze → Job creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_creates_pending_job(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/contracts",
        json={"name": "AnalyzeMe", "language": "solidity", "source": "contract X {}"},
    )
    contract_id = create.json()["id"]

    resp = await client.post(f"/api/v1/contracts/{contract_id}/analyze")
    assert resp.status_code == 202
    job = resp.json()
    assert job["status"] == "pending"
    assert job["contract_id"] == contract_id
    assert "id" in job
    assert "tools" in job


@pytest.mark.asyncio
async def test_analyze_with_custom_tools(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/contracts",
        json={"name": "CustomTools", "language": "solidity", "source": "contract X {}"},
    )
    contract_id = create.json()["id"]
    resp = await client.post(
        f"/api/v1/contracts/{contract_id}/analyze",
        json={"tools": ["slither"]},
    )
    assert resp.status_code == 202
    assert "slither" in resp.json()["tools"]


@pytest.mark.asyncio
async def test_analyze_contract_not_found(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/contracts/ghost-id/analyze")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Jobs — get / findings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_job_by_id(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/contracts",
        json={"name": "JobFetch", "language": "solidity", "source": "contract X {}"},
    )
    contract_id = create.json()["id"]
    analyze = await client.post(f"/api/v1/contracts/{contract_id}/analyze")
    job_id = analyze.json()["id"]

    resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/jobs/ghost-job")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_findings_returns_empty_for_new_job(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/contracts",
        json={"name": "NoFindings", "language": "solidity", "source": "contract X {}"},
    )
    contract_id = create.json()["id"]
    analyze = await client.post(f"/api/v1/contracts/{contract_id}/analyze")
    job_id = analyze.json()["id"]

    resp = await client.get(f"/api/v1/jobs/{job_id}/findings")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_findings_job_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/jobs/ghost-job/findings")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simulate_job_not_found(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/jobs/ghost-job/simulate",
        json={"template": "reentrancy"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_simulate_creates_queued_simulation(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/contracts",
        json={"name": "SimTest", "language": "solidity", "source": "contract X {}"},
    )
    contract_id = create.json()["id"]
    analyze = await client.post(f"/api/v1/contracts/{contract_id}/analyze")
    job_id = analyze.json()["id"]

    resp = await client.post(
        f"/api/v1/jobs/{job_id}/simulate",
        json={"template": "reentrancy"},
    )
    assert resp.status_code == 202
    sim = resp.json()
    assert sim["status"] == "queued"
    assert sim["template"] == "reentrancy"
    assert sim["job_id"] == job_id


@pytest.mark.asyncio
async def test_get_simulation_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/simulations/ghost-sim")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_simulation_by_id(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/contracts",
        json={"name": "SimGet", "language": "solidity", "source": "contract X {}"},
    )
    contract_id = create.json()["id"]
    analyze = await client.post(f"/api/v1/contracts/{contract_id}/analyze")
    job_id = analyze.json()["id"]
    sim_resp = await client.post(
        f"/api/v1/jobs/{job_id}/simulate",
        json={"template": "reentrancy"},
    )
    sim_id = sim_resp.json()["id"]

    resp = await client.get(f"/api/v1/simulations/{sim_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sim_id


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_report_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reports/ghost-report")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_markdown_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reports/ghost-report/markdown")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_report_html_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reports/ghost-report/html")
    assert resp.status_code == 404
