"""Shared pytest fixtures for isolation."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

import pytest
import config
import logging_util
import pytest_sharding


@pytest.fixture(autouse=True)
def _quiet_test_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable quiet routing and reset self-initialized state for every test.

    Without this, tests that run inside python/cli.py checks run-relevant inherit
    LARCH_QUIET_ACTIVE=1 + LARCH_QUIET_PID=<bash-pid> from the parent script,
    making _quiet_active() return True in all tests and causing BreadcrumbWriter
    to route to fd4 rather than sys.stderr (capsys cannot capture fd4).
    Tests that explicitly test quiet behavior call monkeypatch.delenv on
    LARCH_QUIET_DISABLE and set up their own env via monkeypatch.setenv.
    """
    monkeypatch.setenv(config.ENV_LARCH_QUIET_DISABLE, "1")
    logging_util.reset_quiet_state()


@pytest.fixture(autouse=True)
def _session_routing_isolation() -> Iterator[None]:
    """Scrub larch session-routing env vars so the suite stays hermetic when
    `make py-test` runs inside a live /implement or /design session (issue #4495).

    agents.py CI-fixer resolvers (_resolve_execution_issues_log,
    _append_vendor_failure_diagnostics) key off these vars. Outside a session
    they are unset, so standalone CI never writes to them; inside a session they
    point at the real session tmpdir, so simulated CI-fixer failures leaked into
    the committed run log and the tracking issue's execution-issues summary.
    Some wrapper helpers assign process env directly, bypassing monkeypatch.
    Scrub before and after each test so those mutations cannot leak into later
    subprocess tests.
    """
    for name in (
        "IMPLEMENT_TMPDIR",
        "DESIGN_TMPDIR",
        "REVIEW_TMPDIR",
        "SESSION_ENV_PATH",
        "LARCH_EXECUTION_ISSUES_LOG",
        "CLAUDE_PLUGIN_ROOT",
        "LARCH_CLAUDE_PLUGIN_ROOT",
    ):
        os.environ.pop(name, None)
    yield
    for name in (
        "IMPLEMENT_TMPDIR",
        "DESIGN_TMPDIR",
        "REVIEW_TMPDIR",
        "SESSION_ENV_PATH",
        "LARCH_EXECUTION_ISSUES_LOG",
        "CLAUDE_PLUGIN_ROOT",
        "LARCH_CLAUDE_PLUGIN_ROOT",
    ):
        os.environ.pop(name, None)


@pytest.fixture(autouse=True)
def _unique_finder_bonus_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear LARCH_UNIQUE_FINDER_BONUS so no-env tests stay hermetic."""
    monkeypatch.delenv("LARCH_UNIQUE_FINDER_BONUS", raising=False)


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace time.sleep with a no-op so retry/backoff tests don't wait.

    Patching time.sleep globally short-circuits all sleep paths:
    - retry.default_sleeper calls time.sleep internally (its default argument
      captures the function object at definition time, so patching the module
      attribute retry.default_sleeper alone is ineffective; the global patch
      is what actually suppresses sleep in with_transient_retry).
    - merge.py falls back to time.sleep when no sleeper is injected.

    The logging_util.py fd-4 guard (gating os.write(4,...) on
    _self_initialized_quiet) ensures this global patch is safe under
    pytest-xdist: the test that previously triggered an fd-4 write to
    execnet's IPC channel no longer does so.

    Tests that verify sleep *amounts* inject their own sleeper explicitly
    (e.g. sleeper=sleeps.append) and are unaffected by this patch.
    """
    def noop(_s: float) -> None:
        pass

    monkeypatch.setattr(time, "sleep", noop)


def pytest_configure(config: pytest.Config) -> None:
    for marker in (
        "voter_happy",
        "voter_edge_and_r3_claude",
        "voter_retry_claude",
        "voter_retry_codex_success",
        "voter_retry_cursor",
        "voter_retry_codex_fail_and_fallback",
        "voter_regressions_r1_r2",
        "voter_regressions_r3_codex",
    ):
        config.addinivalue_line("markers", f"{marker}: dispatch-code-voters harness section shard")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Keep only the tests assigned to the current shard (issue #4407).

    No-op unless PYTEST_SHARD_ID / PYTEST_SHARD_COUNT are both set, so local
    `make py-test` and targeted harness runs execute the full collection.
    Assigned nodeids use python/shard-assignments.json; unassigned tests
    keep round-robin collection-index fallback.
    """
    parsed = pytest_sharding.read_shard_env(os.environ)
    if parsed is None:
        return
    shard_id, shard_count = parsed
    nodeids = [item.nodeid for item in items]
    assignments = pytest_sharding.load_shard_assignments()
    keep = pytest_sharding.select_shard_nodeids(nodeids=nodeids, shard_id=shard_id, shard_count=shard_count, assignments=assignments)
    selected = [item for index, item in enumerate(items) if index in keep]
    deselected = [item for index, item in enumerate(items) if index not in keep]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected
