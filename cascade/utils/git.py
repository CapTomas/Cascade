"""Git provider for repository operations."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from cascade.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GitResult:
    """Result of a git operation."""

    success: bool
    output: str
    error: str = ""


class GitProvider:
    """
    Provider for Git operations.

    Uses subprocess to interact with git, avoiding external dependencies.
    """

    def __init__(self, repo_path: Path | None = None) -> None:
        """
        Initialize Git provider.

        Args:
            repo_path: Path to the repository. If None, uses current directory.
        """
        self.repo_path = repo_path or Path.cwd()
        self._git_available: bool | None = None

    def is_available(self) -> bool:
        """Check if git is available and we're in a repository."""
        if self._git_available is not None:
            return self._git_available

        try:
            result = self._run_git(["rev-parse", "--git-dir"])
            self._git_available = result.success
        except Exception:
            self._git_available = False

        return self._git_available

    def get_current_branch(self) -> str | None:
        """Get the current branch name."""
        result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        if result.success:
            return result.output.strip()
        return None

    def create_branch(self, name: str, checkout: bool = True) -> GitResult:
        """
        Create a new branch.

        Args:
            name: Branch name.
            checkout: Whether to checkout the branch after creation.
        """
        # Sanitize branch name
        safe_name = self._sanitize_branch_name(name)

        if checkout:
            return self._run_git(["checkout", "-b", safe_name])
        else:
            return self._run_git(["branch", safe_name])

    def checkout(self, branch: str) -> GitResult:
        """Checkout a branch."""
        return self._run_git(["checkout", branch])

    def commit(self, message: str, add_all: bool = False) -> GitResult:
        """
        Create a commit.

        Args:
            message: Commit message.
            add_all: Whether to add all changes before committing.
        """
        if add_all:
            add_result = self._run_git(["add", "-A"])
            if not add_result.success:
                return add_result

        return self._run_git(["commit", "-m", message])

    def get_status(self, short: bool = True) -> GitResult:
        """Get repository status."""
        args = ["status"]
        if short:
            args.append("--short")
        return self._run_git(args)

    def get_diff(self, staged: bool = False, file_path: str | None = None) -> GitResult:
        """
        Get diff output.

        Args:
            staged: If True, show staged changes only.
            file_path: Optional specific file to diff.
        """
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file_path:
            args.extend(["--", file_path])
        return self._run_git(args)

    def get_log(self, count: int = 10, oneline: bool = True) -> GitResult:
        """
        Get commit log.

        Args:
            count: Number of commits to show.
            oneline: Use one-line format.
        """
        args = ["log", f"-{count}"]
        if oneline:
            args.append("--oneline")
        return self._run_git(args)

    def add_files(self, paths: list[str]) -> GitResult:
        """Add files to staging area."""
        if not paths:
            return GitResult(success=False, output="", error="No paths provided")
        return self._run_git(["add"] + paths)

    def stash(self, message: str | None = None) -> GitResult:
        """Stash current changes."""
        args = ["stash", "push"]
        if message:
            args.extend(["-m", message])
        return self._run_git(args)

    def stash_pop(self) -> GitResult:
        """Pop the most recent stash."""
        return self._run_git(["stash", "pop"])

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        result = self._run_git(["status", "--porcelain"])
        return bool(result.output.strip())

    def get_remote_url(self) -> str | None:
        """Get the remote origin URL."""
        result = self._run_git(["remote", "get-url", "origin"])
        if result.success:
            return result.output.strip()
        return None

    def _run_git(self, args: list[str]) -> GitResult:
        """
        Run a git command.

        Args:
            args: Command arguments (without 'git').
        """
        cmd = ["git"] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            success = result.returncode == 0
            output = result.stdout
            error = result.stderr

            if not success:
                logger.debug(f"Git command failed: {' '.join(cmd)}")
                logger.debug(f"Error: {error}")

            return GitResult(success=success, output=output, error=error)

        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: {' '.join(cmd)}")
            return GitResult(success=False, output="", error="Command timed out")
        except FileNotFoundError:
            logger.error("Git executable not found")
            return GitResult(success=False, output="", error="Git not found")
        except Exception as e:
            logger.error(f"Git command error: {e}")
            return GitResult(success=False, output="", error=str(e))

    @staticmethod
    def _sanitize_branch_name(name: str) -> str:
        """
        Sanitize a string for use as a branch name.

        Replaces spaces and special characters with dashes.
        """
        # Replace common separators with dashes
        sanitized = name.strip().lower()
        for char in [" ", "_", ".", "/", "\\", ":"]:
            sanitized = sanitized.replace(char, "-")

        # Remove consecutive dashes
        while "--" in sanitized:
            sanitized = sanitized.replace("--", "-")

        # Remove leading/trailing dashes
        sanitized = sanitized.strip("-")

        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50].rstrip("-")

        return sanitized


def create_ticket_branch_name(ticket_id: int, title: str) -> str:
    """
    Create a branch name for a ticket.

    Format: ticket-{id}-{sanitized-title}
    """
    provider = GitProvider()
    safe_title = provider._sanitize_branch_name(title)
    return f"ticket-{ticket_id}-{safe_title}"
