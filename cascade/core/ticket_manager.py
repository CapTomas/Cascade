"""Ticket management for Cascade."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from cascade.models.enums import Severity, TicketStatus, TicketType
from cascade.models.ticket import Ticket, TicketDependency
from cascade.storage.database import Database


class TicketManager:
    """
    Manages ticket CRUD operations and queries.

    This is the primary interface for working with tickets.
    All ticket operations should go through this class.
    """

    def __init__(self, db: Database):
        """
        Initialize ticket manager.

        Args:
            db: Database instance
        """
        self.db = db

    def create(
        self,
        title: str,
        ticket_type: TicketType = TicketType.TASK,
        description: str = "",
        severity: Severity | None = None,
        parent_ticket_id: int | None = None,
        acceptance_criteria: str = "",
        affected_files: list[str] | None = None,
        estimated_effort: int | None = None,
        status: TicketStatus = TicketStatus.DEFINED,
    ) -> Ticket:
        """
        Create a new ticket.

        Args:
            title: Ticket title
            ticket_type: Type of ticket (TASK, BUG, etc.)
            description: Detailed description
            severity: Priority severity
            parent_ticket_id: Parent ticket for hierarchy
            acceptance_criteria: What "done" means
            affected_files: List of files this ticket affects
            estimated_effort: Estimated story points or hours

        Returns:
            Created ticket with ID
        """
        now = datetime.now()
        data = {
            "ticket_type": ticket_type.value,
            "title": title,
            "description": description,
            "status": status.value,
            "severity": severity.value if severity else None,
            "priority_score": float(self._calculate_priority(severity)),
            "parent_ticket_id": parent_ticket_id,
            "created_at": now,
            "updated_at": now,
            "acceptance_criteria": acceptance_criteria,
            "affected_files": json.dumps(affected_files or []),
            "estimated_effort": estimated_effort,
            "context_mode": "minimal",
            "metadata": json.dumps({}),
        }

        ticket_id = self.db.insert("tickets", data)

        return Ticket(
            id=ticket_id,
            ticket_type=ticket_type,
            title=title,
            description=description,
            status=status,
            severity=severity,
            priority_score=float(data["priority_score"]),  # type: ignore
            parent_ticket_id=parent_ticket_id,
            created_at=now,
            updated_at=now,
            acceptance_criteria=acceptance_criteria,
            affected_files=affected_files or [],
            estimated_effort=estimated_effort,
        )

    def get(self, ticket_id: int) -> Ticket | None:
        """
        Get ticket by ID.

        Args:
            ticket_id: Ticket ID

        Returns:
            Ticket or None if not found
        """
        row = self.db.fetch_one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        if not row:
            return None
        return self._row_to_ticket(row)

    def get_by_status(self, status: TicketStatus) -> list[Ticket]:
        """
        Get all tickets with given status.

        Args:
            status: Ticket status to filter by

        Returns:
            List of matching tickets
        """
        rows = self.db.fetch_all(
            "SELECT * FROM tickets WHERE status = ? ORDER BY priority_score DESC",
            (status.value,),
        )
        return [self._row_to_ticket(row) for row in rows]

    def get_by_type(self, ticket_type: TicketType) -> list[Ticket]:
        """
        Get all tickets of given type.

        Args:
            ticket_type: Ticket type to filter by

        Returns:
            List of matching tickets
        """
        rows = self.db.fetch_all(
            "SELECT * FROM tickets WHERE ticket_type = ? ORDER BY priority_score DESC",
            (ticket_type.value,),
        )
        return [self._row_to_ticket(row) for row in rows]

    def get_ready(self) -> list[Ticket]:
        """Get all tickets ready for execution."""
        return self.get_by_status(TicketStatus.READY)

    def get_next_ready(self, topic_id: int | None = None) -> Ticket | None:
        """
        Get highest priority ready ticket.

        Args:
            topic_id: Optional topic to filter by

        Returns:
            Highest priority ready ticket or None
        """
        if topic_id:
            row = self.db.fetch_one(
                """
                SELECT t.* FROM tickets t
                JOIN ticket_topics tt ON t.id = tt.ticket_id
                WHERE t.status = ? AND tt.topic_id = ?
                ORDER BY t.priority_score DESC
                LIMIT 1
                """,
                (TicketStatus.READY.value, topic_id),
            )
        else:
            row = self.db.fetch_one(
                """
                SELECT * FROM tickets
                WHERE status = ?
                ORDER BY priority_score DESC
                LIMIT 1
                """,
                (TicketStatus.READY.value,),
            )

        return self._row_to_ticket(row) if row else None

    def get_children(self, parent_id: int) -> list[Ticket]:
        """
        Get child tickets of a parent.

        Args:
            parent_id: Parent ticket ID

        Returns:
            List of child tickets
        """
        rows = self.db.fetch_all(
            "SELECT * FROM tickets WHERE parent_ticket_id = ? ORDER BY priority_score DESC",
            (parent_id,),
        )
        return [self._row_to_ticket(row) for row in rows]

    def list_all(
        self,
        status: TicketStatus | None = None,
        ticket_type: TicketType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Ticket]:
        """
        List tickets with optional filters.

        Args:
            status: Filter by status
            ticket_type: Filter by type
            limit: Maximum results
            offset: Skip first N results

        Returns:
            List of matching tickets
        """
        conditions = []
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if ticket_type:
            conditions.append("ticket_type = ?")
            params.append(ticket_type.value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM tickets
            WHERE {where_clause}
            ORDER BY priority_score DESC, created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self.db.fetch_all(query, tuple(params))
        return [self._row_to_ticket(row) for row in rows]

    def update(self, ticket_id: int, **updates: Any) -> Ticket | None:
        """
        Update ticket fields.

        Args:
            ticket_id: Ticket to update
            **updates: Field names and new values

        Returns:
            Updated ticket or None if not found
        """
        if not updates:
            return self.get(ticket_id)

        # Handle enum conversions
        if "status" in updates and isinstance(updates["status"], TicketStatus):
            updates["status"] = updates["status"].value
        if "ticket_type" in updates and isinstance(updates["ticket_type"], TicketType):
            updates["ticket_type"] = updates["ticket_type"].value
        if "severity" in updates and isinstance(updates["severity"], Severity):
            updates["severity"] = updates["severity"].value

        # Handle list/dict conversions
        if "affected_files" in updates:
            updates["affected_files"] = json.dumps(updates["affected_files"])
        if "metadata" in updates:
            updates["metadata"] = json.dumps(updates["metadata"])

        # Always update timestamp
        updates["updated_at"] = datetime.now()

        # Recalculate priority if severity changed
        if "severity" in updates:
            severity = Severity(updates["severity"]) if updates["severity"] else None
            updates["priority_score"] = self._calculate_priority(severity)

        self.db.update("tickets", updates, "id = ?", (ticket_id,))
        return self.get(ticket_id)

    def update_status(self, ticket_id: int, status: TicketStatus) -> Ticket | None:
        """
        Update ticket status.

        Handles special cases like setting completed_at timestamp.

        Args:
            ticket_id: Ticket to update
            status: New status

        Returns:
            Updated ticket or None if not found
        """
        updates = {"status": status.value, "updated_at": datetime.now()}

        if status == TicketStatus.DONE:
            updates["completed_at"] = datetime.now()
        elif status == TicketStatus.IN_PROGRESS and not self._has_started(ticket_id):
            # First time starting
            pass

        self.db.update("tickets", updates, "id = ?", (ticket_id,))
        return self.get(ticket_id)

    def delete(self, ticket_id: int) -> bool:
        """
        Delete a ticket.

        Args:
            ticket_id: Ticket to delete

        Returns:
            True if deleted, False if not found
        """
        count = self.db.delete("tickets", "id = ?", (ticket_id,))
        return count > 0

    def add_dependency(
        self,
        ticket_id: int,
        depends_on_id: int,
        dependency_type: str = "blocks",
    ) -> None:
        """
        Add dependency between tickets.

        Args:
            ticket_id: Ticket that depends on another
            depends_on_id: Ticket that must complete first
            dependency_type: Type of dependency
        """
        self.db.insert(
            "ticket_dependencies",
            {
                "ticket_id": ticket_id,
                "depends_on_ticket_id": depends_on_id,
                "dependency_type": dependency_type,
            },
        )

    def remove_dependency(self, ticket_id: int, depends_on_id: int) -> bool:
        """
        Remove dependency between tickets.

        Args:
            ticket_id: Dependent ticket
            depends_on_id: Dependency to remove

        Returns:
            True if removed
        """
        count = self.db.delete(
            "ticket_dependencies",
            "ticket_id = ? AND depends_on_ticket_id = ?",
            (ticket_id, depends_on_id),
        )
        return count > 0

    def get_dependencies(self, ticket_id: int) -> list[TicketDependency]:
        """
        Get all dependencies for a ticket.

        Args:
            ticket_id: Ticket to get dependencies for

        Returns:
            List of dependencies
        """
        rows = self.db.fetch_all(
            "SELECT * FROM ticket_dependencies WHERE ticket_id = ?",
            (ticket_id,),
        )
        return [
            TicketDependency(
                ticket_id=row["ticket_id"],
                depends_on_ticket_id=row["depends_on_ticket_id"],
                dependency_type=row["dependency_type"],
            )
            for row in rows
        ]

    def get_blocking_tickets(self, ticket_id: int) -> list[Ticket]:
        """
        Get tickets that block this ticket.

        Args:
            ticket_id: Ticket to check

        Returns:
            List of blocking tickets
        """
        rows = self.db.fetch_all(
            """
            SELECT t.* FROM tickets t
            JOIN ticket_dependencies td ON t.id = td.depends_on_ticket_id
            WHERE td.ticket_id = ? AND td.dependency_type = 'blocks'
            """,
            (ticket_id,),
        )
        return [self._row_to_ticket(row) for row in rows]

    def has_unmet_dependencies(self, ticket_id: int) -> bool:
        """
        Check if ticket has incomplete blocking dependencies.

        Args:
            ticket_id: Ticket to check

        Returns:
            True if blocked by incomplete tickets
        """
        count = self.db.fetch_one(
            """
            SELECT COUNT(*) FROM ticket_dependencies td
            JOIN tickets t ON t.id = td.depends_on_ticket_id
            WHERE td.ticket_id = ?
            AND td.dependency_type = 'blocks'
            AND t.status NOT IN ('DONE', 'ABANDONED')
            """,
            (ticket_id,),
        )
        return count[0] > 0 if count else False

    def count(
        self,
        status: TicketStatus | None = None,
        ticket_type: TicketType | None = None,
    ) -> int:
        """
        Count tickets with optional filters.

        Args:
            status: Filter by status
            ticket_type: Filter by type

        Returns:
            Count of matching tickets
        """
        conditions = []
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if ticket_type:
            conditions.append("ticket_type = ?")
            params.append(ticket_type.value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return self.db.count("tickets", where_clause, tuple(params))

    def _row_to_ticket(self, row: Any) -> Ticket:
        """Convert database row to Ticket object."""
        data = dict(row)

        # Handle JSON fields
        if data.get("affected_files"):
            data["affected_files"] = json.loads(data["affected_files"])
        else:
            data["affected_files"] = []

        if data.get("metadata"):
            data["metadata"] = json.loads(data["metadata"])
        else:
            data["metadata"] = {}

        return Ticket.from_dict(data)

    def _calculate_priority(self, severity: Severity | None) -> float:
        """Calculate priority score from severity."""
        if not severity:
            return 0.0

        scores = {
            Severity.CRITICAL: 100.0,
            Severity.HIGH: 75.0,
            Severity.MEDIUM: 50.0,
            Severity.LOW: 25.0,
        }
        return scores.get(severity, 0.0)

    def _has_started(self, ticket_id: int) -> bool:
        """Check if ticket has ever been in progress."""
        row = self.db.fetch_one(
            "SELECT 1 FROM execution_log WHERE ticket_id = ? LIMIT 1",
            (ticket_id,),
        )
        return row is not None

    def get_similar_completed_tickets(self, ticket: Ticket, limit: int = 3) -> list[Ticket]:
        """
        Get completed tickets similar to the current one.

        Matches by:
        - Ticket type
        - Overlapping affected files

        Args:
            ticket: The ticket to find similar ones for
            limit: Maximum results

        Returns:
            List of similar completed tickets
        """
        # For now, simple implementation matching type and overlapping files
        # In a real system, this might use semantic search

        # Get all completed tickets of the same type
        rows = self.db.fetch_all(
            "SELECT * FROM tickets WHERE status = ? AND ticket_type = ? AND id != ? ORDER BY completed_at DESC LIMIT 50",
            (TicketStatus.DONE.value, ticket.ticket_type.value, ticket.id),
        )

        if not rows:
            return []

        completed = [self._row_to_ticket(row) for row in rows]

        # Score by file overlap
        scored = []
        target_files = set(ticket.affected_files or [])

        for t in completed:
            score = 1.0  # Base score for same type

            if target_files:
                current_files = set(t.affected_files or [])
                overlap = len(target_files & current_files)
                score += overlap * 2.0

            scored.append((score, t))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]
