"""Shared pytest fixtures for isolation."""

from __future__ import annotations

import time
import types

import pytest
import config
import logging_util
import merge as _merge_mod
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
    """Replace sleep paths with no-ops so retry/backoff tests don't wait.

    Two paths to cover:
    - retry.default_sleeper: used by with_transient_retry in gh.py reads
    - merge._merge_mod.time: the time module reference inside merge.py;
      patched at the module-attribute level (not time.sleep globally) so
      pytest-xdist / execnet worker threads keep their real time.sleep and
      do not deadlock.

    merge.py only uses time.sleep (confirmed by grep); all other time
    attributes are preserved via SimpleNamespace forwarding.

    Tests that verify sleep *amounts* already inject their own sleeper
    (e.g. sleeper=sleeps.append) and are unaffected by these patches.
    """
    def noop(_s: float) -> None:
        pass

    monkeypatch.setattr(retry, "default_sleeper", noop)
    # Replace merge.py's reference to the time module with a stub that has
    # a no-op sleep but forwards everything else to the real time module.
    fake_time = types.SimpleNamespace(
        **{k: getattr(time, k) for k in dir(time) if not k.startswith("_")}
    )
    fake_time.sleep = noop
    monkeypatch.setattr(_merge_mod, "time", fake_time)
