from unittest.mock import MagicMock

import pytest

from cascade.agents.interface import AgentResponse
from cascade.core.executor import TicketExecutor
from cascade.models.enums import ContextMode, TicketStatus, TicketType
from cascade.models.ticket import Ticket


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.get_name.return_value = "test-agent"
    agent.execute.return_value = AgentResponse(success=True, content="Success", token_count=100)
    return agent


@pytest.fixture
def mock_cb():
    cb = MagicMock()
    return cb


@pytest.fixture
def mock_pb():
    pb = MagicMock()
    pb.build_execution_prompt.return_value = "Test Prompt"
    return pb


@pytest.fixture
def mock_tm():
    tm = MagicMock()
    tm.get.return_value = Ticket(
        id=1,
        title="Test Ticket",
        description="Test Desc",
        ticket_type=TicketType.TASK,
        status=TicketStatus.READY,
    )
    tm.has_unmet_dependencies.return_value = False
    return tm


@pytest.fixture
def mock_qg():
    qg = MagicMock()
    qg.run_all.return_value = MagicMock(all_passed=True)
    return qg


@pytest.fixture
def mock_kb():
    return MagicMock()


@pytest.fixture
def executor(mock_agent, mock_cb, mock_pb, mock_tm, mock_qg, mock_kb):
    return TicketExecutor(mock_agent, mock_cb, mock_pb, mock_tm, mock_qg, mock_kb)


def test_execute_success_minimal(executor, mock_agent, mock_tm, mock_qg):
    result = executor.execute(1)

    assert result.success
    assert result.context_mode == ContextMode.MINIMAL
    assert mock_agent.execute.called
    assert mock_qg.run_all.called
    mock_tm.update_status.assert_any_call(1, TicketStatus.IN_PROGRESS)
    mock_tm.update_status.assert_any_call(1, TicketStatus.DONE)


def test_execute_blocked(executor, mock_tm):
    mock_tm.has_unmet_dependencies.return_value = True
    mock_tm.get_blocking_tickets.return_value = [
        Ticket(id=2, title="Blocker", ticket_type=TicketType.TASK, status=TicketStatus.READY)
    ]

    result = executor.execute(1)

    assert not result.success
    assert "blocked" in result.error
    assert not executor.agent.execute.called


def test_execute_escalation_on_gate_failure(executor, mock_agent, mock_tm, mock_qg):
    # Agent succeeds, but gate fails first time, succeeds second time
    mock_agent.execute.return_value = AgentResponse(
        success=True, content="Success", token_count=100
    )
    mock_qg.run_all.side_effect = [
        MagicMock(
            all_passed=False, results=[MagicMock(gate_name="Test", passed=False, output="Failed")]
        ),
        MagicMock(
            all_passed=True, results=[MagicMock(gate_name="Test", passed=True, output="Passed")]
        ),
    ]

    result = executor.execute(1)

    assert result.success
    assert result.context_mode == ContextMode.STANDARD
    assert mock_agent.execute.call_count == 2
    assert mock_qg.run_all.call_count == 2


def test_execute_escalation_on_agent_failure(executor, mock_agent, mock_tm, mock_qg):
    # Make first two attempts fail (agent), third succeed
    mock_agent.execute.side_effect = [
        AgentResponse(success=False, content="", error="Fail 1"),
        AgentResponse(success=False, content="", error="Fail 2"),
        AgentResponse(success=True, content="Success", token_count=100),
    ]

    result = executor.execute(1)

    assert result.success
    assert result.context_mode == ContextMode.FULL
    assert mock_agent.execute.call_count == 3
    assert mock_qg.run_all.call_count == 1  # Only called on success


def test_execute_all_fail(executor, mock_agent):
    mock_agent.execute.return_value = AgentResponse(
        success=False, content="", error="Permanent Fail"
    )

    result = executor.execute(1)

    assert not result.success
    assert result.context_mode == ContextMode.FULL
    assert mock_agent.execute.call_count == 3
    assert "exhausted" in result.error


def test_execute_cancelled_by_user(executor, mock_agent):
    confirm_callback = MagicMock(return_value=False)

    result = executor.execute(1, confirm_callback=confirm_callback)

    assert not result.success
    assert "cancelled" in result.error
    assert not mock_agent.execute.called


def test_execute_with_knowledge_extraction(executor, mock_agent, mock_kb):
    mock_agent.execute.return_value = AgentResponse(
        success=True,
        content="Implemented it.\n<knowledge_proposal>\ntype: PATTERN\nname: P1\ndescription: D1\n</knowledge_proposal>",
        token_count=100,
    )

    result = executor.execute(1)

    assert result.success
    assert len(result.proposals) == 1
    assert result.proposals[0]["pattern_name"] == "P1"
    assert mock_kb.propose_pattern.called
