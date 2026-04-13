"""Unit tests for job notifications."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.notifications import send_job_notification


@pytest.mark.asyncio
async def test_webhook_sends_correct_payload():
    mock_response = MagicMock()
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.core.notifications.settings") as mock_settings, patch(
        "httpx.AsyncClient", return_value=mock_client
    ):
        mock_settings.webhook_url = "http://example.com/hook"
        mock_settings.slack_webhook_url = None

        await send_job_notification(
            job_id="job-123",
            status="completed",
            findings_count=5,
            report_id="report-abc",
        )

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "http://example.com/hook"
    sent_payload = call_args[1]["json"]
    assert sent_payload["job_id"] == "job-123"
    assert sent_payload["status"] == "completed"
    assert sent_payload["findings_count"] == 5
    assert sent_payload["event"] == "job.completed"


@pytest.mark.asyncio
async def test_slack_sends_on_completion():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.core.notifications.settings") as mock_settings, patch(
        "httpx.AsyncClient", return_value=mock_client
    ):
        mock_settings.webhook_url = None
        mock_settings.slack_webhook_url = "http://slack.example.com/hook"

        await send_job_notification(
            job_id="job-456",
            status="completed",
            findings_count=3,
        )

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    sent_payload = call_args[1]["json"]
    assert "blocks" in sent_payload


@pytest.mark.asyncio
async def test_notification_does_not_raise_on_http_error():
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.HTTPError("connection failed")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.core.notifications.settings") as mock_settings, patch(
        "httpx.AsyncClient", return_value=mock_client
    ):
        mock_settings.webhook_url = "http://example.com/hook"
        mock_settings.slack_webhook_url = None

        # Should not raise
        await send_job_notification(job_id="job-789", status="failed")
