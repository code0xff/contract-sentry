"""SQLAlchemy domain models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.schemas.enums import (
    ContractLanguage,
    JobStatus,
    ReportStatus,
    Severity,
    SimulationStatus,
    ToolName,
    VulnerabilityType,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _utc() -> datetime:
    return datetime.now(tz=timezone.utc)


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    language: Mapped[ContractLanguage] = mapped_column(SAEnum(ContractLanguage))
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    bytecode: Mapped[str | None] = mapped_column(Text, nullable=True)
    compiler_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc)

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="contract", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("contracts.id"))
    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus), default=JobStatus.PENDING)
    tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    contract: Mapped[Contract] = relationship("Contract", back_populates="jobs")
    findings: Mapped[list["Finding"]] = relationship(
        "Finding", back_populates="job", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        "Report", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    simulations: Mapped[list["SimulationRun"]] = relationship(
        "SimulationRun", back_populates="job", cascade="all, delete-orphan"
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    tool: Mapped[ToolName] = mapped_column(SAEnum(ToolName))
    vulnerability_type: Mapped[VulnerabilityType] = mapped_column(SAEnum(VulnerabilityType))
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc)

    job: Mapped[Job] = relationship("Job", back_populates="findings")
    evidences: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="finding", cascade="all, delete-orphan"
    )


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("findings.id"))
    kind: Mapped[str] = mapped_column(String(64))  # raw_output | trace | tx | counter_example
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc)

    finding: Mapped[Finding] = relationship("Finding", back_populates="evidences")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    finding_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("findings.id"), nullable=True)
    status: Mapped[SimulationStatus] = mapped_column(
        SAEnum(SimulationStatus), default=SimulationStatus.QUEUED
    )
    template: Mapped[str] = mapped_column(String(64))
    fork_rpc_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fork_block: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped[Job] = relationship("Job", back_populates="simulations")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), unique=True)
    status: Mapped[ReportStatus] = mapped_column(SAEnum(ReportStatus), default=ReportStatus.DRAFT)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    html: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc)

    job: Mapped[Job] = relationship("Job", back_populates="report")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc)
