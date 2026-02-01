"""Interactive settings command for Cascade CLI."""

from __future__ import annotations

import click
from rich import box
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from cascade.agents.registry import list_agents
from cascade.cli.styles import console, print_error, print_success
from cascade.core.project import get_project
from cascade.core.prompt_templates import (
    DEFAULT_NEXT_COMMAND_PROMPT,
    PROMPT_TEMPLATES,
    get_template,
)
from cascade.models.enums import TicketType


@click.group()
@click.pass_context
def settings(ctx: click.Context) -> None:
    """Interactive configuration and customization."""
    pass


@settings.command("show")
@click.pass_context
def show_settings(ctx: click.Context) -> None:
    """Display all configurable settings with current values."""
    try:
        project = get_project()
        config = project.config

        console.print()

        # Agent Settings
        _show_agent_settings(config)
        console.print()

        # Prompt Settings
        _show_prompt_settings(config)
        console.print()

        # Quality Gates
        _show_quality_settings(config)
        console.print()

        console.print("[muted]Use [white]cascade settings <category>[/white] to configure[/muted]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@settings.command("agents")
@click.pass_context
def configure_agents(ctx: click.Context) -> None:
    """Configure agent assignments for ticket types and commands."""
    try:
        project = get_project()
        available_agents = list_agents()

        console.print()
        console.print(
            Panel(
                "[header]Agent Configuration[/header]\n\n"
                "Configure which AI agents handle different ticket types and commands.",
                border_style="accent",
                box=box.ROUNDED,
            )
        )
        console.print()

        # Default agent
        console.print("[label]Default Agent[/label]")
        console.print(
            f"[muted]Current: [accent]{project.config.agent.default}[/accent][/muted]"
        )
        default = click.prompt(
            "Default agent",
            default=project.config.agent.default,
            type=click.Choice(available_agents, case_sensitive=False),
        )

        # Next command agent
        console.print()
        console.print("[label]Next Command Agent[/label]")
        console.print(
            "[muted]Specific agent for the 'cascade next' command (leave blank for default)[/muted]"
        )
        current_next = project.config.agent.next_command_agent or project.config.agent.default
        console.print(f"[muted]Current: [accent]{current_next}[/accent][/muted]")
        next_agent = click.prompt(
            "Next command agent (blank = use default)",
            default=current_next,
            type=click.Choice(available_agents + ["default"], case_sensitive=False),
            show_default=False,
        )
        if next_agent == "default":
            next_agent = None

        # Per-ticket-type orchestration
        console.print()
        console.print("[label]Ticket Type Orchestration[/label]")
        console.print(
            "[muted]Assign specific agents to ticket types (leave blank to use default)[/muted]"
        )
        orchestration = {}
        for ticket_type in TicketType:
            current_agent = project.config.agent.orchestration.get(
                ticket_type.value.lower(), "default"
            )
            console.print(f"\n[accent]{ticket_type.value}[/accent] tickets:")
            console.print(f"[muted]Current: {current_agent}[/muted]")

            agent_choice = click.prompt(
                f"  Agent for {ticket_type.value}",
                default=current_agent,
                type=click.Choice(available_agents + ["default"], case_sensitive=False),
                show_default=False,
            )
            if agent_choice != "default":
                orchestration[ticket_type.value.lower()] = agent_choice

        # Save changes
        project.config.agent.default = default
        project.config.agent.next_command_agent = next_agent
        project.config.agent.orchestration = orchestration
        project.save_config()

        console.print()
        print_success("Agent configuration updated successfully")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@settings.command("prompts")
@click.option(
    "--ticket-type",
    type=click.Choice([t.value for t in TicketType], case_sensitive=False),
    help="Configure prompts for specific ticket type",
)
@click.option("--next", "next_cmd", is_flag=True, help="Configure 'next' command prompt")
@click.option("--reset", is_flag=True, help="Reset to default prompts")
@click.pass_context
def configure_prompts(
    ctx: click.Context, ticket_type: str | None, next_cmd: bool, reset: bool
) -> None:
    """Configure AI prompts for different ticket types."""
    try:
        project = get_project()

        if reset:
            if click.confirm("Reset all prompts to defaults?"):
                project.config.prompts.task_focus = {}
                project.config.prompts.instructions = {}
                project.config.prompts.response_format = {}
                project.config.prompts.next_command_prompt = None
                project.save_config()
                print_success("Prompts reset to defaults")
            return

        if next_cmd:
            _configure_next_prompt(project)
        elif ticket_type:
            _configure_ticket_type_prompt(project, TicketType(ticket_type.upper()))
        else:
            _show_prompt_menu(project)

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@settings.command("quality-gates")
@click.pass_context
def configure_quality_gates(ctx: click.Context) -> None:
    """Configure quality gate settings."""
    try:
        project = get_project()

        console.print()
        console.print(
            Panel(
                "[header]Quality Gates Configuration[/header]\n\n"
                "Configure verification checks that run after ticket execution.",
                border_style="accent",
                box=box.ROUNDED,
            )
        )
        console.print()

        # Static Analysis
        console.print("[label]Static Analysis[/label]")
        static_enabled = click.confirm(
            "Enable static analysis gate?",
            default=project.config.quality.static_analysis.enabled,
        )

        # Unit Tests
        console.print("\n[label]Unit Tests[/label]")
        tests_enabled = click.confirm(
            "Enable unit tests gate?", default=project.config.quality.unit_tests.enabled
        )

        # Security Scan
        console.print("\n[label]Security Scan[/label]")
        security_enabled = click.confirm(
            "Enable security scan gate?", default=project.config.quality.security_scan.enabled
        )

        # Save
        project.config.quality.static_analysis.enabled = static_enabled
        project.config.quality.unit_tests.enabled = tests_enabled
        project.config.quality.security_scan.enabled = security_enabled
        project.save_config()

        console.print()
        print_success("Quality gates configuration updated")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@settings.command("edit-config")
@click.pass_context
def edit_config_file(ctx: click.Context) -> None:
    """Open the config.yaml file in your default editor."""
    try:
        project = get_project()
        click.edit(filename=str(project.config_path))
        project.reload_config()
        print_success("Configuration reloaded from file")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


def _show_agent_settings(config: Any) -> None:
    """Display agent settings."""
    agent_table = Table(
        title="[header]Agent Configuration[/header]",
        box=box.ROUNDED,
        border_style="border",
        show_header=True,
    )
    agent_table.add_column("Setting", style="label")
    agent_table.add_column("Value", style="accent")

    agent_table.add_row("Default Agent", config.agent.default)
    agent_table.add_row(
        "Next Command Agent",
        config.agent.next_command_agent or f"{config.agent.default} (default)",
    )
    agent_table.add_row("Fallback Agent", config.agent.fallback)

    console.print(agent_table)

    if config.agent.orchestration:
        console.print()
        orch_table = Table(
            title="[header]Ticket Type Orchestration[/header]",
            box=box.ROUNDED,
            border_style="border",
        )
        orch_table.add_column("Ticket Type", style="label")
        orch_table.add_column("Agent", style="accent")

        for ttype, agent in config.agent.orchestration.items():
            orch_table.add_row(ttype.upper(), agent)

        console.print(orch_table)


def _show_prompt_settings(config: Any) -> None:
    """Display prompt settings."""
    prompt_info = []

    if config.prompts.enabled:
        custom_count = (
            len(config.prompts.task_focus)
            + len(config.prompts.instructions)
            + len(config.prompts.response_format)
        )
        status = (
            f"[success]Enabled[/success] ({custom_count} customizations)"
            if custom_count > 0
            else "[muted]Enabled (using defaults)[/muted]"
        )
    else:
        status = "[muted]Disabled[/muted]"

    prompt_info.append(f"[label]Custom Prompts[/label]     {status}")
    prompt_info.append(
        f"[label]Knowledge Extraction[/label] [accent]{'Enabled' if config.prompts.include_knowledge_extraction else 'Disabled'}[/accent]"
    )

    if config.prompts.next_command_prompt:
        prompt_info.append("[label]Next Command[/label]      [success]Custom prompt configured[/success]")
    else:
        prompt_info.append("[label]Next Command[/label]      [muted]Using default[/muted]")

    console.print(
        Panel(
            "\n".join(prompt_info),
            title="[header]Prompt Configuration[/header]",
            border_style="border",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def _show_quality_settings(config: Any) -> None:
    """Display quality gate settings."""
    quality_table = Table(
        title="[header]Quality Gates[/header]", box=box.ROUNDED, border_style="border"
    )
    quality_table.add_column("Gate", style="label")
    quality_table.add_column("Status", style="accent")

    quality_table.add_row(
        "Static Analysis",
        "[success]Enabled[/success]"
        if config.quality.static_analysis.enabled
        else "[muted]Disabled[/muted]",
    )
    quality_table.add_row(
        "Unit Tests",
        "[success]Enabled[/success]"
        if config.quality.unit_tests.enabled
        else "[muted]Disabled[/muted]",
    )
    quality_table.add_row(
        "Security Scan",
        "[success]Enabled[/success]"
        if config.quality.security_scan.enabled
        else "[muted]Disabled[/muted]",
    )

    console.print(quality_table)


def _show_prompt_menu(project: Any) -> None:
    """Show interactive prompt configuration menu."""
    console.print()
    console.print(
        Panel(
            "[header]Prompt Configuration[/header]\n\n"
            "Customize AI prompts for different ticket types and commands.",
            border_style="accent",
            box=box.ROUNDED,
        )
    )
    console.print()

    choices = [f"{t.value} tickets" for t in TicketType] + ["Next command", "Back"]

    console.print("[label]What would you like to configure?[/label]")
    for i, choice in enumerate(choices, 1):
        console.print(f"  {i}. {choice}")

    selection = click.prompt("Select", type=int, default=len(choices))

    if selection == len(choices):
        return
    elif selection == len(choices) - 1:
        _configure_next_prompt(project)
    elif 1 <= selection <= len(TicketType):
        ticket_type = list(TicketType)[selection - 1]
        _configure_ticket_type_prompt(project, ticket_type)


def _configure_next_prompt(project: Any) -> None:
    """Configure the 'next' command prompt."""
    console.print()
    console.print("[header]Configure 'Next' Command Prompt[/header]")
    console.print()

    if project.config.prompts.next_command_prompt:
        console.print("[label]Current custom prompt:[/label]")
        console.print(
            Panel(
                Syntax(project.config.prompts.next_command_prompt, "markdown", theme="monokai"),
                border_style="dim",
            )
        )
    else:
        console.print("[muted]Currently using default prompt[/muted]")

    console.print()
    console.print("Options:")
    console.print("  1. Edit custom prompt")
    console.print("  2. View default prompt")
    console.print("  3. Reset to default")
    console.print("  4. Back")

    choice = click.prompt("Select", type=int, default=4)

    if choice == 1:
        current = project.config.prompts.next_command_prompt or DEFAULT_NEXT_COMMAND_PROMPT
        edited = click.edit(current)
        if edited and edited.strip():
            project.config.prompts.next_command_prompt = edited.strip()
            project.save_config()
            print_success("Next command prompt updated")
    elif choice == 2:
        console.print()
        console.print(
            Panel(
                Syntax(DEFAULT_NEXT_COMMAND_PROMPT, "markdown", theme="monokai"),
                title="Default Next Command Prompt",
                border_style="accent",
            )
        )
    elif choice == 3:
        project.config.prompts.next_command_prompt = None
        project.save_config()
        print_success("Reset to default prompt")


def _configure_ticket_type_prompt(project: Any, ticket_type: TicketType) -> None:
    """Configure prompts for a specific ticket type."""
    console.print()
    console.print(f"[header]Configure {ticket_type.value} Ticket Prompts[/header]")
    console.print()

    template = get_template(ticket_type)
    ticket_type_key = ticket_type.value

    # Show current configuration
    has_custom = any(
        [
            ticket_type_key in project.config.prompts.task_focus,
            ticket_type_key in project.config.prompts.instructions,
            ticket_type_key in project.config.prompts.response_format,
        ]
    )

    if has_custom:
        console.print("[success]Custom prompts configured for this type[/success]")
    else:
        console.print("[muted]Using default prompts[/muted]")

    console.print()
    console.print("What would you like to configure?")
    console.print("  1. Task Focus (objective/goal)")
    console.print("  2. Instructions (step-by-step guidance)")
    console.print("  3. Response Format (expected output structure)")
    console.print("  4. View all defaults for this type")
    console.print("  5. Reset this type to defaults")
    console.print("  6. Back")

    choice = click.prompt("Select", type=int, default=6)

    if choice == 1:
        _edit_task_focus(project, ticket_type_key, template)
    elif choice == 2:
        _edit_instructions(project, ticket_type_key, template)
    elif choice == 3:
        _edit_response_format(project, ticket_type_key, template)
    elif choice == 4:
        _show_default_template(ticket_type, template)
    elif choice == 5:
        _reset_ticket_type(project, ticket_type_key)


def _edit_task_focus(project: Any, ticket_type_key: str, template: Any) -> None:
    """Edit task focus for a ticket type."""
    current = project.config.prompts.task_focus.get(
        ticket_type_key, template.get_task_focus()
    )
    edited = click.edit(current)
    if edited and edited.strip():
        project.config.prompts.task_focus[ticket_type_key] = edited.strip()
        project.save_config()
        print_success("Task focus updated")


def _edit_instructions(project: Any, ticket_type_key: str, template: Any) -> None:
    """Edit instructions for a ticket type."""
    current_list = project.config.prompts.instructions.get(
        ticket_type_key, template.get_instructions()
    )
    current_text = "\n".join(f"{i+1}. {instr}" for i, instr in enumerate(current_list))

    console.print()
    console.print("[muted]Edit instructions (one per line, numbering optional):[/muted]")

    edited = click.edit(current_text)
    if edited and edited.strip():
        # Parse back to list
        lines = [
            line.strip().lstrip("0123456789. ") for line in edited.strip().split("\n") if line.strip()
        ]
        project.config.prompts.instructions[ticket_type_key] = lines
        project.save_config()
        print_success("Instructions updated")


def _edit_response_format(project: Any, ticket_type_key: str, template: Any) -> None:
    """Edit response format for a ticket type."""
    current = project.config.prompts.response_format.get(
        ticket_type_key, template.get_response_format()
    )
    edited = click.edit(current)
    if edited and edited.strip():
        project.config.prompts.response_format[ticket_type_key] = edited.strip()
        project.save_config()
        print_success("Response format updated")


def _show_default_template(ticket_type: TicketType, template: Any) -> None:
    """Show all default prompts for a ticket type."""
    console.print()
    console.print(f"[header]Default Prompts for {ticket_type.value}[/header]")
    console.print()

    console.print("[label]Task Focus:[/label]")
    console.print(Panel(template.get_task_focus(), border_style="dim"))

    console.print()
    console.print("[label]Instructions:[/label]")
    instructions_text = "\n".join(f"{i+1}. {instr}" for i, instr in enumerate(template.get_instructions()))
    console.print(Panel(instructions_text, border_style="dim"))

    console.print()
    console.print("[label]Response Format:[/label]")
    console.print(Panel(template.get_response_format(), border_style="dim"))

    console.print()
    click.pause()


def _reset_ticket_type(project: Any, ticket_type_key: str) -> None:
    """Reset a ticket type to defaults."""
    if click.confirm(f"Reset {ticket_type_key} prompts to defaults?"):
        project.config.prompts.task_focus.pop(ticket_type_key, None)
        project.config.prompts.instructions.pop(ticket_type_key, None)
        project.config.prompts.response_format.pop(ticket_type_key, None)
        project.save_config()
        print_success(f"{ticket_type_key} prompts reset to defaults")
