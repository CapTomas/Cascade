"""Agents commands for Cascade CLI."""

from __future__ import annotations

import click

from cascade.agents.registry import get_agent, list_agents
from cascade.cli.styles import console, create_panel, create_table, print_banner
from cascade.core.project import get_project


@click.group(invoke_without_command=True)
@click.pass_context
def agents(ctx: click.Context) -> None:
    """List and inspect available agents."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_cmd)


@agents.command("list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List available agents."""
    print_banner("Available Agents")

    table = create_table(["NAME", "STATUS", "CAPABILITIES"])

    # Get current default agent
    default_agent = None
    try:
        project = get_project()
        default_agent = project.config.agent.default
    except Exception:
        pass

    for name in list_agents():
        agent = get_agent(name)
        ok = agent.is_available()
        status_text = "[success]ONLINE[/success]" if ok else "[dim]OFFLINE[/dim]"
        capabilities = ", ".join(sorted(c.value for c in agent.get_capabilities().capabilities))

        name_display = name
        if name == default_agent:
            name_display = f"[accent]{name}[/accent] [dim](active)[/dim]"
        else:
            name_display = f"[white]{name}[/white]"

        table.add_row(name_display, status_text, capabilities or "-")

    console.print(table)


@agents.command("show")
@click.argument("name")
@click.pass_context
def show_cmd(ctx: click.Context, name: str) -> None:
    """Show details for an agent."""
    try:
        agent = get_agent(name)
    except KeyError:
        console.print(f"[error]Unknown agent:[/error] {name}")
        raise SystemExit(1)

    caps = agent.get_capabilities()

    print_banner(f"Agent: {agent.get_name()}")

    info = (
        f"[label]Status:[/label]      {'[success]ONLINE[/success]' if agent.is_available() else '[dim]OFFLINE[/dim]'}\n"
        f"[label]Token Limit:[/label] {agent.get_token_limit()}\n"
        f"[label]Streaming:[/label]   {'[success]YES[/success]' if caps.supports_streaming else '[dim]NO[/dim]'}\n"
        f"[label]Tools:[/label]       {'[success]YES[/success]' if caps.supports_tools else '[dim]NO[/dim]'}\n\n"
        f"[label]Capabilities:[/label]\n [dim]•[/dim] "
        + "\n [dim]•[/dim] ".join(sorted(c.value for c in caps.capabilities))
    )

    console.print(create_panel(info, border_style="dim"))


@agents.command("current")
@click.pass_context
def current_cmd(ctx: click.Context) -> None:
    """Show current default and fallback agents."""
    try:
        project = get_project()

        print_banner("Agent Configuration")

        info = (
            f"[label]Primary:[/label]  [accent]{project.config.agent.default}[/accent]\n"
            f"[label]Fallback:[/label] [white]{project.config.agent.fallback}[/white]"
        )
        console.print(create_panel(info, border_style="dim"))

    except FileNotFoundError as exc:
        console.print(f"[error]ERROR:[/error] {exc}")
        raise SystemExit(1)
