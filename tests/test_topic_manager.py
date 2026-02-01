"""Tests for TopicManager."""

import shutil
import tempfile
from pathlib import Path

import pytest

from cascade.core.ticket_manager import TicketManager
from cascade.core.topic_manager import TopicManager
from cascade.models.enums import TicketStatus
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
def topic_manager(temp_db):
    """Create a TopicManager with temporary database."""
    return TopicManager(temp_db)


@pytest.fixture
def ticket_manager(temp_db):
    """Create a TicketManager with temporary database."""
    return TicketManager(temp_db)


class TestTopicCreation:
    """Tests for topic creation."""

    def test_create_topic(self, topic_manager):
        """Test creating a basic topic."""
        topic = topic_manager.create("authentication", "User auth features")

        assert topic.id is not None
        assert topic.name == "authentication"
        assert topic.description == "User auth features"

    def test_topic_name_normalized(self, topic_manager):
        """Test that topic names are normalized."""
        topic = topic_manager.create("User Authentication")

        assert topic.name == "user-authentication"

    def test_duplicate_topic_raises_error(self, topic_manager):
        """Test that creating a duplicate topic raises an error."""
        topic_manager.create("auth")

        with pytest.raises(ValueError):
            topic_manager.create("auth")

    def test_get_or_create_existing(self, topic_manager):
        """Test get_or_create returns existing topic."""
        original = topic_manager.create("existing")
        retrieved = topic_manager.get_or_create("existing")

        assert retrieved.id == original.id

    def test_get_or_create_new(self, topic_manager):
        """Test get_or_create creates new topic."""
        topic = topic_manager.get_or_create("new-topic", "Description")

        assert topic.id is not None
        assert topic.name == "new-topic"


class TestTopicRetrieval:
    """Tests for topic retrieval."""

    def test_get_by_id(self, topic_manager):
        """Test getting topic by ID."""
        created = topic_manager.create("test")
        retrieved = topic_manager.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_by_name(self, topic_manager):
        """Test getting topic by name."""
        topic_manager.create("test-topic")
        retrieved = topic_manager.get_by_name("test-topic")

        assert retrieved is not None
        assert retrieved.name == "test-topic"

    def test_get_by_name_normalized(self, topic_manager):
        """Test that get_by_name normalizes the name."""
        topic_manager.create("test-topic")
        retrieved = topic_manager.get_by_name("Test Topic")

        assert retrieved is not None
        assert retrieved.name == "test-topic"

    def test_list_all(self, topic_manager):
        """Test listing all topics."""
        topic_manager.create("alpha")
        topic_manager.create("beta")
        topic_manager.create("gamma")

        topics = topic_manager.list_all()

        assert len(topics) == 3
        # Should be sorted by name
        assert topics[0].name == "alpha"
        assert topics[1].name == "beta"
        assert topics[2].name == "gamma"


class TestTopicTicketAssignment:
    """Tests for ticket-topic assignment."""

    def test_assign_ticket(self, topic_manager, ticket_manager):
        """Test assigning a ticket to a topic."""
        topic = topic_manager.create("auth")
        ticket = ticket_manager.create(title="Login feature")

        topic_manager.assign_ticket(topic.id, ticket.id)

        assert topic_manager.is_assigned(topic.id, ticket.id) is True

    def test_unassign_ticket(self, topic_manager, ticket_manager):
        """Test removing a ticket from a topic."""
        topic = topic_manager.create("auth")
        ticket = ticket_manager.create(title="Login feature")

        topic_manager.assign_ticket(topic.id, ticket.id)
        topic_manager.unassign_ticket(topic.id, ticket.id)

        assert topic_manager.is_assigned(topic.id, ticket.id) is False

    def test_get_tickets_in_topic(self, topic_manager, ticket_manager):
        """Test getting all tickets in a topic."""
        topic = topic_manager.create("auth")
        ticket1 = ticket_manager.create(title="Login")
        ticket2 = ticket_manager.create(title="Logout")
        ticket3 = ticket_manager.create(title="Unrelated")

        topic_manager.assign_ticket(topic.id, ticket1.id)
        topic_manager.assign_ticket(topic.id, ticket2.id)

        tickets = topic_manager.get_tickets(topic.id)

        assert len(tickets) == 2
        ticket_ids = [t.id for t in tickets]
        assert ticket1.id in ticket_ids
        assert ticket2.id in ticket_ids
        assert ticket3.id not in ticket_ids

    def test_get_tickets_filtered_by_status(self, topic_manager, ticket_manager):
        """Test filtering tickets in a topic by status."""
        topic = topic_manager.create("auth")
        ticket1 = ticket_manager.create(title="Login")
        ticket2 = ticket_manager.create(title="Logout")

        topic_manager.assign_ticket(topic.id, ticket1.id)
        topic_manager.assign_ticket(topic.id, ticket2.id)

        ticket_manager.update_status(ticket1.id, TicketStatus.DONE)

        done_tickets = topic_manager.get_tickets(topic.id, status=TicketStatus.DONE)
        defined_tickets = topic_manager.get_tickets(topic.id, status=TicketStatus.DEFINED)

        assert len(done_tickets) == 1
        assert len(defined_tickets) == 1

    def test_get_topics_for_ticket(self, topic_manager, ticket_manager):
        """Test getting all topics a ticket is assigned to."""
        topic1 = topic_manager.create("auth")
        topic2 = topic_manager.create("security")
        ticket = ticket_manager.create(title="Auth feature")

        topic_manager.assign_ticket(topic1.id, ticket.id)
        topic_manager.assign_ticket(topic2.id, ticket.id)

        topics = topic_manager.get_topics_for_ticket(ticket.id)

        assert len(topics) == 2
        topic_names = [t.name for t in topics]
        assert "auth" in topic_names
        assert "security" in topic_names


class TestTopicProgress:
    """Tests for topic progress tracking."""

    def test_count_tickets(self, topic_manager, ticket_manager):
        """Test counting tickets in a topic."""
        topic = topic_manager.create("feature")
        ticket1 = ticket_manager.create(title="Task 1")
        ticket2 = ticket_manager.create(title="Task 2")

        topic_manager.assign_ticket(topic.id, ticket1.id)
        topic_manager.assign_ticket(topic.id, ticket2.id)

        assert topic_manager.count_tickets(topic.id) == 2

    def test_get_progress(self, topic_manager, ticket_manager):
        """Test getting progress statistics."""
        topic = topic_manager.create("feature")
        ticket1 = ticket_manager.create(title="Task 1")
        ticket2 = ticket_manager.create(title="Task 2")
        ticket3 = ticket_manager.create(title="Task 3")
        ticket4 = ticket_manager.create(title="Task 4")

        topic_manager.assign_ticket(topic.id, ticket1.id)
        topic_manager.assign_ticket(topic.id, ticket2.id)
        topic_manager.assign_ticket(topic.id, ticket3.id)
        topic_manager.assign_ticket(topic.id, ticket4.id)

        # Mark some as done
        ticket_manager.update_status(ticket1.id, TicketStatus.DONE)
        ticket_manager.update_status(ticket2.id, TicketStatus.DONE)
        ticket_manager.update_status(ticket3.id, TicketStatus.IN_PROGRESS)

        progress = topic_manager.get_progress(topic.id)

        assert progress["total"] == 4
        assert progress["done"] == 2
        assert progress["in_progress"] == 1
        assert progress["percentage"] == 50.0


class TestTopicDeletion:
    """Tests for topic deletion."""

    def test_delete_topic(self, topic_manager):
        """Test deleting a topic."""
        topic = topic_manager.create("to-delete")
        assert topic_manager.get(topic.id) is not None

        result = topic_manager.delete(topic.id)

        assert result is True
        assert topic_manager.get(topic.id) is None

    def test_delete_topic_removes_assignments(self, topic_manager, ticket_manager):
        """Test that deleting a topic removes ticket assignments."""
        topic = topic_manager.create("to-delete")
        ticket = ticket_manager.create(title="Test")
        topic_manager.assign_ticket(topic.id, ticket.id)

        topic_manager.delete(topic.id)

        # Ticket should still exist but not be assigned to deleted topic
        assert ticket_manager.get(ticket.id) is not None
        topics = topic_manager.get_topics_for_ticket(ticket.id)
        assert len(topics) == 0
