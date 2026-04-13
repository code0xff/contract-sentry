from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.poc_generator import generate_poc
from app.db.session import get_session
from app.models.domain import Finding, Job, SimulationRun
from app.schemas.enums import SimulationStatus
from app.schemas.finding import FindingDiff, FindingOut
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


@router.get("/{job_id}/diff", response_model=FindingDiff)
async def diff_findings(
    job_id: str,
    baseline: str = Query(..., description="The older job_id to compare against"),
    session: AsyncSession = Depends(get_session),
) -> FindingDiff:
    """Compare findings between two jobs to show new/fixed/persisting vulnerabilities."""
    job_b = await session.get(Job, job_id)
    if job_b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")

    job_a = await session.get(Job, baseline)
    if job_a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "baseline job not found")

    result_a = await session.execute(
        select(Finding)
        .where(Finding.job_id == baseline)
        .options(selectinload(Finding.evidences))
    )
    findings_a = list(result_a.scalars().all())

    result_b = await session.execute(
        select(Finding)
        .where(Finding.job_id == job_id)
        .options(selectinload(Finding.evidences))
    )
    findings_b = list(result_b.scalars().all())

    keys_a = {(f.vulnerability_type, f.location): f for f in findings_a}
    keys_b = {(f.vulnerability_type, f.location): f for f in findings_b}

    new_findings = [FindingOut.model_validate(f) for k, f in keys_b.items() if k not in keys_a]
    fixed_findings = [FindingOut.model_validate(f) for k, f in keys_a.items() if k not in keys_b]
    persisting_findings = [FindingOut.model_validate(f) for k, f in keys_b.items() if k in keys_a]

    return FindingDiff(
        new=new_findings,
        fixed=fixed_findings,
        persisting=persisting_findings,
        summary={
            "new": len(new_findings),
            "fixed": len(fixed_findings),
            "persisting": len(persisting_findings),
        },
    )


@router.post("/{job_id}/findings/{finding_id}/poc", status_code=200)
async def generate_finding_poc(
    job_id: str,
    finding_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Generate LLM-based PoC exploit code for a finding."""
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")

    result = await session.execute(
        select(Finding)
        .where(Finding.id == finding_id, Finding.job_id == job_id)
        .options(selectinload(Finding.evidences))
    )
    finding = result.scalars().first()
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "finding not found")

    poc = await generate_poc(FindingOut.model_validate(finding))
    return {"poc": poc}
