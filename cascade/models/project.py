"""Project configuration model for Cascade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class QualityGateConfig(BaseModel):
    """Configuration for a quality gate."""

    enabled: bool = True
    fail_on_error: bool = True
    tools: dict[str, str] = Field(default_factory=dict)
    command: str | None = None
    min_coverage: int | None = None
    fail_on_critical: bool = True
    fail_on_high: bool = False


class QualityConfig(BaseModel):
    """Quality gates configuration."""

    static_analysis: QualityGateConfig = Field(default_factory=QualityGateConfig)
    unit_tests: QualityGateConfig = Field(default_factory=QualityGateConfig)
    security_scan: QualityGateConfig = Field(default_factory=QualityGateConfig)
    max_gate_retries: int = 3


class ContextConfig(BaseModel):
    """Context loading configuration."""

    default_mode: str = "minimal"
    max_tokens: dict[str, int] = Field(
        default_factory=lambda: {"minimal": 2000, "standard": 5000, "full": 10000}
    )


class ProjectAgentConfig(BaseModel):
    """Agent configuration."""

    default: str = "claude-code"
    fallback: str = "generic"
    orchestration: dict[str, str] = Field(default_factory=dict)
    configurations: dict[str, dict[str, str]] = Field(default_factory=dict)


class ConstraintsConfig(BaseModel):
    """System constraints."""

    max_gate_retries: int = 3
    max_open_tickets: int = 100
    max_blocking_depth: int = 3


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: str = ".cascade/logs/cascade.log"


class ProjectConfig(BaseModel):
    """
    Complete project configuration.

    Loaded from .cascade/config.yaml in the project root.
    """

    name: str = ""
    description: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    agent: ProjectAgentConfig = Field(default_factory=ProjectAgentConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, config_path: Path) -> ProjectConfig:
        """Load configuration from YAML file."""
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ProjectConfig:
        """Create config from dictionary with legacy support."""
        # Map legacy top-level keys if they exist
        project_data = data.get("project", {})
        agent_data = data.get("agent", {})
        context_data = data.get("context", {})
        quality_data = data.get("quality_gates", {})
        constraints_data = data.get("constraints", {})
        logging_data = data.get("logging", {})

        # Build nested data for Pydantic
        config_data = {
            "name": project_data.get("name", ""),
            "description": project_data.get("description", ""),
            "tech_stack": project_data.get("tech_stack", []),
            "agent": agent_data,
            "context": context_data,
            "quality": {
                "static_analysis": quality_data.get("static_analysis", {}),
                "unit_tests": quality_data.get("unit_tests", {}),
                "security_scan": quality_data.get("security_scan", {}),
                "max_gate_retries": constraints_data.get("max_gate_retries", 3),
            },
            "constraints": constraints_data,
            "logging": logging_data,
        }

        # Filter out empty dicts so Pydantic uses defaults
        def clean(d: Any) -> Any:
            if not isinstance(d, dict):
                return d
            return {k: clean(v) for k, v in d.items() if v is not None}

        return cls.model_validate(clean(config_data))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization (maintaining legacy structure)."""
        model_dict = self.model_dump()
        return {
            "project": {
                "name": self.name,
                "description": self.description,
                "tech_stack": self.tech_stack,
            },
            "agent": model_dict["agent"],
            "context": model_dict["context"],
            "quality_gates": {
                "static_analysis": model_dict["quality"]["static_analysis"],
                "unit_tests": model_dict["quality"]["unit_tests"],
                "security_scan": model_dict["quality"]["security_scan"],
            },
            "constraints": model_dict["constraints"],
            "logging": model_dict["logging"],
        }

    def save(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
