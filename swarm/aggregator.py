"""
Aggregates all agent results into a unified structured report.
"""

import time
import logging
from datetime import datetime, UTC
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .schemas import AgentResult, AgentStatus, AggregatedReport

logger = logging.getLogger(__name__)
console = Console()


class Aggregator:
    def aggregate(
        self, command: str, results: list[AgentResult], start_time: float
    ) -> AggregatedReport:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        success_count = sum(1 for r in results if r.status == AgentStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == AgentStatus.FAILED)
        timeout_count = sum(1 for r in results if r.status == AgentStatus.TIMEOUT)
        blocked_count = sum(1 for r in results if r.status == AgentStatus.BLOCKED)

        warnings = []
        if failed_count > 0:
            warnings.append(f"{failed_count} agent(s) failed")
        if timeout_count > 0:
            warnings.append(f"{timeout_count} agent(s) timed out")

        failed_results = [r for r in results if r.status in (AgentStatus.FAILED, AgentStatus.TIMEOUT)]
        for r in failed_results[:3]:
            for e in r.errors[:2]:
                warnings.append(f"Agent {r.agent_id}: {e}")

        summary_parts = []
        total = len(results)
        summary_parts.append(f"{success_count}/{total} agents succeeded")

        if success_count > 0:
            avg_time = sum(r.duration_ms for r in results if r.status == AgentStatus.SUCCESS) // max(success_count, 1)
            summary_parts.append(f"avg {avg_time}ms per successful agent")

        if failed_count > 0:
            summary_parts.append(f"{failed_count} failed")
        if timeout_count > 0:
            summary_parts.append(f"{timeout_count} timed out")

        summary = f"Swarm complete: {', '.join(summary_parts)}. Total: {elapsed_ms}ms."

        return AggregatedReport(
            command=command,
            total_agents=total,
            total_time_ms=elapsed_ms,
            success_count=success_count,
            failed_count=failed_count,
            timed_out_count=timeout_count,
            block_count=blocked_count,
            summary=summary,
            agent_results=results,
            warnings=warnings,
            generated_at=datetime.now(UTC).isoformat(),
        )

    def print_report(self, report: AggregatedReport):
        console.print()
        console.rule("[bold green]Results[/bold green]")

        summary = (
            f"[bold]Command:[/bold] {report.command}\n"
            f"[bold]Total Agents:[/bold] {report.total_agents}\n"
            f"[bold]Success:[/bold] {report.success_count}  "
            f"[bold]Failed:[/bold] {report.failed_count}  "
            f"[bold]Timed Out:[/bold] {report.timed_out_count}\n"
            f"[bold]Total Time:[/bold] {report.total_time_ms}ms\n"
            f"[bold]Summary:[/bold] {report.summary}"
        )
        console.print(Panel(summary, title="Swarm Report", border_style="green"))

        if report.agent_results:
            table = Table(title="Agent Results")
            table.add_column("Agent", style="cyan", justify="right")
            table.add_column("Status", justify="center")
            table.add_column("Time", justify="right")
            table.add_column("Result", style="white")
            table.add_column("Errors", style="red")

            for r in report.agent_results:
                status_style = {
                    AgentStatus.SUCCESS: "green",
                    AgentStatus.FAILED: "red",
                    AgentStatus.TIMEOUT: "yellow",
                    AgentStatus.BLOCKED: "red",
                }.get(r.status, "white")

                table.add_row(
                    str(r.agent_id),
                    f"[{status_style}]{r.status.value}[/{status_style}]",
                    f"{r.duration_ms}ms",
                    r.result[:60] if r.result else "—",
                    "; ".join(r.errors[:2]) if r.errors else "—",
                )

            console.print(table)

        if report.warnings:
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for w in report.warnings:
                console.print(f"  [yellow]⚠ {w}[/yellow]")

        console.print()
