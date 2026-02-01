from unittest.mock import MagicMock

import pytest

from cascade.agents.interface import AgentResponse
from cascade.core.executor import TicketExecutor
from cascade.models.enums import TicketStatus
from cascade.models.ticket import Ticket


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.get_name.return_value = "test-agent"
    agent.execute.return_value = AgentResponse(
        success=True,
        content="Success\n<batch_summary>\n- TICKET #1: SUCCESS\n- TICKET #2: SUCCESS\n</batch_summary>",
        token_count=100,
    )
    return agent


@pytest.fixture
def mock_cb():
    cb = MagicMock()
    return cb


@pytest.fixture
def mock_pb():
    pb = MagicMock()
    pb.build_multi_execution_prompt.return_value = "Batch Prompt"
    return pb


@pytest.fixture
def mock_tm():
    tm = MagicMock()
    t1 = Ticket(id=1, title="T1", status=TicketStatus.READY)
    t2 = Ticket(id=2, title="T2", status=TicketStatus.READY)
    tm.get.side_effect = lambda tid: t1 if tid == 1 else t2 if tid == 2 else None
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


def test_execute_batch_success(executor, mock_agent, mock_tm, mock_qg):
    result = executor.execute_batch([1, 2])

    assert result.success
    assert result.affected_ticket_ids == [1, 2]
    assert mock_agent.execute.called
    assert mock_qg.run_all.call_count == 2
    mock_tm.update_status.assert_any_call(1, TicketStatus.DONE)
    mock_tm.update_status.assert_any_call(2, TicketStatus.DONE)


def test_execute_batch_blocked(executor, mock_tm):
    mock_tm.has_unmet_dependencies.side_effect = lambda tid: tid == 2
    mock_tm.get_blocking_tickets.return_value = [Ticket(id=3, title="Blocker")]

    result = executor.execute_batch([1, 2])

    assert not result.success
    assert "blocked" in result.error
    assert not executor.agent.execute.called


def test_estimate_context_tokens_multi():
    from cascade.models.context import MultiTicketContext
    from cascade.models.ticket import Ticket
    from cascade.utils.tokens import estimate_context_tokens

    t1 = Ticket(id=1, title="Title 1", description="Desc 1")
    t2 = Ticket(id=2, title="Title 2", description="Desc 2")
    context = MultiTicketContext(tickets=[t1, t2])

    tokens = estimate_context_tokens(context)
    assert tokens > 0
    # (Title 1 + Desc 1 + Title 2 + Desc 2) / 4 roughly
    # 7 + 6 + 7 + 6 = 26 chars / 4 = 6.5 -> 6 tokens
    assert tokens >= 6
