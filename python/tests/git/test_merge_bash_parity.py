"""Bash parity for merge MERGE_RESULT classification."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from larch.core import config
from larch.git import gh
from larch.git import git
from larch.git import merge as merge_module
from larch.report import run_logs
from larch.core.proc import CommandResult
from larch.core.run_context import RunContext
from test_support import (
    PR_VIEW_OPEN_JSON,
    RecordingRunner,
    gh_pr_view,
    make_run_context,
    merge_admin_responses,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MERGE_SH = REPO_ROOT / "scripts" / "merge-pr.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="bash is required for merge-pr.sh parity tests",
)


def _mock_checks_pass(*_a: object, **_k: object) -> bool:
    return True


def _mock_rev_cccc(*_a: object, **_k: object) -> str:
    return "cccc3333"


def _mock_refresh_skip_ok(*_a: object, **_k: object) -> run_logs.RefreshSkip:
    return run_logs.RefreshSkip(skipped=False, reason="")


def _mock_ensure_head_behind(*_a: object, **_k: object) -> gh.MergeState:
    return gh.MergeState("BEHIND", "abc")


def _mock_version_gate_none(*_a: object, **_k: object) -> None:
    return None


def _ctx(tmp_path: Path, **kwargs: object) -> RunContext:
    base = make_run_context(
        tmpdir=str(tmp_path),
        manifest_path=str(tmp_path / "manifest.json"),
        pr_number=1,
    )
    return base.with_(**kwargs)


def _flush_recovery_responses() -> list[CommandResult]:
    return [
        gh_pr_view(PR_VIEW_OPEN_JSON),
        gh_pr_view(PR_VIEW_OPEN_JSON),
        gh_pr_view('{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}'),
    ]


def test_python_merge_behind_emits_admin_merged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(responses=merge_admin_responses(double_open_view=True))
    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(merge_module, "_ensure_head_matches_pr", _mock_ensure_head_behind)
    monkeypatch.setattr(merge_module, "_version_race_gate", _mock_version_gate_none)
    ctx = _ctx(tmp_path, state_file=None)
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ADMIN_MERGED


@pytest.mark.skipif(not MERGE_SH.is_file(), reason="merge-pr.sh missing")
def test_behind_emits_admin_merged(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "LARCH_QUIET_DISABLE": "1",
            "GH_MERGE_STATE": "BEHIND",
            "STUB_PR_HEAD_OID": "abc123",
            "GH_ADMIN_EXIT": "0",
        },
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh_log = tmp_path / "gh.log"
    trace = tmp_path / "trace.log"
    env["GH_LOG_FILE"] = str(gh_log)
    env["TRACE_LOG_FILE"] = str(trace)
    gh_stub = bin_dir / "gh"
    _ = gh_stub.write_text(
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        'if [[ "$2" == "view" ]]; then\n'
        '  printf \'{"mergeStateStatus":"%s","headRefOid":"abc123"}\\n\' "${GH_MERGE_STATE:-CLEAN}"\n'
        '  exit 0\n'
        'fi\n'
        'if [[ "$2" == "checks" ]]; then\n'
        '  printf \'[{"name":"ci","bucket":"pass"}]\\n\'\n'
        '  exit 0\n'
        'fi\n'
        'if [[ "$2" == "merge" ]]; then\n'
        '  exit "${GH_ADMIN_EXIT:-0}"\n'
        'fi\n'
        'exit 0\n',
        encoding="utf-8",
    )
    _ = gh_stub.chmod(0o755)
    git_stub = bin_dir / "git"
    _ = git_stub.write_text(
        '#!/usr/bin/env bash\n'
        'case "$1" in\n'
        '  rev-parse) printf "abc123\\n"; exit 0 ;;\n'
        '  fetch) exit 0 ;;\n'
        '  log) exit 0 ;;\n'
        'esac\n'
        'exit 0\n',
        encoding="utf-8",
    )
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
    assert "MERGE_RESULT=admin_merged" in completed.stdout


@pytest.mark.skipif(not MERGE_SH.is_file(), reason="merge-pr.sh missing")
def test_behind_staleness_safety_emits_main_advanced(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "LARCH_QUIET_DISABLE": "1",
            "GH_MERGE_STATE": "BEHIND",
            "STUB_PR_HEAD_OID": "abc123",
            "STUB_BRANCH_LOG": "Bump version to 2.3.4",
            "STUB_ORIGIN_PLUGIN_JSON": '{"version":"2.3.3"}',
            "STUB_ANCESTOR_EXIT": "1",
        },
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    env["GH_LOG_FILE"] = str(tmp_path / "gh.log")
    env["TRACE_LOG_FILE"] = str(tmp_path / "trace.log")
    gh_stub = bin_dir / "gh"
    _ = gh_stub.write_text(
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        'if [[ "$2" == "view" ]]; then\n'
        '  printf \'{"mergeStateStatus":"%s","headRefOid":"abc123"}\\n\' "${GH_MERGE_STATE:-CLEAN}"\n'
        '  exit 0\n'
        'fi\n'
        'if [[ "$2" == "checks" ]]; then\n'
        '  printf \'[{"name":"ci","bucket":"pass"}]\\n\'\n'
        '  exit 0\n'
        'fi\n'
        'exit 0\n',
        encoding="utf-8",
    )
    _ = gh_stub.chmod(0o755)
    git_stub = bin_dir / "git"
    _ = git_stub.write_text(
        '#!/usr/bin/env bash\n'
        'case "$1" in\n'
        '  rev-parse) printf "abc123\\n"; exit 0 ;;\n'
        '  fetch) exit 0 ;;\n'
        '  log)\n'
        '    if [[ "$3" == "origin/main..HEAD" ]]; then printf "%s\\n" "${STUB_BRANCH_LOG:-}"; fi\n'
        '    exit 0 ;;\n'
        '  show)\n'
        '    if [[ "$2" == "origin/main:.claude-plugin/plugin.json" ]]; then printf "%s" "${STUB_ORIGIN_PLUGIN_JSON:-}"; fi\n'
        '    exit 0 ;;\n'
        '  merge-base) exit "${STUB_ANCESTOR_EXIT:-0}" ;;\n'
        'esac\n'
        'exit 0\n',
        encoding="utf-8",
    )
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


@pytest.mark.skipif(not MERGE_SH.is_file(), reason="merge-pr.sh missing")
def test_bash_flush_recovery_k1_emits_admin_merged(tmp_path: Path) -> None:
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    merge_copy = script_dir / "merge-pr.sh"
    _ = merge_copy.write_text(MERGE_SH.read_text(encoding="utf-8"), encoding="utf-8")
    _ = merge_copy.chmod(0o755)
    force_push = script_dir / "push-force-stub.sh"
    _ = force_push.write_text(
        "#!/usr/bin/env bash\nprintf 'PUSHED=true\\nSTATUS=ok\\n'\n",
        encoding="utf-8",
    )
    _ = force_push.chmod(0o755)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    count_file = tmp_path / "view-count"
    gh_stub = bin_dir / "gh"
    _ = gh_stub.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ "$1 $2" == "pr view" ]]; then\n'
        f'  count_file="{count_file}"\n'
        '  count="$(cat "$count_file" 2>/dev/null || printf 0)"\n'
        '  count=$((count + 1))\n'
        '  printf "%s" "$count" > "$count_file"\n'
        '  if [[ "$count" -le 1 ]]; then\n'
        '    printf \'{"mergeStateStatus":"CLEAN","headRefOid":"aaaa1111"}\\n\'\n'
        "  else\n"
        '    printf \'{"mergeStateStatus":"CLEAN","headRefOid":"cccc3333"}\\n\'\n'
        "  fi\n"
        "  exit 0\n"
        "fi\n"
        'if [[ "$1 $2" == "pr checks" ]]; then\n'
        '  printf \'[{"name":"ci","bucket":"pass"}]\\n\'\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "$1 $2" == "pr merge" ]]; then\n'
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    _ = gh_stub.chmod(0o755)
    git_stub = bin_dir / "git"
    _ = git_stub.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'case "$1" in\n'
        "  rev-parse) printf 'cccc3333\\n' ;;\n"
        "  diff) printf 'larch-logs/implement/run-1/manifest.json\\n' ;;\n"
        "  merge-base) exit 0 ;;\n"
        "  fetch) exit 0 ;;\n"
        "  show) exit 1 ;;\n"
        "  log)\n"
        '    if [[ "$*" == *"aaaa1111..HEAD"* ]]; then\n'
        "      printf 'chore(larch-logs): flush run-1\\n'\n"
        "    fi\n"
        "    ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    _ = git_stub.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["LARCH_QUIET_DISABLE"] = "1"
    completed = subprocess.run(
        ["bash", str(merge_copy), "--pr", "1", "--repo", "o/r"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=REPO_ROOT,
    )
    assert completed.returncode == 0
    assert "MERGE_RESULT=admin_merged" in completed.stdout


def test_flush_recovery_mixed_emits_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """N1: mixed flush + non-flush commits refuse merge."""
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(responses=_flush_recovery_responses())
    def fake_log_subjects(*_a: object, **_k: object) -> git.LogSubjects:
        return git.LogSubjects(
            (f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}run", "Fix bug"),
        )

    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git, "try_rev_parse", _mock_rev_cccc)
    monkeypatch.setattr(git, "try_log_subjects", fake_log_subjects)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmp_path, state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
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
    runner = RecordingRunner(responses=_flush_recovery_responses())
    def fake_log_subjects_cap(*_a: object, **_k: object) -> git.LogSubjects:
        return git.LogSubjects(subjects)

    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git, "try_rev_parse", _mock_rev_cccc)
    monkeypatch.setattr(git, "try_log_subjects", fake_log_subjects_cap)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmp_path, state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ERROR


def test_flush_recovery_non_log_paths_emits_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """N2a: flush-subject range touching non-log paths refuses merge."""
    state = tmp_path / "state.env"
    _ = state.write_text("RUN_ID=run-abc\n", encoding="utf-8")
    runner = RecordingRunner(responses=_flush_recovery_responses())
    def fake_log_subjects_paths(*_a: object, **_k: object) -> git.LogSubjects:
        return git.LogSubjects((f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}run",))

    def fake_diff_name_only(*_a: object, **_k: object) -> CommandResult:
        return CommandResult(("git", "diff"), 0, "README.md\n", "", 0.01)

    monkeypatch.setattr(merge_module.gh, "pr_checks_all_pass", _mock_checks_pass)
    monkeypatch.setattr(git, "try_rev_parse", _mock_rev_cccc)
    monkeypatch.setattr(git, "try_log_subjects", fake_log_subjects_paths)
    monkeypatch.setattr(git, "diff_name_only", fake_diff_name_only)
    monkeypatch.setattr(run_logs, "flush_logs_post", _mock_refresh_skip_ok)
    ctx = _ctx(tmp_path, state_file=str(state))
    out = merge_module.merge_pr(runner=runner, ctx=ctx)
    assert out.result == config.MERGE_RESULT_ERROR
    assert "aaaa1111" in out.error
