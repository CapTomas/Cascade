from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cascade.agents.interface import AgentResponse
from cascade.core.quality_gates import (
    QualityGates,
    StaticAnalysisGate,
    UnitTestGate,
)
from cascade.models.project import ProjectConfig, QualityConfig, QualityGateConfig
from cascade.models.ticket import Ticket


@pytest.fixture
def mock_ticket():
    return MagicMock(spec=Ticket, id=1)


@pytest.fixture
def mock_response():
    return MagicMock(spec=AgentResponse)


@pytest.fixture
def project_config():
    config = MagicMock(spec=ProjectConfig)
    config.quality = QualityConfig(
        static_analysis=QualityGateConfig(enabled=True, tools={"ruff": "ruff check ."}),
        unit_tests=QualityGateConfig(enabled=True, command="pytest"),
        security_scan=QualityGateConfig(enabled=True),
    )
    return config


def test_static_analysis_gate_success(mock_ticket, mock_response):
    gate = StaticAnalysisGate(tools={"ruff": "ruff check ."})
    with patch("subprocess.run") as mock_run, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/ruff"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "No issues found"
        mock_run.return_value.stderr = ""

        result = gate.run(Path("."), mock_ticket, mock_response)

        assert result.passed
        assert "ruff" in result.output
        assert "No issues found" in result.output


def test_static_analysis_gate_failure(mock_ticket, mock_response):
    gate = StaticAnalysisGate(tools={"ruff": "ruff check ."})
    with patch("subprocess.run") as mock_run, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/ruff"
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "Unused variable"
        mock_run.return_value.stderr = ""

        result = gate.run(Path("."), mock_ticket, mock_response)

        assert not result.passed
        assert "Unused variable" in result.output


def test_unit_test_gate_success(mock_ticket, mock_response):
    gate = UnitTestGate(command="pytest")
    with patch("subprocess.run") as mock_run, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/pytest"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "10 tests passed"
        mock_run.return_value.stderr = ""

        result = gate.run(Path("."), mock_ticket, mock_response)

        assert result.passed
        assert "10 tests passed" in result.output


def test_quality_gates_run_all_success(project_config, mock_ticket, mock_response):
    manager = QualityGates(project_config, Path("."))

    with patch("subprocess.run") as mock_run, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/tool"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        mock_run.return_value.stderr = ""

        results = manager.run_all(mock_ticket, mock_response)

        assert results.all_passed
        assert len(results.results) == 3


def test_quality_gates_run_all_failure_stops_execution(project_config, mock_ticket, mock_response):
    # Enable fail_on_error for static analysis (default)
    manager = QualityGates(project_config, Path("."))

    with patch("subprocess.run") as mock_run, patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/tool"
        # First gate (Static Analysis) fails
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "Linter error"
        mock_run.return_value.stderr = ""

        results = manager.run_all(mock_ticket, mock_response)

        assert not results.all_passed
        assert len(results.results) == 1  # Should stop after first failure
        assert results.results[0].gate_name == "Static Analysis"
