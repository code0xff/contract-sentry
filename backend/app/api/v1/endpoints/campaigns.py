"""Attack campaign endpoints: trigger and poll holistic exploit verification."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.domain import AttackCampaign, Job
from app.schemas.campaign import CampaignOut
from app.schemas.enums import CampaignStatus
from app.workers.dispatcher import dispatch_campaign

router = APIRouter()

_ACTIVE_STATUSES = {CampaignStatus.QUEUED, CampaignStatus.PLANNING, CampaignStatus.RUNNING}


@router.post("/{job_id}/campaign", response_model=CampaignOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_campaign(
    job_id: str, session: AsyncSession = Depends(get_session)
) -> AttackCampaign:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")

    result = await session.execute(
        select(AttackCampaign).where(AttackCampaign.job_id == job_id)
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        if existing.status in _ACTIVE_STATUSES:
            # Already running — return idempotently
            return existing
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "message": "a campaign already exists for this job",
                "campaign_id": existing.id,
                "status": existing.status,
            },
        )

    campaign = AttackCampaign(job_id=job_id, status=CampaignStatus.QUEUED)
    session.add(campaign)
    await session.flush()
    campaign_id = campaign.id
    await session.commit()

    dispatch_campaign(campaign_id)
    return campaign


@router.get("/{job_id}/campaign", response_model=CampaignOut)
async def get_campaign(
    job_id: str, session: AsyncSession = Depends(get_session)
) -> AttackCampaign:
    result = await session.execute(
        select(AttackCampaign).where(AttackCampaign.job_id == job_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no campaign found for this job")
    return campaign
