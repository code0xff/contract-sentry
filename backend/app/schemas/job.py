from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import JobStatus, ToolName


class JobCreate(BaseModel):
    tools: list[ToolName] = Field(
        default_factory=lambda: [ToolName.SLITHER, ToolName.MYTHRIL]
    )
    entry_files: list[str] | None = None  # relative paths e.g. ["src/Token.sol"]


class ToolExecutionStatus(BaseModel):
    status: Literal["ok", "failed", "skipped"]
    summary: str
    detail: str | None = None
    stage: str | None = None
    command: str | None = None
    returncode: int | None = None
    timed_out: bool = False
    stdout_tail: str | None = None
    stderr_tail: str | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    status: JobStatus
    tools: list[str]
    entry_files: list[str] | None = None
    progress: int
    error: str | None = None
    tool_errors: dict[str, ToolExecutionStatus | str] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
