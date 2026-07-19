# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""/implement Step 0 bootstrap and routing-envelope helpers."""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from larch.calibration.difficulty import resolve_step2_effective_difficulty
from larch.state import dirty_tree, session_env
from larch.core import config, external_defaults, proc, rust_runtime
from larch import io as larch_io
from larch.core import logging_util, redact
from larch.core.repo_roots import larch_entrypoint
from larch.calibration import difficulty
from larch.design import plan_grammar, plan_quality
from larch.git import gh, git, pr, pr_body
from larch.issue import issue_query, tracking_issue
from larch.report import progress_file, run_log_batch, run_logs, statusline_install, timing, tokens
from larch.agents import agents

_REPO_ROOT = Path(__file__).resolve().parents[3]
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
    "SELF_IMPLEMENT_REQUESTED",
    "DESIGN_DIFFICULTY",
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
_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class BootstrapExit(Exception):
    def __init__(self, code: int) -> None:
        self.code = code


def _emit_kv(*, key: str, value: str) -> None:
    logging_util.emit_kv(key=key, value=value.replace("\n", " ").replace("\r", " "))


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _install_statusline_best_effort() -> None:
    _ = statusline_install.install_statusline(
        plugin_root=_REPO_ROOT,
        repo_root=Path.cwd(),
        notice=True,
    )


def _valid_run_id(value: str) -> bool:
    return bool(value) and _RUN_ID_RE.fullmatch(value) is not None


def _activatable_run_id(run_id: str) -> bool:
    try:
        progress_file.validate_run_id(run_id)
    except ValueError:
        return False
    return True


def _valid_issue(value: str) -> bool:
    return bool(value) and value.isdigit()


def _checkpoint_status(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("STATUS="):
            return line.removeprefix("STATUS=")
    return "unknown"


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
            existing = larch_io.parse_kv(path.read_text(encoding="utf-8", errors="replace"), skip_comments=True, cr_strip="rstrip")
        except OSError:
            existing = {}
    data = dict(existing)
    for key, value in values.items():
        if only_missing and data.get(key):
            continue
        data[key] = value
    ordered = ("MERGE", "DRAFT", "FORKED_TARGET", "NO_ADMIN_FALLBACK", "NO_LOGS_COMMIT", "DIFFICULTY_OVERRIDE", "DEFERRED", "MANIFEST_PATH", "TOOL_LABEL")
    text = "".join(f"{key}={data.get(key, '')}\n" for key in ordered if key in data)
    _atomic_text(path=path, text=text)


def _materialize_main_health_env(st: BootstrapState) -> None:
    if not st.implement_tmpdir or not st.opts.preflight_tmpdir:
        return
    source = Path(st.opts.preflight_tmpdir) / "main-health.env"
    if not source.is_file() or source.is_symlink():
        return
    target = Path(st.implement_tmpdir) / "main-health.env"
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
        _atomic_text(path=target, text=text)
    except OSError:
        return


def _materialize_preflight_sidecars(st: BootstrapState) -> None:
    if not st.opts.preflight_tmpdir:
        return
    _atomic_text(path=Path(st.implement_tmpdir) / "preflight-tmpdir.env", text=f"PREFLIGHT_TMPDIR={st.opts.preflight_tmpdir}\n")
    _materialize_main_health_env(st)

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
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement kill-active-leg --owner-token "$_larch_active_leg_owner_token" --implement-tmpdir "$IMPLEMENT_TMPDIR" || true
}

case "$script" in
  *.py)
    _larch_active_leg_owner_token="$(python3 -c 'import uuid; print(uuid.uuid4().hex)' 2>/dev/null || printf '%s.%s.%s\n' "$$" "$(date +%s)" "${RANDOM:-0}")"
    export __OWNER_TOKEN_ENV__="$_larch_active_leg_owner_token"
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
    script = script.replace("__OWNER_TOKEN_ENV__", config.ENV_ACTIVE_LEG_OWNER_TOKEN)
    try:
        _atomic_text(path=path, text=script)
        path.chmod(0o755)
    except OSError:
        return False
    return True


def _resolve_resume_implement_tmpdir(*, claude_pid: str) -> str:
    if not re.fullmatch(r"[1-9][0-9]{0,6}", claude_pid):
        return ""
    pointer = Path.home() / ".cache" / "larch" / "sessions" / f"current-implement-env-{claude_pid}.sh"
    if not pointer.is_file() or pointer.is_symlink():
        return ""
    tmpdir = _read_simple_kv(path=pointer, key="IMPLEMENT_TMPDIR")
    if not tmpdir or not Path(tmpdir).is_absolute():
        return ""
    return tmpdir


def _read_key(*, path: Path, key: str, default: str = "") -> str:
    try:
        return session_env.read_key(
            file=str(path), key=key, default=default, file_flag_present=True
        ).value
    except ValueError:
        return default


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
    self_implement_requested: str = "false"
    difficulty_override: str = ""
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
    claude_binary_found: str = ""
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
    try:
        session_env.write_env(session_env.WriteEnvParams(
            output=str(st.session_env()),
            repo=st.repo,
            repo_root=(os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
                       or os.environ.get("REPO_ROOT", "").strip()
                       or str(Path.cwd())),
            repo_unavailable=st.repo_unavailable or "false",
            codex_present=st.codex_present,
            cursor_present=st.cursor_present,
            claude_binary_found=st.claude_binary_found,
            codex_binary_found=st.codex_binary_found,
            cursor_binary_found=st.cursor_binary_found,
            timing_ledger=str(Path(st.implement_tmpdir) / "timing-ledger.tsv"),
            token_session_id=st.session_id,
            claude_source_file=claude_source,
            prev_implement_tmpdir=st.implement_tmpdir,
            auto_mode=prior_auto_mode,
            dynamic_archetypes=prior_dynamic_archetypes if prior_dynamic_archetypes in {"0", "1"} else "",
            run_id=st.run_id if _valid_run_id(st.run_id) else "",
            forked_target=st.opts.forked_target,
            live_mutation_ok="true",
        ))
        session_env.write_env(session_env.WriteEnvParams(
            output=str(Path(st.implement_tmpdir) / "plugin-root.env"),
            repo_unavailable=None,
            plugin_root_only=True,
            value=str(_REPO_ROOT),
        ))
    except (OSError, ValueError):
        st.emit_step_failed("write-session-env")


def _write_claude_source_snapshot(st: BootstrapState) -> None:
    if not st.implement_tmpdir:
        return
    target = Path(st.implement_tmpdir) / "claude-source.env"
    if target.is_file() and target.stat().st_size > 0:
        return
    result = tokens.token_claude_source()
    if not result.available:
        return
    _atomic_text(
        path=target,
        text=(f"TRANSCRIPT_PATH={result.transcript_path}\n"
              f"SESSION_DIR={result.session_dir or ''}\n"
              f"SESSION_UUID={result.session_uuid}\n"),
    )


def _persist_run_flags(st: BootstrapState) -> bool:
    if not st.implement_tmpdir:
        return True
    try:
        session_env.persist_run_flags(
            implement_tmpdir=Path(st.implement_tmpdir),
            no_issues="false",
            force_requested=st.opts.force_requested,
            self_review_requested=st.opts.self_review_requested,
            self_implement_requested=st.opts.self_implement_requested,
            difficulty_override=st.opts.difficulty_override,
        )
    except (OSError, ValueError):
        st.stall_tracking = "true"
        st.implement_bail_reason = "run-flags-persist-failed"
        return False
    return True


def _ensure_plugin_root_env(st: BootstrapState) -> None:
    plugin_env = Path(st.implement_tmpdir) / "plugin-root.env"
    if not plugin_env.is_file():
        with contextlib.suppress(OSError, ValueError):
            session_env.write_env(session_env.WriteEnvParams(
                output=str(plugin_env), repo_unavailable=None,
                plugin_root_only=True, value=str(_REPO_ROOT),
            ))


def _restore_resume_progress(st: BootstrapState) -> None:
    st.run_id = st.read_session(key="LARCH_RUN_ID") or st.resolve_run_id()
    if _activatable_run_id(st.run_id):
        with contextlib.suppress(OSError, ValueError):
            progress_file.activate_run(Path.cwd(), st.run_id)


def _self_subagents_only(opts: BootstrapOptions) -> bool:
    return opts.self_review_requested == "true" and opts.self_implement_requested == "true"


def _refresh_reviewer_state(st: BootstrapState) -> None:
    if _self_subagents_only(st.opts):
        return
    reviewer = agents.check_reviewers(
        skip_codex_probe=st.opts.skip_codex_probe,
        skip_cursor_probe=st.opts.skip_cursor_probe,
    )
    reviewer_kv = reviewer.kv()
    st.codex_present = reviewer_kv.get("CODEX_PRESENT", st.codex_present)
    st.cursor_present = reviewer_kv.get("CURSOR_PRESENT", st.cursor_present)
    st.codex_binary_found = reviewer_kv.get("CODEX_BINARY_FOUND", st.codex_binary_found)
    st.cursor_binary_found = reviewer_kv.get("CURSOR_BINARY_FOUND", st.cursor_binary_found)
    _write_base_session_env(st)


def _phase_infra(st: BootstrapState) -> None:
    _ = progress_file.clear_active_run(Path.cwd())
    branch = pr.check_branch_state(proc)
    if branch.exit_code != 0:
        st.emit_step_failed("create-branch")
    st.current_branch = branch.current_branch
    st.is_main = str(branch.is_main).lower()
    st.is_user_branch = str(branch.is_user_branch).lower()
    st.user_prefix = branch.user_prefix
    try:
        gate = session_env.entry_gate(
            mode="implement", is_main=st.is_main,
            is_user_branch=st.is_user_branch, user_prefix=st.user_prefix,
            branch_info_supplied=None,
        )
    except ValueError:
        st.emit_step_failed("session-entry-gate")
        return
    st.entry_gate = gate.entry_gate
    st.skip_branch_check = gate.skip_branch_check

    if st.opts.resume_plan_tail and st.implement_tmpdir and st.session_env().is_file():
        st.session_id = (Path(st.implement_tmpdir) / "session-id").read_text(encoding="utf-8", errors="replace").strip() if (Path(st.implement_tmpdir) / "session-id").is_file() else ""
        st.repo = st.read_session(key="REPO")
        st.repo_unavailable = st.read_session(key="REPO_UNAVAILABLE", default="false")
        st.codex_present = st.read_session(key="CODEX_PRESENT")
        st.cursor_present = st.read_session(key="CURSOR_PRESENT")
        st.claude_binary_found = st.read_session(key="CLAUDE_BINARY_FOUND")
        st.codex_binary_found = st.read_session(key="CODEX_BINARY_FOUND")
        st.cursor_binary_found = st.read_session(key="CURSOR_BINARY_FOUND")
        _restore_resume_progress(st)
        _ensure_plugin_root_env(st)
    else:
        skip_external_tool_probes = _self_subagents_only(st.opts)
        try:
            setup = session_env.setup(
                prefix="claude-implement",
                skip_branch_check=st.skip_branch_check == "true",
                skip_codex_probe=st.opts.skip_codex_probe or skip_external_tool_probes,
                skip_cursor_probe=st.opts.skip_cursor_probe or skip_external_tool_probes,
                caller_env=st.opts.caller_env,
            )
        except (OSError, ValueError, session_env.SessionSetupError):
            st.emit_step_failed("session-setup")
            return
        if setup.exit_code != 0:
            st.emit_step_failed("session-setup")
            return
        st.implement_tmpdir = str(setup.session_tmpdir)
        os.environ["IMPLEMENT_TMPDIR"] = st.implement_tmpdir
        st.session_id = setup.session_id
        st.repo = setup.repo
        st.repo_unavailable = setup.repo_unavailable
        st.codex_present = setup.codex_present
        st.cursor_present = setup.cursor_present
        st.claude_binary_found = setup.claude_binary_found
        st.codex_binary_found = setup.codex_binary_found
        st.cursor_binary_found = setup.cursor_binary_found
        _materialize_preflight_sidecars(st)
        session_id_path = Path(st.implement_tmpdir) / "session-id"
        if st.session_id:
            with contextlib.suppress(OSError):
                _atomic_text(path=session_id_path, text=f"{st.session_id}\n")
        else:
            with contextlib.suppress(OSError):
                session_env.write_id(output=session_id_path)
        if not st.session_id and session_id_path.is_file():
            st.session_id = session_id_path.read_text(encoding="utf-8", errors="replace").strip()
        st.run_id = st.resolve_run_id()
        if _activatable_run_id(st.run_id):
            with contextlib.suppress(OSError, ValueError):
                progress_file.activate_run(Path.cwd(), st.run_id)
        _write_claude_source_snapshot(st)
        _write_base_session_env(st)
        _ = tokens.token_mark(step="Step 0 — preflight")
        env = {**os.environ, "LARCH_TIMING_SKILL": "implement"}
        _ = timing.mark(label="Step 0 — preflight", env=env)
        _refresh_reviewer_state(st)
    _install_statusline_best_effort()
    if st.implement_tmpdir and not _write_larch_run_sh(st.implement_tmpdir):
        st.emit_step_failed("larch-run")
    pid = os.environ.get("LARCH_CLAUDE_PID", "")
    if pid and st.implement_tmpdir:
        try:
            session_env.write_implement_env(
                claude_pid=pid, implement_tmpdir=st.implement_tmpdir, cwd=str(Path.cwd())
            )
        except (OSError, ValueError) as exc:
            diag = Path(st.implement_tmpdir) / "write-implement-env-warning.log"
            with contextlib.suppress(OSError):
                diag.write_text(str(exc), encoding="utf-8")
            if diag.is_file():
                _append_failure_with_entry_fallback(
                    st,
                    site="implement-bootstrap write-implement-env",
                    tool="session write-implement-env",
                    exit_code="1",
                    category="Warnings",
                    output_file=diag,
                    status_label="failed",
                )
            st.emit_step_failed("write-implement-env")
    elif st.implement_tmpdir and not pid:
        st.emit_step_failed("write-implement-env")
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
        try:
            read = tracking_issue.read_sentinel(str(sentinel))
        except tracking_issue.CliFailure:
            read = None
        if read is not None and read.adopted == "true":
            issue = read.issue_number
            run_id = read.run_id
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
                if _checkpoint_status(dirty_lines) in {"dirty", "unknown"}:
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
    _adopt_tracking_issue(st)


def _adopt_tracking_issue(st: BootstrapState) -> None:
    try:
        state = issue_query.issue_state(proc, st.opts.issue_number, repo=None)
    except Exception:
        st.emit_step_failed("get-issue-state")
        return
    if state.is_pr:
        st.implement_bail_reason = "adopted-issue-is-pr"
        return
    if state.state == "CLOSED":
        st.implement_bail_reason = "adopted-issue-closed"
        return
    if state.state != "OPEN":
        st.emit_step_failed("get-issue-state")
        return
    dirty_lines = dirty_tree.checkpoint()
    if _checkpoint_status(dirty_lines) in {"dirty", "unknown"}:
        st.implement_bail_reason = "dirty-tree"
        return
    st.branch_selected = "branch-2-adopt"
    st.issue_number_resolved = st.opts.issue_number
    st.run_id = st.resolve_run_id()
    _perform_tracking_side_effects(st, write_sentinel=True)


def _tracking_bail(*, st: BootstrapState, detail: str, result: object | None = None) -> None:
    st.stall_tracking = "true"
    st.implement_bail_reason = "tracking-init-failed"
    if st.implement_tmpdir:
        text = detail + "\n"
        if result is not None:
            text += str(result)
        with contextlib.suppress(OSError):
            (Path(st.implement_tmpdir) / "tracking-init-failed.stderr.log").write_text(text, encoding="utf-8")


def _difficulty_prior_from_preflight(st: BootstrapState) -> str:
    if not st.opts.preflight_tmpdir:
        return ""
    plan = Path(st.opts.preflight_tmpdir) / "plan-from-issue.txt"
    if not plan.is_file():
        return ""
    try:
        return difficulty.plan_difficulty(plan.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def _persist_difficulty_prior(st: BootstrapState, tier: str) -> None:
    if not st.implement_tmpdir:
        return
    path = Path(st.implement_tmpdir) / "difficulty-prior.env"
    value = tier if difficulty.tier_valid(tier) else ""
    text = f"DESIGN_DIFFICULTY={value}\n"
    with contextlib.suppress(OSError):
        _atomic_text(path=path, text=text)


def _write_initial_difficulty_record(st: BootstrapState, tier: str) -> None:
    if not st.implement_tmpdir or not _valid_run_id(st.run_id):
        return
    tmpdir = Path(st.implement_tmpdir)
    out = tmpdir / difficulty.DIFFICULTY_RECORD_BASENAME
    fallback = difficulty.DifficultyRating(
        predicted_tier="MODERATE", confidence="medium",
        rationale="initial record seeded before implement rating", adjusted_tier="MODERATE",
    )
    design = (difficulty.DifficultyRating(tier, "medium", "design wire metadata", tier)
              if difficulty.tier_valid(tier) else None)
    try:
        record = difficulty.build_record(
            rater="fallback", rater_tool="bootstrap", rater_model="unknown",
            design_rating=design, fallback_rating=fallback, changed_paths=(),
            override_tier=st.opts.difficulty_override,
            override_source="operator" if difficulty.tier_valid(st.opts.difficulty_override) else "",
        )
        difficulty.write_record(out, record)
    except (OSError, ValueError):
        return
    with contextlib.suppress(OSError, ValueError):
        run_logs.log_write(log_root=tmpdir / "larch-logs", skill="implement", run_id=st.run_id,
                           batch="difficulty-rating", input_file=str(out))


def _perform_tracking_side_effects(st: BootstrapState, *, write_sentinel: bool) -> bool:
    if not _valid_issue(st.issue_number_resolved):
        _tracking_bail(st=st, detail="invalid issue number")
        return False
    if not _valid_run_id(st.run_id):
        _tracking_bail(st=st, detail="invalid or empty run id")
        return False
    _write_base_session_env(st)
    try:
        current_title = gh.issue_view_template_read(
            proc, st.issue_number_resolved, "title", "{{.title}}", repo=st.repo or None
        )
        if current_title.returncode != 0:
            raise OSError(current_title.stderr)
        repo = st.repo or gh.resolve_repo(proc)
        if not repo:
            raise OSError("repository unavailable for tracking issue rename")
        _ = tracking_issue.rename_with_details(
            proc, st.issue_number_resolved, "implementing", repo=repo,
            current_title=current_title.stdout.strip(),
        )
    except Exception as exc:
        with contextlib.suppress(OSError):
            (Path(st.implement_tmpdir) / "tracking-rename-warning.stderr.log").write_text(
                f"tracking rename failed\n{exc}", encoding="utf-8"
            )
    try:
        _ = run_logs.log_init(
            log_root=Path(st.implement_tmpdir) / "larch-logs", skill="implement",
            run_id=st.run_id, issue=st.issue_number_resolved,
        )
    except (OSError, ValueError) as exc:
        _tracking_bail(st=st, detail="run-log init failed", result=exc)
        return False
    # Emit plan-review tally (stub or preflight candidate) before later Step 0
    # bailouts can skip _phase_plan; _phase_plan overwrites when a real tally exists.
    prior = _difficulty_prior_from_preflight(st)
    _persist_difficulty_prior(st, prior)
    _write_initial_difficulty_record(st, prior)
    _publish_plan_review_tally(st)
    if not _persist_run_flags(st):
        return False
    post = pr_body.post_tracking_issue(
        Path(st.implement_tmpdir),
        issue_number=st.issue_number_resolved if write_sentinel else "",
        run_id=st.run_id, adopted="true", force_requested=st.opts.force_requested,
    )
    if post.exit_code != 0:
        st.deferred = "true"
        return False
    if not post.posted:
        st.deferred = "true"
    return True


def _append_execution_issue_entry(*, log: Path, category: str, entry: str) -> bool:
    try:
        run_log_batch.append_execution_issue(log_file=log, category=category, entry=entry)
    except OSError:
        return False
    return True


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
    try:
        run_logs.log_append_failure(
            log=log, site=site, tool=tool, exit_code=exit_code, category=category,
            output_file=output_file, status_label=status_label, redact_body=True,
        )
        return True
    except (OSError, ValueError):
        pass
    body = "no diagnostics captured"
    with contextlib.suppress(OSError):
        if output_file.is_file() and output_file.stat().st_size:
            body = output_file.read_text(encoding="utf-8", errors="replace").rstrip() or body
    body = _redact_text(body, implement_tmpdir=st.implement_tmpdir)
    entry = (
        f"- **Step {site}: {tool} {status_label} (exit {exit_code}; append-failure fallback)**:\n"
        "  ```\n"
        f"{body}\n"
        "  ```\n"
    )
    return _append_execution_issue_entry(log=log, category=category, entry=entry)


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
    canonical = {"missing-designed-prefix"}
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


_PLAN_PROVENANCE_PREFIXES = ("review_status:", "rounds_completed:", "difficulty:")


def _strip_plan_provenance_headers(text: str) -> str:
    lines = text.splitlines(keepends=True)
    trailers = plan_grammar.parse_final_trailers(text, require_diff_lines=True)
    if not trailers.matches:
        return text
    start = trailers.start_line - 1
    remove = {
        start + idx
        for idx, match in enumerate(trailers.matches)
        if match.key in {"review_status", "rounds_completed", "difficulty"}
    }
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
    elif not _materialize_initial_plan(st, feature_file=feature_file):
        return
    dirty_lines = dirty_tree.checkpoint()
    if _checkpoint_status(dirty_lines) in {"dirty", "unknown"}:
        st.implement_bail_reason = "dirty-tree"
        return
    if st.opts.forked_target != "true" and st.is_user_branch != "true" and feature_file.is_file():
        title = feature_file.read_text(encoding="utf-8", errors="replace").splitlines()[0:1]
        raw = title[0] if title else "issue"
        slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", raw.lower())).strip("-")[:40].rstrip("-") or "issue"
        branch_name = f"{st.user_prefix}/{slug}-{st.issue_number_resolved}" if st.user_prefix and st.issue_number_resolved else ""
        if branch_name:
            created = pr.create_branch(proc, branch=branch_name)
            if created.exit_code != 0:
                st.stall_tracking = "true"
                st.implement_bail_reason = "branch-create-failed"
                return
            st.branch_action = created.action
    with contextlib.suppress(Exception):
        st.branch_name = git.current_branch(proc)
    if not st.branch_name:
        st.stall_tracking = "true"
        st.implement_bail_reason = "branch-create-failed"
        return
    issue = st.issue_number_resolved or st.opts.issue_number
    title = feature_file.read_text(encoding="utf-8", errors="replace").splitlines()[0] if feature_file.is_file() else "planned change"
    goal = f"Implement issue #{issue}: {title or 'planned change'}."
    plan_goals = plan_quality.compose_plan_goals_test(
        plan_text=Path(st.plan_file).read_text(encoding="utf-8", errors="replace"), goal_text=goal,
    )
    plan_goals_path = Path(st.implement_tmpdir) / "plan-goals-test.md"
    plan_goals_path.write_text(plan_goals, encoding="utf-8")
    (Path(st.implement_tmpdir) / "run-step1-plan-log.out").write_text("", encoding="utf-8")
    with contextlib.suppress(OSError, ValueError):
        run_logs.log_write(log_root=Path(st.implement_tmpdir) / "larch-logs", skill="implement",
                           run_id=st.run_id, batch="plan-goals-test", input_file=str(plan_goals_path))
    _publish_plan_review_tally(st)
    _upsert_plan_summary(st)
    _err(f"→ step0: branch {st.branch_name} + plan logged")


def _materialize_initial_plan(st: BootstrapState, *, feature_file: Path) -> bool:
    snapshot = Path(st.implement_tmpdir) / "untracked-baseline.z"
    if not snapshot.exists():
        _ = proc.run([str(larch_entrypoint(_REPO_ROOT)), "git", "snapshot-untracked", "--output", str(snapshot), "--nul"])
    if not _append_force_bypass(st):
        st.emit_tmp_step_failed("force-bypass-log")
    plan_src = Path(st.opts.preflight_tmpdir) / "plan-from-issue.txt"
    try:
        plan_text = plan_src.read_text(encoding="utf-8", errors="replace")
        _persist_difficulty_prior(st, difficulty.plan_difficulty(plan_text))
        Path(st.plan_file).write_text(_strip_plan_provenance_headers(plan_text), encoding="utf-8")
    except OSError as exc:
        (Path(st.implement_tmpdir) / "copy-plan.stderr.log").write_text(str(exc), encoding="utf-8")
        st.emit_tmp_step_failed("copy-plan")
    if st.opts.forked_target == "true" and not st.opts.upstream_repo:
        (Path(st.implement_tmpdir) / "gh-issue-view.stderr.log").write_text(
            "--forked requires UPSTREAM_REPO before gh issue view\n", encoding="utf-8"
        )
        st.emit_tmp_step_failed("gh-issue-view")
    view_repo = st.opts.upstream_repo if st.opts.forked_target == "true" else None
    view_result = gh.issue_view_template_read(
        proc, st.issue_number_resolved or st.opts.issue_number, "title,body",
        "{{.title}}\n\n{{.body}}", repo=view_repo,
    )
    if view_result.returncode != 0:
        (Path(st.implement_tmpdir) / "gh-issue-view.stderr.log").write_text(view_result.stderr, encoding="utf-8")
        st.emit_tmp_step_failed("gh-issue-view")
    feature_file.write_text(view_result.stdout, encoding="utf-8")
    return _persist_run_flags(st)


def _publish_plan_review_tally(st: BootstrapState) -> None:
    if not _valid_run_id(st.run_id):
        return
    preflight = Path(st.opts.preflight_tmpdir) if st.opts.preflight_tmpdir else Path()
    for candidate in (
        preflight / "plan-review-tally.json",
        preflight / "voting-tally.json",
        Path(st.implement_tmpdir) / "plan-review-tally.json",
    ):
        if candidate.is_file():
            _write_plan_review_tally_batch(st=st, source=candidate)
            return
    # /implement plan review runs in /design, so no upstream tally is materialized on
    # this path. Emit a stub anyway so the run-log completeness manifest
    # (plan-review-tally.json, condition `always`) is satisfied and the committed
    # artifact points readers back to the /design run for the real ballots.
    stub = Path(st.implement_tmpdir) / "plan-review-tally-stub.json"
    try:
        stub.write_text(_plan_review_tally_stub_json(), encoding="utf-8")
    except OSError:
        return
    _write_plan_review_tally_batch(st=st, source=stub)


def _plan_review_tally_stub_json() -> str:
    record: dict[str, object] = {
        "schema_version": 2,
        "phase": "plan-review",
        "batch": "plan-review-tally",
        "mode": "simple",
        "rounds": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "exonerated_count": 0,
        "body": (
            "Plan review completed in the /design phase; see the /design run "
            "artifacts for the ballots. No plan-review voting ran in this "
            "/implement run."
        ),
    }
    return json.dumps(record, separators=(",", ":"))


def _write_plan_review_tally_batch(*, st: BootstrapState, source: Path) -> None:
    with contextlib.suppress(OSError, ValueError):
        run_logs.log_write(log_root=Path(st.implement_tmpdir) / "larch-logs", skill="implement",
                           run_id=st.run_id, batch="plan-review-tally", input_file=str(source))


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
    try:
        tracking_issue.upsert_marker_summary(
            proc, issue=issue, marker=f"<!-- larch:plan v1 runid={st.run_id} -->",
            content_file=str(content),
            repo=(st.opts.upstream_repo if st.opts.forked_target == "true" else st.repo) or None,
        )
    except (tracking_issue.CliFailure, OSError):
        return


def _record_coder_fallback(*, st: BootstrapState, reason: str) -> None:
    if st.coder_fallback != "true" or not st.implement_tmpdir:
        return
    warning = "**⚠ Cursor and Codex unavailable — implementing with Claude subagent (larch:claude-implementer).**\n"
    _err(warning.rstrip("\n"))
    diag = Path(st.implement_tmpdir) / "coder-fallback-warning.txt"
    with contextlib.suppress(OSError):
        diag.write_text(f"{warning}REASON={reason}\n", encoding="utf-8")
    if diag.is_file():
        with contextlib.suppress(OSError, ValueError):
            run_logs.log_append_failure(
                log=Path(st.implement_tmpdir) / "execution-issues.md",
                site="implement-bootstrap coder-select", tool="phase_coder_select",
                exit_code="0", category="Warnings", output_file=diag,
                status_label="fallback", redact_body=True,
            )
    if _valid_run_id(st.run_id):
        with contextlib.suppress(OSError, ValueError):
            run_logs.log_manifest_update(
                log_root=Path(st.implement_tmpdir) / "larch-logs", skill="implement",
                run_id=st.run_id, updates={"coder_fallback": True},
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
        with contextlib.suppress(OSError, ValueError):
            run_logs.log_append_failure(
                log=Path(st.implement_tmpdir) / "execution-issues.md",
                site="implement-bootstrap coder-select", tool="phase_coder_select",
                exit_code="0", category="Warnings", output_file=diag,
                status_label="fallback", redact_body=True,
            )


def _phase_coder(st: BootstrapState) -> None:
    if st.implement_bail_reason or st.stall_tracking == "true":
        return
    if st.repo_unavailable == "true" or not st.plan_file or not Path(st.plan_file).is_file() or not (Path(st.implement_tmpdir) / "feature-description.txt").is_file():
        return
    if st.opts.self_implement_requested == "true" or st.opts.coder_opt == "claude":
        st.coder = "claude"
    else:
        if st.opts.coder_opt in {"codex", "cursor"}:
            other = "cursor" if st.opts.coder_opt == "codex" else "codex"
            order = [st.opts.coder_opt, other, "claude"]
        else:
            effective_difficulty = resolve_step2_effective_difficulty(Path(st.implement_tmpdir))
            order = list(
                config.CODER_TOOL_ORDER_BY_DIFFICULTY.get(
                    effective_difficulty,
                    external_defaults.tool_order("implement.step2_coder"),
                )
            )
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
        ("CLAUDE_BINARY_FOUND", st.claude_binary_found),
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
        ("SELF_IMPLEMENT_REQUESTED", st.opts.self_implement_requested),
        ("DIFFICULTY_OVERRIDE", st.opts.difficulty_override),
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
    for key, value in larch_io.parse_kv(text, skip_comments=True, cr_strip="rstrip").items():
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
    _ = implement_tmpdir
    try:
        return redact.redact(text)
    except Exception:
        return "diagnostic redaction failed\n"


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
        "session-setup": "**⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run. This bypass covers branch position and main-sync only; stash cleanliness still applies on feature branches; (c) commit or stash uncommitted changes on `main` first; (d) clear a non-empty stash with `git stash pop` to restore and commit, or `git stash drop` to discard.**",
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


def _refresh_gate_probe(st: BootstrapState) -> str | None:
    try:
        result = agents.check_reviewers()
    except OSError:
        try:
            result = agents.check_reviewers()
        except OSError:
            return "absorbed-gate-probe-refresh-failed"
    kv = result.kv()
    st.codex_present = kv.get("CODEX_PRESENT", st.codex_present)
    st.cursor_present = kv.get("CURSOR_PRESENT", st.cursor_present)
    st.codex_binary_found = kv.get("CODEX_BINARY_FOUND", st.codex_binary_found)
    st.cursor_binary_found = kv.get("CURSOR_BINARY_FOUND", st.cursor_binary_found)
    return None

def _run_1r_probe(st: BootstrapState, *, forked_target: str) -> tuple[dict[str, str], list[str], int]:
    result = rust_runtime.checkpoint_probe(
        proc,
        step_prefix="1.r",
        short_name="plan materialization",
        forked_target=forked_target if forked_target in {"true", "false"} else "false",
    )
    routing = dict(result.routing)
    advisory = list(result.advisory_lines)
    routing["REBASE_RC"] = str(result.exit_code)
    route = routing.get("ROUTE", "")
    if route not in {"continue", "conflict", "bail"}:
        routing["ROUTE"] = "bail"
        routing["CHECKPOINT_NEXT"] = "load-routing"
        routing.setdefault("REBASE_OUTCOME", "failed")
        error = _single_line(result.stderr or f"probe rc {result.exit_code}")
        routing["REBASE_ERROR"] = _redact_text(error, implement_tmpdir=st.implement_tmpdir)
    elif routing.get("CHECKPOINT_NEXT", "") not in {"continue", "load-routing"}:
        routing["CHECKPOINT_NEXT"] = "load-routing"
    return routing, advisory, result.exit_code


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
    if _self_subagents_only(opts):
        probe_routing, advisory, _probe_rc = _run_1r_probe(st, forked_target=opts.forked_target)
        routing = {
            "DEGRADED": "false",
            "BOTH_DOWN": "false",
            "DEGRADED_PROMPT_REQUIRED": "false",
        }
        routing.update({key: value for key, value in probe_routing.items() if value})
        if _step2_blockers({**data, **routing}):
            routing.pop("ROUTE", None)
        return ContinueTailResult(routing=routing, advisory_lines=advisory)
    probe_failed = _refresh_gate_probe(st)
    if probe_failed:
        return ContinueTailResult(contract_failure=True, step_failed=probe_failed)
    forked_target = opts.forked_target if opts.forked_target in {"true", "false"} else "false"
    sentinel = Path(tmpdir) / ".degraded-tools-gate-prompted"
    sentinel_exists = sentinel.is_file()
    gate = agents.degraded_tools_result(
        skill="implement", codex_present=st.codex_present, cursor_present=st.cursor_present,
        codex_binary_found=st.codex_binary_found or "unknown",
        cursor_binary_found=st.cursor_binary_found or "unknown",
    )
    gate_routing = {
        "DEGRADED": str(gate.degraded).lower(), "CODEX_STATE": gate.codex_state,
        "CURSOR_STATE": gate.cursor_state, "BOTH_DOWN": str(gate.both_down).lower(),
    }
    if gate.both_down:
        gate_routing["DEGRADED_HARD_FAIL"] = "true"
    if gate.presence_input_empty:
        gate_routing["PRESENCE_INPUT_EMPTY"] = "true"
    explanation_lines = list(gate.explanation)
    explanation_text = "\n".join(explanation_lines).strip()
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
    parser.add_argument("--self-implement-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--non-interactive", default="", choices=["", "true", "false"])
    parser.add_argument("--difficulty", default="", choices=["", "TRIVIAL", "MODERATE", "HARD"])
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
    if args.mode == "resume" and not implement_tmpdir_env:
        implement_tmpdir_env = _resolve_resume_implement_tmpdir(claude_pid=env.get("LARCH_CLAUDE_PID", ""))
        if implement_tmpdir_env:
            env["IMPLEMENT_TMPDIR"] = implement_tmpdir_env
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
    self_implement = args.self_implement_requested or _str_bool(env.get("self_implement", "")) or "false"
    difficulty_override = args.difficulty or env.get("difficulty", "") or env.get("DIFFICULTY_OVERRIDE", "")
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
        self_implement_requested=self_implement if self_implement in {"true", "false"} else "false",
        difficulty_override=difficulty_override if difficulty_override in {"TRIVIAL", "MODERATE", "HARD"} else "",
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
        kv = larch_io.parse_kv(out, skip_comments=True, cr_strip="rstrip")
        _invoke_error(step_failed=kv.get("STEP_FAILED", ""), out=out, implement_tmpdir=kv.get("IMPLEMENT_TMPDIR", ""))
        return 2
    if rc != 0:
        return rc
    tmpdir = larch_io.parse_kv(out, skip_comments=True, cr_strip="rstrip").get("IMPLEMENT_TMPDIR", "")
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
                "DIFFICULTY_OVERRIDE": opts.difficulty_override,
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
