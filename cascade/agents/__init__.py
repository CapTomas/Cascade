"""Agent implementations for Cascade."""

from cascade.agents.claude_code import ClaudeCodeAgent
from cascade.agents.codex import CodexAgent
from cascade.agents.generic import GenericAgent
from cascade.agents.interface import (
    AgentCapabilities,
    AgentCapability,
    AgentConfig,
    AgentInterface,
    AgentResponse,
)
from cascade.agents.registry import get_agent, list_agents

__all__ = [
    "AgentCapabilities",
    "AgentCapability",
    "AgentConfig",
    "AgentInterface",
    "AgentResponse",
    "ClaudeCodeAgent",
    "CodexAgent",
    "GenericAgent",
    "get_agent",
    "list_agents",
]
