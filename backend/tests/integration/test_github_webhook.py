"""Integration tests for the GitHub webhook receiver."""
from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest

_SECRET = "testsecret"


def _make_request(payload: dict) -> tuple[bytes, str]:
    """Return (body_bytes, signature_header) for the given payload."""
    body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return body, f"sha256={sig}"


@pytest.mark.asyncio
async def test_webhook_no_sol_files(client):
    payload = {
        "commits": [
            {"added": ["README.md"], "modified": ["package.json"]}
        ],
        "repository": {"full_name": "org/repo"},
    }
    body, sig = _make_request(payload)
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = _SECRET
        response = await client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-github-event": "push",
                "x-hub-signature-256": sig,
            },
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
    body, sig = _make_request(payload)
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = _SECRET
        response = await client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-github-event": "push",
                "x-hub-signature-256": sig,
            },
        )
    assert response.status_code == 200
    assert response.json() == {"queued": 2}


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    payload = {
        "commits": [],
        "repository": {"full_name": "org/repo"},
    }
    body, _ = _make_request(payload)
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = "mysecret"
        response = await client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-github-event": "push",
                "x-hub-signature-256": "sha256=invalidsignature",
            },
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_no_secret_configured(client):
    payload = {"commits": [], "repository": {"full_name": "org/repo"}}
    body, sig = _make_request(payload)
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = None
        response = await client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-github-event": "push",
                "x-hub-signature-256": sig,
            },
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_unsupported_event(client):
    payload = {"action": "opened", "issue": {"title": "bug"}}
    body, sig = _make_request(payload)
    with patch("app.api.v1.endpoints.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = _SECRET
        response = await client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "x-github-event": "issues",
                "x-hub-signature-256": sig,
            },
        )
    assert response.status_code == 200
    assert response.json()["queued"] == 0
