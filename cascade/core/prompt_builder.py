"""Prompt builder for ticket execution."""

from __future__ import annotations

import logging

from cascade.core.prompt_templates import (
    DEFAULT_NEXT_COMMAND_PROMPT,
    get_template,
)
from cascade.models.context import MultiTicketContext, TicketContext
from cascade.models.project import PromptConfig
from cascade.models.ticket import Ticket

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds execution prompts for AI agents.

    Assembles ticket details, project conventions, and relevant
    knowledge into a structured prompt for the AI agent.
    """

    def __init__(self, prompt_config: PromptConfig | None = None):
        """
        Initialize prompt builder.

        Args:
            prompt_config: Optional custom prompt configuration
        """
        self.prompt_config = prompt_config or PromptConfig()

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

        # Get template for this ticket type
        template = get_template(ticket.ticket_type)

        # Check if custom prompts are configured
        ticket_type_key = ticket.ticket_type.value
        use_custom = self.prompt_config.enabled

        # Build task focus section
        if use_custom and ticket_type_key in self.prompt_config.task_focus:
            task_focus = self.prompt_config.task_focus[ticket_type_key]
        else:
            task_focus = template.get_task_focus()

        # Build ticket header
        prompt = [
            "# Task: Professional Software Engineering",
            "",
            task_focus,
            "",
            f"## Ticket #{ticket.id}: {title}",
            f"**Type**: {ticket.ticket_type.value}",
            f"**Priority**: {ticket.severity.value if ticket.severity else 'MEDIUM'}",
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

        # Add context sections
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

        # Add approach section
        prompt.extend(
            [
                "## Approach",
                "",
                "Before writing any code, think through your approach:",
                "1. **Understand**: What exactly needs to be done? What's the current state?",
                "2. **Plan**: What files need changes? What's the implementation strategy?",
                "3. **Execute**: Make changes following the plan",
                "4. **Verify**: Does it work? Do tests pass? Are acceptance criteria met?",
                "5. **Reflect**: What else did you discover? What follow-up work is needed?",
                "",
                "## CRITICAL: Proactive Discovery",
                "",
                "While working, actively identify and report follow-up work:",
                "",
                "**Follow-up Tickets** (report in NEW_TICKETS_NEEDED):",
                "**IMPORTANT**: Be specific! Include file paths, line numbers, and clear descriptions.",
                "",
                "Format: `TYPE: Description with file.py:line - specific details`",
                "",
                "Examples:",
                "- `BUG: Similar validation missing in signup.py:156 - allows special characters that should be blocked`",
                "- `SECURITY: SQL injection risk in user_controller.py:89 - needs parameterized queries`",
                "- `TEST: Missing integration tests for auth/oauth.py - no tests for token refresh flow`",
                "- `DOC: API docs outdated in docs/api.md - still shows old v1 endpoints`",
                "- `TASK: Refactor duplicate code in utils/validators.py:45-78 - same logic in 3 places`",
                "",
                "**What to report**:",
                "- Related bugs or edge cases (with file:line)",
                "- Security concerns or vulnerabilities (with specific location)",
                "- Missing tests (which files/functions need coverage)",
                "- Tech debt or code needing refactoring (specific code locations)",
                "- Missing features or improvements (clear value proposition)",
                "- Documentation gaps (which docs need updating)",
                "",
                "**Knowledge to Capture** (use <knowledge_proposal> tags):",
                "- Reusable patterns you created or discovered",
                "- Architectural decisions you made (propose as ADR)",
                "- Best practices or gotchas future developers should know",
                "- Useful code templates or examples",
                "",
                "**Think**: 'What did I learn that others should know?' and 'What else needs attention?'",
                "",
            ]
        )

        # Add instructions
        prompt.append("## Detailed Instructions")
        if use_custom and ticket_type_key in self.prompt_config.instructions:
            instructions = self.prompt_config.instructions[ticket_type_key]
        else:
            instructions = template.get_instructions()

        for i, instruction in enumerate(instructions, 1):
            prompt.append(f"{i}. {instruction}")

        prompt.append("")

        # Add knowledge extraction format if enabled
        if self.prompt_config.include_knowledge_extraction:
            prompt.extend(
                [
                    "## Knowledge Extraction Format",
                    "",
                    "If you created reusable patterns or made significant architectural decisions, capture them with FULL DETAIL:",
                    "",
                    "**For Patterns** (reusable code solutions):",
                    "```",
                    "<knowledge_proposal>",
                    "---",
                    "type: PATTERN",
                    "name: Clear, Descriptive Pattern Name (e.g., 'Input Validation Helper', 'Async Error Handler')",
                    "description: |",
                    "  COMPREHENSIVE description (3-5 sentences):",
                    "  - What problem does this solve?",
                    "  - When should it be used?",
                    "  - What are the key benefits?",
                    "  - What scenarios is it NOT appropriate for?",
                    "template: |",
                    "  # COMPLETE, RUNNABLE code template with:",
                    "  # - All necessary imports",
                    "  # - Type hints",
                    "  # - Docstrings",
                    "  # - Example usage in comments",
                    "  # - Error handling",
                    "  ",
                    "  def example_pattern(input: str) -> bool:",
                    '      """Clear docstring explaining purpose and usage."""',
                    "      # Implementation here",
                    "      pass",
                    "tags: [specific, searchable, relevant, tags, technologies]",
                    "examples: [",
                    "  file1.py:123,  # Where this pattern is used",
                    "  file2.py:45,   # Another example",
                    "  file3.py:89    # More examples help!",
                    "]",
                    "---",
                    "</knowledge_proposal>",
                    "```",
                    "",
                    "**For Architectural Decisions** (significant design choices):",
                    "```",
                    "<knowledge_proposal>",
                    "---",
                    "type: ADR",
                    "title: ADR: Clear, Specific Decision Title (e.g., 'Use Parameterized Queries for All DB Access')",
                    "context: |",
                    "  DETAILED context (2-4 sentences):",
                    "  - What situation or problem led to this decision?",
                    "  - What were the constraints or requirements?",
                    "  - Why does this decision matter now?",
                    "decision: |",
                    "  SPECIFIC decision statement (1-3 sentences):",
                    "  - Exactly what are we choosing to do?",
                    "  - What will change?",
                    "  - What are the boundaries/scope?",
                    "rationale: |",
                    "  COMPREHENSIVE rationale (3-5 sentences):",
                    "  - Why is this the best choice?",
                    "  - What benefits does it provide?",
                    "  - What problems does it solve?",
                    "  - What trade-offs are we accepting?",
                    "consequences: |",
                    "  DETAILED consequences (3-5 sentences):",
                    "  - What are the immediate implications?",
                    "  - What follow-up work is needed?",
                    "  - What will be easier/harder going forward?",
                    "  - What technical debt might this create/eliminate?",
                    "alternatives: |",
                    "  SPECIFIC alternatives considered (2-4 options):",
                    "  - Alternative 1: Description and why rejected",
                    "  - Alternative 2: Description and why rejected",
                    "  - Alternative 3: Description and why rejected",
                    "  - Explain specific reasons for rejection",
                    "---",
                    "</knowledge_proposal>",
                    "```",
                    "",
                    "**Knowledge Quality Standards**:",
                    "- [OK] Patterns have COMPLETE, runnable code (not pseudocode)",
                    "- [OK] Patterns include 2-3 file examples showing actual usage",
                    "- [OK] ADRs explain context thoroughly (someone reading months later should understand)",
                    "- [OK] ADRs list 2-3 specific alternatives that were considered",
                    "- [OK] All fields are filled with substantive content (no placeholders)",
                    "- [OK] Technical terms are explained or obvious from context",
                    "",
                    "**When to propose knowledge**:",
                    "- You solved a problem in a novel or reusable way",
                    "- You made a significant technical decision affecting architecture",
                    "- You discovered a best practice or important gotcha",
                    "- You created a useful abstraction, helper, or utility",
                    "- You found a pattern worth standardizing across the codebase",
                    "",
                ]
            )

        # Add quality expectations
        prompt.extend(
            [
                "## Quality Standards",
                "",
                "Your implementation must meet professional standards:",
                "- [OK] All acceptance criteria met completely",
                "- [OK] Code follows project conventions exactly",
                "- [OK] Changes are minimal and focused (no scope creep)",
                "- [OK] Tests added/updated and passing",
                "- [OK] No syntax errors, linting errors, or type errors",
                "- [OK] Error handling is appropriate and follows existing patterns",
                "- [OK] Code is production-ready",
                "",
            ]
        )

        # Add response format
        prompt.append("## Required Response Format")
        prompt.append("")
        prompt.append("**CRITICAL**: You MUST end your response with the following status summary.")
        prompt.append("Fill in ALL fields with specific, accurate information:")
        prompt.append("")
        if use_custom and ticket_type_key in self.prompt_config.response_format:
            response_format = self.prompt_config.response_format[ticket_type_key]
        else:
            response_format = template.get_response_format()

        prompt.append(response_format)

        return "\n".join(prompt)

    def build_multi_execution_prompt(self, context: MultiTicketContext) -> str:
        """
        Build a prompt for executing multiple tickets together.

        Args:
            context: The assembled MultiTicketContext

        Returns:
            The formatted prompt string
        """
        # Group tickets by type to provide focused guidance
        ticket_types = {t.ticket_type for t in context.tickets}
        is_mixed_types = len(ticket_types) > 1

        prompt = [
            "# Task: Coordinated Batch Execution",
            "",
            "You are executing multiple related tickets together. This requires careful coordination.",
            "",
            "## Batch Execution Strategy",
            "",
            "1. **Read All Tickets First**: Understand the full scope before starting",
            "2. **Identify Dependencies**: Determine the order - what must be done first?",
            "3. **Plan Integration**: How will these changes work together?",
            "4. **Execute in Order**: Implement tickets in dependency order",
            "5. **Verify Together**: Ensure all changes work as a cohesive whole",
            "",
            "**Critical**: All tickets must be COMPLETE. Don't leave any partially done.",
            "",
        ]

        if is_mixed_types:
            prompt.extend(
                [
                    "**Note**: This batch contains different ticket types.",
                    "Apply the specific guidelines for each type while ensuring overall coherence.",
                    "",
                ]
            )

        # List all tickets with their details
        for ticket in context.tickets:
            title = self._sanitize(ticket.title)
            description = self._sanitize(ticket.description)
            ac = self._sanitize(ticket.acceptance_criteria)

            template = get_template(ticket.ticket_type)
            task_focus = template.get_task_focus()

            prompt.extend(
                [
                    f"## Ticket #{ticket.id}: {title}",
                    f"**Type**: {ticket.ticket_type.value}",
                    f"**Priority**: {ticket.severity.value if ticket.severity else 'MEDIUM'}",
                    "",
                    f"**Type-Specific Guidance**: {task_focus}",
                    "",
                    "### Description",
                    f"{description}",
                    "",
                    "### Acceptance Criteria",
                    f"{ac or 'None specified'}",
                    "",
                ]
            )

        # Add context sections
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

        # General batch instructions
        prompt.extend(
            [
                "## Batch Execution Instructions",
                "",
                "1. **Complete ALL Tickets**: Every ticket in this batch must be fully implemented. Mark each as COMPLETE or BLOCKED individually.",
                "",
                "2. **Execution Order**: Implement tickets in logical order based on dependencies. If ticket B needs changes from ticket A, do A first.",
                "",
                "3. **Consistency**: Use consistent patterns across all tickets. Don't solve the same problem two different ways. Establish patterns in early tickets and follow them in later ones.",
                "",
                "4. **Integration**: Think about how these changes interact. Shared files? Common data? Integration points? Handle these coherently.",
                "",
                "5. **Project Conventions**: Strictly follow the project conventions for ALL changes. Maintain consistency with existing code.",
                "",
                "6. **Comprehensive Testing**: Add tests for all new functionality. Ensure tests cover interactions between the changes from different tickets.",
                "",
                "7. **Type-Specific Guidelines**: Follow the guidance specific to each ticket type while maintaining overall batch coherence.",
                "",
                "8. **Proactive Discovery**: While working, identify follow-up work and knowledge opportunities across ALL tickets. Report findings per ticket.",
                "",
            ]
        )

        # Knowledge extraction if enabled
        if self.prompt_config.include_knowledge_extraction:
            prompt.extend(
                [
                    "## Knowledge Proposals (Optional)",
                    "Use the standard `<knowledge_proposal>` format for patterns or ADRs.",
                    "",
                ]
            )

        # Batch summary format
        prompt.extend(
            [
                "## Quality Standards for Batch",
                "",
                "Your batch implementation must meet professional standards:",
                "- ✅ ALL tickets in batch are COMPLETE (or explicitly BLOCKED with reason)",
                "- ✅ Changes work together cohesively",
                "- ✅ Consistent patterns used across all tickets",
                "- ✅ All acceptance criteria met for every ticket",
                "- ✅ Comprehensive testing covers individual tickets AND their interactions",
                "- ✅ Code is production-ready",
                "",
                "## CRITICAL: Batch Status Summary",
                "",
                "**REQUIRED**: You MUST end your response with status for EACH ticket in this exact format:",
                "",
                "<batch_summary>",
            ]
        )

        for ticket in context.tickets:
            prompt.append(
                f"- TICKET #{ticket.id}: [COMPLETE|BLOCKED] - Brief explanation of status and what was done/blocking issue"
            )

        prompt.extend(
            [
                "</batch_summary>",
                "",
                "**Rules**:",
                "- Mark COMPLETE only if the ticket is 100% done with all acceptance criteria met",
                "- Mark BLOCKED if you cannot complete, with specific reason why",
                "- Provide a brief explanation for each ticket's status",
                "- Every ticket in the batch MUST have a status line",
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
        return f"""# Project Requirements Analysis & Breakdown

You are a senior software architect analyzing requirements to create a structured, actionable project plan.

## Requirements to Analyze
{requirements}

## Your Task

Create a comprehensive breakdown that a development team can execute. Think carefully about:
- What technologies are truly needed (don't over-engineer)
- How to organize work into logical, independent units
- What dependencies exist and what order makes sense
- What architectural decisions must be made early

## Analysis Process

### Step 1: Understand the Requirements
- What is the core problem being solved?
- Who are the users and what do they need?
- What are the critical vs nice-to-have features?
- What are the technical constraints?

### Step 2: Identify Architecture & Tech Stack
- What technologies are required? (List only what's necessary)
- What are the major components/layers? (e.g., API, Database, Frontend, CLI, Auth)
- What are the critical architectural decisions? (These become ADRs)

### Step 3: Define Topics (Feature Areas)
Create logical groupings like:
- **Core Infrastructure**: Database, auth, deployment
- **Feature Areas**: User management, payments, notifications
- **Cross-Cutting**: Testing, documentation, security

### Step 4: Create Ticket Hierarchy
Break down into actionable work:

**EPICs**: Large features spanning multiple components (e.g., "User Authentication System")
- Should take multiple sprints
- Contains multiple Stories/Tasks
- Has clear user/technical value

**STORIES**: User-facing features (e.g., "User can sign up with email")
- Focused on user value
- Deliverable in 1-3 days
- Has clear acceptance criteria from user perspective

**TASKS**: Technical implementation work (e.g., "Implement JWT token generation")
- Focused on technical objectives
- Deliverable in 0.5-2 days
- Often enablers for Stories

**TESTS**: Testing infrastructure (e.g., "Add integration tests for auth flow")
- Focused on quality assurance
- Can be parallel work

**DOCS**: Documentation (e.g., "Document API authentication endpoints")
- User guides, API docs, architecture docs

**SECURITY**: Security hardening (e.g., "Add rate limiting to login endpoint")
- Security reviews, vulnerability fixes

### Step 5: Set Priorities
- CRITICAL: Blocking work, security issues, core infrastructure
- HIGH: Important features, significant value
- MEDIUM: Standard features, improvements
- LOW: Nice-to-haves, polish

### Step 6: Define Dependencies
- What must be built before other things?
- Example: Database schema → API endpoints → Frontend UI
- Be specific: "depends on: Database Setup, JWT Implementation"

### Step 7: Write Acceptance Criteria
Make criteria specific, testable, and complete:
- Good: "User can submit email/password, receive JWT token, use token to access protected endpoints"
- Bad: "Authentication works"

## Output Format

Respond with a valid JSON object following this exact structure:

```json
{{
  "project_name": "Concise project name",
  "project_description": "Clear 2-3 sentence description of what this project does and who it's for",
  "tech_stack": ["tech1", "tech2", "tech3"],
  "topics": [
    {{
      "name": "topic-name",
      "description": "What this topic area covers"
    }}
  ],
  "tickets": [
    {{
      "title": "Clear, action-oriented title",
      "description": "Detailed description of what needs to be done and why. Include context.",
      "ticket_type": "EPIC | STORY | TASK | DOC | TEST | SECURITY",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "acceptance_criteria": "Specific, testable criteria for 'done'. Use bullets for multiple criteria.",
      "estimated_effort": 3,
      "topics": ["topic-name"],
      "dependencies": ["Title of blocking ticket"],
      "children": [
        // Nested tickets for EPICs (same structure)
      ]
    }}
  ],
  "suggested_adrs": [
    {{
      "title": "ADR: Clear decision title",
      "context": "What is the situation and why do we need to decide?",
      "decision": "What are we choosing to do?",
      "rationale": "Why is this the best choice? What are the benefits?",
      "consequences": "What are the implications and follow-up work?",
      "alternatives": "What other options did we consider and why not those?"
    }}
  ]
}}
```

## Quality Checklist

Before outputting, verify:
- [ ] Tickets are appropriately sized (EPICs are large, Tasks are small)
- [ ] Dependencies are logical and form a valid DAG (no circular dependencies)
- [ ] Every ticket has clear, testable acceptance criteria
- [ ] Priorities reflect true importance and dependencies
- [ ] Topics group related work logically
- [ ] Tech stack includes only what's necessary
- [ ] ADRs cover significant architectural choices
- [ ] JSON is valid and follows schema exactly

Output ONLY the JSON object. Ensure it is valid JSON that can be parsed."""

    def build_suggestion_prompt(self, tickets: list[Ticket], topic_name: str | None = None) -> str:
        """
        Build a prompt for the AI to suggest the next ticket to work on.

        Args:
            tickets: List of available READY tickets
            topic_name: Optional topic filter for context

        Returns:
            The formatted suggestion prompt
        """
        # Use custom prompt if configured, otherwise use default
        if self.prompt_config.enabled and self.prompt_config.next_command_prompt:
            base_prompt = self.prompt_config.next_command_prompt
        else:
            base_prompt = DEFAULT_NEXT_COMMAND_PROMPT

        prompt = [base_prompt, ""]

        if topic_name:
            prompt.append(f"**Topic Filter**: {topic_name}")
            prompt.append("")

        prompt.append("## Available Tickets")
        for t in tickets:
            prompt.append(f"### Ticket #{t.id}: {t.title}")
            prompt.append(f"**Type**: {t.ticket_type.value}")
            prompt.append(f"**Priority**: {t.severity.value if t.severity else 'MEDIUM'}")
            prompt.append(f"**Description**: {t.description}")
            if t.acceptance_criteria:
                prompt.append(f"**Acceptance Criteria**: {t.acceptance_criteria}")
            prompt.append("")

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
