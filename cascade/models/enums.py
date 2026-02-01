"""Enumerations for Cascade domain models."""

from __future__ import annotations

from enum import Enum


class TicketType(str, Enum):
    """Types of tickets in the system."""

    EPIC = "EPIC"
    STORY = "STORY"
    TASK = "TASK"
    BUG = "BUG"
    SECURITY = "SECURITY"
    TEST = "TEST"
    DOC = "DOC"


class TicketStatus(str, Enum):
    """Status progression for tickets."""

    DEFINED = "DEFINED"  # Initial state, needs refinement
    READY = "READY"  # Ready for execution
    IN_PROGRESS = "IN_PROGRESS"  # Currently being worked on
    BLOCKED = "BLOCKED"  # Cannot proceed
    TESTING = "TESTING"  # Implementation complete, being tested
    DONE = "DONE"  # Completed and verified
    ABANDONED = "ABANDONED"  # Will not be completed


class Severity(str, Enum):
    """Severity levels for prioritization."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class KnowledgeStatus(str, Enum):
    """Approval status for knowledge items (ADRs, patterns)."""

    PROPOSED = "PROPOSED"  # AI-suggested, pending human review
    APPROVED = "APPROVED"  # Human-approved, used in context
    REJECTED = "REJECTED"  # Human-rejected, not used
    SUPERSEDED = "SUPERSEDED"  # Replaced by newer knowledge


class ContextMode(str, Enum):
    """Context loading modes for ticket execution."""

    MINIMAL = "minimal"  # Ticket + conventions only (~1500 tokens)
    STANDARD = "standard"  # + relevant patterns/ADRs (~4000 tokens)
    FULL = "full"  # + similar tickets, all context (~8000 tokens)


class IssueStatus(str, Enum):
    """Status for discovered issues."""

    OPEN = "OPEN"
    CONVERTED = "CONVERTED"  # Became a ticket
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class DependencyType(str, Enum):
    """Types of ticket dependencies."""

    BLOCKS = "blocks"  # Must complete before dependent
    RELATES_TO = "relates_to"  # Related but not blocking
