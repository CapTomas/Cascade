"""Git commands for Cascade CLI."""

from __future__ import annotations

import click

from cascade.cli.styles import (
    console,
    print_banner,
)
from cascade.core.project import get_project
from cascade.utils.git import GitProvider


@click.group("git")
@click.pass_context
def git(ctx: click.Context) -> None:
    """Git repository utilities."""
    pass


@git.command("status")
@click.pass_context
def git_status(ctx: click.Context) -> None:
    """Show git repository status."""
    try:
        project = get_project()
        provider = GitProvider(project.root)

        if not provider.is_available():
            console.print("[error]ERROR:[/error] Not a git repository or git not available.")
            raise SystemExit(1)

        # Current branch
        branch = provider.get_current_branch()
        console.print(f"[accent]Branch:[/accent] {branch or 'detached HEAD'}")

        # Status
        result = provider.get_status(short=True)
        if result.success:
            if result.output.strip():
                console.print()
                print_banner("Changes")
                for line in result.output.strip().split("\n"):
                    if line.startswith("M"):
                        console.print(f"[warning]  {line}[/warning]")
                    elif line.startswith("A") or line.startswith("?"):
                        console.print(f"[success]  {line}[/success]")
                    elif line.startswith("D"):
                        console.print(f"[error]  {line}[/error]")
                    else:
                        console.print(f"  {line}")
            else:
                console.print("[success]✓ Working tree clean[/success]")

    except FileNotFoundError:
        console.print("[error]ERROR:[/error] Not in a Cascade project.")
        raise SystemExit(1)


@git.command("log")
@click.option("--count", "-n", default=10, help="Number of commits to show.")
@click.pass_context
def git_log(ctx: click.Context, count: int) -> None:
    """Show recent commits."""
    try:
        project = get_project()
        provider = GitProvider(project.root)

        if not provider.is_available():
            console.print("[error]ERROR:[/error] Not a git repository.")
            raise SystemExit(1)

        result = provider.get_log(count=count, oneline=True)
        if result.success:
            print_banner(f"Recent Commits (Last {count})")
            for line in result.output.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        sha, msg = parts
                        console.print(f"[dim]{sha}[/dim] {msg}")
                    else:
                        console.print(f"[dim]{line}[/dim]")
        else:
            console.print(f"[error]ERROR:[/error] {result.error}")

    except FileNotFoundError:
        console.print("[error]ERROR:[/error] Not in a Cascade project.")
        raise SystemExit(1)


@git.command("diff")
@click.option("--staged", "-s", is_flag=True, help="Show staged changes only.")
@click.argument("file_path", required=False)
@click.pass_context
def git_diff(ctx: click.Context, staged: bool, file_path: str | None) -> None:
    """Show diff of changes."""
    try:
        project = get_project()
        provider = GitProvider(project.root)

        if not provider.is_available():
            console.print("[error]ERROR:[/error] Not a git repository.")
            raise SystemExit(1)

        result = provider.get_diff(staged=staged, file_path=file_path)
        if result.success:
            if result.output.strip():
                console.print(result.output)
            else:
                label = "staged " if staged else ""
                console.print(f"[dim]No {label}changes.[/dim]")
        else:
            console.print(f"[error]ERROR:[/error] {result.error}")

    except FileNotFoundError:
        console.print("[error]ERROR:[/error] Not in a Cascade project.")
        raise SystemExit(1)


@git.command("branch")
@click.argument("name", required=False)
@click.option("--checkout/--no-checkout", default=True, help="Checkout after creating.")
@click.pass_context
def git_branch(ctx: click.Context, name: str | None, checkout: bool) -> None:
    """Create a new branch or show current branch."""
    try:
        project = get_project()
        provider = GitProvider(project.root)

        if not provider.is_available():
            console.print("[error]ERROR:[/error] Not a git repository.")
            raise SystemExit(1)

        if not name:
            # Show current branch
            branch = provider.get_current_branch()
            console.print(f"[accent]Current branch:[/accent] {branch or 'detached HEAD'}")
            return

        # Create new branch
        result = provider.create_branch(name, checkout=checkout)
        if result.success:
            action = "Created and checked out" if checkout else "Created"
            console.print(f"[success]✓ {action} branch:[/success] {name}")
        else:
            console.print(f"[error]ERROR:[/error] {result.error}")

    except FileNotFoundError:
        console.print("[error]ERROR:[/error] Not in a Cascade project.")
        raise SystemExit(1)


@git.command("commit")
@click.option("--message", "-m", required=True, help="Commit message.")
@click.option("--all", "-a", "add_all", is_flag=True, help="Add all changes before committing.")
@click.pass_context
def git_commit(ctx: click.Context, message: str, add_all: bool) -> None:
    """Create a commit."""
    try:
        project = get_project()
        provider = GitProvider(project.root)

        if not provider.is_available():
            console.print("[error]ERROR:[/error] Not a git repository.")
            raise SystemExit(1)

        result = provider.commit(message, add_all=add_all)
        if result.success:
            console.print(f"[success]✓ Committed:[/success] {message}")
        else:
            if "nothing to commit" in result.error or "nothing to commit" in result.output:
                console.print("[dim]Nothing to commit.[/dim]")
            else:
                console.print(f"[error]ERROR:[/error] {result.error}")

    except FileNotFoundError:
        console.print("[error]ERROR:[/error] Not in a Cascade project.")
        raise SystemExit(1)
