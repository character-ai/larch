# pyright: reportPrivateUsage=false, reportUnknownLambdaType=false, reportUnknownArgumentType=false
"""Tests for merge.py."""

from __future__ import annotations


import pytest

from larch.core import config
from larch.git import gh
from larch.git import git as git_module
from larch.git import merge as merge_module
from larch.report import run_logs
from larch.core.proc import CommandResult
from pathlib import Path

from larch.core.run_context import RunContext


from test_support import RecordingRunner, make_run_context, merge_admin_responses


def _ctx(**kwargs: object) -> RunContext:
    base = make_run_context(pr_number=1)
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


def _mock_ensure_head_behind(*_a: object, **_k: object) -> gh.MergeState:
    return gh.MergeState("BEHIND", "abc")


def _mock_true(*_a: object, **_k: object) -> bool:
    return True


def _mock_rev_new(*_a: object, **_k: object) -> str:
    return "new"


def _mock_force_push_ok(*_a: object, **_k: object) -> git_module.ForcePushResult:
    return git_module.ForcePushResult(pushed=True, status="ok", branch="feat")


def test_redact_merge_diagnostic_truncates() -> None:
    text = "x" * 1000
    out = merge_module.redact_merge_diagnostic(text)
    assert len(out) <= config.MERGE_DIAGNOSTIC_MAX_LEN


def test_merge_results_table_is_exhaustive() -> None:
    assert len(config.MERGE_RESULTS) == 9
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
        out = merge_module.merge_pr(runner=runner, ctx=ctx)
        assert out.result == config.MERGE_RESULT_ERROR
        assert out.error == expected


def test_merge_continues_when_flush_skips_missing_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(responses=merge_admin_responses())
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(merge_module, "_ensure_head_matches_pr", _mock_ensure_head_behind)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(
        tmpdir=str(tmp_path),
        state_file=None,
        pr_number=1,
    )
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED


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
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
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
    assert not merge_module._flush_recoverable(runner=runner, pr_head_oid="aaaa1111", cwd=None)  # pyright: ignore[reportPrivateUsage]


def test_flush_recoverable_returns_false_when_log_fails() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "log"), 1, "", "bad oid", 0.01),
        ],
    )
    assert not merge_module._flush_recoverable(runner=runner, pr_head_oid="deadbeef", cwd=None)  # pyright: ignore[reportPrivateUsage]


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
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "not merged" in out.error


def test_merge_skips_pre_flush_and_runs_post_flush(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
        ],
    )
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(tmp_path / "state.env"))
    _ = (tmp_path / "state.env").write_text("RUN_ID=run-abc\n", encoding="utf-8")
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_MERGED
    assert order == ["post"]


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
    assert not merge_module._flush_recoverable(runner=runner, pr_head_oid="aaaa1111", cwd=None)  # pyright: ignore[reportPrivateUsage]


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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(
        tmpdir=str(tmp_path),
        state_file=str(state),
        no_admin_fallback=True,
    )
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_FAILED


def test_merge_pr_emits_ci_not_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(responses=_open_pr_responses())
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_fail)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_CI_NOT_READY


def test_merge_pr_ci_not_ready_even_when_review_required(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(responses=_open_pr_responses())
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_fail)
    monkeypatch.setattr(
        merge_module.gh,
        "pr_review_decision",
        lambda *_a, **_k: "REVIEW_REQUIRED",
    )
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_CI_NOT_READY
    assert not any(call[1:3] == ("pr", "merge") for call in runner.calls)


def test_merge_pr_review_required_no_admin_fallback(
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
    monkeypatch.setattr(
        merge_module.gh,
        "pr_review_decision",
        lambda *_a, **_k: "REVIEW_REQUIRED",
    )
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(
        tmpdir=str(tmp_path),
        state_file=str(state),
        no_admin_fallback=True,
    )
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_REVIEW_REQUIRED
    assert "--no-admin-fallback" in out.error


def test_merge_pr_review_required_after_admin_failed(
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
    review_decision_calls = {"count": 0}

    def fake_review_decision(*_a: object, **_k: object) -> str:
        review_decision_calls["count"] += 1
        return "REVIEW_REQUIRED"

    monkeypatch.setattr(
        merge_module.gh,
        "pr_review_decision",
        fake_review_decision,
    )
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_REVIEW_REQUIRED
    assert "requires approving review" in out.error
    assert review_decision_calls["count"] == 1


def test_merge_pr_conflict_signal_after_admin_failed_advances_main(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    admin_diag = "PR requires approving review; GraphQL: Pull Request has merge conflicts"
    plain_diag = (
        "X Pull request character-ai/larch#4247 is not mergeable: "
        "the merge commit cannot be cleanly created."
    )
    runner = RecordingRunner(
        responses=[
            *_open_pr_responses(),
            CommandResult(("gh", "pr", "merge"), 1, "", admin_diag, 0.01),
            CommandResult(("gh", "pr", "merge"), 1, "", plain_diag, 0.01),
        ],
    )
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(
        merge_module.gh,
        "pr_review_decision",
        lambda *_a, **_k: pytest.fail("review decision should not be read"),
    )
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_MAIN_ADVANCED
    assert "Pull Request has merge conflicts" in out.error
    assert "not mergeable" in out.error
    assert "cannot be cleanly created" in out.error


def test_merge_pr_not_mergeable_review_only_requires_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            *_open_pr_responses(),
            CommandResult(("gh", "pr", "merge"), 1, "", "admin fail", 0.01),
            CommandResult(("gh", "pr", "merge"), 1, "", "not mergeable", 0.01),
        ],
    )
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    review_decision_calls = {"count": 0}

    def fake_review_decision(*_a: object, **_k: object) -> str:
        review_decision_calls["count"] += 1
        return "REVIEW_REQUIRED"

    monkeypatch.setattr(
        merge_module.gh,
        "pr_review_decision",
        fake_review_decision,
    )
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_REVIEW_REQUIRED
    assert "requires approving review" in out.error
    assert "not mergeable" in out.error
    assert review_decision_calls["count"] == 1


def test_merge_pr_runs_version_race_gate_before_admin_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            *_open_pr_responses(),
            CommandResult(("git", "fetch"), 0, "", "", 0.01),
            CommandResult(("git", "log"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "merge"), 0, "", "", 0.01),
        ],
    )
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_abc)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED
    assert ["git", "fetch", "origin", "main", "--quiet"] in runner.calls


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
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
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
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_MERGED
    assert flushed == [config.MERGE_RESULT_MERGED]


def test_merge_pr_view_failure_is_error(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 1, "", "network down", 0.01),
        ],
    )
    ctx = _ctx(tmpdir=str(tmp_path), pr_number=1)
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "pr view failed" in out.error


def test_ensure_head_empty_local_head_is_error() -> None:
    runner = RecordingRunner()
    state = gh.MergeState("CLEAN", "abc")
    ctx = _ctx()
    out = merge_module._ensure_head_matches_pr(  # pyright: ignore[reportPrivateUsage]
        runner=runner,
        ctx=ctx,
        state=state,
        sleeper=lambda _s: None,
        cwd=None,
    )
    assert isinstance(out, merge_module.MergeResult)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "local HEAD" in out.error


def test_merge_does_not_call_pre_flush_on_clean_green_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(responses=merge_admin_responses())
    pre_calls = {"count": 0}

    def fake_pre_skipped(*_a: object, **_k: object) -> run_logs.RefreshSkip:
        pre_calls["count"] += 1
        return run_logs.RefreshSkip(skipped=True, reason="commit-failed")

    monkeypatch.setattr(run_logs, "flush_logs_pre", fake_pre_skipped)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(merge_module, "_ensure_head_matches_pr", _mock_ensure_head_behind)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state), pr_number=1)
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED
    assert pre_calls["count"] == 0


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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED


def test_merge_flush_recovery_polls_lagged_pr_head_oid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    open_pr = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"old"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"old"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"new"}',
                "",
                0.01,
            ),
            CommandResult(("gh", "pr", "merge"), 0, "", "", 0.01),
        ],
    )
    sleeps: list[float] = []

    monkeypatch.setattr(merge_module, "_flush_recoverable", _mock_true)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_new)
    monkeypatch.setattr(git_module, "force_push_recovery", _mock_force_push_ok)
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx, sleeper=sleeps.append)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED
    assert sleeps == [5.0]


def test_merge_flush_recovery_oid_poll_exhaustion_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    open_pr = '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}'
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 0, open_pr, "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"old"}',
                "",
                0.01,
            ),
            *[
                CommandResult(
                    ("gh", "pr", "view", "1"),
                    0,
                    '{"mergeStateStatus":"CLEAN","headRefOid":"old"}',
                    "",
                    0.01,
                )
                for _ in range(config.MERGE_PR_POST_PUSH_UNKNOWN_RETRIES)
            ],
        ],
    )
    sleeps: list[float] = []
    monkeypatch.setattr(merge_module, "_flush_recoverable", _mock_true)
    monkeypatch.setattr(git_module, "try_rev_parse", _mock_rev_new)
    monkeypatch.setattr(git_module, "force_push_recovery", _mock_force_push_ok)
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx, sleeper=sleeps.append)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "after force-push recovery" in out.error
    assert len(sleeps) == config.MERGE_PR_POST_PUSH_UNKNOWN_RETRIES - 1


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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
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
    assert not merge_module._flush_recoverable(runner=runner, pr_head_oid="aaaa1111", cwd=None)  # pyright: ignore[reportPrivateUsage]


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
    assert not merge_module._flush_recoverable(runner=runner, pr_head_oid="aaaa1111", cwd=None)  # pyright: ignore[reportPrivateUsage]


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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx, sleeper=sleeps.append)
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
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx, sleeper=sleeps.append)
    assert out.result == config.MERGE_RESULT_ERROR
    assert len(sleeps) == config.MERGE_PR_INITIAL_UNKNOWN_RETRIES


def test_merge_post_flush_manifest_recovery_failed_emits_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")

    def fake_post(*_a: object, **_k: object) -> run_logs.RefreshSkip:
        return run_logs.RefreshSkip(
            skipped=True,
            reason=run_logs.REFRESH_SKIP_RECOVERY_FAILED,
        )

    monkeypatch.setattr(run_logs, "flush_logs_post", fake_post)
    ctx = _ctx(tmpdir=str(tmp_path), state_file=str(state))
    out = merge_module._post_flush(  # pyright: ignore[reportPrivateUsage]
        runner=RecordingRunner(),
        ctx=ctx,
        merge_result=config.MERGE_RESULT_MERGED,
    )
    assert out is not None
    assert out.result == config.MERGE_RESULT_ERROR
    assert run_logs.REFRESH_SKIP_RECOVERY_FAILED in out.error


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
        runner=RecordingRunner(),
        ctx=ctx,
        merge_result=config.MERGE_RESULT_MERGED,
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
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_MERGED


def test_merge_post_flush_false_skips_internal_flush(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(responses=merge_admin_responses(double_open_view=True))
    calls = {"post": 0}

    def fake_post(*_args: object, **_kwargs: object) -> run_logs.RefreshSkip:
        calls["post"] += 1
        return run_logs.RefreshSkip(skipped=False, reason="")

    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(merge_module, "_ensure_head_matches_pr", _mock_ensure_head_behind)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    monkeypatch.setattr(run_logs, "flush_logs_post", fake_post)
    out = merge_module.merge_pr(runner=runner, ctx=_ctx(), post_flush=False)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED
    assert calls["post"] == 0


def test_post_flush_warns_on_degraded_skip(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(run_logs, "flush_logs_post", lambda *_a, **_k: run_logs.RefreshSkip(skipped=True, reason="post-merge-refresh-failed"))
    result = merge_module._post_flush(runner=RecordingRunner(), ctx=_ctx(), merge_result=config.MERGE_RESULT_MERGED)  # pylint: disable=protected-access
    assert result is None
    assert "merge: post-merge flush skipped: post-merge-refresh-failed" in capsys.readouterr().err


def test_post_flush_redaction_failed_still_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_logs, "flush_logs_post", lambda *_a, **_k: run_logs.RefreshSkip(skipped=True, reason="redaction-failed"))
    result = merge_module._post_flush(runner=RecordingRunner(), ctx=_ctx(), merge_result=config.MERGE_RESULT_MERGED)  # pylint: disable=protected-access
    assert result is not None
    assert result.result == config.MERGE_RESULT_ERROR
