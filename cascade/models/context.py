"""Context models for ticket execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from cascade.models.enums import ContextMode
from cascade.models.knowledge import ADR, Convention, Pattern
from cascade.models.ticket import Ticket


@dataclass
class TicketContext:
    """
    Assembled context for ticket execution.

    Context is built lazily and minimally - only what's needed for
    the current ticket at the current context mode.
    """

    ticket: Ticket
    conventions: list[Convention] = field(default_factory=list)
    patterns: list[Pattern] = field(default_factory=list)
    adrs: list[ADR] = field(default_factory=list)
    similar_tickets: list[Ticket] = field(default_factory=list)
    mode: ContextMode = ContextMode.MINIMAL

    @property
    def conventions_text(self) -> str:
        """Format conventions for prompt inclusion."""
        if not self.conventions:
            return "No project conventions defined."

        grouped: dict[str, list[Convention]] = {}
        for conv in self.conventions:
            grouped.setdefault(conv.category, []).append(conv)

        lines = []
        for category, convs in sorted(grouped.items()):
            lines.append(f"### {category.title()}")
            for conv in sorted(convs, key=lambda c: -c.priority):
                lines.append(f"- **{conv.convention_key}**: {conv.convention_value}")
            lines.append("")

        return "\n".join(lines)

    @property
    def patterns_text(self) -> str:
        """Format patterns for prompt inclusion."""
        if not self.patterns:
            return ""
        return "\n\n".join(p.to_context_string() for p in self.patterns)

    @property
    def adrs_text(self) -> str:
        """Format ADRs for prompt inclusion."""
        if not self.adrs:
            return ""
        return "\n\n".join(a.to_context_string() for a in self.adrs)

    def estimate_tokens(self) -> int:
        """Rough token count estimate (4 chars per token)."""
        total_chars = (
            len(self.ticket.title)
            + len(self.ticket.description)
            + len(self.ticket.acceptance_criteria)
            + len(self.conventions_text)
            + len(self.patterns_text)
            + len(self.adrs_text)
        )
        # Add overhead for similar tickets
        for t in self.similar_tickets:
            total_chars += len(t.title) + len(t.description)

        return total_chars // 4


@dataclass
class MultiTicketContext:
    """Assembled context for multiple tickets execution."""

    tickets: list[Ticket]
    conventions: list[Convention] = field(default_factory=list)
    patterns: list[Pattern] = field(default_factory=list)
    adrs: list[ADR] = field(default_factory=list)
    mode: ContextMode = ContextMode.MINIMAL

    @property
    def conventions_text(self) -> str:
        return TicketContext(ticket=self.tickets[0], conventions=self.conventions).conventions_text

    @property
    def patterns_text(self) -> str:
        if not self.patterns:
            return ""
        return "\n\n".join(p.to_context_string() for p in self.patterns)

    @property
    def adrs_text(self) -> str:
        if not self.adrs:
            return ""
        return "\n\n".join(a.to_context_string() for a in self.adrs)


@dataclass
class TokenBudget:
    """Hard limits on context size."""

    MINIMAL_MODE: int = 2000
    STANDARD_MODE: int = 5000
    FULL_MODE: int = 10000

    def get_budget(self, mode: ContextMode, agent_token_limit: int) -> int:
        """
        Get token budget for mode, respecting agent limits.

        Reserves 70% of agent capacity for response.
        """
        mode_limits = {
            ContextMode.MINIMAL: self.MINIMAL_MODE,
            ContextMode.STANDARD: self.STANDARD_MODE,
            ContextMode.FULL: self.FULL_MODE,
        }
        mode_limit = mode_limits[mode]
        # Reserve 70% for response
        agent_context_limit = int(agent_token_limit * 0.3)
        return min(mode_limit, agent_context_limit)
