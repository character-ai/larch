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


@dataclass(frozen=True)
class StepResult:
    outcome: Outcome
    detail: str = ""
    payload: Any | None = None
