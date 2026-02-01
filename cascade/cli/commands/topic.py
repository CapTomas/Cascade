"""Topic commands for Cascade CLI."""

from __future__ import annotations

import click

from cascade.cli.styles import (
    console,
    create_panel,
    create_table,
    print_banner,
    print_error,
    print_success,
)
from cascade.core.project import get_project
from cascade.models.enums import TicketStatus


@click.group()
@click.pass_context
def topic(ctx: click.Context) -> None:
    """Manage topics for organizing tickets."""
    pass


@topic.command("create")
@click.argument("name")
@click.option(
    "--description",
    "-d",
    default="",
    help="Topic description",
)
@click.pass_context
def create(ctx: click.Context, name: str, description: str) -> None:
    """Create a new topic."""
    try:
        project = get_project()
        new_topic = project.topics.create(name, description)

        print_success(f"Created topic: [accent]{new_topic.name}[/accent]")
        if description:
            console.print(f" [dim]{description}[/dim]")

    except ValueError as e:
        console.print(f"[warning]{e}[/warning]")
    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@topic.command("list")
@click.pass_context
def list_topics(ctx: click.Context) -> None:
    """List all topics with progress."""
    try:
        project = get_project()
        topics = project.topics.list_all()

        if not topics:
            console.print("[dim]No topics found. Use 'ccd topic create <name>' to begin.[/dim]")
            return

        print_banner("Topic Catalog")
        table = create_table(["NAME", "TICKETS", "DONE", "PROGRESS"])

        for t in topics:
            assert t.id is not None
            progress = project.topics.get_progress(t.id)
            pct = progress["percentage"]

            # Color progress
            if pct >= 100:
                pct_str = f"[success]{pct:.0f}%[/success]"
            elif pct >= 50:
                pct_str = f"[status.progress]{pct:.0f}%[/status.progress]"
            else:
                pct_str = f"[dim]{pct:.0f}%[/dim]"

            table.add_row(
                f"[accent]{t.name}[/accent]", str(progress["total"]), str(progress["done"]), pct_str
            )

        console.print(table)

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@topic.command("show")
@click.argument("name")
@click.option(
    "--status",
    "-s",
    type=click.Choice([s.value for s in TicketStatus], case_sensitive=False),
    default=None,
    help="Filter tickets by status",
)
@click.option(
    "--next",
    "execute_next",
    is_flag=True,
    help="Execute the next priority ticket in this topic",
)
@click.pass_context
def show(ctx: click.Context, name: str, status: str | None, execute_next: bool) -> None:
    """Show topic details and tickets."""
    try:
        project = get_project()
        t = project.topics.get_by_name(name)

        if not t:
            print_error(f"Topic '{name}' not found")
            raise SystemExit(1)

        if execute_next:
            # Find next ready ticket in topic
            assert t.id is not None
            tickets = project.topics.get_tickets(t.id, status=TicketStatus.READY)
            if not tickets:
                tickets = project.topics.get_tickets(t.id, status=TicketStatus.DEFINED)

            if not tickets:
                console.print(f"[yellow]No pending tickets found in topic '{t.name}'.[/yellow]")
                return

            ticket = tickets[0]
            from cascade.cli.commands.ticket import execute

            ctx.invoke(execute, ticket_id=ticket.id)
            return

        assert t.id is not None
        progress = project.topics.get_progress(t.id)

        print_banner(f"Topic: {t.name}")

        # Topic info
        info = (
            f"[label]Description:[/label] {t.description or 'No description'}\n"
            f"[label]Progress:[/label]    {progress['percentage']:.1f}%\n"
            f"[label]Activity:[/label]    {progress['done']} done, {progress['in_progress']} active, {progress['ready']} ready"
        )

        console.print(create_panel(info, border_style="dim"))

        # Tickets in topic
        assert t.id is not None
        tickets = project.topics.get_tickets(
            t.id,
            status=TicketStatus(status) if status else None,
        )

        if tickets:
            table = create_table(["#", "STATUS", "TYPE", "TITLE"])

            for ticket in tickets:
                from cascade.cli.commands.ticket import _status_style

                st_style = _status_style(ticket.status)

                table.add_row(
                    f"[id]{ticket.id}[/id]",
                    f"[{st_style}]{ticket.status.value.upper()}[/{st_style}]",
                    ticket.ticket_type.value.lower(),
                    ticket.title,
                )

            console.print(table)
        else:
            console.print("\n[dim]No tickets found in this topic.[/dim]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@topic.command("assign")
@click.argument("topic_name")
@click.argument("ticket_id", type=int)
@click.pass_context
def assign(ctx: click.Context, topic_name: str, ticket_id: int) -> None:
    """Assign a ticket to a topic."""
    try:
        project = get_project()

        # Get or create topic
        t = project.topics.get_or_create(topic_name)

        # Verify ticket exists
        ticket = project.tickets.get(ticket_id)
        if not ticket:
            print_error(f"Ticket [id]#{ticket_id}[/id] not found")
            raise SystemExit(1)

        assert t.id is not None
        project.topics.assign_ticket(t.id, ticket_id)
        print_success(f"Assigned ticket [id]#{ticket_id}[/id] to topic [accent]{t.name}[/accent]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@topic.command("unassign")
@click.argument("topic_name")
@click.argument("ticket_id", type=int)
@click.pass_context
def unassign(ctx: click.Context, topic_name: str, ticket_id: int) -> None:
    """Remove a ticket from a topic."""
    try:
        project = get_project()

        t = project.topics.get_by_name(topic_name)
        if not t:
            print_error(f"Topic '{topic_name}' not found")
            raise SystemExit(1)

        assert t.id is not None
        removed = project.topics.unassign_ticket(t.id, ticket_id)

        if removed:
            print_success(
                f"Removed ticket [id]#{ticket_id}[/id] from topic [accent]{t.name}[/accent]"
            )
        else:
            console.print(
                f"[warning]TICKET #{ticket_id}[/warning] was not assigned to [accent]{t.name}[/accent]"
            )

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@topic.command("delete")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete(ctx: click.Context, name: str, force: bool) -> None:
    """Delete a topic (does not delete tickets)."""
    try:
        project = get_project()

        t = project.topics.get_by_name(name)
        if not t:
            print_error(f"Topic '{name}' not found")
            raise SystemExit(1)

        assert t.id is not None
        ticket_count = project.topics.count_tickets(t.id)

        if not force:
            msg = f"Delete topic [accent]{name}[/accent]?"
            if ticket_count > 0:
                msg += f" [dim]({ticket_count} tickets will be unassigned)[/dim]"
            if not click.confirm(msg):
                console.print("[dim]Cancelled[/dim]")
                return

        assert t.id is not None
        project.topics.delete(t.id)
        print_success(f"Deleted topic [accent]{name}[/accent]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)
