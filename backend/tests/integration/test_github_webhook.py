"""Integration tests for the GitHub webhook receiver."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_webhook_no_sol_files(client):
    payload = {
        "commits": [
            {"added": ["README.md"], "modified": ["package.json"]}
        ],
        "repository": {"full_name": "org/repo"},
    }
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = None
        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"x-github-event": "push"},
        )
    assert response.status_code == 200
    assert response.json() == {"queued": 0}


@pytest.mark.asyncio
async def test_webhook_queues_sol_files(client):
    payload = {
        "commits": [
            {
                "added": ["contracts/Token.sol"],
                "modified": ["contracts/Vault.sol", "README.md"],
            }
        ],
        "repository": {"full_name": "org/repo"},
    }
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = None
        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"x-github-event": "push"},
        )
    assert response.status_code == 200
    assert response.json() == {"queued": 2}


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    payload = {
        "commits": [],
        "repository": {"full_name": "org/repo"},
    }
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = "mysecret"
        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "x-github-event": "push",
                "x-hub-signature-256": "sha256=invalidsignature",
            },
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_unsupported_event(client):
    payload = {"action": "opened", "issue": {"title": "bug"}}
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = None
        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"x-github-event": "issues"},
        )
    assert response.status_code == 200
    assert response.json()["queued"] == 0
