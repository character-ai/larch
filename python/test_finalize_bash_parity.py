"""Bash-parity smoke tests for finalize.py.

The detailed bash harness remains in scripts/test-implement-finalize.sh; this Python
smoke keeps the Phase 7 module aligned on the post-#3368 skip decisions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import finalize
from run_context import RunContext
from test_finalize import RecordingRunner


pytestmark = pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "scripts" / "implement-finalize.sh").is_file(),
    reason="bash finalize script unavailable",
)


def _ctx(tmp_path: Path, **kwargs: object) -> RunContext:
    base = RunContext(
        branch="feat",
        issue="1",
        repo="o/r",
        run_id="run-abc",
        tmpdir=str(tmp_path),
        merge=True,
        draft=False,
        forked=False,
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="codex",
        no_admin_fallback=False,
        repo_unavailable=False,
        pr_number=2,
        branch_name="feat",
        pr_title="Title",
        issue_number="1",
    )
    return base.with_(**kwargs)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"draft": True}, "skipped-draft"),
        ({"merge": False}, "skipped-merge-false"),
        ({"final_bail_reason": "blocked"}, "skipped-bail"),
    ],
)
def test_postmerge_skip_decisions_match_trimmed_bash(
    tmp_path: Path,
    changes: dict[str, object],
    expected: str,
) -> None:
    result = finalize.postmerge(RecordingRunner(), _ctx(tmp_path, **changes), cwd=str(tmp_path))
    assert result.local_cleanup_status == expected


def test_postbump_uses_rebase_without_changelog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_flush(*_args: object, **_kwargs: object) -> object:
        calls.append("flush")
        return finalize.run_logs.RefreshSkip(skipped=False, reason="")

    def fake_rebase(*_args: object, **_kwargs: object) -> object:
        calls.append("rebase")
        return type("R", (), {"rebased": False, "pushed": True})()

    monkeypatch.setattr(finalize.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(finalize.rebase, "rebase_and_push", fake_rebase)

    def fake_branch(*_args: Any, **_kwargs: Any) -> str:
        return "feat"

    def fake_rev(*_args: Any, **_kwargs: Any) -> str:
        return "abc"

    monkeypatch.setattr(finalize.git, "try_current_branch", fake_branch)
    monkeypatch.setattr(finalize.git, "try_rev_parse", fake_rev)
    result = finalize.postbump(RecordingRunner(), _ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "already-fresh"
    assert calls == ["flush", "rebase"]
