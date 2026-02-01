"""Shared pytest fixtures for Cascade tests."""

import shutil
import tempfile
from pathlib import Path

import pytest

from cascade.core.knowledge_base import KnowledgeBase
from cascade.core.ticket_manager import TicketManager
from cascade.core.topic_manager import TopicManager
from cascade.storage.database import Database


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def temp_db(temp_dir):
    """Create a temporary database for testing."""
    db_path = temp_dir / "test.db"
    db = Database(db_path)
    db.initialize()
    return db


@pytest.fixture
def ticket_manager(temp_db):
    """Create a TicketManager with temporary database."""
    return TicketManager(temp_db)


@pytest.fixture
def topic_manager(temp_db):
    """Create a TopicManager with temporary database."""
    return TopicManager(temp_db)


@pytest.fixture
def knowledge_base(temp_db, temp_dir):
    """Create a KnowledgeBase with temporary database."""
    conventions_path = temp_dir / "conventions.yaml"
    return KnowledgeBase(temp_db, conventions_path)
