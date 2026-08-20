"""Shared pytest fixtures for isolation."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from larch.core import config
from larch.core import logging_util
import pytest_sharding

from tests.support import shell_fixtures as _shell_fixtures

_SESSION_ROUTING_ENV_VARS = (
    "IMPLEMENT_TMPDIR",
    "DESIGN_TMPDIR",
    "REVIEW_TMPDIR",
    "SESSION_ENV_PATH",
    "LARCH_EXECUTION_ISSUES_LOG",
    "CLAUDE_PLUGIN_ROOT",
    "LARCH_CLAUDE_PLUGIN_ROOT",
    "ISSUE_NUMBER",
    "REPO",
    "SESSION_ID",
    "LARCH_DYNAMIC_ARCHETYPES_MAX",
)


@pytest.fixture(autouse=True)
def _quiet_test_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable quiet routing and reset self-initialized state for every test.

    Without this, tests that run inside scripts/larch.sh checks run-relevant inherit
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

    ISSUE_NUMBER, REPO, and SESSION_ID belong to the same class: the /design
    wrapper rehydration helpers export them onto the real process env, so a
    later test in the same shard would otherwise observe another test's session
    identity (for example a leaked ISSUE_NUMBER makes ship's pre-PR governance
    gate run in a test that expects it skipped).
    """
    for name in _SESSION_ROUTING_ENV_VARS:
        os.environ.pop(name, None)
    yield
    for name in _SESSION_ROUTING_ENV_VARS:
        os.environ.pop(name, None)


@pytest.fixture(autouse=True)
def _verified_bootstrap_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give `scripts/larch.sh` an executable to verify and dispatch to.

    Python callers of Rust-owned commands run the verified bootstrap script,
    which needs a version-matching executable. Preference order:

    1. A caller-supplied `LARCH_BINARY` always wins.
    2. CI publishes the real workspace build as `LARCH_TEST_RUST_BINARY`; using
       it exercises the real commands rather than a double.
    3. Otherwise fall back to the `run-log` double, so a Python-only run with no
       Rust build still reaches the consumer behavior under test.
    """
    if os.environ.get("LARCH_BINARY"):
        return
    real = os.environ.get("LARCH_TEST_RUST_BINARY", "")
    if real and os.access(real, os.X_OK):
        monkeypatch.setenv("LARCH_BINARY", real)
        return
    monkeypatch.setenv(
        "LARCH_BINARY", str(Path(__file__).with_name("tests") / "support" / "larch_binary_stub.sh")
    )


@pytest.fixture(autouse=True)
def _deny_live_issue_mutations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Block scoped live GitHub issue mutations in all tests by default.

    Sets the test-deny control so ``check_live_mutation_auth`` refuses every
    mutation attempt, and scrubs any ambient live-session authorization that
    a parent /design or /implement process may have set.
    """
    monkeypatch.setenv(config.LIVE_MUTATION_TEST_DENY_KEY, "true")
    monkeypatch.delenv(config.LIVE_MUTATION_AUTH_KEY, raising=False)


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


@pytest.fixture
def fake_bin_dir(tmp_path: Path) -> _shell_fixtures.FakeBinDirFactory:
    """Return a function-scoped factory for fail-closed external-command fakes."""
    count = 0

    def make() -> _shell_fixtures.FakeBinDir:
        nonlocal count
        count += 1
        return _shell_fixtures.make_fake_bin_dir(tmp_path / f"fake-bin-{count}")

    return make


@pytest.fixture
def subprocess_env() -> _shell_fixtures.SubprocessEnvFactory:
    """Return a function-scoped factory for controlled subprocess environments."""
    return _shell_fixtures.make_subprocess_env


@pytest.fixture
def fake_plugin_tree(tmp_path: Path) -> _shell_fixtures.PluginTreeFactory:
    """Return a function-scoped factory for minimal symlinked plugin trees."""
    count = 0

    def make(sources: Sequence[_shell_fixtures.PluginSource]) -> Path:
        nonlocal count
        count += 1
        return _shell_fixtures.make_fake_plugin_tree(tmp_path / f"plugin-{count}", sources)

    return make


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
