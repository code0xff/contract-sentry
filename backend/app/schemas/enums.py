"""Enumerations shared by schemas and domain models."""
from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityType(str, Enum):
    REENTRANCY = "reentrancy"
    INTEGER_OVERFLOW = "integer_overflow"
    ACCESS_CONTROL = "access_control"
    UNCHECKED_RETURN = "unchecked_return"
    TIMESTAMP_DEPENDENCY = "timestamp_dependency"
    DELEGATECALL = "delegatecall"
    SELF_DESTRUCT = "self_destruct"
    FRONT_RUNNING = "front_running"
    DENIAL_OF_SERVICE = "denial_of_service"
    FLASH_LOAN = "flash_loan"
    OTHER = "other"


class ToolName(str, Enum):
    SLITHER = "slither"
    MYTHRIL = "mythril"
    ECHIDNA = "echidna"
    MEDUSA = "medusa"
    FOUNDRY = "foundry"
    INTERNAL = "internal"


class ContractLanguage(str, Enum):
    SOLIDITY = "solidity"
    VYPER = "vyper"
    BYTECODE = "bytecode"


class SimulationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"


class CampaignStatus(str, Enum):
    QUEUED    = "queued"
    PLANNING  = "planning"
    RUNNING   = "running"
    SUCCEEDED = "succeeded"
    PARTIAL   = "partial"
    FAILED    = "failed"
    TIMED_OUT = "timed_out"


SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}


TERMINAL_JOB_STATES: set[JobStatus] = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}

ALLOWED_JOB_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}


def is_allowed_transition(current: JobStatus, target: JobStatus) -> bool:
    return target in ALLOWED_JOB_TRANSITIONS.get(current, set())
