"""Models for ticket execution results and logging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cascade.models.enums import ContextMode


@dataclass
class GateResult:
    """The result of a single quality gate check."""

    gate_name: str
    passed: bool
    output: str = ""
    error: str | None = None


@dataclass
class GateResults:
    """The collection of results from all quality gates."""

    results: list[GateResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Return True if all gates passed."""
        return all(r.passed for r in self.results)

    @property
    def failed_gates(self) -> list[GateResult]:
        """Get list of failed gates."""
        return [r for r in self.results if not r.passed]


@dataclass
class ExecutionLogEntry:
    """A single entry in the project's execution history."""

    id: int | None = None
    ticket_id: int | None = None
    action: str = ""
    agent: str | None = None
    context_mode: ContextMode | None = None
    details: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int | None = None
    execution_time_ms: int | None = None


@dataclass
class ExecutionResult:
    """The result of executing one or more tickets."""

    success: bool
    ticket_id: int  # Primary ticket ID, or the only one in single-ticket mode
    context_mode: ContextMode
    agent_response: str
    error: str | None = None
    execution_time_ms: int = 0
    token_usage: int = 0
    proposals: list[dict[str, Any]] = field(default_factory=list)
    gate_results: GateResults | None = None
    affected_ticket_ids: list[int] = field(default_factory=list)


@dataclass
class BatchExecutionResult:
    """The result of a batch execution."""

    success: bool
    results: list[ExecutionResult] = field(default_factory=list)
    common_agent_response: str = ""
    total_token_usage: int = 0
    total_time_ms: int = 0
    error: str | None = None
