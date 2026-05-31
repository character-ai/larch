"""Tests for config.py constants."""

from __future__ import annotations

import config


def test_fixer_tier_order() -> None:
    assert config.FIXER_TIER_ORDER == ("cursor", "codex", "claude")


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
