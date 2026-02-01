"""Modern theme system for Cascade CLI.

Provides customizable color schemes inspired by Claude, Codex, and Gemini CLIs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.theme import Theme


@dataclass
class ColorTheme:
    """A complete color theme for the CLI."""

    name: str
    # Primary colors
    primary: str = "rose"
    secondary: str = "white"
    accent: str = "magenta"

    # Semantic colors
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "cyan"
    muted: str = "dim white"

    # UI elements
    border: str = "bright_black"
    border_focus: str = "rose"
    header: str = "bold white"

    # Status colors
    status_ready: str = "blue"
    status_progress: str = "yellow"
    status_done: str = "green"
    status_blocked: str = "red"

    # Severity colors
    severity_critical: str = "bold red"
    severity_high: str = "red"
    severity_medium: str = "yellow"
    severity_low: str = "cyan"

    def to_rich_theme(self) -> Theme:
        """Convert to Rich Theme object."""
        return Theme(
            {
                "primary": self.primary,
                "secondary": self.secondary,
                "accent": self.accent,
                "success": f"bold {self.success}",
                "warning": self.warning,
                "error": f"bold {self.error}",
                "info": self.info,
                "muted": self.muted,
                "border": self.border,
                "border.focus": self.border_focus,
                "header": self.header,
                "label": "bold white",
                "value": self.info,
                "id": "bold yellow",
                "status.ready": self.status_ready,
                "status.progress": self.status_progress,
                "status.done": self.status_done,
                "status.blocked": self.error,
                # Logo and branding
                "logo": self.primary,
                "logo.accent": self.accent,
                # Input prompt
                "prompt": self.primary,
                "prompt.arrow": f"bold {self.primary}",
                # Severity
                "severity.critical": self.severity_critical,
                "severity.high": self.severity_high,
                "severity.medium": self.severity_medium,
                "severity.low": self.severity_low,
            }
        )


# Built-in themes
THEMES: dict[str, ColorTheme] = {
    "cascade": ColorTheme(
        name="cascade",
        primary="magenta",
        secondary="white",
        accent="bright_magenta",
        border="bright_black",
        border_focus="magenta",
    ),
    "rose": ColorTheme(
        name="rose",
        primary="#ff6b9d",  # Rose pink
        secondary="white",
        accent="#ff8fab",
        border="bright_black",
        border_focus="#ff6b9d",
        info="#f0a6ca",
    ),
    "claude": ColorTheme(
        name="claude",
        primary="#d4a574",  # Claude's orange/tan
        secondary="white",
        accent="#e8c49a",
        border="bright_black",
        border_focus="#d4a574",
    ),
    "codex": ColorTheme(
        name="codex",
        primary="#10a37f",  # OpenAI green
        secondary="white",
        accent="#19c37d",
        border="bright_black",
        border_focus="#10a37f",
    ),
    "gemini": ColorTheme(
        name="gemini",
        primary="#4285f4",  # Google blue
        secondary="white",
        accent="#8ab4f8",
        border="bright_black",
        border_focus="#4285f4",
    ),
    "minimal": ColorTheme(
        name="minimal",
        primary="white",
        secondary="dim white",
        accent="bright_white",
        border="dim",
        border_focus="white",
    ),
}


class ThemeManager:
    """Manages theme selection and persistence."""

    USER_CONFIG_PATH = Path.home() / ".cascaderc"

    def __init__(self) -> None:
        self._current_theme: ColorTheme | None = None
        self._user_config: dict[str, Any] = {}
        self._load_user_config()

    def _load_user_config(self) -> None:
        """Load user-wide configuration."""
        if self.USER_CONFIG_PATH.exists():
            try:
                self._user_config = json.loads(self.USER_CONFIG_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                self._user_config = {}

    def _save_user_config(self) -> None:
        """Save user-wide configuration."""
        try:
            self.USER_CONFIG_PATH.write_text(json.dumps(self._user_config, indent=2))
        except OSError:
            pass  # Silently fail if we can't write

    def get_theme(self, project_theme: str | None = None) -> ColorTheme:
        """Get the active theme, checking project then user config."""
        if self._current_theme:
            return self._current_theme

        # Priority: project > user config > default
        theme_name = project_theme or self._user_config.get("theme", "rose")
        self._current_theme = THEMES.get(theme_name, THEMES["rose"])
        return self._current_theme

    def set_theme(self, name: str, scope: str = "user") -> bool:
        """Set theme by name.

        Args:
            name: Theme name from THEMES
            scope: "user" for ~/.cascaderc, "project" for .cascade/config.yaml

        Returns:
            True if successful
        """
        if name not in THEMES:
            return False

        self._current_theme = THEMES[name]

        if scope == "user":
            self._user_config["theme"] = name
            self._save_user_config()

        return True

    def list_themes(self) -> list[str]:
        """List available theme names."""
        return list(THEMES.keys())

    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self._user_config.get(key, default)

    def set_user_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        self._user_config[key] = value
        self._save_user_config()


# Global theme manager instance
_theme_manager: ThemeManager | None = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def get_current_theme() -> ColorTheme:
    """Get the currently active theme."""
    return get_theme_manager().get_theme()
