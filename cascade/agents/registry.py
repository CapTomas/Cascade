"""Agent registry and helpers."""

from __future__ import annotations

from typing import Any, cast

from cascade.agents.anthropic.claude_api import ClaudeApiAgent
from cascade.agents.anthropic.claude_cli import ClaudeCliAgent
from cascade.agents.generic import GenericAgent
from cascade.agents.google.gemini_api import GeminiApiAgent
from cascade.agents.google.gemini_cli import GeminiCliAgent
from cascade.agents.interface import AgentConfig, AgentInterface
from cascade.agents.manual import ManualAgent
from cascade.agents.openai.codex_api import CodexApiAgent
from cascade.agents.openai.codex_cli import CodexCliAgent

AGENT_CLASSES: dict[str, type[AgentInterface]] = {
    "claude-cli": ClaudeCliAgent,
    "claude-api": ClaudeApiAgent,
    "codex-cli": CodexCliAgent,
    "codex-api": CodexApiAgent,
    "gemini-cli": GeminiCliAgent,
    "gemini-api": GeminiApiAgent,
    "generic": GenericAgent,
    "manual": ManualAgent,
    # Aliases
    "claude": ClaudeCliAgent,
    "claude-code": ClaudeCliAgent,
    "codex": CodexApiAgent,
    "antigravity": GeminiApiAgent,
    "gemini": GeminiCliAgent,
}

AGENT_METADATA: dict[str, dict[str, str]] = {
    "claude-cli": {
        "title": "Claude Code (CLI)",
        "description": "Mature agent with streaming and tool support via 'claude' CLI.",
        "provider": "Anthropic",
    },
    "claude-api": {
        "title": "Claude (API)",
        "description": "Direct integration with Anthropic's Claude API.",
        "provider": "Anthropic",
    },
    "gemini-cli": {
        "title": "Gemini (CLI)",
        "description": "Google's Gemini models via 'gemini' CLI tool.",
        "provider": "Google",
    },
    "gemini-api": {
        "title": "Gemini (API)",
        "description": "Direct integration with Google Gemini Pro API.",
        "provider": "Google",
    },
    "codex-cli": {
        "title": "Codex (CLI)",
        "description": "OpenAI Codex/GPT models via 'codex' CLI tool.",
        "provider": "OpenAI",
    },
    "codex-api": {
        "title": "Codex (API)",
        "description": "Direct integration with OpenAI API.",
        "provider": "OpenAI",
    },
    "generic": {
        "title": "Generic Agent",
        "description": "Basic agent for simple text generation tasks.",
        "provider": "Internal",
    },
    "manual": {
        "title": "Manual / Human",
        "description": "Ask a human for input when AI isn't enough.",
        "provider": "User",
    },
}

# In-memory cache for agent instances
_AGENT_INSTANCES: dict[str, AgentInterface] = {}


def list_agents() -> list[str]:
    """List supported agent names."""
    return sorted(AGENT_CLASSES.keys())


def get_agent(name: str, config: AgentConfig | None = None) -> AgentInterface:
    """
    Instantiate an agent by name or return cached instance.

    If config is provided, a new instance is always created to ensure
    fresh configuration is applied. Otherwise, instances are cached.
    """
    if name not in AGENT_CLASSES:
        raise KeyError(f"Unknown agent: {name}")

    if config is not None:
        # Configuration change requires a new instance
        return AGENT_CLASSES[name](config)

    if name not in _AGENT_INSTANCES:
        _AGENT_INSTANCES[name] = AGENT_CLASSES[name]()

    return _AGENT_INSTANCES[name]


def resolve_agent_name(ticket_type: str, agent_config: Any) -> str:
    """
    Resolve agent name based on ticket type and configuration.

    Args:
        ticket_type: The type of ticket (docs, story, etc.)
        agent_config: The agent configuration containing orchestration rules

    Returns:
        The name of the agent to use
    """
    if ticket_type and hasattr(agent_config, "orchestration") and agent_config.orchestration:
        # Case insensitive match to be safe
        orch = {k.lower(): v for k, v in agent_config.orchestration.items()}
        type_key = ticket_type.lower()
        if type_key in orch:
            return cast(str, orch[type_key])

    return cast(str, agent_config.default)


def get_agent_class_for_provider(provider: str, mode: str) -> type[AgentInterface]:
    """Get agent class for a specific provider and mode."""
    key = f"{provider}-{mode}"
    if key in AGENT_CLASSES:
        return AGENT_CLASSES[key]
    raise KeyError(f"Unknown provider/mode combination: {provider}/{mode}")
