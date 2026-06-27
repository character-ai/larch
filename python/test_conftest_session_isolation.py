# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false, reportUnusedCallResult=false, reportUnusedFunction=false
"""Regression for #4495 and #4500: pytest stays hermetic inside a live larch session.

CI-fixer code paths in agents.py resolve their output target from ambient
session-routing env vars (IMPLEMENT_TMPDIR, SESSION_ENV_PATH, DESIGN_TMPDIR,
REVIEW_TMPDIR, LARCH_EXECUTION_ISSUES_LOG). When `make py-test` runs inside an
/implement or /design session those vars point at the real session tmpdir, so
simulated CI-fixer failures leaked into the committed run log and the tracking
issue's execution-issues summary. The autouse isolation in conftest.py scrubs
those vars; these tests prove it.

The module-scoped fixture mimics the bug's ambient condition
(`IMPLEMENT_TMPDIR=$(mktemp -d) make py-test`): module scope instantiates before
the function-scoped conftest scrub, so the vars are present until that scrub
removes them per test. Without the scrub these tests fail.

Keep `_SESSION_ROUTING_VARS` in sync with the delenv list in
`conftest._session_routing_isolation`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from larch.agents import agents

_SESSION_ROUTING_VARS = (
    "IMPLEMENT_TMPDIR",
    "DESIGN_TMPDIR",
    "REVIEW_TMPDIR",
    "SESSION_ENV_PATH",
    "LARCH_EXECUTION_ISSUES_LOG",
)


@pytest.fixture(scope="module", autouse=True)
def _ambient_live_session(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Path]:
    """Export the routing vars a live larch session sets, before the
    function-scoped conftest scrub runs (module scope instantiates first).

    Sets every var to a real, existing directory so the leak actually fires
    pre-fix: _append_vendor_failure_diagnostics only writes when IMPLEMENT_TMPDIR
    is an existing dir. Uses raw os.environ (monkeypatch is function-scoped) and
    restores the prior values on teardown.
    """
    session_dir = tmp_path_factory.mktemp("live-session")
    saved = {name: os.environ.get(name) for name in _SESSION_ROUTING_VARS}
    os.environ["IMPLEMENT_TMPDIR"] = str(session_dir)
    os.environ["DESIGN_TMPDIR"] = str(session_dir)
    os.environ["REVIEW_TMPDIR"] = str(session_dir)
    os.environ["SESSION_ENV_PATH"] = str(session_dir / "session-env.sh")
    os.environ["LARCH_EXECUTION_ISSUES_LOG"] = str(session_dir / "execution-issues.md")
    try:
        yield session_dir
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.mark.parametrize("var", _SESSION_ROUTING_VARS)
def test_autouse_isolation_scrubs_session_routing_var(var: str) -> None:
    """Each session-routing var is absent during tests despite the ambient
    live-session export.
    """
    assert var not in os.environ, f"{var} leaked into the test environment"


def test_execution_issues_log_unresolved_under_isolation() -> None:
    """_resolve_execution_issues_log returns None once the routing vars are
    scrubbed, so the CI-fixer never targets an ambient session tmpdir.
    """
    assert agents._resolve_execution_issues_log() is None


def test_vendor_failure_diagnostics_skips_ambient_session_tmpdir(
    _ambient_live_session: Path, tmp_path: Path
) -> None:
    """The vendor-failure diagnostics sink must not write into the ambient
    session tmpdir once isolation scrubs IMPLEMENT_TMPDIR.
    """
    source = tmp_path / "diag.txt"
    _ = source.write_text("simulated failure diagnostics", encoding="utf-8")
    agents._append_vendor_failure_diagnostics(
        source, site="step3 cursor-ci", exit_code=7
    )
    assert not (_ambient_live_session / "vendor-failure-diagnostics.parts").exists()


@pytest.mark.parametrize("tool", ["codex", "cursor", "claude"])
def test_append_ci_failure_skips_ambient_session_tmpdir(
    _ambient_live_session: Path, tmp_path: Path, tool: str
) -> None:
    """End-to-end guard for #4500 (OOS twin of #4495): `_append_ci_failure` is the
    shared CI-fixer sink the test_launch_codex_ci / test_launch_cursor_ci /
    test_check_reviewers / test_cursor_ci_stall_monitor paths funnel a failing
    launcher exit through. Under the conftest isolation it must resolve no
    execution-issues target and write nothing into the ambient session tmpdir for
    any vendor (covering both the run-log append and the vendor-diagnostics sink
    in one call, one level above test_execution_issues_log_unresolved_under_isolation
    and test_vendor_failure_diagnostics_skips_ambient_session_tmpdir).
    """
    output = tmp_path / f"{tool}-ci-out.txt"
    _ = output.write_text("", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".diag").write_text(
        "STATUS=FAILED\nFAILURE_REASON=health\n", encoding="utf-8"
    )
    agents._append_ci_failure(
        output, tool=tool, launcher_exit=127, site="ci fixer", binary_present=False
    )
    assert not (_ambient_live_session / "execution-issues.md").exists()
    assert not (_ambient_live_session / "vendor-failure-diagnostics.parts").exists()
