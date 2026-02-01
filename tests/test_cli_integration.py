"""CLI integration tests for Cascade."""

import os

import pytest
from click.testing import CliRunner

from cascade.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project for CLI tests."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    os.chdir(project_dir)
    return project_dir


def test_cli_init(runner, temp_project):
    """Test 'cascade init' command."""
    result = runner.invoke(cli, ["init", "--name", "Test CLI Project"])
    assert result.exit_code == 0
    # Check for success indicator in new box-drawn output
    assert "✓" in result.output or "INITIALIZED" in result.output
    assert os.path.exists(".cascade")


def test_cli_status(runner, temp_project):
    """Test 'cascade status' command."""
    runner.invoke(cli, ["init", "--name", "Test Status Project"])
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    # New dashboard-style output shows project name and ticket info
    assert "Project" in result.output or "Ticket" in result.output


def test_cli_ticket_list(runner, temp_project):
    """Test 'cascade ticket list' command."""
    runner.invoke(cli, ["init", "--name", "Test Ticket Project"])
    result = runner.invoke(cli, ["ticket", "list"])
    assert result.exit_code == 0
    # Empty state message or ticket catalog header
    assert "ticket" in result.output.lower()


def test_cli_topic_create_list(runner, temp_project):
    """Test topic creation and listing."""
    runner.invoke(cli, ["init", "--name", "Test Topic Project"])
    runner.invoke(cli, ["topic", "create", "AUTH", "-d", "Authentication system"])

    result = runner.invoke(cli, ["topic", "list"])
    assert result.exit_code == 0
    assert "auth" in result.output.lower()


def test_cli_type_command(runner, temp_project):
    """Test 'cascade type' command."""
    runner.invoke(cli, ["init", "--name", "Test Type Project"])
    result = runner.invoke(cli, ["type", "BUG"])
    assert result.exit_code == 0
    # Check for bug type or no tickets message
    assert "bug" in result.output.lower() or "no" in result.output.lower()


def test_cli_config_show(runner, temp_project):
    """Test 'cascade config show' command."""
    runner.invoke(cli, ["init", "--name", "Test Config Project"])
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    # New settings-style display shows these sections
    assert "Project" in result.output
    assert "Agent" in result.output
