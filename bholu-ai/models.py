from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmailMessage:
    sender: str
    subject: str
    body: str  # empty string if no plain-text part


@dataclass
class ActionPlan:
    actions: list  # list of action dicts from LLM
    raw_response: str  # original LLM text


@dataclass
class ExecutionResult:
    mode: str
    emails_processed: int
    actions_planned: int
    actions_executed: int
    actions_blocked: int
    blocked_reason: Optional[str] = None
