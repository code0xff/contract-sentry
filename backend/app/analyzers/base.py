"""Abstract analyzer base."""
from __future__ import annotations

import abc

from app.schemas.finding import FindingCreate


class AnalyzerError(RuntimeError):
    """Raised when an analyzer encounters an unrecoverable error."""


class BaseAnalyzer(abc.ABC):
    tool_name: str

    @abc.abstractmethod
    def analyze(self, source: str) -> list[FindingCreate]:
        """Run the analyzer and return normalized findings."""
