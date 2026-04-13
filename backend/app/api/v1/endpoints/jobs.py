from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.domain import Finding, Job, SimulationRun
from app.schemas.enums import SimulationStatus
from app.schemas.finding import FindingOut
from app.schemas.job import JobOut
from app.schemas.simulation import SimulationOut, SimulationRequest
from app.workers.dispatcher import dispatch_simulation

router = APIRouter()


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return job


@router.get("/{job_id}/findings", response_model=list[FindingOut])
async def list_findings(
    job_id: str, session: AsyncSession = Depends(get_session)
) -> list[Finding]:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")

    result = await session.execute(
        select(Finding)
        .where(Finding.job_id == job_id)
        .options(selectinload(Finding.evidences))
        .order_by(Finding.created_at.asc())
    )
    return list(result.scalars().all())


@router.post(
    "/{job_id}/simulate",
    response_model=SimulationOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def simulate(
    job_id: str,
    payload: SimulationRequest,
    session: AsyncSession = Depends(get_session),
) -> SimulationRun:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")

    sim = SimulationRun(
        job_id=job.id,
        finding_id=payload.finding_id,
        template=payload.template.value,
        status=SimulationStatus.QUEUED,
        fork_rpc_url=payload.fork_rpc_url,
        fork_block=payload.fork_block,
    )
    session.add(sim)
    await session.commit()
    await session.refresh(sim)

    dispatch_simulation(sim.id, bool(payload.fork_rpc_url))
    return sim
