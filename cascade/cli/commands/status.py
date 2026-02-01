"""Status command for Cascade CLI."""

from __future__ import annotations

from typing import Any

import click
from rich import box
from rich.panel import Panel
from rich.text import Text

from cascade.cli.styles import (
    console,
    create_table,
)
from cascade.cli.ui import (
    create_status_hud,
)
from cascade.core.project import CascadeProject, get_project
from cascade.models.enums import TicketStatus


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

        console.print()

        # Main Dashboard Box
        _display_dashboard(status_data, default_agent)

    except FileNotFoundError:
        console.print(
            Panel(
                "[error]✗[/error] Not in a Cascade project.\n\n"
                "[muted]Run [white]cascade init[/white] to initialize a project in this directory.[/muted]",
                border_style="error",
                box=box.ROUNDED,
            )
        )
        raise SystemExit(1)


def _display_dashboard(status_data: dict[str, Any], agent: str) -> None:
    """Display the main dashboard."""
    tickets = status_data["tickets"]

    # Header HUD
    hud = create_status_hud(
        [
            ("Project", status_data["name"]),
            ("Agent", agent),
            ("Topics", str(status_data["topics"])),
            ("Total Tickets", str(tickets["total"])),
        ]
    )
    console.print(Panel(hud, border_style="border", box=box.ROUNDED, padding=(0, 1)))
    console.print()

    # Ticket status breakdown - visual bar
    total = tickets["total"]
    if total > 0:
        done_pct = (tickets["done"] / total) * 100
        active_pct = (tickets["in_progress"] / total) * 100
        ready_pct = (tickets["ready"] / total) * 100
        blocked_pct = (tickets["blocked"] / total) * 100
        100 - done_pct - active_pct - ready_pct - blocked_pct

        # Create visual progress bar
        bar_width = 40
        done_w = int(done_pct / 100 * bar_width)
        active_w = int(active_pct / 100 * bar_width)
        ready_w = int(ready_pct / 100 * bar_width)
        blocked_w = int(blocked_pct / 100 * bar_width)
        other_w = bar_width - done_w - active_w - ready_w - blocked_w

        bar = Text()
        bar.append("█" * done_w, style="success")
        bar.append("█" * active_w, style="status.progress")
        bar.append("█" * ready_w, style="status.ready")
        bar.append("█" * blocked_w, style="error")
        bar.append("░" * other_w, style="muted")

        # Status breakdown with bar
        status_content = Text()
        status_content.append(bar)
        status_content.append("\n\n")
        status_content.append("  [success]●[/success] Done        ", style="muted")
        status_content.append(f"{tickets['done']}", style="success")
        status_content.append("   [status.progress]●[/status.progress] Active      ", style="muted")
        status_content.append(f"{tickets['in_progress']}", style="status.progress")
        status_content.append("\n")
        status_content.append("  [status.ready]●[/status.ready] Ready       ", style="muted")
        status_content.append(f"{tickets['ready']}", style="status.ready")
        status_content.append("   [error]●[/error] Blocked     ", style="muted")
        status_content.append(f"{tickets['blocked']}", style="error")

        console.print(
            Panel(
                status_content,
                title="[header]Ticket Progress[/header]",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
    else:
        console.print(
            Panel(
                "[muted]No tickets yet. Create your first ticket to begin.[/muted]\n\n"
                "[accent]›[/accent] Run [white]cascade ticket create[/white]",
                title="[header]Ticket Progress[/header]",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    console.print()

    # Recommended action
    _display_recommendations(tickets)


def _display_recommendations(tickets: dict[str, int]) -> None:
    """Display recommended next actions."""
    from cascade.core.project import get_project

    project = get_project()

    content = Text()

    if tickets["in_progress"] > 0:
        # Resume work
        active = project.tickets.get_by_status(TicketStatus.IN_PROGRESS)[0]
        content.append("Resume Work\n", style="header")
        content.append(f"[accent]#{active.id}[/accent] {active.title}\n\n", style="white")
        content.append(
            f"[accent]›[/accent] Run [white]cascade ticket execute {active.id}[/white]",
            style="muted",
        )
    elif tickets["ready"] > 0:
        # Execute next
        ready = project.tickets.get_ready()[0]
        content.append("Execute Next\n", style="header")
        content.append(f"[accent]#{ready.id}[/accent] {ready.title}\n\n", style="white")
        content.append(
            f"[accent]›[/accent] Run [white]cascade ticket execute {ready.id}[/white]",
            style="muted",
        )
    elif tickets["total"] == 0:
        # Empty project
        content.append("Get Started\n", style="header")
        content.append("Create your first ticket to begin work.\n\n", style="muted")
        content.append("[accent]›[/accent] Run [white]cascade ticket create[/white]", style="muted")
    else:
        # Check for defined tickets
        defined_count = tickets["total"] - (
            tickets["done"] + tickets["blocked"] + tickets["ready"] + tickets["in_progress"]
        )
        if defined_count > 0:
            content.append("Activate Tickets\n", style="header")
            content.append(f"{defined_count} tickets are defined but not ready.\n\n", style="muted")
            content.append(
                "[accent]›[/accent] Run [white]cascade ticket ready <id>[/white] to activate",
                style="muted",
            )
        else:
            content.append("All Caught Up!\n", style="header success")
            content.append("All tickets are complete or blocked.\n\n", style="muted")
            content.append("[success]✓[/success] Great work!", style="success")

    console.print(
        Panel(
            content,
            title="[accent]Recommended[/accent]",
            border_style="accent",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    # Recent accomplishments
    if tickets["total"] > 0:
        recent_done = project.tickets.get_by_status(TicketStatus.DONE)[:3]
        if recent_done:
            console.print()
            accomplishments = Text()
            for t in recent_done:
                accomplishments.append("[success]✓[/success] ", style="success")
                accomplishments.append(f"[muted]#{t.id}[/muted] ", style="muted")
                accomplishments.append(f"{t.title}\n")

            console.print(
                Panel(
                    accomplishments,
                    title="[header]Recent Accomplishments[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                    padding=(0, 2),
                )
            )


def _show_health(project: CascadeProject) -> None:
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

    # Agent
    try:
        from cascade.agents.registry import get_agent

        agent = get_agent(project.config.agent.default)
        available = agent.is_available()
        if available:
            checks.append(("Agent", True, f"{project.config.agent.default} ready"))
        else:
            checks.append(("Agent", False, f"{project.config.agent.default} not available"))
    except Exception as e:
        checks.append(("Agent", False, str(e)))

    # Display results
    console.print()
    table = create_table(["Component", "Status", "Details"])
    table.title = "[header]System Health[/header]"

    for name, ok, details in checks:
        status_text = "[success]● HEALTHY[/success]" if ok else "[error]● FAILED[/error]"
        table.add_row(name, status_text, details)

    console.print(table)


def _severity_color(severity: Any) -> str:
    """Get color for severity level."""
    from cascade.models.enums import Severity

    if not severity:
        return "muted"

    return {
        Severity.CRITICAL: "bold red",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "muted",
    }.get(severity, "muted")
