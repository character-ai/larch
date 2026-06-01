"""Bash parity for merge MERGE_RESULT classification."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import config
import git
import merge as merge_module
import run_logs
from proc import CommandResult
from run_context import RunContext

REPO_ROOT = Path(__file__).resolve().parents[1]
MERGE_SH = REPO_ROOT / "scripts" / "merge-pr.sh"


def _mock_checks_pass(*_a: object, **_k: object) -> bool:
    return True


def _mock_rev_cccc(*_a: object, **_k: object) -> str:
    return "cccc3333"


def _mock_refresh_skip_ok(*_a: object, **_k: object) -> run_logs.RefreshSkip:
    return run_logs.RefreshSkip(skipped=False, reason="")


def _empty_str_lists() -> list[list[str]]:
    return []


def _empty_command_results() -> list[CommandResult]:
    return []


@dataclass
class RecordingRunner:
    calls: list[list[str]] = field(default_factory=_empty_str_lists)
    responses: list[CommandResult] = field(default_factory=_empty_command_results)
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


def test_python_merge_behind_emits_main_advanced(tmp_path: Path) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"BEHIND","headRefOid":"abc"}',
                "",
                0.01,
            ),
        ],
    )
    ctx = RunContext(
        branch="feat",
        issue="1",
        repo="o/r",
        run_id="run-1",
        tmpdir=str(tmp_path),
        merge=True,
        draft=False,
        forked=False,
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="cursor",
        no_admin_fallback=False,
        repo_unavailable=False,
        pr_number=1,
        state_file=None,
    )
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_MAIN_ADVANCED


@pytest.mark.skipif(not MERGE_SH.is_file(), reason="merge-pr.sh missing")
def test_behind_emits_main_advanced(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "LARCH_QUIET_DISABLE": "1",
            "GH_MERGE_STATE": "BEHIND",
            "STUB_PR_HEAD_OID": "abc123",
        },
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh_log = tmp_path / "gh.log"
    trace = tmp_path / "trace.log"
    env["GH_LOG_FILE"] = str(gh_log)
    env["TRACE_LOG_FILE"] = str(trace)
    # Minimal stub gh from test-merge-pr.sh pattern
    gh_stub = bin_dir / "gh"
    _ = gh_stub.write_text(
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        'if [[ "$2" == "view" ]]; then\n'
        '  printf \'{"mergeStateStatus":"%s","headRefOid":"abc123"}\\n\' "${GH_MERGE_STATE:-CLEAN}"\n'
        '  exit 0\n'
        'fi\n'
        'exit 0\n',
        encoding="utf-8",
    )
    _ = gh_stub.chmod(0o755)
    git_stub = bin_dir / "git"
    _ = git_stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    _ = git_stub.chmod(0o755)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    completed = subprocess.run(
        ["bash", str(MERGE_SH), "--pr", "1", "--repo", "o/r"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=REPO_ROOT,
    )
    assert completed.returncode == 0
    assert "MERGE_RESULT=main_advanced" in completed.stdout


def test_flush_recovery_mixed_emits_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """N1: mixed flush + non-flush commits refuse merge."""
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}',
                "",
                0.01,
            ),
        ],
    )
    def fake_log_subjects(*_a: object, **_k: object) -> git.LogSubjects:
        return git.LogSubjects(
            (f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}run", "Fix bug"),
        )

    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git, "try_rev_parse", _mock_rev_cccc)
    monkeypatch.setattr(git, "try_log_subjects", fake_log_subjects)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = RunContext(
        branch="feat",
        issue="1",
        repo="o/r",
        run_id="run-1",
        tmpdir=str(tmp_path),
        merge=True,
        draft=False,
        forked=False,
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="cursor",
        no_admin_fallback=False,
        repo_unavailable=False,
        pr_number=1,
        state_file=str(state),
    )
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "aaaa1111" in out.error


def test_flush_recovery_cap_emits_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """P1: more than five flush commits refuse merge."""
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    subjects = tuple(
        f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}{index}"
        for index in range(config.FLUSH_RECOVERY_MAX_COMMITS + 1)
    )
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}',
                "",
                0.01,
            ),
        ],
    )
    def fake_log_subjects_cap(*_a: object, **_k: object) -> git.LogSubjects:
        return git.LogSubjects(subjects)

    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git, "try_rev_parse", _mock_rev_cccc)
    monkeypatch.setattr(git, "try_log_subjects", fake_log_subjects_cap)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = RunContext(
        branch="feat",
        issue="1",
        repo="o/r",
        run_id="run-1",
        tmpdir=str(tmp_path),
        merge=True,
        draft=False,
        forked=False,
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="cursor",
        no_admin_fallback=False,
        repo_unavailable=False,
        pr_number=1,
        state_file=str(state),
    )
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_ERROR


def test_flush_recovery_non_log_paths_emits_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """N2a: flush-subject range touching non-log paths refuses merge."""
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}',
                "",
                0.01,
            ),
        ],
    )
    def fake_log_subjects_paths(*_a: object, **_k: object) -> git.LogSubjects:
        return git.LogSubjects((f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}run",))

    def fake_diff_name_only(*_a: object, **_k: object) -> CommandResult:
        return CommandResult(("git", "diff"), 0, "README.md\n", "", 0.01)

    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git, "try_rev_parse", _mock_rev_cccc)
    monkeypatch.setattr(git, "try_log_subjects", fake_log_subjects_paths)
    monkeypatch.setattr(git, "diff_name_only", fake_diff_name_only)
    monkeypatch.setattr(run_logs, "flush_logs_pre", _mock_refresh_skip_ok)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = RunContext(
        branch="feat",
        issue="1",
        repo="o/r",
        run_id="run-1",
        tmpdir=str(tmp_path),
        merge=True,
        draft=False,
        forked=False,
        manifest_path=str(tmp_path / "manifest.json"),
        tool_label="cursor",
        no_admin_fallback=False,
        repo_unavailable=False,
        pr_number=1,
        state_file=str(state),
    )
    out = merge_module.merge_pr(runner, ctx)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "aaaa1111" in out.error
