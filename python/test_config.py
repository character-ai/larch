"""Tests for config.py constants."""

from __future__ import annotations

from larch.core import config


def test_fixer_tier_order() -> None:
    assert config.FIXER_TIER_ORDER == ("claude", "codex", "cursor")
    assert config.CLAUDE_CI_FIX_MODEL == "claude-opus-4-8"
    assert config.CI_AGENTIC_FIX_MAX_CYCLES == 20


def test_ship_pr_pre_push_handoff_literals() -> None:
    assert config.SHIP_PR_RRR_RESUME_PHASE == "ship-pr-rrr-phase14"
    assert config.SHIP_PR_PRE_PUSH_CALLER_KIND == "ship_pr_pre_push"
    assert (
        config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
        == "ship-pr-rrr-after-phase14.flag"
    )


def test_retry_backoff_immutable() -> None:
    assert config.TRANSIENT_RETRY_BACKOFF_SEC == (2, 4)


def test_post_fix_empty_checks_grace_is_bounded() -> None:
    # Must be > 0 so a missing post-fix CI run surfaces as NO_CHECKS instead of
    # polling "pending" for the full budget (issue #4867), and shorter than the
    # full poll timeout so the bounded window is actually a shortcut.
    assert config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC > 0
    assert config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC < config.CI_WAIT_TIMEOUT_SEC


def test_initial_empty_checks_grace_is_ship_startup_deadline() -> None:
    assert config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC == 300
    assert (
        config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC
        > config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC
    )
    assert config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC < config.CI_WAIT_TIMEOUT_SEC


def test_default_empty_checks_grace_is_bounded() -> None:
    # The manual `ci status` / `ci wait` default must be > 0 so a runless head
    # surfaces as NO_CHECKS within the window instead of polling the full budget
    # (issue #4924), and shorter than the full poll timeout.
    assert config.CI_WAIT_EMPTY_CHECKS_GRACE_SEC == 120
    assert 0 < config.CI_WAIT_EMPTY_CHECKS_GRACE_SEC < config.CI_WAIT_TIMEOUT_SEC


def test_ci_status_query_timeout_is_bounded() -> None:
    # The poll-time gh status query timeout must be > 0 so a hung read is bounded
    # (issue #5066), and dedicated/shorter than the full subprocess + wait budgets
    # so one hung query cannot consume the whole poll budget.
    assert config.CI_STATUS_QUERY_TIMEOUT_SEC == 120
    assert 0 < config.CI_STATUS_QUERY_TIMEOUT_SEC < config.SUBPROCESS_DEFAULT_TIMEOUT_SEC
    assert config.CI_STATUS_QUERY_TIMEOUT_SEC < config.CI_WAIT_TIMEOUT_SEC


def test_pre_rebase_flush_commit_failed_fails_closed() -> None:
    # commit-failed is tolerated as a generic pre-merge flush skip, but the
    # pre-rebase / post-ensure merge gates must fail closed on it so a squash-merge
    # cannot carry a stale log snapshot (issue #4930, NEVER #16).
    assert config.REFRESH_SKIP_COMMIT_FAILED in config.REFRESH_SKIP_MERGE_OK
    assert config.REFRESH_SKIP_COMMIT_FAILED not in config.REFRESH_SKIP_POST_ENSURE_PR_OK


def test_documented_constants_exist() -> None:
    names = (
        "EXIT_OK",
        "EXIT_TIMEOUT",
        "SUBPROCESS_DEFAULT_TIMEOUT_SEC",
        "TRANSIENT_RETRY_MAX_ATTEMPTS",
        "PATH_MANIFEST_TEMPLATE",
        "ENV_LARCH_EXEC_ISSUE_ASSESSMENT_MODEL",
        "EXEC_ISSUE_ASSESSMENT_MODEL_DEFAULT",
    )
    for name in names:
        assert hasattr(config, name)


def test_implement_step4_and_post_dispatch_literals() -> None:
    assert config.POST_DISPATCH_NEXT_CONTINUE == "continue"
    assert config.POST_DISPATCH_NEXT_BAIL == "bail"
    assert config.POST_DISPATCH_BAIL_MAIN_BRANCH == "main-branch-post-dispatch"
    assert config.BAIL_REASON_RECOVERY_OUT_OF_SCOPE == "recovery-out-of-scope"
    assert config.IMPLEMENTATION_COMMIT_FAILED == "implementation-commit-failed"
    assert config.IMPLEMENTATION_COMMIT_FAILED in config.STALL_RECOVERY_BAIL_REASON_TOKENS


def test_exit_stall_removed_bail_kept() -> None:
    assert not hasattr(config, "EXIT_STALL")
    assert config.EXIT_BAIL == 4
