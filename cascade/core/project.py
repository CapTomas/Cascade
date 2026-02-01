"""Project management and initialization for Cascade."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cascade.agents.registry import get_agent
from cascade.core.context_builder import ContextBuilder
from cascade.core.knowledge_base import KnowledgeBase
from cascade.core.metrics import MetricsService
from cascade.core.planner import Planner
from cascade.core.prompt_builder import PromptBuilder
from cascade.core.quality_gates import QualityGates
from cascade.core.ticket_manager import TicketManager
from cascade.core.topic_manager import TopicManager
from cascade.models.project import ProjectConfig
from cascade.storage.database import Database, get_database

logger = logging.getLogger(__name__)


class CascadeProject:
    """
    Main entry point for Cascade project operations.

    Provides access to all managers and handles project initialization,
    configuration loading, and service coordination.
    """

    CASCADE_DIR = ".cascade"
    CONFIG_FILE = "config.yaml"
    CONVENTIONS_FILE = "conventions.yaml"
    DB_FILE = "cascade.db"

    def __init__(self, project_root: Path | None = None):
        """
        Initialize Cascade project.

        Args:
            project_root: Project root directory. If None, searches upward
                          from cwd for existing .cascade directory.
        """
        self._root = project_root or self._find_project_root()
        self._config: ProjectConfig | None = None
        self._db: Database | None = None
        self._tickets: TicketManager | None = None
        self._topics: TopicManager | None = None
        self._kb: KnowledgeBase | None = None
        self._quality_gates: QualityGates | None = None
        self._context_builder: ContextBuilder | None = None
        self._prompt_builder: PromptBuilder | None = None
        self._planner: Planner | None = None
        self._metrics: MetricsService | None = None

    @property
    def root(self) -> Path:
        """Get project root directory."""
        return self._root

    @property
    def cascade_dir(self) -> Path:
        """Get .cascade directory path."""
        return self._root / self.CASCADE_DIR

    @property
    def config_path(self) -> Path:
        """Get config file path."""
        return self.cascade_dir / self.CONFIG_FILE

    @property
    def conventions_path(self) -> Path:
        """Get conventions file path."""
        return self.cascade_dir / self.CONVENTIONS_FILE

    @property
    def db_path(self) -> Path:
        """Get database file path."""
        return self.cascade_dir / self.DB_FILE

    @property
    def is_initialized(self) -> bool:
        """Check if project has been initialized."""
        return self.cascade_dir.exists() and self.db_path.exists()

    @property
    def config(self) -> ProjectConfig:
        """Get project configuration (lazy loaded)."""
        if self._config is None:
            self._config = ProjectConfig.load(self.config_path)
        return self._config

    @property
    def db(self) -> Database:
        """Get database instance (lazy loaded)."""
        if self._db is None:
            self._db = get_database(self._root)
        return self._db

    @property
    def tickets(self) -> TicketManager:
        """Get ticket manager (lazy loaded)."""
        if self._tickets is None:
            self._tickets = TicketManager(self.db)
        return self._tickets

    @property
    def topics(self) -> TopicManager:
        """Get topic manager (lazy loaded)."""
        if self._topics is None:
            self._topics = TopicManager(self.db)
        return self._topics

    @property
    def kb(self) -> KnowledgeBase:
        """Get knowledge base (lazy loaded)."""
        if self._kb is None:
            self._kb = KnowledgeBase(self.db)
        return self._kb

    @property
    def quality_gates(self) -> QualityGates:
        """Get quality gates manager (lazy loaded)."""
        if self._quality_gates is None:
            self._quality_gates = QualityGates(self.config, self._root)
        return self._quality_gates

    @property
    def context_builder(self) -> ContextBuilder:
        """Get context builder (lazy loaded)."""
        if self._context_builder is None:
            self._context_builder = ContextBuilder(self.kb, self.tickets)
        return self._context_builder

    @property
    def prompt_builder(self) -> PromptBuilder:
        """Get prompt builder (lazy loaded)."""
        if self._prompt_builder is None:
            self._prompt_builder = PromptBuilder()
        return self._prompt_builder

    @property
    def planner(self) -> Planner:
        """Get planner (lazy loaded)."""
        if self._planner is None:
            agent = get_agent(self.config.agent.default)
            self._planner = Planner(
                agent=agent,
                prompt_builder=self.prompt_builder,
                ticket_manager=self.tickets,
                topic_manager=self.topics,
                knowledge_base=self.kb,
            )
        return self._planner

    @property
    def metrics(self) -> MetricsService:
        """Get metrics service (lazy loaded)."""
        if self._metrics is None:
            self._metrics = MetricsService(self.db)
        return self._metrics

    def initialize(
        self,
        name: str = "",
        description: str = "",
        tech_stack: list[str] | None = None,
    ) -> None:
        """
        Initialize a new Cascade project.

        Creates .cascade directory, database, and default configuration.

        Args:
            name: Project name
            description: Project description
            tech_stack: List of technologies used

        Raises:
            ValueError: If project already initialized
        """
        if self.is_initialized:
            raise ValueError(f"Cascade project already initialized at {self._root}")

        # Create directories
        self.cascade_dir.mkdir(parents=True, exist_ok=True)
        (self.cascade_dir / "logs").mkdir(exist_ok=True)

        # Initialize database
        self.db.initialize()

        # Create default configuration
        self._config = ProjectConfig(
            name=name or self._root.name,
            description=description,
            tech_stack=tech_stack or [],
        )
        self._config.save(self.config_path)

        # Create empty conventions file
        self._create_default_conventions()

        logger.info(f"Initialized Cascade project at {self._root}")

    def _create_default_conventions(self) -> None:
        """Create default conventions file."""
        import yaml

        default_conventions = {
            "naming": {
                "description": "Naming conventions for the project",
            },
            "style": {
                "description": "Code style preferences",
            },
            "structure": {
                "description": "Project structure guidelines",
            },
            "security": {
                "description": "Security requirements",
            },
        }

        with open(self.conventions_path, "w") as f:
            yaml.dump(default_conventions, f, default_flow_style=False)

    def _find_project_root(self) -> Path:
        """
        Find project root by searching upward for .cascade directory.

        Returns:
            Project root path (current directory if not found)
        """
        current = Path.cwd()

        while current != current.parent:
            if (current / self.CASCADE_DIR).exists():
                return current
            current = current.parent

        # Not found, use current directory
        return Path.cwd()

    def reload_config(self) -> None:
        """Reload configuration from disk."""
        self._config = ProjectConfig.load(self.config_path)

    def save_config(self) -> None:
        """Save current configuration to disk."""
        self.config.save(self.config_path)

    def get_status(self) -> dict[str, Any]:
        """
        Get project status summary.

        Returns:
            Dict with ticket counts by status
        """
        from cascade.models.enums import TicketStatus

        return {
            "name": self.config.name,
            "root": str(self._root),
            "tickets": {
                "total": self.tickets.count(),
                "ready": self.tickets.count(status=TicketStatus.READY),
                "in_progress": self.tickets.count(status=TicketStatus.IN_PROGRESS),
                "done": self.tickets.count(status=TicketStatus.DONE),
                "blocked": self.tickets.count(status=TicketStatus.BLOCKED),
            },
            "topics": len(self.topics.list_all()),
        }


def get_project(project_root: Path | None = None) -> CascadeProject:
    """
    Get Cascade project instance.

    Args:
        project_root: Optional explicit project root

    Returns:
        CascadeProject instance

    Raises:
        FileNotFoundError: If no Cascade project found
    """
    project = CascadeProject(project_root)

    if not project.is_initialized and project_root is None:
        raise FileNotFoundError("No Cascade project found. Run 'cascade init' to initialize.")

    return project


def find_project_root() -> Path | None:
    """
    Find the nearest Cascade project root.

    Searches upward from current directory.

    Returns:
        Project root path or None if not found
    """
    current = Path.cwd()

    while current != current.parent:
        if (current / CascadeProject.CASCADE_DIR).exists():
            return current
        current = current.parent

    return None
