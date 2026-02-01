from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cascade.models.enums import Severity, TicketType


@dataclass
class ProposedTicket:
    """A ticket proposed by the AI during the planning phase."""

    title: str
    description: str
    ticket_type: TicketType = TicketType.TASK
    severity: Severity = Severity.MEDIUM
    acceptance_criteria: str = ""
    estimated_effort: int | None = None
    topics: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Titles of dependent tickets
    children: list[ProposedTicket] = field(default_factory=list)


@dataclass
class ProposedTopic:
    """A topic proposed by the AI during the planning phase."""

    name: str
    description: str = ""


@dataclass
class PlanningResult:
    """The result of a requirements analysis and planning session."""

    project_name: str
    project_description: str
    tech_stack: list[str] = field(default_factory=list)
    topics: list[ProposedTopic] = field(default_factory=list)
    tickets: list[ProposedTicket] = field(default_factory=list)
    suggested_adrs: list[dict[str, Any]] = field(default_factory=list)  # ADR structure
