"""Tests for merge.py."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

import config
import gh
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


def _mock_checks_pass(*_a: object, **_k: object) -> bool:
    return True


def _mock_checks_fail(*_a: object, **_k: object) -> bool:
    return False


def _mock_rev_abc(*_a: object, **_k: object) -> str:
    return "abc"


def _mock_version_gate_none(*_a: object, **_k: object) -> None:
    return None


def _mock_refresh_skip_ok(*_a: object, **_k: object) -> run_logs.RefreshSkip:
    return run_logs.RefreshSkip(skipped=False, reason="")


def _mock_true(*_a: object, **_k: object) -> bool:
    return True


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


def test_merge_closed_unmerged_is_error(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"CLOSED","headRefName":"feat","mergedAt":null}',
                "",
                0.01,
            ),
        ],
    )
    ctx = _ctx(tmpdir=str(tmp_path), pr_number=1)
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "not merged" in out.error


def test_merge_flush_pre_post_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    order: list[str] = []

    def fake_pre(*_a: object, **_k: object) -> run_logs.RefreshSkip:
        order.append("pre")
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_post(*_a: object, **_k: object) -> run_logs.RefreshSkip:
        order.append("post")
        return run_logs.RefreshSkip(skipped=False, reason="")

    def fake_merge(*_a: object, **_k: object) -> merge_module.MergeResult:
        return merge_module.MergeResult(result=config.MERGE_RESULT_MERGED, error="")

    def fake_refresh(*_a: object, **_k: object) -> gh.MergeState:
        return gh.MergeState("CLEAN", "abc")

    def fake_checks(*_a: object, **_k: object) -> bool:
        return True

    def fake_head(*_a: object, **_k: object) -> gh.MergeState:
        return gh.MergeState("CLEAN", "abc")

    def fake_version(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(run_logs, "flush_logs_pre", fake_pre)
    monkeypatch.setattr(run_logs, "flush_logs_post", fake_post)
    monkeypatch.setattr(merge_module, "_attempt_merge", fake_merge)
    monkeypatch.setattr(merge_module, "_refresh_pr_info", fake_refresh)
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", fake_checks)
    monkeypatch.setattr(merge_module, "_ensure_head_matches_pr", fake_head)
    monkeypatch.setattr(merge_module, "_version_race_gate", fake_version)

    open_pr = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
        ],
    )
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(tmp_path / "state.env"))
    _ = (tmp_path / "state.env").write_text("RUN_ID=run-abc\n", encoding="utf-8")
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_MERGED
    assert order == ["pre", "post"]


def test_flush_recoverable_rejects_more_than_five_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    subjects = tuple(
        f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}run-{index}"
        for index in range(config.FLUSH_RECOVERY_MAX_COMMITS + 1)
    )

    def fake_log(*_a: object, **_k: object) -> git_module.LogSubjects:
        return git_module.LogSubjects(subjects)

    monkeypatch.setattr(git_module, "try_log_subjects", fake_log)
    assert not merge_module._flush_recoverable(runner, "aaaa1111", cwd=None)  # pyright: ignore[reportPrivateUsage]


def _open_pr_responses(
    merge_state: str = "CLEAN",
    head_oid: str = "abc",
) -> list[CommandResult]:
    open_pr = (
        '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
    )
    merge_json = (
        f'{{"mergeStateStatus":"{merge_state}","headRefOid":"{head_oid}"}}'
    )
    return [
        CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
        CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
        CommandResult(("gh", "pr", "view", "1"), 0, merge_json, "", 0.01),
    ]


def test_merge_pr_emits_admin_merged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            *_open_pr_responses(),
            CommandResult(("gh", "pr", "merge"), 0, "", "", 0.01),
        ],
    )
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED


def test_merge_pr_emits_merged_via_plain_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            *_open_pr_responses(),
            CommandResult(("gh", "pr", "merge"), 1, "", "admin denied", 0.01),
            CommandResult(("gh", "pr", "merge"), 0, "", "", 0.01),
        ],
    )
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_MERGED


def test_merge_pr_emits_policy_denied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            *_open_pr_responses(),
            CommandResult(("gh", "pr", "merge"), 1, "", "denied", 0.01),
        ],
    )
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(
        tmpdir=str(tmp_path),
        state_file=str(state),
        no_admin_fallback=True,
    )
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_POLICY_DENIED


def test_merge_pr_emits_admin_failed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            *_open_pr_responses(),
            CommandResult(("gh", "pr", "merge"), 1, "", "admin fail", 0.01),
            CommandResult(("gh", "pr", "merge"), 1, "", "plain fail", 0.01),
        ],
    )
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_FAILED


def test_merge_pr_emits_ci_not_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(responses=_open_pr_responses())
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_fail)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_CI_NOT_READY


def test_merge_pr_emits_version_already_published(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(responses=_open_pr_responses())
    def fake_version_race(*_a: object, **_k: object) -> merge_module.MergeResult:
        return merge_module.MergeResult(
            result=config.MERGE_RESULT_VERSION_ALREADY_PUBLISHED,
            error="race",
        )

    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(merge_module, "_version_race_gate", fake_version_race)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_VERSION_ALREADY_PUBLISHED


def test_merge_noop_preserves_admin_merged_from_state(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text(
        "MERGE_RESULT=admin_merged\nRUN_ID=run-abc\n",
        encoding="utf-8",
    )
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
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED


def test_merge_noop_runs_post_flush_on_first_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    flushed: list[str] = []

    def fake_post(*_a: object, **kwargs: object) -> run_logs.RefreshSkip:
        flushed.append(str(kwargs.get("merge_result", "")))
        return run_logs.RefreshSkip(skipped=False, reason="")

    monkeypatch.setattr(run_logs, "flush_logs_post", fake_post)
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
    assert flushed == [config.MERGE_RESULT_MERGED]


def test_merge_pr_view_failure_is_error(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 1, "", "network down", 0.01),
        ],
    )
    ctx = _ctx(tmpdir=str(tmp_path), pr_number=1)
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "pr view failed" in out.error


def test_ensure_head_empty_local_head_is_error() -> None:
    runner = RecordingRunner()
    state = gh.MergeState("CLEAN", "abc")
    ctx = _ctx()
    out = merge_module._ensure_head_matches_pr(  # pyright: ignore[reportPrivateUsage]
        runner,
        ctx,
        state,
        sleeper=lambda _s: None,
        cwd=None,
    )
    assert isinstance(out, merge_module.MergeResult)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "local HEAD" in out.error


def test_merge_continues_when_pre_flush_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
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
    def fake_pre_skipped(*_a: object, **_k: object) -> run_logs.RefreshSkip:
        return run_logs.RefreshSkip(skipped=True, reason="commit-failed")

    monkeypatch.setattr(run_logs, "flush_logs_pre", fake_pre_skipped)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state), pr_number=1)
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_MAIN_ADVANCED


def test_version_race_gate_version_already_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "fetch"), 0, "", "", 0.01),
            CommandResult(("git", "show"), 0, '{"version": "1.2.3"}', "", 0.01),
            CommandResult(("git", "fetch"), 0, "", "", 0.01),
            CommandResult(("git", "show"), 0, '{"version": "1.2.3"}', "", 0.01),
        ],
    )
    def fake_log_bump(*_a: object, **_k: object) -> git_module.LogSubjects:
        return git_module.LogSubjects(("Bump version to 1.2.3",))

    monkeypatch.setattr(git_module, "try_log_subjects", fake_log_bump)
    monkeypatch.setattr(git_module, "is_ancestor", _mock_true)
    out = merge_module._version_race_gate(runner, cwd=None)  # pyright: ignore[reportPrivateUsage]
    assert out is not None
    assert out.result == config.MERGE_RESULT_VERSION_ALREADY_PUBLISHED


def test_version_race_gate_no_bump_commits_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("git", "fetch"), 0, "", "", 0.01)],
    )
    def fake_log_feat(*_a: object, **_k: object) -> git_module.LogSubjects:
        return git_module.LogSubjects(("feat: add widget",))

    monkeypatch.setattr(git_module, "try_log_subjects", fake_log_feat)
    out = merge_module._version_race_gate(runner, cwd=None)  # pyright: ignore[reportPrivateUsage]
    assert out is None


def test_merge_flush_recovery_success_emits_admin_merged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    open_pr = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}',
                "",
                0.01,
            ),
            CommandResult(("gh", "pr", "merge"), 0, "", "", 0.01),
        ],
    )
    recovery = git_module.ForcePushResult(pushed=True, status="ok", branch="feat")
    head_oids = iter(("cccc3333", "aaaa1111"))

    def fake_recoverable(*_a: object, **_k: object) -> bool:
        return True

    def fake_rev_parse(*_a: object, **_k: object) -> str:
        return next(head_oids, "aaaa1111")

    def fake_force_push(*_a: object, **_k: object) -> git_module.ForcePushResult:
        return recovery

    monkeypatch.setattr(merge_module, "_flush_recoverable", fake_recoverable)
    monkeypatch.setattr(git_module, "try_rev_parse", fake_rev_parse)
    monkeypatch.setattr(git_module, "force_push_recovery", fake_force_push)
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED


def test_merge_post_recovery_ci_pending(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    open_pr = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}',
                "",
                0.01,
            ),
        ],
    )
    recovery = git_module.ForcePushResult(pushed=True, status="ok", branch="feat")
    checks_calls = {"count": 0}
    head_oids = iter(("cccc3333", "aaaa1111"))

    def fake_checks(*_a: object, **_k: object) -> bool:
        checks_calls["count"] += 1
        return checks_calls["count"] == 1

    def fake_rev_parse_ci(*_a: object, **_k: object) -> str:
        return next(head_oids, "aaaa1111")

    def fake_force_push_ci(*_a: object, **_k: object) -> git_module.ForcePushResult:
        return recovery

    monkeypatch.setattr(merge_module, "_flush_recoverable", _mock_true)
    monkeypatch.setattr(git_module, "try_rev_parse", fake_rev_parse_ci)
    monkeypatch.setattr(git_module, "force_push_recovery", fake_force_push_ci)
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", fake_checks)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_CI_NOT_READY
    assert "after force-push recovery" in out.error


def test_flush_recoverable_rejects_non_larch_log_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "diff", "--name-only"),
                0,
                "README.md\n",
                "",
                0.01,
            ),
        ],
    )

    def fake_log(*_a: object, **_k: object) -> git_module.LogSubjects:
        return git_module.LogSubjects((f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}run",))

    monkeypatch.setattr(git_module, "try_log_subjects", fake_log)
    assert not merge_module._flush_recoverable(runner, "aaaa1111", cwd=None)  # pyright: ignore[reportPrivateUsage]


def test_flush_recoverable_requires_pr_head_ancestor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()

    def fake_log(*_a: object, **_k: object) -> git_module.LogSubjects:
        return git_module.LogSubjects((f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}run",))

    def fake_diff(*_a: object, **_k: object) -> CommandResult:
        return CommandResult(("git", "diff"), 0, "larch-logs/implement/run/a\n", "", 0.01)

    def fake_is_ancestor(*_a: object, **_k: object) -> bool:
        return False

    monkeypatch.setattr(git_module, "try_log_subjects", fake_log)
    monkeypatch.setattr(git_module, "diff_name_only", fake_diff)
    monkeypatch.setattr(git_module, "is_ancestor", fake_is_ancestor)
    assert not merge_module._flush_recoverable(runner, "aaaa1111", cwd=None)  # pyright: ignore[reportPrivateUsage]


def test_merge_retries_unknown_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    open_pr = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"UNKNOWN","headRefOid":"abc"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"UNKNOWN","headRefOid":"abc"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"abc"}',
                "",
                0.01,
            ),
            CommandResult(("gh", "pr", "merge"), 0, "", "", 0.01),
        ],
    )
    sleeps: list[float] = []
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx, sleeper=sleeps.append)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED
    assert sleeps == [5.0, 5.0]


def test_merge_unknown_exhaustion_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    open_pr = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            *[
                CommandResult(
                    ("gh", "pr", "view", "1"),
                    0,
                    '{"mergeStateStatus":"UNKNOWN","headRefOid":"abc"}',
                    "",
                    0.01,
                )
                for _ in range(config.MERGE_PR_INITIAL_UNKNOWN_RETRIES + 1)
            ],
        ],
    )
    sleeps: list[float] = []
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner, ctx, sleeper=sleeps.append)
    assert out.result == config.MERGE_RESULT_ERROR
    assert len(sleeps) == config.MERGE_PR_INITIAL_UNKNOWN_RETRIES


def test_post_flush_redaction_skip_is_merge_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")

    def fake_post(*_a: object, **_k: object) -> run_logs.RefreshSkip:
        return run_logs.RefreshSkip(skipped=True, reason="redaction-failed")

    monkeypatch.setattr(run_logs, "flush_logs_post", fake_post)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module._post_flush(  # pyright: ignore[reportPrivateUsage]
        RecordingRunner(),
        ctx,
        config.MERGE_RESULT_MERGED,
    )
    assert out is not None
    assert out.result == config.MERGE_RESULT_ERROR


def test_merge_noop_defaults_to_merged_when_state_unknown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state), pr_number=1)
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_MERGED
