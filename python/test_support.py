"""Shared pytest helpers for Python ship-pr modules."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from larch.agents import collect_results
from larch.core.proc import CommandResult
from larch.core.run_context import RunContext


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


def make_zero_findings_plan_review_fake_cli(
    design: Path, reviewer_file: Path
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Build the shared ``_run_cli`` fake for the #5032 zero-findings degraded-panel path.

    ``test_plan_review`` and ``test_plan_review_round`` both stub the same
    panel-dispatch / collect-results / aggregate / voter-dispatch / tally sequence
    for a single OK Cursor reviewer that parses to zero findings. Extracting the
    identical block here keeps it from tripping the R0801 duplicate-code gate.
    """

    def fake_run_cli(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        del env
        if argv[:2] == ["plan-review", "panel-dispatch"]:
            paths_file = design / "plan-review-panel-paths.txt"
            _ = (design / "plan-review-slots.ndjson").write_text(
                '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
                + str(reviewer_file)
                + '","prompt_file":"'
                + str(design / "cursor-plan-arch.prompt")
                + '"}\n',
                encoding="utf-8",
            )
            _ = paths_file.write_text(str(reviewer_file) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, f"PANEL_PRUNED_EMPTY=false\nPANEL_PATHS_FILE={paths_file}\n", "")
        if argv[:2] == ["agent", "collect-results"]:
            record = collect_results.CollectorRecord(
                reviewer_file=str(reviewer_file),
                tool="cursor",
                status="OK",
                exit_code="0",
            )
            blocks = ["\n".join(record.fields())]
            return subprocess.CompletedProcess(argv, 0, "\n\n".join(blocks) + "\n", "")
        if argv[:2] == ["review", "aggregate-findings"]:
            return subprocess.CompletedProcess(argv, 0, "REASON=insufficient-input\nAGGREGATED=false\n", "")
        if argv[:2] == ["plan-review", "voter-dispatch"]:
            return subprocess.CompletedProcess(argv, 0, "DISPATCH_OK=false\nDEGRADED_PANEL=1\n", "")
        if argv[:2] == ["plan-review", "tally"]:
            return subprocess.CompletedProcess(argv, 0, "TALLY_PLAN_REVIEW_STATUS=ok\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    return fake_run_cli
