from unittest.mock import MagicMock

import pytest

from cascade.core.context_builder import ContextBuilder
from cascade.models.enums import ContextMode, TicketStatus, TicketType
from cascade.models.ticket import Ticket


@pytest.fixture
def mock_kb():
    kb = MagicMock()
    kb.get_conventions.return_value = ["Conv 1", "Conv 2"]
    kb.get_relevant_patterns.return_value = ["Pattern 1"]
    kb.get_relevant_adrs.return_value = ["ADR 1"]
    return kb


@pytest.fixture
def mock_tm():
    tm = MagicMock()
    tm.get_similar_completed_tickets.return_value = ["Similar 1"]
    return tm


@pytest.fixture
def test_ticket():
    return Ticket(
        id=1,
        title="Test Ticket",
        description="Test Description",
        ticket_type=TicketType.TASK,
        status=TicketStatus.READY,
    )


def test_build_minimal_context(mock_kb, mock_tm, test_ticket):
    builder = ContextBuilder(mock_kb, mock_tm)
    context = builder.build_context(test_ticket, ContextMode.MINIMAL)

    assert context.mode == ContextMode.MINIMAL
    assert context.conventions == ["Conv 1", "Conv 2"]
    assert len(context.patterns) == 0
    assert len(context.adrs) == 0
    assert len(context.similar_tickets) == 0
    mock_kb.get_conventions.assert_called_once()


def test_build_standard_context(mock_kb, mock_tm, test_ticket):
    builder = ContextBuilder(mock_kb, mock_tm)
    context = builder.build_context(test_ticket, ContextMode.STANDARD)

    assert context.mode == ContextMode.STANDARD
    assert len(context.patterns) == 1
    assert len(context.adrs) == 1
    assert len(context.similar_tickets) == 0
    mock_kb.get_relevant_patterns.assert_called_with(test_ticket, limit=3)


def test_build_full_context(mock_kb, mock_tm, test_ticket):
    builder = ContextBuilder(mock_kb, mock_tm)
    context = builder.build_context(test_ticket, ContextMode.FULL)

    assert context.mode == ContextMode.FULL
    assert len(context.patterns) == 1
    assert len(context.adrs) == 1
    assert len(context.similar_tickets) == 1
    mock_tm.get_similar_completed_tickets.assert_called_with(test_ticket, limit=3)
