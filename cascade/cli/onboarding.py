"""Onboarding and initialization utilities for Cascade CLI.

Extracted from init.py to be shared with interactive mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel

from cascade.cli.styles import print_warning
from cascade.core.project import CascadeProject


def configure_agent(console: Console, project: CascadeProject) -> None:
    """Interactively configure the default agent."""
    import sys

    import questionary

    from cascade.agents.registry import get_agent

    console.print()
    console.print(
        Panel(
            "[header]Agent Configuration[/header]\n\n"
            "[muted]Checking for installed AI tools...[/muted]",
            border_style="border",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )

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
        console.print(
            f"[success]✓[/success] Detected [accent]{selected_agent}[/accent]. Setting as default."
        )
        project.config.agent.default = selected_agent
        project.save_config()
        return

    elif len(available_clis) > 1:
        # Multiple CLIs found - Ask user (if interactive)
        console.print(
            f"[success]✓[/success] Detected: {', '.join(f'[accent]{a}[/accent]' for a in available_clis)}"
        )

        # Check if we're in an interactive environment
        if sys.stdin.isatty():
            selected_agent = questionary.select(
                "Which agent would you like to use as default?", choices=available_clis
            ).ask()
            if selected_agent:
                project.config.agent.default = selected_agent
                project.save_config()
                return

        # Non-interactive or user cancelled - use first available
        selected_agent = available_clis[0]
        console.print(f"[info]ℹ[/info] Using [accent]{selected_agent}[/accent] as default.")
        project.config.agent.default = selected_agent
        project.save_config()
        return

    # No CLIs found - Prompt for API configuration (if interactive)
    console.print("[warning]⚠[/warning] No local CLI tools detected.")

    if not sys.stdin.isatty():
        # Non-interactive - use generic agent
        console.print("[info]ℹ[/info] Using [accent]generic[/accent] agent as default.")
        project.config.agent.default = "generic"
        project.save_config()
        return

    console.print("[muted]Please select an AI provider to configure (API Key required):[/muted]")

    provider_choice = questionary.select(
        "Select Provider:", choices=["Anthropic (Claude)", "Google (Gemini)", "OpenAI (Codex)"]
    ).ask()

    if not provider_choice:
        # User cancelled
        print_warning("No provider selected. Using Generic agent as fallback.")
        project.config.agent.default = "generic"
        project.save_config()
        return

    provider_map = {
        "Anthropic (Claude)": ("claude", "ANTHROPIC_API_KEY"),
        "Google (Gemini)": ("google", "ANTIGRAVITY_API_KEY"),
        "OpenAI (Codex)": ("openai", "OPENAI_API_KEY"),
    }

    provider_key, env_var_name = provider_map[provider_choice]

    console.print(
        f"\n[muted]You can find your API key in your {provider_choice.split()[0]} account settings.[/muted]"
    )
    api_key = questionary.password(f"Enter your {env_var_name}:").ask()

    if not api_key:
        print_warning("No API key provided. Using Generic agent as fallback.")
        project.config.agent.default = "generic"
        project.save_config()
        return

    # 1. Update Config (Mode = API)
    if provider_key not in project.config.agent.configurations:
        project.config.agent.configurations[provider_key] = {}
    project.config.agent.configurations[provider_key]["mode"] = "api"

    agent_name_map = {"claude": "claude-api", "google": "gemini-api", "openai": "codex-api"}
    project.config.agent.default = agent_name_map[provider_key]
    project.save_config()

    # 2. Save Securely to .env
    save_to_env(project.cascade_dir.parent, env_var_name, api_key)
    console.print("[success]✓[/success] API key saved securely to [muted].env[/muted]")
    console.print(
        f"[success]✓[/success] Default agent set to [accent]{project.config.agent.default}[/accent]"
    )


def run_onboarding(console: Console, project_path: Path) -> bool:
    """Run the interactive onboarding flow.

    Returns:
        True if project was initialized, False otherwise.
    """
    import questionary
    from rich import box
    from rich.panel import Panel

    from cascade.cli.styles import get_progress, print_error, print_info, print_success

    console.print(
        Panel(
            "[header]Welcome to Cascade![/header]\n\n"
            "AI assists, human directs. It looks like this directory is not yet\n"
            "initialized as a Cascade project.\n\n"
            "[muted]Initialize now to start building with AI orchestration?[/muted]",
            border_style="accent",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if not questionary.confirm("Initialize Cascade project here?", default=True).ask():
        print_info("Onboarding cancelled. You can run 'cascade init' later.")
        return False

    project = CascadeProject(project_path)

    # 1. Project Info
    console.print("\n[header]Project Details[/header]")
    name = questionary.text("Project name:", default=project_path.name).ask()
    description = questionary.text("Project description (optional):").ask()

    # Detect requirements sources
    req_files = ["README.md", "readme.md", "README", "readme", "requirements.txt"]
    detected_req_file = None
    for f in req_files:
        if (project_path / f).exists():
            detected_req_file = project_path / f
            break

    # 2. Basic initialization
    try:
        with get_progress() as progress:
            task = progress.add_task("[muted]Creating project structure...", total=100)
            project.initialize(
                name=name or project_path.name,
                description=description or "",
            )
            progress.update(task, completed=100, description="[success]Project created[/success]")

        # 3. Agent Configuration
        configure_agent(console, project)

        # 4. Requirements Analysis (Optional)
        console.print("\n[header]Project Planning[/header]")
        requirements = None

        if detected_req_file:
            if questionary.confirm(
                f"Detected [accent]{detected_req_file.name}[/accent]. Use it as project requirements?",
                default=True,
            ).ask():
                try:
                    requirements = detected_req_file.read_text(encoding="utf-8")
                except Exception as e:
                    print_error(f"Failed to read file: {str(e)}")

        if not requirements:
            if questionary.confirm(
                "Would you like AI to analyze your requirements and generate a plan?", default=False
            ).ask():
                requirements = questionary.text(
                    "Describe what you want to build (or leave empty to skip):"
                ).ask()

        if requirements:
            with get_progress() as progress:
                task = progress.add_task("[muted]Analyzing requirements with AI...", total=100)
                try:
                    plan = project.planner.plan(requirements)
                    progress.update(
                        task, completed=100, description="[success]Analysis complete[/success]"
                    )

                    # Update project config
                    project.config.name = plan.project_name
                    project.config.description = plan.project_description
                    project.config.tech_stack = plan.tech_stack
                    project.save_config()

                    # Display and confirm plan
                    console.print()
                    _display_proposed_plan(console, plan)

                    if questionary.confirm("Generate this project plan?", default=True).ask():
                        with get_progress() as progress:
                            task = progress.add_task("[muted]Generating tickets...", total=100)
                            project.planner.generate_tickets(plan)
                            progress.update(task, completed=100)
                        print_success("Project plan generated successfully.")
                except Exception as e:
                    progress.update(task, description="[error]Analysis failed[/error]")
                    print_error(f"Failed to generate plan: {str(e)}")

        console.print()
        print_success("Initialization complete! Entering interactive mode...")
        console.print()
        return True

    except Exception as e:
        print_error(f"Initialization failed: {str(e)}")
        # Partial cleanup - if .cascade was created, maybe remove it if it's empty/incomplete
        # For now, just advise the user to use cascade destroy
        print_info("Use 'cascade destroy' to reset and try again.")
        return False


def _display_proposed_plan(console: Console, plan: Any) -> None:
    """Display the proposed project plan (copied from init.py for independence)."""
    from rich import box

    from cascade.cli.styles import create_table

    tech_stack = ", ".join(f"[accent]{t}[/accent]" for t in plan.tech_stack)

    console.print(
        Panel(
            f"[header]{plan.project_name}[/header]\n\n"
            f"[muted]{plan.project_description}[/muted]\n\n"
            f"[label]Tech Stack:[/label] {tech_stack}",
            title="[accent]Proposed Project[/accent]",
            border_style="accent",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    if plan.topics:
        console.print()
        topic_table = create_table(["Topic", "Description"])
        topic_table.title = "[header]Proposed Topics[/header]"
        for topic in plan.topics:
            topic_table.add_row(f"[accent]{topic.name}[/accent]", topic.description)
        console.print(topic_table)

    if plan.tickets:
        console.print()
        ticket_table = create_table(["Type", "Title", "Severity", "Subtasks"])
        ticket_table.title = "[header]Proposed Tickets[/header]"

        def add_to_table(tickets: list[Any], indent: int = 0) -> None:
            for t in tickets:
                type_str = "  " * indent + t.ticket_type.value.lower()
                sev_str = t.severity.value.upper() if t.severity else "MEDIUM"
                subtasks = str(len(t.children)) if t.children else "-"

                ticket_table.add_row(f"[muted]{type_str}[/muted]", t.title, sev_str, subtasks)
                if t.children:
                    add_to_table(t.children, indent + 1)

        add_to_table(plan.tickets)
        console.print(ticket_table)


def save_to_env(project_root: Path, key: str, value: str) -> None:
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
        gitignore_path.write_text(".env\n")
