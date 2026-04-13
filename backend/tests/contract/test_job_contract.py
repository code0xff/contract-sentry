"""Job state transition contract tests."""
from __future__ import annotations

import pytest

from app.schemas.enums import JobStatus, is_allowed_transition


def test_pending_to_running_allowed():
    assert is_allowed_transition(JobStatus.PENDING, JobStatus.RUNNING)


def test_running_to_completed_allowed():
    assert is_allowed_transition(JobStatus.RUNNING, JobStatus.COMPLETED)


def test_running_to_failed_allowed():
    assert is_allowed_transition(JobStatus.RUNNING, JobStatus.FAILED)


def test_terminal_is_terminal():
    assert not is_allowed_transition(JobStatus.COMPLETED, JobStatus.RUNNING)
    assert not is_allowed_transition(JobStatus.FAILED, JobStatus.RUNNING)
    assert not is_allowed_transition(JobStatus.CANCELLED, JobStatus.PENDING)


def test_pending_to_completed_not_allowed():
    assert not is_allowed_transition(JobStatus.PENDING, JobStatus.COMPLETED)


@pytest.mark.asyncio
async def test_analyze_creates_pending_job(client):
    resp = await client.post(
        "/api/v1/contracts",
        json={
            "name": "T.sol",
            "language": "solidity",
            "source": "contract T {}",
        },
    )
    assert resp.status_code == 201
    contract = resp.json()

    resp2 = await client.post(f"/api/v1/contracts/{contract['id']}/analyze", json={})
    assert resp2.status_code == 202
    job = resp2.json()
    assert job["status"] == "pending"
    assert job["progress"] == 0
    assert isinstance(job["tools"], list) and job["tools"]
