"""Context builder for ticket execution."""

from __future__ import annotations

import logging

from cascade.core.knowledge_base import KnowledgeBase
from cascade.core.ticket_manager import TicketManager
from cascade.models.context import MultiTicketContext, TicketContext
from cascade.models.enums import ContextMode
from cascade.models.ticket import Ticket

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds minimal context for current ticket.

    Implements lazy and minimal context assembly to reduce token waste
    and maintain focus on the current task.
    """

    def __init__(self, kb: KnowledgeBase, tm: TicketManager):
        """
        Initialize context builder.

        Args:
            kb: KnowledgeBase instance to load conventions/patterns/ADRs
            tm: TicketManager instance to load similar tickets
        """
        self.kb = kb
        self.tm = tm

    def build_context(
        self,
        ticket: Ticket,
        mode: ContextMode = ContextMode.MINIMAL,
        token_budget: int | None = None,
    ) -> TicketContext:
        """
        Build context for a ticket based on the specified mode.

        Modes:
        - MINIMAL: Only ticket + conventions
        - STANDARD: + relevant patterns/ADRs
        - FULL: + similar tickets, more patterns/ADRs

        Args:
            ticket: The ticket to build context for
            mode: Requested context mode
            token_budget: Optional token limit for this context

        Returns:
            Assembled TicketContext
        """
        logger.debug(f"Building {mode.value} context for ticket #{ticket.id}")

        # Always include conventions
        conventions = self.kb.get_conventions()

        patterns = []
        adrs = []
        similar_tickets = []

        if mode == ContextMode.STANDARD:
            patterns = self.kb.get_relevant_patterns(ticket, limit=3)
            adrs = self.kb.get_relevant_adrs(ticket, limit=3)

        elif mode == ContextMode.FULL:
            patterns = self.kb.get_relevant_patterns(ticket, limit=5)
            adrs = self.kb.get_relevant_adrs(ticket, limit=5)
            similar_tickets = self.tm.get_similar_completed_tickets(ticket, limit=3)

        context = TicketContext(
            ticket=ticket,
            conventions=conventions,
            patterns=patterns,
            adrs=adrs,
            similar_tickets=similar_tickets,
            mode=mode,
        )

        # Budget Enforcement
        if token_budget:
            from cascade.utils.tokens import estimate_context_tokens

            # Simple trimming if over budget
            # Priority: Ticket > Conventions > Patterns > ADRs > Similar Tickets
            current_tokens = estimate_context_tokens(context)
            if current_tokens > token_budget:
                logger.warning(
                    f"Context for ticket #{ticket.id} exceeds budget ({current_tokens} > {token_budget}). Trimming..."
                )

                # Trim similar tickets first
                if context.similar_tickets:
                    context.similar_tickets = []
                    current_tokens = estimate_context_tokens(context)

                # Trim ADRs if still over
                if current_tokens > token_budget and context.adrs:
                    while context.adrs and current_tokens > token_budget:
                        context.adrs.pop()
                        current_tokens = estimate_context_tokens(context)

                # Trim Patterns if still over
                if current_tokens > token_budget and context.patterns:
                    while context.patterns and current_tokens > token_budget:
                        context.patterns.pop()
                        current_tokens = estimate_context_tokens(context)

                logger.info(f"Context trimmed to {current_tokens} tokens")

        return context

    def build_multi_context(
        self,
        tickets: list[Ticket],
        mode: ContextMode = ContextMode.MINIMAL,
        token_budget: int | None = None,
    ) -> MultiTicketContext:
        """
        Build context for multiple tickets.

        Gathers conventions and unique relevant patterns/ADRs for any
        ticket in the list.

        Args:
            tickets: The tickets to build context for
            mode: Requested context mode
            token_budget: Optional token limit

        Returns:
            Assembled MultiTicketContext
        """
        if not tickets:
            raise ValueError("Ticket list cannot be empty")

        logger.debug(f"Building {mode.value} multi-context for {len(tickets)} tickets")

        conventions = self.kb.get_conventions()
        all_patterns = {}
        all_adrs = {}

        for ticket in tickets:
            if mode == ContextMode.STANDARD:
                for p in self.kb.get_relevant_patterns(ticket, limit=3):
                    all_patterns[p.pattern_name] = p
                for a in self.kb.get_relevant_adrs(ticket, limit=3):
                    all_adrs[a.title] = a
            elif mode == ContextMode.FULL:
                for p in self.kb.get_relevant_patterns(ticket, limit=5):
                    all_patterns[p.pattern_name] = p
                for a in self.kb.get_relevant_adrs(ticket, limit=5):
                    all_adrs[a.title] = a

        context = MultiTicketContext(
            tickets=tickets,
            conventions=conventions,
            patterns=list(all_patterns.values()),
            adrs=list(all_adrs.values()),
            mode=mode,
        )

        # Basic budget enforcement (similar to single-ticket, but simpler for now)
        if token_budget:
            from cascade.utils.tokens import estimate_context_tokens

            current_tokens = estimate_context_tokens(context)
            if current_tokens > token_budget:
                logger.warning(
                    f"Multi-context exceeds budget ({current_tokens} > {token_budget}). Trimming ADRs/Patterns..."
                )
                while context.adrs and current_tokens > token_budget:
                    context.adrs.pop()
                    current_tokens = estimate_context_tokens(context)
                while context.patterns and current_tokens > token_budget:
                    context.patterns.pop()
                    current_tokens = estimate_context_tokens(context)

        return context
