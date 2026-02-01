from __future__ import annotations

from collections.abc import Callable

from cascade.agents.interface import (
    AgentCapabilities,
    AgentCapability,
    AgentConfig,
    AgentInterface,
    AgentResponse,
)
from cascade.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeApiAgent(AgentInterface):
    """
    Claude agent via Anthropic API.

    This agent uses the Anthropic Python SDK to interact indirectly with Claude models.
    """

    def __init__(self, config: AgentConfig | None = None):
        super().__init__(config)

    def get_name(self) -> str:
        return "claude-api"

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            capabilities={
                AgentCapability.CODE_ANALYSIS,
            },
            supports_streaming=True,
            supports_tools=False,  # Basic API implementation first
            max_output_tokens=4096,
        )

    def get_token_limit(self) -> int:
        return 200000

    def is_available(self) -> bool:
        # Check for API key in env or config
        return bool(self._get_api_key())

    def execute(
        self,
        prompt: str,
        working_dir: str | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        # Placeholder for actual API implementation
        return AgentResponse(
            success=False, content="Claude API not yet fully implemented", error="Not implemented"
        )

    def _get_api_key(self) -> str | None:
        import os

        return self.config.environment.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_API_KEY"
        )
