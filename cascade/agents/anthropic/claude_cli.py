import shutil
import subprocess
import time
from collections.abc import Callable

from cascade.agents.interface import (
    AgentCapabilities,
    AgentCapability,
    AgentConfig,
    AgentInterface,
    AgentResponse,
)
from cascade.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeCliAgent(AgentInterface):
    """
    Claude Code agent via CLI.

    This agent integrates with Claude Code (the Anthropic CLI tool)
    to execute prompts with full capabilities including file editing,
    command execution, and code analysis.
    """

    # Claude Code CLI command
    CLI_COMMAND = "claude"

    # Default token limit for Claude models
    DEFAULT_TOKEN_LIMIT = 200000

    def __init__(self, config: AgentConfig | None = None):
        """
        Initialize Claude Code agent.

        Args:
            config: Agent configuration
        """
        super().__init__(config)
        self._cli_path: str | None = None
        self._available: bool | None = None

    def get_name(self) -> str:
        """Return agent identifier."""
        return "claude-cli"

    def get_capabilities(self) -> AgentCapabilities:
        """Return Claude Code capabilities."""
        return AgentCapabilities(
            capabilities={
                AgentCapability.FILE_READ,
                AgentCapability.FILE_WRITE,
                AgentCapability.FILE_EDIT,
                AgentCapability.COMMAND_EXECUTE,
                AgentCapability.CODE_ANALYSIS,
            },
            supports_streaming=True,
            supports_tools=True,
            max_output_tokens=16384,
        )

    def get_token_limit(self) -> int:
        """Return Claude's context window size."""
        return self.DEFAULT_TOKEN_LIMIT

    def is_available(self) -> bool:
        """Check if Claude Code CLI is installed and accessible."""
        if self._available is not None:
            return self._available

        self._cli_path = shutil.which(self.CLI_COMMAND)
        self._available = self._cli_path is not None

        if self._available:
            logger.debug(f"Claude Code CLI found at: {self._cli_path}")
        else:
            logger.warning("Claude Code CLI not found in PATH")

        return self._available

    def execute(
        self,
        prompt: str,
        working_dir: str | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        """
        Execute prompt via Claude Code CLI.

        Args:
            prompt: The prompt to execute
            working_dir: Working directory for the command
            callback: Optional callback for streaming (not currently implemented for CLI)

        Returns:
            AgentResponse with execution results
        """
        # Validate
        is_valid, error = self.validate_prompt(prompt)
        if not is_valid:
            return AgentResponse(
                success=False,
                content="",
                error=error,
            )

        # Validate working directory
        is_safe, error = self._validate_working_dir(working_dir)
        if not is_safe:
            return AgentResponse(
                success=False,
                content="",
                error=error,
            )

        if not self.is_available():
            return AgentResponse(
                success=False,
                content="",
                error="Claude Code CLI is not installed or not in PATH",
            )

        start_time = time.time()

        try:
            # Build command
            cmd = self._build_command()

            logger.debug(f"Executing Claude Code: {' '.join(cmd)}...")

            # Execute - pass prompt via stdin and use Popen for streaming
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir,
                env=self._get_environment(),
            )

            stdout_lines = []
            stderr_lines = []

            # Send prompt and close stdin
            if process.stdin:
                process.stdin.write(prompt)
                process.stdin.close()

            # Read stdout line by line for streaming
            import select

            while True:
                # Use select to wait for output with timeout
                reads = []
                if process.stdout:
                    reads.append(process.stdout)
                if process.stderr:
                    reads.append(process.stderr)

                ready, _, _ = select.select(reads, [], [], 0.1)

                if process.stdout and process.stdout in ready:
                    line = process.stdout.readline()
                    if line:
                        stdout_lines.append(line)
                        if callback:
                            callback(line)

                if process.stderr and process.stderr in ready:
                    line = process.stderr.readline()
                    if line:
                        stderr_lines.append(line)

                # Check if process is done
                if process.poll() is not None:
                    # Read any remaining output
                    if process.stdout:
                        remaining_stdout = process.stdout.read()
                        if remaining_stdout:
                            stdout_lines.append(remaining_stdout)
                            if callback:
                                callback(remaining_stdout)

                    if process.stderr:
                        remaining_stderr = process.stderr.read()
                        if remaining_stderr:
                            stderr_lines.append(remaining_stderr)
                    break

                # Check for timeout
                if time.time() - start_time > self.config.timeout_seconds:
                    process.kill()
                    return AgentResponse(
                        success=False,
                        content="".join(stdout_lines),
                        error=f"Execution timed out after {self.config.timeout_seconds} seconds",
                        execution_time_ms=int((time.time() - start_time) * 1000),
                    )

            execution_time = int((time.time() - start_time) * 1000)

            # Use a dummy CompletedProcess for parsing
            result = subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines),
            )

            # Parse response
            return self._parse_response(result, execution_time)

        except Exception as e:
            logger.exception("Unexpected error executing Claude Code")
            return AgentResponse(
                success=False,
                content="".join(stdout_lines) if "stdout_lines" in locals() else "",
                error=f"Unexpected error: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _build_command(self) -> list[str]:
        """
        Build the CLI command with safety overrides.

        Warning: --dangerously-skip-permissions is used for automation,
        but agents are restricted to the project directory by the core system.
        """
        cmd = [
            self.CLI_COMMAND,
            "--print",  # Print response to stdout
            "--dangerously-skip-permissions",  # Skip confirmation prompts for autonomous tool use
        ]

        # Add any extra args from config, filtering for safety if necessary
        if self.config.extra_args:
            for arg in self.config.extra_args:
                # Basic safety filtering for CLI arguments
                if not any(char in arg for char in [";", "&", "|", ">", "<"]):
                    cmd.append(arg)

        return cmd

    def _parse_response(
        self,
        result: subprocess.CompletedProcess[str],
        execution_time: int,
    ) -> AgentResponse:
        """Parse subprocess result into AgentResponse."""
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode != 0:
            return AgentResponse(
                success=False,
                content=stdout,
                error=stderr or f"Exit code: {result.returncode}",
                execution_time_ms=execution_time,
                raw_output=stdout + stderr,
            )

        # Try to extract structured information
        files_modified = self._extract_modified_files(stdout)
        commands_executed = self._extract_commands(stdout)

        return AgentResponse(
            success=True,
            content=stdout,
            files_modified=files_modified,
            commands_executed=commands_executed,
            execution_time_ms=execution_time,
            raw_output=stdout,
        )

    def _extract_modified_files(self, output: str) -> list[str]:
        """Extract list of modified files from output."""
        import re

        files = set()
        # Common markers in Claude Code output
        patterns = [
            r"(?:Created|Modified|Edited|Wrote|Updated|Applied changes to)\s*(?:file:?\s*)?`?([^`\s\*,]+)`?",
            r"CHANGELOG\.md|package\.json|pyproject\.toml",  # Specific important files often mentioned
            r"(?:into|to)\s+`?([^`\s\*,]+\.[a-z0-9]+)`?",
        ]

        # Also look for file paths in backticks that are mentioned in context of modification
        for line in output.split("\n"):
            # Skip lines that look like code blocks or logs unless they contain markers
            if line.strip().startswith("```") or line.strip().startswith(">"):
                continue

            for pattern in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    path = match.group(1).strip()
                    # Remove any trailing punctuation or formatting
                    path = path.rstrip(".,:;)]`'\"")
                    path = path.lstrip("`'\"")

                    # Basic sanity check for file path
                    if path and "." in path and "/" in path or len(path) > 2:
                        if not any(x in path for x in [" ", "\n", "\t"]):
                            files.add(path)

        return sorted(files)

    def _extract_commands(self, output: str) -> list[str]:
        """Extract executed commands from output."""
        import re

        commands = []
        # Support both prefixed markers and markdown blocks
        markers = [
            r"Running:\s*(.+)",
            r"Executed:\s*(.+)",
            r"^\$ (.+)",
        ]

        for line in output.split("\n"):
            for pattern in markers:
                match = re.search(pattern, line.strip())
                if match:
                    cmd = match.group(1).strip()
                    if cmd:
                        commands.append(cmd)

        return commands
