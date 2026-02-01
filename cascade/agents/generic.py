"""Generic agent implementation via stdin/stdout."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from collections.abc import Callable

from cascade.agents.interface import (
    AgentCapabilities,
    AgentCapability,
    AgentConfig,
    AgentInterface,
    AgentResponse,
)

logger = logging.getLogger(__name__)


class GenericAgent(AgentInterface):
    """
    Generic agent adapter using an external command.

    The command is executed with the prompt passed to stdin and the
    response read from stdout. This enables integration with any
    custom agent that supports stdin/stdout interaction.
    """

    DEFAULT_TOKEN_LIMIT = 32768
    ENV_COMMAND = "CASCADE_GENERIC_AGENT_CMD"

    def __init__(self, config: AgentConfig | None = None):
        super().__init__(config)

    def get_name(self) -> str:
        return "generic"

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            capabilities={
                AgentCapability.CODE_ANALYSIS,
            },
            supports_streaming=False,
            supports_tools=False,
            max_output_tokens=4096,
        )

    def get_token_limit(self) -> int:
        return self.DEFAULT_TOKEN_LIMIT

    def is_available(self) -> bool:
        return self._get_command() is not None

    def execute(
        self,
        prompt: str,
        working_dir: str | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        is_valid, error = self.validate_prompt(prompt)
        if not is_valid:
            return AgentResponse(success=False, content="", error=error)

        # Validate working directory
        is_safe, error = self._validate_working_dir(working_dir)
        if not is_safe:
            return AgentResponse(success=False, content="", error=error)

        command = self._get_command()
        if not command:
            return AgentResponse(
                success=False,
                content="",
                error=f"Generic agent command not configured (set {self.ENV_COMMAND})",
            )

        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                cwd=working_dir,
                timeout=self.config.timeout_seconds,
                env=self._get_environment(),
            )
        except subprocess.TimeoutExpired:
            return AgentResponse(
                success=False,
                content="",
                error=f"Execution timed out after {self.config.timeout_seconds} seconds",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as exc:
            logger.exception("Unexpected error executing generic agent")
            return AgentResponse(
                success=False,
                content="",
                error=f"Unexpected error: {exc}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        execution_time = int((time.time() - start_time) * 1000)

        if result.returncode != 0:
            return AgentResponse(
                success=False,
                content=result.stdout or "",
                error=result.stderr or f"Exit code: {result.returncode}",
                execution_time_ms=execution_time,
                raw_output=(result.stdout or "") + (result.stderr or ""),
            )

        return AgentResponse(
            success=True,
            content=result.stdout or "",
            execution_time_ms=execution_time,
            raw_output=result.stdout or "",
        )

    def _get_command(self) -> list[str] | None:
        command = self.config.command or os.environ.get(self.ENV_COMMAND)
        if not command:
            return None
        return shlex.split(command) + self.config.extra_args
