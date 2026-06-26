"""Direct Python contract tests for former implement-finalize shell parity."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

from pathlib import Path

import finalize
from larch.core.proc import CommandResult
from test_support import RecordingRunner, make_run_context


def _ctx(tmp_path: Path, **kwargs: object):  # type: ignore[no-untyped-def]
    base = make_run_context(
        run_id="run-abc",
        tmpdir=str(tmp_path),
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="codex",
        pr_number=2,
        pr_title="Title",
        issue_number="1",
    )
    return base.with_(**kwargs)


def test_postmerge_skip_decisions_match_former_shell_contract(tmp_path: Path) -> None:
    assert finalize.postmerge(runner=RecordingRunner(), ctx=_ctx(tmp_path, draft=True), cwd=str(tmp_path)).local_cleanup_status == "skipped-draft"
    assert finalize.postmerge(runner=RecordingRunner(), ctx=_ctx(tmp_path, merge=False), cwd=str(tmp_path)).local_cleanup_status == "skipped-merge-false"
    assert finalize.postmerge(runner=RecordingRunner(), ctx=_ctx(tmp_path, final_bail_reason="blocked"), cwd=str(tmp_path)).local_cleanup_status == "skipped-bail"


def test_postbump_branch_mismatch_uses_resume_skip_status(tmp_path: Path) -> None:
    result = finalize.postbump(
        runner=RecordingRunner(
            responses=[
                CommandResult(("git", "rev-parse", "--show-toplevel"), 0, "/repo\n", "", 0.01),
                CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "current\n", "", 0.01),
            ],
        ),
        ctx=_ctx(tmp_path, branch_name="different"),
        cwd=str(tmp_path),
    )
    assert result.status == "branch-mismatch"
    assert result.rebase_status == "skipped-resume"


def test_postbump_uses_rebase_without_changelog(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []

    def fake_rebase(*_args: object, **_kwargs: object) -> str:
        calls.append("rebase")
        return "already-fresh"

    monkeypatch.setattr(finalize, "_rebase_no_push", fake_rebase)
    monkeypatch.setattr(finalize.git, "remote_branch_state", lambda *_a, **_k: type("R", (), {"state": "absent"})())
    result = finalize.postbump(
        runner=RecordingRunner(
            responses=[
                CommandResult(("git", "rev-parse", "--show-toplevel"), 0, f"{tmp_path}\n", "", 0.01),
                CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01),
            ],
        ),
        ctx=_ctx(tmp_path),
        cwd=str(tmp_path),
    )
    assert result.status == "ok"
    assert result.rebase_status == "already-fresh"
    assert calls == ["rebase"]


def test_postbump_unknown_legacy_checkpoint_is_cleared(tmp_path: Path) -> None:
    checkpoint = tmp_path / ".postbump-phase"
    checkpoint.write_text("legacy-phase\n", encoding="utf-8")
    assert finalize._postbump_checkpoint_status(_ctx(tmp_path)) == "ok"  # pyright: ignore[reportPrivateUsage]
    assert not checkpoint.exists()
