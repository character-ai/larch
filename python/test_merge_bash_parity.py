"""Bash parity for merge MERGE_RESULT classification."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import config
import merge as merge_module
from proc import CommandResult
from run_context import RunContext

REPO_ROOT = Path(__file__).resolve().parents[1]
MERGE_SH = REPO_ROOT / "scripts" / "merge-pr.sh"


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
