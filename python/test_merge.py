"""Tests for merge.py."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

import config
import git as git_module
import merge as merge_module
import run_logs
from proc import CommandResult
from pathlib import Path

from run_context import RunContext


def _empty_str_lists() -> list[list[str]]:
    return []


def _empty_command_results() -> list[CommandResult]:
    return []


@dataclass
class RecordingRunner:
    calls: list[list[str]] = field(default_factory=_empty_str_lists)
    responses: list[CommandResult] = field(default_factory=_empty_command_results)
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
            return CommandResult(tuple(argv), 0, "", "", 0.01)
        result = self.responses[self._index]
        self._index += 1
        return result


def _ctx(**kwargs: object) -> RunContext:
    base = RunContext(
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
        pr_number=1,
    )
    return base.with_(**kwargs)


def test_redact_merge_diagnostic_truncates() -> None:
    text = "x" * 1000
    out = merge_module.redact_merge_diagnostic(text)
    assert len(out) <= config.MERGE_DIAGNOSTIC_MAX_LEN


def test_merge_results_table_is_exhaustive() -> None:
    assert len(config.MERGE_RESULTS) == 8
    assert "already_merged" not in config.MERGE_RESULTS


def test_merge_skip_modes_have_dedicated_errors() -> None:
    runner = RecordingRunner()
    cases = (
        (_ctx(merge=False), config.MERGE_SKIP_NOT_REQUESTED),
        (_ctx(draft=True), config.MERGE_SKIP_DRAFT),
        (_ctx(forked=True), config.MERGE_SKIP_FORKED),
        (_ctx(repo_unavailable=True), config.MERGE_SKIP_REPO_UNAVAILABLE),
    )
    for ctx, expected in cases:
        out = merge_module.merge_pr(runner, ctx)
        assert out.result == config.MERGE_RESULT_ERROR
        assert out.error == expected


def test_merge_continues_when_flush_skips_missing_state(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"BEHIND","headRefOid":"abc"}',
                "",
                0.01,
            ),
        ],
    )
    ctx = _ctx(
        tmpdir=str(tmp_path),
        state_file=None,
        pr_number=1,
    )
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_MAIN_ADVANCED
    assert "flush_logs_pre skipped" not in out.error


def test_merge_noop_when_pr_already_merged(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("MERGE_RESULT=merged\nRUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"MERGED","headRefName":"feat"}',
                "",
                0.01,
            ),
        ],
    )
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state), pr_number=1)
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_MERGED
    assert out.error == ""
    assert not any(call[1:3] == ("pr", "merge") for call in runner.calls)


def test_update_manifest_ignores_unknown_keys(tmp_path: Path) -> None:
    ctx = _ctx(tmpdir=str(tmp_path), run_id="run-abc")
    _ = run_logs.init_run(ctx)
    manifest = run_logs.update_manifest(ctx, version="9", updated_at="now")
    assert manifest.version == "9"
    assert manifest.updated_at == "now"
    assert "version" not in manifest.steps_ran


def test_flush_recoverable_rejects_mixed_commit_subjects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()

    def fake_log_subjects(
        *_args: object,
        **_kwargs: object,
    ) -> git_module.LogSubjects:
        return git_module.LogSubjects(
            (
                f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}run",
                "Fix unrelated bug",
            ),
        )

    monkeypatch.setattr(git_module, "try_log_subjects", fake_log_subjects)
    assert not merge_module._flush_recoverable(runner, "aaaa1111", cwd=None)  # pyright: ignore[reportPrivateUsage]


def test_flush_recoverable_returns_false_when_log_fails() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "log"), 1, "", "bad oid", 0.01),
        ],
    )
    assert not merge_module._flush_recoverable(runner, "deadbeef", cwd=None)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "literal",
    sorted(config.MERGE_RESULTS),
)
def test_merge_result_literals_are_stable(literal: str) -> None:
    assert literal in config.MERGE_RESULTS
