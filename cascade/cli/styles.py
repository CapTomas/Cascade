"""Premium styling utilities for Cascade CLI."""

from rich import box
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Studio Theme: Deep, professional, high-contrast
CASCADE_THEME = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "header": "bold white",
    "accent": "bold blue",
    "muted": "dim white",
    "id": "bold yellow",
    "status.open": "blue",
    "status.progress": "yellow",
    "status.done": "green",
    "status.fail": "red",
    "label": "bold white",
    "value": "cyan",
})

console = Console(theme=CASCADE_THEME)

def print_banner(title: str) -> None:
    """Print a minimalist section banner."""
    console.print(f"\n[accent]●[/accent] [header]{title.upper()}[/header] " + "─" * (40 - len(title)))

def create_hud(items: list[tuple[str, str]], title: str = "SYSTEM STATUS") -> Panel:
    """Create a HUD-style horizontal display."""
    parts = []
    for label, value in items:
        parts.append(f"[label]{label.upper()}[/label] [value]{value}[/value]")

    content = "  [dim]•[/dim]  ".join(parts)
    return Panel(content, title=f"[dim]{title}[/dim]", border_style="dim", padding=(0, 1))

def create_table(columns: list[str], title: str | None = None) -> Table:
    """Create a streamlined table with horizontal dividers only."""
    table = Table(
        title=title,
        show_header=True,
        header_style="accent",
        box=box.HORIZONTALS,
        border_style="dim",
        expand=True
    )
    for col in columns:
        table.add_column(col)
    return table

def print_step(message: str, current: int, total: int) -> None:
    """Print a progress step."""
    console.print(f"[dim][{current}/{total}][/dim] [info]{message}...[/info]")

def create_panel(content: str, title: str | None = None, border_style: str = "dim") -> Panel:
    """Create a rich panel."""
    return Panel(content, title=title, border_style=border_style, padding=(1, 2))

def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[success]SUCCESS:[/success] {message}")

def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[error]ERROR:[/error] {message}")

def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]WARNING:[/warning] {message}")

def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[info]INFO:[/info] {message}")

def create_solution_panel(error: str, solution: str) -> Panel:
    """Create a panel for errors with solutions."""
    content = f"[error]ERROR:[/error] {error}\n\n[accent]TRY THIS:[/accent]\n{solution}"
    return Panel(content, title="[bold red]ISSUE DETECTED[/bold red]", border_style="red")
def get_progress() -> Progress:
    """Get a standard Progress instance."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None, pulse_style="accent"),
        TaskProgressColumn(),
        console=console,
        transient=True
    )
