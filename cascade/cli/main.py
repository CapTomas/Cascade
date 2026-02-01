"""Main CLI entry point for Cascade."""

from __future__ import annotations

import logging
import sys

import click
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel

from cascade.cli.commands import (
    agents,
    config,
    destroy,
    git,
    init,
    knowledge,
    metrics,
    next,
    status,
    ticket,
    topic,
    type_cmd,
)
from cascade.cli.themes import get_current_theme
from cascade.core.project import get_project
from cascade.utils.logger import get_logger, setup_logging

# Load environment variables from .env file
load_dotenv()

logger = get_logger(__name__)


def get_console() -> Console:
    """Get a themed console instance."""
    theme = get_current_theme()
    return Console(theme=theme.to_rich_theme())


# Global console - initialized lazily
_console: Console | None = None


def get_themed_console() -> Console:
    """Get the global themed console."""
    global _console
    if _console is None:
        _console = get_console()
    return _console


@click.group(invoke_without_command=True)
@click.version_option(package_name="cascade-ai")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    Cascade: Human-Directed AI Development Orchestration

    AI assists, human directs - works with any AI agent.

    Run 'cascade init' to initialize a new project, or enter
    interactive mode by running 'cascade' with no arguments.
    """
    ctx.ensure_object(dict)
    ctx.obj["console"] = get_themed_console()

    # Setup logging if we are in a project
    try:
        project = get_project()
        log_file = project.cascade_dir / "logs" / "cascade.log"
        level_name = project.config.logging.level if hasattr(project.config, "logging") else "INFO"
        level = getattr(logging, level_name.upper(), logging.INFO)
        setup_logging(
            level=level,
            log_file=log_file,
            console=False,  # We use rich directly in CLI
        )
    except (FileNotFoundError, Exception):
        # Not in a project or config error, just setup basic logging
        setup_logging(level=logging.INFO, console=False)

    # If no command specified, enter interactive mode
    if ctx.invoked_subcommand is None:
        from cascade.cli.interactive import start_interactive_mode

        start_interactive_mode(ctx.obj["console"])


def main() -> None:
    """Main entry point."""
    console = get_themed_console()

    try:
        cli(obj={})
    except SystemExit as e:
        sys.exit(e.code)
    except click.ClickException as e:
        console.print(f"[error]Error:[/error] {e.format_message()}")
        sys.exit(e.exit_code)
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(
            Panel(
                f"[error]An unexpected error occurred:[/error]\n{str(e)}\n\n"
                f"[muted]See logs for full details.[/muted]",
                title="[error]Fatal Error[/error]",
                border_style="error",
                box=box.ROUNDED,
            )
        )
        sys.exit(1)


# Register command groups
cli.add_command(init.init_cmd)
cli.add_command(ticket.ticket)
cli.add_command(topic.topic)
cli.add_command(status.status)
cli.add_command(config.config)
cli.add_command(knowledge.knowledge)
cli.add_command(agents.agents)
cli.add_command(type_cmd.type_cmd)
cli.add_command(next.next_cmd)
cli.add_command(metrics.metrics)
cli.add_command(git.git)
cli.add_command(destroy.destroy_cmd)


if __name__ == "__main__":
    main()
