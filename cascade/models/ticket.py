from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cascade.models.enums import ContextMode, Severity, TicketStatus, TicketType


@dataclass
class Ticket:
    """
    Represents a unit of work in Cascade.

    Tickets are the core execution unit - each ticket represents a single,
    focused task that an AI agent will complete. Tickets support hierarchical
    organization (parent/child) and dependency tracking.
    """

    id: int | None = None
    ticket_type: TicketType = TicketType.TASK
    title: str = ""
    description: str = ""
    status: TicketStatus = TicketStatus.DEFINED
    severity: Severity | None = None
    priority_score: float = 0.0
    parent_ticket_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_effort: int | None = None  # Story points or hours
    actual_effort: int | None = None
    affected_files: list[str] = field(default_factory=list)
    acceptance_criteria: str = ""
    context_mode: ContextMode = ContextMode.MINIMAL
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize ticket data."""
        if isinstance(self.ticket_type, str):
            self.ticket_type = TicketType(self.ticket_type)
        if isinstance(self.status, str):
            self.status = TicketStatus(self.status)
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity)
        if isinstance(self.context_mode, str):
            self.context_mode = ContextMode(self.context_mode)

    @property
    def is_complete(self) -> bool:
        """Check if ticket is in a terminal state."""
        return self.status in (TicketStatus.DONE, TicketStatus.ABANDONED)

    @property
    def is_executable(self) -> bool:
        """Check if ticket can be executed."""
        return self.status == TicketStatus.READY

    @property
    def is_blocked(self) -> bool:
        """Check if ticket is blocked."""
        return self.status == TicketStatus.BLOCKED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "ticket_type": self.ticket_type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "severity": self.severity.value if self.severity else None,
            "priority_score": self.priority_score,
            "parent_ticket_id": self.parent_ticket_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_effort": self.estimated_effort,
            "actual_effort": self.actual_effort,
            "affected_files": self.affected_files,
            "acceptance_criteria": self.acceptance_criteria,
            "context_mode": self.context_mode.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ticket:
        """Create ticket from dictionary."""
        # Handle datetime fields
        for field_name in ("created_at", "updated_at", "completed_at"):
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])

        # Handle list fields stored as JSON strings
        if isinstance(data.get("affected_files"), str):
            import json

            data["affected_files"] = json.loads(data["affected_files"])
        if isinstance(data.get("metadata"), str):
            import json

            data["metadata"] = json.loads(data["metadata"])

        return cls(**data)


@dataclass
class TicketDependency:
    """Represents a dependency between tickets."""

    ticket_id: int
    depends_on_ticket_id: int
    dependency_type: str = "blocks"
