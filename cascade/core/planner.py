"""Planner for analyzing requirements and generating a project plan."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from cascade.agents.interface import AgentInterface
from cascade.core.knowledge_base import KnowledgeBase
from cascade.core.prompt_builder import PromptBuilder
from cascade.core.ticket_manager import TicketManager
from cascade.core.topic_manager import TopicManager
from cascade.models.enums import Severity, TicketStatus, TicketType
from cascade.models.planning import PlanningResult, ProposedTicket, ProposedTopic

logger = logging.getLogger(__name__)


class Planner:
    """
    Analyzes project requirements and generates a structured plan.

    Uses an AI agent to break down requirements into a hierarchy of
    tickets, topics, and initial ADRs.
    """

    def __init__(
        self,
        agent: AgentInterface,
        prompt_builder: PromptBuilder,
        ticket_manager: TicketManager,
        topic_manager: TopicManager,
        knowledge_base: KnowledgeBase,
    ):
        """
        Initialize the planner.

        Args:
            agent: The AI agent to use for analysis
            prompt_builder: Component to build planning prompts
            ticket_manager: Component to create tickets
            topic_manager: Component to create topics
            knowledge_base: Component to create initial ADRs
        """
        self.agent = agent
        self.prompt_builder = prompt_builder
        self.tm = ticket_manager
        self.topic_manager = topic_manager
        self.kb = knowledge_base

    def plan(self, requirements: str, max_retries: int = 2) -> PlanningResult:
        """
        Analyze requirements and return a proposed plan.

        Args:
            requirements: The project requirements text
            max_retries: Number of times to retry if agent returns invalid data

        Returns:
            PlanningResult containing the proposed breakdown
        """
        prompt = self.prompt_builder.build_planning_prompt(requirements)

        last_error = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"Retrying planning analysis (attempt {attempt}/{max_retries})")
                # Add a hint to the prompt about the previous failure if possible
                retry_prompt = (
                    prompt
                    + f"\n\nIMPORTANT: Your previous response was invalid. Error: {last_error}\nPlease ensure you return a valid JSON object strictly following the schema."
                )
            else:
                retry_prompt = prompt

            logger.info("Calling agent for requirements analysis")
            response = self.agent.execute(retry_prompt)

            if not response.success:
                last_error = response.error or "Agent execution failed"
                continue

            try:
                result = self._parse_response(response.content)
                self._validate_plan(result)
                return result
            except ValueError as e:
                last_error = str(e)
                logger.warning(f"Failed to parse or validate plan: {e}")
                continue

        raise ValueError(f"All planning attempts failed. Last error: {last_error}")

    def _validate_plan(self, result: PlanningResult) -> None:
        """Perform deep validation of the planning result."""
        if not result.project_name:
            raise ValueError("Project name is missing")
        if not result.tickets:
            raise ValueError("No tickets were generated")

        # Check for circular dependencies or missing references
        all_titles: set[str] = set()

        def collect_titles(tickets: list[ProposedTicket]) -> None:
            for t in tickets:
                all_titles.add(t.title)
                collect_titles(t.children)

        collect_titles(result.tickets)

        def check_deps(tickets: list[ProposedTicket]) -> None:
            for t in tickets:
                for dep in t.dependencies:
                    if dep not in all_titles:
                        logger.warning(f"Ticket '{t.title}' depends on unknown ticket '{dep}'")
                check_deps(t.children)

        check_deps(result.tickets)

    def generate_tickets(self, result: PlanningResult) -> None:
        """
        Convert a planning result into database entities.

        Args:
            result: The proposed plan to implement
        """
        # 1. Create topics
        topic_map: dict[str, int | None] = {}
        for prop_topic in result.topics:
            topic = self.topic_manager.create(
                name=prop_topic.name, description=prop_topic.description
            )
            topic_map[prop_topic.name] = topic.id

        # 2. Create tickets (recursively)
        created_tickets: dict[str, int | None] = {}  # title -> id

        def create_recursive(prop_ticket: ProposedTicket, parent_id: int | None = None) -> None:
            # Determine initial status: READY if no dependencies and no children, else DEFINED
            initial_status = TicketStatus.READY
            if prop_ticket.dependencies or prop_ticket.children:
                initial_status = TicketStatus.DEFINED

            ticket = self.tm.create(
                ticket_type=prop_ticket.ticket_type,
                title=prop_ticket.title,
                description=prop_ticket.description,
                status=initial_status,
                severity=prop_ticket.severity,
                parent_ticket_id=parent_id,
                estimated_effort=prop_ticket.estimated_effort,
                acceptance_criteria=prop_ticket.acceptance_criteria,
            )
            created_tickets[prop_ticket.title] = ticket.id

            # Assign topics
            for t_name in prop_ticket.topics:
                if t_name in topic_map:
                    topic_id = topic_map[t_name]
                    assert topic_id is not None
                    assert ticket.id is not None
                    self.topic_manager.assign_ticket(topic_id, ticket.id)

            # Recurse children
            for child in prop_ticket.children:
                create_recursive(child, ticket.id)

        for top_ticket in result.tickets:
            create_recursive(top_ticket)

        # 3. Handle dependencies
        # This is a bit tricky since we need to match by title
        def process_dependencies(prop_ticket: ProposedTicket) -> None:
            current_id = created_tickets.get(prop_ticket.title)
            if current_id:
                for dep_title in prop_ticket.dependencies:
                    dep_id = created_tickets.get(dep_title)
                    if dep_id:
                        self.tm.add_dependency(current_id, dep_id)

            for child in prop_ticket.children:
                process_dependencies(child)

        for top_ticket in result.tickets:
            process_dependencies(top_ticket)

        # 4. Create initial ADRs
        for adr in result.suggested_adrs:
            self.kb.propose_adr(
                title=adr.get("title", ""),
                context=adr.get("context", ""),
                decision=adr.get("decision", ""),
                rationale=adr.get("rationale", ""),
                consequences=adr.get("consequences", ""),
                alternatives_considered=adr.get("alternatives", ""),
            )

    def _parse_response(self, content: str) -> PlanningResult:
        """
        Parse JSON response from agent with enhanced robustness.

        Args:
            content: Raw response from agent

        Returns:
            PlanningResult object
        """
        # Find JSON block
        json_str = content
        match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            # Fallback for agents that don't use fences but return JSON
            # Find the first { and last }
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                json_str = content[start : end + 1].strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse agent JSON: {e}")
            logger.debug(f"Raw content: {content}")
            raise ValueError(
                "Agent response was not valid JSON. Please try again or refine requirements."
            ) from e

        # Basic validation
        if "tickets" not in data or not isinstance(data["tickets"], list):
            raise ValueError("Agent result missing 'tickets' list")

        return PlanningResult(
            project_name=data.get("project_name", "New Project"),
            project_description=data.get("project_description", ""),
            tech_stack=data.get("tech_stack", []),
            topics=[ProposedTopic(**t) for t in data.get("topics", [])],
            tickets=self._parse_tickets(data.get("tickets", [])),
            suggested_adrs=data.get("suggested_adrs", []),
        )

    def _parse_tickets(self, tickets_data: list[dict[str, Any]]) -> list[ProposedTicket]:
        """Recursively parse tickets from JSON data."""
        tickets = []
        for t_data in tickets_data:
            children_data = t_data.pop("children", [])

            # Convert string enums
            if "ticket_type" in t_data:
                t_data["ticket_type"] = TicketType(t_data["ticket_type"])
            if "severity" in t_data:
                t_data["severity"] = Severity(t_data["severity"])

            ticket = ProposedTicket(**t_data)
            ticket.children = self._parse_tickets(children_data)
            tickets.append(ticket)
        return tickets
