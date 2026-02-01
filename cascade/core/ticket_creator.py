"""Automatic ticket creation from AI discoveries."""

from __future__ import annotations

import logging
import re

from cascade.core.ticket_manager import TicketManager
from cascade.models.enums import Severity, TicketType

logger = logging.getLogger(__name__)


class TicketCreator:
    """Creates tickets from AI-discovered work and suggestions."""

    def __init__(self, ticket_manager: TicketManager):
        """
        Initialize ticket creator.

        Args:
            ticket_manager: The ticket manager to create tickets with
        """
        self.tm = ticket_manager

    def create_from_discoveries(
        self,
        discovered_items: list[str],
        parent_ticket_id: int,
        default_severity: Severity = Severity.MEDIUM,
    ) -> list[int]:
        """
        Create complete, verbose tickets from AI-discovered work items.

        Args:
            discovered_items: List of discovery strings from NEW_TICKETS_NEEDED
            parent_ticket_id: The ticket that discovered these items
            default_severity: Default severity for created tickets

        Returns:
            List of created ticket IDs
        """
        created_ids = []

        for item in discovered_items:
            item = item.strip()
            if not item:
                continue

            # Parse the discovery item to extract ticket type and details
            ticket_data = self._parse_discovery_item(item, parent_ticket_id, default_severity)

            if ticket_data:
                try:
                    # Create ticket with ALL fields populated
                    ticket_id = self.tm.create(
                        title=ticket_data["title"],
                        description=ticket_data["description"],
                        ticket_type=ticket_data["type"],
                        severity=ticket_data["severity"],
                        topics=ticket_data.get("topics", []),
                        acceptance_criteria=ticket_data.get("acceptance_criteria", ""),
                        affected_files=ticket_data.get("affected_files", []),
                        estimated_effort=ticket_data.get("estimated_effort"),
                    )
                    created_ids.append(ticket_id)
                    logger.info(
                        f"Auto-created {ticket_data['type'].value} ticket #{ticket_id}: "
                        f"{ticket_data['title']} (discovered by #{parent_ticket_id}) "
                        f"with {len(ticket_data.get('affected_files', []))} affected files"
                    )
                except Exception as e:
                    logger.error(f"Failed to create ticket from discovery '{item[:50]}...': {e}")

        return created_ids

    def _parse_discovery_item(
        self, item: str, parent_ticket_id: int, default_severity: Severity
    ) -> dict | None:
        """
        Parse a discovery item into ticket data.

        Discovery items can be formatted like:
        - "BUG: Similar validation missing in signup.py:156"
        - "SECURITY: Password reset has no rate limiting"
        - "TEST: Missing integration tests for OAuth flow"
        - "DOC: API docs outdated"
        - "TASK: Refactor duplicate code in auth module"
        - "Similar bugs in user_controller.py"

        Args:
            item: Discovery string
            parent_ticket_id: Parent ticket ID
            default_severity: Default severity

        Returns:
            Dictionary with ticket data or None if unparseable
        """
        # Try to extract type prefix
        type_match = re.match(r"^(BUG|SECURITY|TEST|DOC|TASK|STORY|EPIC):\s*(.+)", item, re.I)

        if type_match:
            type_str = type_match.group(1).upper()
            description = type_match.group(2).strip()
            ticket_type = TicketType(type_str)
        else:
            # No explicit type - infer from keywords
            ticket_type = self._infer_ticket_type(item)
            description = item

        # Determine severity based on type and keywords
        severity = self._determine_severity(item, ticket_type, default_severity)

        # Generate title (first 80 chars or until period/newline)
        title = self._generate_title(description, ticket_type)

        # Build full description with context
        full_description = self._build_description(description, parent_ticket_id)

        # Extract affected files from the description (file.py:line patterns)
        affected_files = self._extract_affected_files(description)

        # Generate acceptance criteria based on type and description
        acceptance_criteria = self._generate_acceptance_criteria(
            ticket_type, description, affected_files
        )

        # Estimate effort based on type and complexity
        estimated_effort = self._estimate_effort(ticket_type, description, affected_files)

        return {
            "title": title,
            "description": full_description,
            "type": ticket_type,
            "severity": severity,
            "topics": [],  # Could be inferred from parent ticket in future
            "acceptance_criteria": acceptance_criteria,
            "affected_files": affected_files,
            "estimated_effort": estimated_effort,
        }

    def _infer_ticket_type(self, text: str) -> TicketType:
        """Infer ticket type from text content."""
        text_lower = text.lower()

        # Security keywords
        if any(
            kw in text_lower
            for kw in [
                "security",
                "vulnerability",
                "injection",
                "xss",
                "csrf",
                "authentication",
                "authorization",
                "exposure",
                "leak",
            ]
        ):
            return TicketType.SECURITY

        # Test keywords
        if any(
            kw in text_lower
            for kw in ["test", "testing", "coverage", "integration test", "unit test"]
        ):
            return TicketType.TEST

        # Doc keywords
        if any(
            kw in text_lower
            for kw in ["documentation", "docs", "readme", "outdated", "document", "api docs"]
        ):
            return TicketType.DOC

        # Bug keywords
        if any(
            kw in text_lower
            for kw in ["bug", "fix", "broken", "error", "crash", "fails", "incorrect"]
        ):
            return TicketType.BUG

        # Default to TASK for everything else
        return TicketType.TASK

    def _determine_severity(
        self, text: str, ticket_type: TicketType, default: Severity
    ) -> Severity:
        """Determine severity based on text and type."""
        text_lower = text.lower()

        # Critical indicators
        if any(
            kw in text_lower
            for kw in [
                "critical",
                "blocking",
                "security vulnerability",
                "data loss",
                "crash",
                "production",
            ]
        ):
            return Severity.CRITICAL

        # High indicators
        if any(
            kw in text_lower for kw in ["important", "major", "high priority", "urgent", "affects"]
        ):
            return Severity.HIGH

        # Security issues default to HIGH unless specified otherwise
        if ticket_type == TicketType.SECURITY:
            return Severity.HIGH

        # Low indicators
        if any(kw in text_lower for kw in ["minor", "cosmetic", "nice to have", "polish"]):
            return Severity.LOW

        return default

    def _generate_title(self, description: str, ticket_type: TicketType) -> str:
        """Generate a concise title from description."""
        # Take first sentence or 80 chars, whichever is shorter
        first_sentence = description.split(".")[0].split("\n")[0].strip()
        title = first_sentence[:80] if len(first_sentence) > 80 else first_sentence

        # Remove any file references with line numbers for cleaner titles
        title = re.sub(r"\s+\([^)]*:\d+\)", "", title)
        title = re.sub(r"\s+in\s+\S+\.py:\d+", "", title)

        return title

    def _build_description(self, original_description: str, parent_ticket_id: int) -> str:
        """Build full, verbose description with context."""
        return f"""{original_description}

**Discovery Context**:
- Discovered while working on ticket #{parent_ticket_id}
- Auto-created from AI analysis during execution
- Review and adjust details as needed before execution

**Why This Matters**:
This issue was identified during active development, indicating it's directly related to current work and likely important for system quality.

**Next Steps**:
1. Verify the issue/opportunity exists by examining the code/files mentioned
2. Prioritize relative to other work based on severity and impact
3. Update acceptance criteria and description if more details are discovered
4. Execute when ready - all necessary context is provided below
"""

    def _extract_affected_files(self, description: str) -> list[str]:
        """
        Extract file paths from description.

        Looks for patterns like:
        - filename.py
        - path/to/file.py
        - file.py:123 (with line numbers)
        """
        files = []

        # Pattern 1: file.ext or path/file.ext or file.ext:line
        file_patterns = [
            r"([a-zA-Z0-9_/\-\.]+\.[a-zA-Z]{2,4})(?::\d+)?",  # file.ext or file.ext:line
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, description)
            files.extend(matches)

        # Deduplicate while preserving order
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen and self._is_valid_filename(f):
                seen.add(f)
                unique_files.append(f)

        return unique_files[:10]  # Limit to 10 files to avoid noise

    def _is_valid_filename(self, filename: str) -> bool:
        """Check if string looks like a valid filename."""
        # Must have extension
        if "." not in filename:
            return False

        # Common code file extensions
        valid_extensions = {
            "py",
            "js",
            "ts",
            "jsx",
            "tsx",
            "java",
            "cpp",
            "c",
            "h",
            "go",
            "rs",
            "rb",
            "php",
            "css",
            "html",
            "sql",
            "sh",
            "yaml",
            "yml",
            "json",
            "xml",
            "md",
        }

        ext = filename.split(".")[-1].lower()
        return ext in valid_extensions

    def _generate_acceptance_criteria(
        self, ticket_type: TicketType, description: str, affected_files: list[str]
    ) -> str:
        """
        Generate comprehensive acceptance criteria based on ticket type.

        Creates specific, testable criteria that an AI can verify.
        """
        criteria_parts = []

        # Type-specific criteria
        if ticket_type == TicketType.BUG:
            criteria_parts.append("**Fix Verification**:")
            criteria_parts.append("- [ ] Root cause identified and documented")
            criteria_parts.append("- [ ] Fix implemented with minimal code changes")
            criteria_parts.append("- [ ] Issue no longer reproduces with the fix")
            criteria_parts.append("- [ ] No new bugs introduced (existing tests pass)")
            criteria_parts.append("")
            criteria_parts.append("**Testing**:")
            criteria_parts.append("- [ ] Regression test added that would have caught this bug")
            criteria_parts.append("- [ ] Test fails without the fix, passes with the fix")

        elif ticket_type == TicketType.SECURITY:
            criteria_parts.append("**Security Fix Verification**:")
            criteria_parts.append("- [ ] Vulnerability completely eliminated (not just mitigated)")
            criteria_parts.append("- [ ] Similar patterns checked system-wide and fixed")
            criteria_parts.append("- [ ] No new security issues introduced")
            criteria_parts.append("- [ ] OWASP/security best practices followed")
            criteria_parts.append("")
            criteria_parts.append("**Testing**:")
            criteria_parts.append("- [ ] Security tests added that attempt to exploit the vulnerability")
            criteria_parts.append("- [ ] Tests fail (blocked) after fix")

        elif ticket_type == TicketType.TEST:
            criteria_parts.append("**Test Coverage**:")
            criteria_parts.append("- [ ] Tests cover happy path scenarios")
            criteria_parts.append("- [ ] Tests cover edge cases and boundary conditions")
            criteria_parts.append("- [ ] Tests cover error/failure paths")
            criteria_parts.append("- [ ] All new tests pass")
            criteria_parts.append("")
            criteria_parts.append("**Test Quality**:")
            criteria_parts.append("- [ ] Test names clearly describe what is being tested")
            criteria_parts.append("- [ ] Tests are independent (no shared state)")
            criteria_parts.append("- [ ] Tests run fast (mocked external dependencies)")

        elif ticket_type == TicketType.DOC:
            criteria_parts.append("**Documentation Quality**:")
            criteria_parts.append("- [ ] Documentation is technically accurate (verified against code)")
            criteria_parts.append("- [ ] Content is clear and appropriate for target audience")
            criteria_parts.append("- [ ] Examples are provided and runnable")
            criteria_parts.append("- [ ] Formatting is consistent (markdown, links, code blocks)")

        elif ticket_type == TicketType.TASK:
            criteria_parts.append("**Implementation**:")
            criteria_parts.append("- [ ] Implements exactly what is described (no scope creep)")
            criteria_parts.append("- [ ] Follows project conventions and patterns")
            criteria_parts.append("- [ ] Code is clean, maintainable, and well-structured")
            criteria_parts.append("")
            criteria_parts.append("**Testing**:")
            criteria_parts.append("- [ ] Unit tests added for new functionality")
            criteria_parts.append("- [ ] All tests pass")

        elif ticket_type == TicketType.STORY:
            criteria_parts.append("**Feature Completion**:")
            criteria_parts.append("- [ ] Feature works as described from user perspective")
            criteria_parts.append("- [ ] Handles happy path scenarios correctly")
            criteria_parts.append("- [ ] Handles edge cases gracefully with clear error messages")
            criteria_parts.append("- [ ] Consistent with existing UI/UX patterns")
            criteria_parts.append("")
            criteria_parts.append("**Testing**:")
            criteria_parts.append("- [ ] Tests cover user workflows")
            criteria_parts.append("- [ ] Tests cover edge cases")

        # Add file-specific criteria if files are mentioned
        if affected_files:
            criteria_parts.append("")
            criteria_parts.append("**Affected Files**:")
            for file_path in affected_files[:5]:  # Limit to 5
                criteria_parts.append(f"- [ ] Changes in `{file_path}` are complete and tested")

        # General criteria for all types
        criteria_parts.append("")
        criteria_parts.append("**Quality Gates**:")
        criteria_parts.append("- [ ] Code passes linting/static analysis")
        criteria_parts.append("- [ ] No syntax or type errors")
        criteria_parts.append("- [ ] All tests pass")

        return "\n".join(criteria_parts)

    def _estimate_effort(
        self, ticket_type: TicketType, description: str, affected_files: list[str]
    ) -> int:
        """
        Estimate effort in story points (1-8 scale).

        1-2: Quick fixes, simple changes
        3-5: Standard work, moderate complexity
        5-8: Complex work, multiple files, architectural changes
        """
        base_effort = {
            TicketType.BUG: 3,  # Bugs vary, default to medium
            TicketType.SECURITY: 5,  # Security is complex and thorough
            TicketType.TEST: 2,  # Tests are usually quick
            TicketType.DOC: 2,  # Docs are usually quick
            TicketType.TASK: 3,  # Tasks vary, default to medium
            TicketType.STORY: 5,  # Stories are typically larger
            TicketType.EPIC: 8,  # Epics are always large
        }.get(ticket_type, 3)

        # Adjust based on complexity indicators
        description_lower = description.lower()

        # Increase for complexity keywords
        if any(
            kw in description_lower
            for kw in [
                "refactor",
                "architecture",
                "system-wide",
                "multiple",
                "complex",
                "significant",
            ]
        ):
            base_effort = min(8, base_effort + 2)

        # Increase based on number of affected files
        if len(affected_files) > 3:
            base_effort = min(8, base_effort + 1)
        elif len(affected_files) > 5:
            base_effort = min(8, base_effort + 2)

        # Decrease for simple keywords
        if any(kw in description_lower for kw in ["simple", "quick", "minor", "small"]):
            base_effort = max(1, base_effort - 1)

        return base_effort

    def _build_description(self, original_description: str, parent_ticket_id: int) -> str:
        """Build full, verbose description with context."""
        return f"""{original_description}

**Discovery Context**:
- Discovered while working on ticket #{parent_ticket_id}
- Auto-created from AI analysis during execution
- Review and adjust details as needed before execution

**Why This Matters**:
This issue was identified during active development, indicating it's directly related to current work and likely important for system quality.

**Next Steps**:
1. Verify the issue/opportunity exists by examining the code/files mentioned
2. Prioritize relative to other work based on severity and impact
3. Update acceptance criteria and description if more details are discovered
4. Execute when ready - all necessary context is provided below
"""
