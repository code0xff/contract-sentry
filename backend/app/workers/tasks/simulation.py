"""Exploit simulation task."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.db.session import session_scope
from app.models.domain import SimulationRun
from app.schemas.enums import SimulationStatus, VulnerabilityType
from app.simulators.fork_simulator import ForkSimulator
from app.simulators.foundry_simulator import FoundrySimulator
from app.workers.celery_app import celery_app

log = get_logger(__name__)


async def _run(simulation_id: str, use_fork: bool) -> None:
    async with session_scope() as session:
        sim = await session.get(SimulationRun, simulation_id)
        if sim is None:
            return
        sim.status = SimulationStatus.RUNNING

    try:
        template = VulnerabilityType(sim.template)
    except ValueError:
        template = VulnerabilityType.OTHER

    try:
        if use_fork and sim.fork_rpc_url:
            result = ForkSimulator().run(
                template=template,
                fork_rpc_url=sim.fork_rpc_url,
                fork_block=sim.fork_block,
            )
        else:
            result = FoundrySimulator().run(template=template)
    except Exception as exc:
        log.error("simulation_failed", simulation_id=simulation_id, error=str(exc))
        result = {"status": SimulationStatus.FAILED, "output": str(exc), "trace": None}

    async with session_scope() as session:
        sim = await session.get(SimulationRun, simulation_id)
        assert sim is not None
        sim.status = result["status"]
        sim.output = result.get("output")
        sim.trace = result.get("trace")
        sim.finished_at = datetime.now(tz=timezone.utc)


@celery_app.task(
    name="app.workers.tasks.simulation.run_simulation",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run_simulation(self, simulation_id: str, use_fork: bool = False) -> None:
    try:
        asyncio.run(_run(simulation_id, use_fork))
    except Exception as exc:
        raise self.retry(exc=exc)
