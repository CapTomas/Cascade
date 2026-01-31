"""Models for ticket execution results and logging."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from cascade.models.enums import ContextMode


@dataclass
class GateResult:
    """The result of a single quality gate check."""

    gate_name: str
    passed: bool
    output: str = ""
    error: Optional[str] = None


@dataclass
class GateResults:
    """The collection of results from all quality gates."""

    results: List[GateResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Return True if all gates passed."""
        return all(r.passed for r in self.results)

    @property
    def failed_gates(self) -> List[GateResult]:
        """Get list of failed gates."""
        return [r for r in self.results if not r.passed]


@dataclass
class ExecutionLogEntry:
    """A single entry in the project's execution history."""

    id: Optional[int] = None
    ticket_id: Optional[int] = None
    action: str = ""
    agent: Optional[str] = None
    context_mode: Optional[ContextMode] = None
    details: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: Optional[int] = None
    execution_time_ms: Optional[int] = None


@dataclass
class ExecutionResult:
    """The result of executing one or more tickets."""

    success: bool
    ticket_id: int  # Primary ticket ID, or the only one in single-ticket mode
    context_mode: ContextMode
    agent_response: str
    error: Optional[str] = None
    execution_time_ms: int = 0
    token_usage: int = 0
    proposals: List[dict] = field(default_factory=list)
    gate_results: Optional[GateResults] = None
    affected_ticket_ids: List[int] = field(default_factory=list)


@dataclass
class BatchExecutionResult:
    """The result of a batch execution."""

    success: bool
    results: List[ExecutionResult] = field(default_factory=list)
    common_agent_response: str = ""
    total_token_usage: int = 0
    total_time_ms: int = 0
    error: Optional[str] = None
