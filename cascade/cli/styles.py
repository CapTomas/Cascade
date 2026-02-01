"""Premium styling utilities for Cascade CLI.

Integrates with the theme system for consistent styling across commands.
"""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.theme import Theme

from cascade.cli.themes import get_current_theme


def get_console() -> Console:
    """Get a themed console instance."""
    theme = get_current_theme()
    return Console(theme=theme.to_rich_theme())


# Default console instance - uses theme system
console = get_console()


# Re-export CASCADE_THEME for backwards compatibility
def _get_cascade_theme() -> Theme:
    """Get the current CASCADE theme for backwards compatibility."""
    return get_current_theme().to_rich_theme()


CASCADE_THEME = _get_cascade_theme()


def print_banner(title: str) -> None:
    """Print a minimalist section banner."""
    console.print(
        f"\n[accent]●[/accent] [header]{title.upper()}[/header] " + "─" * (40 - len(title))
    )


def create_hud(items: list[tuple[str, str]], title: str = "SYSTEM STATUS") -> Panel:
    """Create a HUD-style horizontal display."""
    parts = []
    for label, value in items:
        parts.append(f"[label]{label.upper()}[/label] [value]{value}[/value]")

    content = "  [muted]•[/muted]  ".join(parts)
    return Panel(
        content,
        title=f"[muted]{title}[/muted]",
        border_style="border",
        box=box.ROUNDED,
        padding=(0, 1),
    )


def create_table(columns: list[str], title: str | None = None) -> Table:
    """Create a streamlined table with modern styling."""
    table = Table(
        title=title,
        show_header=True,
        header_style="accent",
        box=box.ROUNDED,
        border_style="border",
        expand=True,
        padding=(0, 1),
    )
    for col in columns:
        table.add_column(col)
    return table


def print_step(message: str, current: int, total: int) -> None:
    """Print a progress step."""
    console.print(f"[muted][{current}/{total}][/muted] [info]{message}...[/info]")


def create_panel(content: str, title: str | None = None, border_style: str = "border") -> Panel:
    """Create a rich panel with modern styling."""
    return Panel(content, title=title, border_style=border_style, box=box.ROUNDED, padding=(1, 2))


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[success]✓[/success] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[error]✗[/error] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]⚠[/warning] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[info]ℹ[/info] {message}")


def create_solution_panel(error: str, solution: str) -> Panel:
    """Create a panel for errors with solutions."""
    content = f"[error]ERROR:[/error] {error}\n\n[accent]TRY THIS:[/accent]\n{solution}"
    return Panel(
        content,
        title="[error]Issue Detected[/error]",
        border_style="error",
        box=box.ROUNDED,
    )


def get_progress() -> Progress:
    """Get a standard Progress instance."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None, pulse_style="accent"),
        TaskProgressColumn(),
        console=console,
        transient=True,
    )


# ASCII Logo for display
CASCADE_LOGO = """
╔═╗┌─┐┌─┐┌─┐┌─┐┌┬┐┌─┐
║  ├─┤└─┐│  ├─┤ ││├┤
╚═╝┴ ┴└─┘└─┘┴ ┴─┴┘└─┘
"""


def print_logo() -> None:
    """Print the Cascade logo."""
    for line in CASCADE_LOGO.strip().split("\n"):
        console.print(f"[logo]{line}[/logo]")


def print_welcome(project_name: str | None = None, agent: str | None = None) -> None:
    """Print a welcome message."""
    from cascade.cli.ui import create_welcome_box

    welcome = create_welcome_box(
        console,
        project_name=project_name,
        agent=agent,
    )
    console.print(welcome)
