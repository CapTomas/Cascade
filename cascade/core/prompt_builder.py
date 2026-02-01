"""Prompt builder for ticket execution."""

from __future__ import annotations

import logging

from cascade.models.context import MultiTicketContext, TicketContext
from cascade.models.ticket import Ticket

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds execution prompts for AI agents.

    Assembles ticket details, project conventions, and relevant
    knowledge into a structured prompt for the AI agent.
    """

    def _sanitize(self, text: str) -> str:
        """
        Sanitize text to prevent prompt injection.
        Escapes markdown headers and markers that could confuse the agent.
        """
        if not text:
            return ""

        # Simple escaping: prefix common prompt markers if they are at the start of lines
        lines = []
        for line in text.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                # Escape markdown headers
                line = "\\" + line
            elif stripped.startswith(("Instructions", "Instructions:", "###", "##", "#")):
                line = " - " + line
            lines.append(line)

        return "\n".join(lines)

    def build_execution_prompt(self, context: TicketContext) -> str:
        """
        Build a prompt for executing a single ticket.

        Args:
            context: The assembled TicketContext

        Returns:
            The formatted prompt string
        """
        ticket = context.ticket
        title = self._sanitize(ticket.title)
        description = self._sanitize(ticket.description)
        ac = self._sanitize(ticket.acceptance_criteria)

        prompt = [
            "# Task",
            "Complete the following ticket. Focus only on this ticket.",
            "",
            f"## Ticket #{ticket.id}: {title}",
            f"Type: {ticket.ticket_type.value}",
            f"Priority: {ticket.severity.value if ticket.severity else 'MEDIUM'}",
            "",
            "### Description",
            f"{description}",
            "",
            "### Acceptance Criteria",
            f"{ac or 'None specified'}",
            "",
        ]

        if ticket.affected_files:
            prompt.append("### Affected Files")
            for file_path in ticket.affected_files:
                prompt.append(f"- {file_path}")
            prompt.append("")

        prompt.append("## Project Conventions")
        prompt.append(context.conventions_text)
        prompt.append("")

        if context.patterns:
            prompt.append("## Relevant Patterns")
            prompt.append(context.patterns_text)
            prompt.append("")

        if context.adrs:
            prompt.append("## Architecture Decision Records (ADRs)")
            prompt.append(context.adrs_text)
            prompt.append("")

        if context.similar_tickets:
            prompt.append("## Similar Completed Tickets")
            for t in context.similar_tickets:
                prompt.append(f"### Ticket #{t.id}: {t.title}")
                prompt.append(f"{t.description}")
                prompt.append("")

        prompt.extend(
            [
                "## Instructions",
                "1. **Implement exactly** what the ticket describes. Do not over-engineer.",
                "2. **Strictly follow** the project conventions provided above.",
                "3. **Test-Driven Development**: If you are adding new functionality, ensure corresponding unit tests are created or updated.",
                "4. **Isolation**: Do not modify unrelated code. If you discover a bug elsewhere, note it but do not fix it unless it blocks this ticket.",
                "5. **Clean Code**: Ensure your code is professional, documented, and follows the tech stack best practices.",
                "6. **Summary**: Provide a concise summary of your changes (files changed, main logic) after implementation.",
                "7. **Propose Knowledge**: If you identify a reusable pattern or a significant architectural decision, propose it using the following format at the end of your response:",
                "",
                "<knowledge_proposal>",
                "---",
                "type: PATTERN",
                "name: Pattern Name",
                "description: What it does",
                "template: |",
                "  Code template here",
                "tags: [tag1, tag2]",
                "examples: [file1.py]",
                "---",
                "type: ADR",
                "title: Decision Title",
                "context: Why now?",
                "decision: What decided?",
                "rationale: Why this?",
                "consequences: What next?",
                "alternatives: What else?",
                "</knowledge_proposal>",
            ]
        )

        return "\n".join(prompt)

    def build_multi_execution_prompt(self, context: MultiTicketContext) -> str:
        """
        Build a prompt for executing multiple tickets together.

        Args:
            context: The assembled MultiTicketContext

        Returns:
            The formatted prompt string
        """
        prompt = [
            "# Task: Batch Execution",
            "Complete the following set of related tickets in a single pass.",
            "Ensure consistency across all changes.",
            "",
        ]

        for ticket in context.tickets:
            title = self._sanitize(ticket.title)
            description = self._sanitize(ticket.description)
            ac = self._sanitize(ticket.acceptance_criteria)

            prompt.extend(
                [
                    f"## Ticket #{ticket.id}: {title}",
                    f"Type: {ticket.ticket_type.value}",
                    f"Priority: {ticket.severity.value if ticket.severity else 'MEDIUM'}",
                    "",
                    "### Description",
                    f"{description}",
                    "",
                    "### Acceptance Criteria",
                    f"{ac or 'None specified'}",
                    "",
                ]
            )

        prompt.append("## Project Conventions")
        prompt.append(context.conventions_text)
        prompt.append("")

        if context.patterns:
            prompt.append("## Relevant Patterns")
            prompt.append(context.patterns_text)
            prompt.append("")

        if context.adrs:
            prompt.append("## Architecture Decision Records (ADRs)")
            prompt.append(context.adrs_text)
            prompt.append("")

        prompt.extend(
            [
                "## Instructions",
                "1. **Implement all tickets** described above.",
                "2. **Strictly follow** the project conventions provided.",
                "3. **Test-Driven Development**: Ensure corresponding unit tests are created or updated for ALL changes.",
                "4. **Batch Summary**: You MUST provide a status summary for EACH ticket using the following XML format at the end of your response:",
                "",
                "<batch_summary>",
                "- TICKET #ID: [SUCCESS|FAILED] - Brief explanation",
                "</batch_summary>",
                "",
                "5. **Propose Knowledge**: If applicable, use the `<knowledge_proposal>` format as described in project conventions.",
            ]
        )

        return "\n".join(prompt)

    def build_planning_prompt(self, requirements: str) -> str:
        """
        Build a prompt for analyzing requirements and generating a plan.

        Args:
            requirements: The project requirements text

        Returns:
            The formatted planning prompt
        """
        return f"""
# Core Requirements Analysis

Analyze the following requirements and break them down into a structured project plan.
Your goal is to produce a high-quality, professional senior engineer level breakdown.

## Requirements
{requirements}

## Instructions
1. **Identify the Core Tech Stack**: List the main technologies needed.
2. **Define Topics**: Identify logical feature areas or components (e.g., Auth, Database, Frontend, CLI).
3. **Generate Tickets**: Create a hierarchy of tickets:
    - **EPICs**: High-level features.
    - **STORIES**: User-facing features within Epics.
    - **TASKS**: Technical units of work within Stories or Epics.
    - **DOCS**: Documentation tasks.
    - **TESTS**: Testing infrastructure tasks.
4. **Define Dependencies**: Identify which tickets block others.
5. **Set Acceptance Criteria**: Every ticket must have clear "done" criteria.
6. **Assign Topics**: Every ticket should ideally belong to at least one topic.
7. **Propose initial ADRs**: If there are critical architectural decisions, propose them.

## Output Format
You MUST respond with a JSON object following this structure:

```json
{{
  "project_name": "Name of the project",
  "project_description": "Clear description",
  "tech_stack": ["tech1", "tech2"],
  "topics": [
    {{
      "name": "topic-name",
      "description": "Topic description"
    }}
  ],
  "tickets": [
    {{
      "title": "Ticket Title",
      "description": "Detailed description",
      "ticket_type": "EPIC | STORY | TASK | DOC | TEST",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "acceptance_criteria": "How to verify",
      "estimated_effort": 3,
      "topics": ["topic-name"],
      "dependencies": ["Other Ticket Title"],
      "children": [
        // Sub-tickets following same structure
      ]
    }}
  ],
  "suggested_adrs": [
    {{
      "title": "Decision Title",
      "context": "Why is this needed?",
      "decision": "What is the decision?",
      "rationale": "Why this way?",
      "consequences": "What next?",
      "alternatives": "What else?"
    }}
  ]
}}
```

Ensure the JSON is valid and follows the schema strictly.
"""

    def build_suggestion_prompt(self, tickets: list[Ticket], topic_name: str | None = None) -> str:
        """
        Build a prompt for the AI to suggest the next ticket to work on.

        Args:
            tickets: List of available READY tickets
            topic_name: Optional topic filter for context

        Returns:
            The formatted suggestion prompt
        """
        prompt = [
            "# Ticket Selection",
            "You are a technical project manager assisting an engineer.",
            "Based on the following list of pending tickets, suggest which one should be tackled next.",
            "",
        ]

        if topic_name:
            prompt.append(f"Focusing on Topic: **{topic_name}**")
            prompt.append("")

        prompt.append("## Available Tickets")
        for t in tickets:
            prompt.append(f"### Ticket #{t.id}: {t.title}")
            prompt.append(f"Type: {t.ticket_type.value}")
            prompt.append(f"Severity: {t.severity.value if t.severity else 'MEDIUM'}")
            prompt.append(f"Description: {t.description}")
            if t.acceptance_criteria:
                prompt.append(f"Acceptance Criteria: {t.acceptance_criteria}")
            prompt.append("")

        prompt.extend(
            [
                "## Instructions",
                "1. Analyze dependencies and priorities.",
                "2. Select the single most impactful ticket OR a BATCH of 2-4 highly related tickets that should be tackled next.",
                "3. Provide your selection in the following format:",
                "",
                "SELECTION: #ID1, #ID2 (if batch) or SELECTION: #ID",
                "TYPE: [SINGLE|BATCH]",
                "RATIONALE: Detailed reasoning why this ticket or batch is next.",
                "",
                "4. Do not include any other text except the selection, type, and rationale.",
            ]
        )

        return "\n".join(prompt)

    def build_summary_prompt(self, ticket: Ticket, result_content: str) -> str:
        """
        Build a prompt to summarize what was done.

        Args:
            ticket: The executed ticket
            result_content: The raw content returned by the agent

        Returns:
            A summary prompt
        """
        return f"""
Summarize the work completed for Ticket #{ticket.id}: {ticket.title}.
Focus on:
1. Files modified
2. New functionality added
3. Any issues discovered that were not fixed

Raw output:
{result_content}
"""
