"""Init command for Cascade CLI."""

import click
from pathlib import Path
from rich.console import Console
from cascade.core.project import CascadeProject
from cascade.cli.styles import (
    console,
    print_banner,
    print_step,
    print_success,
    print_error,
    create_table,
    create_panel,
    get_progress
)


@click.command("init")
@click.argument("requirements", required=False)
@click.option(
    "--name", "-n",
    help="Project name",
)
@click.option(
    "--description", "-d",
    default="",
    help="Project description (if not using requirements)",
)
@click.option(
    "--tech-stack", "-t",
    multiple=True,
    help="Technologies used (if not using requirements)",
)
@click.option(
    "--path", "-p",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    default=None,
    help="Project path (defaults to current directory)",
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation for generated plan",
)
@click.pass_context
def init_cmd(
    ctx: click.Context,
    requirements: str | None,
    name: str | None,
    description: str,
    tech_stack: tuple[str, ...],
    path: Path | None,
    yes: bool,
) -> None:
    """
    Initialize a new Cascade project.

    Creates a .cascade directory with database and configuration files.

    If REQUIREMENTS are provided, Cascade will analyze them and
    generate a project plan (tickets, topics, ADRs). REQUIREMENTS
    can be a text string or a path to a file containing the requirements.

    Examples:

        cascade init "Build a REST API with FastAPI"

        cascade init ./my-idea.txt

        cascade init --name "My Project" -d "A simple project" -t python
    """
    console: Console = ctx.obj["console"]
    project_path = path or Path.cwd()

    # Handle requirements file if path is provided
    if requirements:
        req_path = Path(requirements).expanduser().resolve()
        if req_path.exists() and req_path.is_file():
            try:
                console.print(f"[dim]Reading requirements from {req_path}[/dim]")
                requirements = req_path.read_text(encoding="utf-8")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not read file {req_path}: {e}[/yellow]")
                console.print("[dim]Treating input as raw text string.[/dim]")

    try:
        project = CascadeProject(project_path)

        if project.is_initialized:
            console.print(
                f"[yellow]Project already initialized at {project_path}[/yellow]"
            )
            return

        # 1. Basic initialization
        project.initialize(
            name=name or project_path.name,
            description=description,
            tech_stack=list(tech_stack) if tech_stack else [],
        )

        # 2. Interactive Agent Configuration (Do this BEFORE planning)
        _configure_agent(console, project)

        # 3. Planning if requirements provided
        if requirements:
            with get_progress() as progress:
                task = progress.add_task("[dim]Analyzing requirements...", total=100)
                plan = project.planner.plan(requirements)
                progress.update(task, completed=100)

            # Update project config with AI-discovered info
            project.config.name = plan.project_name
            project.config.description = plan.project_description
            project.config.tech_stack = plan.tech_stack
            project.save_config()

            print_banner("Proposed Project")
            console.print(f"[white]Name:[/white] [accent]{plan.project_name}[/accent]")
            console.print(f"[dim]{plan.project_description}[/dim]")

            # Display Tech Stack
            stack_text = ", ".join(f"[cyan]{t}[/cyan]" for t in plan.tech_stack)
            console.print(f"[label]Tech Stack:[/label] {stack_text}")

            # Display Topics
            if plan.topics:
                print_banner("Proposed Topics")
                topic_table = create_table(["TOPIC", "DESCRIPTION"])
                for topic in plan.topics:
                    topic_table.add_row(f"[accent]{topic.name}[/accent]", topic.description)
                console.print(topic_table)

            # Display Tickets
            if plan.tickets:
                print_banner("Proposed Tickets")
                ticket_table = create_table(["TYPE", "TITLE", "SEVERITY", "SUBTASKS"])

                def add_to_table(tickets, indent=0):
                    for t in tickets:
                        type_str = "  " * indent + t.ticket_type.value.lower()
                        sev_style = "dim"
                        if t.severity:
                            sev_str = t.severity.value.upper()
                        else:
                            sev_str = "MEDIUM"

                        ticket_table.add_row(
                            type_str,
                            t.title,
                            sev_str,
                            str(len(t.children)) if t.children else "-"
                        )
                        if t.children:
                            add_to_table(t.children, indent + 1)

                add_to_table(plan.tickets)
                console.print(ticket_table)

            generate_plan = True
            if not yes:
                console.print()
                if not click.confirm("Generate this project plan?", default=True):
                    generate_plan = False
                    print_success("Skipping plan generation.")

            if generate_plan:
                project.planner.generate_tickets(plan)
                print_success("Project plan generated successfully.")

        summary = (
            f"[label]Project:[/label]  [accent]{project.config.name}[/accent]\n"
            f"[label]Location:[/label] [dim]{project_path}[/dim]\n"
            f"[label]Config:[/label]   [dim]{project.config_path.name}[/dim]\n"
            f"[label]Agent:[/label]    [accent]{project.config.agent.default}[/accent]\n\n"
            f"[white]Next steps:[/white]\n"
            f" [accent]→[/accent] Run [white]ccd status[/white] to view the dashboard\n"
            f" [accent]→[/accent] Run [white]ccd ticket list[/white] to see all tickets\n"
            f" [accent]→[/accent] Run [white]ccd ticket execute 1[/white] to start"
        )
        console.print(create_panel(summary, title="CASCADE INITIALIZED", border_style="green"))

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Failed to initialize project:[/red] {e}")
        import logging
        logging.getLogger(__name__).exception("Init failure")
        raise SystemExit(1)


def _configure_agent(console: Console, project: CascadeProject) -> None:
    """Interactively configure the default agent."""
    from cascade.agents.registry import get_agent
    import click

    print_banner("Agent Configuration")
    console.print("[dim]Checking for installed AI tools...[/dim]")

    # Check for CLI tools
    available_clis = []
    cli_agents = ["claude-cli", "gemini-cli", "codex-cli"]

    for name in cli_agents:
        try:
            agent = get_agent(name)
            if agent.is_available():
                available_clis.append(name)
        except Exception:
            pass

    selected_agent = None

    if len(available_clis) == 1:
        # Only one CLI found - Use it
        selected_agent = available_clis[0]
        console.print(f"[green]Detected {selected_agent}. Setting as default.[/green]")
        project.config.agent.default = selected_agent
        project.save_config()
        return

    elif len(available_clis) > 1:
        # Multiple CLIs found - Ask user
        console.print(f"[green]Detected multiple tools: {', '.join(available_clis)}[/green]")
        import questionary
        selected_agent = questionary.select(
            "Which agent would you like to use as default?",
            choices=available_clis
        ).ask()
        project.config.agent.default = selected_agent
        project.save_config()
        return

    # No CLIs found - Prompt for API configuration
    console.print("[yellow]No local CLI tools detected.[/yellow]")
    console.print("Please select an AI provider to configure (API Key required):")

    import questionary
    provider_choice = questionary.select(
        "Select Provider:",
        choices=[
            "Anthropic (Claude)",
            "Google (Gemini)",
            "OpenAI (Codex)"
        ]
    ).ask()

    provider_map = {
        "Anthropic (Claude)": ("claude", "ANTHROPIC_API_KEY"),
        "Google (Gemini)": ("google", "ANTIGRAVITY_API_KEY"),
        "OpenAI (Codex)": ("openai", "OPENAI_API_KEY")
    }

    provider_key, env_var_name = provider_map[provider_choice]

    console.print(f"\n[dim]You can find your API key in your {provider_choice.split()[0]} account settings.[/dim]")
    api_key = questionary.password(f"Enter your {env_var_name}:").ask()

    if not api_key:
        console.print("[yellow]No API key provided. Using Generic agent as fallback.[/yellow]")
        project.config.agent.default = "generic"
        project.save_config()
        return

    # 1. Update Config (Mode = API)
    if provider_key not in project.config.agent.configurations:
        project.config.agent.configurations[provider_key] = {}
    project.config.agent.configurations[provider_key]["mode"] = "api"

    agent_name_map = {
        "claude": "claude-api",
        "google": "gemini-api",
        "openai": "codex-api"
    }
    project.config.agent.default = agent_name_map[provider_key]
    project.save_config()

    # 2. Save Securely to .env
    _save_to_env(project.cascade_dir.parent, env_var_name, api_key)
    console.print(f"[green]API key saved securely to .env[/green]")
    console.print(f"[green]Default agent set to {project.config.agent.default}[/green]")


def _save_to_env(project_root: Path, key: str, value: str) -> None:
    """Save variable to .env file and ensure it is gitignored."""
    env_path = project_root / ".env"

    # Read existing
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    # Update or Append
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"{key}={value}")

    # Write back
    env_path.write_text("\n".join(new_lines) + "\n")

    # Update .gitignore
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if ".env" not in content:
            with open(gitignore_path, "a") as f:
                f.write("\n.env\n")
    else:
        # Create if not exists (safer to assume we should if we are managing secrets)
        pass # Actually, if no gitignore, maybe we shouldn't create one unless we init git?
             # But protecting .env is critical. Let's create it if missing to be safe.
        gitignore_path.write_text(".env\n")
