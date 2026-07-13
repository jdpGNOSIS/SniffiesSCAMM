"""
CLI interface for the Swarm Multi-Agent Orchestration System.

Usage:
  bots 10 test signup flow on https://example.com
  bots 5 scrape product pages
  swarm --help
"""

import asyncio
import sys
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .controller import SwarmController
from .config import SwarmConfig

console = Console()


def show_commands():
    cmd_path = Path(__file__).parent.parent / "agents" / "command-station" / "COMMANDS.md"
    if not cmd_path.exists():
        console.print("[red]COMMANDS.md not found.[/red]")
        return
    text = cmd_path.read_text(encoding="utf-8")
    categories = []
    for line in text.splitlines():
        if line.startswith("## "):
            cat = line.strip("# ").strip()
            if cat and cat not in ("How To Use",):
                categories.append(cat)
    table = Table(title=f"1,281+ Commands — {len(categories)} Categories", border_style="cyan")
    table.add_column("Category", style="magenta")
    for i, cat in enumerate(categories, 1):
        table.add_row(f"{i:2d}. {cat}")
    console.print(table)
    console.print("\n[dim]See agents/command-station/COMMANDS.md for full details.[/dim]")


def show_teams():
    teams = [
        ("Marketing", 60), ("Sales", 10), ("Intelligence", 10), ("Strategy", 7),
        ("Content", 10), ("Research", 8), ("Direction", 4), ("Managing", 4),
    ]
    table = Table(title="8 Teams — 113 Agents", border_style="cyan")
    table.add_column("Team", style="magenta")
    table.add_column("Agents", justify="right", style="green")
    for name, count in teams:
        table.add_row(name, str(count))
    console.print(table)


def run_cli():
    config = SwarmConfig()
    controller = SwarmController(config)

    console.print()
    console.rule("[bold magenta]Swarm Multi-Agent Orchestrator[/bold magenta]")
    console.print()
    console.print(Panel(
        "Type [bold cyan]bots <number> <task>[/bold cyan] to launch agents.\n"
        "Examples:\n"
        "  bots 5 health check https://example.com\n"
        "  bots 10 ssl check https://example.com\n"
        "  bots 20 port scan example.com\n"
        "  bots 3 check if my API is responding\n\n"
        "Commands: [bold]list commands[/bold] [bold]list teams[/bold] "
        "[bold]history[/bold] [bold]replay[/bold] [bold]help[/bold] [bold]exit[/bold]",
        title="Swarm CLI",
        border_style="magenta",
    ))
    console.print()

    while True:
        try:
            raw = input("swarm> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Goodbye.[/yellow]")
            break

        if not raw:
            continue

        c = raw.lower()

        if c in ("exit", "quit", "q"):
            console.print("[yellow]Shutting down swarm controller.[/yellow]")
            break

        if c in ("history", "h"):
            history = controller.get_history()
            if not history:
                console.print("[dim]No task history yet.[/dim]")
            else:
                for i, h in enumerate(history, 1):
                    console.print(f"  {i}. {h.command} — {h.summary[:80]}")
            continue

        if c in ("replay", "r"):
            controller.replay_last()
            continue

        if c in ("help", "?"):
            console.print(Panel(
                "[bold]Usage[/bold]\n\n"
                "  [cyan]bots <N> <task>[/cyan]  Launch N agents on a task\n"
                "  [cyan]list commands[/cyan]     Show all command categories\n"
                "  [cyan]list teams[/cyan]        Show the 8 teams\n"
                "  [cyan]history[/cyan]           Show task history\n"
                "  [cyan]replay[/cyan]            Re-run last task\n"
                "  [cyan]exit[/cyan]              Quit\n\n"
                "[bold]Server Testing Examples[/bold]\n"
                "  bots 5 health check https://example.com\n"
                "  bots 10 ssl check https://example.com\n"
                "  bots 8 port scan example.com\n"
                "  bots 15 load test https://api.example.com",
                title="Help",
                border_style="cyan",
            ))
            continue

        if c in ("list commands", "commands"):
            show_commands()
            continue

        if c in ("list teams", "teams"):
            show_teams()
            continue

        if raw.startswith("bots ") or raw.startswith("bot "):
            asyncio.run(controller.run(raw))
        else:
            console.print(
                "[yellow]Unknown command. Try: bots <N> <task> | list commands | "
                "list teams | history | help | exit[/yellow]"
            )


def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s | %(name)s | %(message)s",
    )
    run_cli()


if __name__ == "__main__":
    main()
