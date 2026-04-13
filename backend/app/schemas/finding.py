from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import Severity, ToolName, VulnerabilityType


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    payload: dict[str, Any]


class FindingCreate(BaseModel):
    tool: ToolName
    vulnerability_type: VulnerabilityType
    severity: Severity
    title: str = Field(min_length=1, max_length=255)
    description: str
    location: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    tool: ToolName
    vulnerability_type: VulnerabilityType
    severity: Severity
    title: str
    description: str
    location: str | None = None
    confidence: float
    created_at: datetime
    evidences: list[EvidenceOut] = []
