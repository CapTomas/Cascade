"""Centralized logging for Cascade."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    level: int = logging.INFO, log_file: Path | None = None, console: bool = True
) -> None:
    """
    Configure global logging for Cascade.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional path to log file. If not provided, logs to .cascade/logs/cascade.log
        console: Whether to log to stdout
    """
    # Create log directory if it doesn't exist
    if log_file:
        log_dir = log_file.parent
    else:
        # Default path
        log_dir = Path.cwd() / ".cascade" / "logs"
        log_file = log_dir / "cascade.log"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to current directory if .cascade is not accessible
        log_dir = Path.cwd()
        log_file = log_dir / "cascade.log"

    handlers: list[logging.Handler] = []

    # File handler with rotation (10MB per file, keep 5 copies)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_fmt)
    handlers.append(file_handler)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        # Professional CLI format: just level and message for console
        console_fmt = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_fmt)
        handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,  # Ensure we override any existing basicConfig
    )

    logging.info(f"Logging initialized at level {logging.getLevelName(level)}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
