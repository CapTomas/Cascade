"""Main CLI entry point for Cascade."""

import sys
import click
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

from cascade.cli.styles import console
from cascade.cli.commands import init, ticket, topic, status, config, knowledge, agents, type_cmd, next, metrics, git, destroy
from cascade.core.project import get_project
from cascade.utils.logger import setup_logging, get_logger

# Load environment variables from .env file
load_dotenv()

logger = get_logger(__name__)


@click.group()
@click.version_option(package_name="cascade-ai")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    Cascade: Human-Directed AI Development Orchestration

    AI assists, human directs - works with any AI agent.

    Run 'cascade init' to initialize a new project, or run commands
    in an existing project directory.
    """
    ctx.ensure_object(dict)
    ctx.obj["console"] = console

    # Setup logging if we are in a project
    try:
        project = get_project()
        log_file = project.cascade_dir / "logs" / "cascade.log"
        setup_logging(
            level=project.config.logging.level if hasattr(project.config, "logging") else "INFO",
            log_file=log_file,
            console=False, # We use rich directly in CLI
        )
    except (FileNotFoundError, Exception):
        # Not in a project or config error, just setup basic logging
        setup_logging(level="INFO", console=False)


def main() -> None:
    """Main entry point."""
    try:
        cli(obj={})
    except SystemExit as e:
        sys.exit(e.code)
    except click.ClickException as e:
        console.print(f"[red]Error:[/red] {e.format_message()}")
        sys.exit(e.exit_code)
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(
            Panel(
                f"[bold red]An unexpected error occurred:[/bold red]\n{str(e)}\n\n"
                f"[dim]See logs for full details.[/dim]",
                title="Fatal Error",
                border_style="red",
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
