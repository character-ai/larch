"""Exception hierarchy for ship-pr Python."""

from __future__ import annotations


class ShipError(Exception):
    """Base error for ship-pr operations."""


class TransientNetworkError(ShipError):
    """Retryable network or infrastructure failure."""


class NeedsUserInput(ShipError):
    """Operator input required before continuing."""


class Stalled(ShipError):
    """Run stalled waiting on external preconditions."""
