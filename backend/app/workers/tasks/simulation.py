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
    # Capture all sim fields inside the session to avoid detached-instance access
    sim_template: str = ""
    sim_fork_rpc_url: str | None = None
    sim_fork_block: int | None = None

    async with session_scope() as session:
        sim = await session.get(SimulationRun, simulation_id)
        if sim is None:
            log.error("simulation_missing", simulation_id=simulation_id)
            return
        sim.status = SimulationStatus.RUNNING
        sim_template = sim.template
        sim_fork_rpc_url = sim.fork_rpc_url
        sim_fork_block = sim.fork_block

    try:
        template = VulnerabilityType(sim_template)
    except ValueError:
        template = VulnerabilityType.OTHER

    try:
        if use_fork and sim_fork_rpc_url:
            result = ForkSimulator().run(
                template=template,
                fork_rpc_url=sim_fork_rpc_url,
                fork_block=sim_fork_block,
            )
        else:
            result = FoundrySimulator().run(template=template)
    except Exception as exc:
        log.error("simulation_failed", simulation_id=simulation_id, error=str(exc))
        result = {"status": SimulationStatus.FAILED, "output": str(exc), "trace": None}

    async with session_scope() as session:
        sim = await session.get(SimulationRun, simulation_id)
        if sim is None:
            log.error("simulation_disappeared", simulation_id=simulation_id)
            return
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
        log.error("simulation_task_failed", simulation_id=simulation_id, error=str(exc))
        raise self.retry(exc=exc)
