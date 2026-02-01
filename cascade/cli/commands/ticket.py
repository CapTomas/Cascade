"""Ticket commands for Cascade CLI."""

from __future__ import annotations

from typing import Any

import click
from rich import box
from rich.console import Console
from rich.panel import Panel

from cascade.agents.registry import get_agent, resolve_agent_name
from cascade.cli.styles import (
    console,
    create_panel,
    create_table,
    print_banner,
    print_error,
    print_info,
    print_success,
)
from cascade.core.executor import TicketExecutor
from cascade.core.project import get_project
from cascade.models.enums import Severity, TicketStatus, TicketType
from cascade.utils.git import GitProvider


@click.group()
@click.pass_context
def ticket(ctx: click.Context) -> None:
    """Manage tickets."""
    pass


@ticket.command("create")
@click.option(
    "--title",
    "-t",
    prompt="Ticket title",
    help="Ticket title",
)
@click.option(
    "--type",
    "-T",
    "ticket_type",
    type=click.Choice([t.value for t in TicketType], case_sensitive=False),
    default=TicketType.TASK.value,
    help="Ticket type",
)
@click.option(
    "--description",
    "-d",
    default="",
    help="Ticket description",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice([s.value for s in Severity], case_sensitive=False),
    default=None,
    help="Ticket severity",
)
@click.option(
    "--parent",
    "-p",
    type=int,
    default=None,
    help="Parent ticket ID",
)
@click.option(
    "--acceptance",
    "-a",
    default="",
    help="Acceptance criteria",
)
@click.option(
    "--topic",
    multiple=True,
    help="Assign to topic(s)",
)
@click.pass_context
def create(
    ctx: click.Context,
    title: str,
    ticket_type: str,
    description: str,
    severity: str | None,
    parent: int | None,
    acceptance: str,
    topic: tuple[str, ...],
) -> None:
    """Create a new ticket."""
    try:
        project = get_project()

        new_ticket = project.tickets.create(
            title=title,
            ticket_type=TicketType(ticket_type),
            description=description,
            severity=Severity(severity) if severity else None,
            parent_ticket_id=parent,
            acceptance_criteria=acceptance,
        )

        # Assign to topics
        for topic_name in topic:
            t = project.topics.get_or_create(topic_name)
            assert t.id is not None
            assert new_ticket.id is not None
            project.topics.assign_ticket(t.id, new_ticket.id)

        print_success(f"Created ticket [ticket.id]#{new_ticket.id}[/ticket.id]: {new_ticket.title}")

        if topic:
            console.print(f"[dim]Assigned to topics: {', '.join(topic)}[/dim]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)
    except Exception as e:
        print_error(f"Failed to create ticket: {e}")
        raise SystemExit(1)


@ticket.command("show")
@click.argument("ticket_id", type=int)
@click.pass_context
def show(ctx: click.Context, ticket_id: int) -> None:
    """Show ticket details."""
    try:
        project = get_project()
        t = project.tickets.get(ticket_id)

        if not t:
            print_error(f"Ticket #{ticket_id} not found")
            raise SystemExit(1)

        # Get topics
        topics = project.topics.get_topics_for_ticket(ticket_id)
        topic_names = ", ".join(tp.name for tp in topics) if topics else "None"

        # Get dependencies
        blocking = project.tickets.get_blocking_tickets(ticket_id)

        status_style = _status_style(t.status)
        severity_style = _severity_color(t.severity)

        content = (
            f"[label]Type:[/label]      {t.ticket_type.value.lower()}\n"
            f"[label]Status:[/label]    [{status_style}]{t.status.value.upper()}[/{status_style}]\n"
            f"[label]Severity:[/label]  [{severity_style}]{t.severity.value.upper() if t.severity else '-'}[/{severity_style}]\n"
            f"[label]Priority:[/label]  {t.priority_score:.1f}\n"
            f"[label]Topics:[/label]    {topic_names}\n"
            f"\n[bold white]Description:[/bold white]\n{t.description or 'No description'}\n"
            f"\n[bold white]Acceptance Criteria:[/bold white]\n{t.acceptance_criteria or 'Not defined'}\n"
        )

        if t.affected_files:
            content += "\n[bold white]Affected Files:[/bold white]\n"
            for f in t.affected_files:
                content += f" [dim]•[/dim] {f}\n"

        if blocking:
            content += "\n[bold white]Blocked By:[/bold white]\n"
            for b in blocking:
                content += f" [error]![/error] [id]#{b.id}[/id]: {b.title} ({b.status.value})\n"

        console.print(
            Panel(
                content,
                title=f"[header]Ticket #{t.id}[/header]: [accent]{t.title}[/accent]",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    except FileNotFoundError:
        print_error("Not a Cascade project.")
        console.print("[dim]Run 'cascade init' to initialize a project in this directory.[/dim]")
        raise SystemExit(1)
    except Exception as e:
        print_error(f"Failed to show ticket: {e}")
        raise SystemExit(1)


@ticket.command("list")
@click.option(
    "--status",
    "-s",
    type=click.Choice([s.value for s in TicketStatus], case_sensitive=False),
    default=None,
    help="Filter by status",
)
@click.option(
    "--type",
    "-t",
    "ticket_type",
    type=click.Choice([t.value for t in TicketType], case_sensitive=False),
    default=None,
    help="Filter by type",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=50,
    help="Maximum tickets to show",
)
@click.pass_context
def list_tickets(
    ctx: click.Context,
    status: str | None,
    ticket_type: str | None,
    limit: int,
) -> None:
    """List tickets with optional filters."""
    try:
        project = get_project()

        tickets = project.tickets.list_all(
            status=TicketStatus(status) if status else None,
            ticket_type=TicketType(ticket_type) if ticket_type else None,
            limit=limit,
        )

        if not tickets:
            console.print(
                Panel(
                    "[muted]No tickets found.[/muted]\n\n"
                    "[accent]›[/accent] Run [white]cascade ticket create[/white] to create one",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )
            return

        console.print()
        table = create_table(["#", "Type", "Status", "Severity", "Title"])
        table.title = "[header]Ticket Catalog[/header]"

        for t in tickets:
            st = t.status.value.upper()
            status_style = _status_style(t.status)
            severity_style = _severity_color(t.severity)

            table.add_row(
                f"[id]{t.id}[/id]",
                t.ticket_type.value.lower(),
                f"[{status_style}]{st}[/{status_style}]",
                f"[{severity_style}]{t.severity.value.upper() if t.severity else '-'}[/{severity_style}]",
                t.title,
            )

        console.print(table)

    except FileNotFoundError:
        print_error("Not a Cascade project.")
        raise SystemExit(1)
    except Exception as e:
        print_error(f"Failed to list tickets: {e}")
        raise SystemExit(1)


@ticket.command("update")
@click.argument("ticket_id", type=int)
@click.option("--title", "-t", default=None, help="New title")
@click.option("--description", "-d", default=None, help="New description")
@click.option(
    "--status",
    "-s",
    type=click.Choice([s.value for s in TicketStatus], case_sensitive=False),
    default=None,
    help="New status",
)
@click.option(
    "--severity",
    type=click.Choice([s.value for s in Severity], case_sensitive=False),
    default=None,
    help="New severity",
)
@click.option("--acceptance", "-a", default=None, help="New acceptance criteria")
@click.pass_context
def update(
    ctx: click.Context,
    ticket_id: int,
    title: str | None,
    description: str | None,
    status: str | None,
    severity: str | None,
    acceptance: str | None,
) -> None:
    """Update ticket fields."""
    console: Console = ctx.obj["console"]

    try:
        project = get_project()

        # Build updates dict
        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = TicketStatus(status)
        if severity is not None:
            updates["severity"] = Severity(severity)
        if acceptance is not None:
            updates["acceptance_criteria"] = acceptance

        if not updates:
            console.print("[yellow]No updates specified[/yellow]")
            return

        updated = project.tickets.update(ticket_id, **updates)

        if not updated:
            console.print(f"[red]Ticket #{ticket_id} not found[/red]")
            raise SystemExit(1)

        console.print(f"[green]Updated ticket #{ticket_id}[/green]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@ticket.command("ready")
@click.argument("ticket_ids", type=int, nargs=-1, required=True)
@click.pass_context
def mark_ready(ctx: click.Context, ticket_ids: tuple[int, ...]) -> None:
    """Mark ticket(s) as ready for execution."""
    console: Console = ctx.obj["console"]

    try:
        project = get_project()
        success_count = 0

        for ticket_id in ticket_ids:
            # Check dependencies
            if project.tickets.has_unmet_dependencies(ticket_id):
                blocking = project.tickets.get_blocking_tickets(ticket_id)
                console.print(f"[red]Cannot mark #{ticket_id} ready - blocked by:[/red]")
                for b in blocking:
                    if not b.is_complete:
                        console.print(f"  • #{b.id}: {b.title} ({b.status.value})")
                continue

            updated = project.tickets.update_status(ticket_id, TicketStatus.READY)

            if not updated:
                console.print(f"[red]Ticket #{ticket_id} not found[/red]")
                continue

            console.print(f"[green]Ticket #{ticket_id} marked READY[/green]")
            success_count += 1

        if len(ticket_ids) > 1:
            print_success(f"Successfully marked {success_count}/{len(ticket_ids)} tickets as READY")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@ticket.command("block")
@click.argument("ticket_id", type=int)
@click.option("--reason", "-r", default="", help="Block reason")
@click.pass_context
def mark_blocked(ctx: click.Context, ticket_id: int, reason: str) -> None:
    """Mark ticket as blocked."""
    try:
        project = get_project()

        updates: dict[str, Any] = {"status": TicketStatus.BLOCKED}
        if reason:
            t = project.tickets.get(ticket_id)
            if t:
                metadata = t.metadata or {}
                metadata["block_reason"] = reason
                updates["metadata"] = metadata

        updated = project.tickets.update(ticket_id, **updates)

        if not updated:
            console.print(f"[red]Ticket #{ticket_id} not found[/red]")
            raise SystemExit(1)

        console.print(f"[yellow]Ticket #{ticket_id} marked BLOCKED[/yellow]")
        if reason:
            console.print(f"[dim]Reason: {reason}[/dim]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@ticket.command("delete")
@click.argument("ticket_id", type=int)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete(ctx: click.Context, ticket_id: int, force: bool) -> None:
    """Delete a ticket."""
    console: Console = ctx.obj["console"]

    try:
        project = get_project()
        t = project.tickets.get(ticket_id)

        if not t:
            console.print(f"[red]Ticket #{ticket_id} not found[/red]")
            raise SystemExit(1)

        if not force:
            if not click.confirm(f"Delete ticket #{ticket_id}: {t.title}?"):
                console.print("[dim]Cancelled[/dim]")
                return

        project.tickets.delete(ticket_id)
        console.print(f"[green]Deleted ticket #{ticket_id}[/green]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@ticket.command("depends")
@click.argument("ticket_id", type=int)
@click.argument("depends_on_id", type=int)
@click.option(
    "--remove",
    "-r",
    is_flag=True,
    help="Remove dependency instead of adding",
)
@click.pass_context
def dependency(
    ctx: click.Context,
    ticket_id: int,
    depends_on_id: int,
    remove: bool,
) -> None:
    """Add or remove ticket dependency."""
    console: Console = ctx.obj["console"]

    try:
        project = get_project()

        if remove:
            project.tickets.remove_dependency(ticket_id, depends_on_id)
            console.print(
                f"[green]Removed dependency: #{ticket_id} no longer depends on #{depends_on_id}[/green]"
            )
        else:
            project.tickets.add_dependency(ticket_id, depends_on_id)
            console.print(
                f"[green]Added dependency: #{ticket_id} depends on #{depends_on_id}[/green]"
            )

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@ticket.command("execute")
@click.argument("ticket_ids", type=int, nargs=-1, required=True)
@click.option("--agent", "-A", help="Override default agent")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option("--dry-run", is_flag=True, help="Show the prompt and exit without calling the agent")
@click.pass_context
def execute(
    ctx: click.Context,
    ticket_ids: tuple[int, ...],
    agent: str | None,
    yes: bool,
    dry_run: bool = False,
) -> None:
    """Execute one or more tickets."""
    try:
        project = get_project()

        # Resolve agent
        if agent:
            agent_name = agent
        else:
            # Peek at first ticket to determine agent
            first_ticket_id = ticket_ids[0]
            t = project.tickets.get(first_ticket_id)
            if t:
                # Use duck typing for config as Pydantic model has same fields
                agent_name = resolve_agent_name(t.ticket_type.value, project.config.agent)
            else:
                agent_name = project.config.agent.default

        try:
            agent_instance = get_agent(agent_name)
        except KeyError:
            print_error(f"Unknown agent: {agent_name}")
            raise SystemExit(1)

        is_batch = len(ticket_ids) > 1
        banner_text = (
            f"Execution: #{ticket_ids[0]}"
            if not is_batch
            else f"Batch Execution: {', '.join(map(str, ticket_ids))}"
        )
        print_banner(banner_text)

        executor = TicketExecutor(
            agent=agent_instance,
            context_builder=project.context_builder,
            prompt_builder=project.prompt_builder,
            ticket_manager=project.tickets,
            quality_gates=project.quality_gates,
            knowledge_base=project.kb,
            git_provider=GitProvider(project.root),
        )

        def confirm_callback(tickets: list[Any], prompt: str) -> bool:
            if yes:
                return True
            console.print(create_panel(prompt, title="AGENT PROMPT", border_style="dim"))

            label = f"Proceed with {agent_name}?"
            if is_batch:
                label = f"Proceed with batch of {len(tickets)} tickets using {agent_name}?"

            return click.confirm(f"\n{label}")

        def streaming_callback(chunk: str) -> None:
            """Show basic streaming progress."""
            # Only used if progress bar is active
            pass

        if agent_name == "manual":
            # Manual agent: No progress bar, direct console interaction
            print_info("Gathering context for manual execution...")
            if is_batch:
                result = executor.execute_batch(
                    list(ticket_ids), confirm_callback=confirm_callback, dry_run=dry_run
                )
            else:
                result = executor.execute(
                    ticket_ids[0],
                    confirm_callback=lambda t, p: confirm_callback([t], p),
                    dry_run=dry_run,
                )
        else:
            # Automated agent: Use progress bar
            from cascade.cli.styles import get_progress

            with get_progress() as progress:
                task = progress.add_task("[dim]Initializing...", total=100)

                def wrapped_confirm(tickets: list[Any], prompt: str) -> bool:
                    progress.stop()
                    res = confirm_callback(tickets, prompt)
                    progress.start()
                    return res

                def bar_streaming(chunk: str) -> None:
                    progress.update(
                        task, description=f"[info]Agent Working: {chunk[:30]}...[/info]"
                    )

                progress.update(task, completed=20, description="[info]Gathering context...[/info]")
                progress.update(task, completed=40, description="[info]Contacting agent...[/info]")

                if is_batch:
                    result = executor.execute_batch(
                        list(ticket_ids),
                        confirm_callback=wrapped_confirm,
                        dry_run=dry_run,
                        streaming_callback=bar_streaming,
                    )
                else:
                    result = executor.execute(
                        ticket_ids[0],
                        confirm_callback=lambda t, p: wrapped_confirm([t], p),
                        dry_run=dry_run,
                        streaming_callback=bar_streaming,
                    )
                progress.update(
                    task, completed=80, description="[info]Running quality gates...[/info]"
                )
                progress.update(task, completed=100, description="[success]Completed[/success]")

        if dry_run:
            print_banner("Dry Run Prompt Preview")
            console.print(create_panel(result.agent_response, title="PROMPT"))
            console.print("\n[yellow]No changes were made. Agent was not contacted.[/yellow]")
            return

        if result.success:
            id_str = f"#{ticket_ids[0]}" if not is_batch else f"Batch {list(ticket_ids)}"
            print_success(f"Execution {id_str} successful.")

            if result.gate_results:
                print_banner("Quality Validation")
                for gr in result.gate_results.results:
                    st = "[success]PASSED[/success]" if gr.passed else "[error]FAILED[/error]"
                    console.print(f" {st:15} {gr.gate_name}")

            console.print(
                f"\n[dim]Time: {result.execution_time_ms}ms  |  Tokens: {result.token_usage}[/dim]"
            )
        else:
            print_error(f"Execution failed: {result.error}")
            raise SystemExit(1)

    except FileNotFoundError:
        print_error("Not in a Cascade project.")
        raise SystemExit(1)
    except Exception as e:
        print_error(f"Unexpected failure: {e}")
        raise SystemExit(1)


def _status_style(status: TicketStatus) -> str:
    """Get rich style for ticket status."""
    return {
        TicketStatus.DONE: "status.done",
        TicketStatus.IN_PROGRESS: "status.progress",
        TicketStatus.BLOCKED: "error",
        TicketStatus.READY: "status.open",
    }.get(status, "dim")


def _severity_color(severity: Severity | None) -> str:
    """Get color for severity level."""
    if not severity:
        return "dim"

    return {
        Severity.CRITICAL: "bold red",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "dim",
    }.get(severity, "dim")
