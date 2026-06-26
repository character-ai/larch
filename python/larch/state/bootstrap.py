# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""/implement Step 0 bootstrap and routing-envelope helpers."""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from larch.state import dirty_tree
import external_defaults
from larch import io as larch_io
from larch.core import logging_util

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PY_CLI = Path(__file__).resolve().parents[2] / "cli.py"
_PS = shutil.which("ps") or "/bin/ps"
BOOTSTRAP_CONTRACT_FAILURE = 2
ROUTING_KEYS: tuple[str, ...] = (
    "IMPLEMENT_TMPDIR",
    "IMPLEMENT_BAIL_REASON",
    "STALL_TRACKING",
    "PLAN_FILE",
    "coder",
    "coder_fallback",
    "REPO_UNAVAILABLE",
    "DEFERRED",
    "ISSUE_NUMBER",
    "REPO",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "codex_available",
    "cursor_available",
    "RUN_ID",
    "BRANCH_NAME",
    "BRANCH_ACTION",
    "SELF_REVIEW_REQUESTED",
    "DEGRADED",
    "BOTH_DOWN",
    "CODEX_STATE",
    "CURSOR_STATE",
    "DEGRADED_PROMPT_REQUIRED",
    "DEGRADED_HARD_FAIL",
    "BOOTSTRAP_NEXT",
    "ROUTE",
    "CHECKPOINT_NEXT",
    "REBASE_RC",
    "REBASE_OUTCOME",
    "CONFLICT_FILES",
    "REBASE_ERROR",
    "SKIPPED_ALREADY_PUSHED",
    "SKIPPED_ALREADY_FRESH",
)
_ADVISORY_STDOUT_PREFIXES: tuple[str, ...] = ("PHANTOM_",)
_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class BootstrapExit(Exception):
    def __init__(self, code: int) -> None:
        self.code = code


def _emit_kv(*, key: str, value: str) -> None:
    logging_util.emit_kv(key=key, value=value.replace("\n", " ").replace("\r", " "))


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _run(argv: list[str], *, env: dict[str, str] | None = None, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, capture_output=True, text=True, errors="replace", env=env, cwd=cwd, check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"{exc}\n")


def _cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return _run([sys.executable, str(_PY_CLI), *args], env=env)


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, skip_comments=True, cr_strip="rstrip")


def _valid_run_id(value: str) -> bool:
    return bool(value) and _RUN_ID_RE.fullmatch(value) is not None


def _valid_issue(value: str) -> bool:
    return bool(value) and value.isdigit()


def _atomic_text(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, temp_name=f"{path.name}.tmp.{os.getpid()}")




def _read_simple_kv(*, path: Path, key: str) -> str:
    return larch_io.read_kv(path=path, key=key, first_match=True, cr_strip="suffix", reject_symlink=True, on_error_default=True)


def _bool_text(*, value: str, default: str = "false") -> str:
    if value in {"true", "false"}:
        return value
    return default


def _merge_write_ship_seed_input(*, tmpdir: str, values: dict[str, str], only_missing: bool) -> None:
    if not tmpdir:
        return
    path = Path(tmpdir) / "ship-seed-input.env"
    existing: dict[str, str] = {}
    if path.is_file() and not path.is_symlink():
        try:
            existing = _parse_kv(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            existing = {}
    data = dict(existing)
    for key, value in values.items():
        if only_missing and data.get(key):
            continue
        data[key] = value
    ordered = ("MERGE", "DRAFT", "FORKED_TARGET", "NO_ADMIN_FALLBACK", "NO_LOGS_COMMIT", "DEFERRED", "MANIFEST_PATH", "TOOL_LABEL")
    text = "".join(f"{key}={data.get(key, '')}\n" for key in ordered if key in data)
    _atomic_text(path=path, text=text)

def _write_larch_run_sh(implement_tmpdir: str) -> bool:
    if not implement_tmpdir:
        return False
    path = Path(implement_tmpdir) / "larch-run.sh"
    script = """#!/usr/bin/env bash
set -uo pipefail

IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)}"
export IMPLEMENT_TMPDIR

[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
export CLAUDE_PLUGIN_ROOT

[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || { printf '%s\\n' 'larch-run.sh: CLAUDE_PLUGIN_ROOT could not be resolved' >&2; exit 2; }
[ "$#" -ge 1 ] || { printf '%s\\n' 'larch-run.sh: missing relative script path' >&2; exit 2; }

script=$1
shift
case "$script" in
  /*|*..*) printf '%s\\n' "larch-run.sh: invalid relative script path: $script" >&2; exit 2 ;;
esac

_larch_cleanup_active_leg() {
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement kill-active-leg --implement-tmpdir "$IMPLEMENT_TMPDIR" 2>/dev/null || true
}

case "$script" in
  *.py)
    trap _larch_cleanup_active_leg EXIT INT TERM
    python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@"
    rc=$?
    _larch_cleanup_active_leg
    trap - EXIT INT TERM
    exit "$rc"
    ;;
  *.sh) exec "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;
  *) printf '%s\\n' "larch-run.sh: unsupported script target: $script" >&2; exit 2 ;;
esac
"""
    try:
        _atomic_text(path=path, text=script)
        path.chmod(0o755)
    except OSError:
        return False
    return True


def _read_key(*, path: Path, key: str, default: str = "") -> str:
    result = _cli("session", "read-key", "--file", str(path), "--key", key, "--default", default)
    return result.stdout.strip() if result.returncode == 0 else default


def _single_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()


@dataclass(frozen=True)
class BootstrapOptions:
    up_to_phase: str
    caller_env: str = ""
    issue_number: str = ""
    forked_target: str = "false"
    merge_requested: str = "false"
    draft_requested: str = "false"
    no_admin_fallback: str = "false"
    no_logs_commit: str = "false"
    force_requested: str = "false"
    self_review_requested: str = "false"
    upstream_repo: str = ""
    run_id: str = ""
    preflight_tmpdir: str = ""
    coder_opt: str = ""
    resume_plan_tail: bool = False
    skip_codex_probe: bool = False
    skip_cursor_probe: bool = False
    non_interactive: str = ""


# Mutable state: fields (coder / branch_name / repo / run_id / deferred / ...) are set as bootstrap phases run.
@dataclass
class BootstrapState:
    opts: BootstrapOptions
    current_branch: str = ""
    is_main: str = ""
    is_user_branch: str = ""
    user_prefix: str = ""
    entry_gate: str = ""
    skip_branch_check: str = ""
    implement_tmpdir: str = field(default_factory=lambda: os.environ.get("IMPLEMENT_TMPDIR", ""))
    session_id: str = ""
    repo: str = ""
    repo_unavailable: str = "false"
    codex_present: str = ""
    cursor_present: str = ""
    codex_binary_found: str = ""
    cursor_binary_found: str = ""
    codex_available: str = ""
    cursor_available: str = ""
    issue_number_resolved: str = ""
    run_id: str = ""
    branch_selected: str = ""
    deferred: str = "false"
    stall_tracking: str = "false"
    branch_name: str = ""
    branch_action: str = ""
    plan_file: str = ""
    coder: str = ""
    coder_fallback: str = ""
    implement_bail_reason: str = ""

    def emit_step_failed(self, value: str) -> None:
        _emit_kv(key="STEP_FAILED", value=value)
        raise BootstrapExit(2)

    def emit_tmp_step_failed(self, value: str) -> None:
        _emit_kv(key="IMPLEMENT_TMPDIR", value=self.implement_tmpdir)
        self.emit_step_failed(value)

    def session_env(self) -> Path:
        return Path(self.implement_tmpdir) / "session-env.sh"

    def read_session(self, *, key: str, default: str = "") -> str:
        if self.session_env().is_file():
            return _read_key(path=self.session_env(), key=key, default=default)
        return default

    def resolve_run_id(self) -> str:
        for candidate in (self.opts.run_id, self.run_id):
            if _valid_run_id(candidate):
                return candidate
        sid = Path(self.implement_tmpdir) / "session-id"
        if sid.is_file():
            value = sid.read_text(encoding="utf-8", errors="replace").strip()
            if _valid_run_id(value):
                return value
        if _valid_run_id(self.session_id):
            return self.session_id
        return ""


def _write_base_session_env(st: BootstrapState) -> None:
    prior_claude_source = st.read_session(key="LARCH_CLAUDE_SOURCE_FILE")
    prior_auto_mode = st.read_session(key="LARCH_AUTO_MODE")
    prior_dynamic_archetypes = st.read_session(key="LARCH_DYNAMIC_ARCHETYPES_MAX")
    claude_source = prior_claude_source
    claude_source_path = Path(st.implement_tmpdir) / "claude-source.env"
    if not claude_source and claude_source_path.is_file():
        claude_source = str(claude_source_path)
    args = [
        "session",
        "write-env",
        "--output",
        str(st.session_env()),
        "--repo",
        st.repo,
        "--repo-unavailable",
        st.repo_unavailable or "false",
        "--codex-present",
        st.codex_present,
        "--cursor-present",
        st.cursor_present,
        "--codex-binary-found",
        st.codex_binary_found,
        "--cursor-binary-found",
        st.cursor_binary_found,
        "--timing-ledger",
        str(Path(st.implement_tmpdir) / "timing-ledger.tsv"),
        "--token-session-id",
        st.session_id,
        "--prev-implement-tmpdir",
        st.implement_tmpdir,
        "--forked-target",
        st.opts.forked_target,
    ]
    if claude_source:
        args.extend(["--claude-source-file", claude_source])
    if prior_auto_mode:
        args.extend(["--auto-mode", prior_auto_mode])
    if prior_dynamic_archetypes:
        args.extend(["--dynamic-archetypes", prior_dynamic_archetypes])
    if _valid_run_id(st.run_id):
        args.extend(["--run-id", st.run_id])
    result = _cli(*args)
    if result.returncode != 0:
        st.emit_step_failed("write-session-env")
    _cli("session", "write-env", "--plugin-root-only", "--output", str(Path(st.implement_tmpdir) / "plugin-root.env"), "--value", str(_REPO_ROOT))


def _write_claude_source_snapshot(st: BootstrapState) -> None:
    if not st.implement_tmpdir:
        return
    target = Path(st.implement_tmpdir) / "claude-source.env"
    if target.is_file() and target.stat().st_size > 0:
        return
    env = {**os.environ, "LARCH_TOKEN_SESSION_ID": st.session_id}
    result = _cli("token", "claude-source", env=env)
    if result.returncode != 0 or "TRANSCRIPT_PATH=" not in result.stdout:
        return
    _atomic_text(path=target, text=result.stdout)


def _persist_run_flags(st: BootstrapState) -> bool:
    if not st.implement_tmpdir:
        return True
    result = _cli(
        "session",
        "persist-run-flags",
        "--implement-tmpdir",
        st.implement_tmpdir,
        "--no-issues",
        "false",
        "--force-requested",
        st.opts.force_requested,
        "--self-review-requested",
        st.opts.self_review_requested,
    )
    if result.returncode != 0:
        st.stall_tracking = "true"
        st.implement_bail_reason = "run-flags-persist-failed"
        return False
    return True


def _phase_infra(st: BootstrapState) -> None:
    branch = _cli("pr", "create-branch", "--check")
    if branch.returncode != 0:
        st.emit_step_failed("create-branch")
    bkv = _parse_kv(branch.stdout)
    st.current_branch = bkv.get("CURRENT_BRANCH", "")
    st.is_main = bkv.get("IS_MAIN", "")
    st.is_user_branch = bkv.get("IS_USER_BRANCH", "")
    st.user_prefix = bkv.get("USER_PREFIX", "")

    gate = _cli(
        "session",
        "entry-gate",
        "--mode",
        "implement",
        "--current-branch",
        st.current_branch,
        "--is-main",
        st.is_main,
        "--is-user-branch",
        st.is_user_branch,
        "--user-prefix",
        st.user_prefix,
    )
    if gate.returncode != 0:
        sys.stderr.write(gate.stderr)
        st.emit_step_failed("session-entry-gate")
    gkv = _parse_kv(gate.stdout)
    st.entry_gate = gkv.get("ENTRY_GATE", "")
    st.skip_branch_check = gkv.get("SKIP_BRANCH_CHECK", "")

    if st.opts.resume_plan_tail and st.implement_tmpdir and st.session_env().is_file():
        st.session_id = (Path(st.implement_tmpdir) / "session-id").read_text(encoding="utf-8", errors="replace").strip() if (Path(st.implement_tmpdir) / "session-id").is_file() else ""
        st.repo = st.read_session(key="REPO")
        st.repo_unavailable = st.read_session(key="REPO_UNAVAILABLE", default="false")
        st.codex_present = st.read_session(key="CODEX_PRESENT")
        st.cursor_present = st.read_session(key="CURSOR_PRESENT")
        st.codex_binary_found = st.read_session(key="CODEX_BINARY_FOUND")
        st.cursor_binary_found = st.read_session(key="CURSOR_BINARY_FOUND")
        if not (Path(st.implement_tmpdir) / "plugin-root.env").is_file():
            _cli("session", "write-env", "--plugin-root-only", "--output", str(Path(st.implement_tmpdir) / "plugin-root.env"), "--value", str(_REPO_ROOT))
    else:
        setup_args = ["session", "setup", "--prefix", "claude-implement", "--check-reviewers"]
        if st.skip_branch_check == "true":
            setup_args.append("--skip-branch-check")
        if st.opts.skip_codex_probe:
            setup_args.append("--skip-codex-probe")
        if st.opts.skip_cursor_probe:
            setup_args.append("--skip-cursor-probe")
        if st.opts.caller_env:
            setup_args.extend(["--caller-env", st.opts.caller_env])
        setup = _cli(*setup_args)
        if setup.returncode != 0:
            sys.stdout.write(setup.stdout)
            st.emit_step_failed("session-setup")
        skv = _parse_kv(setup.stdout)
        st.implement_tmpdir = skv.get("SESSION_TMPDIR", "")
        os.environ["IMPLEMENT_TMPDIR"] = st.implement_tmpdir
        st.session_id = skv.get("SESSION_ID", "")
        st.repo = skv.get("REPO", "")
        st.repo_unavailable = skv.get("REPO_UNAVAILABLE", "false")
        st.codex_present = skv.get("CODEX_PRESENT", "")
        st.cursor_present = skv.get("CURSOR_PRESENT", "")
        st.codex_binary_found = skv.get("CODEX_BINARY_FOUND", "")
        st.cursor_binary_found = skv.get("CURSOR_BINARY_FOUND", "")
        if st.opts.preflight_tmpdir:
            _atomic_text(path=Path(st.implement_tmpdir) / "preflight-tmpdir.env", text=f"PREFLIGHT_TMPDIR={st.opts.preflight_tmpdir}\n")
        _cli("session", "write-id", "--output", str(Path(st.implement_tmpdir) / "session-id"))
        if not st.session_id and (Path(st.implement_tmpdir) / "session-id").is_file():
            st.session_id = (Path(st.implement_tmpdir) / "session-id").read_text(encoding="utf-8", errors="replace").strip()
        st.run_id = st.resolve_run_id()
        _write_claude_source_snapshot(st)
        _write_base_session_env(st)
        _cli("token", "mark", "Step 0 — preflight")
        env = {**os.environ, "LARCH_TIMING_SKILL": "implement"}
        _cli("timing", "mark", "Step 0 — preflight", env=env)
    if st.implement_tmpdir and not _write_larch_run_sh(st.implement_tmpdir):
        st.emit_step_failed("larch-run")
    pid = os.environ.get("LARCH_CLAUDE_PID", "")
    if pid and st.implement_tmpdir:
        pointer = _cli("session", "write-implement-env", "--claude-pid", pid, "--implement-tmpdir", st.implement_tmpdir, "--cwd", str(Path.cwd()))
        if pointer.returncode != 0:
            diag = Path(st.implement_tmpdir) / "write-implement-env-warning.log"
            with contextlib.suppress(OSError):
                diag.write_text(pointer.stdout + pointer.stderr, encoding="utf-8")
            if diag.is_file():
                _append_failure_with_entry_fallback(
                    st,
                    site="implement-bootstrap write-implement-env",
                    tool="session write-implement-env",
                    exit_code=str(pointer.returncode),
                    category="Warnings",
                    output_file=diag,
                    status_label="failed",
                )
    st.codex_available = "true" if st.codex_binary_found == "true" else "false"
    st.cursor_available = "true" if st.cursor_binary_found == "true" else "false"
    _err(f"→ step0: infra ready (tmpdir={st.implement_tmpdir} session={st.session_id})")


def _phase_tracking(st: BootstrapState) -> None:
    if st.repo_unavailable == "true":
        st.branch_selected = "repo-unavailable-skip"
        st.deferred = "true"
        return
    if st.opts.forked_target == "true":
        st.branch_selected = "forked-target-skip"
        st.deferred = "true"
        return
    sentinel = Path(st.implement_tmpdir) / "parent-issue.md"
    if sentinel.is_file():
        read = _cli("tracking-issue", "read", "--sentinel", str(sentinel))
        rkv = _parse_kv(read.stdout)
        if read.returncode == 0 and rkv.get("FAILED") != "true" and rkv.get("ADOPTED") == "true":
            issue = rkv.get("ISSUE_NUMBER", "")
            run_id = rkv.get("RUN_ID", "")
            if st.opts.issue_number and issue != st.opts.issue_number:
                if st.opts.resume_plan_tail:
                    st.emit_step_failed("resume-plan-tail-sentinel")
                with contextlib.suppress(OSError):
                    sentinel.unlink()
            elif not st.opts.issue_number:
                st.emit_step_failed("issue-number-required-for-resume")
            elif _valid_issue(issue) and _valid_run_id(run_id):
                st.branch_selected = "branch-1-resume"
                st.issue_number_resolved = issue
                st.run_id = run_id
                if st.opts.resume_plan_tail:
                    return
                dirty_lines = dirty_tree.checkpoint()
                dkv = _parse_kv("\n".join(dirty_lines))
                if dkv.get("STATUS") in {"dirty", "unknown"}:
                    st.implement_bail_reason = "dirty-tree"
                    return
                _perform_tracking_side_effects(st, write_sentinel=False)
                return
        elif st.opts.resume_plan_tail:
            st.emit_step_failed("resume-plan-tail-sentinel")
    elif st.opts.resume_plan_tail and not ((Path(st.implement_tmpdir) / "plan.txt").is_file() and (Path(st.implement_tmpdir) / "feature-description.txt").is_file()):
        st.emit_step_failed("resume-plan-tail-sentinel")

    if not st.opts.issue_number:
        return
    if st.opts.resume_plan_tail and (Path(st.implement_tmpdir) / "plan.txt").is_file():
        st.issue_number_resolved = st.opts.issue_number
        st.run_id = st.resolve_run_id()
        st.branch_selected = "branch-2-adopt"
        st.deferred = "true"
        return
    state = _cli("issue", "state", "--issue", st.opts.issue_number)
    skv = _parse_kv(state.stdout)
    if state.returncode != 0 or skv.get("FAILED") == "true":
        st.emit_step_failed("get-issue-state")
    if skv.get("IS_PR") == "true":
        st.implement_bail_reason = "adopted-issue-is-pr"
        return
    if skv.get("STATE") == "CLOSED":
        st.implement_bail_reason = "adopted-issue-closed"
        return
    if skv.get("STATE") != "OPEN":
        st.emit_step_failed("get-issue-state")
    dirty_lines = dirty_tree.checkpoint()
    dkv = _parse_kv("\n".join(dirty_lines))
    if dkv.get("STATUS") in {"dirty", "unknown"}:
        st.implement_bail_reason = "dirty-tree"
        return
    st.branch_selected = "branch-2-adopt"
    st.issue_number_resolved = st.opts.issue_number
    st.run_id = st.resolve_run_id()
    _perform_tracking_side_effects(st, write_sentinel=True)


def _tracking_bail(*, st: BootstrapState, detail: str, result: subprocess.CompletedProcess[str] | None = None) -> None:
    st.stall_tracking = "true"
    st.implement_bail_reason = "tracking-init-failed"
    if st.implement_tmpdir:
        text = detail + "\n"
        if result is not None:
            text += result.stdout
            text += result.stderr
        with contextlib.suppress(OSError):
            (Path(st.implement_tmpdir) / "tracking-init-failed.stderr.log").write_text(text, encoding="utf-8")


def _perform_tracking_side_effects(st: BootstrapState, *, write_sentinel: bool) -> bool:
    if not _valid_issue(st.issue_number_resolved):
        _tracking_bail(st=st, detail="invalid issue number")
        return False
    if not _valid_run_id(st.run_id):
        _tracking_bail(st=st, detail="invalid or empty run id")
        return False
    _write_base_session_env(st)
    rename = _cli("tracking-issue", "rename", "--issue", st.issue_number_resolved, "--state", "implementing")
    if st.implement_tmpdir and (rename.returncode != 0 or _parse_kv(rename.stdout).get("FAILED") == "true"):
        text = "tracking rename failed\n" + rename.stdout + rename.stderr
        with contextlib.suppress(OSError):
            (Path(st.implement_tmpdir) / "tracking-rename-warning.stderr.log").write_text(text, encoding="utf-8")
    init = _cli("run-log", "init", "--log-root", str(Path(st.implement_tmpdir) / "larch-logs"), "--skill", "implement", "--run-id", st.run_id, "--issue", st.issue_number_resolved)
    if init.returncode != 0:
        _tracking_bail(st=st, detail="run-log init failed", result=init)
        return False
    if not _persist_run_flags(st):
        return False
    post_args = ["tracking", "post-issue", "--implement-tmpdir", st.implement_tmpdir, "--run-id", st.run_id, "--adopted", "true", "--force-requested", st.opts.force_requested]
    if write_sentinel:
        post_args.extend(["--issue-number", st.issue_number_resolved])
    post = _cli(*post_args)
    pkv = _parse_kv(post.stdout)
    if post.returncode != 0:
        st.deferred = "true"
        return False
    if pkv.get("POSTED") == "false":
        st.deferred = "true"
    return True


def _append_execution_issue_entry(*, log: Path, category: str, entry: str) -> subprocess.CompletedProcess[str]:
    return _cli(
        "run-log",
        "append-entry",
        "--log",
        str(log),
        "--category",
        category,
        "--entry",
        entry,
    )


def _append_failure_with_entry_fallback(
    st: BootstrapState,
    *,
    site: str,
    tool: str,
    exit_code: str,
    category: str,
    output_file: Path,
    status_label: str,
) -> bool:
    log = Path(st.implement_tmpdir) / "execution-issues.md"
    result = _cli(
        "run-log",
        "append-failure",
        "--log",
        str(log),
        "--site",
        site,
        "--tool",
        tool,
        "--exit-code",
        exit_code,
        "--category",
        category,
        "--output-file",
        str(output_file),
        "--status-label",
        status_label,
        "--redact",
    )
    if result.returncode == 0:
        return True
    body = "no diagnostics captured"
    with contextlib.suppress(OSError):
        if output_file.is_file() and output_file.stat().st_size:
            body = output_file.read_text(encoding="utf-8", errors="replace").rstrip() or body
    body = _redact_text(body, implement_tmpdir=st.implement_tmpdir)
    entry = (
        f"- **Step {site} — {tool} {status_label} (exit {exit_code}; append-failure fallback)**:\n"
        "  ```\n"
        f"{body}\n"
        "  ```\n"
    )
    return _append_execution_issue_entry(log=log, category=category, entry=entry).returncode == 0


def _append_force_bypass(st: BootstrapState) -> bool:
    if st.opts.force_requested != "true" or not st.opts.preflight_tmpdir:
        return True
    source = Path(st.opts.preflight_tmpdir) / "force-bypass.log"
    sentinel = Path(st.implement_tmpdir) / ".force-bypass-log-consumed"
    if not source.is_file() or sentinel.exists():
        return True
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    expected_issue = st.issue_number_resolved or st.opts.issue_number
    canonical = {"missing-plan", "malformed-plan", "missing-designed-prefix"}
    valid = bool(text.strip())
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.fullmatch(r"BYPASS kind=([a-z-]+) issue=([0-9]+)", stripped)
        if not match or match.group(1) not in canonical or match.group(2) != expected_issue:
            valid = False
            break
    if not valid:
        redacted = Path(st.implement_tmpdir) / "force-bypass.invalid-format.redacted.log"
        try:
            redacted.write_text(
                "Invalid force bypass log redacted.\n"
                f"EXPECTED_ISSUE={expected_issue}\n"
                "EXIT_CODE=99\n",
                encoding="utf-8",
            )
        except OSError:
            return False
        if not _append_failure_with_entry_fallback(
            st,
            site="implement-bootstrap force-bypass-log",
            tool="/implement --force preflight",
            exit_code="99",
            category="Warnings",
            output_file=redacted,
            status_label="invalid-format",
        ):
            return False
    sentinel.write_text("", encoding="utf-8")
    return True


_PLAN_PROVENANCE_PREFIXES = ("review_status:", "rounds_completed:")
_OPTIONAL_PLAN_SIZE_TRAILER_RE = re.compile(
    r"^(diff_added: [0-9]+|diff_deleted: [0-9]+|mechanical_churn: .+)$"
)


def _strip_plan_provenance_headers(text: str) -> str:
    lines = text.splitlines(keepends=True)
    diff_idx = -1
    in_fence = False
    in_fence_by_idx: list[bool] = []
    for idx, line in enumerate(lines):
        in_fence_by_idx.append(in_fence)
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if re.fullmatch(r"diff_lines: \d+", line.rstrip("\n")):
            diff_idx = idx
    if diff_idx < 0 or in_fence_by_idx[diff_idx]:
        return text

    idx = diff_idx - 1
    while idx >= 0:
        stripped = lines[idx].rstrip("\n")
        if in_fence_by_idx[idx] or not _OPTIONAL_PLAN_SIZE_TRAILER_RE.fullmatch(stripped):
            break
        idx -= 1

    remove: set[int] = set()
    while idx >= 0:
        stripped = lines[idx].rstrip("\n")
        if in_fence_by_idx[idx]:
            break
        if not any(stripped.startswith(prefix) for prefix in _PLAN_PROVENANCE_PREFIXES):
            break
        remove.add(idx)
        idx -= 1
    if not remove:
        return text
    return "".join(line for idx, line in enumerate(lines) if idx not in remove)


def _phase_plan(st: BootstrapState) -> None:
    st.plan_file = str(Path(st.implement_tmpdir) / "plan.txt")
    feature_file = Path(st.implement_tmpdir) / "feature-description.txt"
    if st.opts.resume_plan_tail:
        if not _append_force_bypass(st):
            st.emit_tmp_step_failed("force-bypass-log")
        if not _persist_run_flags(st):
            return
    else:
        snapshot = Path(st.implement_tmpdir) / "untracked-baseline.z"
        if not snapshot.exists():
            _run([sys.executable, str(_PY_CLI), "git", "snapshot-untracked", "--output", str(snapshot), "--nul"])
        if not _append_force_bypass(st):
            st.emit_tmp_step_failed("force-bypass-log")
        plan_src = Path(st.opts.preflight_tmpdir) / "plan-from-issue.txt"
        try:
            Path(st.plan_file).write_text(
                _strip_plan_provenance_headers(plan_src.read_text(encoding="utf-8", errors="replace")),
                encoding="utf-8",
            )
        except OSError as exc:
            (Path(st.implement_tmpdir) / "copy-plan.stderr.log").write_text(str(exc), encoding="utf-8")
            st.emit_tmp_step_failed("copy-plan")
        issue = st.issue_number_resolved or st.opts.issue_number
        if st.opts.forked_target == "true" and not st.opts.upstream_repo:
            (Path(st.implement_tmpdir) / "gh-issue-view.stderr.log").write_text(
                "--forked requires UPSTREAM_REPO before gh issue view\n",
                encoding="utf-8",
            )
            st.emit_tmp_step_failed("gh-issue-view")
        gh_args = ["gh", "issue", "view", issue, "--json", "title,body", "--template", "{{.title}}\n\n{{.body}}"]
        if st.opts.forked_target == "true" and st.opts.upstream_repo:
            gh_args[4:4] = ["--repo", st.opts.upstream_repo]
        gh = _run(gh_args)
        if gh.returncode != 0:
            (Path(st.implement_tmpdir) / "gh-issue-view.stderr.log").write_text(gh.stderr, encoding="utf-8")
            st.emit_tmp_step_failed("gh-issue-view")
        feature_file.write_text(gh.stdout, encoding="utf-8")
        if not _persist_run_flags(st):
            return
    dirty_lines = dirty_tree.checkpoint()
    dkv = _parse_kv("\n".join(dirty_lines))
    if dkv.get("STATUS") in {"dirty", "unknown"}:
        st.implement_bail_reason = "dirty-tree"
        return
    if st.opts.forked_target != "true" and st.is_user_branch != "true" and feature_file.is_file():
        title = feature_file.read_text(encoding="utf-8", errors="replace").splitlines()[0:1]
        raw = title[0] if title else "issue"
        slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", raw.lower())).strip("-")[:40].rstrip("-") or "issue"
        branch_name = f"{st.user_prefix}/{slug}-{st.issue_number_resolved}" if st.user_prefix and st.issue_number_resolved else ""
        if branch_name:
            created = _cli("pr", "create-branch", "--branch", branch_name)
            if created.returncode != 0:
                st.stall_tracking = "true"
                st.implement_bail_reason = "branch-create-failed"
                return
            st.branch_action = _parse_kv(created.stdout).get("ACTION", "")
    branch = _run([sys.executable, str(_PY_CLI), "git", "current-branch"])
    if branch.returncode == 0:
        st.branch_name = _parse_kv(branch.stdout).get("BRANCH", "")
    if not st.branch_name:
        st.stall_tracking = "true"
        st.implement_bail_reason = "branch-create-failed"
        return
    issue = st.issue_number_resolved or st.opts.issue_number
    title = feature_file.read_text(encoding="utf-8", errors="replace").splitlines()[0] if feature_file.is_file() else "planned change"
    goal = f"Implement issue #{issue}: {title or 'planned change'}."
    planlog = _run([sys.executable, str(_PY_CLI), "plan", "step1-log", "--implement-tmpdir", st.implement_tmpdir, "--goal-text", goal])
    (Path(st.implement_tmpdir) / "run-step1-plan-log.out").write_text(planlog.stdout, encoding="utf-8")
    _publish_plan_review_tally(st)
    _upsert_plan_summary(st)
    _err(f"→ step0: branch {st.branch_name} + plan logged")


def _publish_plan_review_tally(st: BootstrapState) -> None:
    if not _valid_run_id(st.run_id):
        return
    preflight = Path(st.opts.preflight_tmpdir) if st.opts.preflight_tmpdir else Path()
    for candidate in (
        preflight / "plan-review-tally.json",
        preflight / "voting-tally.json",
        Path(st.implement_tmpdir) / "plan-review-tally.json",
    ):
        if not candidate.is_file():
            continue
        _cli(
            "run-log",
            "write",
            "--log-root",
            str(Path(st.implement_tmpdir) / "larch-logs"),
            "--skill",
            "implement",
            "--run-id",
            st.run_id,
            "--batch",
            "plan-review-tally",
            "--input-file",
            str(candidate),
        )
        return


def _upsert_plan_summary(st: BootstrapState) -> None:
    issue = st.issue_number_resolved or st.opts.issue_number
    if not issue or not _valid_run_id(st.run_id) or not st.plan_file:
        return
    content = Path(st.implement_tmpdir) / "summary-plan.md"
    try:
        plan_text = Path(st.plan_file).read_text(encoding="utf-8", errors="replace")
        content.write_text(plan_text[:12000], encoding="utf-8")
    except OSError:
        return
    cli_args = [
        "tracking-issue", "upsert-summary",
        "--issue", issue,
        "--marker", f"<!-- larch:plan v1 runid={st.run_id} -->",
        "--content-file", str(content),
    ]
    if st.opts.forked_target == "true" and st.opts.upstream_repo:
        cli_args.extend(["--repo", st.opts.upstream_repo])
    elif st.repo:
        cli_args.extend(["--repo", st.repo])
    _cli(*cli_args)


def _record_coder_fallback(*, st: BootstrapState, reason: str) -> None:
    if st.coder_fallback != "true" or not st.implement_tmpdir:
        return
    warning = "**⚠ Cursor and Codex unavailable — implementing with main agent.**\n"
    _err(warning.rstrip("\n"))
    diag = Path(st.implement_tmpdir) / "coder-fallback-warning.txt"
    with contextlib.suppress(OSError):
        diag.write_text(f"{warning}REASON={reason}\n", encoding="utf-8")
    if diag.is_file():
        _cli(
            "run-log",
            "append-failure",
            "--log",
            str(Path(st.implement_tmpdir) / "execution-issues.md"),
            "--site",
            "implement-bootstrap coder-select",
            "--tool",
            "phase_coder_select",
            "--exit-code",
            "0",
            "--category",
            "Warnings",
            "--output-file",
            str(diag),
            "--status-label",
            "fallback",
            "--redact",
        )
    if _valid_run_id(st.run_id):
        _cli(
            "run-log",
            "manifest",
            "--log-root",
            str(Path(st.implement_tmpdir) / "larch-logs"),
            "--skill",
            "implement",
            "--run-id",
            st.run_id,
            "--field",
            "coder_fallback=true",
        )


def _record_explicit_coder_unavailable(*, st: BootstrapState, requested: str, selected: str) -> None:
    if not st.implement_tmpdir:
        return
    warning = f"**⚠ Requested {requested} implementer unavailable — using {selected}.**\n"
    _err(warning.rstrip("\n"))
    diag = Path(st.implement_tmpdir) / f"{requested}-unavailable-warning.txt"
    with contextlib.suppress(OSError):
        diag.write_text(f"{warning}REQUESTED={requested}\nSELECTED={selected}\n", encoding="utf-8")
    if diag.is_file():
        _cli(
            "run-log",
            "append-failure",
            "--log",
            str(Path(st.implement_tmpdir) / "execution-issues.md"),
            "--site",
            "implement-bootstrap coder-select",
            "--tool",
            "phase_coder_select",
            "--exit-code",
            "0",
            "--category",
            "Warnings",
            "--output-file",
            str(diag),
            "--status-label",
            "fallback",
            "--redact",
        )


def _phase_coder(st: BootstrapState) -> None:
    if st.implement_bail_reason or st.stall_tracking == "true":
        return
    if st.repo_unavailable == "true" or not st.plan_file or not Path(st.plan_file).is_file() or not (Path(st.implement_tmpdir) / "feature-description.txt").is_file():
        return
    if st.opts.force_requested == "true" or st.opts.coder_opt == "claude":
        st.coder = "claude"
    else:
        order = list(external_defaults.tool_order("implement.step2_coder"))
        if st.opts.coder_opt in {"codex", "cursor"}:
            other = "cursor" if st.opts.coder_opt == "codex" else "codex"
            order = [st.opts.coder_opt, other, "claude"]
        for candidate in order:
            if candidate == "codex" and st.codex_available != "true":
                continue
            if candidate == "cursor" and st.cursor_available != "true":
                continue
            st.coder = candidate
            break
        if not st.coder:
            st.coder = "claude"
        if st.coder == "claude":
            st.coder_fallback = "true"
    requested_available = (
        (st.opts.coder_opt == "codex" and st.codex_available == "true")
        or (st.opts.coder_opt == "cursor" and st.cursor_available == "true")
    )
    if st.opts.coder_opt in {"codex", "cursor"} and st.coder != st.opts.coder_opt and not requested_available:
        _record_explicit_coder_unavailable(st=st, requested=st.opts.coder_opt, selected=st.coder)
    if st.coder_fallback == "true":
        _record_coder_fallback(st=st, reason="requested external coder unavailable")
    _err(f"→ step0: coder={st.coder}")


def _emit_final(st: BootstrapState) -> None:
    for key, value in (
        ("CURRENT_BRANCH", st.current_branch),
        ("IS_MAIN", st.is_main),
        ("IS_USER_BRANCH", st.is_user_branch),
        ("USER_PREFIX", st.user_prefix),
        ("ENTRY_GATE", st.entry_gate),
        ("SKIP_BRANCH_CHECK", st.skip_branch_check),
        ("IMPLEMENT_TMPDIR", st.implement_tmpdir),
        ("SESSION_ID", st.session_id),
        ("CODEX_BINARY_FOUND", st.codex_binary_found),
        ("CURSOR_BINARY_FOUND", st.cursor_binary_found),
        ("REPO", st.repo),
        ("REPO_UNAVAILABLE", st.repo_unavailable),
        ("codex_available", st.codex_available),
        ("cursor_available", st.cursor_available),
        ("ISSUE_NUMBER", st.issue_number_resolved or st.opts.issue_number),
        ("RUN_ID", st.run_id),
        ("BRANCH_SELECTED", st.branch_selected),
        ("DEFERRED", st.deferred),
        ("STALL_TRACKING", st.stall_tracking),
        ("BRANCH_NAME", st.branch_name),
        ("BRANCH_ACTION", st.branch_action),
        ("PLAN_FILE", st.plan_file),
        ("FORCE_REQUESTED", st.opts.force_requested),
        ("SELF_REVIEW_REQUESTED", st.opts.self_review_requested),
        ("coder", st.coder),
        ("coder_fallback", st.coder_fallback),
        ("IMPLEMENT_BAIL_REASON", st.implement_bail_reason),
    ):
        _emit_kv(key=key, value=value)


def run_bootstrap(opts: BootstrapOptions) -> int:
    st = BootstrapState(opts)
    try:
        _phase_infra(st)
        if opts.up_to_phase in {"tracking", "plan", "coder", "all"}:
            _phase_tracking(st)
            if _valid_run_id(st.run_id):
                _write_base_session_env(st)
        if opts.up_to_phase in {"plan", "coder", "all"} and not st.implement_bail_reason and st.stall_tracking != "true" and st.repo_unavailable != "true":
            _phase_plan(st)
        if opts.up_to_phase in {"coder", "all"} and not st.implement_bail_reason and st.stall_tracking != "true":
            _phase_coder(st)
        _emit_final(st)
        return 0
    except BootstrapExit as exc:
        return exc.code
    except Exception as exc:
        _emit_kv(key="STEP_FAILED", value="internal-error")
        if st.implement_tmpdir:
            with contextlib.suppress(OSError):
                (Path(st.implement_tmpdir) / "bootstrap-internal-error.log").write_text(_single_line(str(exc)) + "\n", encoding="utf-8")
        return BOOTSTRAP_CONTRACT_FAILURE


def bootstrap_main(argv: list[str]) -> int:
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    parser = argparse.ArgumentParser(prog="bootstrap internal", add_help=True)
    parser.add_argument("--up-to-phase", required=True, choices=["infra", "tracking", "plan", "coder", "all"])
    parser.add_argument("--caller-env", default="")
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--forked-target", default="false", choices=["true", "false"])
    parser.add_argument("--merge-requested", default="false", choices=["true", "false"])
    parser.add_argument("--draft-requested", default="false", choices=["true", "false"])
    parser.add_argument("--no-admin-fallback", default="false", choices=["true", "false"])
    parser.add_argument("--no-logs-commit", default="false", choices=["true", "false"])
    parser.add_argument("--force-requested", default="false", choices=["true", "false"])
    parser.add_argument("--self-review-requested", default="false", choices=["true", "false"])
    parser.add_argument("--upstream-repo", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--coder", default="", choices=["", "claude", "codex", "cursor"])
    parser.add_argument("--preflight-tmpdir", default="")
    parser.add_argument("--resume-plan-tail", action="store_true")
    parser.add_argument("--skip-codex-probe", action="store_true")
    parser.add_argument("--skip-cursor-probe", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if int(exc.code or 0) != 0 else 0
    if args.issue_number and not args.issue_number.isdigit():
        print("bootstrap: --issue-number must be numeric", file=sys.stderr)
        return 2
    if args.upstream_repo and re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", args.upstream_repo) is None:
        print("bootstrap: --upstream-repo must be OWNER/REPO", file=sys.stderr)
        return 2
    if args.up_to_phase in {"plan", "coder", "all"} and args.issue_number and not args.preflight_tmpdir:
        print("bootstrap: --preflight-tmpdir is required with --issue-number when --up-to-phase is plan, coder, or all", file=sys.stderr)
        return 2
    opts = BootstrapOptions(
        up_to_phase=args.up_to_phase,
        caller_env=args.caller_env,
        issue_number=args.issue_number,
        forked_target=args.forked_target,
        merge_requested=args.merge_requested,
        draft_requested=args.draft_requested,
        no_admin_fallback=args.no_admin_fallback,
        no_logs_commit=args.no_logs_commit,
        force_requested=args.force_requested,
        self_review_requested=args.self_review_requested,
        upstream_repo=args.upstream_repo,
        run_id=args.run_id,
        preflight_tmpdir=args.preflight_tmpdir,
        coder_opt=args.coder,
        resume_plan_tail=args.resume_plan_tail,
        skip_codex_probe=args.skip_codex_probe,
        skip_cursor_probe=args.skip_cursor_probe,
    )
    return run_bootstrap(opts)


def _filtered_envelope(text: str, *, resume: bool) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not _KEY_RE.fullmatch(key) or key not in ROUTING_KEYS:
            continue
        if resume and key in {"coder", "coder_fallback"} and not value:
            continue
        lines.append(f"{key}={value}")
    return "\n".join(lines) + ("\n" if lines else "")


def _routing_file_trusted(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _restore_resume_coder(*, data: dict[str, str], routing_file: Path, tmpdir: str) -> None:
    if data.get("coder"):
        return
    sources: list[Path] = []
    if routing_file.exists() and _routing_file_trusted(routing_file):
        sources.append(routing_file)
    sources.extend((Path(tmpdir) / "session-env.sh", Path(tmpdir) / "run-flags.sh"))
    for path in sources:
        if not path.is_file():
            continue
        try:
            prior = _parse_env_lines(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        for key in ("coder", "coder_fallback"):
            if prior.get(key) and not data.get(key):
                data[key] = prior[key]
        if data.get("coder"):
            return
    for path in (Path(tmpdir) / "session-env.sh", Path(tmpdir) / "run-flags.sh"):
        if not path.is_file():
            continue
        if not data.get("coder"):
            value = _read_key(path=path, key="coder", default="")
            if value in {"claude", "codex", "cursor"}:
                data["coder"] = value
        if not data.get("coder_fallback"):
            value = _read_key(path=path, key="coder_fallback", default="")
            if value:
                data["coder_fallback"] = value
        if data.get("coder"):
            return


def _step2_blockers(data: dict[str, str]) -> bool:
    if data.get("REPO_UNAVAILABLE") == "true":
        return True
    plan = data.get("PLAN_FILE", "")
    if not plan or not Path(plan).is_file():
        return True
    tmpdir = data.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        return False
    tmp = Path(tmpdir)
    return not (tmp / "plan.txt").is_file() or not (tmp / "feature-description.txt").is_file()


def _preserve_resume_routing(*, envelope: str, routing_file: Path) -> str:
    if not routing_file.is_file() or routing_file.is_symlink():
        return envelope
    try:
        prior = _parse_env_lines(routing_file.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return envelope
    data = _parse_env_lines(envelope)
    changed = False
    for key in ("coder", "coder_fallback"):
        if not data.get(key) and prior.get(key):
            data[key] = prior[key]
            changed = True
    if not changed:
        return envelope
    lines = [f"{key}={data[key]}" for key in ROUTING_KEYS if data.get(key)]
    return "\n".join(lines) + ("\n" if lines else "")


def _redact_text(text: str, *, implement_tmpdir: str = "") -> str:
    current = text
    # The CLI redactors are stdin filters. If either filter fails, prefer a
    # fixed diagnostic over returning raw stderr from plan or gh helpers.
    tmpdir = subprocess.run(
        [sys.executable, str(_PY_CLI), "redact", "tmpdir-paths"],
        input=current,
        capture_output=True,
        text=True,
        errors="replace",
        env={**os.environ, "IMPLEMENT_TMPDIR": implement_tmpdir} if implement_tmpdir else os.environ.copy(),
        check=False,
    )
    if tmpdir.returncode != 0:
        return "diagnostic redaction failed\n"
    current = tmpdir.stdout
    secrets = subprocess.run(
        [sys.executable, str(_PY_CLI), "redact", "secrets"],
        input=current,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    if secrets.returncode != 0:
        return "diagnostic redaction failed\n"
    return secrets.stdout


def _redact_file(path: Path, *, implement_tmpdir: str = "") -> str:
    if not path.is_file():
        return ""
    return _redact_text(path.read_text(encoding="utf-8", errors="replace"), implement_tmpdir=implement_tmpdir)


def _invoke_error(*, step_failed: str, out: str, implement_tmpdir: str) -> None:
    lines = [line for line in out.splitlines() if line.startswith(("STEP_FAILED=", "GATE_ERROR=", "PREFLIGHT_ERROR="))]
    for line in lines:
        print(line, file=sys.stderr)
    messages = {
        "session-entry-gate": "**⚠ /implement: internal Step 0 contract violation in session-entry-gate.sh. Aborting.**",
        "session-setup": "**⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run; (c) commit or stash uncommitted changes on `main` first.**",
        "get-issue-state": "**⚠ /implement Step 0 tracking: could not verify the adopted issue state. Aborting.**",
        "issue-number-required-for-resume": "**⚠ /implement Step 0 tracking: --issue-number is required to resume an adopted tracking sentinel. Re-run `/implement <issue-N>` for the sentinel's issue.**",
        "copy-plan": "**⚠ /implement Step 0 plan materialization: could not copy the preflight plan into the implement session. Aborting.**",
        "gh-issue-view": "**⚠ /implement Step 0 plan materialization: could not read the issue title/body. Aborting.**",
        "resume-plan-tail-sentinel": "**⚠ /implement Step 0 dirty-tree recovery: the resume tail could not validate tracking state from the existing session artifacts. Restore or inspect `$IMPLEMENT_TMPDIR`, then restart `/implement`.**",
        "create-branch": "**⚠ /implement Step 0: could not verify branch state before bootstrap. Aborting.**",
        "write-session-env": "**⚠ /implement Step 0: could not write session environment. Aborting.**",
        "larch-run": "**⚠ /implement Step 0: could not write the session launcher. Aborting.**",
        "degraded-both-down-hard-fail": "**⚠ /implement Step 0: both Codex and Cursor are unavailable after health probes. Aborting.**",
        "force-bypass-log": "**⚠ /implement Step 0: force bypass log handling failed. Aborting.**",
    }
    if step_failed in {"copy-plan", "gh-issue-view"} and implement_tmpdir:
        log = Path(implement_tmpdir) / ("copy-plan.stderr.log" if step_failed == "copy-plan" else "gh-issue-view.stderr.log")
        if log.is_file():
            sys.stderr.write(_redact_file(log, implement_tmpdir=implement_tmpdir))
    if step_failed == "absorbed-degraded-gate" and out.strip():
        detail = out if out.endswith("\n") else out + "\n"
        sys.stderr.write(detail)
    print(messages.get(step_failed, f"**⚠ /implement Step 0 bootstrap failed at step={step_failed or 'unknown'}. Aborting.**"), file=sys.stderr)


def _str_bool(value: str) -> str:
    return value if value in {"true", "false"} else ""


def _is_advisory_stdout_key(key: str) -> bool:
    return any(key.startswith(prefix) for prefix in _ADVISORY_STDOUT_PREFIXES)


def _envelope_text(data: dict[str, str]) -> str:
    lines = [f"{key}={data[key]}" for key in ROUTING_KEYS if data.get(key)]
    return "\n".join(lines) + ("\n" if lines else "")


_GATE_STDERR_KV_PREFIXES: tuple[str, ...] = (
    "DEGRADED=",
    "BOTH_DOWN=",
    "CODEX_STATE=",
    "CURSOR_STATE=",
    "PRESENCE_INPUT_EMPTY=",
    "DEGRADED_HARD_FAIL=",
)


def _parent_invocation_non_interactive() -> bool:
    def ps_query(*, field: str, pid_value: int) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                [_PS, "-o", field, "-p", str(pid_value)],
                capture_output=True,
                text=True,
                errors="replace",
                check=False,
            )
        except OSError:
            return None

    pid = os.getppid()
    visited: set[int] = set()
    for _ in range(8):
        if pid <= 1 or pid in visited:
            break
        visited.add(pid)
        comm = ps_query(field="comm=", pid_value=pid)
        if comm is None:
            return False
        if comm.returncode == 0:
            comm_name = comm.stdout.strip().lower()
            if comm_name in {"cron", "crond"} or "cron" in comm_name:
                return True
        args = ps_query(field="args=", pid_value=pid)
        if args is None:
            return False
        if args.returncode == 0:
            args_line = args.stdout.strip()
            if args_line:
                lower = args_line.lower()
                if "<<autonomous-loop" in lower:
                    return True
                if re.search(r"\bclaude\b", lower) and re.search(r"(?:\s|^)(?:-p\b|--print\b)", lower):
                    return True
        ppid = ps_query(field="ppid=", pid_value=pid)
        if ppid is None:
            return False
        if ppid.returncode != 0:
            break
        try:
            pid = int(ppid.stdout.strip())
        except ValueError:
            break
    return False


def _relay_gate_stderr(stderr: str, *, force_all: bool = False) -> None:
    if not stderr.strip():
        return
    if force_all:
        for line in stderr.splitlines():
            if line.strip():
                _err(line)
        return
    for line in stderr.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in {"DEGRADED_EXPLANATION_BEGIN", "DEGRADED_EXPLANATION_END"}:
            continue
        if any(stripped.startswith(prefix) for prefix in _GATE_STDERR_KV_PREFIXES):
            continue
        _err(line)


def _resolve_non_interactive(
    *, explicit: str,
    env: Mapping[str, str] | None = None,
) -> bool:
    if explicit in {"true", "false"}:
        return explicit == "true"
    runtime = env or os.environ
    for key in ("LARCH_SKILL_NON_INTERACTIVE", "LARCH_AUTONOMOUS_LOOP", "LARCH_EVAL_RUN", "LARCH_CRON"):
        if runtime.get(key, "") == "true":
            return True
    if runtime.get("CLAUDE_CODE_SUBAGENT", "").lower() in {"1", "true", "yes"}:
        return True
    return _parent_invocation_non_interactive()


def resolve_non_interactive_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap resolve-non-interactive", add_help=True)
    parser.add_argument("--explicit", default="", choices=["", "true", "false"])
    args = parser.parse_args(argv)
    print("true" if _resolve_non_interactive(explicit=args.explicit) else "false")
    return 0


def _resolve_probe_cwd() -> Path:
    git = shutil.which("git")
    if git is None:
        return _REPO_ROOT
    result = subprocess.run(
        [git, "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        top = result.stdout.strip()
        if top:
            return Path(top)
    return _REPO_ROOT


def _continue_predicate(data: dict[str, str]) -> bool:
    if data.get("IMPLEMENT_BAIL_REASON"):
        return False
    if data.get("STALL_TRACKING") == "true":
        return False
    if _step2_blockers(data):
        return False
    return bool(data.get("coder"))


def _bootstrap_next(data: dict[str, str], *, continue_tail_attempted: bool) -> str:
    next_step = "cleanup"
    if data.get("DEGRADED_PROMPT_REQUIRED") == "true":
        next_step = "degraded-prompt"
    else:
        route = data.get("ROUTE", "")
        bail_reason = data.get("IMPLEMENT_BAIL_REASON", "")
        if route in {"conflict", "bail"} and not _step2_blockers(data):
            next_step = "rebase-routing"
        elif bail_reason == "dirty-tree":
            next_step = "dirty-recovery"
        elif _step2_blockers(data) or bail_reason or data.get("STALL_TRACKING") == "true":
            next_step = "cleanup"
        elif continue_tail_attempted and route not in {"continue", "conflict", "bail"}:
            next_step = "rebase-routing"
        elif route == "continue" and data.get("coder"):
            next_step = "step2"
    return next_step


def _merge_tail_routing_and_next(
    data: dict[str, str],
    *,
    tail: ContinueTailResult,
    continue_tail_attempted: bool,
) -> None:
    data.update({key: value for key, value in tail.routing.items() if value})
    data["BOOTSTRAP_NEXT"] = _bootstrap_next(data, continue_tail_attempted=continue_tail_attempted)


@dataclass(frozen=True)
class ContinueTailResult:
    routing: dict[str, str] = field(default_factory=dict)
    advisory_lines: list[str] = field(default_factory=list)
    contract_failure: bool = False
    step_failed: str = ""
    failure_detail: str = ""


def _parse_gate_output(text: str) -> tuple[dict[str, str], list[str], str]:
    routing: dict[str, str] = {}
    explanation: list[str] = []
    in_explanation = False
    for line in text.splitlines():
        if line == "DEGRADED_EXPLANATION_BEGIN":
            in_explanation = True
            continue
        if line == "DEGRADED_EXPLANATION_END":
            in_explanation = False
            continue
        if in_explanation:
            explanation.append(line)
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"DEGRADED", "BOTH_DOWN", "DEGRADED_HARD_FAIL", "CODEX_STATE", "CURSOR_STATE", "PRESENCE_INPUT_EMPTY"}:
            routing[key] = value
    return routing, explanation, "\n".join(explanation).strip()


def _parse_probe_stdout(text: str) -> tuple[dict[str, str], list[str]]:
    routing: dict[str, str] = {}
    advisory: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            if _is_advisory_stdout_key(key):
                advisory.append(f"{key}={value}")
                continue
            if key in ROUTING_KEYS:
                routing[key] = value
                continue
        for token in line.split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            if _is_advisory_stdout_key(key):
                advisory.append(f"{key}={value}")
            elif key in ROUTING_KEYS:
                routing[key] = value
    return routing, advisory



def _refresh_gate_probe(st: BootstrapState) -> str | None:
    args = ["agent", "check-reviewers"]
    result = _cli(*args)
    if result.returncode != 0:
        result = _cli(*args)
        if result.returncode != 0:
            return "absorbed-gate-probe-refresh-failed"
    kv = _parse_kv(result.stdout)
    st.codex_present = kv.get("CODEX_PRESENT", st.codex_present)
    st.cursor_present = kv.get("CURSOR_PRESENT", st.cursor_present)
    st.codex_binary_found = kv.get("CODEX_BINARY_FOUND", st.codex_binary_found)
    st.cursor_binary_found = kv.get("CURSOR_BINARY_FOUND", st.cursor_binary_found)
    return None

def _run_1r_probe(st: BootstrapState, *, forked_target: str) -> tuple[dict[str, str], list[str], int]:
    env = {**os.environ, "IMPLEMENT_TMPDIR": st.implement_tmpdir}
    result = _run(
        [
            sys.executable,
            str(_PY_CLI),
            "push",
            "checkpoint-probe",
            "1.r",
            "plan materialization",
            "--forked-target",
            forked_target if forked_target in {"true", "false"} else "false",
        ],
        env=env,
        cwd=str(_resolve_probe_cwd()),
    )
    routing, advisory = _parse_probe_stdout(result.stdout)
    routing["REBASE_RC"] = str(result.returncode)
    route = routing.get("ROUTE", "")
    if route not in {"continue", "conflict", "bail"}:
        routing["ROUTE"] = "bail"
        routing["CHECKPOINT_NEXT"] = "load-routing"
        routing.setdefault("REBASE_OUTCOME", "failed")
        error = _single_line(result.stderr or result.stdout or f"probe rc {result.returncode}")
        routing["REBASE_ERROR"] = _redact_text(error, implement_tmpdir=st.implement_tmpdir)
    elif routing.get("CHECKPOINT_NEXT", "") not in {"continue", "load-routing"}:
        routing["CHECKPOINT_NEXT"] = "load-routing"
    return routing, advisory, result.returncode


def _run_absorbed_continue_tail(
  data: dict[str, str],
  *,
  opts: BootstrapOptions,
  non_interactive: bool,
) -> ContinueTailResult:
    if not _continue_predicate(data):
        return ContinueTailResult()
    tmpdir = data.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        return ContinueTailResult(contract_failure=True, step_failed="absorbed-continue-tail")
    st = BootstrapState(opts, implement_tmpdir=tmpdir)
    st.codex_present = data.get("CODEX_PRESENT", st.codex_present)
    st.cursor_present = data.get("CURSOR_PRESENT", st.cursor_present)
    st.codex_binary_found = data.get("CODEX_BINARY_FOUND", st.codex_binary_found)
    st.cursor_binary_found = data.get("CURSOR_BINARY_FOUND", st.cursor_binary_found)
    probe_failed = _refresh_gate_probe(st)
    if probe_failed:
        return ContinueTailResult(contract_failure=True, step_failed=probe_failed)
    forked_target = opts.forked_target if opts.forked_target in {"true", "false"} else "false"
    sentinel = Path(tmpdir) / ".degraded-tools-gate-prompted"
    sentinel_exists = sentinel.is_file()
    gate = _cli(
        "agent",
        "degraded-tools-gate",
        "--skill",
        "implement",
        "--codex-present",
        st.codex_present,
        "--cursor-present",
        st.cursor_present,
        "--codex-binary-found",
        st.codex_binary_found or "unknown",
        "--cursor-binary-found",
        st.cursor_binary_found or "unknown",
    )
    if gate.returncode != 0:
        gate_diag = (gate.stderr or "").strip()
        if gate.stdout and gate.stdout.strip():
            gate_diag = f"{gate_diag}\n{gate.stdout.strip()}".strip() if gate_diag else gate.stdout.strip()
        detail = _redact_text(gate_diag, implement_tmpdir=tmpdir) if gate_diag else ""
        return ContinueTailResult(
            contract_failure=True,
            step_failed="absorbed-degraded-gate",
            failure_detail=detail,
        )
    gate_text = gate.stdout + gate.stderr
    gate_routing, explanation_lines, explanation_text = _parse_gate_output(gate_text)
    _relay_gate_stderr(
        gate.stderr,
        force_all=gate_routing.get("PRESENCE_INPUT_EMPTY") == "true",
    )
    both_down_seen = "BOTH_DOWN" in gate_routing
    both_down = gate_routing.get("BOTH_DOWN", "")
    degraded = gate_routing.get("DEGRADED", "false") == "true"
    routing: dict[str, str] = {
        "DEGRADED": gate_routing.get("DEGRADED", "false"),
        "CODEX_STATE": gate_routing.get("CODEX_STATE", ""),
        "CURSOR_STATE": gate_routing.get("CURSOR_STATE", ""),
        "DEGRADED_PROMPT_REQUIRED": "false",
    }
    if gate_routing.get("DEGRADED_HARD_FAIL") == "true":
        routing["DEGRADED_HARD_FAIL"] = "true"
    if gate_routing.get("BOTH_DOWN") in {"true", "false"}:
        routing["BOTH_DOWN"] = gate_routing["BOTH_DOWN"]
    if gate_routing.get("PRESENCE_INPUT_EMPTY") == "true":
        _append_execution_issue_entry(
            log=Path(tmpdir) / "execution-issues.md",
            category="Warnings",
            entry="- **Step 0 degraded-tools gate**: PRESENCE_INPUT_EMPTY=true (caller rehydration warning)\n",
        )
    prompt_required = False
    run_probe = True
    if degraded:
        if not explanation_text:
            return ContinueTailResult(contract_failure=True, step_failed="absorbed-degraded-explanation-missing")
        if not both_down_seen:
            if non_interactive:
                return ContinueTailResult(contract_failure=True, step_failed="absorbed-both-down-missing")
            for line in explanation_lines:
                _err(line)
            prompt_required = True
            run_probe = False
        elif both_down == "false":
            if not sentinel_exists:
                for line in explanation_lines:
                    _err(line)
                prompt_required = True
                run_probe = False
        elif both_down == "true":
            for line in explanation_lines:
                _err(line)
            routing["DEGRADED_HARD_FAIL"] = "true"
            return ContinueTailResult(
                routing=routing,
                contract_failure=True,
                step_failed="degraded-both-down-hard-fail",
                failure_detail=explanation_text,
            )
        else:
            if non_interactive:
                return ContinueTailResult(contract_failure=True, step_failed="absorbed-both-down-missing")
            for line in explanation_lines:
                _err(line)
            prompt_required = True
            run_probe = False
    advisory: list[str] = []
    if prompt_required:
        routing["DEGRADED_PROMPT_REQUIRED"] = "true"
    elif run_probe:
        probe_routing, probe_advisory, _probe_rc = _run_1r_probe(st, forked_target=forked_target)
        routing.update({key: value for key, value in probe_routing.items() if value})
        if _step2_blockers({**data, **routing}):
            routing.pop("ROUTE", None)
        advisory.extend(probe_advisory)
    return ContinueTailResult(routing=routing, advisory_lines=advisory)


def invoke_main(argv: list[str]) -> int:
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    parser = argparse.ArgumentParser(prog="bootstrap invoke", add_help=True)
    parser.add_argument("--mode", required=True, choices=["initial", "resume"])
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--forked-target", default="", choices=["", "true", "false"])
    parser.add_argument("--merge-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--draft-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--no-admin-fallback", default="", choices=["", "true", "false"])
    parser.add_argument("--no-logs-commit", default="", choices=["", "true", "false"])
    parser.add_argument("--upstream-repo", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--coder", default="", choices=["", "claude", "codex", "cursor"])
    parser.add_argument("--preflight-tmpdir", default="")
    parser.add_argument("--caller-env", default="")
    parser.add_argument("--force-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--self-review-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--non-interactive", default="", choices=["", "true", "false"])
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 1 if int(exc.code or 0) != 0 else 0
    env = os.environ
    issue = args.issue_number or env.get("TARGET_ISSUE_NUMBER") or env.get("ISSUE_NUMBER", "")
    caller_env = args.caller_env or env.get("CALLER_ENV_PATH") or env.get("SESSION_ENV_PATH", "")
    preflight = args.preflight_tmpdir or env.get("PREFLIGHT_TMPDIR", "")
    forked = args.forked_target or env.get("forked_target") or (env.get("FORKED_TARGET", "") if not env.get("forked_target") else "") or "false"
    upstream = args.upstream_repo or env.get("UPSTREAM_REPO", "")
    run_id = args.run_id or env.get("RUN_ID", "")
    implement_tmpdir_env = env.get("IMPLEMENT_TMPDIR", "")
    seed_file = Path(implement_tmpdir_env) / "ship-seed-input.env" if implement_tmpdir_env else Path()
    resume_seed = args.mode == "resume"
    merge_requested = (
        args.merge_requested
        or _str_bool(env.get("merge", ""))
        or _str_bool(env.get("MERGE", ""))
        or (_read_simple_kv(path=seed_file, key="MERGE") if resume_seed else "")
        or "false"
    )
    draft_requested = (
        args.draft_requested
        or _str_bool(env.get("draft", ""))
        or _str_bool(env.get("DRAFT", ""))
        or (_read_simple_kv(path=seed_file, key="DRAFT") if resume_seed else "")
        or "false"
    )
    no_admin_fallback = (
        args.no_admin_fallback
        or _str_bool(env.get("no_admin_fallback", ""))
        or _str_bool(env.get("NO_ADMIN_FALLBACK", ""))
        or (_read_simple_kv(path=seed_file, key="NO_ADMIN_FALLBACK") if resume_seed else "")
        or "false"
    )
    no_logs_commit = (
        args.no_logs_commit
        or _str_bool(env.get("no_logs_commit", ""))
        or _str_bool(env.get("NO_LOGS_COMMIT", ""))
        or (_read_simple_kv(path=seed_file, key="NO_LOGS_COMMIT") if resume_seed else "")
        or "false"
    )
    force = args.force_requested or _str_bool(env.get("force_requested", "")) or "false"
    self_review = args.self_review_requested or _str_bool(env.get("self_review", "")) or "false"
    non_interactive = args.non_interactive or _str_bool(env.get("non_interactive", "")) or ""
    coder = "" if args.mode == "resume" else (args.coder or env.get("coder", ""))
    if args.mode == "resume" and not env.get("IMPLEMENT_TMPDIR", ""):
        print("bootstrap invoke: --mode resume requires exported IMPLEMENT_TMPDIR", file=sys.stderr)
        return 1
    opts = BootstrapOptions(
        up_to_phase="coder" if args.mode == "initial" else "plan",
        caller_env=caller_env,
        issue_number=issue,
        forked_target=forked if forked in {"true", "false"} else "false",
        merge_requested=_bool_text(value=merge_requested),
        draft_requested=_bool_text(value=draft_requested),
        no_admin_fallback=_bool_text(value=no_admin_fallback),
        no_logs_commit=_bool_text(value=no_logs_commit),
        force_requested=force if force in {"true", "false"} else "false",
        self_review_requested=self_review if self_review in {"true", "false"} else "false",
        upstream_repo=upstream,
        run_id=run_id,
        preflight_tmpdir=preflight,
        coder_opt=coder if coder in {"claude", "codex", "cursor"} else "",
        resume_plan_tail=args.mode == "resume",
        non_interactive=non_interactive,
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_bootstrap(opts)
    out = buf.getvalue()
    if rc == BOOTSTRAP_CONTRACT_FAILURE:
        kv = _parse_kv(out)
        _invoke_error(step_failed=kv.get("STEP_FAILED", ""), out=out, implement_tmpdir=kv.get("IMPLEMENT_TMPDIR", ""))
        return 2
    if rc != 0:
        return rc
    tmpdir = _parse_kv(out).get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        print("bootstrap invoke: bootstrap success missing IMPLEMENT_TMPDIR", file=sys.stderr)
        return 1
    envelope = _filtered_envelope(out, resume=args.mode == "resume")
    routing_file = Path(tmpdir) / "bootstrap-routing.env"
    routing_trusted = _routing_file_trusted(routing_file)
    if args.mode == "resume" and routing_trusted:
        envelope = _preserve_resume_routing(envelope=envelope, routing_file=routing_file)
    data = _parse_env_lines(envelope)
    if args.mode == "resume":
        _restore_resume_coder(data=data, routing_file=routing_file, tmpdir=tmpdir)
    continue_tail_attempted = _continue_predicate(data)
    tail = _run_absorbed_continue_tail(
        data,
        opts=opts,
        non_interactive=_resolve_non_interactive(explicit=non_interactive, env=env),
    )
    if tail.contract_failure:
        _emit_kv(key="STEP_FAILED", value=tail.step_failed or "absorbed-continue-tail")
        _invoke_error(step_failed=tail.step_failed or "absorbed-continue-tail", out=tail.failure_detail, implement_tmpdir=tmpdir)
        return 2
    _merge_tail_routing_and_next(data, tail=tail, continue_tail_attempted=continue_tail_attempted)
    envelope = _envelope_text(data)
    try:
        _merge_write_ship_seed_input(
            tmpdir=tmpdir,
            values={
                "MERGE": _bool_text(value=opts.merge_requested),
                "DRAFT": _bool_text(value=opts.draft_requested),
                "FORKED_TARGET": _bool_text(value=opts.forked_target),
                "NO_ADMIN_FALLBACK": _bool_text(value=opts.no_admin_fallback),
                "NO_LOGS_COMMIT": _bool_text(value=opts.no_logs_commit),
                "DEFERRED": _bool_text(value=data.get("DEFERRED", "false")),
            },
            only_missing=args.mode == "resume",
        )
    except OSError as exc:
        print(f"bootstrap invoke: could not write ship-seed-input.env ({exc})", file=sys.stderr)
        if args.mode == "initial":
            return 2

    def _emit_envelope() -> None:
        sys.stdout.write(envelope)
        for line in tail.advisory_lines:
            sys.stdout.write(line + "\n")

    if routing_file.is_symlink():
        print("bootstrap invoke: refusing to overwrite symlinked bootstrap-routing.env (stdout envelope emitted)", file=sys.stderr)
        _emit_envelope()
        return 0
    if routing_file.exists() and not routing_file.is_file():
        print("bootstrap invoke: refusing to overwrite non-regular bootstrap-routing.env (stdout envelope emitted)", file=sys.stderr)
        _emit_envelope()
        return 0
    try:
        _atomic_text(path=routing_file, text=envelope)
    except OSError as exc:
        print(f"bootstrap invoke: could not write bootstrap-routing.env ({exc}); stdout envelope emitted", file=sys.stderr)
        _emit_envelope()
        return 0
    _emit_envelope()
    return 0


def _parse_env_lines(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, allowed_keys=ROUTING_KEYS, key_pattern=_KEY_RE.pattern)


def _shell_assignments(data: dict[str, str], *, preserve_coder: bool) -> str:
    lines: list[str] = []
    for key in ROUTING_KEYS:
        if preserve_coder and key in {"coder", "coder_fallback"}:
            continue
        if key in data and data[key] != "":
            lines.append(f"{key}={shlex.quote(data[key])}")
            lines.append(f"export {key}")
        else:
            lines.append(f"unset {key}")
    return "\n".join(lines) + "\n"


def parse_routing_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap parse-routing", add_help=True)
    parser.add_argument("--stdout-file", required=True)
    parser.add_argument("--tmpdir", default="")
    parser.add_argument("--resume", default="false", choices=["true", "false"])
    parser.add_argument("--output", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 1 if int(exc.code or 0) != 0 else 0
    try:
        stdout_text = Path(args.stdout_file).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"bootstrap parse-routing: {exc}", file=sys.stderr)
        return 1
    stdout_data = _parse_env_lines(stdout_text)
    tmpdir = args.tmpdir or stdout_data.get("IMPLEMENT_TMPDIR", "")
    merged: dict[str, str] = {}
    if tmpdir:
        routing_file = Path(tmpdir) / "bootstrap-routing.env"
        if routing_file.is_file() and not routing_file.is_symlink():
            with contextlib.suppress(OSError):
                merged.update(_parse_env_lines(routing_file.read_text(encoding="utf-8", errors="replace")))
    for key, value in stdout_data.items():
        if key not in merged or merged[key] == "":
            merged[key] = value
    if args.resume == "true":
        merged.pop("coder", None)
        merged.pop("coder_fallback", None)
    text = _shell_assignments(merged, preserve_coder=args.resume == "true")
    if args.output:
        _atomic_text(path=Path(args.output), text=text)
    else:
        sys.stdout.write(text)
    return 0
