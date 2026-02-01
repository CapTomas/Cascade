"""Token counting utility for Cascade."""

from __future__ import annotations

import logging
from typing import Any

try:
    import tiktoken

    HAS_TIKTOKEN = True
except ImportError:
    tiktoken = None  # type: ignore
    HAS_TIKTOKEN = False

logger = logging.getLogger(__name__)


class TokenBudget:
    """Token budget limits for different context modes."""

    # Default limits (Phase 2.3 of Roadmap)
    MINIMAL = 2000
    STANDARD = 5000
    FULL = 10000

    def __init__(
        self,
        minimal: int = MINIMAL,
        standard: int = STANDARD,
        full: int = FULL,
    ):
        self.minimal = minimal
        self.standard = standard
        self.full = full

    def get_limit(self, mode: str) -> int:
        """Get the token limit for a specific mode."""
        mode_lower = mode.lower()
        if "minimal" in mode_lower:
            return self.minimal
        if "standard" in mode_lower:
            return self.standard
        if "full" in mode_lower:
            return self.full
        return self.minimal


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in a string using tiktoken.
    Falls back to a simple word-based estimate if tiktoken is not available.
    """
    if not text:
        return 0

    if HAS_TIKTOKEN and tiktoken:
        try:
            # Map common names to tiktoken encodings
            model_lower = model.lower()
            if "claude" in model_lower:
                # Claude uses different tokens, but cl100k_base is common for modern models
                encoding_name = "cl100k_base"
            elif "gpt-4" in model_lower or "gpt-3.5" in model_lower:
                encoding_name = "cl100k_base"
            else:
                encoding_name = "cl100k_base"  # Safe default

            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Tiktoken error: {e}. Falling back to estimate.")

    # Fallback: ~4 characters per token as a rough estimate
    return len(text) // 4


def estimate_context_tokens(context: Any, model: str = "gpt-4") -> int:
    """
    Estimate total tokens in a TicketContext.

    Args:
        context: The TicketContext instance
        model: Model Name for encoding

    Returns:
        Total estimated tokens
    """
    total = 0

    # Handle both TicketContext and MultiTicketContext
    tickets = []
    if hasattr(context, "ticket") and context.ticket:
        tickets = [context.ticket]
    elif hasattr(context, "tickets") and context.tickets:
        tickets = context.tickets

    # Ticket info
    for t in tickets:
        total += count_tokens(t.title + (t.description or ""), model)

    # Conventions
    for conv in context.conventions:
        # Some conventions might be strings or objects, handle both
        content = conv.content if hasattr(conv, "content") else str(conv)
        total += count_tokens(content, model)

    # Patterns
    for pattern in context.patterns:
        total += count_tokens(pattern.description + (pattern.code_template or ""), model)

    # ADRs
    for adr in context.adrs:
        total += count_tokens(adr.context + adr.decision + adr.rationale, model)

    # Similar tickets (Only in Single TicketContext)
    similar_tickets = getattr(context, "similar_tickets", [])
    for ticket in similar_tickets:
        total += count_tokens(ticket.title + (ticket.description or ""), model)

    return total
