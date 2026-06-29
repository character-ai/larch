"""Tests for retry.py including bash parity on signatures."""

from __future__ import annotations

import pytest

from larch.core import config
from larch.core import retry

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Could not resolve host: api.github.com", True),
        ("fatal: unable to access 'https://github.com/x/y.git/': Failed to connect", True),
        ("dial tcp: Connection refused", True),
        ("Temporary failure in name resolution", True),
        ("operation timed out while dialing", True),
        ("TLS handshake failure", True),
        ("HTTP 502 Bad Gateway", True),
        ("EOF during request body write", True),
        ("context deadline exceeded", True),
        ("ci-status-stale", True),
        ("ci-status.sh returned no valid output 3 times consecutively", True),
        ("git fetch origin main failed (network/auth issue)", True),
        ("lookup api.github.com: no such host", True),
        ("dial tcp: lookup foo.example: no such host", True),
        ("read tcp 10.0.0.1:443: Connection reset by peer", True),
        ("repository has no such hosted zone configured", False),
        ("could not resolve: no such hostname in registry", False),
        ("lookup api.github.com: server misbehaving", False),
        ("TLS alert: peer reset notification without connection-reset phrase", False),
        ("", False),
        ("permission denied", False),
    ],
)
def test_is_transient_net_signature(text: str, expected: bool) -> None:
    assert retry.is_transient_net_signature(text) is expected




@pytest.mark.parametrize(
    "text",
    [
        "during request: unexpected EOF",
        "failed before git fetch",
    ],
)
def test_ordered_substrings_reversed_do_not_match(text: str) -> None:
    assert retry.is_transient_net_signature(text) is False




def test_with_transient_retry_backoff_schedule() -> None:
    sleeps: list[float] = []

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)

    attempts = {"n": 0}

    def fn() -> tuple[str, int, str]:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return "", 1, "fatal: Could not resolve host"
        return "ok", 0, ""

    result = retry.with_transient_retry(fn, sleeper=sleeper)
    assert result.value == "ok"
    assert result.attempts == 3
    assert sleeps == [
        float(config.TRANSIENT_RETRY_BACKOFF_SEC[0]),
        float(config.TRANSIENT_RETRY_BACKOFF_SEC[1]),
    ]


def test_with_transient_retry_predicate_branch() -> None:
    sleeps: list[float] = []
    attempts = {"n": 0}

    def fn() -> tuple[str, int, str]:
        attempts["n"] += 1
        if attempts["n"] < 2:
            return "", 1, "permission denied"
        return "ok", 0, ""

    result = retry.with_transient_retry(
        fn,
        predicate=lambda text: "permission denied" in text,
        sleeper=sleeps.append,
        max_attempts=3,
    )
    assert result.value == "ok"
    assert result.attempts == 2
    assert sleeps == [float(config.TRANSIENT_RETRY_BACKOFF_SEC[0])]


def test_with_transient_retry_reuses_last_backoff() -> None:
    sleeps: list[float] = []
    attempts = {"n": 0}

    def fn() -> tuple[str, int, str]:
        attempts["n"] += 1
        return "", 1, "fatal: Could not resolve host"

    result = retry.with_transient_retry(fn, sleeper=sleeps.append, max_attempts=4)
    assert result.attempts == 4
    assert sleeps == [2.0, 4.0, 4.0]
