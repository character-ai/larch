"""Shared pytest fixtures for isolation."""

from __future__ import annotations

import time

import pytest
import config
import logging_util
import retry


@pytest.fixture(autouse=True)
def _quiet_test_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable lib-quiet routing and reset self-initialized state for every test.

    Without this, tests that run inside run-relevant-checks-captured.sh inherit
    LARCH_QUIET_ACTIVE=1 + LARCH_QUIET_PID=<bash-pid> from the parent script,
    making _quiet_active() return True in all tests and causing BreadcrumbWriter
    to route to fd4 rather than sys.stderr (capsys cannot capture fd4).
    Tests that explicitly test quiet behavior call monkeypatch.delenv on
    LARCH_QUIET_DISABLE and set up their own env via monkeypatch.setenv.
    """
    monkeypatch.setenv(config.ENV_LARCH_QUIET_DISABLE, "1")
    logging_util.reset_quiet_state()


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace all sleep paths with no-ops so retry/backoff tests don't wait.

    Two paths to cover:
    - retry.default_sleeper: used by with_transient_retry in gh.py reads
    - time.sleep: fallback in merge.py when no sleeper is injected

    Tests that verify sleep *amounts* already inject their own sleeper
    (e.g. sleeper=sleeps.append) and are unaffected by these patches.
    """
    def noop(_s: float) -> None:
        pass

    monkeypatch.setattr(retry, "default_sleeper", noop)
    monkeypatch.setattr(time, "sleep", noop)
