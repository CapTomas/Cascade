from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime

from cascade.agents.interface import AgentInterface
from cascade.core.context_builder import ContextBuilder
from cascade.core.exceptions import (
    TicketError,
)
from cascade.core.knowledge_base import KnowledgeBase
from cascade.core.knowledge_extractor import KnowledgeExtractor
from cascade.core.prompt_builder import PromptBuilder
from cascade.core.quality_gates import QualityGates
from cascade.core.ticket_manager import TicketManager
from cascade.models.enums import ContextMode, TicketStatus
from cascade.models.execution import ExecutionResult
from cascade.models.knowledge import ADR, Pattern
from cascade.models.ticket import Ticket
from cascade.utils.git import GitProvider, create_ticket_branch_name
from cascade.utils.logger import get_logger

logger = get_logger(__name__)


class TicketExecutor:
    """
    Executes exactly one ticket with context escalation.

    Orchestrates the process of building context, generating prompts,
    calling AI agents, and handling results.
    """

    def __init__(
        self,
        agent: AgentInterface,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        ticket_manager: TicketManager,
        quality_gates: QualityGates,
        knowledge_base: KnowledgeBase,
        knowledge_extractor: KnowledgeExtractor | None = None,
        git_provider: GitProvider | None = None,
    ):
        """
        Initialize ticket executor.

        Args:
            agent: The AI agent to use for execution
            context_builder: Component to build execution context
            prompt_builder: Component to build AI prompts
            ticket_manager: Component to manage ticket state
            git_provider: Provider for git operations (optional)
        """
        self.agent = agent
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.tm = ticket_manager
        self.quality_gates = quality_gates
        self.kb = knowledge_base
        self.knowledge_extractor = knowledge_extractor or KnowledgeExtractor()
        self.git_provider = git_provider

    def execute(
        self,
        ticket_id: int,
        confirm_callback: Callable[[Ticket, str], bool] | None = None,
        dry_run: bool = False,
        streaming_callback: Callable[[str], None] | None = None,
    ) -> ExecutionResult:
        """
        Execute a single ticket.

        Steps:
        1. Load ticket and check dependencies
        2. Context escalation loop (Minimal -> Standard -> Full)
        3. For each mode:
            a. Build context and prompt
            b. Get human confirmation (if callback provided)
            c. Execute via agent
            d. Verify (quality gates - Phase 4)
            e. On success: update ticket, log, and return
        4. If all modes fail, return error result

        Args:
            ticket_id: ID of the ticket to execute
            confirm_callback: Optional function to get human approval before execution

        Returns:
            ExecutionResult containing outcome
        """
        ticket = self.tm.get(ticket_id)
        if not ticket:
            logger.error(f"Execution failed: Ticket #{ticket_id} not found")
            raise TicketError(f"Ticket #{ticket_id} not found")

        if self.tm.has_unmet_dependencies(ticket_id):
            blocking = [t.id for t in self.tm.get_blocking_tickets(ticket_id)]
            logger.warning(
                f"Execution blocked: Ticket #{ticket_id} depends on incomplete tickets {blocking}"
            )
            return ExecutionResult(
                success=False,
                ticket_id=ticket_id,
                context_mode=ContextMode.MINIMAL,
                agent_response="",
                error=f"Ticket is blocked by tickets: {blocking}",
            )

        # Update status to IN_PROGRESS
        self.tm.update_status(ticket_id, TicketStatus.IN_PROGRESS)
        self.log_action(ticket_id, "START_EXECUTION", details=f"Agent: {self.agent.get_name()}")

        # Git: Create branch if clean
        ticket_branch = None
        if self.git_provider and self.git_provider.is_available():
            if not self.git_provider.has_uncommitted_changes() and not dry_run:
                ticket_branch = create_ticket_branch_name(ticket_id, ticket.title)
                res = self.git_provider.create_branch(ticket_branch)
                if res.success:
                    logger.info(f"Created branch: {ticket_branch}")
                    self.log_action(ticket_id, "GIT_BRANCH_CREATED", details=ticket_branch)
                else:
                    logger.warning(f"Failed to create branch: {res.error}")

        modes = [ContextMode.MINIMAL, ContextMode.STANDARD, ContextMode.FULL]
        last_error = None

        for mode in modes:
            logger.info(f"Executing ticket #{ticket_id} in {mode.value} mode")
            self.log_action(
                ticket_id,
                "ESCALATION_EVENT",
                details=f"Attempting execution with {mode.value} context mode",
            )

            from cascade.utils.tokens import TokenBudget

            budget = TokenBudget().get_limit(mode.value)

            context = self.context_builder.build_context(ticket, mode, token_budget=budget)
            prompt = self.prompt_builder.build_execution_prompt(context)

            if dry_run:
                self.log_action(
                    ticket_id, "DRY_RUN", details=f"Prompt generated for mode: {mode.value}"
                )
                self.tm.update_status(ticket_id, TicketStatus.READY)
                # Cleanup branch if created (though dry run shouldn't create it usually, but we guard above)
                return ExecutionResult(
                    success=True,
                    ticket_id=ticket_id,
                    context_mode=mode,
                    agent_response=prompt,  # We return the prompt as the response
                    error="Dry run completed successfully",
                )

            # Human confirmation step
            if confirm_callback and not confirm_callback(ticket, prompt):
                self.log_action(ticket_id, "EXECUTION_CANCELLED", details="Cancelled by human")
                self.tm.update_status(ticket_id, TicketStatus.READY)
                if ticket_branch:
                    # Switch back to previous branch? For now we stay on the new branch but maybe log it
                    logger.info("Execution cancelled, remaining on ticket branch.")
                return ExecutionResult(
                    success=False,
                    ticket_id=ticket_id,
                    context_mode=mode,
                    agent_response="",
                    error="Execution cancelled by user",
                )

            start_time = time.time()
            try:
                response = self.agent.execute(prompt, callback=streaming_callback)
                execution_time_ms = int((time.time() - start_time) * 1000)

                if response.success:
                    # Run quality gates (Phase 4)
                    gate_results = self.quality_gates.run_all(ticket, response)

                    if gate_results.all_passed:
                        # Success!
                        self.tm.update_status(ticket_id, TicketStatus.DONE)
                        self.tm.update(ticket_id, context_mode=mode.value)

                        # Git: Commit changes
                        if self.git_provider and self.git_provider.is_available() and ticket_branch:
                            commit_msg = f"Complete ticket #{ticket_id}: {ticket.title}"
                            res = self.git_provider.commit(commit_msg, add_all=True)
                            if res.success:
                                logger.info(f"Committed changes: {commit_msg}")
                                self.log_action(ticket_id, "GIT_COMMIT", details=commit_msg)
                            else:
                                logger.warning(f"Failed to commit: {res.error}")

                        # Knowledge Extraction (Phase 5)
                        proposals = []
                        if self.knowledge_extractor:
                            try:
                                extracted = self.knowledge_extractor.extract_proposals(
                                    response.content, ticket_id
                                )
                                for item in extracted:
                                    if isinstance(item, Pattern):
                                        self.kb.propose_pattern(
                                            pattern_name=item.pattern_name,
                                            description=item.description,
                                            code_template=item.code_template,
                                            applies_to_tags=item.applies_to_tags,
                                            learned_from_ticket_id=item.learned_from_ticket_id,
                                            file_examples=item.file_examples,
                                        )
                                    elif isinstance(item, ADR):
                                        self.kb.propose_adr(
                                            title=item.title,
                                            context=item.context,
                                            decision=item.decision,
                                            rationale=item.rationale,
                                            consequences=item.consequences,
                                            alternatives_considered=item.alternatives_considered,
                                            created_by_ticket_id=item.created_by_ticket_id,
                                        )
                                    proposals.append(item.to_dict())
                            except Exception as ke:
                                logger.error(f"Knowledge extraction failed: {ke}")
                                self.log_action(
                                    ticket_id, "KNOWLEDGE_EXTRACTION_ERROR", details=str(ke)
                                )

                        self.log_action(
                            ticket_id,
                            "EXECUTION_SUCCESS",
                            agent=self.agent.get_name(),
                            context_mode=mode,
                            details=f"Modified {len(response.files_modified)} files. All quality gates passed. Extracted {len(proposals)} knowledge proposals.",
                            token_count=response.token_count,
                            execution_time_ms=execution_time_ms,
                        )

                        return ExecutionResult(
                            success=True,
                            ticket_id=ticket_id,
                            context_mode=mode,
                            agent_response=response.content,
                            token_usage=response.token_count,
                            execution_time_ms=execution_time_ms,
                            gate_results=gate_results,
                            proposals=proposals,
                        )
                    else:
                        failed_gate_names = [r.gate_name for r in gate_results.failed_gates]
                        last_error = f"Quality gates failed: {', '.join(failed_gate_names)}"
                        for r in gate_results.failed_gates:
                            if r.output:
                                logger.debug(f"Gate {r.gate_name} output: {r.output}")

                        self.log_action(
                            ticket_id,
                            "QUALITY_GATE_FAILURE",
                            agent=self.agent.get_name(),
                            context_mode=mode,
                            details=last_error,
                            execution_time_ms=execution_time_ms,
                        )
                        # Fall through to escalation/retry
                else:
                    last_error = response.error or "Unknown agent error"
                    self.log_action(
                        ticket_id,
                        "AGENT_EXECUTION_FAILURE",
                        agent=self.agent.get_name(),
                        context_mode=mode,
                        details=last_error,
                        execution_time_ms=execution_time_ms,
                    )

            except Exception as e:
                last_error = str(e)
                logger.exception(f"Unexpected error during execution with mode {mode.value}")
                self.log_action(
                    ticket_id,
                    "EXECUTION_ERROR",
                    agent=self.agent.get_name(),
                    context_mode=mode,
                    details=f"Exception: {last_error}",
                )

            logger.warning(f"Execution failed in {mode.value} mode. Last error: {last_error}")
            if mode != modes[-1]:
                logger.info(f"Escalating from {mode.value} to next mode...")

        # If we reach here, all modes failed
        self.tm.update_status(ticket_id, TicketStatus.BLOCKED)
        return ExecutionResult(
            success=False,
            ticket_id=ticket_id,
            context_mode=ContextMode.FULL,
            agent_response="",
            error=f"All context modes exhausted. Last error: {last_error}",
        )

    def execute_batch(
        self,
        ticket_ids: list[int],
        confirm_callback: Callable[[list[Ticket], str], bool] | None = None,
        dry_run: bool = False,
        streaming_callback: Callable[[str], None] | None = None,
    ) -> ExecutionResult:
        """
        Execute multiple tickets together.

        Steps:
        1. Load all tickets and check dependencies.
        2. Escalation loop (Minimal -> Standard -> Full).
        3. Build combined multi-context and batch prompt.
        4. Execute via agent.
        5. Parse <batch_summary> to determine per-ticket success.
        6. Run quality gates for all affected tickets.
        7. Update statuses and log.
        """
        tickets = []
        for tid in ticket_ids:
            t = self.tm.get(tid)
            if not t:
                raise TicketError(f"Ticket #{tid} not found")
            if self.tm.has_unmet_dependencies(tid):
                blocking = [bt.id for bt in self.tm.get_blocking_tickets(tid)]
                return ExecutionResult(
                    success=False,
                    ticket_id=tid,
                    context_mode=ContextMode.MINIMAL,
                    agent_response="",
                    error=f"Ticket #{tid} is blocked by: {blocking}",
                )
            tickets.append(t)

        # Update all to IN_PROGRESS
        for tid in ticket_ids:
            self.tm.update_status(tid, TicketStatus.IN_PROGRESS)
            self.log_action(tid, "START_BATCH_EXECUTION", details=f"Batch size: {len(ticket_ids)}")

        modes = [ContextMode.MINIMAL, ContextMode.STANDARD, ContextMode.FULL]
        last_error = None

        for mode in modes:
            logger.info(f"Executing batch {ticket_ids} in {mode.value} mode")

            from cascade.utils.tokens import TokenBudget

            budget = TokenBudget().get_limit(mode.value)

            context = self.context_builder.build_multi_context(tickets, mode, token_budget=budget)
            prompt = self.prompt_builder.build_multi_execution_prompt(context)

            if dry_run:
                for tid in ticket_ids:
                    self.tm.update_status(tid, TicketStatus.READY)
                return ExecutionResult(
                    success=True,
                    ticket_id=ticket_ids[0],
                    affected_ticket_ids=ticket_ids,
                    context_mode=mode,
                    agent_response=prompt,
                    error="Dry run batch completed",
                )

            if confirm_callback and not confirm_callback(tickets, prompt):
                for tid in ticket_ids:
                    self.tm.update_status(tid, TicketStatus.READY)
                return ExecutionResult(
                    success=False,
                    ticket_id=ticket_ids[0],
                    context_mode=mode,
                    agent_response="",
                    error="Batch execution cancelled by user",
                )

            start_time = time.time()
            try:
                response = self.agent.execute(prompt, callback=streaming_callback)
                execution_time_ms = int((time.time() - start_time) * 1000)

                if response.success:
                    # Parse batch summary
                    import re

                    summary_match = re.search(
                        r"<batch_summary>(.*?)</batch_summary>", response.content, re.DOTALL
                    )
                    statuses = {}
                    if summary_match:
                        summary_text = summary_match.group(1)
                        for line in summary_text.strip().split("\n"):
                            m = re.search(r"TICKET #(\d+):\s*(\w+)", line)
                            if m:
                                t_id = int(m.group(1))
                                t_status = m.group(2).upper()
                                statuses[t_id] = t_status

                    # Verify and run gates per ticket
                    all_passed = True
                    results_map = {}
                    for t in tickets:
                        # Even if agent says success, we run gates
                        assert t.id is not None
                        gate_results = self.quality_gates.run_all(t, response)
                        results_map[t.id] = gate_results

                        agent_success = statuses.get(t.id) == "SUCCESS"
                        if gate_results.all_passed and agent_success:
                            self.tm.update_status(t.id, TicketStatus.DONE)
                            self.tm.update(t.id, context_mode=mode.value)
                            self.log_action(
                                t.id, "BATCH_EXECUTION_SUCCESS", details="Part of successful batch"
                            )
                        else:
                            all_passed = False
                            # If it failed, we'll need to handle it. For now, mark as READY/BLOCKED depending on mode
                            self.tm.update_status(t.id, TicketStatus.READY)
                            self.log_action(
                                t.id,
                                "BATCH_EXECUTION_FAILURE",
                                details="Gate failed or agent reported failure for this ticket.",
                            )

                    # Knowledge extraction (on whole response)
                    proposals = []
                    if self.knowledge_extractor:
                        try:
                            extracted = self.knowledge_extractor.extract_proposals(
                                response.content, ticket_ids[0]
                            )
                            for item in extracted:
                                # (same KB proposal logic as single execute)
                                if isinstance(item, Pattern):
                                    self.kb.propose_pattern(
                                        pattern_name=item.pattern_name,
                                        description=item.description,
                                        code_template=item.code_template,
                                        applies_to_tags=item.applies_to_tags,
                                        learned_from_ticket_id=ticket_ids[
                                            0
                                        ],  # Using first ticket in batch for simplicity
                                        file_examples=item.file_examples,
                                    )
                                elif isinstance(item, ADR):
                                    self.kb.propose_adr(
                                        title=item.title,
                                        context=item.context,
                                        decision=item.decision,
                                        rationale=item.rationale,
                                        consequences=item.consequences,
                                        alternatives_considered=item.alternatives_considered,
                                        created_by_ticket_id=ticket_ids[0],
                                    )
                                proposals.append(item.to_dict())
                        except Exception as ke:
                            logger.error(f"Knowledge extraction failed: {ke}")

                    return ExecutionResult(
                        success=all_passed,
                        ticket_id=ticket_ids[0],
                        affected_ticket_ids=ticket_ids,
                        context_mode=mode,
                        agent_response=response.content,
                        token_usage=response.token_count,
                        execution_time_ms=execution_time_ms,
                        proposals=proposals,
                        # We might need a way to return multiple gate results, but for now we aggregate
                        error=None
                        if all_passed
                        else "Some tickets in the batch failed validation.",
                    )
                else:
                    last_error = response.error or "Unknown agent error"
            except Exception as e:
                last_error = str(e)
                logger.exception("Batch execution error")

        # All modes failed
        for tid in ticket_ids:
            self.tm.update_status(tid, TicketStatus.BLOCKED)
        return ExecutionResult(
            success=False,
            ticket_id=ticket_ids[0],
            context_mode=ContextMode.FULL,
            agent_response="",
            error=f"All modes exhausted for batch. Last error: {last_error}",
        )

    def log_action(
        self,
        ticket_id: int,
        action: str,
        agent: str | None = None,
        context_mode: ContextMode | None = None,
        details: str | None = None,
        token_count: int | None = None,
        execution_time_ms: int | None = None,
    ) -> None:
        """Log an execution action to the database."""
        data = {
            "ticket_id": ticket_id,
            "action": action,
            "agent": agent,
            "context_mode": context_mode.value if context_mode else None,
            "details": details,
            "token_count": token_count,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now(),
        }
        self.tm.db.insert("execution_log", data)
