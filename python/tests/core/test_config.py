"""Tests for config.py constants."""

from __future__ import annotations

from larch.core import config


def test_fixer_tier_order() -> None:
    assert config.FIXER_TIER_ORDER == ("codex", "cursor", "claude")
    assert config.CLAUDE_CI_FIX_MODEL == "claude-opus-4-8"
    assert config.FIXER_LANE_TIMEOUT_SEC == 1800
    assert config.FIXER_TIER_ACTION_SELECTED == "selected"
    assert config.FIXER_TIER_ACTION_UNAVAILABLE == "unavailable"
    assert config.FIXER_TIER_ACTION_EXHAUSTED == "exhausted"
    assert config.FIXER_TIER_ACTIONS == (
        config.FIXER_TIER_ACTION_SELECTED,
        config.FIXER_TIER_ACTION_UNAVAILABLE,
        config.FIXER_TIER_ACTION_EXHAUSTED,
    )
    assert config.FIXER_TIER_FAIL_REASON_UNAVAILABLE == "unavailable"
    assert config.FIXER_TIER_FAIL_REASON_EXHAUSTED == "exhausted"
    assert config.FIXER_TIER_FAIL_REASONS == (
        config.FIXER_TIER_FAIL_REASON_UNAVAILABLE,
        config.FIXER_TIER_FAIL_REASON_EXHAUSTED,
    )


def test_ship_pr_pre_push_handoff_literals() -> None:
    assert config.SHIP_PR_RRR_RESUME_PHASE == "ship-pr-rrr-phase14"
    assert config.SHIP_PR_PRE_PUSH_CALLER_KIND == "ship_pr_pre_push"
    assert (
        config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
        == "ship-pr-rrr-after-phase14.flag"
    )


def test_retry_backoff_immutable() -> None:
    assert config.TRANSIENT_RETRY_BACKOFF_SEC == (2, 4)


def test_release_commit_subject_template_is_canonical() -> None:
    assert config.BUMP_COMMIT_SUBJECT_TEMPLATE == "Release v{version}"


def test_post_fix_empty_checks_grace_is_bounded() -> None:
    # Must be > 0 so a missing post-fix CI run surfaces as NO_CHECKS instead of
    # polling "pending" for the full budget (issue #4867), and shorter than the
    # full poll timeout so the bounded window is actually a shortcut.
    assert config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC > 0
    assert config.CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC < config.CI_WAIT_TIMEOUT_SEC


def test_live_mutation_auth_literals() -> None:
    assert config.LIVE_MUTATION_AUTH_KEY == "LARCH_LIVE_MUTATION_OK"
    assert config.LIVE_MUTATION_TEST_DENY_KEY == "LARCH_ISSUE_MUTATION_DENY"
    assert config.LIVE_MUTATION_OPERATOR_MODE == "operator"
    assert config.LIVE_MUTATION_SESSION_MODE == "session"
    assert config.LIVE_MUTATION_REFUSAL_STATUS == "mutation-refused"
    assert config.LIVE_MUTATION_REFUSAL_REASON == "unauthorized-mutation"
    assert config.EXIT_MUTATION_REFUSED == 5


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


def test_refresh_skip_pre_rebase_flush_commit_failed_fails_closed() -> None:
    # commit-failed is tolerated as a generic pre-merge flush skip, but the
    # pre-rebase / post-ensure merge gates must fail closed on it so a squash-merge
    # cannot carry a stale log snapshot (issue #4930, NEVER #16).
    assert config.REFRESH_SKIP_COMMIT_FAILED in config.REFRESH_SKIP_MERGE_OK
    assert config.REFRESH_SKIP_COMMIT_FAILED not in config.REFRESH_SKIP_POST_ENSURE_PR_OK
    assert config.REFRESH_SKIP_PRETERMINAL_OUTCOME in config.REFRESH_SKIP_MERGE_OK
    assert config.REFRESH_SKIP_PRETERMINAL_OUTCOME not in config.REFRESH_SKIP_POST_ENSURE_PR_OK


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
    assert config.REVIEW_CHANGE_DETECTION_FAILED == "review-change-detection-failed"
    assert config.REVIEW_CHANGE_DETECTION_FAILED in config.STALL_RECOVERY_BAIL_REASON_TOKENS
    assert "quota" in config.STALL_RECOVERY_BAIL_REASON_TOKENS


def test_exit_stall_removed_bail_kept() -> None:
    assert not hasattr(config, "EXIT_STALL")
    assert config.EXIT_BAIL == 4


def test_cursor_implement_model_by_difficulty() -> None:
    assert config.CURSOR_DEFAULT_MODEL == "composer-2.5"
    assert set(config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY) == set(config.DIFFICULTY_TIERS)
    assert (
        config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_TRIVIAL]
        == config.CURSOR_GROK_4_5_HIGH_MODEL
    )
    assert (
        config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_HARD]
        == config.CURSOR_DEFAULT_MODEL
    )
    assert (
        config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_MODERATE]
        == "cursor-grok-4.5-high"
    )


def test_coder_and_codex_implement_routing_by_difficulty() -> None:
    assert config.CODER_TOOL_ORDER_BY_DIFFICULTY[config.DIFFICULTY_TIER_TRIVIAL] == (
        "cursor",
        "codex",
        "claude",
    )
    assert config.CODEX_DEFAULT_MODEL == "gpt-5.6-sol"
    assert config.CODEX_IMPLEMENT_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_MODERATE] == config.CODEX_TERRA_MODEL
    assert config.CODEX_IMPLEMENT_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_HARD] == config.CODEX_TERRA_MODEL
    assert config.CODEX_REVIEW_PANEL_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_MODERATE] == config.CODEX_TERRA_MODEL
    assert config.CODEX_REVIEW_PANEL_MODEL_BY_DIFFICULTY[config.DIFFICULTY_TIER_HARD] == config.CODEX_TERRA_MODEL
