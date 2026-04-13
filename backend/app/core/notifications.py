"""Fire-and-forget webhook and Slack notifications for job events."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_job_notification(
    job_id: str,
    status: str,
    findings_count: int = 0,
    report_id: str | None = None,
) -> None:
    """Send notification to configured webhook / Slack. Never raises."""
    payload = {
        "event": f"job.{status}",
        "job_id": job_id,
        "status": status,
        "findings_count": findings_count,
        "report_id": report_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    async with httpx.AsyncClient(timeout=5) as client:
        if settings.webhook_url:
            try:
                await client.post(settings.webhook_url, json=payload)
            except Exception:
                logger.warning("webhook delivery failed", exc_info=True)

        if settings.slack_webhook_url:
            severity_emoji = {"completed": "✅", "failed": "❌"}.get(status, "⚠️")
            slack_payload = {
                "text": f"{severity_emoji} Contract analysis {status}: {findings_count} findings",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"{severity_emoji} *Contract analysis {status}*\n"
                                f"Job: `{job_id}`\n"
                                f"Findings: {findings_count}"
                                + (f"\nReport: `{report_id}`" if report_id else "")
                            ),
                        },
                    }
                ],
            }
            try:
                await client.post(settings.slack_webhook_url, json=slack_payload)
            except Exception:
                logger.warning("slack notification failed", exc_info=True)
