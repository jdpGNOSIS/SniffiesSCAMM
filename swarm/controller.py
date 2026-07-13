"""
Master orchestrator — parses command, decomposes tasks, spawns workers, collects results.
"""

import asyncio
import logging
import time
import json
import os
from datetime import datetime, UTC
from rich.console import Console

from .schemas import SwarmCommand, AgentResult, AgentStatus, AggregatedReport, ProgressReport
from .parser import parse_command
from .decomposer import decompose
from .worker import WorkerAgent
from .aggregator import Aggregator
from .config import SwarmConfig

logger = logging.getLogger(__name__)
console = Console()


class SwarmController:
    def __init__(self, config: SwarmConfig | None = None):
        self.config = config or SwarmConfig()
        self.config.ensure_dirs()
        self._history: list[AggregatedReport] = []
        self._active_tasks: dict[int, asyncio.Task] = {}

    async def run(self, raw_command: str) -> AggregatedReport:
        start = time.monotonic()
        console.rule(f"[bold cyan]Swarm: {raw_command}[/bold cyan]")

        parsed = parse_command(raw_command)
        if isinstance(parsed, str):
            console.print(f"[red][ERR] {parsed}[/red]")
            return AggregatedReport(
                command=raw_command,
                total_agents=0,
                total_time_ms=0,
                success_count=0,
                failed_count=0,
                timed_out_count=0,
                block_count=1,
                summary=parsed,
                warnings=[parsed],
                generated_at=datetime.now(UTC).isoformat(),
            )

        console.print(f"[green][OK] Parsed: {parsed.agent_count} bots | {parsed.task_description}[/green]")
        if parsed.target_url:
            console.print(f"  Target URL: {parsed.target_url}")
        console.print(f"  Inferred type: {parsed.inferred_type.value}")

        subtasks = decompose(parsed)
        console.print(f"[cyan]>> Decomposed into {len(subtasks)} sub-tasks[/cyan]")

        results = await self._execute_swarm(subtasks)

        aggregator = Aggregator()
        report = aggregator.aggregate(raw_command, results, start)

        self._save_report(report)
        self._history.append(report)

        aggregator.print_report(report)
        return report

    async def _execute_swarm(self, subtasks: list) -> list[AgentResult]:
        semaphore = asyncio.Semaphore(10)

        async def run_worker(subtask):
            async with semaphore:
                worker = WorkerAgent(subtask.agent_id)
                result = await worker.execute(subtask)
                status_icon = "+" if result.status == AgentStatus.SUCCESS else "-"
                console.print(
                    f"  [{status_icon}] Agent {result.agent_id:2d} | "
                    f"{result.status.value:8s} | {result.duration_ms:5d}ms | "
                    f"{result.result[:60] if result.result else '—'}"
                )
                return result

        tasks = [run_worker(s) for s in subtasks]
        results = await asyncio.gather(*tasks)
        return results

    def _save_report(self, report: AggregatedReport):
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.config.results_dir, f"swarm_{timestamp}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2, default=str)
        console.print(f"[dim]Report saved: {path}[/dim]")

    def get_history(self) -> list[AggregatedReport]:
        return self._history.copy()

    def replay_last(self) -> AggregatedReport | None:
        if not self._history:
            console.print("[yellow]No task history to replay[/yellow]")
            return None
        last = self._history[-1]
        console.print(f"[cyan]Replaying: {last.command}[/cyan]")
        return last
