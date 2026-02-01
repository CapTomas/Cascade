import os
from unittest.mock import MagicMock, patch

from cascade.agents import AntigravityAgent
from cascade.agents.interface import AgentCapability
from cascade.agents.manual import ManualAgent
from cascade.agents.registry import get_agent, list_agents


def test_list_agents():
    agents = list_agents()
    assert "antigravity" in agents
    assert "claude-code" in agents
    assert "codex" in agents
    assert "generic" in agents
    assert "manual" in agents


@patch.dict(os.environ, {"ANTIGRAVITY_API_KEY": "test-key"})
def test_get_antigravity_agent():
    agent = get_agent("antigravity")
    assert isinstance(agent, AntigravityAgent)
    assert agent.get_name() == "gemini-api"
    assert agent.is_available() is True


def test_antigravity_capabilities():
    agent = get_agent("antigravity")
    caps = agent.get_capabilities()
    assert caps.has_capability(AgentCapability.FILE_EDIT)
    assert caps.has_capability(AgentCapability.COMMAND_EXECUTE)
    assert caps.has_capability(AgentCapability.WEB_SEARCH)
    assert caps.supports_streaming is True


@patch.dict(os.environ, {"ANTIGRAVITY_API_KEY": "test-key"})
@patch("urllib.request.urlopen")
def test_antigravity_execute(mock_urlopen):
    # Mock successful response
    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = (
        b'{"content": "Antigravity response", "usage": {"total_tokens": 100}}'
    )
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    agent = get_agent("antigravity")
    response = agent.execute("test prompt")

    assert response.success is True
    assert "Antigravity response" in response.content
    assert response.token_count == 100


def test_manual_agent_capabilities():
    agent = get_agent("manual")
    assert isinstance(agent, ManualAgent)
    caps = agent.get_capabilities()
    assert caps.has_capability(AgentCapability.FILE_EDIT)
    assert caps.supports_streaming is False


@patch("sys.stdin.readline")
@patch("subprocess.Popen")
def test_manual_agent_execute(mock_popen, mock_readline):
    # Mock clipboard success
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (None, None)
    mock_popen.return_value = mock_proc

    # Mock user input
    mock_readline.side_effect = ["User Response line 1\n", "User Response line 2\n", ""]

    agent = get_agent("manual")
    response = agent.execute("test prompt")

    assert response.success is True
    assert "User Response line 1" in response.content
    assert "User Response line 2" in response.content
    mock_popen.assert_called()


def test_prompt_builder():
    from cascade.core.prompt_builder import PromptBuilder
    from cascade.models.context import TicketContext
    from cascade.models.enums import TicketStatus, TicketType
    from cascade.models.ticket import Ticket

    ticket = Ticket(
        id=1,
        title="Test Ticket",
        description="Test Description",
        ticket_type=TicketType.TASK,
        status=TicketStatus.READY,
        acceptance_criteria="Test Criteria",
    )
    context = TicketContext(ticket=ticket)
    builder = PromptBuilder()
    prompt = builder.build_execution_prompt(context)

    assert "# Task" in prompt
    assert "Ticket #1: Test Ticket" in prompt
    assert "Test Description" in prompt
    assert "Test Criteria" in prompt
    assert "## Project Conventions" in prompt
