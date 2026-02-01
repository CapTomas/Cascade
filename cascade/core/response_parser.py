"""Parser for structured AI responses."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExecutionSummary:
    """Structured execution summary from AI response."""

    ticket_id: int
    status: str  # COMPLETE, BLOCKED, NEEDS_BREAKDOWN, etc.
    summary: dict[str, str]  # Key-value pairs from the summary
    blockers: list[str] | None = None
    suggested_tickets: list[str] | None = None
    raw_summary: str = ""


def parse_execution_summary(response: str, ticket_id: int) -> ExecutionSummary | None:
    """
    Parse execution summary from AI response.

    Looks for <execution_summary> tags and extracts structured information.

    Args:
        response: The AI's response text
        ticket_id: The ticket ID being executed

    Returns:
        ExecutionSummary if found, None otherwise
    """
    # Find execution summary block
    match = re.search(
        r"<execution_summary>(.*?)</execution_summary>", response, re.DOTALL | re.IGNORECASE
    )

    if not match:
        logger.warning(f"No execution summary found for ticket #{ticket_id}")
        return None

    raw_summary = match.group(1).strip()
    summary_dict: dict[str, str] = {}
    status = "UNKNOWN"
    blockers = None
    suggested_tickets = None

    # Parse key-value pairs
    for line in raw_summary.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Match KEY: Value format
        kv_match = re.match(r"^([A-Z_]+):\s*(.+)$", line)
        if kv_match:
            key = kv_match.group(1).strip()
            value = kv_match.group(2).strip()
            summary_dict[key] = value

            # Extract specific fields
            if key == "TICKET_STATUS":
                status = value.upper()
            elif key == "BLOCKERS":
                blockers = [b.strip() for b in value.split(",") if b.strip()]
            elif key in ("SUGGESTED_TICKETS", "NEW_TICKETS_NEEDED"):
                suggested_tickets = [t.strip() for t in value.split(",") if t.strip()]

    return ExecutionSummary(
        ticket_id=ticket_id,
        status=status,
        summary=summary_dict,
        blockers=blockers,
        suggested_tickets=suggested_tickets,
        raw_summary=raw_summary,
    )


def parse_batch_summary(response: str) -> dict[int, str]:
    """
    Parse batch execution summary.

    Returns:
        Dict mapping ticket_id to status (COMPLETE/BLOCKED/SUCCESS/FAILED)
    """
    match = re.search(r"<batch_summary>(.*?)</batch_summary>", response, re.DOTALL | re.IGNORECASE)

    if not match:
        return {}

    summary_text = match.group(1).strip()
    results = {}

    # Parse each line: "TICKET #ID: STATUS - explanation"
    for line in summary_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Match patterns like:
        # - TICKET #123: COMPLETE - explanation
        # - TICKET #123: [COMPLETE] - explanation
        ticket_match = re.search(
            r"TICKET\s*#(\d+):\s*\[?(\w+)\]?", line, re.IGNORECASE
        )
        if ticket_match:
            ticket_id = int(ticket_match.group(1))
            status = ticket_match.group(2).upper()
            # Normalize status
            if status in ("SUCCESS", "COMPLETE", "DONE"):
                status = "COMPLETE"
            elif status in ("FAILED", "BLOCKED", "ERROR"):
                status = "BLOCKED"
            results[ticket_id] = status

    return results


def extract_ticket_status(summary: ExecutionSummary) -> str:
    """
    Extract normalized ticket status from execution summary.

    Returns:
        One of: COMPLETE, BLOCKED, NEEDS_BREAKDOWN, UNKNOWN
    """
    status = summary.status.upper()

    if status in ("COMPLETE", "DONE", "SUCCESS"):
        return "COMPLETE"
    elif status in ("BLOCKED", "FAILED", "ERROR"):
        return "BLOCKED"
    elif status in ("NEEDS_BREAKDOWN", "TOO_LARGE"):
        return "NEEDS_BREAKDOWN"
    else:
        return "UNKNOWN"
