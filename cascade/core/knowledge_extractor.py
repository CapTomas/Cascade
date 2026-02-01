"""Knowledge extraction logic for Cascade."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import yaml

from cascade.models.enums import KnowledgeStatus
from cascade.models.knowledge import ADR, Pattern

logger = logging.getLogger(__name__)


class KnowledgeExtractor:
    """
    Extracts knowledge proposals (Patterns, ADRs) from AI agent responses.

    Agents use a specific XML-like tag to propose knowledge:
    <knowledge_proposal>
    ---
    type: PATTERN
    name: Repository Pattern
    description: Abstract data access logic behind a common interface.
    template: |
      class {Name}Repository:
          def get(self, id): ...
    tags: [persistence, design-pattern]
    examples: [src/storage/db.py]
    ---
    type: ADR
    title: Use PostgreSQL for main database
    context: We need a reliable relational database for user data.
    decision: We will use PostgreSQL 14.
    rationale: It supports ACID transactions and JSONB for flexibility.
    consequences: Requires setting up a PG instance; better data integrity.
    alternatives: MongoDB, MySQL
    </knowledge_proposal>
    """

    PROPOSAL_REGEX = re.compile(
        r"<knowledge_proposal>(.*?)</knowledge_proposal>", re.DOTALL | re.IGNORECASE
    )

    def extract_proposals(
        self, response_text: str, ticket_id: int | None = None
    ) -> list[Pattern | ADR]:
        """
        Parse the agent response for knowledge proposals.

        Args:
            response_text: The full text response from the AI agent
            ticket_id: The ID of the ticket being executed

        Returns:
            List of Pattern or ADR objects in PROPOSED status.
        """
        proposals: list[Any] = []
        matches = self.PROPOSAL_REGEX.findall(response_text)

        for match_text in matches:
            try:
                # Handle multiple documents in one proposal block
                raw_proposals = yaml.safe_load_all(match_text.strip())
                for raw in raw_proposals:
                    if not raw or not isinstance(raw, dict):
                        continue

                    proposal_type = raw.get("type", "").upper()

                    if proposal_type == "PATTERN":
                        proposals.append(self._create_pattern(raw, ticket_id))
                    elif proposal_type == "ADR":
                        proposals.append(self._create_adr(raw, ticket_id))
                    else:
                        logger.warning(f"Unknown knowledge proposal type: {proposal_type}")

            except (yaml.YAMLError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse knowledge proposal: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error during knowledge extraction: {e}")

        return proposals

    def _create_pattern(self, data: dict[str, Any], ticket_id: int | None) -> Pattern:
        """Create a Pattern model from raw data with validation."""
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()

        if not name:
            raise ValueError("Pattern name is required")
        if not description:
            raise ValueError("Pattern description is required")

        return Pattern(
            pattern_name=name,
            description=description,
            code_template=data.get("template", "").strip(),
            applies_to_tags=data.get("tags", []),
            learned_from_ticket_id=ticket_id,
            status=KnowledgeStatus.PROPOSED,
            file_examples=data.get("examples", []),
        )

    def _create_adr(self, data: dict[str, Any], ticket_id: int | None) -> ADR:
        """Create an ADR model from raw data with validation."""
        title = data.get("title", "").strip()
        context = data.get("context", "").strip()
        decision = data.get("decision", "").strip()
        rationale = data.get("rationale", "").strip()

        if not title:
            raise ValueError("ADR title is required")
        if not context:
            raise ValueError("ADR context is required")
        if not decision:
            raise ValueError("ADR decision is required")
        if not rationale:
            raise ValueError("ADR rationale is required")

        return ADR(
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
            consequences=data.get("consequences", "").strip(),
            alternatives_considered=data.get("alternatives", "").strip(),
            created_by_ticket_id=ticket_id,
            status=KnowledgeStatus.PROPOSED,
        )
