"""Modern UI components for Cascade CLI.

Box-drawing utilities and screen layouts inspired by Claude, Codex, and Gemini CLIs.
"""

from __future__ import annotations

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# Box drawing characters (Unicode)
class BoxChars:
    """Unicode box drawing characters."""

    # Single line
    H = "─"  # horizontal
    V = "│"  # vertical
    TL = "╭"  # top-left rounded
    TR = "╮"  # top-right rounded
    BL = "╰"  # bottom-left rounded
    BR = "╯"  # bottom-right rounded

    # Double line
    DH = "═"
    DV = "║"
    DTL = "╔"
    DTR = "╗"
    DBL = "╚"
    DBR = "╝"

    # Connectors
    T_DOWN = "┬"
    T_UP = "┴"
    T_RIGHT = "├"
    T_LEFT = "┤"
    CROSS = "┼"


# ASCII Art Logo for Cascade
CASCADE_LOGO = """
╔═╗┌─┐┌─┐┌─┐┌─┐┌┬┐┌─┐
║  ├─┤└─┐│  ├─┤ ││├┤
╚═╝┴ ┴└─┘└─┘┴ ┴─┴┘└─┘
"""

CASCADE_LOGO_SMALL = """
╔═╗┌─┐┌─┐┌─┐┌─┐┌┬┐┌─┐
║  ├─┤└─┐│  ├─┤ ││├┤
╚═╝┴ ┴└─┘└─┘┴ ┴─┴┘└─┘
"""

CASCADE_LOGO_MINI = "▐█▌ CASCADE"


def get_terminal_width(console: Console) -> int:
    """Get terminal width, defaulting to 80 if unknown."""
    return console.width or 80


def draw_horizontal_line(
    console: Console,
    char: str = BoxChars.H,
    style: str = "border",
    width: int | None = None,
) -> None:
    """Draw a horizontal line across the terminal."""
    w = width or get_terminal_width(console)
    console.print(char * w, style=style)


def draw_divider(console: Console, title: str | None = None) -> None:
    """Draw a divider line, optionally with a centered title."""
    width = get_terminal_width(console)

    if title:
        title_text = f" {title} "
        side_width = (width - len(title_text)) // 2
        left = BoxChars.H * side_width
        right = BoxChars.H * (width - side_width - len(title_text))
        console.print(
            f"[border]{left}[/border][header]{title_text}[/header][border]{right}[/border]"
        )
    else:
        console.print(BoxChars.H * width, style="border")


def create_box(
    content: str | Text,
    title: str | None = None,
    subtitle: str | None = None,
    border_style: str = "border",
    padding: tuple[int, int] = (0, 1),
    width: int | None = None,
) -> Panel:
    """Create a modern box panel with rounded corners."""
    return Panel(
        content,
        title=title,
        subtitle=subtitle,
        border_style=border_style,
        box=box.ROUNDED,
        padding=padding,
        width=width,
        expand=True if width is None else False,
    )


def create_welcome_box(
    console: Console,
    project_name: str | None = None,
    agent: str | None = None,
    directory: str | None = None,
    version: str = "1.0.0",
    user: str | None = None,
) -> Panel:
    """Create a welcome screen box like Claude/Codex/Gemini CLIs."""
    width = min(get_terminal_width(console), 100)

    # Left side: Logo and basic info
    left_content = Text()

    # Add small logo
    for line in CASCADE_LOGO_SMALL.strip().split("\n"):
        left_content.append(line + "\n", style="logo")

    left_content.append("\n")

    if user:
        left_content.append("Welcome back, ", style="muted")
        left_content.append(f"{user}!\n", style="header")

    if agent:
        left_content.append(f"\n{agent}", style="accent")
        left_content.append(" · ", style="muted")

    if directory:
        left_content.append(f"\n{directory}", style="muted")

    # Right side: Tips and recent activity
    right_content = Text()
    right_content.append("Tips for getting started\n", style="header")
    right_content.append("Type ", style="muted")
    right_content.append("help", style="accent")
    right_content.append(" to see available commands\n", style="muted")
    right_content.append("Type ", style="muted")
    right_content.append("status", style="accent")
    right_content.append(" to view project dashboard\n", style="muted")

    right_content.append("\n" + BoxChars.H * 40 + "\n", style="border")

    right_content.append("Recent activity\n", style="header")
    right_content.append("No recent activity\n", style="muted")

    # Create two-column layout
    left_panel = Panel(
        left_content,
        border_style="border",
        box=box.ROUNDED,
        width=width // 2 - 2,
    )

    right_panel = Panel(
        right_content,
        border_style="border",
        box=box.ROUNDED,
        width=width // 2 - 2,
    )

    # Combine into main box
    columns = Columns([left_panel, right_panel], equal=True, expand=True)

    title = f"[logo]Cascade[/logo] [muted]v{version}[/muted]"
    if project_name:
        title = f"[logo]Cascade[/logo] [muted]·[/muted] [header]{project_name}[/header]"

    return Panel(
        columns,
        title=title,
        border_style="border.focus",
        box=box.ROUNDED,
        padding=(0, 0),
    )


def create_prompt_box(console: Console, placeholder: str = "Type your message...") -> Panel:
    """Create an input prompt box like modern CLIs."""
    content = Text()
    content.append("› ", style="prompt.arrow")
    content.append(placeholder, style="muted")

    return Panel(
        content,
        border_style="border",
        box=box.ROUNDED,
        padding=(0, 1),
    )


def create_status_hud(items: list[tuple[str, str]]) -> Table:
    """Create a horizontal status bar (HUD)."""
    table = Table(
        box=None,
        show_header=False,
        expand=True,
        padding=(0, 2),
    )

    for _ in items:
        table.add_column(justify="center")

    row = []
    for label, value in items:
        row.append(f"[muted]{label}[/muted] [accent]{value}[/accent]")

    table.add_row(*row)
    return table


def create_dashboard_panel(
    title: str,
    content: str | Text | Table,
    border_style: str = "border",
) -> Panel:
    """Create a dashboard-style panel."""
    return Panel(
        content,
        title=f"[header]{title}[/header]",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 2),
    )


def create_modern_table(
    columns: list[str],
    title: str | None = None,
    show_lines: bool = False,
) -> Table:
    """Create a clean, modern table."""
    table = Table(
        title=title,
        show_header=True,
        header_style="accent",
        box=box.ROUNDED if show_lines else box.SIMPLE_HEAD,
        border_style="border",
        expand=True,
        padding=(0, 1),
    )

    for col in columns:
        table.add_column(col)

    return table


def print_success_box(console: Console, message: str, title: str = "Success") -> None:
    """Print a success message in a styled box."""
    console.print(
        Panel(
            f"[success]✓[/success] {message}",
            title=f"[success]{title}[/success]",
            border_style="success",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def print_error_box(console: Console, message: str, title: str = "Error") -> None:
    """Print an error message in a styled box."""
    console.print(
        Panel(
            f"[error]✗[/error] {message}",
            title=f"[error]{title}[/error]",
            border_style="error",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def print_warning_box(console: Console, message: str, title: str = "Warning") -> None:
    """Print a warning message in a styled box."""
    console.print(
        Panel(
            f"[warning]⚠[/warning] {message}",
            title=f"[warning]{title}[/warning]",
            border_style="warning",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def print_info_box(console: Console, message: str, title: str | None = None) -> None:
    """Print an info message in a styled box."""
    console.print(
        Panel(
            f"[info]ℹ[/info] {message}",
            title=f"[info]{title}[/info]" if title else None,
            border_style="info",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def print_keyboard_shortcuts(console: Console) -> None:
    """Print keyboard shortcuts help."""
    shortcuts = [
        ("?", "Show this help"),
        ("Type help", "To see all commands"),
        ("Type status", "To see project dashboard"),
        ("↑/↓", "Navigate history"),
        ("Tab", "Autocomplete"),
        ("Ctrl+C", "Cancel / Exit"),
    ]

    table = create_modern_table(["Key", "Action"])
    for key, action in shortcuts:
        table.add_row(f"[accent]{key}[/accent]", action)

    console.print(
        Panel(
            table,
            title="[header]Keyboard Shortcuts[/header]",
            border_style="border",
            box=box.ROUNDED,
        )
    )
