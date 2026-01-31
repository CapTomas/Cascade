"""Status command for Cascade CLI."""

import click
from rich.console import Console

from cascade.core.project import get_project
from cascade.models.enums import TicketStatus, TicketType
from cascade.cli.styles import (
    console,
    print_banner,
    create_hud,
    create_table,
    create_panel,
    CASCADE_THEME
)


@click.command()
@click.option(
    "--health",
    is_flag=True,
    help="Show system health check",
)
@click.pass_context
def status(ctx: click.Context, health: bool) -> None:
    """Show project status overview."""
    try:
        project = get_project()

        if health:
            _show_health(project)
            return

        status_data = project.get_status()
        default_agent = project.config.agent.default if hasattr(project.config, "agent") else "none"

        # HUD Top Bar
        hud_items = [
            ("Project", status_data['name']),
            ("Agent", default_agent),
            ("Topics", str(status_data['topics'])),
        ]
        console.print(create_hud(hud_items))

        # Ticket Summary Banner
        print_banner("Activity Overview")

        from rich.table import Table
        summary_cols = ["IDLE", "ACTIVE", "BLOCKED", "DONE", "TOTAL"]
        summary_table = Table(box=None, expand=True, show_header=True, header_style="dim")
        for col in summary_cols:
            summary_table.add_column(col, justify="center")

        tickets = status_data["tickets"]
        summary_table.add_row(
            f"[status.open]{tickets['ready']}[/status.open]",
            f"[status.progress]{tickets['in_progress']}[/status.progress]",
            f"[error]{tickets['blocked']}[/error]",
            f"[status.done]{tickets['done']}[/status.done]",
            f"[bold white]{tickets['total']}[/bold white]"
        )
        console.print(summary_table)

        # Intelligence: Recommended Next Action
        print_banner("Recommended Next")

        if tickets["in_progress"] > 0:
            active = project.tickets.get_by_status(TicketStatus.IN_PROGRESS)[0]
            console.print(f"[accent]→ Resume Work:[/accent] [id]{active.id}[/id] {active.title}")
            console.print(f"  [dim]Run:[/dim] [white]cascade ticket execute {active.id}[/white]")
        elif tickets["ready"] > 0:
            ready = project.tickets.get_ready()[0]
            console.print(f"[accent]→ Execute Next:[/accent] [id]{ready.id}[/id] {ready.title}")
            console.print(f"  [dim]Run:[/dim] [white]cascade ticket execute {ready.id}[/white]")
        elif tickets["total"] == 0:
            console.print("[info]Project is empty.[/info] [dim]Create your first ticket to begin.[/dim]")
            console.print(f"  [dim]Run:[/dim] [white]cascade ticket create[/white]")
        else:
            console.print("[success]All caught up![/success] [dim]All tickets are currently complete or blocked.[/dim]")

        # Recent Accomplishments
        if tickets["total"] > 0:
            recent_done = project.tickets.get_by_status(TicketStatus.DONE)[:2]
            if recent_done:
                console.print()
                print_banner("Recent Accomplishments")
                for t in recent_done:
                    console.print(f" [success]✓[/success] [dim]#{t.id}[/dim] {t.title}")

    except FileNotFoundError as e:
        console.print(f"[error]ERROR:[/error] Not in a Cascade project.")
        console.print("[dim]Run 'cascade init' to initialize.[/dim]")
        raise SystemExit(1)


def _show_health(project) -> None:
    """Show system health check."""
    checks = []

    # Database
    try:
        project.db.fetch_one("SELECT 1")
        checks.append(("Database", True, "Connected"))
    except Exception as e:
        checks.append(("Database", False, str(e)))

    # Config
    try:
        config = project.config
        checks.append(("Config", True, f"Loaded ({config.name})"))
    except Exception as e:
        checks.append(("Config", False, str(e)))

    # Display results
    print_banner("System Health")

    table = create_table(["Component", "Status", "Details"])

    for name, ok, details in checks:
        status_text = "[success]HEALTHY[/success]" if ok else "[error]FAILED[/error]"
        table.add_row(name, status_text, details)

    console.print(table)


def _severity_color(severity) -> str:
    """Get color for severity level."""
    from cascade.models.enums import Severity

    if not severity:
        return "dim"

    return {
        Severity.CRITICAL: "bold red",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "dim",
    }.get(severity, "dim")
