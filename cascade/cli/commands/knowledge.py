"""Knowledge commands for Cascade CLI."""

from __future__ import annotations

from typing import Any

import click

from cascade.cli.styles import (
    console,
    create_panel,
    create_table,
    print_banner,
    print_error,
    print_success,
)
from cascade.core.knowledge_base import KnowledgeBase
from cascade.core.project import get_project
from cascade.models.enums import KnowledgeStatus


@click.group()
@click.pass_context
def knowledge(ctx: click.Context) -> None:
    """Manage knowledge base (conventions, patterns, ADRs)."""
    pass


@knowledge.command("pending")
@click.pass_context
def pending(ctx: click.Context) -> None:
    """View proposed knowledge awaiting approval."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)
        pending_items = kb.get_pending_knowledge()

        patterns = pending_items["patterns"]
        adrs = pending_items["adrs"]

        if not patterns and not adrs:
            console.print("[dim]No pending knowledge items found.[/dim]")
            return

        # Show patterns
        if patterns:
            print_banner("Proposed Patterns")
            table = create_table(["ID", "NAME", "DESCRIPTION", "SOURCE"])

            for p in patterns:
                table.add_row(
                    f"[id]{p.id}[/id]",
                    p.pattern_name,
                    p.description[:60] + "..." if len(p.description) > 60 else p.description,
                    f"#{p.learned_from_ticket_id}" if p.learned_from_ticket_id else "-",
                )
            console.print(table)

        # Show ADRs
        if adrs:
            print_banner("Proposed ADRs")
            table = create_table(["ID", "REF", "TITLE", "DECISION"])

            for a in adrs:
                table.add_row(
                    f"[id]{a.id}[/id]",
                    f"ADR-{a.adr_number}",
                    a.title,
                    a.decision[:50] + "..." if len(a.decision) > 50 else a.decision,
                )
            console.print(table)

        console.print("\n[dim]Run:[/dim] [white]ccd knowledge approve <pattern|adr> <id>[/white]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@knowledge.command("approve")
@click.argument("entity_type", type=click.Choice(["pattern", "adr"]))
@click.argument("entity_id", type=int)
@click.pass_context
def approve(ctx: click.Context, entity_type: str, entity_id: int) -> None:
    """Approve a proposed pattern or ADR."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)

        if kb.approve(entity_type, entity_id):
            print_success(f"Approved {entity_type} [id]#{entity_id}[/id]")
        else:
            print_error(f"{entity_type.title()} #{entity_id} not found")
            raise SystemExit(1)

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@knowledge.command("reject")
@click.argument("entity_type", type=click.Choice(["pattern", "adr"]))
@click.argument("entity_id", type=int)
@click.pass_context
def reject(ctx: click.Context, entity_type: str, entity_id: int) -> None:
    """Reject a proposed pattern or ADR."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)

        if kb.reject(entity_type, entity_id):
            print_success(f"Rejected {entity_type} [id]#{entity_id}[/id]")
        else:
            print_error(f"{entity_type.title()} #{entity_id} not found")
            raise SystemExit(1)

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@knowledge.command("add-convention")
@click.option(
    "--category", "-c", required=True, help="Category (naming, style, structure, security)"
)
@click.option("--key", "-k", required=True, help="Convention key")
@click.option("--value", "-v", required=True, help="Convention value/rule")
@click.option("--rationale", "-r", default="", help="Why this convention exists")
@click.pass_context
def add_convention(ctx: click.Context, category: str, key: str, value: str, rationale: str) -> None:
    """Add a project convention."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)
        kb.add_convention(category, key, value, rationale)
        kb.sync_conventions_to_yaml()

        print_success(f"Added convention: [accent]{category}.{key}[/accent]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@knowledge.command("conventions")
@click.option(
    "--category",
    "-c",
    default=None,
    help="Filter by category (naming, style, structure, security)",
)
@click.pass_context
def conventions(ctx: click.Context, category: str | None) -> None:
    """View project conventions."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)
        convs = kb.get_conventions(category)

        if not convs:
            console.print(
                "[dim]No conventions defined. Edit .cascade/conventions.yaml to add some.[/dim]"
            )
            return

        print_banner("Project Conventions")

        # Group by category
        grouped: dict[str, list[Any]] = {}
        for c in convs:
            grouped.setdefault(c.category, []).append(c)

        for cat, items in sorted(grouped.items()):
            console.print(f"\n[label]{cat.upper()}[/label]")
            for item in items:
                console.print(
                    f" [accent]•[/accent] [white]{item.convention_key}[/white]: {item.convention_value}"
                )
                if item.rationale:
                    console.print(f"   [dim]({item.rationale})[/dim]")

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@knowledge.command("patterns")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["proposed", "approved", "rejected"]),
    default=None,
    help="Filter by status",
)
@click.pass_context
def patterns(ctx: click.Context, status: str | None) -> None:
    """List patterns."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)

        status_filter = KnowledgeStatus(status.upper()) if status else None
        pattern_list = kb.get_patterns(status=status_filter)

        if not pattern_list:
            console.print("[dim]No patterns found.[/dim]")
            return

        print_banner("Known Patterns")
        table = create_table(["ID", "NAME", "STATUS", "USES", "DESCRIPTION"])

        for p in pattern_list:
            status_style = {
                KnowledgeStatus.APPROVED: "success",
                KnowledgeStatus.PROPOSED: "status.progress",
                KnowledgeStatus.REJECTED: "error",
            }.get(p.status, "dim")

            table.add_row(
                f"[id]{p.id}[/id]",
                p.pattern_name,
                f"[{status_style}]{p.status.value}[/{status_style}]",
                str(p.reuse_count),
                p.description[:50] + "..." if len(p.description) > 50 else p.description,
            )
        console.print(table)

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@knowledge.command("adrs")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["proposed", "approved", "rejected", "superseded"]),
    default=None,
    help="Filter by status",
)
@click.pass_context
def adrs(ctx: click.Context, status: str | None) -> None:
    """List Architecture Decision Records."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)

        status_filter = KnowledgeStatus(status.upper()) if status else None
        adr_list = kb.get_adrs(status=status_filter)

        if not adr_list:
            console.print("[dim]No ADRs found.[/dim]")
            return

        print_banner("Architecture Catalog")
        table = create_table(["REF", "STATUS", "TITLE"])

        for a in adr_list:
            status_style = {
                KnowledgeStatus.APPROVED: "success",
                KnowledgeStatus.PROPOSED: "status.progress",
                KnowledgeStatus.REJECTED: "error",
                KnowledgeStatus.SUPERSEDED: "dim",
            }.get(a.status, "dim")

            table.add_row(
                f"ADR-{a.adr_number}",
                f"[{status_style}]{a.status.value}[/{status_style}]",
                a.title,
            )
        console.print(table)

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@knowledge.command("show-adr")
@click.argument("adr_number", type=int)
@click.pass_context
def show_adr(ctx: click.Context, adr_number: int) -> None:
    """Show ADR details."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)
        adr = kb.get_adr_by_number(adr_number)

        if not adr:
            print_error(f"ADR-{adr_number} not found")
            raise SystemExit(1)

        print_banner(f"ADR-{adr.adr_number}: {adr.title}")

        content = (
            f"[label]Status:[/label]    {adr.status.value}\n\n"
            f"[bold white]Context:[/bold white]\n{adr.context}\n\n"
            f"[bold white]Decision:[/bold white]\n{adr.decision}\n\n"
            f"[bold white]Rationale:[/bold white]\n{adr.rationale}\n"
        )

        if adr.consequences:
            content += f"\n[bold white]Consequences:[/bold white]\n{adr.consequences}\n"

        if adr.alternatives_considered:
            content += f"\n[bold white]Alternatives:[/bold white]\n{adr.alternatives_considered}\n"

        console.print(create_panel(content, border_style="dim"))

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@knowledge.command("show-pattern")
@click.argument("pattern_id", type=int)
@click.pass_context
def show_pattern(ctx: click.Context, pattern_id: int) -> None:
    """Show pattern details."""
    try:
        project = get_project()
        kb = KnowledgeBase(project.db, project.conventions_path)
        pattern = kb.get_pattern(pattern_id)

        if not pattern:
            print_error(f"Pattern #{pattern_id} not found")
            raise SystemExit(1)

        print_banner(f"Pattern: {pattern.pattern_name}")

        content = (
            f"[label]Status:[/label]    {pattern.status.value}\n"
            f"[label]Uses:[/label]      {pattern.reuse_count}\n\n"
            f"[bold white]Description:[/bold white]\n{pattern.description}\n"
        )

        if pattern.applies_to_tags:
            content += f"\n[label]Tags:[/label]      {', '.join(pattern.applies_to_tags)}\n"

        if pattern.code_template:
            content += f"\n[bold white]Code Template:[/bold white]\n{pattern.code_template}\n"

        if pattern.file_examples:
            content += "\n[bold white]Example Files:[/bold white]\n"
            for f in pattern.file_examples:
                content += f" [dim]•[/dim] {f}\n"

        console.print(create_panel(content, border_style="dim"))

    except FileNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)
