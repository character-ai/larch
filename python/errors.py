"""Exception hierarchy for ship-pr Python."""

from __future__ import annotations


class ShipError(Exception):
    """Base error for ship-pr operations."""


class TransientNetworkError(ShipError):
    """Retryable network or infrastructure failure."""

    def __init__(self, message: str, *, result: object | None = None) -> None:
        super().__init__(message)
        self.result = result


class NeedsUserInput(ShipError):
    """Operator input required before continuing."""


class Stalled(ShipError):
    """Run stalled waiting on external preconditions."""
