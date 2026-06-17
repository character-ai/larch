from pathlib import Path

import argparse
import pytest

import stall_recovery


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
    assert "FAILURE_CLASS=protected-path" in out
    assert "RESUME_HINT=step2-impl" in out
    assert "MATCHED_CLASSIFIER_PATTERN=protected-path-bail-token" in out


def test_record_escalation_writes_canonical_ledger(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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
    assert "ESCALATION_RECORDED=true" in capsys.readouterr().out
    assert "site=step5" in (tmp_path / "stall-recovery-escalation-ledger.tsv").read_text(encoding="utf-8")


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


def test_record_attempt_writes_count(tmp_path: Path) -> None:
    rc = stall_recovery.record_attempt_main([
        "--implement-tmpdir", str(tmp_path),
        "--class", "transient-infra",
        "--signature", "abc",
        "--outcome", "failed",
    ])
    assert rc == 0
    assert "attempt_count=1" in (tmp_path / "stall-recovery-attempts.env").read_text(encoding="utf-8")


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
    assert "EXIT_CODE=4" in text
    assert "BAIL_REASON=adopted-issue-closed" in text
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


_LINT_FIX_BAIL_TOKENS = ("lint-fix-failed", "lint-fix-attempt-cap", "lint-fix-main-agent-required")

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
    assert "RESUME_HINT=step8-shippr" in out
    assert "MATCHED_CLASSIFIER_PATTERN=transient-output" in out


def test_compose_report_allows_lint_fix_bail_classifier_pattern() -> None:
    # The classifier pattern and the three Step 5 lint-fix bail tokens must all pass the
    # Tier B chat-print sensitive-token allowlist so report rendering does not reject them (issue #4402).
    assert stall_recovery._sensitive_value_is_allowlisted("lint-fix-bail-token")  # pyright: ignore[reportPrivateUsage]
    for token in _LINT_FIX_BAIL_TOKENS:
        assert stall_recovery._sensitive_value_is_allowlisted(token)  # pyright: ignore[reportPrivateUsage]
