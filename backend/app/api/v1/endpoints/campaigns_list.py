"""Top-level campaign list/detail endpoints (not scoped to a job)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.domain import AttackCampaign, Contract, Job
from app.schemas.campaign import CampaignListOut, CampaignOut

router = APIRouter()


async def _enrich(campaign: AttackCampaign, session: AsyncSession) -> CampaignListOut:
    job = await session.get(Job, campaign.job_id)
    contract_id = job.contract_id if job else None
    contract_name = None
    tools = job.tools if job else None
    if contract_id:
        contract = await session.get(Contract, contract_id)
        if contract:
            contract_name = contract.name
    data = CampaignOut.model_validate(campaign).model_dump()
    return CampaignListOut(**data, contract_id=contract_id, contract_name=contract_name, tools=tools)


@router.get("", response_model=list[CampaignListOut])
async def list_campaigns(session: AsyncSession = Depends(get_session)) -> list[CampaignListOut]:
    result = await session.execute(
        select(AttackCampaign).order_by(AttackCampaign.created_at.desc())
    )
    campaigns = list(result.scalars().all())
    return [await _enrich(c, session) for c in campaigns]


@router.get("/{campaign_id}", response_model=CampaignListOut)
async def get_campaign_by_id(
    campaign_id: str, session: AsyncSession = Depends(get_session)
) -> CampaignListOut:
    campaign = await session.get(AttackCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "campaign not found")
    return await _enrich(campaign, session)
