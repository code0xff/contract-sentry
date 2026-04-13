"""API contract tests (routes, status codes, shapes)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_live(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_health_ready_shape(client):
    resp = await client.get("/health/ready")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "status" in body
    assert "checks" in body


@pytest.mark.asyncio
async def test_create_contract_requires_payload(client):
    resp = await client.post("/api/v1/contracts", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_contract_success(client):
    resp = await client.post(
        "/api/v1/contracts",
        json={
            "name": "Dummy.sol",
            "language": "solidity",
            "source": "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\ncontract D {}",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["name"] == "Dummy.sol"
    assert body["language"] == "solidity"


@pytest.mark.asyncio
async def test_create_contract_bytecode_validation(client):
    resp = await client.post(
        "/api/v1/contracts",
        json={"name": "b", "language": "bytecode", "bytecode": "invalid"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_unknown_contract_404(client):
    resp = await client.get("/api/v1/contracts/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_unknown_job_404(client):
    resp = await client.get("/api/v1/jobs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_unknown_report_404(client):
    resp = await client.get("/api/v1/reports/nonexistent")
    assert resp.status_code == 404
