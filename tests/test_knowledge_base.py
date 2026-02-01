"""Tests for KnowledgeBase."""

from cascade.models.enums import KnowledgeStatus


class TestConventions:
    """Tests for convention management."""

    def test_add_convention(self, knowledge_base):
        """Test adding a convention."""
        conv = knowledge_base.add_convention(
            category="naming",
            key="variables",
            value="camelCase",
            rationale="Consistency",
        )

        assert conv.id is not None
        assert conv.category == "naming"
        assert conv.convention_key == "variables"
        assert conv.convention_value == "camelCase"

    def test_get_convention(self, knowledge_base):
        """Test getting a specific convention."""
        knowledge_base.add_convention("naming", "variables", "camelCase")

        conv = knowledge_base.get_convention("naming", "variables")

        assert conv is not None
        assert conv.convention_value == "camelCase"

    def test_update_existing_convention(self, knowledge_base):
        """Test that adding a duplicate convention updates it."""
        knowledge_base.add_convention("naming", "variables", "camelCase")
        knowledge_base.add_convention("naming", "variables", "snake_case")

        conv = knowledge_base.get_convention("naming", "variables")

        assert conv.convention_value == "snake_case"

    def test_get_all_conventions(self, knowledge_base):
        """Test getting all conventions."""
        knowledge_base.add_convention("naming", "variables", "camelCase")
        knowledge_base.add_convention("naming", "functions", "camelCase")
        knowledge_base.add_convention("style", "indentation", "2 spaces")

        all_convs = knowledge_base.get_conventions()

        assert len(all_convs) == 3

    def test_get_conventions_by_category(self, knowledge_base):
        """Test filtering conventions by category."""
        knowledge_base.add_convention("naming", "variables", "camelCase")
        knowledge_base.add_convention("naming", "functions", "camelCase")
        knowledge_base.add_convention("style", "indentation", "2 spaces")

        naming_convs = knowledge_base.get_conventions("naming")

        assert len(naming_convs) == 2
        assert all(c.category == "naming" for c in naming_convs)

    def test_delete_convention(self, knowledge_base):
        """Test deleting a convention."""
        knowledge_base.add_convention("naming", "variables", "camelCase")

        result = knowledge_base.delete_convention("naming", "variables")

        assert result is True
        assert knowledge_base.get_convention("naming", "variables") is None

    def test_sync_to_yaml(self, knowledge_base):
        """Test exporting conventions to YAML."""
        knowledge_base.add_convention("naming", "variables", "camelCase")
        knowledge_base.add_convention("style", "indentation", "2 spaces")

        knowledge_base.sync_conventions_to_yaml()

        assert knowledge_base.conventions_path.exists()
        content = knowledge_base.conventions_path.read_text()
        assert "camelCase" in content


class TestPatterns:
    """Tests for pattern management."""

    def test_propose_pattern(self, knowledge_base):
        """Test proposing a new pattern."""
        pattern = knowledge_base.propose_pattern(
            pattern_name="repository-pattern",
            description="Data access abstraction",
            code_template="class Repository:\n    pass",
            applies_to_tags=["data", "persistence"],
        )

        assert pattern.id is not None
        assert pattern.status == KnowledgeStatus.PROPOSED
        assert pattern.reuse_count == 0

    def test_get_pattern(self, knowledge_base):
        """Test getting a pattern by ID."""
        created = knowledge_base.propose_pattern(
            pattern_name="test-pattern",
            description="Test",
        )

        retrieved = knowledge_base.get_pattern(created.id)

        assert retrieved is not None
        assert retrieved.pattern_name == "test-pattern"

    def test_approve_pattern(self, knowledge_base):
        """Test approving a pattern."""
        pattern = knowledge_base.propose_pattern(
            pattern_name="test",
            description="Test",
        )

        approved = knowledge_base.approve_pattern(pattern.id)

        assert approved.status == KnowledgeStatus.APPROVED
        assert approved.approved_at is not None

    def test_reject_pattern(self, knowledge_base):
        """Test rejecting a pattern."""
        pattern = knowledge_base.propose_pattern(
            pattern_name="test",
            description="Test",
        )

        rejected = knowledge_base.reject_pattern(pattern.id)

        assert rejected.status == KnowledgeStatus.REJECTED

    def test_get_patterns_by_status(self, knowledge_base):
        """Test filtering patterns by status."""
        p1 = knowledge_base.propose_pattern("pattern1", "Test 1")
        knowledge_base.propose_pattern("pattern2", "Test 2")
        knowledge_base.approve_pattern(p1.id)

        proposed = knowledge_base.get_patterns(status=KnowledgeStatus.PROPOSED)
        approved = knowledge_base.get_patterns(status=KnowledgeStatus.APPROVED)

        assert len(proposed) == 1
        assert len(approved) == 1

    def test_increment_usage(self, knowledge_base):
        """Test incrementing pattern usage count."""
        pattern = knowledge_base.propose_pattern("test", "Test")

        knowledge_base.increment_pattern_usage(pattern.id)
        knowledge_base.increment_pattern_usage(pattern.id)

        updated = knowledge_base.get_pattern(pattern.id)
        assert updated.reuse_count == 2


class TestADRs:
    """Tests for ADR management."""

    def test_propose_adr(self, knowledge_base):
        """Test proposing a new ADR."""
        adr = knowledge_base.propose_adr(
            title="Use PostgreSQL for persistence",
            context="We need a database",
            decision="Use PostgreSQL",
            rationale="ACID compliance, JSON support",
        )

        assert adr.id is not None
        assert adr.adr_number == 1
        assert adr.status == KnowledgeStatus.PROPOSED

    def test_adr_numbers_increment(self, knowledge_base):
        """Test that ADR numbers auto-increment."""
        adr1 = knowledge_base.propose_adr("ADR 1", "ctx", "dec", "rat")
        adr2 = knowledge_base.propose_adr("ADR 2", "ctx", "dec", "rat")
        adr3 = knowledge_base.propose_adr("ADR 3", "ctx", "dec", "rat")

        assert adr1.adr_number == 1
        assert adr2.adr_number == 2
        assert adr3.adr_number == 3

    def test_get_adr_by_number(self, knowledge_base):
        """Test getting an ADR by its number."""
        knowledge_base.propose_adr("ADR 1", "ctx", "dec", "rat")
        adr2 = knowledge_base.propose_adr("ADR 2", "ctx", "dec", "rat")

        retrieved = knowledge_base.get_adr_by_number(2)

        assert retrieved is not None
        assert retrieved.id == adr2.id

    def test_approve_adr(self, knowledge_base):
        """Test approving an ADR."""
        adr = knowledge_base.propose_adr("Test ADR", "ctx", "dec", "rat")

        approved = knowledge_base.approve_adr(adr.id)

        assert approved.status == KnowledgeStatus.APPROVED
        assert approved.approved_at is not None

    def test_reject_adr(self, knowledge_base):
        """Test rejecting an ADR."""
        adr = knowledge_base.propose_adr("Test ADR", "ctx", "dec", "rat")

        rejected = knowledge_base.reject_adr(adr.id)

        assert rejected.status == KnowledgeStatus.REJECTED


class TestPendingKnowledge:
    """Tests for pending knowledge queries."""

    def test_get_pending_knowledge(self, knowledge_base):
        """Test getting all pending knowledge."""
        p1 = knowledge_base.propose_pattern("pattern1", "Test")
        knowledge_base.propose_pattern("pattern2", "Test")
        knowledge_base.approve_pattern(p1.id)

        knowledge_base.propose_adr("ADR 1", "ctx", "dec", "rat")

        pending = knowledge_base.get_pending_knowledge()

        assert len(pending["patterns"]) == 1
        assert len(pending["adrs"]) == 1

    def test_approve_via_generic_method(self, knowledge_base):
        """Test approving via the generic approve method."""
        pattern = knowledge_base.propose_pattern("test", "Test")

        result = knowledge_base.approve("pattern", pattern.id)

        assert result is True
        assert knowledge_base.get_pattern(pattern.id).status == KnowledgeStatus.APPROVED

    def test_reject_via_generic_method(self, knowledge_base):
        """Test rejecting via the generic reject method."""
        adr = knowledge_base.propose_adr("Test", "ctx", "dec", "rat")

        result = knowledge_base.reject("adr", adr.id)

        assert result is True
        assert knowledge_base.get_adr(adr.id).status == KnowledgeStatus.REJECTED
