"""Init command for Cascade CLI."""

import click
from pathlib import Path
from cascade.core.project import CascadeProject
from cascade.cli.styles import (
    console,
    print_banner,
    print_step,
    print_success,
    print_error,
    create_table,
    create_panel,
    get_progress
)


@click.command("init")
@click.argument("requirements", required=False)
@click.option(
    "--name", "-n",
    help="Project name",
)
@click.option(
    "--description", "-d",
    default="",
    help="Project description (if not using requirements)",
)
@click.option(
    "--tech-stack", "-t",
    multiple=True,
    help="Technologies used (if not using requirements)",
)
@click.option(
    "--path", "-p",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    default=None,
    help="Project path (defaults to current directory)",
)
@click.option(
    "--yes", "-y",
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
    generate a project plan (tickets, topics, ADRs).

    Examples:

        cascade init "Build a REST API with FastAPI"

        cascade init --name "My Project" -d "A simple project" -t python
    """
    console: Console = ctx.obj["console"]
    project_path = path or Path.cwd()

    try:
        project = CascadeProject(project_path)

        if project.is_initialized:
            console.print(
                f"[yellow]Project already initialized at {project_path}[/yellow]"
            )
            return

        # 1. Basic initialization
        project.initialize(
            name=name or project_path.name,
            description=description,
            tech_stack=list(tech_stack) if tech_stack else [],
        )

        # 2. Planning if requirements provided
        if requirements:
            with get_progress() as progress:
                task = progress.add_task("[dim]Analyzing requirements...", total=100)
                plan = project.planner.plan(requirements)
                progress.update(task, completed=100)

            # Update project config with AI-discovered info
            project.config.name = plan.project_name
            project.config.description = plan.project_description
            project.config.tech_stack = plan.tech_stack
            project.save_config()

            print_banner("Proposed Project")
            console.print(f"[white]Name:[/white] [accent]{plan.project_name}[/accent]")
            console.print(f"[dim]{plan.project_description}[/dim]")

            # Display Tech Stack
            stack_text = ", ".join(f"[cyan]{t}[/cyan]" for t in plan.tech_stack)
            console.print(f"[label]Tech Stack:[/label] {stack_text}")

            # Display Topics
            if plan.topics:
                print_banner("Proposed Topics")
                topic_table = create_table(["TOPIC", "DESCRIPTION"])
                for topic in plan.topics:
                    topic_table.add_row(f"[accent]{topic.name}[/accent]", topic.description)
                console.print(topic_table)

            # Display Tickets
            if plan.tickets:
                print_banner("Proposed Tickets")
                ticket_table = create_table(["TYPE", "TITLE", "SEVERITY", "SUBTASKS"])

                def add_to_table(tickets, indent=0):
                    for t in tickets:
                        type_str = "  " * indent + t.ticket_type.value.lower()
                        sev_style = "dim"
                        if t.severity:
                            from cascade.cli.styles import CASCADE_THEME
                            # We don't have direct access to _severity_color here easily if it's local to ticket.py
                            # But we can use common sense or import it. For now let's use dim.
                            sev_str = t.severity.value.upper()
                        else:
                            sev_str = "MEDIUM"

                        ticket_table.add_row(
                            type_str,
                            t.title,
                            sev_str,
                            str(len(t.children)) if t.children else "-"
                        )
                        if t.children:
                            add_to_table(t.children, indent + 1)

                add_to_table(plan.tickets)
                console.print(ticket_table)

            if not yes:
                console.print()
                if not click.confirm("Generate this project plan?", default=True):
                    print_success("Initialization completed (skipping plan generation).")
                    return

            project.planner.generate_tickets(plan)
            print_success("Project plan generated successfully.")

        summary = (
            f"[label]Project:[/label]  [accent]{project.config.name}[/accent]\n"
            f"[label]Location:[/label] [dim]{project_path}[/dim]\n"
            f"[label]Config:[/label]   [dim]{project.config_path.name}[/dim]\n\n"
            f"[white]Next steps:[/white]\n"
            f" [accent]→[/accent] Run [white]ccd status[/white] to view the dashboard\n"
            f" [accent]→[/accent] Run [white]ccd ticket list[/white] to see all tickets\n"
            f" [accent]→[/accent] Run [white]ccd ticket execute 1[/white] to start"
        )
        console.print(create_panel(summary, title="CASCADE INITIALIZED", border_style="green"))

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Failed to initialize project:[/red] {e}")
        logger.exception("Init failure")
        raise SystemExit(1)
