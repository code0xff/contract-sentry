from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import SimulationStatus, VulnerabilityType


class SimulationRequest(BaseModel):
    finding_id: str | None = None
    template: VulnerabilityType = VulnerabilityType.REENTRANCY
    fork_rpc_url: str | None = None
    fork_block: int | None = Field(default=None, ge=0)


class SimulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    finding_id: str | None = None
    status: SimulationStatus
    template: str
    fork_rpc_url: str | None = None
    fork_block: int | None = None
    output: str | None = None
    trace: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
