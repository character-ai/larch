"""Bash-vs-Python parity harness for checks.py (temp fixtures only)."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

import checks
import config
import proc
from proc import CommandResult

REPO_ROOT = Path(__file__).resolve().parents[1]


class _ProcRunner:
    def run(self, argv: object, **kwargs: object) -> CommandResult:
        return proc.run(argv, **kwargs)  # type: ignore[arg-type]


SHIP_PR = REPO_ROOT / "scripts" / "ship-pr.sh"
CAPTURED = REPO_ROOT / "scripts" / "run-relevant-checks-captured.sh"
_STUB_SCRIPTS = (
    "ship-pr.sh",
    "lib-quiet.sh",
    "lib-net.sh",
    "lib-finalize-state-keys.sh",
    "oos-disposition-shared.inc.bash",
    "redact-secrets.sh",
    "redact-tmpdir-paths.sh",
    "lib-failed-agent-stderr-tail.sh",
    "ci-failed-jobs.sh",
)
_STUB_EXECUTABLES = (
    "redact-secrets.sh",
    "redact-tmpdir-paths.sh",
    "ci-failed-jobs.sh",
    "ship-pr.sh",
)


def test_external_health_check_timeout_config_matches_bash_sources() -> None:
    assert config.ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT == "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT"
    assert config.EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC == 30

    design_writer = (REPO_ROOT / "scripts" / "write-design-current-env.sh").read_text(
        encoding="utf-8",
    )
    session_writer = (REPO_ROOT / "scripts" / "write-session-env.sh").read_text(
        encoding="utf-8",
    )
    assert 'EXTERNAL_HEALTH_CHECK_TIMEOUT_VALUE="${LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT:-30}"' in design_writer
    assert 'build_export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT "$EXTERNAL_HEALTH_CHECK_TIMEOUT_VALUE"' in design_writer
    assert 'EXTERNAL_HEALTH_CHECK_TIMEOUT_VALUE="${LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT:-30}"' in session_writer
    assert 'LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=$EXTERNAL_HEALTH_CHECK_TIMEOUT_VALUE"' in session_writer


def _prepare_stub_repo(tmp_path: Path) -> Path:
    root = tmp_path / "stub-repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in _STUB_SCRIPTS:
        _ = shutil.copy(REPO_ROOT / "scripts" / name, scripts / name)
    for name in _STUB_EXECUTABLES:
        (scripts / name).chmod(0o755)
    stub_lint = scripts / "lint-fix-loop.sh"
    _ = stub_lint.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail
            site=""
            while [[ $# -gt 0 ]]; do
              case "$1" in
                --site) site="$2"; shift 2 ;;
                --checks-log) shift 2 ;;
                --tmpdir) shift 2 ;;
                *) shift ;;
              esac
            done
            echo "LINT_FIX_STATUS=${STUB_LINT_FIX_STATUS:-failed}"
            echo "LINT_FIX_SITE=${site:-unknown}"
            """
        ),
        encoding="utf-8",
    )
    _ = stub_lint.chmod(0o755)
    return root


def _bash_normalize_max_iter(raw: str) -> int:
    script = f'source "{SHIP_PR}"\nnormalize_rcc_max_iter "$1"\n'
    completed = subprocess.run(
        ["bash", "-c", script, "bash", raw],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return int(completed.stdout.strip())


def _bash_rcc_loop_status(
    *,
    tmp_path: Path,
    dispatch_first: bool,
    max_iter: int,
    stub_fix_status: str,
    initial_redacted: Path | None = None,
    empty_logs: bool = False,
) -> tuple[str, int]:
    """Source ship-pr.sh RCC loop with stub rerun/fix hooks (scripts/test-ship-pr.sh shape)."""
    root = _prepare_stub_repo(tmp_path)
    script_path = tmp_path / "rcc-parity.sh"
    initial_arg = f'"{initial_redacted}"' if initial_redacted is not None else '""'
    dispatch_flag = "1" if dispatch_first else "0"
    if empty_logs:
        rerun_body = textwrap.dedent(
            """\
            rcc_rerun() {
              count=$(cat "$count_file" 2>/dev/null || echo 0)
              count=$((count + 1))
              printf '%s\\n' "$count" > "$count_file"
              _RCC_RAW_LOG_PATH="$tmp/rcc-$count.log"
              : > "$_RCC_RAW_LOG_PATH"
              _RCC_CMD_RC=1
            }
            """
        )
    else:
        rerun_body = textwrap.dedent(
            """\
            rcc_rerun() {
              count=$(cat "$count_file" 2>/dev/null || echo 0)
              count=$((count + 1))
              printf '%s\\n' "$count" > "$count_file"
              _RCC_RAW_LOG_PATH="$tmp/rcc-$count.log"
              printf 'failure %s\\n' "$count" > "$_RCC_RAW_LOG_PATH"
              _RCC_CMD_RC=1
            }
            """
        )
    _ = script_path.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            set -uo pipefail
            root=$1
            tmp=$2
            source "$root/scripts/ship-pr.sh"
            IMPLEMENT_TMPDIR="$tmp"
            count_file="$tmp/rcc-count"
            : > "$count_file"
            {rerun_body}
            _RCC_RERUN_FN=rcc_rerun
            _RCC_PHASE=test-rcc
            _RCC_SITE=ship-pr-ci-per-job
            _RCC_TARGET_CMD_ARGS_FILE=""
            _RCC_DISPATCH_FIRST={dispatch_flag}
            _RCC_MAX_ITER={max_iter}
            _RCC_INITIAL_REDACTED_LOG={initial_arg}
            run_captured_cmd_then_fix_loop >/dev/null 2>&1
            printf 'STATUS=%s\\nCOUNT=%s\\n' "$_RCC_STATUS" "$(cat "$count_file")"
            """
        ),
        encoding="utf-8",
    )
    _ = script_path.chmod(0o755)
    env = {
        **os.environ,
        "IMPLEMENT_TMPDIR": str(tmp_path),
        "CLAUDE_PLUGIN_ROOT": str(root),
        "STUB_LINT_FIX_STATUS": stub_fix_status,
        "PATH": f"{root / 'scripts'}:{os.environ.get('PATH', '')}",
    }
    completed = subprocess.run(
        ["bash", str(script_path), str(root), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode in {0, 1}, completed.stderr
    status = ""
    count = 0
    for line in completed.stdout.splitlines():
        if line.startswith("STATUS="):
            status = line.removeprefix("STATUS=")
        elif line.startswith("COUNT="):
            count = int(line.removeprefix("COUNT="))
    return status, count


@pytest.mark.skipif(
    not SHIP_PR.is_file() or shutil.which("bash") is None,
    reason="bash or ship-pr.sh unavailable",
)
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", 3),
        ("0", 3),
        ("1", 1),
        ("3", 3),
        ("6", 6),
        ("7", 6),
        ("99", 6),
        ("x", 3),
        ("03", 3),
    ],
)
def test_parity_normalize_max_iter(raw: str, expected: int) -> None:
    assert checks.normalize_max_iter(raw) == expected
    assert checks.normalize_max_iter(raw) == _bash_normalize_max_iter(raw)


@pytest.mark.skipif(
    not CAPTURED.is_file() or shutil.which("bash") is None,
    reason="bash or run-relevant-checks-captured.sh unavailable",
)
def test_parity_run_relevant_checks_log_markers(tmp_path: Path) -> None:
    xdg = tmp_path / "cache"
    session = xdg / "larch" / "sessions" / "claude-implement-parity"
    session.mkdir(parents=True)
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    check_script = scripts / "relevant-checks.sh"
    _ = check_script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'echo "=== Running pre-commit on 1 changed file(s) ==="\n'
        'echo "=== Running agent-lint ==="\n'
        "exit 1\n",
        encoding="utf-8",
    )
    _ = check_script.chmod(0o755)

    env = {
        **os.environ,
        "XDG_CACHE_HOME": str(xdg),
        "CLAUDE_PROJECT_DIR": str(repo),
    }
    completed = subprocess.run(
        [str(CAPTURED), "--site", "step6", "--tmpdir", str(session)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 1
    assert "PHASE=agent-lint" in completed.stdout

    os.environ["XDG_CACHE_HOME"] = str(xdg)
    py = checks.run_relevant_checks(
        _ProcRunner(),
        site="step6",
        tmpdir=str(session),
        repo_root=str(repo),
    )
    assert py.ok is False
    assert py.phase == "agent-lint"
    assert py.coverage == "changed-file-only"


@pytest.mark.skipif(
    not SHIP_PR.is_file() or shutil.which("bash") is None,
    reason="bash or ship-pr.sh unavailable",
)
def test_parity_run_check_fix_loop_empty_failure_exhausted_bash_sourced(
    tmp_path: Path,
) -> None:
    status, count = _bash_rcc_loop_status(
        tmp_path=tmp_path,
        dispatch_first=False,
        max_iter=3,
        stub_fix_status="applied",
        empty_logs=True,
    )
    assert status == "exhausted"
    assert count == 2

    sequence = [
        checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=None,
        ),
        checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=None,
            phase="unknown",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=None,
        ),
    ]

    def checks_runner() -> checks.ChecksResult:
        return sequence.pop(0)

    def fixer(_log: str) -> checks.FixOutcome:
        raise AssertionError("fixer must not run")

    loop = checks.run_check_fix_loop(
        checks_runner=checks_runner,
        fixer=fixer,
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == status


@pytest.mark.skipif(
    not SHIP_PR.is_file() or shutil.which("bash") is None,
    reason="bash or ship-pr.sh unavailable",
)
def test_parity_run_check_fix_loop_no_changes_stale(tmp_path: Path) -> None:
    initial = tmp_path / "initial.redacted.log"
    _ = initial.write_text("error\n", encoding="utf-8")
    status, _count = _bash_rcc_loop_status(
        tmp_path=tmp_path,
        dispatch_first=True,
        max_iter=3,
        stub_fix_status="no-changes",
        initial_redacted=initial,
    )
    assert status == "no-changes-stale"

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=str(tmp_path / "fail.redacted.log"),
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(tmp_path / "fail.log"),
        ),
        fixer=lambda _log: checks.FixOutcome(
            status="no-changes",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool="codex",
        ),
        dispatch_first=True,
        initial_redacted_log=str(initial),
        allowed_tmpdir=str(tmp_path),
    )
    assert loop.status == status


@pytest.mark.skipif(
    not SHIP_PR.is_file() or shutil.which("bash") is None,
    reason="bash or ship-pr.sh unavailable",
)
def test_parity_run_check_fix_loop_main_agent_required(tmp_path: Path) -> None:
    raw = tmp_path / "fail.log"
    _ = raw.write_text("error\n", encoding="utf-8")
    redacted = tmp_path / "fail.redacted.log"
    _ = redacted.write_text("error\n", encoding="utf-8")
    status, _count = _bash_rcc_loop_status(
        tmp_path=tmp_path,
        dispatch_first=False,
        max_iter=3,
        stub_fix_status="main-agent-required",
    )
    assert status == "main-agent-required"

    loop = checks.run_check_fix_loop(
        checks_runner=lambda: checks.ChecksResult(
            ok=False,
            exit_code=1,
            site="step6",
            redacted_log_path=str(redacted),
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
            raw_log_path=str(raw),
        ),
        fixer=lambda _log: checks.FixOutcome(
            status="main-agent-required",
            delta_paths=(),
            failure_reason="dispatch-failed",
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
        ),
        dispatch_first=False,
        max_iter=3,
    )
    assert loop.status == status
