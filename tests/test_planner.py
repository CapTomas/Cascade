"""Tests for the Planner class."""

from unittest.mock import MagicMock

import pytest

from cascade.agents.interface import AgentResponse
from cascade.core.planner import Planner
from cascade.models.enums import Severity, TicketStatus, TicketType
from cascade.models.planning import PlanningResult, ProposedTicket, ProposedTopic


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.get_name.return_value = "mock-agent"
    return agent


@pytest.fixture
def mock_managers():
    tm = MagicMock()
    topic_m = MagicMock()
    kb = MagicMock()
    prompt_b = MagicMock()
    return tm, topic_m, kb, prompt_b


def test_planner_plan_success(mock_agent, mock_managers):
    tm, topic_m, kb, prompt_b = mock_managers
    planner = Planner(mock_agent, prompt_b, tm, topic_m, kb)

    requirements = "Build a task manager"
    prompt_b.build_planning_prompt.return_value = "planning prompt"

    mock_agent.execute.return_value = AgentResponse(
        success=True,
        content="""
```json
{
  "project_name": "Task Manager",
  "project_description": "A simple task manager",
  "tech_stack": ["Python", "FastAPI"],
  "topics": [{"name": "Auth", "description": "Authentication"}],
  "tickets": [
    {
      "title": "Setup API",
      "description": "Initialize FastAPI",
      "ticket_type": "EPIC",
      "severity": "HIGH",
      "acceptance_criteria": "FastAPI runs",
      "estimated_effort": 2,
      "topics": ["Auth"],
      "dependencies": [],
      "children": []
    }
  ],
  "suggested_adrs": []
}
```
""",
    )

    result = planner.plan(requirements)

    assert result.project_name == "Task Manager"
    assert len(result.tickets) == 1
    assert result.tickets[0].title == "Setup API"
    assert result.tickets[0].ticket_type == TicketType.EPIC


def test_planner_generate_tickets(mock_agent, mock_managers):
    tm, topic_m, kb, prompt_b = mock_managers
    planner = Planner(mock_agent, prompt_b, tm, topic_m, kb)

    result = PlanningResult(
        project_name="Test Project",
        project_description="Desc",
        tech_stack=["Python"],
        topics=[ProposedTopic(name="core", description="Core component")],
        tickets=[
            ProposedTicket(
                title="Grandparent",
                description="GP desc",
                ticket_type=TicketType.EPIC,
                topics=["core"],
                children=[
                    ProposedTicket(
                        title="Parent",
                        description="P desc",
                        ticket_type=TicketType.STORY,
                        children=[
                            ProposedTicket(
                                title="Child", description="C desc", ticket_type=TicketType.TASK
                            )
                        ],
                    )
                ],
            )
        ],
    )

    topic_m.create.return_value = MagicMock(id=1)
    tm.create.side_effect = [MagicMock(id=10), MagicMock(id=11), MagicMock(id=12)]

    planner.generate_tickets(result)

    assert topic_m.create.called
    assert tm.create.call_count == 3
    # Verify hierarchy
    tm.create.assert_any_call(
        ticket_type=TicketType.EPIC,
        title="Grandparent",
        description="GP desc",
        status=TicketStatus.DEFINED,
        severity=Severity.MEDIUM,
        parent_ticket_id=None,
        estimated_effort=None,
        acceptance_criteria="",
    )
    tm.create.assert_any_call(
        ticket_type=TicketType.STORY,
        title="Parent",
        description="P desc",
        status=TicketStatus.DEFINED,
        severity=Severity.MEDIUM,
        parent_ticket_id=10,
        estimated_effort=None,
        acceptance_criteria="",
    )


def test_planner_dependencies(mock_agent, mock_managers):
    tm, topic_m, kb, prompt_b = mock_managers
    planner = Planner(mock_agent, prompt_b, tm, topic_m, kb)

    result = PlanningResult(
        project_name="Test",
        project_description="Test",
        tickets=[
            ProposedTicket(title="Task A", description="A"),
            ProposedTicket(title="Task B", description="B", dependencies=["Task A"]),
        ],
    )

    tm.create.side_effect = [MagicMock(id=1), MagicMock(id=2)]

    planner.generate_tickets(result)

    tm.add_dependency.assert_called_with(2, 1)
