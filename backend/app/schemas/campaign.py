"""Pydantic schemas for AttackCampaign."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enums import CampaignStatus


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    status: CampaignStatus
    attack_plan: str | None = None
    test_code: str | None = None
    output: str | None = None
    trace: str | None = None
    results: dict | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
