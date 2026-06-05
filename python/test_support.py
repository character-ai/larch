"""Shared pytest helpers for Python ship-pr modules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from proc import CommandResult


def _empty_calls() -> list[list[str]]:
    return []


def _empty_results() -> list[CommandResult]:
    return []


@dataclass
class RecordingRunner:
    """Indexed response-queue runner for unit tests."""

    calls: list[list[str]] = field(default_factory=_empty_calls)
    responses: list[CommandResult] = field(default_factory=_empty_results)
    strict: bool = False
    default: CommandResult | None = None
    _index: int = 0

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        self.calls.append(list(argv))
        if self._index >= len(self.responses):
            if self.strict:
                msg = f"no response for call {argv}"
                raise AssertionError(msg)
            return self.default or CommandResult(tuple(argv), 0, "", "", 0.01)
        result = self.responses[self._index]
        self._index += 1
        return result
