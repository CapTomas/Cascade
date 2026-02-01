"""Knowledge base management for Cascade (conventions, patterns, ADRs)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from cascade.models.enums import KnowledgeStatus
from cascade.models.knowledge import ADR, Convention, Pattern
from cascade.models.ticket import Ticket
from cascade.storage.database import Database


class KnowledgeBase:
    """
    Manages patterns, ADRs, and conventions.

    - Conventions are lightweight rules always loaded into context
    - Patterns and ADRs are loaded on-demand based on relevance
    - Only APPROVED knowledge is used in agent context
    - AI proposes knowledge, humans approve/reject
    """

    def __init__(self, db: Database, conventions_path: Path | None = None):
        """
        Initialize knowledge base.

        Args:
            db: Database instance
            conventions_path: Path to conventions.yaml for sync
        """
        self.db = db
        self.conventions_path = conventions_path

    # ==================== CONVENTIONS ====================

    def add_convention(
        self,
        category: str,
        key: str,
        value: str,
        rationale: str = "",
        priority: int = 0,
    ) -> Convention:
        """
        Add or update a convention.

        Args:
            category: Convention category (naming, style, structure, security)
            key: Convention key
            value: Convention value/rule
            rationale: Why this convention exists
            priority: Higher = loaded first

        Returns:
            Created or updated convention
        """
        # Check if exists (upsert logic)
        existing = self.get_convention(category, key)
        if existing:
            self.db.update(
                "conventions",
                {
                    "convention_value": value,
                    "rationale": rationale,
                    "priority": priority,
                },
                "category = ? AND convention_key = ?",
                (category, key),
            )
            existing.convention_value = value
            existing.rationale = rationale
            existing.priority = priority
            return existing

        now = datetime.now()
        conv_id = self.db.insert(
            "conventions",
            {
                "category": category,
                "convention_key": key,
                "convention_value": value,
                "rationale": rationale,
                "priority": priority,
                "created_at": now,
            },
        )

        return Convention(
            id=conv_id,
            category=category,
            convention_key=key,
            convention_value=value,
            rationale=rationale,
            priority=priority,
            created_at=now,
        )

    def get_convention(self, category: str, key: str) -> Convention | None:
        """Get a specific convention."""
        row = self.db.fetch_one(
            "SELECT * FROM conventions WHERE category = ? AND convention_key = ?",
            (category, key),
        )
        return Convention.from_dict(dict(row)) if row else None

    def get_conventions(self, category: str | None = None) -> list[Convention]:
        """
        Get all conventions, optionally filtered by category.

        Returns conventions ordered by priority (highest first).
        """
        if category:
            rows = self.db.fetch_all(
                "SELECT * FROM conventions WHERE category = ? ORDER BY priority DESC",
                (category,),
            )
        else:
            rows = self.db.fetch_all("SELECT * FROM conventions ORDER BY category, priority DESC")

        return [Convention.from_dict(dict(row)) for row in rows]

    def delete_convention(self, category: str, key: str) -> bool:
        """Delete a convention."""
        count = self.db.delete(
            "conventions",
            "category = ? AND convention_key = ?",
            (category, key),
        )
        return count > 0

    def sync_conventions_to_yaml(self) -> None:
        """Export conventions to YAML file for human readability."""
        if not self.conventions_path:
            return

        conventions = self.get_conventions()
        grouped: dict[str, dict[str, Any]] = {}

        for conv in conventions:
            if conv.category not in grouped:
                grouped[conv.category] = {}
            grouped[conv.category][conv.convention_key] = conv.convention_value

        with open(self.conventions_path, "w") as f:
            yaml.dump(grouped, f, default_flow_style=False, sort_keys=False)

    def load_conventions_from_yaml(self) -> None:
        """Import conventions from YAML file."""
        if not self.conventions_path or not self.conventions_path.exists():
            return

        with open(self.conventions_path) as f:
            data = yaml.safe_load(f) or {}

        for category, items in data.items():
            if isinstance(items, dict):
                for key, value in items.items():
                    if key != "description" and isinstance(value, str):
                        self.add_convention(category, key, value)

    # ==================== PATTERNS ====================

    def propose_pattern(
        self,
        pattern_name: str,
        description: str,
        code_template: str = "",
        applies_to_tags: list[str] | None = None,
        learned_from_ticket_id: int | None = None,
        file_examples: list[str] | None = None,
    ) -> Pattern:
        """
        Propose a new pattern (status = PROPOSED).

        Patterns are proposed by AI and require human approval.

        Args:
            pattern_name: Unique pattern name
            description: What this pattern does
            code_template: Example code
            applies_to_tags: Tags for matching relevance
            learned_from_ticket_id: Ticket that led to this pattern
            file_examples: Example files using this pattern

        Returns:
            Created pattern
        """
        now = datetime.now()
        pattern_id = self.db.insert(
            "patterns",
            {
                "pattern_name": pattern_name,
                "description": description,
                "code_template": code_template,
                "applies_to_tags": json.dumps(applies_to_tags or []),
                "learned_from_ticket_id": learned_from_ticket_id,
                "status": KnowledgeStatus.PROPOSED.value,
                "reuse_count": 0,
                "file_examples": json.dumps(file_examples or []),
                "created_at": now,
            },
        )

        return Pattern(
            id=pattern_id,
            pattern_name=pattern_name,
            description=description,
            code_template=code_template,
            applies_to_tags=applies_to_tags or [],
            learned_from_ticket_id=learned_from_ticket_id,
            status=KnowledgeStatus.PROPOSED,
            file_examples=file_examples or [],
            created_at=now,
        )

    def get_pattern(self, pattern_id: int) -> Pattern | None:
        """Get pattern by ID."""
        row = self.db.fetch_one("SELECT * FROM patterns WHERE id = ?", (pattern_id,))
        return Pattern.from_dict(dict(row)) if row else None

    def get_pattern_by_name(self, name: str) -> Pattern | None:
        """Get pattern by name."""
        row = self.db.fetch_one("SELECT * FROM patterns WHERE pattern_name = ?", (name,))
        return Pattern.from_dict(dict(row)) if row else None

    def get_patterns(
        self,
        status: KnowledgeStatus | None = None,
        limit: int = 100,
    ) -> list[Pattern]:
        """Get patterns, optionally filtered by status."""
        if status:
            rows = self.db.fetch_all(
                """
                SELECT * FROM patterns
                WHERE status = ?
                ORDER BY reuse_count DESC, created_at DESC
                LIMIT ?
                """,
                (status.value, limit),
            )
        else:
            rows = self.db.fetch_all(
                """
                SELECT * FROM patterns
                ORDER BY reuse_count DESC, created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        return [Pattern.from_dict(dict(row)) for row in rows]

    def get_relevant_patterns(
        self,
        ticket: Ticket,
        limit: int = 3,
    ) -> list[Pattern]:
        """
        Get patterns relevant to a ticket.

        Matches by:
        - Tags in ticket metadata
        - Affected files
        - Ticket type

        Only returns APPROVED patterns.
        """
        # Get all approved patterns
        approved = self.get_patterns(status=KnowledgeStatus.APPROVED, limit=50)

        if not approved:
            return []

        # Score patterns by relevance
        scored = []
        ticket_files = set(ticket.affected_files or [])
        ticket_tags = set(ticket.metadata.get("tags", []))

        for pattern in approved:
            score = 0

            # Tag matching
            pattern_tags = set(pattern.applies_to_tags or [])
            tag_overlap = len(ticket_tags & pattern_tags)
            score += tag_overlap * 10

            # File matching
            pattern_files = set(pattern.file_examples or [])
            file_overlap = len(ticket_files & pattern_files)
            score += file_overlap * 5

            # Reuse count bonus
            score += min(pattern.reuse_count, 10)

            if score > 0:
                scored.append((score, pattern))

        # Sort by score and return top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def approve_pattern(self, pattern_id: int) -> Pattern | None:
        """Approve a proposed pattern."""
        self.db.update(
            "patterns",
            {
                "status": KnowledgeStatus.APPROVED.value,
                "approved_at": datetime.now(),
            },
            "id = ?",
            (pattern_id,),
        )
        return self.get_pattern(pattern_id)

    def reject_pattern(self, pattern_id: int) -> Pattern | None:
        """Reject a proposed pattern."""
        self.db.update(
            "patterns",
            {"status": KnowledgeStatus.REJECTED.value},
            "id = ?",
            (pattern_id,),
        )
        return self.get_pattern(pattern_id)

    def increment_pattern_usage(self, pattern_id: int) -> None:
        """Increment pattern reuse count."""
        self.db.execute(
            "UPDATE patterns SET reuse_count = reuse_count + 1 WHERE id = ?",
            (pattern_id,),
        )

    # ==================== ADRs ====================

    def propose_adr(
        self,
        title: str,
        context: str,
        decision: str,
        rationale: str,
        consequences: str = "",
        alternatives_considered: str = "",
        created_by_ticket_id: int | None = None,
    ) -> ADR:
        """
        Propose a new Architecture Decision Record.

        ADRs capture significant architectural decisions with context.
        They are proposed by AI and require human approval.

        Args:
            title: Short decision title
            context: Why was this decision needed?
            decision: What was decided?
            rationale: Why this decision?
            consequences: What are the implications?
            alternatives_considered: What else was considered?
            created_by_ticket_id: Ticket that led to this ADR

        Returns:
            Created ADR
        """
        # Get next ADR number
        result = self.db.fetch_one("SELECT MAX(adr_number) FROM adrs")
        next_number = (result[0] or 0) + 1 if result else 1

        now = datetime.now()
        adr_id = self.db.insert(
            "adrs",
            {
                "adr_number": next_number,
                "title": title,
                "status": KnowledgeStatus.PROPOSED.value,
                "context": context,
                "decision": decision,
                "rationale": rationale,
                "consequences": consequences,
                "alternatives_considered": alternatives_considered,
                "created_by_ticket_id": created_by_ticket_id,
                "created_at": now,
            },
        )

        return ADR(
            id=adr_id,
            adr_number=next_number,
            title=title,
            status=KnowledgeStatus.PROPOSED,
            context=context,
            decision=decision,
            rationale=rationale,
            consequences=consequences,
            alternatives_considered=alternatives_considered,
            created_by_ticket_id=created_by_ticket_id,
            created_at=now,
        )

    def get_adr(self, adr_id: int) -> ADR | None:
        """Get ADR by ID."""
        row = self.db.fetch_one("SELECT * FROM adrs WHERE id = ?", (adr_id,))
        return ADR.from_dict(dict(row)) if row else None

    def get_adr_by_number(self, adr_number: int) -> ADR | None:
        """Get ADR by number."""
        row = self.db.fetch_one("SELECT * FROM adrs WHERE adr_number = ?", (adr_number,))
        return ADR.from_dict(dict(row)) if row else None

    def get_adrs(
        self,
        status: KnowledgeStatus | None = None,
        limit: int = 100,
    ) -> list[ADR]:
        """Get ADRs, optionally filtered by status."""
        if status:
            rows = self.db.fetch_all(
                """
                SELECT * FROM adrs
                WHERE status = ?
                ORDER BY adr_number DESC
                LIMIT ?
                """,
                (status.value, limit),
            )
        else:
            rows = self.db.fetch_all(
                """
                SELECT * FROM adrs
                ORDER BY adr_number DESC
                LIMIT ?
                """,
                (limit,),
            )

        return [ADR.from_dict(dict(row)) for row in rows]

    def get_relevant_adrs(
        self,
        ticket: Ticket,
        limit: int = 3,
    ) -> list[ADR]:
        """
        Get ADRs relevant to a ticket.

        Currently returns most recent approved ADRs.
        Future: match by affected areas/technologies.

        Only returns APPROVED ADRs.
        """
        return self.get_adrs(status=KnowledgeStatus.APPROVED, limit=limit)

    def approve_adr(self, adr_id: int) -> ADR | None:
        """Approve a proposed ADR."""
        self.db.update(
            "adrs",
            {
                "status": KnowledgeStatus.APPROVED.value,
                "approved_at": datetime.now(),
            },
            "id = ?",
            (adr_id,),
        )
        return self.get_adr(adr_id)

    def reject_adr(self, adr_id: int) -> ADR | None:
        """Reject a proposed ADR."""
        self.db.update(
            "adrs",
            {"status": KnowledgeStatus.REJECTED.value},
            "id = ?",
            (adr_id,),
        )
        return self.get_adr(adr_id)

    def supersede_adr(self, adr_id: int, superseded_by_id: int) -> ADR | None:
        """Mark an ADR as superseded by another."""
        self.db.update(
            "adrs",
            {"status": KnowledgeStatus.SUPERSEDED.value},
            "id = ?",
            (adr_id,),
        )
        return self.get_adr(adr_id)

    # ==================== PENDING REVIEW ====================

    def get_pending_knowledge(self) -> dict[str, Any]:
        """
        Get all knowledge items pending human review.

        Returns:
            Dict with 'patterns' and 'adrs' lists
        """
        return {
            "patterns": self.get_patterns(status=KnowledgeStatus.PROPOSED),
            "adrs": self.get_adrs(status=KnowledgeStatus.PROPOSED),
        }

    def approve(self, entity_type: str, entity_id: int) -> bool:
        """
        Approve a knowledge item.

        Args:
            entity_type: 'pattern' or 'adr'
            entity_id: Item ID

        Returns:
            True if approved
        """
        if entity_type == "pattern":
            return self.approve_pattern(entity_id) is not None
        elif entity_type == "adr":
            return self.approve_adr(entity_id) is not None
        return False

    def reject(self, entity_type: str, entity_id: int) -> bool:
        """
        Reject a knowledge item.

        Args:
            entity_type: 'pattern' or 'adr'
            entity_id: Item ID

        Returns:
            True if rejected
        """
        if entity_type == "pattern":
            return self.reject_pattern(entity_id) is not None
        elif entity_type == "adr":
            return self.reject_adr(entity_id) is not None
        return False
