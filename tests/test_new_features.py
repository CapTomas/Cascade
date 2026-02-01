"""Tests for new features: Metrics, Git, Orchestration."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from cascade.agents.registry import resolve_agent_name
from cascade.core.metrics import MetricsService
from cascade.utils.git import GitProvider

# --- Metrics Tests ---


def test_metrics_aggregation():
    """Test aggregation of execution logic."""
    mock_db = MagicMock()
    mock_db.fetch_all.return_value = [
        {
            "agent": "claude",
            "context_mode": "minimal",
            "token_count": 100,
            "execution_time_ms": 1000,
        },
        {"agent": "claude", "context_mode": "full", "token_count": 200, "execution_time_ms": 2000},
    ]

    service = MetricsService(mock_db)
    metrics = service.get_execution_metrics()

    assert metrics.total_executions == 2
    assert metrics.total_tokens == 300
    assert metrics.total_time_ms == 3000
    assert metrics.by_agent["claude"] == 2
    assert metrics.by_context_mode["minimal"] == 1
    assert metrics.by_context_mode["full"] == 1


# --- Git Tests ---


@patch("subprocess.run")
def test_git_provider_create_branch(mock_run):
    """Test git branch creation."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    provider = GitProvider()
    result = provider.create_branch("feature/test")

    assert result.success
    # Expect sanitized name
    args = mock_run.call_args[0][0]
    assert args[1:] == ["checkout", "-b", "feature-test"]


@patch("subprocess.run")
def test_git_provider_commit(mock_run):
    """Test git commit."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    provider = GitProvider()
    result = provider.commit("Initial commit", add_all=True)

    assert result.success
    # Verify two calls: add and commit
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0][0][0][1:] == ["add", "-A"]
    assert mock_run.call_args_list[1][0][0][1:] == ["commit", "-m", "Initial commit"]


# --- Orchestration Tests ---


@dataclass
class MockAgentConfig:
    default: str
    orchestration: dict


def test_resolve_agent_name():
    """Test agent name resolution."""
    # Use a mock config similar to ProjectConfig's AgentConfig
    config = MockAgentConfig(
        default="default-agent", orchestration={"docs": "doc-agent", "bug": "bug-agent"}
    )

    # Matching type
    assert resolve_agent_name("DOCS", config) == "doc-agent"
    assert resolve_agent_name("bug", config) == "bug-agent"

    # Non-matching type
    assert resolve_agent_name("story", config) == "default-agent"

    # Empty config
    empty_config = MockAgentConfig(default="default-agent", orchestration={})
    assert resolve_agent_name("docs", empty_config) == "default-agent"
