"""Topic management for Cascade."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from cascade.models.enums import TicketStatus
from cascade.models.ticket import Ticket
from cascade.models.topic import Topic
from cascade.storage.database import Database


class TopicManager:
    """
    Manages topic CRUD operations and ticket assignments.

    Topics provide logical grouping for tickets by feature area,
    component, or any other organizational scheme.
    """

    def __init__(self, db: Database):
        """
        Initialize topic manager.

        Args:
            db: Database instance
        """
        self.db = db

    def create(self, name: str, description: str = "") -> Topic:
        """
        Create a new topic.

        Args:
            name: Topic name (will be normalized to lowercase kebab-case)
            description: Optional description

        Returns:
            Created topic with ID

        Raises:
            ValueError: If topic with name already exists
        """
        # Normalize name
        normalized_name = name.strip().lower().replace(" ", "-")

        # Check for duplicates
        if self.get_by_name(normalized_name):
            raise ValueError(f"Topic '{normalized_name}' already exists")

        now = datetime.now()
        topic_id = self.db.insert(
            "topics",
            {
                "name": normalized_name,
                "description": description,
                "created_at": now,
            },
        )

        return Topic(
            id=topic_id,
            name=normalized_name,
            description=description,
            created_at=now,
        )

    def get(self, topic_id: int) -> Topic | None:
        """
        Get topic by ID.

        Args:
            topic_id: Topic ID

        Returns:
            Topic or None if not found
        """
        row = self.db.fetch_one("SELECT * FROM topics WHERE id = ?", (topic_id,))
        if not row:
            return None
        return self._row_to_topic(row)

    def get_by_name(self, name: str) -> Topic | None:
        """
        Get topic by name.

        Args:
            name: Topic name (will be normalized)

        Returns:
            Topic or None if not found
        """
        normalized_name = name.strip().lower().replace(" ", "-")
        row = self.db.fetch_one("SELECT * FROM topics WHERE name = ?", (normalized_name,))
        if not row:
            return None
        return self._row_to_topic(row)

    def get_or_create(self, name: str, description: str = "") -> Topic:
        """
        Get existing topic or create new one.

        Args:
            name: Topic name
            description: Description for new topic

        Returns:
            Existing or newly created topic
        """
        existing = self.get_by_name(name)
        if existing:
            return existing
        return self.create(name, description)

    def list_all(self) -> list[Topic]:
        """
        List all topics.

        Returns:
            List of all topics ordered by name
        """
        rows = self.db.fetch_all("SELECT * FROM topics ORDER BY name")
        return [self._row_to_topic(row) for row in rows]

    def update(self, topic_id: int, **updates: Any) -> Topic | None:
        """
        Update topic fields.

        Args:
            topic_id: Topic to update
            **updates: Field names and new values

        Returns:
            Updated topic or None if not found
        """
        if not updates:
            return self.get(topic_id)

        # Normalize name if being updated
        if "name" in updates:
            updates["name"] = updates["name"].strip().lower().replace(" ", "-")

        self.db.update("topics", updates, "id = ?", (topic_id,))
        return self.get(topic_id)

    def delete(self, topic_id: int) -> bool:
        """
        Delete a topic.

        Note: This removes the topic but does not delete assigned tickets.
        Ticket-topic associations are removed via CASCADE.

        Args:
            topic_id: Topic to delete

        Returns:
            True if deleted, False if not found
        """
        count = self.db.delete("topics", "id = ?", (topic_id,))
        return count > 0

    def assign_ticket(self, topic_id: int, ticket_id: int) -> None:
        """
        Assign a ticket to a topic.

        Args:
            topic_id: Topic ID
            ticket_id: Ticket ID

        Raises:
            ValueError: If assignment already exists
        """
        # Check if already assigned
        if self.is_assigned(topic_id, ticket_id):
            return  # Silently ignore duplicate assignment

        self.db.insert(
            "ticket_topics",
            {
                "ticket_id": ticket_id,
                "topic_id": topic_id,
            },
        )

    def unassign_ticket(self, topic_id: int, ticket_id: int) -> bool:
        """
        Remove a ticket from a topic.

        Args:
            topic_id: Topic ID
            ticket_id: Ticket ID

        Returns:
            True if removed, False if not assigned
        """
        count = self.db.delete(
            "ticket_topics",
            "topic_id = ? AND ticket_id = ?",
            (topic_id, ticket_id),
        )
        return count > 0

    def is_assigned(self, topic_id: int, ticket_id: int) -> bool:
        """
        Check if ticket is assigned to topic.

        Args:
            topic_id: Topic ID
            ticket_id: Ticket ID

        Returns:
            True if assigned
        """
        return self.db.exists(
            "ticket_topics",
            "topic_id = ? AND ticket_id = ?",
            (topic_id, ticket_id),
        )

    def get_tickets(
        self,
        topic_id: int,
        status: TicketStatus | None = None,
    ) -> list[Ticket]:
        """
        Get all tickets assigned to a topic.

        Args:
            topic_id: Topic ID
            status: Optional status filter

        Returns:
            List of assigned tickets
        """
        import json

        if status:
            rows = self.db.fetch_all(
                """
                SELECT t.* FROM tickets t
                JOIN ticket_topics tt ON t.id = tt.ticket_id
                WHERE tt.topic_id = ? AND t.status = ?
                ORDER BY t.priority_score DESC
                """,
                (topic_id, status.value),
            )
        else:
            rows = self.db.fetch_all(
                """
                SELECT t.* FROM tickets t
                JOIN ticket_topics tt ON t.id = tt.ticket_id
                WHERE tt.topic_id = ?
                ORDER BY t.priority_score DESC
                """,
                (topic_id,),
            )

        tickets = []
        for row in rows:
            data = dict(row)
            if data.get("affected_files"):
                data["affected_files"] = json.loads(data["affected_files"])
            else:
                data["affected_files"] = []
            if data.get("metadata"):
                data["metadata"] = json.loads(data["metadata"])
            else:
                data["metadata"] = {}
            tickets.append(Ticket.from_dict(data))

        return tickets

    def get_topics_for_ticket(self, ticket_id: int) -> list[Topic]:
        """
        Get all topics a ticket is assigned to.

        Args:
            ticket_id: Ticket ID

        Returns:
            List of topics
        """
        rows = self.db.fetch_all(
            """
            SELECT t.* FROM topics t
            JOIN ticket_topics tt ON t.id = tt.topic_id
            WHERE tt.ticket_id = ?
            ORDER BY t.name
            """,
            (ticket_id,),
        )
        return [self._row_to_topic(row) for row in rows]

    def count_tickets(self, topic_id: int, status: TicketStatus | None = None) -> int:
        """
        Count tickets in a topic.

        Args:
            topic_id: Topic ID
            status: Optional status filter

        Returns:
            Ticket count
        """
        if status:
            result = self.db.fetch_one(
                """
                SELECT COUNT(*) FROM ticket_topics tt
                JOIN tickets t ON t.id = tt.ticket_id
                WHERE tt.topic_id = ? AND t.status = ?
                """,
                (topic_id, status.value),
            )
        else:
            result = self.db.fetch_one(
                "SELECT COUNT(*) FROM ticket_topics WHERE topic_id = ?",
                (topic_id,),
            )
        return result[0] if result else 0

    def get_progress(self, topic_id: int) -> dict[str, Any]:
        """
        Get progress statistics for a topic.

        Args:
            topic_id: Topic ID

        Returns:
            Dict with total, done, in_progress, ready counts
        """
        total = self.count_tickets(topic_id)
        done = self.count_tickets(topic_id, TicketStatus.DONE)
        in_progress = self.count_tickets(topic_id, TicketStatus.IN_PROGRESS)
        ready = self.count_tickets(topic_id, TicketStatus.READY)

        return {
            "total": total,
            "done": done,
            "in_progress": in_progress,
            "ready": ready,
            "percentage": (done / total * 100) if total > 0 else 0,
        }

    def _row_to_topic(self, row: Any) -> Topic:
        """Convert database row to Topic object."""
        return Topic.from_dict(dict(row))
