from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import JobStatus, ToolName


class JobCreate(BaseModel):
    tools: list[ToolName] = Field(
        default_factory=lambda: [ToolName.SLITHER, ToolName.MYTHRIL]
    )


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    status: JobStatus
    tools: list[str]
    progress: int
    error: str | None = None
    tool_errors: dict[str, str] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
