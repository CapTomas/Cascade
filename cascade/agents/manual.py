"""Manual agent implementation for human-in-the-loop flows."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from collections.abc import Callable

from rich.console import Console
from rich.panel import Panel

from cascade.agents.interface import (
    AgentCapabilities,
    AgentCapability,
    AgentConfig,
    AgentInterface,
    AgentResponse,
)

logger = logging.getLogger(__name__)


class ManualAgent(AgentInterface):
    """
    Manual agent that facilitates human-in-the-loop orchestration.

    This agent "executes" by:
    1.  Printing the context-rich prompt to the terminal.
    2.  Attempts to copy the prompt to the system clipboard.
    3.  Waits for the user to paste the response from an external AI
        (like ChatGPT Plus, Claude Pro, or Gemini Advanced).

    This is the ideal agent for users who want to use their web-based
    subscriptions instead of paying for API credits.
    """

    def __init__(self, config: AgentConfig | None = None):
        """
        Initialize Manual agent.

        Args:
            config: Agent configuration
        """
        super().__init__(config)
        self.console = Console()

    def get_name(self) -> str:
        """Return agent identifier."""
        return "manual"

    def get_capabilities(self) -> AgentCapabilities:
        """Return Manual agent capabilities (effectively infinite)."""
        return AgentCapabilities(
            capabilities={
                AgentCapability.FILE_READ,
                AgentCapability.FILE_WRITE,
                AgentCapability.FILE_EDIT,
                AgentCapability.COMMAND_EXECUTE,
                AgentCapability.CODE_ANALYSIS,
                AgentCapability.WEB_SEARCH,
            },
            supports_streaming=False,
            supports_tools=False,
            max_output_tokens=32768,
        )

    def get_token_limit(self) -> int:
        """Unlimited since human is the bridge."""
        return 1000000

    def is_available(self) -> bool:
        """Manual agent is always available as long as a human is present."""
        return True

    def execute(
        self,
        prompt: str,
        working_dir: str | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        """
        Facilitate manual execution by human.

        Args:
            prompt: The prompt to execute
            working_dir: Working directory (not directly used)

        Returns:
            AgentResponse with user-provided content
        """
        # Validate
        is_valid, error = self.validate_prompt(prompt)
        if not is_valid:
            return AgentResponse(success=False, content="", error=error)

        # Validate working directory
        is_safe, error = self._validate_working_dir(working_dir)
        if not is_safe:
            return AgentResponse(success=False, content="", error=error)

        start_time = time.time()

        self.console.print("\n")
        self.console.print(
            Panel(
                "[bold blue]Manual Mode Active[/bold blue]\n\n"
                "Cascade has prepared the following prompt for your external AI.\n"
                "Copy it to your clipboard, paste it into ChatGPT/Claude/Gemini,\n"
                "and paste the full response back here.",
                title="Cascade Manual Bridge",
                border_style="blue",
            )
        )

        # Show the prompt
        self.console.print("\n[bold]--- PROMPT START ---[/bold]")
        self.console.print(prompt)
        self.console.print("[bold]--- PROMPT END ---[/bold]\n")

        # Attempt to copy to clipboard (macOS specific for now, easily extendable)
        copied = self._copy_to_clipboard(prompt)
        if copied:
            self.console.print("[green]✓ Prompt copied to system clipboard.[/green]")
        else:
            self.console.print(
                "[yellow]! Could not auto-copy to clipboard. Please copy manually.[/yellow]"
            )

        self.console.print("\n[bold cyan]Waiting for AI response...[/bold cyan]")
        self.console.print(
            "(Paste the response below. Use [bold]Ctrl-D[/bold] on a new line when finished)"
        )

        # Read multiple lines until EOF
        content_lines = []
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                content_lines.append(line)
        except KeyboardInterrupt:
            return AgentResponse(
                success=False,
                content="",
                error="Execution cancelled by user",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        content = "".join(content_lines).strip()
        execution_time = int((time.time() - start_time) * 1000)

        if not content:
            return AgentResponse(
                success=False,
                content="",
                error="No response provided",
                execution_time_ms=execution_time,
            )

        return AgentResponse(
            success=True,
            content=content,
            execution_time_ms=execution_time,
            raw_output=content,
        )

    def _copy_to_clipboard(self, text: str) -> bool:
        """Attempt to copy text to system clipboard."""
        try:
            if sys.platform == "darwin":
                process = subprocess.Popen(["/usr/bin/pbcopy"], stdin=subprocess.PIPE, text=True)
                process.communicate(input=text)
                return process.returncode == 0
            elif sys.platform == "linux":
                # Check for xclip or xsel
                for cmd in ["xclip -selection clipboard", "xsel -bi"]:
                    try:
                        cmd_parts = cmd.split()
                        process = subprocess.Popen(cmd_parts, stdin=subprocess.PIPE, text=True)
                        process.communicate(input=text)
                        if process.returncode == 0:
                            return True
                    except FileNotFoundError:
                        continue
            return False
        except Exception as e:
            logger.debug(f"Clipboard copy failed: {e}")
            return False
