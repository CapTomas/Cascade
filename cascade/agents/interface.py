"""Interfaces and base classes for AI agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class AgentCapability(str, Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    COMMAND_EXECUTE = "command_execute"
    WEB_SEARCH = "web_search"
    CODE_ANALYSIS = "code_analysis"


@dataclass
class AgentCapabilities:
    """Describes what an agent can do."""

    capabilities: set[AgentCapability] = field(default_factory=set)
    supports_streaming: bool = False
    supports_tools: bool = False
    max_output_tokens: int = 4096

    @property
    def can_edit_files(self) -> bool:
        """Check if agent can edit files."""
        return AgentCapability.FILE_EDIT in self.capabilities

    @property
    def can_execute_commands(self) -> bool:
        """Check if agent can run shell commands."""
        return AgentCapability.COMMAND_EXECUTE in self.capabilities

    def has_capability(self, cap: AgentCapability) -> bool:
        """Check if agent has a specific capability."""
        return cap in self.capabilities


@dataclass
class AgentResponse:
    """Response from an agent execution."""

    success: bool
    content: str
    error: str | None = None
    files_modified: list[str] = field(default_factory=list)
    commands_executed: list[str] = field(default_factory=list)
    token_count: int = 0
    execution_time_ms: int = 0
    raw_output: str | None = None

    @property
    def has_error(self) -> bool:
        """Check if response contains an error."""
        return not self.success or self.error is not None


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""

    name: str
    timeout_seconds: int = 300
    max_retries: int = 3
    environment: dict[str, str] = field(default_factory=dict)
    extra_args: list[str] = field(default_factory=list)
    command: str | None = None
    orchestration: dict[str, str] = field(default_factory=dict)


class AgentInterface(ABC):
    """
    Abstract interface for AI agents.

    Implement this for each supported agent (Claude Code, Codex, etc.).
    This allows Cascade to work with any AI coding agent through a
    common interface.
    """

    def __init__(self, config: AgentConfig | None = None):
        """
        Initialize agent with optional configuration.

        Args:
            config: Agent-specific configuration
        """
        self.config = config or AgentConfig(name=self.get_name())

    @abstractmethod
    def get_name(self) -> str:
        """
        Return the agent's identifier name.

        Returns:
            Agent name (e.g., 'claude-code', 'codex', 'generic')
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """
        Return what this agent can do.

        Returns:
            AgentCapabilities describing supported features
        """
        pass

    @abstractmethod
    def get_token_limit(self) -> int:
        """
        Return agent's context window size.

        Returns:
            Maximum tokens the agent can handle
        """
        pass

    @abstractmethod
    def execute(
        self,
        prompt: str,
        working_dir: str | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        """
        Execute a prompt and return the response.

        This is the main execution method. The agent should:
        1. Process the prompt
        2. Perform any requested actions (file edits, commands)
        3. Return a structured response

        Args:
            prompt: The prompt to execute
            working_dir: Working directory for file operations
            callback: Optional callback for streaming partial results

        Returns:
            AgentResponse with results
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the agent is available and properly configured.

        Returns:
            True if agent can be used
        """
        pass

    def validate_prompt(self, prompt: str) -> tuple[bool, str | None]:
        """
        Validate a prompt before execution.

        Override to add agent-specific validation.

        Args:
            prompt: The prompt to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not prompt or not prompt.strip():
            return False, "Prompt cannot be empty"

        token_estimate = len(prompt) // 4
        if token_estimate > self.get_token_limit() * 0.3:
            return False, f"Prompt too long (estimated {token_estimate} tokens)"

        return True, None

    def _validate_working_dir(self, working_dir: str | None) -> tuple[bool, str | None]:
        """
        Ensure working_dir is safe (within project boundaries).

        Args:
            working_dir: The directory to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not working_dir:
            return True, None

        from pathlib import Path

        try:
            target = Path(working_dir).resolve()
            project_root = Path.cwd().resolve()

            if not str(target).startswith(str(project_root)):
                return (
                    False,
                    f"Security violation: working directory '{working_dir}' is outside project root",
                )

            return True, None
        except Exception as e:
            return False, f"Failed to validate working directory: {e}"

    def _get_environment(self) -> dict[str, str]:
        """
        Get environment variables for subprocess execution.

        Merges system environment with overrides from config.
        """
        import os

        env = os.environ.copy()
        if self.config.environment:
            env.update(self.config.environment)
        return env

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.get_name()})"
