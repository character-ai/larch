"""Tests for finalize.py."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import finalize
import run_logs
from proc import CommandResult
from run_context import RunContext


def _empty_calls() -> list[list[str]]:
    return []


def _empty_results() -> list[CommandResult]:
    return []


@dataclass
class RecordingRunner:
    calls: list[list[str]] = field(default_factory=_empty_calls)
    responses: list[CommandResult] = field(default_factory=_empty_results)
    _index: int = 0

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        self.calls.append(list(argv))
        if self._index >= len(self.responses):
            return CommandResult(tuple(argv), 0, "", "", 0.01)
        result = self.responses[self._index]
        self._index += 1
        return result


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
        pr_number=7,
        branch_name="feat",
        pr_title="Implement thing",
        issue_number="1",
    )
    return base.with_(**kwargs)


def test_postmerge_skips_draft_without_done_manifest(tmp_path: Path) -> None:
    runner = RecordingRunner()
    ctx = _ctx(tmp_path, draft=True)
    _ = run_logs.init_run(ctx)
    result = finalize.postmerge(runner, ctx, cwd=str(tmp_path))
    manifest_path = tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.local_cleanup_status == "skipped-draft"
    assert manifest["status"] == "partial"
    assert not any(call[:2] == ["git", "commit"] for call in runner.calls)


def test_postmerge_verifies_main_title(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "switch", "main"), 0, "", "", 0.01),
            CommandResult(("git", "pull", "--ff-only", "origin", "main"), 0, "", "", 0.01),
            CommandResult(("git", "branch", "-D", "feat"), 0, "", "", 0.01),
            CommandResult(("git", "log", "-1", "--format=%s", "main"), 0, "Implement thing (#7)\n", "", 0.01),
        ],
    )
    result = finalize.postmerge(runner, _ctx(tmp_path), cwd=str(tmp_path))
    assert result.local_cleanup_status == "success"
    assert result.verify_main_status == "verified"


def test_teardown_stall_preserves_tmpdir_and_writes_manifest(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "issue", "view"), 0, '{"title":"Existing title","state":"OPEN"}\n', "", 0.01),
            CommandResult(("gh", "issue", "edit"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, " M file\n", "", 0.01),
            CommandResult(("git", "stash"), 0, "", "", 0.01),
            CommandResult(("git", "stash", "list"), 0, "stash@{0} larch-stalled-1-12\n", "", 0.01),
            CommandResult(("git", "rev-parse", "--git-dir"), 0, ".git\n", "", 0.01),
        ],
    )
    result = finalize.teardown(
        runner,
        _ctx(tmp_path, stall_tracking=True, stall_step="12"),
        cwd=str(tmp_path),
    )
    assert result.status == "stalled-preserved"
    assert tmp_path.exists()
    assert (git_dir / "larch-stalled-run.txt").is_file()
    manifest = json.loads(
        (tmp_path / "larch-logs" / "implement" / "run-abc" / "manifest.json").read_text(
            encoding="utf-8",
        ),
    )
    assert manifest["steps_ran"]["stalled_at_step"] == "12"


def test_write_finalize_state_contains_teardown_keys(tmp_path: Path) -> None:
    target = tmp_path / "finalize-state.sh"
    finalize.write_finalize_state(_ctx(tmp_path, pr_closed=True), target)
    text = target.read_text(encoding="utf-8")
    assert "PR_CLOSED=true\n" in text
    assert "NO_LOGS_COMMIT=false\n" in text
