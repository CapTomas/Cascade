"""Models for the planning phase of a Cascade project."""

from dataclasses import dataclass, field
from typing import List, Optional
from cascade.models.enums import TicketType, Severity


@dataclass
class ProposedTicket:
    """A ticket proposed by the AI during the planning phase."""

    title: str
    description: str
    ticket_type: TicketType = TicketType.TASK
    severity: Severity = Severity.MEDIUM
    acceptance_criteria: str = ""
    estimated_effort: Optional[int] = None
    topics: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Titles of dependent tickets
    children: List["ProposedTicket"] = field(default_factory=list)


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
    tech_stack: List[str] = field(default_factory=list)
    topics: List[ProposedTopic] = field(default_factory=list)
    tickets: List[ProposedTicket] = field(default_factory=list)
    suggested_adrs: List[dict] = field(default_factory=list)  # ADR structure
