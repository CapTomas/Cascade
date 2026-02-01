"""Custom exceptions for Cascade."""

from __future__ import annotations


class CascadeError(Exception):
    """Base exception for all Cascade errors."""

    pass


class ConfigurationError(CascadeError):
    """Raised when there is an issue with configuration."""

    pass


class AgentError(CascadeError):
    """Raised when an agent execution fails."""

    pass


class TicketError(CascadeError):
    """Raised when there is an issue with ticket operations."""

    pass


class DatabaseError(CascadeError):
    """Raised when a database operation fails."""

    pass


class TokenLimitError(AgentError):
    """Raised when token limit is exceeded."""

    pass
