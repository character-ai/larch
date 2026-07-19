"""Transient network retry helpers."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from larch.core import config

T = TypeVar("T")

Sleeper = Callable[[float], None]


def default_sleeper(seconds: float) -> None:
    time.sleep(seconds)


def is_transient_net_signature(text: str) -> bool:
    """Classify stderr/stdout blobs for transient network failures."""
    if "no such hosted" in text or "no such hostname" in text:
        return False
    if "Could not resolve" in text:
        return True
    if "unable to access" in text:
        return True
    if "Connection refused" in text:
        return True
    if "Temporary failure" in text:
        return True
    if "timed out" in text:
        return True
    if "TLS handshake" in text:
        return True
    if "HTTP 5" in text:
        return True
    if "network/auth issue" in text:
        return True
    if "connection reset" in text:
        return True
    if "Connection reset by peer" in text:
        return True
    if (
        "EOF" in text
        and "during" in text
        and text.index("EOF") < text.index("during")
    ):
        return True
    if "context deadline exceeded" in text:
        return True
    if text == "ci-status-stale":
        return True
    if "no valid output 3 times" in text:
        return True
    if (
        "git fetch" in text
        and "failed" in text
        and text.index("git fetch") < text.index("failed")
    ):
        return True
    if (
        "lookup" in text
        and "no such host" in text
        and text.index("lookup") < text.index("no such host")
    ):
        return True
    return "no such host" in text


@dataclass(frozen=True)
class RetryResult(Generic[T]):
    value: T
    attempts: int
    last_returncode: int = 0


def with_transient_retry(
    fn: Callable[[], tuple[T, int, str]],
    *,
    predicate: Callable[[str], bool] | None = None,
    sleeper: Sleeper = default_sleeper,
    max_attempts: int = config.TRANSIENT_RETRY_MAX_ATTEMPTS,
) -> RetryResult[T]:
    """Retry fn up to max_attempts when predicate(content) or transient signature.

    fn returns (value, returncode, combined_output).
    """
    pred: Callable[[str], bool] = predicate or (lambda _content: False)
    for attempt in range(1, max_attempts + 1):
        value, rc, content = fn()
        transient = pred(content)
        if not transient and rc != 0 and is_transient_net_signature(content):
            transient = True
        if not transient:
            return RetryResult(value=value, attempts=attempt, last_returncode=rc)
        if attempt >= max_attempts:
            return RetryResult(value=value, attempts=attempt, last_returncode=rc)
        backoff_index = min(attempt - 1, len(config.TRANSIENT_RETRY_BACKOFF_SEC) - 1)
        backoff = config.TRANSIENT_RETRY_BACKOFF_SEC[backoff_index]
        sleeper(float(backoff))
    raise AssertionError("loop totality")
