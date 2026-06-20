"""Tests for config.py constants."""

from __future__ import annotations

import config


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


def test_documented_constants_exist() -> None:
    names = (
        "EXIT_OK",
        "EXIT_TIMEOUT",
        "SUBPROCESS_DEFAULT_TIMEOUT_SEC",
        "TRANSIENT_RETRY_MAX_ATTEMPTS",
        "PATH_MANIFEST_TEMPLATE",
    )
    for name in names:
        assert hasattr(config, name)


def test_exit_stall_removed_bail_kept() -> None:
    assert not hasattr(config, "EXIT_STALL")
    assert config.EXIT_BAIL == 4
