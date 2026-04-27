"""
Bholu AI — Dual-Agent Planner–Executor Framework
=================================================
Demonstrates agentic prompt injection attacks and their architectural mitigation.

Usage:
    python main.py                          # secure mode, 5 emails
    python main.py --mode vulnerable        # show the attack succeeding
    python main.py --mode secure --count 10 # read 10 emails, secure mode
    python main.py --help                   # full usage

Requirements:
    - Ollama running locally  (ollama serve)
    - llama3.2 model pulled   (ollama pull llama3.2)
    - credentials.json in this directory (see README.md for Gmail API setup)
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure imports work when running from the bholu-ai/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from tools.gmail_client import GmailClient
from tools.ollama_client import OllamaClient
from agents.planner import PlannerAgent, ALLOWED_ACTION_TYPES
from agents.executor import ExecutorAgent, EXECUTION_LOG, REJECTED_LOG
from models import ExecutionResult

console = Console()

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema", "action_schema.json")

BANNER = """
██████╗ ██╗  ██╗ ██████╗ ██╗     ██╗   ██╗     █████╗ ██╗
██╔══██╗██║  ██║██╔═══██╗██║     ██║   ██║    ██╔══██╗██║
██████╔╝███████║██║   ██║██║     ██║   ██║    ███████║██║
██╔══██╗██╔══██║██║   ██║██║     ██║   ██║    ██╔══██║██║
██████╔╝██║  ██║╚██████╔╝███████╗╚██████╔╝    ██║  ██║██║
╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝ ╚═════╝     ╚═╝  ╚═╝╚═╝
     Dual-Agent Planner–Executor Security Framework
"""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bholu-ai",
        description=(
            "Bholu AI — demonstrates agentic prompt injection attacks and their mitigation.\n\n"
            "MODES:\n"
            "  secure     (default) Planner → JSON Schema Wall → Executor\n"
            "             Injected instructions are blocked deterministically.\n\n"
            "  vulnerable Single-agent, no schema wall.\n"
            "             Injected instructions execute — shows the attack.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["secure", "vulnerable"],
        default="secure",
        help="Run mode: 'secure' (dual-agent with schema wall) or 'vulnerable' (no wall). Default: secure",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        metavar="N",
        help="Number of emails to fetch from inbox. Default: 5",
    )
    parser.add_argument(
        "--model",
        default="llama3.2",
        help="Ollama model name. Default: llama3.2",
    )
    parser.add_argument(
        "--ollama-host",
        default="http://localhost:11434",
        metavar="URL",
        help="Ollama base URL. Default: http://localhost:11434",
    )
    parser.add_argument(
        "--credentials",
        default="credentials.json",
        metavar="FILE",
        help="Path to Gmail OAuth2 credentials file. Default: credentials.json",
    )
    parser.add_argument(
        "--token",
        default="token.json",
        metavar="FILE",
        help="Path to OAuth2 token cache file. Default: token.json",
    )
    parser.add_argument(
        "--intent",
        default="Summarize my inbox emails",
        metavar="TEXT",
        help='User intent passed to the Planner. Default: "Summarize my inbox emails"',
    )
    return parser


def print_banner(mode: str) -> None:
    console.print(f"[bold cyan]{BANNER}[/bold cyan]")

    if mode == "vulnerable":
        console.print(
            Panel(
                "[bold red]⚠  WARNING: VULNERABLE MODE ACTIVE  ⚠[/bold red]\n\n"
                "The JSON Schema Secure Wall is [bold red]DISABLED[/bold red].\n"
                "Prompt injection attacks will [bold red]SUCCEED[/bold red].\n"
                "This mode exists to demonstrate the attack — all execution is mock only.",
                title="[bold red]SECURITY WARNING[/bold red]",
                border_style="red",
            )
        )
    else:
        console.print(
            Panel(
                "[bold green]✓  SECURE MODE ACTIVE[/bold green]\n\n"
                "The JSON Schema Secure Wall is [bold green]ENABLED[/bold green].\n"
                "Prompt injection attacks will be [bold green]BLOCKED[/bold green] deterministically.",
                title="[bold green]SECURE MODE[/bold green]",
                border_style="green",
            )
        )


def print_log_paths() -> None:
    console.print(f"\n[dim]📄 Execution log : {Path(EXECUTION_LOG).resolve()}[/dim]")
    console.print(f"[dim]📄 Rejected log  : {Path(REJECTED_LOG).resolve()}[/dim]\n")


def print_emails(emails: list) -> None:
    console.print(Panel(
        f"Fetched [bold]{len(emails)}[/bold] email(s) from inbox.",
        title="[bold blue]📬 Gmail Inbox[/bold blue]",
        border_style="blue",
    ))
    for i, email in enumerate(emails, 1):
        console.print(f"  [bold]{i}.[/bold] From: [cyan]{email.sender}[/cyan]")
        console.print(f"     Subject: [white]{email.subject}[/white]")
        body_preview = (email.body[:120].replace("\n", " ") + "...") if len(email.body) > 120 else email.body.replace("\n", " ")
        if body_preview:
            console.print(f"     Preview: [dim]{body_preview}[/dim]")
        console.print()


def print_plan(plan, mode: str) -> None:
    # Check for suspected injection
    injected = [a for a in plan.actions if a.get("type") not in ALLOWED_ACTION_TYPES]

    if injected:
        types = ", ".join(a.get("type", "?") for a in injected)
        console.print(Panel(
            f"[bold yellow]⚠ Suspected prompt injection detected![/bold yellow]\n"
            f"The Planner produced action type(s) NOT in the allowed set: [bold red]{types}[/bold red]\n\n"
            f"{'In SECURE mode, the Executor will BLOCK this plan.' if mode == 'secure' else 'In VULNERABLE mode, the Executor will EXECUTE this plan.'}",
            title="[bold yellow]🔍 Injection Detected in Plan[/bold yellow]",
            border_style="yellow",
        ))

    table = Table(title="Action Plan from Planner Agent", box=box.ROUNDED, border_style="blue")
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", style="bold")
    table.add_column("Details")
    table.add_column("Safe?", justify="center")

    for i, action in enumerate(plan.actions, 1):
        action_type = action.get("type", "unknown")
        is_safe = action_type in ALLOWED_ACTION_TYPES
        details = ", ".join(f"{k}={v}" for k, v in action.items() if k != "type")
        safe_icon = "[green]✓[/green]" if is_safe else "[red]✗ INJECTED[/red]"
        table.add_row(str(i), action_type, details or "-", safe_icon)

    console.print(table)
    console.print()


def print_summary(result: ExecutionResult, emails_count: int, plan=None) -> None:
    result.emails_processed = emails_count
    actions = plan.actions if plan else []

    if result.mode == "secure":
        status = "[bold green]SECURE — Attack Blocked[/bold green]" if result.actions_blocked > 0 else "[bold green]SECURE — Normal Execution[/bold green]"
        border = "green"
    else:
        injected_executed = any(a.get("type") not in ALLOWED_ACTION_TYPES for a in actions)
        status = "[bold red]VULNERABLE — Attack Succeeded[/bold red]" if injected_executed else "[bold yellow]VULNERABLE — Normal Execution (no injection detected)[/bold yellow]"
        border = "red" if injected_executed else "yellow"

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Mode", result.mode.upper())
    table.add_row("Emails processed", str(result.emails_processed))
    table.add_row("Actions planned", str(result.actions_planned))
    table.add_row("Actions executed", str(result.actions_executed))
    table.add_row("Actions blocked", str(result.actions_blocked))
    if result.blocked_reason:
        table.add_row("Block reason", result.blocked_reason[:80])

    console.print(Panel(
        table,
        title=f"[bold]📊 Run Summary — {status}[/bold]",
        border_style=border,
    ))

    if result.mode == "secure" and result.actions_blocked > 0:
        console.print(
            "\n[bold green]✓ The Dual-Agent framework successfully neutralized the attack.[/bold green]\n"
            "[green]  The Planner was hijacked, but the Executor's schema wall stopped execution.[/green]\n"
        )
    elif result.mode == "vulnerable":
        injected = any(a.get("type") not in ALLOWED_ACTION_TYPES for a in actions)
        if injected:
            console.print(
                "\n[bold red]✗ The single-agent system was hijacked.[/bold red]\n"
                "[red]  Without the schema wall, the injected instructions executed.[/red]\n"
                "[dim]  (All execution was mock — no real actions were taken)[/dim]\n"
            )
        else:
            console.print(
                "\n[bold yellow]ℹ No injection detected in this run.[/bold yellow]\n"
                "[dim]  Send yourself the poisoned email from samples/poisoned_email.txt to trigger the attack.[/dim]\n"
            )


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    # Change working directory to bholu-ai/ so relative paths work
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print_banner(args.mode)
    print_log_paths()

    # --- Step 1: Authenticate and fetch emails ---
    console.print("[bold blue]Step 1/3 — Connecting to Gmail...[/bold blue]")
    gmail = GmailClient(
        credentials_path=args.credentials,
        token_path=args.token,
    )
    gmail.authenticate()

    console.print(f"[bold blue]Step 2/3 — Fetching {args.count} email(s) from inbox...[/bold blue]")
    emails = gmail.fetch_inbox(count=args.count)

    if not emails:
        console.print("[yellow]No emails found in inbox.[/yellow]")
        return

    print_emails(emails)

    # --- Step 2: Planner Agent reasons and produces a JSON plan ---
    console.print(f"[bold blue]Step 3/3 — Planner Agent reasoning (model: {args.model})...[/bold blue]")
    console.print("[dim]  Sending emails to local LLM. This may take 10–30 seconds...[/dim]\n")

    ollama = OllamaClient(
        host=args.ollama_host,
        model=args.model,
    )
    planner = PlannerAgent(ollama_client=ollama)
    plan = planner.plan(emails=emails, user_intent=args.intent)

    console.print("[bold]Planner Agent produced a plan:[/bold]")
    print_plan(plan, args.mode)

    # --- Step 3: Executor Agent validates (secure) or executes (vulnerable) ---
    if args.mode == "secure":
        console.print("[bold green]🔒 Secure Wall — validating plan against JSON Schema...[/bold green]\n")
    else:
        console.print("[bold red]⚡ Vulnerable mode — skipping schema validation...[/bold red]\n")

    executor = ExecutorAgent(schema_path=SCHEMA_PATH, mode=args.mode)
    result = executor.execute(plan=plan, console=console)

    # --- Final summary ---
    print_summary(result, len(emails), plan)


if __name__ == "__main__":
    main()
