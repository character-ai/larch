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


class PrePushConflictHandoff(Stalled):
    """Pre-push rebase conflicts need the legacy conflict-resolution handoff."""

    def __init__(
        self,
        *,
        conflict_files: tuple[str, ...],
        resume_phase: str,
        caller_kind: str,
        message: str = "fixer waterfall could not resolve conflicts",
    ) -> None:
        super().__init__(message)
        self.conflict_files = conflict_files
        self.resume_phase = resume_phase
        self.caller_kind = caller_kind

    @property
    def conflict_csv(self) -> str:
        """Comma-separated conflict list matching the bash ``CONFLICT_FILES`` shape."""
        return ",".join(self.conflict_files)
