"""Outcome enum and step results for ship-pr state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Outcome(Enum):
    OK = "OK"
    NEEDS_USER_INPUT = "NEEDS_USER_INPUT"
    STALLED = "STALLED"
    TRANSIENT = "TRANSIENT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class StepResult:
    outcome: Outcome
    detail: str = ""
    payload: Any | None = None
    ledger_ready: bool = False
    ledger_site: str = ""
    ledger_trigger: str = ""
    ledger_step: str = ""
    ledger_phase: str = ""
    ledger_dispatcher: str = ""
    ledger_exit_code: int | None = None
    ledger_failure_detail_log: str = ""
