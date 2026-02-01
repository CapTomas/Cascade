"""Metrics command for Cascade CLI."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import click

from cascade.cli.styles import (
    console,
    create_hud,
    create_table,
    print_banner,
)
from cascade.core.metrics import MetricsService
from cascade.core.project import get_project


@click.command("metrics")
@click.option(
    "--days",
    "-d",
    default=7,
    help="Number of days to include in time-based metrics.",
)
@click.option(
    "--tickets",
    "-t",
    is_flag=True,
    help="Show detailed ticket metrics.",
)
@click.option(
    "--quality",
    "-q",
    is_flag=True,
    help="Show quality gate metrics.",
)
@click.option(
    "--activity",
    "-a",
    is_flag=True,
    help="Show daily activity breakdown.",
)
@click.pass_context
def metrics(
    ctx: click.Context,
    days: int,
    tickets: bool,
    quality: bool,
    activity: bool,
) -> None:
    """Show project metrics and analytics."""
    try:
        project = get_project()
        service = MetricsService(project.db)

        since = datetime.now() - timedelta(days=days)
        project_metrics = service.get_project_metrics(since=since)

        # Default: show overview
        if not any([tickets, quality, activity]):
            _show_overview(project_metrics, days)
            return

        if tickets:
            _show_ticket_metrics(project_metrics.tickets)

        if quality:
            _show_quality_metrics(project_metrics.quality)

        if activity:
            _show_activity(service, days)

    except FileNotFoundError:
        console.print("[error]ERROR:[/error] Not in a Cascade project.")
        console.print("[dim]Run 'cascade init' to initialize.[/dim]")
        raise SystemExit(1)


def _show_overview(metrics: Any, days: int) -> None:
    """Show metrics overview."""
    exec_metrics = metrics.execution
    ticket_metrics = metrics.tickets

    # HUD with key stats
    hud_items = [
        ("Executions", str(exec_metrics.total_executions)),
        ("Tokens", f"{exec_metrics.total_tokens:,}"),
        ("Tickets", str(ticket_metrics.total)),
        ("Done", str(ticket_metrics.by_status.get("DONE", 0))),
    ]
    console.print(create_hud(hud_items))

    # Execution summary
    print_banner(f"Execution Summary (Last {days} Days)")

    if exec_metrics.total_executions == 0:
        console.print("[dim]No executions recorded yet.[/dim]")
    else:
        table = create_table(["Metric", "Value"])
        table.add_row("Total Executions", str(exec_metrics.total_executions))
        table.add_row("Total Tokens", f"{exec_metrics.total_tokens:,}")
        table.add_row(
            "Avg Tokens/Execution",
            f"{exec_metrics.avg_tokens_per_execution:,.0f}",
        )
        table.add_row(
            "Total Time",
            _format_duration(exec_metrics.total_time_ms),
        )
        table.add_row(
            "Avg Time/Execution",
            _format_duration(exec_metrics.avg_time_ms_per_execution),
        )
        console.print(table)

        # Agent breakdown
        if exec_metrics.by_agent:
            console.print()
            print_banner("By Agent")
            agent_table = create_table(["Agent", "Executions", "Share"])
            total = exec_metrics.total_executions
            for agent, count in sorted(exec_metrics.by_agent.items(), key=lambda x: -x[1]):
                share = (count / total) * 100
                agent_table.add_row(agent, str(count), f"{share:.1f}%")
            console.print(agent_table)

    # Ticket summary
    console.print()
    print_banner("Ticket Summary")
    if ticket_metrics.total == 0:
        console.print("[dim]No tickets created yet.[/dim]")
    else:
        ticket_table = create_table(["Status", "Count"])
        for status, count in sorted(ticket_metrics.by_status.items()):
            ticket_table.add_row(status, str(count))
        console.print(ticket_table)

        if ticket_metrics.estimated_effort > 0:
            console.print()
            console.print(
                f"[dim]Effort Accuracy:[/dim] {ticket_metrics.effort_accuracy:.0%} "
                f"(actual {ticket_metrics.actual_effort}h / estimated {ticket_metrics.estimated_effort}h)"
            )


def _show_ticket_metrics(metrics: Any) -> None:
    """Show detailed ticket metrics."""
    print_banner("Ticket Breakdown")

    if metrics.total == 0:
        console.print("[dim]No tickets created yet.[/dim]")
        return

    # By type
    console.print("[bold]By Type:[/bold]")
    type_table = create_table(["Type", "Count", "Share"])
    for ticket_type, count in sorted(metrics.by_type.items(), key=lambda x: -x[1]):
        share = (count / metrics.total) * 100
        type_table.add_row(ticket_type, str(count), f"{share:.1f}%")
    console.print(type_table)

    # By status
    console.print()
    console.print("[bold]By Status:[/bold]")
    status_table = create_table(["Status", "Count", "Share"])
    for status, count in sorted(metrics.by_status.items(), key=lambda x: -x[1]):
        share = (count / metrics.total) * 100
        status_table.add_row(status, str(count), f"{share:.1f}%")
    console.print(status_table)


def _show_quality_metrics(metrics: Any) -> None:
    """Show quality gate metrics."""
    print_banner("Quality Gates")

    if metrics.total_runs == 0:
        console.print("[dim]No quality gate runs recorded.[/dim]")
        return

    # Overall
    console.print(
        f"[bold]Overall Pass Rate:[/bold] {metrics.pass_rate:.0%} "
        f"({metrics.passed}/{metrics.total_runs})"
    )
    console.print()

    # By gate
    gate_table = create_table(["Gate", "Passed", "Failed", "Rate"])
    for gate_name, stats in sorted(metrics.by_gate.items()):
        passed = stats["passed"]
        failed = stats["failed"]
        total = passed + failed
        rate = (passed / total) * 100 if total > 0 else 0
        gate_table.add_row(
            gate_name,
            str(passed),
            str(failed),
            f"{rate:.0f}%",
        )
    console.print(gate_table)


def _show_activity(service: MetricsService, days: int) -> None:
    """Show daily activity."""
    print_banner(f"Daily Activity (Last {days} Days)")

    activity = service.get_daily_activity(days)

    if not activity:
        console.print("[dim]No activity recorded.[/dim]")
        return

    table = create_table(["Date", "Executions", "Tokens", "Activity"])
    max_execs = max(row["executions"] for row in activity) if activity else 1

    for row in activity:
        date = row["day"]
        execs = row["executions"]
        tokens = row["tokens"]

        # Simple bar chart
        bar_len = int((execs / max_execs) * 20) if max_execs > 0 else 0
        bar = "█" * bar_len + "░" * (20 - bar_len)

        table.add_row(
            date,
            str(execs),
            f"{tokens:,}",
            f"[accent]{bar}[/accent]",
        )

    console.print(table)


def _format_duration(ms: float) -> str:
    """Format milliseconds as human-readable duration."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms / 1000:.1f}s"
    else:
        minutes = int(ms // 60000)
        seconds = (ms % 60000) / 1000
        return f"{minutes}m {seconds:.0f}s"
