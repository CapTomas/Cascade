"""Quality gate framework for enforcing project standards."""

from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from cascade.agents.interface import AgentResponse
from cascade.models.execution import GateResult, GateResults
from cascade.models.project import ProjectConfig
from cascade.models.ticket import Ticket

logger = logging.getLogger(__name__)


class BaseGate(ABC):
    """Abstract base class for quality gates."""

    def __init__(self, name: str, fail_on_error: bool = True):
        self.name = name
        self.fail_on_error = fail_on_error

    @abstractmethod
    def run(self, project_root: Path, ticket: Ticket, response: AgentResponse) -> GateResult:
        """Run the gate check."""
        pass

    def _run_command(self, command: str, cwd: Path) -> tuple[bool, str, str | None]:
        """
        Run a shell command safely and return (success, output, error).

        Args:
            command: The command to run
            cwd: Working directory

        Returns:
            Tuple of (success, combined_output, error_message)
        """
        import shlex
        import shutil

        # Basic security check: No multiple commands
        if ";" in command or "&&" in command or "||" in command:
            return False, "", f"Potentially unsafe command blocked: {command}"

        try:
            # Check if base command exists
            cmd_parts = shlex.split(command)
            if not cmd_parts:
                return False, "", "Empty command"

            base_cmd = cmd_parts[0]
            if not shutil.which(base_cmd):
                return False, "", f"Tool '{base_cmd}' not found in PATH. Please install it."

            # We use shell=True because many dev tools (like 'npm test')
            # rely on shell environment/aliases, but we've added basic checks.
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output, None
        except Exception as e:
            return False, "", str(e)


class StaticAnalysisGate(BaseGate):
    """Gate for linting and type checking."""

    def __init__(self, tools: dict[str, str], fail_on_error: bool = True):
        super().__init__("Static Analysis", fail_on_error)
        self.tools = tools

    def run(self, project_root: Path, ticket: Ticket, response: AgentResponse) -> GateResult:
        logger.info(f"Running Static Analysis gate with tools: {self.tools}")

        all_output = []
        all_passed = True

        for tool, cmd in self.tools.items():
            success, output, error = self._run_command(cmd, project_root)
            all_output.append(f"--- {tool} ---\n{output}")
            if not success:
                all_passed = False
                if error:
                    all_output.append(f"Error: {error}")

        return GateResult(gate_name=self.name, passed=all_passed, output="\n".join(all_output))


class UnitTestGate(BaseGate):
    """Gate for running unit tests."""

    def __init__(self, command: str, min_coverage: int | None = None, fail_on_error: bool = True):
        super().__init__("Unit Tests", fail_on_error)
        self.command = command
        self.min_coverage = min_coverage

    def run(self, project_root: Path, ticket: Ticket, response: AgentResponse) -> GateResult:
        logger.info(f"Running Unit Test gate with command: {self.command}")

        success, output, error = self._run_command(self.command, project_root)

        if success and self.min_coverage is not None:
            coverage = self._parse_coverage(output)
            if coverage is not None and coverage < self.min_coverage:
                success = False
                output += (
                    f"\n\nCoverage failure: {coverage}% is below threshold {self.min_coverage}%"
                )

        return GateResult(gate_name=self.name, passed=success, output=output, error=error)

    def _parse_coverage(self, output: str) -> float | None:
        """Attempt to parse coverage percentage from output."""
        import re

        # Support for pytest-cov output
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            return float(match.group(1))

        # Support for generic 'Coverage: X%'
        match = re.search(r"Coverage:\s*(\d+(\.\d+)?)%", output, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return None


class SecurityScanGate(BaseGate):
    """
    Gate for security scanning.

    Runs various security scanners based on project language
    and reports findings.
    """

    def __init__(
        self,
        tools: dict[str, list[str]] | None = None,
        fail_on_critical: bool = True,
        fail_on_high: bool = False,
    ):
        super().__init__("Security Scan", fail_on_critical)
        self.tools = tools or {}
        self.fail_on_critical = fail_on_critical
        self.fail_on_high = fail_on_high

    def run(self, project_root: Path, ticket: Ticket, response: AgentResponse) -> GateResult:
        logger.info("Running Security Scan gate")

        all_output = []
        all_passed = True
        error_msg = None

        # Resolve tools if not specified
        tools_to_run = self.tools
        if not tools_to_run:
            tools_to_run = self._autodiscover_tools(project_root)

        if not tools_to_run:
            return GateResult(
                gate_name=self.name,
                passed=True,
                output="No security scan tools matched or configured. Skipping.",
            )

        import shutil

        for lang, commands in tools_to_run.items():
            for cmd in commands:
                base_cmd = cmd.split()[0]
                if not shutil.which(base_cmd):
                    all_output.append(f"Skipping {lang} scan: '{base_cmd}' not found in PATH")
                    continue

                logger.debug(f"Running security scan for {lang}: {cmd}")
                success, output, error = self._run_command(cmd, project_root)
                all_output.append(f"--- {lang} ({cmd}) ---\n{output}")

                if error:
                    all_output.append(f"Execution Error: {error}")

                # Analysis logic
                issues_found = False
                lower_output = output.lower()

                if "critical" in lower_output and self.fail_on_critical:
                    issues_found = True
                    logger.warning(f"CRITICAL security vulnerability found via {cmd}")
                elif "high" in lower_output and self.fail_on_high:
                    issues_found = True
                    logger.warning(f"HIGH security vulnerability found via {cmd}")

                # Some tools use non-zero exit code to indicate ANY findings
                if not success and ("audit" in cmd or "bandit" in cmd):
                    if not issues_found:  # If not already flagged by keywords
                        issues_found = True

                if issues_found:
                    all_passed = False

        return GateResult(
            gate_name=self.name,
            passed=all_passed,
            output="\n".join(all_output),
            error=error_msg,
        )

    def _autodiscover_tools(self, project_root: Path) -> dict[str, list[str]]:
        """Identify relevant security tools based on project content."""
        tools = {}
        # Python
        if any(project_root.glob("**/*.py")):
            tools["python"] = ["bandit -r . -ll"]

        # JavaScript/TypeScript
        if (project_root / "package.json").exists():
            tools["javascript"] = ["npm audit --audit-level=critical"]

        return tools


class QualityGates:
    """Manager for loading and running quality gates."""

    def __init__(self, config: ProjectConfig, project_root: Path):
        self.config = config
        self.project_root = project_root
        self.gates: list[BaseGate] = []
        self._load_gates()

    def _load_gates(self) -> None:
        """Load enabled gates from configuration."""
        q = self.config.quality

        if q.static_analysis.enabled:
            self.gates.append(
                StaticAnalysisGate(
                    tools=q.static_analysis.tools, fail_on_error=q.static_analysis.fail_on_error
                )
            )

        if q.unit_tests.enabled and q.unit_tests.command:
            self.gates.append(
                UnitTestGate(
                    command=q.unit_tests.command,
                    min_coverage=q.unit_tests.min_coverage,
                    fail_on_error=q.unit_tests.fail_on_error,
                )
            )

        if q.security_scan.enabled:
            self.gates.append(
                SecurityScanGate(
                    fail_on_critical=q.security_scan.fail_on_critical,
                    fail_on_high=q.security_scan.fail_on_high,
                )
            )

    def run_all(self, ticket: Ticket, response: AgentResponse) -> GateResults:
        """Run all loaded quality gates."""
        results = []
        for gate in self.gates:
            result = gate.run(self.project_root, ticket, response)
            results.append(result)
            if not result.passed and gate.fail_on_error:
                logger.warning(f"Quality gate {gate.name} failed. Stopping further gates.")
                break

        return GateResults(results=results)
