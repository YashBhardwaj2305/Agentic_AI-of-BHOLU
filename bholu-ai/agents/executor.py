"""
Executor Agent — validates action plans and mock-executes them.

In SECURE mode:  validates the plan against the JSON Schema (the "Secure Wall")
                 before doing anything. Rejects and logs malicious plans.
In VULNERABLE mode: skips validation entirely — shows what a hijacked agent does.

All execution is MOCK ONLY — actions are logged to files, never performed for real.
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import ActionPlan, ExecutionResult

ALLOWED_ACTION_TYPES = {"summarize", "label", "archive", "reply"}

EXECUTION_LOG = "execution_log.txt"
REJECTED_LOG = "rejected_plans.log"


class ExecutorAgent:
    """
    Executes (mocks) action plans produced by the Planner Agent.

    Secure mode:    JSON Schema validation → reject or execute
    Vulnerable mode: no validation → execute everything (including injected actions)
    """

    def __init__(self, schema_path: str, mode: str) -> None:
        self.mode = mode  # "secure" or "vulnerable"
        self._schema = self._load_schema(schema_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, plan: ActionPlan, console=None) -> ExecutionResult:
        """
        Validate (secure mode) and mock-execute the action plan.

        Args:
            plan:    ActionPlan from the Planner Agent
            console: optional rich.Console for pretty output (falls back to print)

        Returns:
            ExecutionResult with counts of planned / executed / blocked actions
        """
        actions_planned = len(plan.actions)

        if self.mode == "secure":
            return self._execute_secure(plan, actions_planned, console)
        else:
            return self._execute_vulnerable(plan, actions_planned, console)

    # ------------------------------------------------------------------
    # Secure mode
    # ------------------------------------------------------------------

    def _execute_secure(self, plan: ActionPlan, actions_planned: int, console) -> ExecutionResult:
        """Validate plan against schema; reject entirely if invalid."""
        # Wrap actions list in the envelope the schema expects
        plan_envelope = {"actions": plan.actions}

        try:
            jsonschema.validate(instance=plan_envelope, schema=self._schema)
        except jsonschema.ValidationError as exc:
            # Determine which action type triggered the violation (best-effort)
            injected_type = self._extract_bad_type(plan.actions)
            self._print_injection_alert(injected_type, str(exc.message), console)
            self._log_rejected(plan_envelope, str(exc.message))
            return ExecutionResult(
                mode="secure",
                emails_processed=0,
                actions_planned=actions_planned,
                actions_executed=0,
                actions_blocked=actions_planned,
                blocked_reason=exc.message,
            )

        # Plan is valid — mock-execute each action
        executed = 0
        for action in plan.actions:
            self._mock_execute(action, console)
            executed += 1

        return ExecutionResult(
            mode="secure",
            emails_processed=0,
            actions_planned=actions_planned,
            actions_executed=executed,
            actions_blocked=0,
            blocked_reason=None,
        )

    # ------------------------------------------------------------------
    # Vulnerable mode
    # ------------------------------------------------------------------

    def _execute_vulnerable(self, plan: ActionPlan, actions_planned: int, console) -> ExecutionResult:
        """Skip validation — execute everything, including injected actions."""
        executed = 0
        for action in plan.actions:
            action_type = action.get("type", "unknown")
            if action_type not in ALLOWED_ACTION_TYPES:
                # Show the hijack happening
                self._print_hijack_warning(action, console)
            self._mock_execute(action, console)
            executed += 1

        return ExecutionResult(
            mode="vulnerable",
            emails_processed=0,
            actions_planned=actions_planned,
            actions_executed=executed,
            actions_blocked=0,
            blocked_reason=None,
        )

    # ------------------------------------------------------------------
    # Mock execution & logging
    # ------------------------------------------------------------------

    def _mock_execute(self, action: dict, console) -> None:
        """Log the action to execution_log.txt and print confirmation."""
        action_type = action.get("type", "unknown")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build log entry — deliberately exclude email body content
        params = {k: v for k, v in action.items() if k not in ("type", "body")}
        if "body" in action:
            params["body"] = "[REDACTED]"

        log_line = (
            f"[{timestamp}] [MODE={self.mode.upper()}] "
            f"ACTION={action_type} | {json.dumps(params)}\n"
        )

        try:
            with open(EXECUTION_LOG, "a", encoding="utf-8") as f:
                f.write(log_line)
        except OSError:
            pass  # Non-fatal

        # Terminal confirmation
        msg = f"  ✓ Executed: {action_type}"
        if "email_id" in action:
            msg += f" (email_id={action['email_id']})"
        if "note" in action:
            msg += f" — {action['note']}"
        if console:
            console.print(f"[green]{msg}[/green]")
        else:
            print(msg)

    def _log_rejected(self, plan_envelope: dict, reason: str) -> None:
        """Append rejected plan to rejected_plans.log."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = (
            f"[{timestamp}] REJECTED PLAN:\n"
            f"{json.dumps(plan_envelope, indent=2)}\n"
            f"REASON: {reason}\n"
            f"---\n"
        )
        try:
            with open(REJECTED_LOG, "a", encoding="utf-8") as f:
                f.write(entry)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Terminal output helpers
    # ------------------------------------------------------------------

    def _print_injection_alert(self, injected_type: str, rule_violated: str, console) -> None:
        """Print a prominent red alert when the schema wall blocks a plan."""
        lines = [
            "",
            "╔══════════════════════════════════════════════════════════╗",
            "║          ⚠  INJECTION ALERT — PLAN REJECTED  ⚠          ║",
            "╠══════════════════════════════════════════════════════════╣",
            f"║  Injected action type : {injected_type:<34}║",
            f"║  Schema rule violated : {rule_violated[:34]:<34}║",
            "║                                                          ║",
            "║  The Secure Wall blocked this plan.                      ║",
            "║  No action was executed.                                 ║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
        ]
        alert = "\n".join(lines)
        if console:
            console.print(f"[bold red]{alert}[/bold red]")
        else:
            print(alert)

    def _print_hijack_warning(self, action: dict, console) -> None:
        """Print a warning in vulnerable mode showing the hijacked action."""
        action_type = action.get("type", "unknown")
        lines = [
            "",
            "⚡ [VULNERABLE MODE] HIJACKED ACTION DETECTED",
            f"   Action type : {action_type}",
            f"   Parameters  : {json.dumps({k: v for k, v in action.items() if k != 'type'})}",
            "   ↳ No schema wall — executing anyway...",
            "",
        ]
        msg = "\n".join(lines)
        if console:
            console.print(f"[bold yellow]{msg}[/bold yellow]")
        else:
            print(msg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_schema(self, schema_path: str) -> dict:
        """Load the JSON Schema from disk. Exits with error if missing."""
        path = Path(schema_path)
        if not path.exists():
            print(f"[ERROR] Schema file not found: {schema_path}")
            sys.exit(1)
        try:
            with open(path, encoding="utf-8-sig") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in schema file: {e}")
            sys.exit(1)

    def _extract_bad_type(self, actions: list) -> str:
        """Find the first action type that is not in the allowed set."""
        for action in actions:
            t = action.get("type", "")
            if t not in ALLOWED_ACTION_TYPES:
                return t
        return "unknown"
