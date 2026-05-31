"""Tests for retry.py including bash parity on signatures."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import config
import retry

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB_NET = REPO_ROOT / "scripts" / "lib-net.sh"


def _bash_is_transient(text: str) -> bool:
    script = (
        f'source "{LIB_NET}"\n'
        'if is_transient_net_signature "$1"; then echo yes; else echo no; fi\n'
    )
    proc = subprocess.run(
        ["bash", "-c", script, "bash", text],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() == "yes"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Could not resolve host: api.github.com", True),
        ("repository has no such hosted zone configured", False),
        ("could not resolve: no such hostname in registry", False),
        ("permission denied", False),
    ],
)
def test_is_transient_net_signature(text: str, expected: bool) -> None:
    assert retry.is_transient_net_signature(text) is expected


@pytest.mark.skipif(
    not LIB_NET.is_file() or shutil.which("bash") is None,
    reason="bash or lib-net.sh unavailable",
)
@pytest.mark.parametrize(
    "text",
    [
        "Could not resolve host: api.github.com",
        "fatal: unable to access 'https://github.com/x/y.git/': Failed to connect",
        "dial tcp: lookup foo.example: no such host",
        "failed during EOF cleanup",
        "failed after git fetch",
    ],
)
def test_parity_is_transient_net_signature(text: str) -> None:
    assert retry.is_transient_net_signature(text) == _bash_is_transient(text)


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


def test_with_transient_retry_reuses_last_backoff() -> None:
    sleeps: list[float] = []
    attempts = {"n": 0}

    def fn() -> tuple[str, int, str]:
        attempts["n"] += 1
        return "", 1, "fatal: Could not resolve host"

    result = retry.with_transient_retry(fn, sleeper=sleeps.append, max_attempts=4)
    assert result.attempts == 4
    assert sleeps == [2.0, 4.0, 4.0]
