"""Config commands for Cascade CLI."""

import click
import yaml
from rich.syntax import Syntax
from cascade.core.project import get_project
from cascade.agents.registry import list_agents
from cascade.cli.styles import (
    console,
    print_banner,
    print_success,
    print_error,
    create_panel
)


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

        yaml_str = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
        syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)

        print_banner("Project Configuration")
        console.print(create_panel(syntax, title=str(project.config_path.name), border_style="dim"))

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
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

        cascade config set agent.default claude-code

        cascade config set quality_gates.unit_tests.enabled true
    """
    console: Console = ctx.obj["console"]

    try:
        project = get_project()

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
                console.print(
                    "[red]Invalid agent:[/red] "
                    f"{converted_value}. Available: {', '.join(list_agents())}"
                )
                raise SystemExit(1)
        current[final_key] = converted_value

        # Reload config from dict and save
        from cascade.models.project import ProjectConfig
        project._config = ProjectConfig._from_dict(config_dict)
        project.save_config()

        print_success(f"Set {key} = {converted_value}")

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
            console.print(yaml_str.strip())
        else:
            console.print(str(current))

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
                console.print("[dim]Cancelled[/dim]")
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


def _convert_value(value: str):
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
