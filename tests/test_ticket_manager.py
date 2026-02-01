"""Tests for TicketManager."""

import shutil
import tempfile
from pathlib import Path

import pytest

from cascade.core.ticket_manager import TicketManager
from cascade.models.enums import Severity, TicketStatus, TicketType
from cascade.storage.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    db = Database(db_path)
    db.initialize()
    yield db
    shutil.rmtree(temp_dir)


@pytest.fixture
def ticket_manager(temp_db):
    """Create a TicketManager with temporary database."""
    return TicketManager(temp_db)


class TestTicketCreation:
    """Tests for ticket creation."""

    def test_create_basic_ticket(self, ticket_manager):
        """Test creating a basic ticket."""
        ticket = ticket_manager.create(
            title="Test ticket",
            ticket_type=TicketType.TASK,
        )

        assert ticket.id is not None
        assert ticket.title == "Test ticket"
        assert ticket.ticket_type == TicketType.TASK
        assert ticket.status == TicketStatus.DEFINED

    def test_create_ticket_with_all_fields(self, ticket_manager):
        """Test creating a ticket with all fields."""
        ticket = ticket_manager.create(
            title="Full ticket",
            ticket_type=TicketType.BUG,
            description="A bug description",
            severity=Severity.HIGH,
            acceptance_criteria="Bug is fixed",
            affected_files=["src/main.py", "tests/test_main.py"],
            estimated_effort=5,
        )

        assert ticket.title == "Full ticket"
        assert ticket.ticket_type == TicketType.BUG
        assert ticket.description == "A bug description"
        assert ticket.severity == Severity.HIGH
        assert ticket.acceptance_criteria == "Bug is fixed"
        assert ticket.affected_files == ["src/main.py", "tests/test_main.py"]
        assert ticket.estimated_effort == 5

    def test_priority_calculated_from_severity(self, ticket_manager):
        """Test that priority score is calculated from severity."""
        critical = ticket_manager.create(title="Critical", severity=Severity.CRITICAL)
        high = ticket_manager.create(title="High", severity=Severity.HIGH)
        medium = ticket_manager.create(title="Medium", severity=Severity.MEDIUM)
        low = ticket_manager.create(title="Low", severity=Severity.LOW)

        assert critical.priority_score > high.priority_score
        assert high.priority_score > medium.priority_score
        assert medium.priority_score > low.priority_score


class TestTicketRetrieval:
    """Tests for ticket retrieval."""

    def test_get_ticket_by_id(self, ticket_manager):
        """Test getting a ticket by ID."""
        created = ticket_manager.create(title="Test")
        retrieved = ticket_manager.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_nonexistent_ticket(self, ticket_manager):
        """Test getting a ticket that doesn't exist."""
        result = ticket_manager.get(99999)
        assert result is None

    def test_get_by_status(self, ticket_manager):
        """Test getting tickets by status."""
        ticket_manager.create(title="Defined 1")
        ticket_manager.create(title="Defined 2")

        ready = ticket_manager.create(title="Ready")
        ticket_manager.update_status(ready.id, TicketStatus.READY)

        defined_tickets = ticket_manager.get_by_status(TicketStatus.DEFINED)
        ready_tickets = ticket_manager.get_by_status(TicketStatus.READY)

        assert len(defined_tickets) == 2
        assert len(ready_tickets) == 1

    def test_get_by_type(self, ticket_manager):
        """Test getting tickets by type."""
        ticket_manager.create(title="Task 1", ticket_type=TicketType.TASK)
        ticket_manager.create(title="Task 2", ticket_type=TicketType.TASK)
        ticket_manager.create(title="Bug", ticket_type=TicketType.BUG)

        tasks = ticket_manager.get_by_type(TicketType.TASK)
        bugs = ticket_manager.get_by_type(TicketType.BUG)

        assert len(tasks) == 2
        assert len(bugs) == 1


class TestTicketUpdate:
    """Tests for ticket updates."""

    def test_update_ticket_fields(self, ticket_manager):
        """Test updating ticket fields."""
        ticket = ticket_manager.create(title="Original")

        updated = ticket_manager.update(
            ticket.id,
            title="Updated",
            description="New description",
        )

        assert updated.title == "Updated"
        assert updated.description == "New description"

    def test_update_status(self, ticket_manager):
        """Test updating ticket status."""
        ticket = ticket_manager.create(title="Test")

        updated = ticket_manager.update_status(ticket.id, TicketStatus.READY)
        assert updated.status == TicketStatus.READY

        updated = ticket_manager.update_status(ticket.id, TicketStatus.IN_PROGRESS)
        assert updated.status == TicketStatus.IN_PROGRESS

    def test_completed_at_set_on_done(self, ticket_manager):
        """Test that completed_at is set when status becomes DONE."""
        ticket = ticket_manager.create(title="Test")
        assert ticket.completed_at is None

        updated = ticket_manager.update_status(ticket.id, TicketStatus.DONE)
        assert updated.completed_at is not None


class TestTicketDeletion:
    """Tests for ticket deletion."""

    def test_delete_ticket(self, ticket_manager):
        """Test deleting a ticket."""
        ticket = ticket_manager.create(title="To delete")
        assert ticket_manager.get(ticket.id) is not None

        result = ticket_manager.delete(ticket.id)
        assert result is True
        assert ticket_manager.get(ticket.id) is None

    def test_delete_nonexistent_ticket(self, ticket_manager):
        """Test deleting a ticket that doesn't exist."""
        result = ticket_manager.delete(99999)
        assert result is False


class TestTicketDependencies:
    """Tests for ticket dependencies."""

    def test_add_dependency(self, ticket_manager):
        """Test adding a dependency between tickets."""
        ticket1 = ticket_manager.create(title="Dependent")
        ticket2 = ticket_manager.create(title="Blocker")

        ticket_manager.add_dependency(ticket1.id, ticket2.id)

        deps = ticket_manager.get_dependencies(ticket1.id)
        assert len(deps) == 1
        assert deps[0].depends_on_ticket_id == ticket2.id

    def test_has_unmet_dependencies(self, ticket_manager):
        """Test checking for unmet dependencies."""
        ticket1 = ticket_manager.create(title="Dependent")
        ticket2 = ticket_manager.create(title="Blocker")

        ticket_manager.add_dependency(ticket1.id, ticket2.id)

        # Ticket2 is not done, so ticket1 has unmet dependencies
        assert ticket_manager.has_unmet_dependencies(ticket1.id) is True

        # Complete ticket2
        ticket_manager.update_status(ticket2.id, TicketStatus.DONE)

        # Now ticket1 has no unmet dependencies
        assert ticket_manager.has_unmet_dependencies(ticket1.id) is False

    def test_get_blocking_tickets(self, ticket_manager):
        """Test getting tickets that block another ticket."""
        ticket1 = ticket_manager.create(title="Dependent")
        ticket2 = ticket_manager.create(title="Blocker 1")
        ticket3 = ticket_manager.create(title="Blocker 2")

        ticket_manager.add_dependency(ticket1.id, ticket2.id)
        ticket_manager.add_dependency(ticket1.id, ticket3.id)

        blocking = ticket_manager.get_blocking_tickets(ticket1.id)
        assert len(blocking) == 2


class TestTicketQueries:
    """Tests for ticket queries."""

    def test_list_all_with_limit(self, ticket_manager):
        """Test listing tickets with limit."""
        for i in range(10):
            ticket_manager.create(title=f"Ticket {i}")

        limited = ticket_manager.list_all(limit=5)
        assert len(limited) == 5

    def test_count_tickets(self, ticket_manager):
        """Test counting tickets."""
        ticket_manager.create(title="Task 1", ticket_type=TicketType.TASK)
        ticket_manager.create(title="Task 2", ticket_type=TicketType.TASK)
        ticket_manager.create(title="Bug", ticket_type=TicketType.BUG)

        total = ticket_manager.count()
        tasks = ticket_manager.count(ticket_type=TicketType.TASK)
        bugs = ticket_manager.count(ticket_type=TicketType.BUG)

        assert total == 3
        assert tasks == 2
        assert bugs == 1

    def test_get_next_ready(self, ticket_manager):
        """Test getting the highest priority ready ticket."""
        low = ticket_manager.create(title="Low", severity=Severity.LOW)
        high = ticket_manager.create(title="High", severity=Severity.HIGH)

        ticket_manager.update_status(low.id, TicketStatus.READY)
        ticket_manager.update_status(high.id, TicketStatus.READY)

        next_ticket = ticket_manager.get_next_ready()
        assert next_ticket.id == high.id  # High priority comes first
