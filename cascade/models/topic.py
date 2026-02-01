"""Topic models for Cascade."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Topic:
    """
    Represents a logical grouping of tickets.

    Topics organize tickets by feature area, component, or any other
    logical grouping. A ticket can belong to multiple topics.
    """

    id: int | None = None
    name: str = ""
    description: str = ""
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Normalize topic name."""
        self.name = self.name.strip().lower().replace(" ", "-")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Topic:
        """Create topic from dictionary."""
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
