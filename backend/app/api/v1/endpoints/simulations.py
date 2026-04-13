from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.domain import SimulationRun
from app.schemas.simulation import SimulationOut
from app.simulators.foundry_simulator import DEFI_TEMPLATES
from app.workers.dispatcher import dispatch_simulation

router = APIRouter()


@router.get("/templates")
async def list_templates() -> list[dict[str, str]]:
    return [{"name": name, "description": tpl["description"]} for name, tpl in DEFI_TEMPLATES.items()]


@router.get("/{simulation_id}", response_model=SimulationOut)
async def get_simulation(
    simulation_id: str, session: AsyncSession = Depends(get_session)
) -> SimulationRun:
    sim = await session.get(SimulationRun, simulation_id)
    if sim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "simulation not found")
    return sim


@router.post("/{simulation_id}/fork-run", response_model=SimulationOut)
async def fork_run(
    simulation_id: str, session: AsyncSession = Depends(get_session)
) -> SimulationRun:
    sim = await session.get(SimulationRun, simulation_id)
    if sim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "simulation not found")
    if not sim.fork_rpc_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "simulation has no fork_rpc_url")
    dispatch_simulation(sim.id, use_fork=True)
    return sim
