"""Agent implementations for Cascade."""

from cascade.agents.anthropic.claude_api import ClaudeApiAgent
from cascade.agents.anthropic.claude_cli import ClaudeCliAgent
from cascade.agents.generic import GenericAgent
from cascade.agents.google.gemini_api import GeminiApiAgent
from cascade.agents.google.gemini_cli import GeminiCliAgent
from cascade.agents.interface import (
    AgentCapabilities,
    AgentCapability,
    AgentConfig,
    AgentInterface,
    AgentResponse,
)
from cascade.agents.openai.codex_api import CodexApiAgent
from cascade.agents.openai.codex_cli import CodexCliAgent
from cascade.agents.registry import get_agent, list_agents

# Backward compatibility aliases
ClaudeCodeAgent = ClaudeCliAgent
CodexAgent = CodexApiAgent
AntigravityAgent = GeminiApiAgent

__all__ = [
    "AgentCapabilities",
    "AgentCapability",
    "AgentConfig",
    "AgentInterface",
    "AgentResponse",
    "ClaudeCliAgent",
    "ClaudeApiAgent",
    "CodexCliAgent",
    "CodexApiAgent",
    "GeminiCliAgent",
    "GeminiApiAgent",
    "ClaudeCodeAgent",
    "CodexAgent",
    "AntigravityAgent",
    "GenericAgent",
    "get_agent",
    "list_agents",
]
