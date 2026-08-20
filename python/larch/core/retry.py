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


_NETWORK_UNREACHABLE_SIGNATURES = (
    "could not resolve host",
    "could not resolve hostname",
    "couldn't resolve host",
    "temporary failure in name resolution",
    "name or service not known",
    "connection refused",
    "connection reset",
    "connection timed out",
    "operation timed out",
    "failed to connect to",
    "couldn't connect to server",
    "network is unreachable",
    "no route to host",
    "unable to look up",
)


def is_network_unreachable_signature(text: str) -> bool:
    """Classify stderr/stdout as a network-unreachable failure: the request never
    reached the server (DNS failure, connect timeout, or a refused or reset
    connection).

    Narrower than :func:`is_transient_net_signature`: it deliberately excludes
    HTTP-level failures (4xx/5xx) and read timeouts on a live connection, mirroring
    the Rust adapter's ``Unreachable`` classification. Offline-aware push and merge
    retry only this class so HTTP-level failures stay fail-closed.
    """
    lowered = text.lower()
    return any(signature in lowered for signature in _NETWORK_UNREACHABLE_SIGNATURES)


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
    net_signature: Callable[[str], bool] = is_transient_net_signature,
    sleeper: Sleeper = default_sleeper,
    max_attempts: int = config.TRANSIENT_RETRY_MAX_ATTEMPTS,
) -> RetryResult[T]:
    """Retry fn up to max_attempts when predicate(content) or a net signature.

    fn returns (value, returncode, combined_output). ``net_signature`` selects the
    network-failure class that is retryable on a non-zero exit; the default is the
    broad transient class, but offline-aware push callers pass the narrower
    :func:`is_network_unreachable_signature` so HTTP 5xx stays fail-closed.
    """
    pred: Callable[[str], bool] = predicate or (lambda _content: False)
    for attempt in range(1, max_attempts + 1):
        value, rc, content = fn()
        transient = pred(content)
        if not transient and rc != 0 and net_signature(content):
            transient = True
        if not transient:
            return RetryResult(value=value, attempts=attempt, last_returncode=rc)
        if attempt >= max_attempts:
            return RetryResult(value=value, attempts=attempt, last_returncode=rc)
        backoff_index = min(attempt - 1, len(config.TRANSIENT_RETRY_BACKOFF_SEC) - 1)
        backoff = config.TRANSIENT_RETRY_BACKOFF_SEC[backoff_index]
        sleeper(float(backoff))
    raise AssertionError("loop totality")
