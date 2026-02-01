from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cascade.models.enums import KnowledgeStatus


@dataclass
class ADR:
    """
    Architecture Decision Record.

    ADRs capture important architectural decisions with context and rationale.
    They are proposed by AI during execution and approved by humans.
    Only approved ADRs are loaded into context.
    """

    id: int | None = None
    adr_number: int = 0
    title: str = ""
    status: KnowledgeStatus = KnowledgeStatus.PROPOSED
    context: str = ""  # Why was this decision needed?
    decision: str = ""  # What was decided?
    rationale: str = ""  # Why this decision?
    consequences: str = ""  # What are the implications?
    alternatives_considered: str = ""  # What else was considered?
    created_by_ticket_id: int | None = None
    created_at: datetime | None = None
    approved_at: datetime | None = None

    def __post_init__(self) -> None:
        """Normalize enum values."""
        if isinstance(self.status, str):
            self.status = KnowledgeStatus(self.status)

    @property
    def is_approved(self) -> bool:
        """Check if ADR is approved for use in context."""
        return self.status == KnowledgeStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "adr_number": self.adr_number,
            "title": self.title,
            "status": self.status.value,
            "context": self.context,
            "decision": self.decision,
            "rationale": self.rationale,
            "consequences": self.consequences,
            "alternatives_considered": self.alternatives_considered,
            "created_by_ticket_id": self.created_by_ticket_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ADR:
        """Create ADR from dictionary."""
        for field_name in ("created_at", "approved_at"):
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])
        return cls(**data)

    def to_context_string(self) -> str:
        """Format ADR for inclusion in agent context."""
        return f"""### ADR-{self.adr_number}: {self.title}
**Context:** {self.context}
**Decision:** {self.decision}
**Rationale:** {self.rationale}
"""


@dataclass
class Pattern:
    """
    Reusable code pattern.

    Patterns capture successful implementations that can be reused.
    They are proposed by AI and approved by humans.
    """

    id: int | None = None
    pattern_name: str = ""
    description: str = ""
    code_template: str = ""
    applies_to_tags: list[str] = field(default_factory=list)
    learned_from_ticket_id: int | None = None
    status: KnowledgeStatus = KnowledgeStatus.PROPOSED
    reuse_count: int = 0
    file_examples: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    approved_at: datetime | None = None

    def __post_init__(self) -> None:
        """Normalize enum values."""
        if isinstance(self.status, str):
            self.status = KnowledgeStatus(self.status)

    @property
    def is_approved(self) -> bool:
        """Check if pattern is approved for use in context."""
        return self.status == KnowledgeStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "pattern_name": self.pattern_name,
            "description": self.description,
            "code_template": self.code_template,
            "applies_to_tags": self.applies_to_tags,
            "learned_from_ticket_id": self.learned_from_ticket_id,
            "status": self.status.value,
            "reuse_count": self.reuse_count,
            "file_examples": self.file_examples,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Pattern:
        """Create pattern from dictionary."""
        import json

        for field_name in ("created_at", "approved_at"):
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])

        # Handle JSON string fields
        for field_name in ("applies_to_tags", "file_examples"):
            if isinstance(data.get(field_name), str):
                data[field_name] = json.loads(data[field_name])

        return cls(**data)

    def to_context_string(self) -> str:
        """Format pattern for inclusion in agent context."""
        return f"""### Pattern: {self.pattern_name}
**Description:** {self.description}
**Tags:** {", ".join(self.applies_to_tags)}

```
{self.code_template}
```
"""


@dataclass
class Convention:
    """
    Project convention (code style, naming, structure rules).

    Conventions are lightweight rules always included in context.
    They are stored in the database but also exported to a
    human-readable YAML file.
    """

    id: int | None = None
    category: str = ""  # 'naming', 'style', 'structure', 'security'
    convention_key: str = ""
    convention_value: str = ""
    rationale: str = ""
    priority: int = 0  # Higher = load first
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "category": self.category,
            "convention_key": self.convention_key,
            "convention_value": self.convention_value,
            "rationale": self.rationale,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Convention:
        """Create convention from dictionary."""
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
