"""Bash-present parity tests for finalize.py high-value decisions."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import finalize
from proc import CommandResult
from run_context import RunContext
from test_support import RecordingRunner


IMPLEMENT_FINALIZE_SH = Path(__file__).resolve().parents[1] / "scripts" / "implement-finalize.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required for finalize parity")


def test_finalize_bash_reference_script_present() -> None:
    assert shutil.which("bash") is not None
    assert IMPLEMENT_FINALIZE_SH.is_file()


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
def test_postmerge_skip_decisions_match_python_contract(
    tmp_path: Path,
    changes: dict[str, object],
    expected: str,
) -> None:
    result = finalize.postmerge(RecordingRunner(), _ctx(tmp_path, **changes), cwd=str(tmp_path))
    assert result.local_cleanup_status == expected


def test_postmerge_draft_status_matches_bash_subprocess(tmp_path: Path) -> None:
    state = tmp_path / "state.sh"
    bail = tmp_path / "final-bail-reason"
    _ = state.write_text(
        "BRANCH_NAME=feat\n"
        "PR_NUMBER=2\n"
        "PR_URL=https://example.test/pr/2\n"
        "PR_TITLE=Title\n"
        "ISSUE_NUMBER=1\n"
        "REPO=o/r\n"
        "DRAFT=true\n"
        "MERGE=true\n"
        "DEFERRED=false\n"
        "REPO_UNAVAILABLE=false\n"
        "PR_CLOSED=false\n"
        "DESIGN_ONLY_DONE=false\n"
        "BAIL_NEEDS_USER_INPUT=false\n"
        "STALL_TRACKING=false\n"
        "DONE_RENAME_APPLIED=false\n"
        "RUN_ID=run-abc\n"
        "FORKED_TARGET=false\n"
        "MERGE_RESULT=\n",
        encoding="utf-8",
    )
    _ = bail.write_text("", encoding="utf-8")
    bash = subprocess.run(
        [
            "bash",
            str(IMPLEMENT_FINALIZE_SH),
            "postmerge",
            "--state-file",
            str(state),
            "--final-bail-reason-file",
            str(bail),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    bash_kv = dict(line.split("=", 1) for line in bash.stdout.splitlines() if "=" in line)
    python_result = finalize.postmerge(
        RecordingRunner(),
        _ctx(tmp_path, draft=True),
        cwd=str(tmp_path),
    )
    assert bash_kv["LOCAL_CLEANUP_STATUS"] == python_result.local_cleanup_status
    assert bash_kv["VERIFY_MAIN_STATUS"] == python_result.verify_main_status


def test_postbump_uses_rebase_without_changelog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_rebase(*_args: object, **_kwargs: object) -> str:
        calls.append("rebase")
        return "already-fresh"

    monkeypatch.setattr(finalize, "_rebase_no_push", fake_rebase)

    def fake_remote_state(*_args: Any, **_kwargs: Any) -> object:
        return type("R", (), {"state": "present"})()

    def fake_force_push(*_args: Any, **_kwargs: Any) -> object:
        return type("P", (), {"pushed": True, "status": "pushed"})()

    monkeypatch.setattr(finalize.git, "remote_branch_state", fake_remote_state)
    monkeypatch.setattr(finalize.git, "force_push_recovery", fake_force_push)

    def fake_branch(*_args: Any, **_kwargs: Any) -> str:
        return "feat"

    def fake_rev(*_args: Any, **_kwargs: Any) -> str:
        return "abc"

    monkeypatch.setattr(finalize.git, "try_current_branch", fake_branch)
    monkeypatch.setattr(finalize.git, "try_rev_parse", fake_rev)
    result = finalize.postbump(RecordingRunner(), _ctx(tmp_path), cwd=str(tmp_path))
    assert result.status == "ok"
    assert result.rebase_status == "already-fresh"
    assert result.log_write_status == "skipped"
    assert calls == ["rebase"]


def test_postbump_branch_mismatch_status_matches_bash_subprocess(tmp_path: Path) -> None:
    state = tmp_path / "postbump-state.sh"
    _ = state.write_text(
        "BRANCH_NAME=definitely-not-the-current-branch\n"
        "ISSUE_NUMBER=1\n"
        "PR_TITLE=Title\n"
        "REPO=o/r\n"
        "FORKED_TARGET=false\n"
        "REPO_UNAVAILABLE=false\n"
        "BUMP_TYPE=NONE\n"
        "NEW_VERSION=\n",
        encoding="utf-8",
    )
    bash = subprocess.run(
        [
            "bash",
            str(IMPLEMENT_FINALIZE_SH),
            "postbump",
            "--state-file",
            str(state),
            "--implement-tmpdir",
            str(tmp_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    bash_kv = dict(line.split("=", 1) for line in bash.stdout.splitlines() if "=" in line)
    python_result = finalize.postbump(
        RecordingRunner(
            responses=[
                CommandResult(("git", "rev-parse", "--show-toplevel"), 0, "/repo\n", "", 0.01),
                CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "current\n", "", 0.01),
            ],
        ),
        _ctx(tmp_path, branch_name="definitely-not-the-current-branch"),
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert bash.returncode == 0
    assert bash_kv["STATUS"] == python_result.status
    assert python_result.rebase_status == "skipped-resume"


def test_postbump_unknown_legacy_checkpoint_is_cleared(tmp_path: Path) -> None:
    checkpoint = tmp_path / ".postbump-phase"
    _ = checkpoint.write_text("legacy-phase\n", encoding="utf-8")
    assert finalize._postbump_checkpoint_status(_ctx(tmp_path)) == "ok"  # pyright: ignore[reportPrivateUsage]
    assert not checkpoint.exists()
