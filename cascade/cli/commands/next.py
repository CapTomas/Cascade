"""Next command for Cascade CLI."""

from __future__ import annotations

import re

import click

from cascade.agents.registry import get_agent
from cascade.cli.styles import console, create_panel, print_banner, print_error
from cascade.core.project import get_project
from cascade.models.enums import TicketStatus, TicketType


@click.command("next")
@click.option("--topic", "topic_name", help="Suggest within topic")
@click.option(
    "--type",
    "ticket_type",
    type=click.Choice([t.value for t in TicketType], case_sensitive=False),
    help="Suggest within ticket type",
)
@click.option("--agent", "-A", help="Override default agent for selection")
@click.pass_context
def next_cmd(
    ctx: click.Context, topic_name: str | None, ticket_type: str | None, agent: str | None
) -> None:
    """AI suggests the next ticket to work on."""
    try:
        project = get_project()

        # 1. Gather tickets
        if topic_name:
            t = project.topics.get_by_name(topic_name)
            if not t:
                print_error(f"Topic '{topic_name}' not found")
                return
            assert t.id is not None
            tickets = project.topics.get_tickets(t.id, status=TicketStatus.READY)
        elif ticket_type:
            ttype = TicketType(ticket_type.upper())
            tickets = project.tickets.list_all(status=TicketStatus.READY, ticket_type=ttype)
        else:
            tickets = project.tickets.list_all(status=TicketStatus.READY)

        if not tickets:
            console.print(
                "[yellow]No tickets are currently READY. Use 'ccd status' to see pending work.[/yellow]"
            )
            return

        if len(tickets) == 1:
            ticket = tickets[0]
            assert ticket.id is not None
            console.print(
                f"[info]Only one ticket is READY:[/info] [id]#{ticket.id}[/id]: {ticket.title}"
            )
            if click.confirm("\nExecute it?"):
                from cascade.cli.commands.ticket import execute

                ctx.invoke(execute, ticket_id=ticket.id)
            return

        # 2. Call AI for selection
        agent_name = agent or project.config.agent.default
        agent_instance = get_agent(agent_name)

        print_banner("AI Suggestion")
        console.print(f"[dim]Analyzing {len(tickets)} READY tickets using {agent_name}...[/dim]")

        prompt = project.prompt_builder.build_suggestion_prompt(tickets, topic_name)
        response = agent_instance.execute(prompt)

        if not response.success:
            print_error(f"AI failed to provide a suggestion: {response.error}")
            return

        # 3. Parse suggestion
        content = response.content
        match = re.search(r"SELECTION:\s*(.*)", content)
        type_match = re.search(r"TYPE:\s*(\w+)", content)
        rationale_match = re.search(r"RATIONALE:\s*(.*)", content, re.DOTALL)

        if not match:
            print_error("AI response did not follow formatting rules (missing SELECTION).")
            console.print(create_panel(content, title="RAW RESPONSE"))
            return

        selection_str = match.group(1).strip()
        is_batch = type_match and type_match.group(1).upper() == "BATCH"
        rationale = (
            rationale_match.group(1).strip() if rationale_match else "No rationale provided."
        )

        # Extract IDs - handle #1, #2 or 1, 2
        ticket_ids = [int(i.strip().replace("#", "")) for i in re.findall(r"#?\d+", selection_str)]

        if not ticket_ids:
            print_error(f"AI failed to specify valid ticket IDs in selection: {selection_str}")
            return

        selected_tickets = [t for t in tickets if t.id in ticket_ids]
        if len(selected_tickets) != len(ticket_ids):
            found_ids = [t.id for t in selected_tickets]
            missing = [tid for tid in ticket_ids if tid not in found_ids]
            print_error(f"AI selected non-existent or unready tickets: {missing}")
            return

        # 4. Present to human
        if is_batch:
            titles = "\n".join([f"- [id]#{t.id}[/id]: {t.title}" for t in selected_tickets])
            msg = f"[bold white]Recommended Batch:[/bold white]\n{titles}\n\n[bold white]Rationale:[/bold white]\n{rationale}"
        else:
            sel_t = selected_tickets[0]
            msg = f"[bold white]Selected Ticket:[/bold white] [id]#{sel_t.id}[/id]: {sel_t.title}\n\n[bold white]Rationale:[/bold white]\n{rationale}"

        console.print(create_panel(msg, title="Recommendation", border_style="green"))

        if click.confirm("\nProceed with this selection?"):
            from cascade.cli.commands.ticket import execute

            ctx.invoke(execute, ticket_ids=tuple(ticket_ids))

    except FileNotFoundError:
        print_error("Not a Cascade project.")
        raise SystemExit(1)
    except Exception as e:
        print_error(f"Failed to get next suggestion: {e}")
        raise SystemExit(1)
