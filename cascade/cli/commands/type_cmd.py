"""Type commands for Cascade CLI."""

from __future__ import annotations

import click

from cascade.cli.styles import console, create_table, print_banner, print_error
from cascade.core.project import get_project
from cascade.models.enums import TicketStatus, TicketType


@click.command("type")
@click.argument(
    "ticket_type",
    type=click.Choice([t.value for t in TicketType], case_sensitive=False),
)
@click.option(
    "--next",
    "execute_next",
    is_flag=True,
    help="Execute the next priority ticket of this type",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=50,
    help="Maximum tickets to show",
)
@click.pass_context
def type_cmd(ctx: click.Context, ticket_type: str, execute_next: bool, limit: int) -> None:
    """List tickets of a specific type or execute the next one."""
    try:
        project = get_project()
        ttype = TicketType(ticket_type.upper())

        if execute_next:
            # Find next ready ticket of this type
            tickets = project.tickets.list_all(
                status=TicketStatus.READY, ticket_type=ttype, limit=1
            )

            if not tickets:
                # Try finding DEFINED if no READY
                tickets = project.tickets.list_all(
                    status=TicketStatus.DEFINED, ticket_type=ttype, limit=1
                )

            if not tickets:
                console.print(f"[yellow]No pending tickets of type {ttype.value} found.[/yellow]")
                return

            ticket = tickets[0]

            # We invoke the ticket execute command
            from cascade.cli.commands.ticket import execute

            ctx.invoke(execute, ticket_id=ticket.id)
            return

        # Regular listing
        tickets = project.tickets.list_all(ticket_type=ttype, limit=limit)

        if not tickets:
            console.print(f"[dim]No tickets of type {ttype.value} found.[/dim]")
            return

        print_banner(f"Tickets: {ttype.value}")
        table = create_table(["#", "STATUS", "SEVERITY", "TITLE"])

        from cascade.cli.commands.ticket import _severity_color, _status_style

        for t in tickets:
            st_style = _status_style(t.status)
            sev_style = _severity_color(t.severity)

            table.add_row(
                f"[id]{t.id}[/id]",
                f"[{st_style}]{t.status.value.upper()}[/{st_style}]",
                f"[{sev_style}]{t.severity.value.upper() if t.severity else '-'}[/{sev_style}]",
                t.title,
            )

        console.print(table)

    except FileNotFoundError:
        print_error("Not a Cascade project.")
        raise SystemExit(1) from None
    except Exception as e:
        print_error(f"Failed to process type command: {e}")
        raise SystemExit(1) from e
