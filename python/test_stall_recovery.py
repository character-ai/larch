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
        "STALL_STEP=rebase-failed\nPHASE=rebase-failed\nBAIL_REASON=\nEXIT_CODE=1\n",
        encoding="utf-8",
    )
    rc = stall_recovery.classify_main(["--implement-tmpdir", str(tmp_path), "--stall-step", "rebase-failed"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FAILURE_CLASS=transient-infra" in out
    assert "RESUME_HINT=step8-shippr" in out


def test_classify_ci_fix_exhausted_with_detail_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "ship-pr-state.sh").write_text(
        "STALL_STEP=8\nPHASE=ci-merge\nBAIL_REASON=ci-fix-exhausted\nEXIT_CODE=2\n",
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
    assert "FAILURE_CLASS=ci-fix-exhausted" in out


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


def test_compose_report_python_impl(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    rc = stall_recovery.compose_report_main([
        "--implement-tmpdir", str(tmp_path),
        "--surface", "chat-print",
        "--report-kind", "terminal-failure",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[Bug] /implement terminal:" in out
    assert "STALL_RECOVERY_REPORT_STATUS=printed" in out
    assert "REPORT_DEDUP_SIGNATURE=" in out


def test_lint_subcommand_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = stall_recovery.lint_main([])
    assert rc == 0
    assert "LINT_OK=true" in capsys.readouterr().out
