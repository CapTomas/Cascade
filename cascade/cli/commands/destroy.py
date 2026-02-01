"""Destroy command for Cascade CLI."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from cascade.cli.styles import console, print_error, print_success, print_warning
from cascade.core.project import CascadeProject


@click.command("destroy")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation",
)
@click.pass_context
def destroy_cmd(ctx: click.Context, force: bool) -> None:
    """
    Uninitialize a Cascade project.

    Permanently deletes the .cascade directory and all its contents
    (database, configuration, logs, etc.).
    """
    try:
        # We don't use get_project() because it raises if not initialized
        # we just want to find the root
        current = Path.cwd()
        project_root = None
        while current != current.parent:
            if (current / CascadeProject.CASCADE_DIR).exists():
                project_root = current
                break
            current = current.parent

        if not project_root:
            project_root = Path.cwd()
            if not (project_root / CascadeProject.CASCADE_DIR).exists():
                print_warning("No Cascade project found in this directory (or parents).")
                return

        cascade_dir = project_root / CascadeProject.CASCADE_DIR

        if not force:
            print_warning(f"This will permanently delete the Cascade project at {cascade_dir}")
            print_warning("All tickets, topics, and configuration will be lost.")
            if not click.confirm("Are you sure you want to continue?"):
                console.print("Operation cancelled.")
                return

        console.print(f"[dim]Removing {cascade_dir}...[/dim]")
        shutil.rmtree(cascade_dir)
        print_success("Project uninitialized successfully.")

    except Exception as e:
        print_error(f"Failed to destroy project: {e}")
        raise SystemExit(1)
