"""Shared pytest helpers for Python ship-pr modules."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from proc import CommandResult
from run_context import RunContext


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


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "python" / "cli.py"


def run_cli(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run python/cli.py in a subprocess with CLAUDE_PLUGIN_ROOT set to the repo root."""
    merged = os.environ.copy()
    merged["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


# Shared RunContext defaults for ship-pr unit tests; override fields via
# make_run_context(). The frozen dataclass is safe to share as a singleton.
_DEFAULT_RUN_CONTEXT = RunContext(
    branch="feat",
    issue="1",
    repo="o/r",
    run_id="run-1",
    tmpdir="/tmp/impl",
    merge=True,
    draft=False,
    forked=False,
    manifest_path="/tmp/impl/manifest.json",
    tool_label="cursor",
    no_admin_fallback=False,
    repo_unavailable=False,
)


def make_run_context(**overrides: object) -> RunContext:
    """Build a RunContext from shared test defaults, applying field overrides."""
    return _DEFAULT_RUN_CONTEXT.with_(**overrides)


# Common `gh pr view 1` JSON payloads for merge/ship unit tests.
PR_VIEW_OPEN_JSON = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
PR_VIEW_BEHIND_JSON = '{"mergeStateStatus":"BEHIND","headRefOid":"abc"}'


def gh_result(argv: tuple[str, ...], stdout: str = "") -> CommandResult:
    """Stubbed gh CommandResult: exit 0, empty stderr, 0.01s duration."""
    return CommandResult(argv, 0, stdout, "", 0.01)


def gh_pr_view(stdout: str) -> CommandResult:
    """Stubbed `gh pr view 1` CommandResult carrying the given JSON stdout."""
    return gh_result(("gh", "pr", "view", "1"), stdout)


def merge_admin_responses(*, double_open_view: bool = False) -> list[CommandResult]:
    """Build the gh response queue for a BEHIND PR that merge_pr() admin-merges.

    With double_open_view, two OPEN `gh pr view` results precede the BEHIND
    view, matching tests that re-view the PR before merging.
    """
    opens = [gh_pr_view(PR_VIEW_OPEN_JSON) for _ in range(2 if double_open_view else 1)]
    return [*opens, gh_pr_view(PR_VIEW_BEHIND_JSON), gh_result(("gh", "pr", "merge"))]
