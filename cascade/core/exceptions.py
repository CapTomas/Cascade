"""Custom exceptions for the Cascade system."""

class CascadeError(Exception):
    """Base exception for all Cascade errors."""
    def __init__(self, message: str, details: str = None):
        super().__init__(message)
        self.message = message
        self.details = details


class AgentError(CascadeError):
    """Raised when an AI agent fails to execute a prompt."""
    pass


class AgentTimeoutError(AgentError):
    """Raised when an agent execution exceeds the timeout."""
    pass


class AgentAuthenticationError(AgentError):
    """Raised when agent credentials are invalid or missing."""
    pass


class TicketError(CascadeError):
    """Raised when there is an issue with ticket operations."""
    pass


class TicketBlockedError(TicketError):
    """Raised when attempting to execute a blocked ticket."""
    pass


class ContextError(CascadeError):
    """Raised when there are issues building or escalating context."""
    pass


class QualityGateError(CascadeError):
    """Raised when a mandatory quality gate fails."""
    pass


class ConfigurationError(CascadeError):
    """Raised when there is a project or system configuration error."""
    pass
