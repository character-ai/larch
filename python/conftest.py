"""Shared pytest fixtures for isolation."""

from __future__ import annotations

import pytest
import config
import logging_util


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
    monkeypatch.setattr(logging_util, "_self_initialized_quiet", False)
