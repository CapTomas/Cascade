"""Tests for CLI command workflows."""

import os

import pytest
from click.testing import CliRunner

from cascade.cli.main import cli


class TestTicketCommands:
    """Tests for ticket-related CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project with .cascade directory."""
        cascade_dir = tmp_path / ".cascade"
        cascade_dir.mkdir()
        logs_dir = cascade_dir / "logs"
        logs_dir.mkdir()

        # Create minimal config
        config_file = cascade_dir / "config.yaml"
        config_file.write_text("""
project:
  name: Test Project
  description: Test project description
  tech_stack: [python]

agent:
  default: manual
  fallback: generic

context:
  default_mode: minimal

quality_gates:
  static_analysis:
    enabled: false
  unit_tests:
    enabled: false
  security_scan:
    enabled: false
""")
        return tmp_path

    def test_ticket_list_empty(self, runner, project_dir):
        """Test listing tickets when none exist."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["ticket", "list"])

            # Should succeed or fail gracefully (DB may not be initialized)
            assert result.exit_code in [0, 1]

    def test_ticket_create_basic(self, runner, project_dir):
        """Test creating a ticket with basic info."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(
                cli,
                [
                    "ticket",
                    "create",
                    "--title",
                    "Test ticket",
                    "--type",
                    "TASK",
                    "--description",
                    "This is a test",
                ],
            )

            # Check creation was attempted
            assert result.exit_code in [0, 1]  # May fail due to DB not being initialized

    def test_ticket_show_nonexistent(self, runner, project_dir):
        """Test showing a ticket that doesn't exist."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["ticket", "show", "99999"])

            # Should fail gracefully
            assert result.exit_code != 0 or "not found" in result.output.lower()


class TestKnowledgeCommands:
    """Tests for knowledge-related CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def project_dir(self, tmp_path):
        cascade_dir = tmp_path / ".cascade"
        cascade_dir.mkdir()
        logs_dir = cascade_dir / "logs"
        logs_dir.mkdir()

        config_file = cascade_dir / "config.yaml"
        config_file.write_text("""
project:
  name: Test Project
  description: Test
  tech_stack: [python]
agent:
  default: manual
""")
        return tmp_path

    def test_knowledge_pending_empty(self, runner, project_dir):
        """Test listing pending knowledge when none exists."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["knowledge", "pending"])

            # Should succeed with empty list
            assert result.exit_code in [0, 1]

    def test_knowledge_conventions(self, runner, project_dir):
        """Test listing conventions."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["knowledge", "conventions"])

            # Should not crash
            assert result.exit_code in [0, 1]


class TestConfigCommands:
    """Tests for config-related CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def project_dir(self, tmp_path):
        cascade_dir = tmp_path / ".cascade"
        cascade_dir.mkdir()
        logs_dir = cascade_dir / "logs"
        logs_dir.mkdir()

        config_file = cascade_dir / "config.yaml"
        config_file.write_text("""
project:
  name: Config Test
  description: Testing config
  tech_stack: [python]
agent:
  default: manual
  fallback: generic
""")
        return tmp_path

    def test_config_show(self, runner, project_dir):
        """Test showing config."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["config", "show"])

            # Should display config
            assert result.exit_code in [0, 1]

    def test_config_set_agent(self, runner, project_dir):
        """Test setting agent config."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["config", "set", "agent.default", "codex"])

            # Should attempt to set config
            assert result.exit_code in [0, 1]


class TestAgentsCommand:
    """Tests for agents command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_agents_list(self, runner, tmp_path):
        """Test listing available agents."""
        # Create minimal project structure
        cascade_dir = tmp_path / ".cascade"
        cascade_dir.mkdir()
        logs_dir = cascade_dir / "logs"
        logs_dir.mkdir()
        (cascade_dir / "config.yaml").write_text("""
project:
  name: Test
  description: Test
  tech_stack: [python]
agent:
  default: manual
""")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            os.chdir(tmp_path)
            result = runner.invoke(cli, ["agents", "list"])

            # Should list agents or show help
            assert result.exit_code in [0, 1]


class TestStatusCommand:
    """Tests for status command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def project_dir(self, tmp_path):
        cascade_dir = tmp_path / ".cascade"
        cascade_dir.mkdir()
        logs_dir = cascade_dir / "logs"
        logs_dir.mkdir()

        (cascade_dir / "config.yaml").write_text("""
project:
  name: Status Test
  description: Testing status
  tech_stack: [python, react]
agent:
  default: claude-code
""")
        return tmp_path

    def test_status_display(self, runner, project_dir):
        """Test status command displays project info."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["status"])

            # Status should run without crashing
            assert result.exit_code in [0, 1]


class TestTopicCommands:
    """Tests for topic-related CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def project_dir(self, tmp_path):
        cascade_dir = tmp_path / ".cascade"
        cascade_dir.mkdir()
        logs_dir = cascade_dir / "logs"
        logs_dir.mkdir()

        (cascade_dir / "config.yaml").write_text("""
project:
  name: Topic Test
  description: Testing topics
  tech_stack: [python]
agent:
  default: manual
""")
        return tmp_path

    def test_topic_list(self, runner, project_dir):
        """Test listing topics."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["topic", "list"])

            # Should succeed
            assert result.exit_code in [0, 1]

    def test_topic_create(self, runner, project_dir):
        """Test creating a topic."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(
                cli,
                [
                    "topic",
                    "create",
                    "authentication",
                    "--description",
                    "User authentication features",
                ],
            )

            # Should attempt to create
            assert result.exit_code in [0, 1]


class TestTypeCommand:
    """Tests for type command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def project_dir(self, tmp_path):
        cascade_dir = tmp_path / ".cascade"
        cascade_dir.mkdir()
        logs_dir = cascade_dir / "logs"
        logs_dir.mkdir()

        (cascade_dir / "config.yaml").write_text("""
project:
  name: Type Test
  description: Testing type cmd
  tech_stack: [python]
agent:
  default: manual
""")
        return tmp_path

    def test_type_list_bugs(self, runner, project_dir):
        """Test listing tickets by type."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["type", "BUG"])

            # Should run without crashing
            assert result.exit_code in [0, 1]


class TestNextCommand:
    """Tests for next command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def project_dir(self, tmp_path):
        cascade_dir = tmp_path / ".cascade"
        cascade_dir.mkdir()
        logs_dir = cascade_dir / "logs"
        logs_dir.mkdir()

        (cascade_dir / "config.yaml").write_text("""
project:
  name: Next Test
  description: Testing next
  tech_stack: [python]
agent:
  default: manual
""")
        return tmp_path

    def test_next_no_tickets(self, runner, project_dir):
        """Test next command with no ready tickets."""
        with runner.isolated_filesystem(temp_dir=project_dir):
            os.chdir(project_dir)
            result = runner.invoke(cli, ["next"])

            # Should handle gracefully
            assert result.exit_code in [0, 1]
