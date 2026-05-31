"""Tests for agents.py classification and waterfall."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import agents
import config
from agents import LaunchFailure, TierAttempt

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB_COMMON = REPO_ROOT / "scripts" / "lib-external-launcher-common.sh"


def _bash_classify(*args: str) -> tuple[str, str]:
    script = f'source "{LIB_COMMON}"\nexternal_classify_launch_failure "$@"\n'
    proc = subprocess.run(
        ["bash", "-c", script, "bash", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    cls = ""
    reason = ""
    for line in proc.stdout.splitlines():
        if line.startswith("LAUNCHER_FAILURE_CLASS="):
            cls = line.split("=", 1)[1]
        if line.startswith("LAUNCHER_FAILURE_REASON="):
            reason = line.split("=", 1)[1]
    return cls, reason


def test_classify_success() -> None:
    failure = agents.classify_launch_failure(0)
    assert failure == LaunchFailure("none", "")


def test_classify_timeout() -> None:
    failure = agents.classify_launch_failure(config.EXIT_TIMEOUT)
    assert failure.failure_class == "other"
    assert failure.reason == "timeout"


@pytest.mark.skipif(
    not LIB_COMMON.is_file() or shutil.which("bash") is None,
    reason="bash or lib-external-launcher-common.sh unavailable",
)
def test_parity_classify_timeout() -> None:
    py = agents.classify_launch_failure(124)
    bash_cls, bash_reason = _bash_classify("124", "/dev/null", "non-auth", "1", "cursor", "")
    assert py.failure_class == bash_cls
    assert py.reason == bash_reason


def test_build_launch_argv_cursor() -> None:
    argv = agents.build_launch_argv(
        "cursor",
        role="fix",
        output="/tmp/out",
        run_id="run",
        repo="o/r",
    )
    assert argv[0] == "scripts/launch-cursor-ci.sh"
    assert "--role" in argv


def test_waterfall_short_circuits_on_first_other() -> None:
    tiers = list(config.FIXER_TIER_ORDER)

    def launch_fn(tier: str) -> TierAttempt:
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("other", "unknown"),
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier=tiers[0])
    assert result.winning_tier is None
    assert result.short_circuited is True
    assert len(result.attempts) == 1


def test_waterfall_falls_through_health() -> None:
    tiers = list(config.FIXER_TIER_ORDER)
    calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        calls.append(tier)
        if tier == tiers[-1]:
            return TierAttempt(
                tier=tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            )
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("health", "auth"),
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier=tiers[0])
    assert result.winning_tier == tiers[-1]
    assert len(calls) == len(tiers)
