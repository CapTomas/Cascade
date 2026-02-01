"""Init command for Cascade CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cascade.cli.styles import (
    CASCADE_LOGO,
    create_table,
    get_progress,
    print_error,
    print_success,
    print_warning,
)
from cascade.cli.ui import (
    print_info_box,
)
from cascade.core.project import CascadeProject


@click.command("init")
@click.argument("requirements", required=False)
@click.option(
    "--name",
    "-n",
    help="Project name",
)
@click.option(
    "--description",
    "-d",
    default="",
    help="Project description (if not using requirements)",
)
@click.option(
    "--tech-stack",
    "-t",
    multiple=True,
    help="Technologies used (if not using requirements)",
)
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    default=None,
    help="Project path (defaults to current directory)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation for generated plan",
)
@click.pass_context
def init_cmd(
    ctx: click.Context,
    requirements: str | None,
    name: str | None,
    description: str,
    tech_stack: tuple[str, ...],
    path: Path | None,
    yes: bool,
) -> None:
    """
    Initialize a new Cascade project.

    Creates a .cascade directory with database and configuration files.

    If REQUIREMENTS are provided, Cascade will analyze them and
    generate a project plan (tickets, topics, ADRs). REQUIREMENTS
    can be a text string or a path to a file containing the requirements.

    Examples:

        cascade init "Build a REST API with FastAPI"

        cascade init ./my-idea.txt

        cascade init --name "My Project" -d "A simple project" -t python
    """
    console: Console = ctx.obj["console"]
    project_path = path or Path.cwd()

    # Handle requirements file if path is provided
    if requirements:
        req_path = Path(requirements).expanduser().resolve()
        if req_path.exists() and req_path.is_file():
            try:
                console.print(f"[muted]Reading requirements from {req_path}[/muted]")
                requirements = req_path.read_text(encoding="utf-8")
            except Exception as e:
                print_warning(f"Could not read file {req_path}: {e}")
                console.print("[muted]Treating input as raw text string.[/muted]")

    try:
        project = CascadeProject(project_path)

        if project.is_initialized:
            console.print(
                Panel(
                    f"[warning]⚠[/warning] Project already initialized at [accent]{project_path}[/accent]\n\n"
                    f"[muted]If this project is broken, run [white]cascade destroy[/white] first.[/muted]",
                    border_style="warning",
                    box=box.ROUNDED,
                )
            )
            return

        # Show getting started message
        console.print()
        console.print(
            Panel(
                "[header]Initializing Cascade Project[/header]\n\n"
                "[muted]Setting up your AI-powered development environment...[/muted]",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

        # 1. Basic initialization
        with get_progress() as progress:
            task = progress.add_task("[muted]Creating project structure...", total=100)
            project.initialize(
                name=name or project_path.name,
                description=description,
                tech_stack=list(tech_stack) if tech_stack else [],
            )
            progress.update(task, completed=50)
            progress.update(task, completed=100, description="[success]Project created[/success]")

        # 2. Interactive Agent Configuration (Do this BEFORE planning)
        from cascade.cli.onboarding import configure_agent

        configure_agent(console, project)

        # 3. Planning if requirements provided
        if requirements:
            console.print()
            with get_progress() as progress:
                task = progress.add_task("[muted]Analyzing requirements with AI...", total=100)
                plan = project.planner.plan(requirements)
                progress.update(
                    task, completed=100, description="[success]Analysis complete[/success]"
                )

            # Update project config with AI-discovered info
            project.config.name = plan.project_name
            project.config.description = plan.project_description
            project.config.tech_stack = plan.tech_stack
            project.save_config()

            # Display proposed project in a nice box
            console.print()
            _display_proposed_plan(console, plan)

            generate_plan = True
            if not yes:
                console.print()
                if not click.confirm("Generate this project plan?", default=True):
                    generate_plan = False
                    print_info_box(console, "Skipping plan generation.")

            if generate_plan:
                with get_progress() as progress:
                    task = progress.add_task("[muted]Generating tickets...", total=100)
                    project.planner.generate_tickets(plan)
                    progress.update(task, completed=100)
                print_success("Project plan generated successfully.")

        # Show success summary
        _display_success_summary(console, project, project_path)

    except ValueError as e:
        print_error(str(e))
        raise SystemExit(1)
    except Exception as e:
        console.print(
            Panel(
                f"[error]✗[/error] Failed to initialize project\n\n[muted]{str(e)}[/muted]",
                title="[error]Initialization Failed[/error]",
                border_style="error",
                box=box.ROUNDED,
            )
        )
        import logging

        logging.getLogger(__name__).exception("Init failure")
        raise SystemExit(1)


def _display_proposed_plan(console: Console, plan: Any) -> None:
    """Display the proposed project plan in styled boxes."""
    # Project overview
    tech_stack = ", ".join(f"[accent]{t}[/accent]" for t in plan.tech_stack)

    overview = Text()
    overview.append(f"{plan.project_name}\n", style="header")
    overview.append(f"{plan.project_description}\n\n", style="muted")
    overview.append("Tech Stack: ", style="label")

    console.print(
        Panel(
            f"[header]{plan.project_name}[/header]\n\n"
            f"[muted]{plan.project_description}[/muted]\n\n"
            f"[label]Tech Stack:[/label] {tech_stack}",
            title="[accent]Proposed Project[/accent]",
            border_style="accent",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    # Topics table
    if plan.topics:
        console.print()
        topic_table = create_table(["Topic", "Description"])
        topic_table.title = "[header]Proposed Topics[/header]"
        for topic in plan.topics:
            topic_table.add_row(f"[accent]{topic.name}[/accent]", topic.description)
        console.print(topic_table)

    # Tickets table
    if plan.tickets:
        console.print()
        ticket_table = create_table(["Type", "Title", "Severity", "Subtasks"])
        ticket_table.title = "[header]Proposed Tickets[/header]"

        def add_to_table(tickets: list[Any], indent: int = 0) -> None:
            for t in tickets:
                type_str = "  " * indent + t.ticket_type.value.lower()
                sev_str = t.severity.value.upper() if t.severity else "MEDIUM"
                subtasks = str(len(t.children)) if t.children else "-"

                ticket_table.add_row(f"[muted]{type_str}[/muted]", t.title, sev_str, subtasks)
                if t.children:
                    add_to_table(t.children, indent + 1)

        add_to_table(plan.tickets)
        console.print(ticket_table)


def _display_success_summary(console: Console, project: CascadeProject, project_path: Path) -> None:
    """Display the success summary in a modern styled box."""
    console.print()

    # ASCII logo with success message
    logo_text = Text()
    for line in CASCADE_LOGO.strip().split("\n"):
        logo_text.append(line + "\n", style="logo")

    # Build summary content
    summary_content = (
        f"[label]Project[/label]    [accent]{project.config.name}[/accent]\n"
        f"[label]Location[/label]   [muted]{project_path}[/muted]\n"
        f"[label]Agent[/label]      [accent]{project.config.agent.default}[/accent]\n"
        f"[label]Config[/label]     [muted]{project.config_path.name}[/muted]\n\n"
        f"[header]Getting Started[/header]\n"
        f"  [accent]›[/accent] Run [white]cascade[/white] to enter interactive mode\n"
        f"  [accent]›[/accent] Run [white]cascade status[/white] to view dashboard\n"
        f"  [accent]›[/accent] Run [white]cascade ticket list[/white] to see tickets"
    )

    console.print(
        Panel(
            summary_content,
            title="[success]✓ CASCADE INITIALIZED[/success]",
            border_style="success",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
