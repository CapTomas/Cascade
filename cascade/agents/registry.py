"""Agent registry and helpers."""

from typing import Optional, Type

from cascade.agents.interface import AgentInterface, AgentConfig
from cascade.agents.claude_code import ClaudeCodeAgent
from cascade.agents.codex import CodexAgent
from cascade.agents.generic import GenericAgent
from cascade.agents.antigravity import AntigravityAgent
from cascade.agents.manual import ManualAgent

AGENT_CLASSES: dict[str, Type[AgentInterface]] = {
    "claude-code": ClaudeCodeAgent,
    "codex": CodexAgent,
    "generic": GenericAgent,
    "antigravity": AntigravityAgent,
    "manual": ManualAgent,
}

# In-memory cache for agent instances
_AGENT_INSTANCES: dict[str, AgentInterface] = {}


def list_agents() -> list[str]:
    """List supported agent names."""
    return sorted(AGENT_CLASSES.keys())


def get_agent(name: str, config: Optional[AgentConfig] = None) -> AgentInterface:
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


def resolve_agent_name(ticket_type: str, agent_config: AgentConfig) -> str:
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
            return orch[type_key]

    return agent_config.default
