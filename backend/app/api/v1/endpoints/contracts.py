from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.domain import Contract, Job
from app.schemas.contract import ContractCreate, ContractOut
from app.schemas.enums import JobStatus, ToolName
from app.schemas.job import JobCreate, JobOut
from app.workers.dispatcher import dispatch_job

router = APIRouter()


@router.post("", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    session: AsyncSession = Depends(get_session),
) -> Contract:
    contract = Contract(
        name=payload.name,
        language=payload.language,
        source=payload.source,
        bytecode=payload.bytecode,
        compiler_version=payload.compiler_version,
    )
    session.add(contract)
    await session.commit()
    await session.refresh(contract)
    return contract


@router.get("", response_model=list[ContractOut])
async def list_contracts(session: AsyncSession = Depends(get_session)) -> list[Contract]:
    result = await session.execute(select(Contract).order_by(Contract.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{contract_id}", response_model=ContractOut)
async def get_contract(contract_id: str, session: AsyncSession = Depends(get_session)) -> Contract:
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "contract not found")
    return contract


@router.post("/{contract_id}/analyze", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def analyze_contract(
    contract_id: str,
    payload: JobCreate | None = None,
    session: AsyncSession = Depends(get_session),
) -> Job:
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "contract not found")

    tools = payload.tools if payload else [ToolName.SLITHER, ToolName.MYTHRIL]
    job = Job(
        contract_id=contract.id,
        status=JobStatus.PENDING,
        tools=[t.value for t in tools],
        progress=0,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    dispatch_job(job.id, contract.id, [t.value for t in tools])
    return job
