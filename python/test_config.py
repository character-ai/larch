"""Tests for config.py constants."""

from __future__ import annotations

import config


def test_fixer_tier_order() -> None:
    assert config.FIXER_TIER_ORDER == ("codex", "cursor", "claude")


def test_ship_pr_pre_push_handoff_literals() -> None:
    assert config.SHIP_PR_RRR_RESUME_PHASE == "ship-pr-rrr-phase14"
    assert config.SHIP_PR_PRE_PUSH_CALLER_KIND == "ship_pr_pre_push"
    assert (
        config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
        == "ship-pr-rrr-after-phase14.flag"
    )


def test_retry_backoff_immutable() -> None:
    assert config.TRANSIENT_RETRY_BACKOFF_SEC == (2, 4)


def test_documented_constants_exist() -> None:
    names = (
        "EXIT_OK",
        "EXIT_TIMEOUT",
        "SUBPROCESS_DEFAULT_TIMEOUT_SEC",
        "TRANSIENT_RETRY_MAX_ATTEMPTS",
        "ENV_LARCH_SHIP_PR_IMPL",
        "PATH_MANIFEST_TEMPLATE",
    )
    for name in names:
        assert hasattr(config, name)


def test_exit_stall_removed_bail_kept() -> None:
    assert not hasattr(config, "EXIT_STALL")
    assert config.EXIT_BAIL == 4
