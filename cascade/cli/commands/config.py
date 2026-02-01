"""Config commands for Cascade CLI."""

from __future__ import annotations

from typing import Any

import click
import yaml
from rich import box
from rich.panel import Panel
from rich.syntax import Syntax

from cascade.agents.registry import list_agents
from cascade.cli.styles import (
    console,
    create_table,
    print_error,
    print_success,
)
from cascade.cli.themes import THEMES, get_current_theme, get_theme_manager
from cascade.core.project import get_project


@click.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Manage project configuration."""
    pass


@config.command("show")
@click.pass_context
def show(ctx: click.Context) -> None:
    """Show current configuration."""
    try:
        project = get_project()
        config_dict = project.config.to_dict()

        # Settings-style display
        console.print()

        # Project section
        project_info = (
            f"[label]Name[/label]         [accent]{config_dict.get('project', {}).get('name', 'N/A')}[/accent]\n"
            f"[label]Description[/label]  [muted]{config_dict.get('project', {}).get('description', 'N/A')}[/muted]\n"
            f"[label]Tech Stack[/label]   [accent]{', '.join(config_dict.get('project', {}).get('tech_stack', []))}[/accent]"
        )
        console.print(
            Panel(
                project_info,
                title="[header]⚙ Project[/header]",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

        console.print()

        # Agent section
        agent_config = config_dict.get("agent", {})
        agent_info = (
            f"[label]Default[/label]   [accent]{agent_config.get('default', 'N/A')}[/accent]\n"
            f"[label]Fallback[/label]  [muted]{agent_config.get('fallback', 'N/A')}[/muted]"
        )
        console.print(
            Panel(
                agent_info,
                title="[header]⚙ Agent[/header]",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

        console.print()

        # Theme section
        current_theme = get_current_theme()
        theme_info = (
            f"[label]Current[/label]  [accent]{current_theme.name}[/accent]\n"
            f"[label]Colors[/label]   [{current_theme.primary}]■[/{current_theme.primary}] [{current_theme.accent}]■[/{current_theme.accent}] [{current_theme.success}]■[/{current_theme.success}]"
        )
        console.print(
            Panel(
                theme_info,
                title="[header]⚙ Theme[/header]",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

        console.print()
        console.print(
            "[muted]Run [white]cascade config set <key> <value>[/white] to modify settings[/muted]"
        )
        console.print("[muted]Run [white]cascade config edit[/white] to open in editor[/muted]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def set_config(ctx: click.Context, key: str, value: str) -> None:
    """
    Set a configuration value.

    KEY uses dot notation for nested values (e.g., 'agent.default').

    Examples:

        cascade config set agent.default claude-cli

        cascade config set quality_gates.unit_tests.enabled true
    """
    try:
        project = get_project()

        # Special handling for theme
        if key == "theme":
            tm = get_theme_manager()
            if tm.set_theme(value):
                print_success(f"Theme set to [accent]{value}[/accent]")
            else:
                print_error(f"Unknown theme: {value}")
                console.print(f"[muted]Available: {', '.join(tm.list_themes())}[/muted]")
                raise SystemExit(1)
            return

        # Parse the key path
        parts = key.split(".")
        config_dict = project.config.to_dict()

        # Navigate to parent
        current = config_dict
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Convert value type
        final_key = parts[-1]
        converted_value = _convert_value(value)

        # Validate agent names when setting defaults
        if key in ("agent.default", "agent.fallback"):
            if not isinstance(converted_value, str) or converted_value not in list_agents():
                print_error(f"Invalid agent: {converted_value}")
                console.print(f"[muted]Available: {', '.join(list_agents())}[/muted]")
                raise SystemExit(1)
        current[final_key] = converted_value

        # Reload config from dict and save
        from cascade.models.project import ProjectConfig

        project._config = ProjectConfig._from_dict(config_dict)
        project.save_config()

        print_success(f"Set [accent]{key}[/accent] = [white]{converted_value}[/white]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)
    except KeyError as e:
        print_error(f"Invalid key: {e}")
        raise SystemExit(1)


@config.command("get")
@click.argument("key")
@click.pass_context
def get_config(ctx: click.Context, key: str) -> None:
    """
    Get a configuration value.

    KEY uses dot notation for nested values.
    """
    try:
        project = get_project()
        config_dict = project.config.to_dict()

        # Navigate to value
        parts = key.split(".")
        current = config_dict
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                print_error(f"Key not found: {key}")
                raise SystemExit(1)

        if isinstance(current, dict):
            yaml_str = yaml.dump(current, default_flow_style=False)
            console.print(
                Panel(
                    Syntax(yaml_str.strip(), "yaml", theme="monokai"),
                    title=f"[accent]{key}[/accent]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )
        else:
            console.print(f"[accent]{key}[/accent] = [white]{current}[/white]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@config.command("edit")
@click.pass_context
def edit_config(ctx: click.Context) -> None:
    """Open configuration file in default editor."""
    try:
        project = get_project()
        click.edit(filename=str(project.config_path))
        project.reload_config()
        print_success("Configuration reloaded")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@config.command("reset")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def reset_config(ctx: click.Context, force: bool) -> None:
    """Reset configuration to defaults."""
    try:
        project = get_project()

        if not force:
            if not click.confirm("Reset configuration to defaults?"):
                console.print("[muted]Cancelled[/muted]")
                return

        from cascade.models.project import ProjectConfig

        project._config = ProjectConfig(
            name=project.config.name,  # Keep name
            description=project.config.description,  # Keep description
            tech_stack=project.config.tech_stack,  # Keep tech stack
        )
        project.save_config()

        print_success("Configuration reset to defaults")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@config.command("theme")
@click.argument("name", required=False)
@click.option(
    "--scope",
    type=click.Choice(["user", "project"]),
    default="user",
    help="Where to save the theme preference",
)
@click.pass_context
def set_theme(ctx: click.Context, name: str | None, scope: str) -> None:
    """Set or view the color theme."""
    tm = get_theme_manager()

    if name:
        if tm.set_theme(name, scope):
            print_success(f"Theme set to [accent]{name}[/accent] ({scope})")
        else:
            print_error(f"Unknown theme: {name}")
            console.print(f"[muted]Available: {', '.join(tm.list_themes())}[/muted]")
            raise SystemExit(1)
    else:
        # Display available themes
        console.print()
        table = create_table(["Theme", "Preview", "Status"])
        table.title = "[header]Available Themes[/header]"

        current = get_current_theme()
        for theme_name, theme in THEMES.items():
            preview = f"[{theme.primary}]■[/{theme.primary}] [{theme.accent}]■[/{theme.accent}] [{theme.success}]■[/{theme.success}]"
            status = "[success]● Active[/success]" if theme_name == current.name else ""
            table.add_row(f"[accent]{theme_name}[/accent]", preview, status)

        console.print(table)
        console.print()
        console.print("[muted]Usage: cascade config theme <name> [--scope user|project][/muted]")


def _convert_value(value: str) -> Any:
    """Convert string value to appropriate type."""
    # Boolean
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    if value.lower() in ("false", "no", "0", "off"):
        return False

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # List (comma-separated)
    if "," in value:
        return [v.strip() for v in value.split(",")]

    # String
    return value
