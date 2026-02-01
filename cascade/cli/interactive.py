"""Interactive REPL mode for Cascade CLI.

Provides a modern interactive shell with slash commands like Claude/Codex/Gemini CLIs.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import questionary
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completion, NestedCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style as PTStyle
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cascade.cli.themes import THEMES, get_current_theme, get_theme_manager
from cascade.cli.ui import (
    create_modern_table,
    create_welcome_box,
    draw_divider,
    print_keyboard_shortcuts,
)
from cascade.models.enums import Severity, TicketStatus, TicketType
from cascade.utils.git import GitProvider


class MetaNestedCompleter(NestedCompleter):
    """A nested completer that supports display_meta for its options."""

    def __init__(
        self, options: dict[str, Any], meta_dict: dict[str, str | None] | None = None
    ) -> None:
        super().__init__(options)
        self.meta_dict = meta_dict or {}

    @classmethod
    def from_meta_dict(cls, data: dict[str, Any]) -> MetaNestedCompleter:
        """Build from a dict that includes metadata.

        Format:
        {
            "command": {
                "__meta__": "Command description",
                "subcommand": {
                    "__meta__": "Subcommand description",
                }
            }
        }
        OR
        {
            "command": (sub_dict, "Command description")
        }
        """
        options = {}
        meta_dict = {}

        for key, value in data.items():
            if isinstance(value, tuple):
                sub_data, description = value
            elif isinstance(value, dict):
                description = value.get("__meta__")
                # Create a sub-copy without the meta if it's a dict
                sub_data = {k: v for k, v in value.items() if k != "__meta__"}
            else:
                description = None
                sub_data = value

            meta_dict[key] = description

            if isinstance(sub_data, dict):
                options[key] = cls.from_meta_dict(sub_data)
            else:
                options[key] = sub_data

        return cls(options, meta_dict)

    def get_completions(self, document: Any, complete_event: Any) -> Any:
        """Get completions for nested CLI commands."""
        # Determine if we are completing the current level or a sub-level
        text = document.text_before_cursor.lstrip()
        parts = text.split()

        # If there's only one word or we are at the end of a word that is a command,
        # we might be completing the keys of this level.
        if len(parts) <= 1:
            for completion in super().get_completions(document, complete_event):
                if completion.text in self.meta_dict:
                    yield Completion(
                        completion.text,
                        start_position=completion.start_position,
                        display_meta=self.meta_dict[completion.text],
                    )
                else:
                    yield completion
        else:
            # Delegate to parent which handles nested completions
            yield from super().get_completions(document, complete_event)


class SlashCommand:
    """A slash command definition."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        aliases: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.aliases = aliases or []


class InteractiveMode:
    """Interactive REPL with slash commands."""

    _project: Any | None

    def __init__(self, console: Console):
        self.console = console
        self.running = False
        self.commands: dict[str, SlashCommand] = {}
        self.history: list[str] = []
        self._project = None

        # Register built-in commands
        self._register_commands()

        # Build nested completer for subcommands
        theme = get_current_theme()
        self.completer = self._build_completer()

        # prompt_toolkit style
        self.pt_style = PTStyle.from_dict(
            {
                "prompt": theme.primary,
                "arrow": f"bold {theme.primary}",
                "completion-menu.completion": "bg:#333333 #ffffff",
                "completion-menu.completion.current": f"bg:{theme.primary} #ffffff",
            }
        )

        self.session: PromptSession[str] = PromptSession(
            completer=self.completer,
            style=self.pt_style,
        )

    def _register_commands(self) -> None:
        """Register all slash commands."""
        commands = [
            SlashCommand("help", "Show available commands", self._cmd_help, ["?"]),
            SlashCommand("status", "Show project dashboard", self._cmd_status),
            SlashCommand("ticket", "Manage tickets", self._cmd_ticket, ["t"]),
            SlashCommand("topic", "Manage topics", self._cmd_topic),
            SlashCommand("knowledge", "View knowledge base", self._cmd_knowledge, ["kb"]),
            SlashCommand("metrics", "Show project metrics", self._cmd_metrics),
            SlashCommand("git", "Git integration", self._cmd_git),
            SlashCommand("next", "AI suggests next ticket", self._cmd_next),
            SlashCommand("execute", "Execute ready tickets", self._cmd_execute, ["e"]),
            SlashCommand("settings", "Configure Cascade", self._cmd_settings),
            SlashCommand("model", "Change AI agent", self._cmd_model),
            SlashCommand("theme", "Change color theme", self._cmd_theme),
            SlashCommand("docs", "Open documentation", self._cmd_docs),
            SlashCommand("destroy", "Uninitialize Cascade project", self._cmd_destroy),
            SlashCommand("clear", "Clear screen", self._cmd_clear, ["cls"]),
            SlashCommand("quit", "Exit Cascade", self._cmd_quit, ["exit", "q"]),
        ]

        for cmd in commands:
            self.commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self.commands[alias] = cmd

    def _build_completer(self) -> MetaNestedCompleter:
        """Build nested completer for subcommands."""
        # Define subcommands with descriptions and hints
        ticket_subs = {
            "__meta__": "Manage tickets and tasks",
            "list": {"__meta__": "List all tickets"},
            "show": {"__meta__": "Show ticket details", "<id>": {"__meta__": "argument"}},
            "create": {"__meta__": "Create a new ticket"},
            "update": {"__meta__": "Update ticket fields", "<id>": {"__meta__": "argument"}},
            "ready": {"__meta__": "Mark tickets as ready", "<ids...>": {"__meta__": "argument"}},
            "block": {"__meta__": "Mark ticket as blocked", "<id>": {"__meta__": "argument"}},
            "delete": {"__meta__": "Delete a ticket", "<id>": {"__meta__": "argument"}},
            "execute": {
                "__meta__": "Execute a ticket with AI agent",
                "<id>": {"__meta__": "argument"},
            },
            "depends": {"__meta__": "Manage ticket dependencies", "<id>": {"__meta__": "argument"}},
        }
        topic_subs = {
            "__meta__": "Manage knowledge topics",
            "list": {"__meta__": "List all topics"},
            "create": {"__meta__": "Create a new topic", "<name>": {"__meta__": "argument"}},
            "delete": {"__meta__": "Delete a topic", "<name>": {"__meta__": "argument"}},
        }
        kb_subs = {
            "__meta__": "View and manage knowledge base",
            "pending": {"__meta__": "View pending knowledge items"},
            "approve": {
                "__meta__": "Approve knowledge items",
                "pattern": {"__meta__": "type"},
                "adr": {"__meta__": "type"},
            },
            "conventions": {"__meta__": "List all conventions"},
        }
        git_subs = {
            "__meta__": "Git integration commands",
            "status": {"__meta__": "Show git status"},
            "branch": {"__meta__": "List or create branches"},
            "commit": {"__meta__": "Commit changes", "<message>": {"__meta__": "argument"}},
            "diff": {"__meta__": "Show changes"},
        }
        settings_subs = {
            "__meta__": "Configure Cascade settings",
            "show": {"__meta__": "Show current configuration"},
            "set": {
                "__meta__": "Set a configuration value",
                "theme": {"__meta__": "option"},
                "agent": {"__meta__": "option"},
            },
        }

        # Build nested data
        main_commands_data = {
            "help": {"__meta__": "Show available commands"},
            "status": {"__meta__": "Show project dashboard"},
            "ticket": ticket_subs,
            "t": ticket_subs,
            "topic": topic_subs,
            "knowledge": kb_subs,
            "kb": kb_subs,
            "metrics": {"__meta__": "Show project metrics"},
            "git": git_subs,
            "next": {"__meta__": "AI suggests next ticket"},
            "execute": {"__meta__": "Execute ready tickets", "<id>": {"__meta__": "argument"}},
            "e": {"__meta__": "Execute ready tickets", "<id>": {"__meta__": "argument"}},
            "settings": settings_subs,
            "model": {
                "__meta__": "Change AI agent",
                "claude-code": {"__meta__": "agent"},
                "codex-cli": {"__meta__": "agent"},
                "gemini-cli": {"__meta__": "agent"},
            },
            "theme": {
                "__meta__": "Change color theme",
                "studio": {"__meta__": "theme"},
                "modern": {"__meta__": "theme"},
                "classic": {"__meta__": "theme"},
            },
            "docs": {"__meta__": "Open documentation"},
            "destroy": {"__meta__": "Uninitialize Cascade project"},
            "clear": {"__meta__": "Clear screen"},
            "cls": {"__meta__": "Clear screen"},
            "quit": {"__meta__": "Exit Cascade"},
            "exit": {"__meta__": "Exit Cascade"},
            "q": {"__meta__": "Exit Cascade"},
            "?": {"__meta__": "Show keyboard shortcuts"},
        }

        # Add both slash and non-slash versions
        completion_data = {}
        for cmd, data in main_commands_data.items():
            completion_data[cmd] = data
            if not cmd.startswith("?"):
                completion_data["/" + cmd] = data

        return MetaNestedCompleter.from_meta_dict(completion_data)

    def _get_project(self) -> Any:
        """Lazy load project."""
        if self._project is None:
            try:
                from cascade.core.project import get_project

                self._project = get_project()
            except (FileNotFoundError, Exception):
                pass
        return self._project

    def show_welcome(self) -> None:
        """Display the welcome screen."""
        project = self._get_project()
        # Get user info
        user = os.environ.get("USER") or os.environ.get("USERNAME") or "Developer"

        # Get project info
        project_name = None
        agent = None
        directory = os.getcwd()

        if project:
            project_name = project.config.name
            agent = project.config.agent.default

        # Print welcome box
        welcome = create_welcome_box(
            self.console,
            project_name=project_name,
            agent=agent,
            directory=directory,
            user=user,
        )
        self.console.print(welcome)

        # Warning if in home directory
        if Path.cwd() == Path.home():
            self.console.print(
                Panel(
                    "[warning]⚠[/warning] You are running Cascade in your home directory.\n"
                    "[muted]For best experience, run it in a project directory.[/muted]",
                    border_style="warning",
                    box=box.ROUNDED,
                )
            )

        self.console.print()

    def show_prompt(self) -> str:
        """Show the interactive prompt and get input."""
        draw_divider(self.console)

        # We use prompt_toolkit for the interactive input
        # HTML is used for styling the prompt to match Rich colors
        theme = get_current_theme()
        prompt_html = HTML(f'<style color="{theme.primary}">› </style>')

        try:
            user_input = self.session.prompt(prompt_html)
            return user_input.strip()
        except (KeyboardInterrupt, EOFError):
            return "quit"

    def run(self) -> None:
        """Run the interactive REPL."""
        self.running = True

        while self.running:
            # Check for project and run onboarding if needed
            project = self._get_project()
            if project is None:
                from cascade.cli.onboarding import run_onboarding

                if run_onboarding(self.console, Path.cwd()):
                    # Project was initialized, reset lazy loaded project
                    self._project = None
                    project = self._get_project()
                else:
                    # Onboarding failed or was cancelled
                    self.running = False
                    return

            # Show welcome only once or after reset
            if not getattr(self, "_welcome_shown", False):
                self.show_welcome()
                # Show hint
                self.console.print("[muted]  Type help for commands  [/muted]", justify="center")
                self.console.print()
                self._welcome_shown = True

            try:
                user_input = self.show_prompt()

                if not user_input:
                    continue

                self.history.append(user_input)

                # Handle commands (with or without slash)
                first_word = user_input.split()[0].lower() if user_input else ""

                if user_input.startswith("/"):
                    self._handle_slash_command(user_input)
                elif first_word in self.commands:
                    # Treat as command without slash
                    self._handle_slash_command("/" + user_input)
                elif user_input == "?":
                    print_keyboard_shortcuts(self.console)
                else:
                    # Treat as natural language query
                    self._handle_natural_input(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[muted]Type quit to exit[/muted]")
            except Exception as e:
                self.console.print(f"[error]Error:[/error] {e}")

    def _handle_slash_command(self, input_str: str) -> None:
        """Handle a slash command."""
        parts = input_str[1:].split(maxsplit=1)
        cmd_name = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if cmd_name in self.commands:
            self.commands[cmd_name].handler(args)
        else:
            self.console.print(f"[warning]Unknown command:[/warning] {cmd_name}")
            self.console.print("[muted]Type help for available commands[/muted]")

    def _handle_natural_input(self, input_str: str) -> None:
        """Handle natural language input."""
        self.console.print(
            Panel(
                "[muted]Natural language mode coming soon![/muted]\n\n"
                "For now, use commands:\n"
                "  [accent]status[/accent]  - View project dashboard\n"
                "  [accent]ticket[/accent]  - Manage tickets\n"
                "  [accent]help[/accent]    - See all commands",
                border_style="border",
                box=box.ROUNDED,
            )
        )

    # Command handlers
    def _cmd_help(self, args: str) -> None:
        """Show help for commands."""
        table = create_modern_table(["Command", "Description"])

        seen = set()
        for _name, cmd in sorted(self.commands.items()):
            if cmd.name in seen:
                continue
            seen.add(cmd.name)

            # Skip hidden commands or aliases if they clutter help
            if cmd.name in ["?", "cls", "q", "exit", "destroy"]:
                continue

            cmd_str = f"[accent]{cmd.name}[/accent]"
            if cmd.aliases:
                cmd_str += f" [muted]({', '.join(cmd.aliases)})[/muted]"

            table.add_row(cmd_str, cmd.description)

        self.console.print(
            Panel(
                table,
                title="[header]Available Commands[/header]",
                border_style="border",
                box=box.ROUNDED,
            )
        )

    def _cmd_status(self, args: str) -> None:
        """Show project status."""
        project = self._get_project()

        if not project:
            self.console.print("[warning]Not in a Cascade project.[/warning]")
            self.console.print("[muted]Run 'cascade init' to initialize.[/muted]")
            return

        # Get detailed metrics
        metrics = project.metrics.get_project_metrics()
        status_data = project.get_status()
        agent = project.config.agent.default

        # 1. Top HUD
        from cascade.cli.ui import create_status_hud

        hud = create_status_hud(
            [
                ("Project", status_data["name"]),
                ("Agent", agent),
                ("Topics", str(status_data["topics"])),
                ("Tickets", str(metrics.tickets.total)),
            ]
        )
        self.console.print(Panel(hud, border_style="border", box=box.ROUNDED, padding=(0, 1)))

        # 2. Main Body (Columns)
        from rich.console import Group

        # Left: Ticket & Quality Stats
        ticket_stats = Text()
        for s in ["DONE", "IN_PROGRESS", "READY", "BLOCKED"]:
            count = metrics.tickets.by_status.get(s, 0)
            style = self._status_style(s)
            ticket_stats.append(f"• {s:12}", style="muted")
            ticket_stats.append(f"{count:>3}\n", style=style)

        quality_info = Text()
        pass_rate = metrics.quality.pass_rate * 100
        quality_info.append("Pass Rate: ", style="muted")
        quality_info.append(f"{pass_rate:.1f}%", style="success" if pass_rate > 80 else "warning")
        quality_info.append(
            f"\nTests Run: [accent]{metrics.quality.total_runs}[/accent]", style="muted"
        )

        left_group = Group(
            Text("\nTicket Status", style="header"),
            ticket_stats,
            Text("\nQuality Gates", style="header"),
            quality_info,
        )

        # Right: Activity & Knowledge
        activity_stats = Text()
        activity_stats.append(
            f"Executions: [accent]{metrics.execution.total_executions}[/accent]\n", style="muted"
        )
        activity_stats.append(
            f"Total Tokens: [accent]{metrics.execution.total_tokens}[/accent]\n", style="muted"
        )
        activity_stats.append(
            f"Avg Time:     [accent]{metrics.execution.avg_time_ms_per_execution / 1000:.1f}s[/accent]\n",
            style="muted",
        )

        kb_data = project.kb.get_pending_knowledge()
        kb_pending = len(kb_data["patterns"]) + len(kb_data["adrs"])
        knowledge_stats = Text()
        knowledge_stats.append("Pending Review: ", style="muted")
        knowledge_stats.append(f"{kb_pending}\n", style="warning" if kb_pending > 0 else "muted")
        knowledge_stats.append(
            f"Approved Pat:   [accent]{len(project.kb.get_patterns())}[/accent]\n", style="muted"
        )

        right_group = Group(
            Text("\nActivity Info", style="header"),
            activity_stats,
            Text("\nKnowledge Base", style="header"),
            knowledge_stats,
        )

        main_cols = Columns(
            [
                Panel(
                    left_group,
                    title="[header]Progress[/header]",
                    border_style="border",
                    expand=True,
                ),
                Panel(
                    right_group, title="[header]Vitals[/header]", border_style="border", expand=True
                ),
            ],
            equal=True,
            expand=True,
        )

        self.console.print(main_cols)

        # 3. Recent Tickets
        tickets = project.tickets.list_all(limit=5)
        if tickets:
            self.console.print("\n[header]Recent Activity[/header]")
            table = create_modern_table(["#", "Type", "Status", "Title", "Sev"])
            for t in tickets[:3]:  # Show top 3 for compactness
                status_style = self._status_style(t.status)
                sev_val = t.severity.value if t.severity else "low"
                sev_display = (
                    f"[severity.{sev_val}]{sev_val.upper()}[/]" if t.severity else "[muted]-[ /]"
                )
                table.add_row(
                    f"[accent]{t.id}[/accent]",
                    t.ticket_type.value.capitalize(),
                    f"[{status_style}]{t.status.value}[/{status_style}]",
                    t.title[:50],
                    sev_display,
                )
            self.console.print(table)
        else:
            self.console.print("[muted]No tickets yet[/muted]")

    def _cmd_ticket(self, args: str) -> None:
        """Ticket operations."""
        project = self._get_project()

        if not project:
            self.console.print("[warning]Not in a Cascade project.[/warning]")
            return

        if not args:
            # Show help and summary list
            help_table = create_modern_table(["Subcommand", "Description"])
            help_table.add_row("[accent]list[/accent]", "List recent tickets")
            help_table.add_row("[accent]show <id>[/accent]", "Show ticket details")
            help_table.add_row("[accent]create[/accent]", "Create a new ticket")
            help_table.add_row("[accent]update <id>[/accent]", "Update ticket fields")
            help_table.add_row("[accent]ready <ids>[/accent]", "Mark tickets as ready")
            help_table.add_row("[accent]block <id>[/accent]", "Mark ticket as blocked")
            help_table.add_row("[accent]delete <id>[/accent]", "Delete a ticket")
            help_table.add_row("[accent]execute <id>[/accent]", "Execute a ticket with AI agent")

            self.console.print(
                Panel(
                    help_table,
                    title="[header]Ticket Subcommands[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )

            # Auto-list tickets as well
            tickets = project.tickets.list_all(limit=15)
            if tickets:
                table = create_modern_table(["#", "Type", "Status", "Title", "Sev"])
                for t in tickets:
                    status_style = self._status_style(t.status)
                    sev_val = t.severity.value if t.severity else "low"
                    sev_display = (
                        f"[severity.{sev_val}]{sev_val.upper()}[/]"
                        if t.severity
                        else "[muted]-[ /]"
                    )
                    table.add_row(
                        f"[accent]{t.id}[/accent]",
                        t.ticket_type.value.capitalize(),
                        f"[{status_style}]{t.status.value}[/{status_style}]",
                        t.title[:50] + ("..." if len(t.title) > 50 else ""),
                        sev_display,
                    )
                self.console.print(table)

                total = project.tickets.count()
                if total > 15:
                    self.console.print(
                        f"\n[info]ℹ[/info] Showing 15 of {total} tickets. Use [accent]ticket list[/accent] to browse all tickets with interactive pagination."
                    )
            return

        parts = args.split()
        subcmd = parts[0].lower()
        subargs = parts[1:]

        if subcmd == "list":
            page = 0
            page_size = 10
            total_tickets = project.tickets.count()
            total_pages = (total_tickets + page_size - 1) // page_size if total_tickets > 0 else 0

            while True:
                tickets = project.tickets.list_all(limit=page_size, offset=page * page_size)
                if not tickets:
                    self.console.print("[muted]No tickets found on this page.[/muted]")
                    break

                table = create_modern_table(["#", "Type", "Status", "Title", "Sev"])
                for t in tickets:
                    status_style = self._status_style(t.status)
                    sev_val = t.severity.value if t.severity else "low"
                    sev_display = (
                        f"[severity.{sev_val}]{sev_val.upper()}[/]"
                        if t.severity
                        else "[muted]-[ /]"
                    )
                    table.add_row(
                        f"[accent]{t.id}[/accent]",
                        t.ticket_type.value.capitalize(),
                        f"[{status_style}]{t.status.value}[/{status_style}]",
                        t.title[:50] + ("..." if len(t.title) > 50 else ""),
                        sev_display,
                    )

                self.console.clear()
                self.console.print(
                    Panel(
                        table,
                        title=f"[header]Ticket List - Page {page + 1}/{max(1, total_pages)}[/header]",
                        border_style="border",
                        box=box.ROUNDED,
                    )
                )

                if total_pages <= 1:
                    break

                choices = []
                if page < total_pages - 1:
                    choices.append("Next Page")
                if page > 0:
                    choices.append("Previous Page")
                choices.append("Exit Pager")

                action = questionary.select("Navigation:", choices=choices).ask()

                if action == "Next Page":
                    page += 1
                elif action == "Previous Page":
                    page -= 1
                else:
                    break

        elif subcmd == "show" or (len(parts) == 1 and parts[0].isdigit()):
            ticket_id_str = (
                subargs[0]
                if subcmd == "show" and subargs
                else (parts[0] if parts[0].isdigit() else None)
            )
            if not ticket_id_str:
                self.console.print("[error]Usage: ticket show <id>[/error]")
                return

            t = project.tickets.get(int(ticket_id_str))
            if t:
                status_style = self._status_style(t.status)
                sev_val = t.severity.value if t.severity else "low"
                sev_display = (
                    f"[severity.{sev_val}]{sev_val.upper()}[/]" if t.severity else "[muted]-[ /]"
                )

                content = (
                    f"[label]Type:[/label]      {t.ticket_type.value}\n"
                    f"[label]Status:[/label]    [{status_style}]{t.status.value}[/{status_style}]\n"
                    f"[label]Severity:[/label]  {sev_display}\n\n"
                    f"[header]Description[/header]\n{t.description or 'No description'}\n"
                )
                if t.acceptance_criteria:
                    content += f"\n[header]Acceptance Criteria[/header]\n{t.acceptance_criteria}"

                self.console.print(
                    Panel(
                        content.strip(),
                        title=f"[header]#{t.id}[/header] {t.title}",
                        border_style="border",
                        box=box.ROUNDED,
                    )
                )
            else:
                self.console.print(f"[error]Ticket #{ticket_id_str} not found[/error]")

        elif subcmd == "ready":
            if not subargs:
                self.console.print("[error]Usage: ticket ready <ids...>[/error]")
                return

            success_count = 0
            for tid_str in subargs:
                if not tid_str.isdigit():
                    continue
                tid = int(tid_str)
                if project.tickets.has_unmet_dependencies(tid):
                    self.console.print(
                        f"[warning]Ticket #{tid} is blocked by unmet dependencies.[/warning]"
                    )
                    continue
                if project.tickets.update_status(tid, TicketStatus.READY):
                    self.console.print(
                        f"[success]✓[/success] Ticket [accent]#{tid}[/accent] marked [status.ready]READY[/status.ready]"
                    )
                    success_count += 1
                else:
                    self.console.print(f"[error]Ticket #{tid} not found[/error]")

            if success_count > 1:
                self.console.print(f"[success]Total {success_count} tickets marked READY[/success]")

        elif subcmd == "block":
            if not subargs:
                self.console.print("[error]Usage: ticket block <id> [reason][/error]")
                return

            tid = int(subargs[0])
            reason = " ".join(subargs[1:]) if len(subargs) > 1 else ""

            updates: dict[str, Any] = {"status": TicketStatus.BLOCKED}
            if reason:
                t = project.tickets.get(tid)
                if t:
                    meta = t.metadata or {}
                    meta["block_reason"] = reason
                    updates["metadata"] = meta

            if project.tickets.update(tid, **updates):
                self.console.print(
                    f"[success]✓[/success] Ticket [accent]#{tid}[/accent] marked [error]BLOCKED[/error]"
                )
            else:
                self.console.print(f"[error]Ticket #{tid} not found[/error]")

        elif subcmd == "delete":
            if not subargs:
                self.console.print("[error]Usage: ticket delete <id>[/error]")
                return

            tid = int(subargs[0])
            t = project.tickets.get(tid)
            if not t:
                self.console.print(f"[error]Ticket #{tid} not found[/error]")
                return

            if questionary.confirm(
                f"Are you sure you want to delete ticket #{tid}: {t.title}?"
            ).ask():
                project.tickets.delete(tid)
                self.console.print(f"[success]✓[/success] Deleted ticket [accent]#{tid}[/accent]")
            else:
                self.console.print("[muted]Cancelled[/muted]")

        elif subcmd == "create":
            # Interactive creation with questionary
            title = questionary.text("Ticket title:").ask()
            if not title:
                return

            t_type = questionary.select(
                "Ticket type:", choices=[t.value for t in TicketType], default=TicketType.TASK.value
            ).ask()

            description = questionary.text("Description (optional):").ask()

            severity = questionary.select(
                "Severity (optional):", choices=["none"] + [s.value for s in Severity]
            ).ask()
            severity = None if severity == "none" else severity

            new_t = project.tickets.create(
                title=title,
                ticket_type=TicketType(t_type),
                description=description,
                severity=Severity(severity) if severity else None,
            )
            self.console.print(
                f"[success]✓[/success] Created ticket [accent]#{new_t.id}[/accent]: {new_t.title}"
            )

        elif subcmd == "execute":
            # Delegate to our optimized _cmd_execute
            self._cmd_execute(" ".join(subargs))

        elif subcmd == "update":
            if not subargs:
                self.console.print("[error]Usage: ticket update <id>[/error]")
                return

            tid = int(subargs[0])
            t = project.tickets.get(tid)
            if not t:
                self.console.print(f"[error]Ticket #{tid} not found[/error]")
                return

            # Interactive update
            field = questionary.select(
                "Select field to update:",
                choices=["title", "description", "status", "severity", "cancel"],
            ).ask()

            if field == "cancel":
                return

            if field == "status":
                new_val = questionary.select(
                    "New status:", choices=[s.value for s in TicketStatus], default=t.status.value
                ).ask()
                updates = {"status": TicketStatus(new_val)}
            elif field == "severity":
                new_val = questionary.select(
                    "New severity:",
                    choices=["none"] + [s.value for s in Severity],
                    default=t.severity.value if t.severity else "none",
                ).ask()
                updates = {"severity": None if new_val == "none" else Severity(new_val)}
            else:
                new_val = questionary.text(f"New {field}:", default=getattr(t, field) or "").ask()
                updates = {field: new_val}

            if project.tickets.update(tid, **updates):
                self.console.print(f"[success]✓[/success] Updated ticket [accent]#{tid}[/accent]")
            else:
                self.console.print(f"[error]Failed to update ticket #{tid}[/error]")

        else:
            self.console.print(f"[warning]Unknown ticket subcommand:[/warning] {subcmd}")

    def _cmd_topic(self, args: str) -> None:
        """Topic operations."""
        project = self._get_project()

        if not project:
            self.console.print("[warning]Not in a Cascade project.[/warning]")
            return

        if not args:
            # Show help and summary list
            help_table = create_modern_table(["Subcommand", "Description"])
            help_table.add_row("[accent]list[/accent]", "List all topics")
            help_table.add_row("[accent]create <name>[/accent]", "Create a new topic")
            help_table.add_row("[accent]delete <name>[/accent]", "Delete a topic")

            self.console.print(
                Panel(
                    help_table,
                    title="[header]Topic Subcommands[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )

            topics = project.topics.list_all()
            if not topics:
                self.console.print("[muted]No topics yet.[/muted]")
                return

            table = create_modern_table(["Topic", "Tickets", "Description"])
            for t in topics:
                ticket_count = len(project.topics.get_tickets(t.id))
                table.add_row(
                    f"[accent]{t.name}[/accent]", str(ticket_count), (t.description or "-")[:40]
                )
            self.console.print(table)
            return

        parts = args.split()
        subcmd = parts[0].lower()
        subargs = parts[1:]

        if subcmd == "list":
            topics = project.topics.list_all()
            if not topics:
                self.console.print("[muted]No topics yet.[/muted]")
                return
            table = create_modern_table(["Topic", "Tickets", "Description"])
            for t in topics:
                ticket_count = len(project.topics.get_tickets(t.id))
                table.add_row(
                    f"[accent]{t.name}[/accent]", str(ticket_count), (t.description or "-")[:40]
                )
            self.console.print(table)

        elif subcmd == "create":
            name = subargs[0] if subargs else questionary.text("Topic name:").ask()
            if not name:
                return
            desc = questionary.text("Description (optional):").ask() if not subargs else ""

            t = project.topics.get_or_create(name)
            if desc:
                project.topics.update(t.id, description=desc)
            self.console.print(f"[success]✓[/success] Topic [accent]{name}[/accent] ready")

        elif subcmd == "delete":
            if not subargs:
                self.console.print("[error]Usage: topic delete <name>[/error]")
                return
            name = subargs[0]
            t = next((x for x in project.topics.list_all() if x.name == name), None)
            if not t:
                self.console.print(f"[error]Topic '{name}' not found[/error]")
                return

            if questionary.confirm(f"Are you sure you want to delete topic '{name}'?").ask():
                project.topics.delete(t.id)
                self.console.print(f"[success]✓[/success] Deleted topic [accent]{name}[/accent]")

        else:
            self.console.print(f"[warning]Unknown topic subcommand:[/warning] {subcmd}")

    def _cmd_knowledge(self, args: str) -> None:
        """Knowledge base operations."""
        project = self._get_project()

        if not project:
            self.console.print("[warning]Not in a Cascade project.[/warning]")
            return

        from cascade.models.enums import KnowledgeStatus

        if not args:
            # Show subcommands help
            help_table = create_modern_table(["Subcommand", "Description"])
            help_table.add_row("[accent]pending[/accent]", "View pending knowledge items")
            help_table.add_row(
                "[accent]approve <type> <id>[/accent]", "Approve knowledge (pattern/adr)"
            )
            help_table.add_row("[accent]conventions[/accent]", "List all conventions")

            self.console.print(
                Panel(
                    help_table,
                    title="[header]Knowledge Subcommands[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )

            # Show summary
            pending_data = project.kb.get_pending_knowledge()
            pending_count = len(pending_data["patterns"]) + len(pending_data["adrs"])

            patterns = project.kb.get_patterns(status=KnowledgeStatus.APPROVED)
            adrs = project.kb.get_adrs(status=KnowledgeStatus.APPROVED)
            conventions = project.kb.get_conventions()

            self.console.print(
                Panel(
                    f"[label]Pending Review:[/label] [accent]{pending_count}[/accent]\n"
                    f"[label]Patterns:[/label]       [accent]{len(patterns)}[/accent]\n"
                    f"[label]ADRs:[/label]           [accent]{len(adrs)}[/accent]\n"
                    f"[label]Conventions:[/label]    [accent]{len(conventions)}[/accent]\n\n"
                    "[muted]Use knowledge <subcommand> for details[/muted]",
                    title="[header]Knowledge Base Summary[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )
            return

        parts = args.split()
        subcmd = parts[0].lower()
        subargs = parts[1:]

        if subcmd == "pending":
            pending = project.kb.get_pending_knowledge()
            if not pending["patterns"] and not pending["adrs"]:
                self.console.print("[muted]No pending items to review.[/muted]")
                return

            if pending["patterns"]:
                self.console.print("\n[header]Pending Patterns[/header]")
                table = create_modern_table(["ID", "Name", "Description"])
                for p in pending["patterns"]:
                    table.add_row(f"[accent]{p.id}[/accent]", p.name, (p.description or "")[:50])
                self.console.print(table)

            if pending["adrs"]:
                self.console.print("\n[header]Pending ADRs[/header]")
                table = create_modern_table(["ID", "Title", "Status"])
                for a in pending["adrs"]:
                    table.add_row(f"[accent]{a.id}[/accent]", a.title, a.status.value)
                self.console.print(table)

        elif subcmd == "conventions":
            conventions = project.kb.get_conventions()
            if not conventions:
                self.console.print("[muted]No conventions defined.[/muted]")
                return
            table = create_modern_table(["Name", "Description"])
            for c in conventions:
                table.add_row(f"[accent]{c.name}[/accent]", (c.description or "")[:70])
            self.console.print(table)

        elif subcmd == "approve":
            if len(subargs) < 2:
                self.console.print("[error]Usage: knowledge approve <pattern|adr> <id>[/error]")
                return
            ktype = subargs[0].lower()
            kid = int(subargs[1])

            if ktype == "pattern":
                res = project.kb.update_pattern(kid, status=KnowledgeStatus.APPROVED)
            elif ktype == "adr":
                res = project.kb.update_adr(kid, status=KnowledgeStatus.APPROVED)
            else:
                self.console.print(f"[error]Unknown type: {ktype}[/error]")
                return

            if res:
                self.console.print(f"[success]✓[/success] Approved {ktype} #{kid}")
            else:
                self.console.print(f"[error]{ktype.capitalize()} #{kid} not found[/error]")

        else:
            self.console.print(f"[warning]Unknown knowledge subcommand:[/warning] {subcmd}")

    def _cmd_metrics(self, args: str) -> None:
        """Show project metrics."""
        project = self._get_project()

        if not project:
            self.console.print("[warning]Not in a Cascade project.[/warning]")
            return

        metrics = project.metrics.get_project_metrics()

        if not args:
            # Show subcommands help
            help_table = create_modern_table(["Subcommand", "Description"])
            help_table.add_row("[accent]--tickets[/accent]", "Detailed ticket analytics")
            help_table.add_row("[accent]--quality[/accent]", "Quality gate performance")
            help_table.add_row("[accent]--activity[/accent]", "Daily activity log")

            self.console.print(
                Panel(
                    help_table,
                    title="[header]Metrics Subcommands[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )

            self.console.print(
                Panel(
                    f"[label]Total Executions:[/label]  [accent]{metrics.execution.total_executions}[/accent]\n"
                    f"[label]Total Tokens:[/label]      [accent]{metrics.execution.total_tokens}[/accent]\n"
                    f"[label]Avg Duration:[/label]      [accent]{metrics.execution.avg_time_ms_per_execution / 1000.0:.1f}s[/accent]\n"
                    f"[label]Tickets Done:[/label]      [accent]{metrics.tickets.by_status.get('DONE', 0)}[/accent]",
                    title="[header]Project Metrics Overview[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )
            self.console.print("[muted]Append options like --tickets to see more detail[/muted]")
            return

        if "--tickets" in args:
            self.console.print("\n[header]Ticket Analytics[/header]")

            # Status table
            status_table = create_modern_table(["Status", "Count"])
            for status, count in metrics.tickets.by_status.items():
                status_table.add_row(status, str(count))

            # Type table
            type_table = create_modern_table(["Type", "Count"])
            for ttype, count in metrics.tickets.by_type.items():
                type_table.add_row(ttype, str(count))

            self.console.print(
                Columns(
                    [
                        Panel(status_table, title="By Status", border_style="border"),
                        Panel(type_table, title="By Type", border_style="border"),
                    ],
                    equal=True,
                )
            )

            if metrics.tickets.estimated_effort > 0:
                accuracy = metrics.tickets.effort_accuracy * 100
                self.console.print(
                    f"\n[label]Effort Estimation Accuracy:[/label] [accent]{accuracy:.1f}%[/accent]"
                )

        if "--quality" in args:
            self.console.print("\n[header]Quality Gate Performance[/header]")
            passed = metrics.quality.passed
            failed = metrics.quality.failed
            rate = metrics.quality.pass_rate * 100

            self.console.print(
                f"Pass Rate: [accent]{rate:.1f}%[/accent] ({passed} passed, {failed} failed)\n"
            )

            gate_table = create_modern_table(["Gate", "Passed", "Failed", "Rate"])
            for gate, stats in metrics.quality.by_gate.items():
                g_total = stats["passed"] + stats["failed"]
                g_rate = (stats["passed"] / g_total * 100) if g_total > 0 else 0
                gate_table.add_row(
                    gate,
                    f"[success]{stats['passed']}[/]",
                    f"[error]{stats['failed']}[/]",
                    f"{g_rate:.1f}%",
                )
            self.console.print(gate_table)

        if "--activity" in args:
            self.console.print("\n[header]Daily Activity (Last 7 Days)[/header]")
            activity = project.metrics.get_daily_activity(days=7)
            if not activity:
                self.console.print("[muted]No activity recorded yet.[/muted]")
            else:
                table = create_modern_table(["Day", "Executions", "Tokens"])
                for day in activity:
                    table.add_row(day["day"], str(day["executions"]), str(day["tokens"]))
                self.console.print(table)

    def _cmd_git(self, args: str) -> None:
        """Git integration."""
        project = self._get_project()

        if not project:
            self.console.print("[warning]Not in a Cascade project.[/warning]")
            return

        git = GitProvider(project.root)

        if not git.is_available():
            self.console.print("[warning]Not a git repository.[/warning]")
            return

        if not args:
            # Show subcommands help
            help_table = create_modern_table(["Subcommand", "Description"])
            help_table.add_row("[accent]status[/accent]", "Show repository status")
            help_table.add_row("[accent]branch[/accent]", "List or create branches")
            help_table.add_row("[accent]commit[/accent]", "Commit changes")
            help_table.add_row("[accent]diff[/accent]", "Show changes")

            self.console.print(
                Panel(
                    help_table,
                    title="[header]Git Subcommands[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )

            branch = git.get_current_branch()
            res = git.get_status()
            status = res.output if res.success else "[error]Error getting status[/error]"

            self.console.print(
                Panel(
                    f"[label]Branch:[/label]   [accent]{branch}[/accent]\n"
                    f"[label]Status:[/label]   {status or '[success]Clean[/success]'}",
                    title="[header]Current Git Context[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )
            return

        parts = args.split()
        subcmd = parts[0].lower()
        subargs = parts[1:]

        if subcmd == "status":
            res = git.get_status()
            if res.success:
                self.console.print(
                    Panel(
                        res.output or "[success]Clean[/success]",
                        title="Git Status",
                        border_style="border",
                    )
                )
            else:
                self.console.print(f"[error]Git error: {res.error}[/error]")

        elif subcmd == "branch":
            if not subargs:
                # List branches
                res = git._run_git(["branch"])
                if res.success:
                    self.console.print(Panel(res.output, title="Branches", border_style="border"))
                else:
                    self.console.print(f"[error]Git error: {res.error}[/error]")
            else:
                # Create/switch branch
                name = subargs[0]
                res = git._run_git(
                    ["checkout", "-b", name] if "-b" in subargs else ["checkout", name]
                )
                if res.success:
                    self.console.print(
                        f"[success]✓[/success] Switched to branch [accent]{name}[/accent]"
                    )
                else:
                    # Try creating if checkout failed and not already tried
                    if "-b" not in subargs:
                        if questionary.confirm(f"Branch '{name}' not found. Create it?").ask():
                            res = git._run_git(["checkout", "-b", name])
                            if res.success:
                                self.console.print(
                                    f"[success]✓[/success] Created and switched to branch [accent]{name}[/accent]"
                                )
                                return
                    self.console.print(f"[error]Git error: {res.error}[/error]")

        elif subcmd == "diff":
            res = git._run_git(["diff", "--stat"])
            if res.success:
                self.console.print(
                    Panel(
                        res.output or "[muted]No changes[/muted]",
                        title="Git Diff Stat",
                        border_style="border",
                    )
                )
            else:
                self.console.print(f"[error]Git error: {res.error}[/error]")

        elif subcmd == "commit":
            msg = " ".join(subargs) if subargs else questionary.text("Commit message:").ask()
            if not msg:
                return

            # stage all
            git._run_git(["add", "."])
            res = git._run_git(["commit", "-m", msg])
            if res.success:
                self.console.print(f"[success]✓[/success] Committed: [muted]{msg}[/muted]")
            else:
                self.console.print(f"[error]Git error: {res.error}[/error]")

        else:
            self.console.print(f"[warning]Unknown git subcommand:[/warning] {subcmd}")

    def _cmd_next(self, args: str) -> None:
        """Get AI suggestion for next ticket."""
        project = self._get_project()
        if not project:
            self.console.print("[warning]Not in a Cascade project.[/warning]")
            return

        ready = project.tickets.list_all(status=TicketStatus.READY)
        if ready:
            t = ready[0]
            self.console.print(
                Panel(
                    f"[header]Suggested Next:[/header]\n\n"
                    f"[accent]#{t.id}[/accent] {t.title}\n\n"
                    f"[muted]{t.description or 'No description'}[/muted]\n\n"
                    f"[accent]›[/accent] Run [white]execute {t.id}[/white]",
                    border_style="accent",
                    box=box.ROUNDED,
                )
            )
        else:
            self.console.print("[muted]No ready tickets to suggest.[/muted]")

    def _cmd_execute(self, args: str) -> None:
        """Execute tickets natively."""
        project = self._get_project()
        if not project:
            self.console.print("[warning]Not in a Cascade project.[/warning]")
            return

        ids = []
        if args:
            raw_args = args.replace(",", " ").split()
            for arg in raw_args:
                if arg.isdigit():
                    ids.append(int(arg))
        else:
            ready_tickets = project.tickets.list_all(status=TicketStatus.READY)
            if not ready_tickets:
                self.console.print(
                    "[info]No tickets with status [status.ready]READY[/status.ready] found.[/info]"
                )
                return
            ids = [t.id for t in ready_tickets]
            self.console.print(
                f"[info]Executing all [status.ready]READY[/status.ready] tickets: {', '.join(map(str, ids))}[/info]"
            )

        if not ids:
            self.console.print("[error]No valid ticket IDs provided.[/error]")
            return

        # Native execution logic without CliRunner
        from rich.progress import Progress, SpinnerColumn, TextColumn

        from cascade.agents.registry import get_agent
        from cascade.core.executor import TicketExecutor
        from cascade.core.quality_gates import QualityGates

        executor = TicketExecutor(
            agent=get_agent(project.config.agent.default),
            context_builder=project.context_builder,
            prompt_builder=project.prompt_builder,
            ticket_manager=project.tickets,
            quality_gates=QualityGates(project.config, project.root),
            knowledge_base=project.kb,
            git_provider=GitProvider(project.root),
        )

        # Global confirmation state for this execution session
        has_confirmed = False

        def confirm_callback(tickets: list[Any], prompt: str) -> bool:
            nonlocal has_confirmed
            if has_confirmed:
                return True

            # Inline imports to ensure they are available
            from rich.panel import Panel

            print_prompt = f"{prompt}\n\n[accent]Proceed with execution?[/accent]"
            self.console.print(Panel(print_prompt, title="AGENT PROMPT", border_style="dim"))

            res = questionary.confirm("Execute ticket(s)?").ask()
            if res:
                has_confirmed = True
            return bool(res)

        if len(ids) > 1:
            # Handle batch execution natively
            self.console.print(
                f"\n[bold accent]🚀 Executing Batch:[/bold accent] [white]{', '.join(map(str, ids))}[/white]"
            )
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                    transient=True,
                ) as progress:
                    progress.add_task(description="Running batch execution...", total=None)

                    def batch_confirm(ts: list[Any], p: str) -> bool:
                        progress.stop()
                        res = confirm_callback(ts, p)
                        progress.start()
                        return res

                    result = executor.execute_batch(ids, confirm_callback=batch_confirm)

                if result.success:
                    self.console.print("[success]✓[/success] Batch executed successfully!")
                else:
                    self.console.print(f"[error]✗[/error] Batch failed: {result.error}")
            except Exception as e:
                self.console.print(f"[error]Error executing batch:[/error] {e}")
        else:
            tid = ids[0]
            t = project.tickets.get(tid)
            if not t:
                self.console.print(f"[error]Ticket #{tid} not found[/error]")
                return

            self.console.print(
                f"\n[bold accent]🚀 Executing Ticket #{tid}:[/bold accent] [white]{t.title}[/white]"
            )
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                    transient=True,
                ) as progress:
                    progress.add_task(description=f"Agent working on #{tid}...", total=None)

                    from cascade.models.ticket import Ticket

                    def single_confirm(ts: Ticket, p: str) -> bool:
                        progress.stop()
                        res = confirm_callback([ts], p)
                        progress.start()
                        return res

                    result = executor.execute(tid, confirm_callback=single_confirm)

                if result.success:
                    self.console.print(
                        f"[success]✓[/success] Ticket [accent]#{tid}[/accent] executed successfully!"
                    )
                else:
                    self.console.print(
                        f"[error]✗[/error] Ticket [accent]#{tid}[/accent] failed: {result.error}"
                    )
            except Exception as e:
                self.console.print(f"[error]Error executing ticket #{tid}:[/error] {e}")

    def _cmd_settings(self, args: str) -> None:
        """View or update settings."""
        project = self._get_project()
        agent = project.config.agent.default if project else "N/A"

        if not args:
            # Show subcommands help
            help_table = create_modern_table(["Subcommand", "Description"])
            help_table.add_row("[accent]show[/accent]", "View configuration details")
            help_table.add_row("[accent]/theme <name>[/accent]", "Change color scheme")
            help_table.add_row("[accent]/model <name>[/accent]", "Select active AI agent")

            self.console.print(
                Panel(
                    help_table,
                    title="[header]Configuration Commands[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )

            self.console.print(
                Panel(
                    f"[label]Theme:[/label]      [accent]{get_current_theme().name}[/accent]\n"
                    f"[label]Agent:[/label]      [accent]{agent}[/accent]\n"
                    f"[label]Directory:[/label]  [muted]{os.getcwd()}[/muted]",
                    border_style="border",
                    box=box.ROUNDED,
                    title="[header]Current Settings[/header]",
                )
            )
            return

        parts = args.split()
        subcmd = parts[0].lower()

        if subcmd == "show" and project:
            import yaml

            config_dict = project.config.to_dict()
            self.console.print(
                Panel(
                    f"[muted]{yaml.dump(config_dict, default_flow_style=False)}[/muted]",
                    title="[header]Full Configuration[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )
        else:
            self.console.print(f"[warning]Unknown settings subcommand:[/warning] {subcmd}")

    def _cmd_model(self, args: str) -> None:
        """Change AI agent."""
        from cascade.agents.registry import get_agent, list_agents

        agents = list_agents()

        if args and args in agents:
            project = self._get_project()
            if project:
                project.config.agent.default = args
                project.save_config()
                self.console.print(f"[success]✓[/success] Agent set to [accent]{args}[/accent]")
            else:
                self.console.print("[warning]Not in a project.[/warning]")
        else:
            # Show available agents
            table = create_modern_table(["Agent", "Status"])
            for agent_name in agents:
                try:
                    agent = get_agent(agent_name)
                    available = agent.is_available()
                    status = (
                        "[success]Available[/success]"
                        if available
                        else "[muted]Not available[/muted]"
                    )
                except Exception:
                    status = "[muted]Unknown[/muted]"
                table.add_row(f"[accent]{agent_name}[/accent]", status)

            self.console.print(
                Panel(
                    table,
                    title="[header]Available Agents[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )
            self.console.print("\n[muted]Usage: /model <agent-name>[/muted]")

    def _cmd_theme(self, args: str) -> None:
        """Change color theme."""
        tm = get_theme_manager()

        if args:
            parts = args.split()
            theme_name = parts[0]
            scope = parts[1] if len(parts) > 1 else "user"

            if tm.set_theme(theme_name, scope):
                self.console.print(
                    f"[success]✓[/success] Theme set to [accent]{theme_name}[/accent] ({scope})"
                )
            else:
                self.console.print(f"[warning]Unknown theme:[/warning] {theme_name}")
                self.console.print(f"[muted]Available: {', '.join(tm.list_themes())}[/muted]")
        else:
            # Show available themes
            current = get_current_theme()

            table = create_modern_table(["Theme", "Colors"])

            for name, theme in THEMES.items():
                marker = " [success]●[/success]" if name == current.name else ""
                colors = f"[{theme.primary}]■[/{theme.primary}] [{theme.accent}]■[/{theme.accent}]"
                table.add_row(f"[accent]{name}[/accent]{marker}", colors)

            self.console.print(
                Panel(
                    table,
                    title="[header]Available Themes[/header]",
                    border_style="border",
                    box=box.ROUNDED,
                )
            )
            self.console.print("\n[muted]Usage: /theme <name> [user|project][/muted]")

    def _cmd_docs(self, args: str) -> None:
        """Open documentation."""
        import webbrowser

        url = "https://github.com/cascade-ai/cascade#readme"

        try:
            webbrowser.open(url)
            self.console.print("[success]✓[/success] Opened documentation in browser")
        except Exception:
            self.console.print(f"[info]ℹ[/info] Documentation: {url}")

    def _cmd_clear(self, args: str) -> None:
        """Clear the screen."""
        self.console.clear()
        self.show_welcome()

    def _cmd_destroy(self, args: str) -> None:
        """Destroy the current Cascade project."""
        project = self._get_project()
        if not project:
            from cascade.cli.ui import print_warning_box

            print_warning_box(self.console, "No Cascade project found to destroy.")
            return

        from rich import box
        from rich.panel import Panel

        from cascade.cli.ui import print_error_box, print_success_box, print_warning_box

        cascade_dir = project.cascade_dir

        self.console.print(
            Panel(
                f"[warning]⚠[/warning] This will permanently delete the Cascade project at [accent]{cascade_dir}[/accent]\n"
                f"[muted]All tickets, topics, and configuration will be lost.[/muted]",
                title="[error]Permanent Destruction[/error]",
                border_style="error",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

        if questionary.confirm("Are you sure you want to continue?", default=False).ask():
            try:
                # We need to be careful about file handles.
                # Closing DB might be needed if held open.
                if hasattr(project, "_db") and project._db:
                    project._db.close()

                shutil.rmtree(cascade_dir)
                print_success_box(self.console, "Project uninitialized successfully.", "Restored")

                # Reset project state to trigger re-onboarding in the loop
                self._project = None
                self._welcome_shown = False

            except Exception as e:
                print_error_box(self.console, f"Failed to destroy project: {e}")
        else:
            self.console.print("[muted]  Operation cancelled.  [/muted]")

    def _cmd_quit(self, args: str) -> None:
        """Exit the REPL."""
        self.running = False
        self.console.print("\n[muted]Goodbye! 👋[/muted]\n")

    def _status_style(self, status: str | TicketStatus) -> str:
        """Get style for ticket status."""
        from cascade.models.enums import TicketStatus

        st = status.value if isinstance(status, TicketStatus) else status.upper()
        return {
            "DEFINED": "muted",
            "READY": "status.ready",
            "IN_PROGRESS": "status.progress",
            "DONE": "success",
            "BLOCKED": "error",
        }.get(st, "muted")


def start_interactive_mode(console: Console) -> None:
    """Start the interactive REPL."""
    mode = InteractiveMode(console)
    mode.run()
