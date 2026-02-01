"""Metrics service for aggregating execution and ticket data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from cascade.storage.database import Database


@dataclass
class ExecutionMetrics:
    """Metrics for a single execution or aggregated executions."""

    total_executions: int = 0
    total_tokens: int = 0
    total_time_ms: int = 0
    avg_tokens_per_execution: float = 0.0
    avg_time_ms_per_execution: float = 0.0
    by_agent: dict[str, int] = field(default_factory=dict)
    by_context_mode: dict[str, int] = field(default_factory=dict)


@dataclass
class TicketMetrics:
    """Metrics for tickets."""

    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    estimated_effort: int = 0
    actual_effort: int = 0
    effort_accuracy: float = 0.0  # actual / estimated


@dataclass
class QualityMetrics:
    """Metrics for quality gates."""

    total_runs: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    by_gate: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass
class ProjectMetrics:
    """Complete project metrics."""

    execution: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    tickets: TicketMetrics = field(default_factory=TicketMetrics)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    period_start: datetime | None = None
    period_end: datetime | None = None


class MetricsService:
    """
    Service for aggregating and computing project metrics.

    Reads from the database to compute execution stats, ticket progress,
    and quality gate performance.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_execution_metrics(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> ExecutionMetrics:
        """Get execution metrics for a time period."""
        metrics = ExecutionMetrics()

        # Build query with optional time filters
        query = "SELECT agent, context_mode, token_count, execution_time_ms FROM execution_log WHERE 1=1"
        params: list[Any] = []

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())

        rows = self.db.fetch_all(query, tuple(params))

        if not rows:
            return metrics

        metrics.total_executions = len(rows)

        for row in rows:
            agent = row["agent"] or "unknown"
            context_mode = row["context_mode"] or "unknown"
            tokens = row["token_count"] or 0
            time_ms = row["execution_time_ms"] or 0

            metrics.total_tokens += tokens
            metrics.total_time_ms += time_ms
            metrics.by_agent[agent] = metrics.by_agent.get(agent, 0) + 1
            metrics.by_context_mode[context_mode] = metrics.by_context_mode.get(context_mode, 0) + 1

        if metrics.total_executions > 0:
            metrics.avg_tokens_per_execution = metrics.total_tokens / metrics.total_executions
            metrics.avg_time_ms_per_execution = metrics.total_time_ms / metrics.total_executions

        return metrics

    def get_ticket_metrics(self) -> TicketMetrics:
        """Get ticket metrics."""
        metrics = TicketMetrics()

        # Count by status
        status_query = "SELECT status, COUNT(*) as count FROM tickets GROUP BY status"
        for row in self.db.fetch_all(status_query):
            status = row["status"]
            count = row["count"]
            metrics.by_status[status] = count
            metrics.total += count

        # Count by type
        type_query = "SELECT ticket_type, COUNT(*) as count FROM tickets GROUP BY ticket_type"
        for row in self.db.fetch_all(type_query):
            ticket_type = row["ticket_type"]
            count = row["count"]
            metrics.by_type[ticket_type] = count

        # Effort metrics
        effort_query = """
            SELECT
                COALESCE(SUM(estimated_effort), 0) as estimated,
                COALESCE(SUM(actual_effort), 0) as actual
            FROM tickets
            WHERE status = 'DONE'
        """
        res = self.db.fetch_one(effort_query)
        if res:
            metrics.estimated_effort = res["estimated"] or 0
            metrics.actual_effort = res["actual"] or 0
            if metrics.estimated_effort > 0:
                metrics.effort_accuracy = metrics.actual_effort / metrics.estimated_effort

        return metrics

    def get_quality_metrics(self) -> QualityMetrics:
        """Get quality gate metrics."""
        metrics = QualityMetrics()

        query = "SELECT gate_name, passed FROM quality_gates"
        rows = self.db.fetch_all(query)

        if not rows:
            return metrics

        metrics.total_runs = len(rows)

        for row in rows:
            gate_name = row["gate_name"]
            passed = row["passed"]

            if gate_name not in metrics.by_gate:
                metrics.by_gate[gate_name] = {"passed": 0, "failed": 0}

            if passed:
                metrics.passed += 1
                metrics.by_gate[gate_name]["passed"] += 1
            else:
                metrics.failed += 1
                metrics.by_gate[gate_name]["failed"] += 1

        if metrics.total_runs > 0:
            metrics.pass_rate = metrics.passed / metrics.total_runs

        return metrics

    def get_project_metrics(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> ProjectMetrics:
        """Get complete project metrics."""
        return ProjectMetrics(
            execution=self.get_execution_metrics(since, until),
            tickets=self.get_ticket_metrics(),
            quality=self.get_quality_metrics(),
            period_start=since,
            period_end=until,
        )

    def get_daily_activity(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily execution activity for the last N days."""
        since = datetime.now() - timedelta(days=days)

        query = """
            SELECT
                DATE(timestamp) as day,
                COUNT(*) as executions,
                COALESCE(SUM(token_count), 0) as tokens
            FROM execution_log
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY day DESC
        """

        rows = self.db.fetch_all(query, (since.isoformat(),))
        return [dict(row) for row in rows]
