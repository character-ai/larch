from pathlib import Path

import argparse
import io
import os
import subprocess
import tempfile
import pytest

from larch.core import config
from larch.issue import issue_create
from larch.state import stall_recovery
from larch.state import _escalation as _sr_escalation
from larch.state import _report as _sr_report


def _stdout_kv(output: str, key: str) -> str:
    prefix = key + "="
    return next(line[len(prefix):] for line in output.splitlines() if line.startswith(prefix))


def _record_escalation_args(tmp_path: Path, detail_log: str = "") -> list[str]:
    args = [
        "--implement-tmpdir", str(tmp_path),
        "--site", "step5",
        "--trigger", "main-agent-required",
        "--step", "5",
        "--phase", "review",
        "--dispatcher", "lint-fix-loop",
        "--exit-code", "1",
    ]
    if detail_log:
        args.extend(["--failure-detail-log", detail_log])
    return args


def _escalation_ledger_fields(tmp_path: Path) -> dict[str, str]:
    row = (tmp_path / "stall-recovery-escalation-ledger.tsv").read_text(encoding="utf-8").strip()
    return dict(part.split("=", 1) for part in row.split("\t"))


def _assert_no_record_escalation_tool_failure(tmp_path: Path) -> None:
    execution = tmp_path / "execution-issues.md"
    if execution.exists():
        assert "Tool Failure: record-escalation" not in execution.read_text(encoding="utf-8")


def test_retry_policy_transient(capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.retry_policy_main(["--class", "transient-infra"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "MAX_ATTEMPTS=4" in out
    assert "RETRY_DELAY=sleep-seconds.sh 5" in out


def test_normalize_issue_env_created(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    issue_out = tmp_path / "issue.out"
    _ = issue_out.write_text(
        "ISSUES_CREATED=1\nISSUES_FAILED=0\nISSUE_1_NUMBER=12\nISSUE_1_URL=https://github.com/o/r/issues/12\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_issue_env_main([
        "--implement-tmpdir", str(tmp_path),
        "--issue-stdout-file", str(issue_out),
        "--issue-exit-code", "0",
    ])

    assert rc == 0
    assert "NORMALIZED=true" in capsys.readouterr().out
    assert "ISSUE_NUMBER=12" in (tmp_path / "stall-recovery-issue.env").read_text(encoding="utf-8")


def test_classify_transient_infra(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=ci-initial\nSTALL_TRACKING=true\nSTALL_STEP=8\nBAIL_REASON=\nEXIT_CODE=4\n",
        encoding="utf-8",
    )
    log = tmp_path / "failure.log"
    _ = log.write_text("gh: API rate limit exceeded\n", encoding="utf-8")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=step8-shippr" in out


def test_classify_protected_path_modification_required(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=implementation\nSTALL_TRACKING=true\nSTALL_STEP=2\nBAIL_REASON=protected-path-modification-required\nEXIT_CODE=4\n",
        encoding="utf-8",
    )

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=unrecoverable" in out
    assert "FAILURE_CLASS=protected-path" not in out


def test_classify_timeout_with_unrelated_protected_path_text_stays_transient(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=ci-initial\nSTALL_TRACKING=true\nSTALL_STEP=8\nBAIL_REASON=\nEXIT_CODE=4\n"
        "NOTE=protected-path sandbox mention\n",
        encoding="utf-8",
    )
    log = tmp_path / "failure.log"
    _ = log.write_text("network timeout while contacting github api unavailable\n", encoding="utf-8")
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "FAILURE_CLASS=protected-path" not in out


def test_classify_relevant_checks_failed_detail_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=review\nSTALL_TRACKING=true\nSTALL_STEP=5\nBAIL_REASON=\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    log = tmp_path / "failure.log"
    _ = log.write_text("relevant-checks failed\n", encoding="utf-8")
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=lint-failure" in out
    assert "RESUME_HINT=step5-review" in out
    assert "MATCHED_CLASSIFIER_PATTERN=lint-output" in out


@pytest.mark.parametrize("word", ["flint", "splinter", "plint"])
def test_classify_bare_lint_substring_false_positives(
    word: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=review\nSTALL_TRACKING=true\nSTALL_STEP=5\nBAIL_REASON=\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    log = tmp_path / "failure.log"
    _ = log.write_text(f"error in {word} tool output\n", encoding="utf-8")
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=lint-failure" not in out
    assert "MATCHED_CLASSIFIER_PATTERN=fallback" in out


def test_record_escalation_writes_canonical_ledger(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.record_escalation_main(_record_escalation_args(tmp_path))

    assert rc == 0
    assert "ESCALATION_RECORDED=true" in capsys.readouterr().out
    assert "site=step5" in (tmp_path / "stall-recovery-escalation-ledger.tsv").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("case", "expected_skip"),
    [
        ("non-absolute", "failure-detail-log-non-absolute"),
        ("symlink", "failure-detail-log-symlink"),
        ("outside-tmpdir", "failure-detail-log-outside-tmpdir"),
        ("missing", "failure-detail-log-missing"),
        ("directory", "failure-detail-log-not-regular-file"),
        ("unreadable", "failure-detail-log-unreadable"),
    ],
)
def test_record_escalation_detail_log_misses_are_nonfatal(
    case: str,
    expected_skip: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-detail.log"
    detail = "relative.log"
    if case == "symlink":
        target = tmp_path / "target.log"
        _ = target.write_text("detail\n", encoding="utf-8")
        link = tmp_path / "detail-link.log"
        link.symlink_to(target)
        detail = str(link)
    elif case == "outside-tmpdir":
        _ = outside.write_text("detail\n", encoding="utf-8")
        detail = str(outside)
    elif case == "missing":
        detail = str(tmp_path / "missing.log")
    elif case == "directory":
        directory = tmp_path / "detail-dir"
        directory.mkdir()
        detail = str(directory)
    elif case == "unreadable":
        unreadable = tmp_path / "unreadable.log"
        _ = unreadable.write_text("detail\n", encoding="utf-8")
        unreadable.chmod(0o000)
        detail = str(unreadable)

    try:
        rc = stall_recovery.record_escalation_main(_record_escalation_args(tmp_path, detail))
        assert rc == 0
        assert "ESCALATION_RECORDED=true" in capsys.readouterr().out
        fields = _escalation_ledger_fields(tmp_path)
        assert fields["failure_detail_log"] == ""
        assert fields["detail_log_skipped"] == expected_skip
        _assert_no_record_escalation_tool_failure(tmp_path)
    finally:
        if case == "unreadable":
            Path(detail).chmod(0o600)
        outside.unlink(missing_ok=True)


def test_record_escalation_truncates_oversize_detail_log(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    oversize = tmp_path / "oversize.log"
    content = b"x" * (stall_recovery.MAX_OPTIONAL_EVIDENCE_BYTES + 1)
    _ = oversize.write_bytes(content)

    rc = stall_recovery.record_escalation_main(_record_escalation_args(tmp_path, str(oversize)))

    assert rc == 0
    assert "ESCALATION_RECORDED=true" in capsys.readouterr().out
    fields = _escalation_ledger_fields(tmp_path)
    assert fields["failure_detail_log"]
    assert fields["failure_detail_log"] != oversize.name
    assert "detail_log_skipped" not in fields
    sidecar = tmp_path / fields["failure_detail_log"]
    assert sidecar.is_file()
    assert not sidecar.is_symlink()
    assert sidecar.stat().st_size <= stall_recovery.MAX_OPTIONAL_EVIDENCE_BYTES
    assert sidecar.read_bytes() == content[:stall_recovery.MAX_OPTIONAL_EVIDENCE_BYTES]
    _assert_no_record_escalation_tool_failure(tmp_path)


def test_classify_uses_truncated_escalation_sidecar_for_oversize_detail_log(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state(tmp_path, "5", "review")
    oversize = tmp_path / "oversize.log"
    _ = oversize.write_bytes(
        b"relevant-checks failed\n"
        + (b"x" * stall_recovery.MAX_OPTIONAL_EVIDENCE_BYTES)
    )
    assert stall_recovery.record_escalation_main(_record_escalation_args(tmp_path, str(oversize))) == 0
    fields = _escalation_ledger_fields(tmp_path)
    sidecar = tmp_path / fields["failure_detail_log"]
    _ = capsys.readouterr()

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(oversize),
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "--failure-detail-log exceeds 64KiB" in captured.err
    assert "FAILURE_CLASS=lint-failure" in captured.out
    assert "MATCHED_CLASSIFIER_PATTERN=lint-output" in captured.out
    assert f"FAILURE_DETAIL_LOG={sidecar.resolve()}" in captured.out
    assert f"FAILURE_DETAIL_LOG={oversize}" not in captured.out


def test_record_escalation_oversize_truncate_failure_is_nonfatal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversize = tmp_path / "oversize.log"
    _ = oversize.write_bytes(b"x" * (stall_recovery.MAX_OPTIONAL_EVIDENCE_BYTES + 1))

    def fail_truncate(*, tmpdir: Path, path: Path) -> str | None:
        _ = tmpdir, path
        sidecar: str | None = None
        return sidecar

    monkeypatch.setattr(_sr_escalation, "_materialize_truncated_failure_detail_log", fail_truncate)

    rc = stall_recovery.record_escalation_main(_record_escalation_args(tmp_path, str(oversize)))

    assert rc == 0
    assert "ESCALATION_RECORDED=true" in capsys.readouterr().out
    fields = _escalation_ledger_fields(tmp_path)
    assert fields["failure_detail_log"] == ""
    assert fields["detail_log_skipped"] == "failure-detail-log-truncate-failed"
    _assert_no_record_escalation_tool_failure(tmp_path)


def test_validate_token_accepts_design_step(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.validate_token_main([
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--implement-tmpdir", str(tmp_path),
        "--token-kind", "step",
        "--value", "judge-panel",
    ])

    assert rc == 0
    assert "TOKEN_VALID=true" in capsys.readouterr().out


def test_validate_token_rejects_unknown_step(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.validate_token_main([
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--implement-tmpdir", str(tmp_path),
        "--token-kind", "step",
        "--value", "not-a-step",
    ])

    assert rc == 1
    assert "TOKEN_VALID=false" in capsys.readouterr().out


def test_validate_terminal_state_accepts_design_state(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "design-failure-terminal-state.env"
    _ = state.write_text(
        "DESIGN_FAILURE_VERSION=1\n"
        "DESIGN_FAILURE_KIND=terminal\n"
        "FAILURE_OUTCOME=failed-judge-panel\n"
        "STALL_STEP=judge-panel\n"
        "PHASE=judge-panel\n"
        "SITE=decompose-panel\n"
        "TRIGGER=decompose-panel-retry-exhausted\n"
        "BAIL_REASON=decompose-panel-retry-exhausted\n"
        "EXIT_CODE=1\n"
        "FAILURE_DETAIL_LOG=\n"
        "SOURCE_SCRIPT=split-path\n",
        encoding="utf-8",
    )

    ns = argparse.Namespace(
        implement_tmpdir=str(tmp_path),
        primary_state_file=str(state),
        profile="generic",
        artifact_prefix="design-failure",
    )
    rc = stall_recovery.validate_terminal_state(ns)

    assert rc == 0
    assert "VALID=true" in capsys.readouterr().out


def test_dedup_tier_a_report_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")

    rc = stall_recovery.dedup_tier_a_report_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "STALL_RECOVERY_REPORT_STATUS=dry-run" in capsys.readouterr().out


def test_classify_rebase_failed_step(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=rebase-failed\nPHASE=rebase-failed\nBAIL_REASON=\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path), "--stall-step", "rebase-failed"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=step8-shippr" in out


def test_classify_ci_fix_exhausted_with_detail_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=8\nPHASE=ci-merge\nBAIL_REASON=ci-fix-exhausted\nEXIT_CODE=2\n",
        encoding="utf-8",
    )
    detail = tmp_path / "failure.log"
    _ = detail.write_text("ci fix loop exhausted\n", encoding="utf-8")
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(detail),
        "--bail-reason", "ci-fix-exhausted",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=unrecoverable" in out
    assert "RESUME_HINT=none" in out


def test_classify_ci_fix_exhausted_outranks_test_evidence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=8\nPHASE=ci-merge\nBAIL_REASON=ci-fix-exhausted\nEXIT_CODE=2\n",
        encoding="utf-8",
    )
    detail = tmp_path / "failure.log"
    _ = detail.write_text("pytest reports 2 failing tests\n", encoding="utf-8")
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(detail),
        "--bail-reason", "ci-fix-exhausted",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=unrecoverable" in out
    assert "RESUME_HINT=none" in out


def test_retry_policy_ci_fix_exhausted_cap(capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.retry_policy_main(["--class", "ci-fix-exhausted"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "MAX_ATTEMPTS=0" in out
    assert "RETRY_DELAY=none" in out


def test_retry_policy_lint_failure_cap(capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.retry_policy_main(["--class", "lint-failure"])
    assert rc == 0
    assert "MAX_ATTEMPTS=8" in capsys.readouterr().out


def test_record_attempt_appends_history(tmp_path: Path) -> None:
    first = stall_recovery.record_attempt_main([
        "--implement-tmpdir", str(tmp_path),
        "--class", "transient-infra",
        "--signature", "abc",
        "--outcome", "failed",
    ])
    second = stall_recovery.record_attempt_main([
        "--implement-tmpdir", str(tmp_path),
        "--class", "lint-failure",
        "--signature", "def",
        "--resume-hint", "step5-review",
        "--outcome", "success",
    ])

    assert first == 0
    assert second == 0
    text = (tmp_path / "stall-recovery-attempts.env").read_text(encoding="utf-8")
    assert "attempt_count=2" in text
    assert "attempt.1.class=transient-infra" in text
    assert "attempt.1.signature=abc" in text
    assert "attempt.2.class=lint-failure" in text
    assert "attempt.2.signature=def" in text
    assert "attempt.2.resume_hint=step5-review" in text
    assert "attempt.2.outcome=success" in text
    assert "last_signature=def" in text


def test_validate_tier_b_public_file_rejects_sensitive_token(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    corpus = tmp_path / "stall-recovery-sensitive-corpus.txt"
    public = tmp_path / "public.md"
    _ = corpus.write_text("super-secret-token\n", encoding="utf-8")
    _ = public.write_text("contains super-secret-token\n", encoding="utf-8")
    rc = stall_recovery.validate_tier_b_public_file_main([
        "--implement-tmpdir", str(tmp_path),
        "--public-file", str(public.resolve()),
        "--sensitive-corpus-file", str(corpus.resolve()),
    ])
    assert rc == 1
    assert "PUBLIC_FILE_VALID=false" in capsys.readouterr().out


def test_compose_report_python_impl(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    custom_class = tmp_path / "custom-class.env"
    custom_root = tmp_path / "custom-root.md"
    custom_bounded = tmp_path / "custom-bounded.md"
    custom_corpus = tmp_path / "custom-sensitive.env"
    source_env = tmp_path / "source-env.sh"
    _ = custom_class.write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    _ = custom_root.write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=custom summary\n\nDetailed root cause.\n",
        encoding="utf-8",
    )
    _ = custom_bounded.write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=custom summary\n\nBounded detail.\n",
        encoding="utf-8",
    )
    _ = custom_corpus.write_text("safe-token\n", encoding="utf-8")
    _ = source_env.write_text("export SESSION_ID='compose-run-123'\n", encoding="utf-8")
    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "chat-print",
        "--report-kind", "terminal-failure",
        "--classification-file", str(custom_class),
        "--root-cause-file", str(custom_root),
        "--bounded-root-cause-file", str(custom_bounded),
        "--sensitive-corpus-file", str(custom_corpus),
        "--session-env-file", str(source_env),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_RECOVERY_REPORT_KIND=terminal-failure" in out
    assert "STALL_RECOVERY_REPORT_TIER=B" in out
    assert "STALL_RECOVERY_REPORT_STATUS=dry-run" in out
    assert "REPORT_DEDUP_SIGNATURE=" in out
    assert "compose-run-123" in (tmp_path / "design-failure-chat-print.md").read_text(encoding="utf-8")


def test_lint_subcommand_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.lint_main([])
    assert rc == 0
    assert "LINT_OK=true" in capsys.readouterr().out


def test_normalize_outcome_reports_full_kv_layers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text("STALL_TRACKING=false\nMERGE_RESULT=already_merged\n", encoding="utf-8")
    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "IMPLEMENT_NORMALIZED_OUTCOME=force-merged-externally" in out
    assert "IMPLEMENT_ANY_STALL_TRACKING=false" in out
    assert "IMPLEMENT_SHIP_STALL_TRACKING=false" in out


def test_normalize_outcome_flags_panel_failed_merge_downgrade(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-seed-input.env").write_text("MERGE=true\n", encoding="utf-8")
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nPR_NUMBER=12\nMERGE=false\nDRAFT=false\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "STALL_STEP=5\nRESUME_HINT=step8-shippr\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "execution-issues.md").write_text("Step 5 — wrapper stalled: panel-failed\n", encoding="utf-8")

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "IMPLEMENT_NORMALIZED_OUTCOME=pr-created" in out
    assert "IMPLEMENT_MERGE_DOWNGRADED=true" in out


def test_normalize_outcome_merge_with_pr_evidence_is_pr_created(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPHASE=rebase\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=pr-created" in capsys.readouterr().out


def test_normalize_outcome_draft_pr_evidence_is_pr_created_draft(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nMERGE_RESULT=\nDRAFT=true\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=pr-created-draft" in capsys.readouterr().out


def test_normalize_outcome_pre_ship_no_pr_evidence_is_shipping(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Seeded ship state with no PR yet — in-flight pre-ship snapshot should be
    # labelled "shipping", not the misleading "bailed".
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=shipping" in capsys.readouterr().out


def test_normalize_outcome_no_state_files_is_shipping(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # No ship state at all (Step 7a pre-ship flush before seed-initial-state runs).
    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=shipping" in capsys.readouterr().out


def test_normalize_outcome_bail_reason_without_pr_evidence_stays_bailed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Bail reason present — genuine bail even without PR evidence.
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=\nMERGE_RESULT=\nBAIL_REASON=some-error\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=bailed" in capsys.readouterr().out


def test_normalize_outcome_post_pr_stalled_guard_not_pr_created(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPHASE=stalled\nBAIL_REASON=ci-fix-exhausted\nMERGE_RESULT=\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=stalled" in capsys.readouterr().out


def test_normalize_outcome_ignores_stale_finalize_stalled_on_resume(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPHASE=ci-initial\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "finalize-state.sh").write_text("PHASE=stalled\n", encoding="utf-8")

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=pr-created" in capsys.readouterr().out


def test_normalize_outcome_exit_code_guard_not_pr_created(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nEXIT_CODE=4\nMERGE_RESULT=\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=bailed" in capsys.readouterr().out


def test_normalize_outcome_recovered_stall_ship_flag_pre_pr_is_shipping(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # In-flight ship flush carrying STALL_TRACKING=true from a mid-flight stall the
    # run already recovered from (no PR yet, no failure signals, finalize-state not
    # written). The stale flag must not freeze the committed log at "stalled".
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nMERGE=true\nPR_NUMBER=\nPHASE=checks\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=shipping" in capsys.readouterr().out


def test_normalize_outcome_recovered_stall_with_pr_evidence_is_pr_created(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Recovered stall flag lingering on a during-ship flush that already has a PR
    # (issue #5676, run 2931787A). Re-evaluate to "pr-created", not "stalled".
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nMERGE=true\nPR_NUMBER=12\nPHASE=ci-initial\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=pr-created" in capsys.readouterr().out


def test_normalize_outcome_recovered_stall_merged_is_merged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A run that stalled mid-flight, recovered, and merged. The merge result wins
    # over a stale stall flag.
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nMERGE=true\nPR_NUMBER=12\nMERGE_RESULT=merged\nDRAFT=false\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=merged" in capsys.readouterr().out


def test_normalize_outcome_recovered_stall_memory_only_pre_ship_is_shipping(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Step-7a pre-ship flush with an in-memory stall flag (issue #5676, run
    # BC6EFF24): no state files, no failure signals. Must reconcile to "shipping".
    rc = stall_recovery.normalize_outcome_main(
        ["--implement-tmpdir", str(tmp_path), "--in-memory-stall-tracking", "true"]
    )

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=shipping" in capsys.readouterr().out


def test_normalize_outcome_terminal_stall_finalize_state_stays_stalled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Live teardown report of a genuine terminal stall: finalize-state.sh records
    # the stall even without a bail reason. This must stay "stalled".
    _ = (tmp_path / "finalize-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=5\nMERGE=true\nPR_NUMBER=\nMERGE_RESULT=\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(
        ["--implement-tmpdir", str(tmp_path), "--in-memory-stall-tracking", "true"]
    )

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=stalled" in capsys.readouterr().out


def test_normalize_outcome_terminal_stall_ship_phase_no_bail_stays_stalled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Genuine ship-phase terminal stall (PHASE=stalled) without an explicit bail
    # reason must stay "stalled" via the ship-phase terminal indicator.
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nMERGE=true\nPR_NUMBER=\nPHASE=stalled\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=stalled" in capsys.readouterr().out


def test_normalize_outcome_stall_flag_with_bail_reason_stays_stalled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A stall flag plus an explicit bail reason is a genuine terminal stall even
    # when the ship phase is still in-flight: the failure-signal indicator (not
    # PHASE=stalled) keeps it "stalled".
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=true\nMERGE=true\nPR_NUMBER=\nPHASE=ci-initial\nMERGE_RESULT=\nBAIL_REASON=ci-fix-exhausted\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=stalled" in capsys.readouterr().out



def test_normalize_outcome_stale_finalize_terminal_fields_with_clean_pr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPR_URL=https://example.test/pr/12\n"
        "PHASE=ci-initial\nMERGE_RESULT=\nDRAFT=false\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "finalize-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=5\nPHASE=stalled\nEXIT_CODE=4\nBAIL_NEEDS_USER_INPUT=true\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "IMPLEMENT_NORMALIZED_OUTCOME=pr-created" in out
    assert "IMPLEMENT_ANY_STALL_TRACKING=false" in out
    assert "IMPLEMENT_FINALIZE_STALL_TRACKING=true" in out


def test_normalize_outcome_stale_finalize_terminal_fields_with_clean_merge(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPHASE=postmerge\nMERGE_RESULT=merged\nDRAFT=false\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "finalize-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=5\nPHASE=stalled\nEXIT_CODE=4\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=merged" in capsys.readouterr().out


def test_normalize_outcome_finalize_overlay_not_stale_with_active_ship_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_TRACKING=false\nMERGE=true\nPR_NUMBER=12\nPHASE=ci-initial\n"
        "MERGE_RESULT=\nBAIL_REASON=ci-fix-exhausted\nDRAFT=false\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "finalize-state.sh").write_text(
        "STALL_TRACKING=true\nSTALL_STEP=5\nPHASE=stalled\nEXIT_CODE=4\n",
        encoding="utf-8",
    )

    rc = stall_recovery.normalize_outcome_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "IMPLEMENT_NORMALIZED_OUTCOME=stalled" in capsys.readouterr().out


def test_classify_design_state_file_merge(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    primary = tmp_path / "design-failure-terminal-state.env"
    _ = primary.write_text(
        "STALL_TRACKING=true\nSTALL_STEP=judge-panel\nPHASE=judge-panel\nBAIL_REASON=decompose-panel-retry-exhausted\nEXIT_CODE=1\nDISPATCHER=split-path\n",
        encoding="utf-8",
    )
    rc = stall_recovery.classify_main(
        [
            "--implement-tmpdir",
            str(tmp_path),
            "--primary-state-file",
            str(primary),
            "--in-memory-stall-tracking",
            "true",
            "--artifact-prefix",
            "design-failure",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_TRACKING=true" in out
    assert "MATCHED_CLASSIFIER_PATTERN=" in out
    assert (tmp_path / "design-failure-classification.env").is_file()


def test_classify_generic_terminal_state_matches_design_contract(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    primary = tmp_path / "design-failure-terminal-state.env"
    _ = primary.write_text(
        "DESIGN_FAILURE_VERSION=1\n"
        "DESIGN_FAILURE_KIND=terminal\n"
        "FAILURE_OUTCOME=failed-judge-panel\n"
        "STALL_STEP=judge-panel\n"
        "PHASE=judge-panel\n"
        "SITE=decompose-panel\n"
        "TRIGGER=decompose-panel-retry-exhausted\n"
        "BAIL_REASON=decompose-panel-retry-exhausted\n"
        "EXIT_CODE=1\n"
        "FAILURE_DETAIL_LOG=\n"
        "SOURCE_SCRIPT=split-path\n",
        encoding="utf-8",
    )

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--primary-state-file", str(primary),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_TRACKING=true" in out
    assert "RESUME_HINT=none" in out
    assert "STALL_STEP=judge-panel" in out
    assert "PHASE=judge-panel" in out
    assert "BAIL_REASON=decompose-panel-retry-exhausted" in out
    assert "DISPATCHER=split-path" in out
    assert "CLASSIFICATION_FILE=" in out
    assert (tmp_path / "design-failure-classification.env").is_file()


def test_classify_no_stall_emits_no_stall_pattern(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    primary = tmp_path / "design-failure-terminal-state.env"
    _ = primary.write_text(
        "STALL_TRACKING=false\nSTALL_STEP=judge-panel\nPHASE=judge-panel\nBAIL_REASON=decompose-panel-retry-exhausted\nEXIT_CODE=1\nDISPATCHER=split-path\n",
        encoding="utf-8",
    )
    rc = stall_recovery.classify_main(
        [
            "--implement-tmpdir",
            str(tmp_path),
            "--primary-state-file",
            str(primary),
            "--artifact-prefix",
            "design-failure",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=unrecoverable" in out
    assert "MATCHED_CLASSIFIER_PATTERN=no-stall" in out


def test_populate_sensitive_corpus_python_impl(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "stall-recovery-sensitive-corpus.env").write_text("existing-token\n", encoding="utf-8")
    _ = (tmp_path / "plan.txt").write_text("https://client.example.test/private\n", encoding="utf-8")
    rc = stall_recovery.populate_sensitive_corpus_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SENSITIVE_CORPUS_FILE=" in out
    corpus = (tmp_path / "stall-recovery-sensitive-corpus.env").read_text(encoding="utf-8")
    assert "existing-token" in corpus
    assert "https://client.example.test/private" in corpus


def test_build_sensitive_corpus_includes_detail_log(tmp_path: Path) -> None:
    sensitive = tmp_path / "stall-recovery-sensitive-corpus.env"
    _ = sensitive.write_text("existing-token\n", encoding="utf-8")
    class_file = tmp_path / "stall-recovery-classification.env"
    detail = tmp_path / "failure.log"
    _ = detail.write_text("failure-detail-secret\n", encoding="utf-8")
    _ = class_file.write_text(f"FAILURE_DETAIL_LOG={detail}\n", encoding="utf-8")
    out = tmp_path / "effective.env"
    stall_recovery.build_sensitive_corpus_from_evidence(
        tmpdir=tmp_path,
        sensitive_file=sensitive,
        class_file=class_file,
        attempts_file=tmp_path / "stall-recovery-attempts.env",
        ledger=tmp_path / "stall-recovery-escalation-ledger.tsv",
        fallback=tmp_path / "stall-recovery-escalation-fallback.tsv",
        marker=tmp_path / "stall-recovery-escalation-record-failure.env",
        out_file=out,
    )
    text = out.read_text(encoding="utf-8")
    assert "existing-token" in text
    assert "failure-detail-secret" in text


def test_validate_tier_b_public_file_rebuilds_effective_corpus(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    corpus = tmp_path / "stall-recovery-sensitive-corpus.env"
    _ = corpus.write_text("safe-token\n", encoding="utf-8")
    _ = (tmp_path / "plan.txt").write_text("https://client.example.test/private\n", encoding="utf-8")
    public = tmp_path / "public.md"
    _ = public.write_text("mentions https://client.example.test/private\n", encoding="utf-8")
    rc = stall_recovery.validate_tier_b_public_file_main(
        [
            "--implement-tmpdir",
            str(tmp_path),
            "--public-file",
            str(public.resolve()),
            "--sensitive-corpus-file",
            str(corpus.resolve()),
        ]
    )
    assert rc == 1
    assert "PUBLIC_FILE_VALID=false" in capsys.readouterr().out


def test_compose_report_rejects_outside_output_path(tmp_path: Path) -> None:
    outside = Path("/tmp/stall-recovery-outside-report.md")
    rc = stall_recovery.compose_report_main(
        [
            "--implement-tmpdir",
            str(tmp_path),
            "--surface",
            "chat-print",
            "--report-kind",
            "terminal-failure",
            "--output-file",
            str(outside),
        ]
    )
    assert rc == 1


def test_compose_report_rejects_outside_ledger_path(tmp_path: Path) -> None:
    custom_class = tmp_path / "custom-class.env"
    custom_root = tmp_path / "custom-root.md"
    custom_bounded = tmp_path / "custom-bounded.md"
    custom_corpus = tmp_path / "custom-sensitive.env"
    _ = custom_class.write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    _ = custom_root.write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=custom summary\n\nDetailed root cause.\n",
        encoding="utf-8",
    )
    _ = custom_bounded.write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=custom summary\n\nBounded detail.\n",
        encoding="utf-8",
    )
    _ = custom_corpus.write_text("safe-token\n", encoding="utf-8")
    outside_ledger = Path("/tmp/stall-ledger-outside.tsv")
    _ = outside_ledger.write_text("utc=now\tsite=step5\ttrigger=main-agent-required\n", encoding="utf-8")
    rc = stall_recovery.compose_report_main(
        [
            "--implement-tmpdir",
            str(tmp_path),
            "--surface",
            "chat-print",
            "--report-kind",
            "terminal-failure",
            "--classification-file",
            str(custom_class),
            "--root-cause-file",
            str(custom_root),
            "--bounded-root-cause-file",
            str(custom_bounded),
            "--sensitive-corpus-file",
            str(custom_corpus),
            "--escalation-ledger-file",
            str(outside_ledger),
            "--output-file",
            str(tmp_path / "out.md"),
        ],
    )
    assert rc == 1


def test_compose_report_rejects_sensitive_plan_evidence(tmp_path: Path) -> None:
    custom_class = tmp_path / "custom-class.env"
    custom_root = tmp_path / "custom-root.md"
    custom_bounded = tmp_path / "custom-bounded.md"
    custom_corpus = tmp_path / "custom-sensitive.env"
    _ = custom_class.write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    _ = custom_root.write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=custom summary\n\nDetailed root cause.\n",
        encoding="utf-8",
    )
    _ = custom_bounded.write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=custom summary\n\nBounded finding mentions https://client.example.test/private.\n",
        encoding="utf-8",
    )
    _ = custom_corpus.write_text("safe-token\n", encoding="utf-8")
    _ = (tmp_path / "plan.txt").write_text("https://client.example.test/private\n", encoding="utf-8")
    rc = stall_recovery.compose_report_main(
        [
            "--implement-tmpdir",
            str(tmp_path),
            "--surface",
            "chat-print",
            "--report-kind",
            "terminal-failure",
            "--classification-file",
            str(custom_class),
            "--root-cause-file",
            str(custom_root),
            "--bounded-root-cause-file",
            str(custom_bounded),
            "--sensitive-corpus-file",
            str(custom_corpus),
            "--output-file",
            str(tmp_path / "out.md"),
        ],
    )
    assert rc == 1


def test_clear_stall_clears_tracking_and_preserves_keys(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text(
        "PHASE=ci-initial\nSTALL_TRACKING=true\nSTALL_STEP=5\nEXIT_CODE=4\n"
        "BAIL_REASON=adopted-issue-closed\nBAIL_FAILURE_DETAIL_LOG=/tmp/failure.log\n",
        encoding="utf-8",
    )
    rc = stall_recovery.clear_stall_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    text = state.read_text(encoding="utf-8")
    assert "STALL_TRACKING=false" in text
    assert "STALL_STEP=" in text
    assert "PHASE=ci-initial" in text
    assert "EXIT_CODE=unknown" in text
    assert "BAIL_REASON=" in text
    assert "BAIL_FAILURE_DETAIL_LOG=/tmp/failure.log" in text
    assert "CLEARED=true" in capsys.readouterr().out


def test_clear_stall_rejects_malformed_state_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text("not valid\n", encoding="utf-8")

    rc = stall_recovery.clear_stall_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 3
    assert "CLEARED=false" in capsys.readouterr().out


def test_clear_stall_rejects_dangling_state_symlink(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "ship-pr-state.sh"
    state.symlink_to(tmp_path / "missing-state.sh")

    rc = stall_recovery.clear_stall_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 3
    assert "CLEARED=false" in capsys.readouterr().out


def test_clear_stall_unlinks_dead_checks_bg_wait_marker(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_bg_wait_marker(tmp_path, step="implement-step3-checks", pid=_dead_pid())

    rc = stall_recovery.clear_stall_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    assert not (tmp_path / ".bg-wait-active").exists()
    assert "CLEARED=true" in capsys.readouterr().out


def test_seed_terminal_state_rewrite_honors_stall_step(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text(
        "PHASE=ci-initial\nSTALL_TRACKING=true\nSTALL_STEP=3\nEXIT_CODE=4\n"
        "BAIL_REASON=first-fixer-non-health\nBAIL_FAILURE_DETAIL_LOG=/tmp/failure.log\n",
        encoding="utf-8",
    )
    rc = stall_recovery.seed_terminal_state_main(
        ["--implement-tmpdir", str(tmp_path), "--stall-step", "5", "--phase", "review"],
    )
    assert rc == 0
    text = state.read_text(encoding="utf-8")
    assert "STALL_TRACKING=true" in text
    assert "STALL_STEP=5" in text
    assert "PHASE=review" in text
    assert "EXIT_CODE=4" in text
    out = capsys.readouterr().out
    assert "SEEDED=true" in out
    assert "SEED_MODE=rewrite" in out


def test_seed_terminal_state_fresh_seeds_defaults(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.seed_terminal_state_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    state = tmp_path / "ship-pr-state.sh"
    text = state.read_text(encoding="utf-8")
    assert "STALL_TRACKING=true" in text
    assert "STALL_STEP=8" in text
    assert "PHASE=ci-initial" in text
    assert "EXIT_CODE=4" in text
    out = capsys.readouterr().out
    assert "SEEDED=true" in out
    assert "SEED_MODE=seed" in out


def test_seed_terminal_state_rejects_malformed_state_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "ship-pr-state.sh"
    _ = state.write_text("not valid\n", encoding="utf-8")

    rc = stall_recovery.seed_terminal_state_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 3
    assert "SEEDED=false" in capsys.readouterr().out


def test_seed_terminal_state_rejects_dangling_state_symlink(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "ship-pr-state.sh"
    state.symlink_to(tmp_path / "missing-state.sh")

    rc = stall_recovery.seed_terminal_state_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 3
    assert "SEEDED=false" in capsys.readouterr().out


_LINT_FIX_BAIL_TOKENS = config.LINT_FIX_BAIL_REASON_TOKENS

# A timeout-only detail log would classify as transient-infra without the Step 5 lint-fix
# bail handoff; the bail token must beat the timeout scan (issue #4402).
_TIMEOUT_PYRIGHT_LOG = (
    "subprocess timed out after 600s\n"
    'python/test_collect_results.py:42:9 - error: "_retry_output_path" is private (reportPrivateUsage)\n'
    "timeout\n"
)


@pytest.mark.parametrize("token", _LINT_FIX_BAIL_TOKENS)
def test_classify_lint_fix_bail_token_beats_timeout(token: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=review\nSTALL_TRACKING=true\nSTALL_STEP=5\nBAIL_REASON=\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    log = tmp_path / "failure.log"
    _ = log.write_text(_TIMEOUT_PYRIGHT_LOG, encoding="utf-8")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
        "--bail-reason", token,
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=lint-failure" in out
    assert "RESUME_HINT=step5-review" in out
    assert "MATCHED_CLASSIFIER_PATTERN=lint-fix-bail-token" in out


@pytest.mark.parametrize("token", _LINT_FIX_BAIL_TOKENS)
def test_classify_lint_fix_bail_token_from_state_beats_timeout(token: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        f"PHASE=review\nSTALL_TRACKING=true\nSTALL_STEP=5\nBAIL_REASON={token}\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    log = tmp_path / "failure.log"
    _ = log.write_text(_TIMEOUT_PYRIGHT_LOG, encoding="utf-8")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=lint-failure" in out
    assert "RESUME_HINT=step5-review" in out
    assert "MATCHED_CLASSIFIER_PATTERN=lint-fix-bail-token" in out


def test_classify_timeout_without_lint_fix_token_stays_transient(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=review\nSTALL_TRACKING=true\nSTALL_STEP=5\nBAIL_REASON=\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    log = tmp_path / "failure.log"
    _ = log.write_text("subprocess timed out after 600s\ntimeout\n", encoding="utf-8")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=step5-review" in out
    assert "MATCHED_CLASSIFIER_PATTERN=transient-output" in out


def test_compose_report_allows_lint_fix_bail_classifier_pattern() -> None:
    # The classifier pattern and the three Step 5 lint-fix bail tokens must all pass the
    # Tier B chat-print sensitive-token allowlist so report rendering does not reject them (issue #4402).
    assert stall_recovery._sensitive_value_is_allowlisted("lint-fix-bail-token")  # pyright: ignore[reportPrivateUsage]
    for token in _LINT_FIX_BAIL_TOKENS:
        assert stall_recovery._sensitive_value_is_allowlisted(token)  # pyright: ignore[reportPrivateUsage]


def test_compose_report_allows_checks_commit_route_retry_resume_hint() -> None:
    assert stall_recovery._sensitive_value_is_allowlisted("checks-commit-route-retry")  # pyright: ignore[reportPrivateUsage]


def _write_state(tmp_path: Path, step: str, phase: str, bail: str = "", extra: str = "") -> None:
    lines = [
        f"PHASE={phase}",
        "STALL_TRACKING=true",
        f"STALL_STEP={step}",
        f"BAIL_REASON={bail}",
        "EXIT_CODE=4",
    ]
    if extra:
        lines.append(extra)
    _ = (tmp_path / "ship-pr-state.sh").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_state_no_exit_code(tmp_path: Path, step: str, phase: str, bail: str = "") -> None:
    lines = [
        f"PHASE={phase}",
        "STALL_TRACKING=true",
        f"STALL_STEP={step}",
        f"BAIL_REASON={bail}",
    ]
    _ = (tmp_path / "ship-pr-state.sh").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_classify_rejects_oversize_failure_detail_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "8", "ci-initial")
    oversize = tmp_path / "oversize.log"
    _ = oversize.write_bytes(b"x" * (65_537))
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(oversize),
    ])
    captured = capsys.readouterr()
    assert rc == 0
    assert "--failure-detail-log exceeds 64KiB" in captured.err
    assert "FAILURE_DETAIL_LOG=" in captured.out
    assert f"FAILURE_DETAIL_LOG={oversize}" not in captured.out


def test_classify_rejects_outside_failure_detail_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "8", "ci-initial")
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        _ = handle.write(b"outside\n")
        outside = handle.name
    try:
        rc = stall_recovery.classify_main([
            "--implement-tmpdir", str(tmp_path),
            "--failure-detail-log", outside,
        ])
        assert rc == 0
        captured = capsys.readouterr()
        assert "--failure-detail-log outside implement tmpdir" in captured.err
    finally:
        Path(outside).unlink(missing_ok=True)


def test_classify_same_cause_repeat_after_record_attempt(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "8", "ci-initial", extra="NOTE=network timeout")
    attempts = tmp_path / "attempts.env"
    assert stall_recovery.init_attempts_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
    ]) == 0
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
    ])
    assert rc == 0
    first = capsys.readouterr().out
    sig = _stdout_kv(first, "FAILURE_SIGNATURE")
    klass = _stdout_kv(first, "FAILURE_CLASS")
    hint = _stdout_kv(first, "RESUME_HINT")
    assert stall_recovery.record_attempt_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
        "--class", klass,
        "--signature", sig,
        "--resume-hint", hint,
        "--outcome", "failed",
    ]) == 0
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=same-cause-repeat" in out
    assert "RESUME_HINT=none" in out


def test_classify_contract_failure_not_promoted_to_same_cause_repeat(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "6", "checks", extra="NOTE=network/auth issue")
    attempts = tmp_path / "attempts.env"
    _ = stall_recovery.init_attempts_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
    ])
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
    ])
    assert rc == 0
    first = capsys.readouterr().out
    sig = _stdout_kv(first, "FAILURE_SIGNATURE")
    _ = stall_recovery.record_attempt_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
        "--class", "contract-failure",
        "--signature", sig,
        "--resume-hint", "none",
        "--outcome", "failed",
    ])
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=contract-failure" in out
    assert "RESUME_HINT=none" in out


def test_classify_without_attempts_file_skips_same_cause_repeat(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "8", "ci-initial", extra="NOTE=network timeout")
    attempts = tmp_path / "stall-recovery-attempts.env"
    _ = attempts.write_text(
        "version=1\nattempt_count=1\nattempt.1.signature=deadbeef\nlast_signature=deadbeef\n",
        encoding="utf-8",
    )
    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "FAILURE_CLASS=same-cause-repeat" not in out


def test_classify_rejects_outside_attempts_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "8", "ci-initial", extra="NOTE=network timeout")
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        _ = handle.write(b"version=1\nattempt_count=0\n")
        outside = handle.name
    try:
        rc = stall_recovery.classify_main([
            "--implement-tmpdir", str(tmp_path),
            "--attempts-file", outside,
        ])
        assert rc == 1
        assert "--attempts-file outside implement tmpdir" in capsys.readouterr().err
    finally:
        Path(outside).unlink(missing_ok=True)


def test_record_attempt_rejects_symlink_attempts_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    real = tmp_path / "real-attempts.env"
    _ = real.write_text("version=1\nattempt_count=0\n", encoding="utf-8")
    link = tmp_path / "attempts.env"
    link.symlink_to(real)
    rc = stall_recovery.record_attempt_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(link),
        "--class", "transient-infra",
        "--signature", "abc",
        "--resume-hint", "step8-shippr",
        "--outcome", "failed",
    ])
    assert rc == 1
    assert "--attempts-file must not be a symlink" in capsys.readouterr().err


def test_init_attempts_rejects_outside_tmpdir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        outside = handle.name
    try:
        rc = stall_recovery.init_attempts_main([
            "--implement-tmpdir", str(tmp_path),
            "--attempts-file", outside,
        ])
        assert rc == 1
        assert "--attempts-file outside implement tmpdir" in capsys.readouterr().err
    finally:
        Path(outside).unlink(missing_ok=True)


def test_classify_rejects_symlinked_ship_pr_state(tmp_path: Path) -> None:
    real = tmp_path / "ship-pr-state.real"
    _ = real.write_text("PHASE=ci-initial\nSTALL_TRACKING=true\nSTALL_STEP=8\nEXIT_CODE=4\n", encoding="utf-8")
    (tmp_path / "ship-pr-state.sh").symlink_to(real)
    assert stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)]) == 3


def test_classify_rejects_malformed_ship_pr_state(tmp_path: Path) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text("not valid\n", encoding="utf-8")
    assert stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)]) == 3


def test_classify_sanitizes_raw_step_phase_dispatcher(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=/secret/phase\nSTALL_TRACKING=true\nSTALL_STEP=/abs/path\n"
        "BAIL_REASON=not-allowlisted\nDISPATCHER=/evil\nEXIT_CODE=abc\n",
        encoding="utf-8",
    )
    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_STEP=unknown" in out
    assert "PHASE=unknown" in out
    assert "DISPATCHER=redacted" in out
    assert "EXIT_CODE=unknown" in out
    assert "BAIL_REASON=redacted" in out


@pytest.mark.parametrize(
    ("state_bail", "argv_bail", "expected_class", "expected_hint", "expected_pattern"),
    [
        ("", "wrapper-validation-failure", "dispatch-failure", "step2-impl", "dispatch-bail-token"),
        ("", "orchestrator-envelope-invalid", "dispatch-failure", "step2-impl", "dispatch-bail-token"),
        ("", "dirty-state-after-timeout", "dispatch-failure", "step2-impl", "dispatch-bail-token"),
        ("protected-path-edit-required-out-of-scope", "", "protected-path", "step2-impl", "protected-path-bail-token"),
        ("", "protected-path-edit-required-out-of-scope", "protected-path", "step2-impl", "protected-path-bail-token"),
        ("submodule-edit-required-out-of-scope", "", "submodule-restricted", "none", "submodule-restricted-bail-token"),
        ("", "submodule-edit-required-out-of-scope", "submodule-restricted", "none", "submodule-restricted-bail-token"),
    ],
)
def test_classify_bail_precedence_tokens(
    state_bail: str,
    argv_bail: str,
    expected_class: str,
    expected_hint: str,
    expected_pattern: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state(tmp_path, "2", "implementation", bail=state_bail, extra="NOTE=network timeout")
    argv = ["--implement-tmpdir", str(tmp_path)]
    if argv_bail:
        argv.extend(["--bail-reason", argv_bail])
    rc = stall_recovery.classify_main(argv)
    assert rc == 0
    out = capsys.readouterr().out
    assert f"FAILURE_CLASS={expected_class}" in out
    assert f"RESUME_HINT={expected_hint}" in out
    assert f"MATCHED_CLASSIFIER_PATTERN={expected_pattern}" in out


def test_compose_report_tier_a_skips_oversize_detail_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    (tmp_path / "skills" / "implement").mkdir(parents=True)
    _ = (tmp_path / "skills" / "implement" / "SKILL.md").write_text("# implement\n", encoding="utf-8")
    detail = tmp_path / "failure.log"
    _ = detail.write_bytes(b"x" * (65_537))
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        f"FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\n"
        f"EXIT_CODE=1\nFAILURE_DETAIL_LOG={detail}\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe summary\n\nProse.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "issue-input",
        "--report-kind", "terminal-failure",
    ])
    assert rc == 0
    body = (tmp_path / "stall-recovery-issue-input.md").read_text(encoding="utf-8")
    assert "## Validated failure-detail log" not in body


def test_compose_report_tier_a_uses_truncated_escalation_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    (tmp_path / "skills" / "implement").mkdir(parents=True)
    _ = (tmp_path / "skills" / "implement" / "SKILL.md").write_text("# implement\n", encoding="utf-8")
    detail = tmp_path / "failure.log"
    _ = detail.write_bytes(
        b"relevant-checks failed\n"
        + (b"x" * stall_recovery.MAX_OPTIONAL_EVIDENCE_BYTES)
    )
    assert stall_recovery.record_escalation_main(_record_escalation_args(tmp_path, str(detail))) == 0
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        f"FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\n"
        f"EXIT_CODE=1\nFAILURE_DETAIL_LOG={detail}\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe summary\n\nProse.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "issue-input",
        "--report-kind", "terminal-failure",
    ])

    assert rc == 0
    body = (tmp_path / "stall-recovery-issue-input.md").read_text(encoding="utf-8")
    assert "## Validated failure-detail log" in body
    assert "relevant-checks failed" in body


def test_normalize_issue_env_dedup_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    issue_out = tmp_path / "issue.out"
    _ = issue_out.write_text(
        "ISSUES_CREATED=0\nISSUES_FAILED=0\nISSUE_1_DUPLICATE_OF_NUMBER=456\n"
        "ISSUE_1_DUPLICATE_OF_URL=https://github.com/example/repo/issues/456\n",
        encoding="utf-8",
    )
    rc = stall_recovery.normalize_issue_env_main([
        "--implement-tmpdir", str(tmp_path),
        "--issue-stdout-file", str(issue_out),
        "--issue-exit-code", "0",
    ])
    assert rc == 0
    assert "NORMALIZED=true" in capsys.readouterr().out
    assert "ISSUE_NUMBER=456" in (tmp_path / "stall-recovery-issue.env").read_text(encoding="utf-8")


def test_normalize_issue_env_dedup_success_accepts_bare_duplicate_url(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    issue_out = tmp_path / "issue.out"
    _ = issue_out.write_text(
        "ISSUES_CREATED=0\nISSUES_FAILED=0\nISSUE_DUPLICATE=1\nISSUE_DUPLICATE_OF_URL=https://github.com/example/repo/issues/456\n",
        encoding="utf-8",
    )
    rc = stall_recovery.normalize_issue_env_main([
        "--implement-tmpdir", str(tmp_path),
        "--issue-stdout-file", str(issue_out),
        "--issue-exit-code", "0",
    ])
    assert rc == 0
    assert "NORMALIZED=true" in capsys.readouterr().out
    assert "ISSUE_NUMBER=456" in (tmp_path / "stall-recovery-issue.env").read_text(encoding="utf-8")


def test_normalize_issue_env_failed_filing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    issue_out = tmp_path / "issue.out"
    _ = issue_out.write_text("ISSUES_FAILED=1\n", encoding="utf-8")
    stale = tmp_path / "stall-recovery-issue.env"
    _ = stale.write_text("ISSUE_NUMBER=1\n", encoding="utf-8")
    rc = stall_recovery.normalize_issue_env_main([
        "--implement-tmpdir", str(tmp_path),
        "--issue-stdout-file", str(issue_out),
        "--issue-exit-code", "0",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "NORMALIZED=false" in captured.out
    assert not stale.exists()


def test_normalize_issue_env_rejects_outside_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as handle:
        _ = handle.write("ISSUES_CREATED=1\nISSUE_1_NUMBER=1\nISSUE_1_URL=https://github.com/x/y/issues/1\n")
        outside = handle.name
    try:
        rc = stall_recovery.normalize_issue_env_main([
            "--implement-tmpdir", str(tmp_path),
            "--issue-stdout-file", outside,
            "--issue-exit-code", "0",
        ])
        assert rc == 1
        assert "--issue-stdout-file outside implement tmpdir" in capsys.readouterr().err
    finally:
        Path(outside).unlink(missing_ok=True)


def test_compose_report_tier_b_create_failure_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("LARCH_STALL_RECOVERY_DRY_RUN", raising=False)
    monkeypatch.setenv("LARCH_STALL_RECOVERY_ENABLE_TEST_FILING", "1")
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=lint fix loop missed retry path\n\nProse.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-bounded-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=lint fix loop missed retry path\n\nBounded.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-sensitive-corpus.env").write_text("safe-token\n", encoding="utf-8")
    chat_path = tmp_path / "chat.md"

    def _fake_emit(tmpdir: Path, out_file: Path, title: str, sensitive_file: Path, prefix: str) -> None:
        _ = (tmpdir, out_file, title, sensitive_file, prefix)
        stall_recovery.emit(key="STALL_RECOVERY_REPORT_STATUS", value="fallback-print-required")
        stall_recovery.emit(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", value="create-failed")

    monkeypatch.setattr(_sr_report, "_emit_chat_print_filing_status", _fake_emit)
    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "chat-print",
        "--report-kind", "terminal-failure",
        "--output-file", str(chat_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_RECOVERY_REPORT_STATUS=fallback-print-required" in out
    assert chat_path.is_file()
    assert "lint fix loop missed retry path" in chat_path.read_text(encoding="utf-8")


def test_validate_terminal_state_rejects_outside_state_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as handle:
        _ = handle.write("DESIGN_FAILURE_VERSION=1\n")
        outside = handle.name
    try:
        ns = argparse.Namespace(
            implement_tmpdir=str(tmp_path),
            primary_state_file=outside,
            profile="generic",
            artifact_prefix="design-failure",
        )
        rc = stall_recovery.validate_terminal_state(ns)
        assert rc == 1
        assert "VALID=false" in capsys.readouterr().out
    finally:
        Path(outside).unlink(missing_ok=True)


def test_validate_tier_b_public_file_rejects_repo_relative_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    corpus = tmp_path / "stall-recovery-sensitive-corpus.env"
    _ = corpus.write_text("other-token\n", encoding="utf-8")
    _ = (tmp_path / "plan.txt").write_text("plan names docs/private-plan.md\n", encoding="utf-8")
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    public = tmp_path / "public.md"
    _ = public.write_text("Bounded finding mentions docs/private-plan.md.\n", encoding="utf-8")
    rc = stall_recovery.validate_tier_b_public_file_main([
        "--implement-tmpdir", str(tmp_path),
        "--public-file", str(public.resolve()),
        "--sensitive-corpus-file", str(corpus.resolve()),
    ])
    assert rc == 1
    assert "PUBLIC_FILE_VALID=false" in capsys.readouterr().out


def test_compose_report_rejects_allowlisted_assignment_in_bounded_body(tmp_path: Path) -> None:
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe\n\nProse.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-bounded-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe\n\nBounded mentions CUSTOMER_SECRET=super-secret-value.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-sensitive-corpus.env").write_text("safe-token\n", encoding="utf-8")
    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "chat-print",
        "--report-kind", "terminal-failure",
        "--output-file", str(tmp_path / "out.md"),
    ])
    assert rc == 1


def test_record_escalation_rejects_symlink_ledger(tmp_path: Path) -> None:
    real = tmp_path / "real-ledger.tsv"
    _ = real.write_text("", encoding="utf-8")
    link = tmp_path / "stall-recovery-escalation-ledger.tsv"
    link.symlink_to(real)
    rc = stall_recovery.record_escalation_main([
        "--implement-tmpdir", str(tmp_path),
        "--site", "step5",
        "--trigger", "main-agent-required",
        "--step", "5",
        "--phase", "review",
        "--dispatcher", "lint-fix-loop",
        "--exit-code", "1",
    ])
    assert rc == 1
    execution = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "Tool Failure: record-escalation" in execution


GHP_TOKEN = "ghp_" + "123456789012345678901234567890123456"


def test_classify_step3_contract_failure_despite_pytest_evidence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "3", "checks", extra="NOTE=pytest failing tests")
    log = tmp_path / "failure.log"
    _ = log.write_text("pytest reports 2 failing tests\n", encoding="utf-8")
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=contract-failure" in out
    assert "MATCHED_CLASSIFIER_PATTERN=step-contract" in out


def test_classify_step6_contract_failure_despite_lint_evidence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "6", "checks", extra="NOTE=shellcheck failed")
    log = tmp_path / "failure.log"
    _ = log.write_text("shellcheck reported errors\n", encoding="utf-8")
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=contract-failure" in out


def test_classify_step3_checks_child_sigterm_retries(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "3", "checks", bail="checks-child-failed")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--in-memory-stall-tracking", "true",
        "--exit-code", "-15",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_TRACKING=true" in out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=checks-commit-route-retry" in out
    assert "MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm" in out
    assert "MATCHED_CLASSIFIER_PATTERN=no-stall" not in out


def test_classify_step3_checks_child_unknown_exit_retries(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state(tmp_path, "3", "checks", bail="checks-child-failed")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--in-memory-stall-tracking", "true",
        "--exit-code", "unknown",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_TRACKING=true" in out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=checks-commit-route-retry" in out
    assert "MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm" in out
    assert "MATCHED_CLASSIFIER_PATTERN=no-stall" not in out


def test_classify_step3_checks_child_positive_exit_stays_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state(tmp_path, "3", "checks", bail="checks-child-failed")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--in-memory-stall-tracking", "true",
        "--exit-code", "1",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=contract-failure" in out
    assert "MATCHED_CLASSIFIER_PATTERN=step-contract" in out


def test_classify_step3_checks_child_positive_exit_without_disk_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state_no_exit_code(tmp_path, "3", "checks", bail="checks-child-failed")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--in-memory-stall-tracking", "true",
        "--stall-step", "3",
        "--phase", "checks",
        "--bail-reason", "checks-child-failed",
        "--exit-code", "1",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=contract-failure" in out
    assert "MATCHED_CLASSIFIER_PATTERN=step-contract" in out
    assert "MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm" not in out


def test_classify_step6_checks_child_sigterm_has_no_retry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state(tmp_path, "6", "checks", bail="checks-child-failed")

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--in-memory-stall-tracking", "true",
        "--exit-code", "-15",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=none" in out
    assert "MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm" in out


def test_classify_test_failure_step8_uses_shippr_resume_hint(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "8", "ci-initial")
    log = tmp_path / "failure.log"
    _ = log.write_text("pytest reports 2 failing tests\n", encoding="utf-8")
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--failure-detail-log", str(log),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=test-failure" in out
    assert "RESUME_HINT=step8-shippr" in out


def _write_bg_wait_marker(tmp_path: Path, *, step: str, pid: int) -> None:
    _ = (tmp_path / ".bg-wait-active").write_text(
        f"PID={pid}\nCLAUDE_PID=1\nSTART_EPOCH=0\nSTEP={step}\nTIMEOUT_S=15600\n",
        encoding="utf-8",
    )


def _dead_pid() -> int:
    with subprocess.Popen(["true"]) as proc:
        _ = proc.wait()
        return proc.pid


def test_classify_step3_abandoned_checks_marker_retries(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_bg_wait_marker(tmp_path, step="implement-step3-checks", pid=_dead_pid())

    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_TRACKING=true" in out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=checks-commit-route-retry" in out
    assert "STALL_STEP=3" in out
    assert "MATCHED_CLASSIFIER_PATTERN=checks-leg-abandoned" in out


def test_classify_step3_live_marker_stays_no_stall(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_bg_wait_marker(tmp_path, step="implement-step3-checks", pid=os.getpid())

    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=unrecoverable" in out
    assert "MATCHED_CLASSIFIER_PATTERN=no-stall" in out


def test_classify_step5_self_review_abandoned_marker_retries_checks_commit_route(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _write_bg_wait_marker(tmp_path, step="implement-step5-self-review", pid=_dead_pid())

    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=checks-commit-route-retry" in out
    assert "STALL_STEP=5" in out
    assert "MATCHED_CLASSIFIER_PATTERN=checks-leg-abandoned" in out


def test_classify_non_checks_marker_stays_no_stall(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_bg_wait_marker(tmp_path, step="implement-step8-ship", pid=_dead_pid())

    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=unrecoverable" in out
    assert "MATCHED_CLASSIFIER_PATTERN=no-stall" in out


def test_classify_dispatch_bail_token_manifest_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_state(tmp_path, "2", "implementation", bail="manifest-missing")
    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=dispatch-failure" in out
    assert "MATCHED_CLASSIFIER_PATTERN=dispatch-bail-token" in out


def test_init_attempts_emits_attempt_kvs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    attempts = tmp_path / "attempts.env"
    rc = stall_recovery.init_attempts_main([
        "--implement-tmpdir", str(tmp_path),
        "--attempts-file", str(attempts),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"ATTEMPTS_FILE={attempts}" in out
    assert "ATTEMPT_COUNT=0" in out


def test_record_escalation_nonwritable_ledger_writes_fallback(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger = tmp_path / "stall-recovery-escalation-ledger.tsv"
    _ = ledger.write_text("", encoding="utf-8")
    ledger.chmod(0o444)
    try:
        rc = stall_recovery.record_escalation_main([
            "--implement-tmpdir", str(tmp_path),
            "--site", "step5",
            "--trigger", "main-agent-required",
            "--step", "5",
            "--phase", "review",
            "--dispatcher", "lint-fix-loop",
            "--exit-code", "1",
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "ESCALATION_RECORDED=false" in out
        assert "ESCALATION_FALLBACK_WRITTEN=true" in out
    finally:
        ledger.chmod(0o644)


def test_record_escalation_sanitizes_dispatcher_metacharacters(tmp_path: Path) -> None:
    rc = stall_recovery.record_escalation_main([
        "--implement-tmpdir", str(tmp_path),
        "--site", "step5",
        "--trigger", "main-agent-required",
        "--step", "5",
        "--phase", "review",
        "--dispatcher", "evil\tdispatcher",
        "--exit-code", "not-a-number",
    ])
    assert rc == 0
    row = (tmp_path / "stall-recovery-escalation-ledger.tsv").read_text(encoding="utf-8")
    assert "dispatcher=redacted" in row
    assert "exit_code=unknown" in row
    assert "\t" not in row.split("dispatcher=")[1].split("\t")[0]


def test_populate_sensitive_corpus_rejects_outside_tmpdir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    outside = tmp_path.parent / "outside-corpus.env"
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    rc = stall_recovery.populate_sensitive_corpus_main([
        "--implement-tmpdir", str(tmp_path),
        "--sensitive-corpus-file", str(outside),
    ])
    assert rc == 1
    assert "--sensitive-corpus-file outside implement tmpdir" in capsys.readouterr().err


def test_dedup_tier_a_report_rejects_outside_body_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as handle:
        _ = handle.write("# body\n")
        outside = handle.name
    try:
        rc = stall_recovery.dedup_tier_a_report_main([
            "--implement-tmpdir", str(tmp_path),
            "--body-file", outside,
        ])
        assert rc == 1
        assert "--body-file outside implement tmpdir" in capsys.readouterr().err
    finally:
        Path(outside).unlink(missing_ok=True)


def test_dedup_tier_a_report_normalizes_helper_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body_file = tmp_path / "stall-recovery-issue-input.md"
    _ = body_file.write_text("# body\n", encoding="utf-8")
    plugin_root = tmp_path / "plugin"
    script_dir = plugin_root / "scripts"
    script_dir.mkdir(parents=True)
    helper = script_dir / "file-failure-report-cross-repo.sh"
    _ = helper.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    issue_url = "https://github.com/owner/repo/issues/6192"

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd and cmd[0] == "gh":
            return subprocess.CompletedProcess(cmd, 0, stdout="owner/repo\n", stderr="")
        stdout = kwargs.get("stdout")
        assert isinstance(stdout, io.TextIOBase)
        _ = stdout.write(
            "FILE_FAILURE_REPORT_STATUS=dedup-comment\n"
            f"FILE_FAILURE_REPORT_URL={issue_url}\n"
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(stall_recovery.subprocess, "run", fake_run)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))

    rc = stall_recovery.dedup_tier_a_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--body-file", str(body_file),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_RECOVERY_REPORT_STATUS=dedup-comment" in out
    assert f"STALL_RECOVERY_REPORT_URL={issue_url}" in out
    assert f"STALL_RECOVERY_REPORT_ISSUE_URL={issue_url}" in out
    assert "STALL_RECOVERY_REPORT_ISSUE_NUMBER=6192" in out
    assert "FILE_FAILURE_REPORT_STATUS=" not in out


def test_dedup_tier_a_report_uses_prefixed_compose_slices(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    monkeypatch.setenv("LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES", "1")
    (tmp_path / "skills" / "implement").mkdir(parents=True)
    _ = (tmp_path / "skills" / "implement" / "SKILL.md").write_text("# implement\n", encoding="utf-8")
    _ = (tmp_path / "design-failure-classification.env").write_text(
        "FAILURE_CLASS=unrecoverable\nFAILURE_SIGNATURE=abc\nSTALL_STEP=judge-panel\nPHASE=judge-panel\n"
        "BAIL_REASON=decompose-panel-retry-exhausted\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "design-failure-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=design summary\n\nProse.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    body_file = tmp_path / "design-failure-issue-input.md"
    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--surface", "issue-input",
        "--report-kind", "terminal-failure",
        "--output-file", str(body_file),
    ])
    assert rc == 0
    prefixed_attempts = tmp_path / "design-failure-tier-a-attempts.md"
    prefixed_escalation = tmp_path / "design-failure-tier-a-escalation.md"
    prefixed_root = tmp_path / "design-failure-tier-a-root-cause.md"
    assert prefixed_attempts.is_file()
    assert prefixed_escalation.is_file()
    assert prefixed_root.is_file()
    _ = (tmp_path / "stall-recovery-tier-a-attempts.md").write_text("", encoding="utf-8")
    _ = (tmp_path / "stall-recovery-tier-a-escalation.md").write_text("", encoding="utf-8")
    _ = (tmp_path / "stall-recovery-tier-a-root-cause.md").write_text("", encoding="utf-8")
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd and cmd[0] == "gh":
            return subprocess.CompletedProcess(cmd, 0, stdout="owner/repo\n", stderr="")
        captured.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(stall_recovery.subprocess, "run", fake_run)
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "")
    rc = stall_recovery.dedup_tier_a_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--body-file", str(body_file),
    ])
    assert rc == 0
    helper_calls = [cmd for cmd in captured if "file-failure-report-cross-repo.sh" in cmd[0]]
    assert len(helper_calls) == 1
    cmd = helper_calls[0]
    assert str(prefixed_attempts) in cmd
    assert str(prefixed_escalation) in cmd
    assert str(prefixed_root) in cmd


def test_redact_text_strips_ghp_token() -> None:
    redacted = stall_recovery._redact_text(f"leaked {GHP_TOKEN} value")  # pyright: ignore[reportPrivateUsage]
    assert redacted is not None
    assert GHP_TOKEN not in redacted


def test_compose_report_redact_text_fails_closed_when_redactor_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe summary\n\nProse.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-bounded-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe summary\n\nBounded.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-sensitive-corpus.env").write_text("safe-token\n", encoding="utf-8")
    monkeypatch.setattr(_sr_report, "_REPO_ROOT", tmp_path / "missing-plugin-root")
    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "chat-print",
        "--report-kind", "terminal-failure",
        "--output-file", str(tmp_path / "chat.md"),
    ])
    assert rc == 1
    out = capsys.readouterr().out
    assert "STALL_RECOVERY_REPORT_STATUS=fallback-print-required" in out
    assert "STALL_RECOVERY_REPORT_FALLBACK_REASON=redactor-failed" in out
    assert not (tmp_path / "chat.md").exists()


def test_compose_report_tier_a_redacts_raw_bail_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    monkeypatch.setenv("LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES", "1")
    (tmp_path / "skills" / "implement").mkdir(parents=True)
    _ = (tmp_path / "skills" / "implement" / "SKILL.md").write_text("# implement\n", encoding="utf-8")
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        f"FAILURE_CLASS=unrecoverable\nFAILURE_SIGNATURE=abc\nSTALL_STEP=8\nPHASE=ship\n"
        f"BAIL_REASON=redacted\nBAIL_REASON_RAW=operator supplied {GHP_TOKEN} during handoff\nEXIT_CODE=4\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe summary\n\nProse.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    out_path = tmp_path / "issue-input.md"
    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "issue-input",
        "--report-kind", "terminal-failure",
        "--output-file", str(out_path),
    ])
    assert rc == 0
    body = out_path.read_text(encoding="utf-8")
    assert GHP_TOKEN not in body
    assert "redacted" in body.lower()


def _compose_terminal_issue_input(tmp_path: Path, *, bail: str = "wrapper-validation-failure", extra_class: str = "") -> str:
    class_lines = [
        "FAILURE_CLASS=lint-failure",
        "FAILURE_SIGNATURE=abcdef",
        "STALL_STEP=5",
        "PHASE=review",
        f"BAIL_REASON={bail}",
        "EXIT_CODE=1",
        "MATCHED_CLASSIFIER_PATTERN=lint-output",
        "DISPATCHER=codex",
    ]
    if extra_class:
        class_lines.append(extra_class)
    _ = (tmp_path / "stall-recovery-classification.env").write_text("\n".join(class_lines) + "\n", encoding="utf-8")
    _ = (tmp_path / "stall-recovery-attempts.env").write_text(
        "version=1\ncreated_utc=2026-01-01T00:00:00Z\nattempt_count=0\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=lint fix loop missed retry path\n\nProse.\n",
        encoding="utf-8",
    )
    (tmp_path / "skills" / "implement").mkdir(parents=True, exist_ok=True)
    _ = (tmp_path / "skills" / "implement" / "SKILL.md").write_text("# implement\n", encoding="utf-8")
    return str(tmp_path)


def test_compose_report_issue_input_preserves_dedup_marker_after_title(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", _compose_terminal_issue_input(tmp_path))
    out_file = tmp_path / "issue-input.md"

    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "issue-input",
        "--report-kind", "terminal-failure",
        "--output-file", str(out_file),
    ])

    stdout = capsys.readouterr().out
    assert rc == 0
    signature = _stdout_kv(stdout, "REPORT_DEDUP_SIGNATURE")
    issue_input = out_file.read_text(encoding="utf-8")
    lines = issue_input.splitlines()
    expected_marker = f"<!-- larch-stall:signature={signature} -->"
    items, parse_mode = issue_create.parse_issue_input(issue_input)

    assert lines[0].startswith("### ")
    assert lines[1] == expected_marker
    assert issue_input.find(expected_marker) > issue_input.find("### ")
    assert parse_mode == "generic"
    assert len(items) == 1
    assert expected_marker in items[0].body


def test_report_dedup_signature_stable_across_excluded_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", _compose_terminal_issue_input(tmp_path))
    rc1 = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "issue-input",
        "--report-kind", "terminal-failure",
        "--output-file", str(tmp_path / "issue-a.md"),
    ])
    sig1 = _stdout_kv(capsys.readouterr().out, "REPORT_DEDUP_SIGNATURE")
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=changed\nSTALL_STEP=5\nPHASE=review\n"
        "BAIL_REASON=wrapper-validation-failure\nEXIT_CODE=99\n"
        "MATCHED_CLASSIFIER_PATTERN=dispatch-output\nDISPATCHER=evil\n",
        encoding="utf-8",
    )
    rc2 = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "issue-input",
        "--report-kind", "terminal-failure",
        "--output-file", str(tmp_path / "issue-b.md"),
    ])
    sig2 = _stdout_kv(capsys.readouterr().out, "REPORT_DEDUP_SIGNATURE")
    assert rc1 == rc2 == 0
    assert sig1 == sig2


def test_report_dedup_signature_differs_generic_vs_implement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", _compose_terminal_issue_input(tmp_path))
    rc_impl = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "issue-input",
        "--report-kind", "terminal-failure",
        "--output-file", str(tmp_path / "issue-impl.md"),
    ])
    sig_impl = _stdout_kv(capsys.readouterr().out, "REPORT_DEDUP_SIGNATURE")
    design = tmp_path / "design"
    design.mkdir()
    state = design / "design-failure-terminal-state.env"
    _ = state.write_text(
        "DESIGN_FAILURE_VERSION=1\n"
        "DESIGN_FAILURE_KIND=terminal\n"
        "FAILURE_OUTCOME=failed-judge-panel\n"
        "STALL_STEP=judge-panel\n"
        "PHASE=judge-panel\n"
        "SITE=decompose-panel\n"
        "TRIGGER=decompose-panel-retry-exhausted\n"
        "BAIL_REASON=decompose-panel-retry-exhausted\n"
        "EXIT_CODE=1\n"
        "FAILURE_DETAIL_LOG=\n"
        "SOURCE_SCRIPT=split-path\n",
        encoding="utf-8",
    )
    _ = (design / "design-failure-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=design summary\n\nProse.\n",
        encoding="utf-8",
    )
    _ = (design / "design-failure-bounded-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=design summary\n\nBounded.\n",
        encoding="utf-8",
    )
    _ = (design / "design-failure-sensitive-corpus.env").write_text("safe-token\n", encoding="utf-8")
    (design / "skills" / "implement").mkdir(parents=True)
    _ = (design / "skills" / "implement" / "SKILL.md").write_text("# implement\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(design))
    _ = stall_recovery.classify_main([
        "--implement-tmpdir", str(design),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--primary-state-file", str(state),
    ])
    _ = capsys.readouterr()
    rc_design = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(design),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--surface", "chat-print",
        "--report-kind", "terminal-failure",
        "--classification-file", str(design / "design-failure-classification.env"),
        "--root-cause-file", str(design / "design-failure-root-cause.md"),
        "--bounded-root-cause-file", str(design / "design-failure-bounded-root-cause.md"),
        "--sensitive-corpus-file", str(design / "design-failure-sensitive-corpus.env"),
        "--output-file", str(design / "design-failure-chat-print.md"),
    ])
    sig_design = _stdout_kv(capsys.readouterr().out, "REPORT_DEDUP_SIGNATURE")
    assert rc_impl == rc_design == 0
    assert sig_impl != sig_design


def test_compose_report_allows_design_dispatcher_in_sensitive_corpus() -> None:
    assert stall_recovery._sensitive_value_is_allowlisted("design-step3-review")  # pyright: ignore[reportPrivateUsage]
    assert stall_recovery._sensitive_value_is_allowlisted("dispatch-bail-token")  # pyright: ignore[reportPrivateUsage]


def test_validate_token_accepts_implement_bail_tokens(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for token in ("dirty-tree", "ci-local-unfixable:lint_1,test-2"):
        rc = stall_recovery.validate_token_main([
            "--implement-tmpdir", str(tmp_path),
            "--token-kind", "bail",
            "--value", token,
        ])
        assert rc == 0
        assert "TOKEN_VALID=true" in capsys.readouterr().out


def test_classify_generic_without_primary_state_file_uses_prefixed_terminal_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = tmp_path / "design-failure-terminal-state.env"
    _ = state.write_text(
        "DESIGN_FAILURE_VERSION=1\n"
        "DESIGN_FAILURE_KIND=terminal\n"
        "FAILURE_OUTCOME=failed-judge-panel\n"
        "STALL_STEP=judge-panel\n"
        "PHASE=judge-panel\n"
        "SITE=decompose-panel\n"
        "TRIGGER=decompose-panel-retry-exhausted\n"
        "BAIL_REASON=decompose-panel-retry-exhausted\n"
        "EXIT_CODE=1\n"
        "FAILURE_DETAIL_LOG=\n"
        "SOURCE_SCRIPT=split-path\n",
        encoding="utf-8",
    )
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DISPATCHER=split-path" in out
    assert (tmp_path / "design-failure-classification.env").is_file()


def test_classify_generic_uses_prefixed_failure_detail_log_sidecar(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    oversize = tmp_path / "generic-oversize.log"
    _ = oversize.write_bytes(
        b"relevant-checks failed\n"
        + (b"x" * stall_recovery.MAX_OPTIONAL_EVIDENCE_BYTES)
    )
    assert stall_recovery.record_escalation_main([
        "--implement-tmpdir", str(tmp_path),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--site", "decompose-panel",
        "--trigger", "decompose-panel-retry-exhausted",
        "--step", "judge-panel",
        "--phase", "judge-panel",
        "--dispatcher", "split-path",
        "--exit-code", "1",
        "--failure-detail-log", str(oversize),
    ]) == 0
    fields = dict(
        part.split("=", 1)
        for part in (tmp_path / "design-failure-escalation-ledger.tsv").read_text(encoding="utf-8").strip().split("\t")
    )
    sidecar = tmp_path / fields["failure_detail_log"]
    state = tmp_path / "design-failure-terminal-state.env"
    _ = state.write_text(
        "DESIGN_FAILURE_VERSION=1\n"
        "DESIGN_FAILURE_KIND=terminal\n"
        "FAILURE_OUTCOME=failed-judge-panel\n"
        "STALL_STEP=judge-panel\n"
        "PHASE=judge-panel\n"
        "SITE=decompose-panel\n"
        "TRIGGER=decompose-panel-retry-exhausted\n"
        "BAIL_REASON=decompose-panel-retry-exhausted\n"
        "EXIT_CODE=1\n"
        f"FAILURE_DETAIL_LOG={oversize}\n"
        "SOURCE_SCRIPT=split-path\n",
        encoding="utf-8",
    )
    _ = capsys.readouterr()

    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
    ])

    captured = capsys.readouterr()
    assert rc == 0
    assert "FAILURE_CLASS=lint-failure" in captured.out
    assert f"FAILURE_DETAIL_LOG={sidecar.resolve()}" in captured.out
    assert f"FAILURE_DETAIL_LOG={oversize}" not in captured.out


def test_classify_rejects_invalid_artifact_prefix(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.classify_main([
        "--implement-tmpdir", str(tmp_path),
        "--profile", "generic",
        "--artifact-prefix", "../leak",
    ])
    assert rc == 2
    assert "simple dash token" in capsys.readouterr().err


def test_main_accepts_global_flags_before_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "design-failure-terminal-state.env"
    _ = state.write_text(
        "DESIGN_FAILURE_VERSION=1\n"
        "DESIGN_FAILURE_KIND=terminal\n"
        "FAILURE_OUTCOME=failed-judge-panel\n"
        "STALL_STEP=judge-panel\n"
        "PHASE=judge-panel\n"
        "SITE=decompose-panel\n"
        "TRIGGER=decompose-panel-retry-exhausted\n"
        "BAIL_REASON=decompose-panel-retry-exhausted\n"
        "EXIT_CODE=1\n"
        "FAILURE_DETAIL_LOG=\n"
        "SOURCE_SCRIPT=split-path\n",
        encoding="utf-8",
    )
    rc = stall_recovery.main([
        "--profile", "generic",
        "--artifact-prefix", "design-failure",
        "--implement-tmpdir", str(tmp_path),
        "classify",
    ])
    assert rc == 0
    assert "DISPATCHER=split-path" in capsys.readouterr().out


def test_normalize_issue_env_rejects_missing_issues_failed_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    issue_out = tmp_path / "issue.out"
    _ = issue_out.write_text(
        "ISSUE_1_NUMBER=12\nISSUE_1_URL=https://github.com/o/r/issues/12\n",
        encoding="utf-8",
    )
    rc = stall_recovery.normalize_issue_env_main([
        "--implement-tmpdir", str(tmp_path),
        "--issue-stdout-file", str(issue_out),
        "--issue-exit-code", "0",
    ])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "NORMALIZED=false" in captured
    assert "REASON=issues-failed-invalid" in captured


def test_normalize_issue_env_filters_disallowed_stdout_keys(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    issue_out = tmp_path / "issue.out"
    _ = issue_out.write_text(
        "SECRET_TOKEN=leak\nISSUES_FAILED=0\nISSUE_1_NUMBER=12\n"
        "ISSUE_1_URL=https://github.com/o/r/issues/12\n",
        encoding="utf-8",
    )
    rc = stall_recovery.normalize_issue_env_main([
        "--implement-tmpdir", str(tmp_path),
        "--issue-stdout-file", str(issue_out),
        "--issue-exit-code", "0",
    ])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "NORMALIZED=true" in captured
    assert "ISSUE_NUMBER=12" in (tmp_path / "stall-recovery-issue.env").read_text(encoding="utf-8")


def test_chat_print_delegates_to_compose_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_STALL_RECOVERY_DRY_RUN", "1")
    _ = (tmp_path / "stall-recovery-classification.env").write_text(
        "FAILURE_CLASS=lint-failure\nFAILURE_SIGNATURE=abc\nSTALL_STEP=5\nPHASE=review\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe summary\n\nProse.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-bounded-root-cause.md").write_text(
        "verdict=larch-defect\nconfidence=high\nsummary=safe summary\n\nBounded.\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "stall-recovery-sensitive-corpus.env").write_text("safe-token\n", encoding="utf-8")
    out_path = tmp_path / "stall-recovery-chat-print.md"
    rc = stall_recovery.chat_print_main([
        "--implement-tmpdir", str(tmp_path),
        "--report-kind", "terminal-failure",
        "--output-file", str(out_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STALL_RECOVERY_REPORT_KIND=terminal-failure" in out
    assert out_path.is_file()
