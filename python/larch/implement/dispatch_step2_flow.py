# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Step 2 dispatch orchestration helpers extracted from step2_dispatch_main."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from larch.core import redact
from larch.implement.dispatch_helpers import (
    _binary_available,
    _emit_kv,
    _err,
    _git_stdout,
    _invoke_cli,
    _run,
    _session_get,
    _write_text_atomic,
    GIT_BIN,
    RESUME_CAP,
    WRAPPER_VALIDATION_RC,
    _PLUGIN_ROOT,
    _SAFE_CODERS,
)
from larch.implement.dispatch_manifest import (
    DispatchState,
    _clear_external_scout_state,
    _complete_schema_valid,
    _emit_manifest_invalid_or_recover,
    _json_load,
    _manifest_complete_salvageable,
    _validate_manifest_paths,
    _write_prelaunch_baseline,
)


@dataclass
class _LauncherOutcome:
    wrapper_rc: int
    kv: dict[str, str]
    warn_nonzero: bool = False


def _validate_step2_coder_args(args: argparse.Namespace) -> int | None:
    if args.coder and args.codex_available:
        _err("implement step2-dispatch: --coder and --codex-available are mutually exclusive")
        return 2
    if args.codex_available:
        if args.codex_available == "true":
            _err("implement step2-dispatch: WARNING: --codex-available is deprecated; pass --coder codex instead")
            args.coder = "codex"
        elif args.codex_available == "false":
            _err("implement step2-dispatch: WARNING: --codex-available is deprecated; pass --coder claude instead")
            args.coder = "claude"
        else:
            _err(f"implement step2-dispatch: --codex-available must be 'true' or 'false', got: {args.codex_available}")
            return 2
    if not args.coder:
        _err("implement step2-dispatch: --coder is required")
        return 2
    if args.coder not in _SAFE_CODERS:
        _err(f"implement step2-dispatch: --coder must be one of {{claude,codex,cursor}}, got: {args.coder}")
        return 2
    for flag_name in ("codex_present", "cursor_present", "cursor_available", "codex_binary_found", "cursor_binary_found"):
        value = getattr(args, flag_name)
        if value and value not in {"true", "false"}:
            _err(f"implement step2-dispatch: --{flag_name.replace('_', '-')} must be 'true', 'false', or empty, got: {value}")
            return 2
    return None


def _step2_setup_tmpdir_env(args: argparse.Namespace) -> tuple[int | None, Path | None]:
    tmpdir_raw = Path(args.tmpdir)
    if not tmpdir_raw.is_dir():
        _err(f"implement step2-dispatch: --tmpdir not a directory: {tmpdir_raw}")
        return 2, None
    tmpdir = tmpdir_raw.resolve()
    os.environ["IMPLEMENT_TMPDIR"] = str(tmpdir)
    if (tmpdir / "session-id").is_file():
        session_id = (tmpdir / "session-id").read_text(encoding="utf-8", errors="replace").strip()
        if session_id:
            os.environ["LARCH_TOKEN_SESSION_ID"] = session_id
    if (tmpdir / "claude-source.env").is_file():
        os.environ["LARCH_CLAUDE_SOURCE_FILE"] = str(tmpdir / "claude-source.env")
    if not Path(args.plan_file).is_file():
        _err(f"implement step2-dispatch: --plan-file not found: {args.plan_file}")
        return 2, None
    if not Path(args.feature_file).is_file():
        _err(f"implement step2-dispatch: --feature-file not found: {args.feature_file}")
        return 2, None
    return None, tmpdir


def _step2_claude_fallback_response() -> int:
    _emit_kv(key="STATUS", value="claude_fallback")
    _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
    return 0


def _step2_maybe_claude_fallback(args: argparse.Namespace, tmpdir: Path) -> int | None:
    if args.coder == "claude":
        _clear_external_scout_state(tmpdir)
        return _step2_claude_fallback_response()
    session_env = tmpdir / "session-env.sh"
    if not args.cursor_binary_found:
        args.cursor_binary_found = _binary_available(session_env=session_env, key="CURSOR_BINARY_FOUND", binary="cursor")
    if not args.codex_binary_found:
        args.codex_binary_found = _binary_available(session_env=session_env, key="CODEX_BINARY_FOUND", binary="codex")
    if args.coder == "cursor" and args.cursor_binary_found != "true":
        _clear_external_scout_state(tmpdir)
        return _step2_claude_fallback_response()
    if args.coder == "codex" and args.codex_binary_found != "true":
        _clear_external_scout_state(tmpdir)
        return _step2_claude_fallback_response()
    return None


def _step2_build_dispatch_state(args: argparse.Namespace, tmpdir: Path) -> tuple[int | None, DispatchState | None]:
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("LARCH_CLAUDE_PLUGIN_ROOT") or _PLUGIN_ROOT).resolve()
    repo_result = _run(["git", "rev-parse", "--show-toplevel"])
    if repo_result.returncode != 0 or not repo_result.stdout.strip():
        _err("implement step2-dispatch: must be invoked from within a git working tree (git rev-parse --show-toplevel failed)")
        return 2, None
    repo_root = Path(repo_result.stdout.strip()).resolve()
    from larch.implement.dispatch_step2 import _dispatch_state

    st = _dispatch_state(args=args, repo_root=repo_root, tmpdir=tmpdir, plugin_root=plugin_root)
    if not (plugin_root / "agents" / f"{st.tool_tag}-implementer.md").is_file():
        _err(f"implement step2-dispatch: agent prompt missing: {plugin_root / 'agents' / (st.tool_tag + '-implementer.md')}")
        return 2, None
    return None, st


def _step2_record_spawn_metadata(st: DispatchState) -> int | None:
    if st.spawn_coder_file.is_file():
        if st.spawn_coder_file.read_text(encoding="utf-8", errors="replace").strip() != st.coder:
            return st.emit_bailed("coder-mismatch-tmpdir-reuse")
    else:
        _write_text_atomic(path=st.spawn_coder_file, text=st.coder + "\n")
    if not st.baseline_file.is_file():
        _write_text_atomic(path=st.baseline_file, text=_git_stdout(st.repo_root, "rev-parse", "HEAD") + "\n")
    st.baseline_sha = st.baseline_file.read_text(encoding="utf-8", errors="replace").strip()
    if not st.spawn_branch_file.is_file():
        _write_text_atomic(path=st.spawn_branch_file, text=_git_stdout(st.repo_root, "symbolic-ref", "-q", "--short", "HEAD") + "\n")
    st.spawn_branch = st.spawn_branch_file.read_text(encoding="utf-8", errors="replace").strip()
    return None


def _step2_validate_spawn_branch(st: DispatchState) -> int | None:
    session_env = st.tmpdir / "session-env.sh"
    parent_issue = st.tmpdir / "parent-issue.md"
    issue_from_parent = _session_get(file=parent_issue, key="ISSUE_NUMBER", default="") if parent_issue.is_file() else ""
    forked_target = _session_get(file=session_env, key="FORKED_TARGET", default="false") if session_env.is_file() else "false"
    issue_anchored = bool(issue_from_parent) or session_env.is_file()
    if forked_target != "true" and issue_anchored and (not st.spawn_branch or st.spawn_branch == "HEAD"):
        return st.emit_bailed("detached-head-prohibited")
    if forked_target != "true" and issue_anchored and st.spawn_branch in {"main", "master"}:
        return st.emit_bailed("main-branch-prohibited")
    return None


def _step2_handle_resume(st: DispatchState) -> int | None:
    resume_count = 0
    if st.resume_count_file.is_file():
        raw = st.resume_count_file.read_text(encoding="utf-8", errors="replace").strip()
        if raw.isdigit():
            resume_count = int(raw)
        else:
            return st.emit_bailed("manifest-schema-invalid")
    if st.answers_file is not None:
        if not st.answers_file.is_file():
            _err(f"implement step2-dispatch: --answers given but path does not exist: {st.answers_file}")
            return 2
        resume_count += 1
        _write_text_atomic(path=st.resume_count_file, text=f"{resume_count}\n")
    if resume_count > RESUME_CAP:
        return st.emit_bailed("qa-loop-exceeded")
    return None


def _step2_prepare_launch_artifacts(st: DispatchState) -> None:
    for path in (st.manifest_path, st.manifest_raw_path, st.qa_pending_path, st.transcript_path, st.sidecar_log, st.launch_scout_manifest):
        with contextlib.suppress(OSError):
            path.unlink()
    _clear_external_scout_state(st.tmpdir)
    _write_prelaunch_baseline(st)


def _step2_evaluate_launcher_result(st: DispatchState, wrapper_rc: int, kv: dict[str, str]) -> tuple[int | None, _LauncherOutcome]:
    from larch.implement.dispatch_step2 import _append_warning

    if wrapper_rc == WRAPPER_VALIDATION_RC:
        return st.emit_bailed("wrapper-validation-failure"), _LauncherOutcome(wrapper_rc=wrapper_rc, kv=kv)
    launcher_exit = kv.get("LAUNCHER_EXIT", "99")
    manifest_written = kv.get("MANIFEST_WRITTEN", "false")
    launcher_status = kv.get("STATUS", "")
    if launcher_status == "cap_hit":
        return st.emit_bailed("cap_hit"), _LauncherOutcome(wrapper_rc=wrapper_rc, kv=kv)
    if wrapper_rc != 0:
        return st.emit_bailed(st.runtime_failure_token), _LauncherOutcome(wrapper_rc=wrapper_rc, kv=kv)
    if manifest_written != "true":
        return st.emit_bailed(st.runtime_failure_token), _LauncherOutcome(wrapper_rc=wrapper_rc, kv=kv)
    warn_nonzero = False
    if launcher_exit != "0":
        if st.coder == "codex" and _manifest_complete_salvageable(st.manifest_path):
            warn_nonzero = True
            _append_warning(
                st=st,
                text=(
                    f"Step 4 — {st.tool_tag} exited non-zero (LAUNCHER_EXIT={launcher_exit}) after atomically writing a complete manifest; "
                    f"not discarding it — continuing to validation/commit ({st.nonzero_exit_warn_token}=true). "
                    "A self-verification step likely failed after the implementation work completed."
                ),
            )
        else:
            return st.emit_bailed(st.runtime_failure_token), _LauncherOutcome(wrapper_rc=wrapper_rc, kv=kv)
    return None, _LauncherOutcome(wrapper_rc=wrapper_rc, kv=kv, warn_nonzero=warn_nonzero)


def _step2_run_launcher_with_retry(st: DispatchState) -> tuple[int | None, _LauncherOutcome | None]:
    from larch.implement.dispatch_step2 import _run_launcher

    wrapper_rc, kv, _ = _run_launcher(st)
    launcher_exit = kv.get("LAUNCHER_EXIT", "99")
    manifest_written = kv.get("MANIFEST_WRITTEN", "false")
    launcher_status = kv.get("STATUS", "")
    retry = (wrapper_rc != 0 or manifest_written != "true" or launcher_exit != "0") and manifest_written != "true"
    bail: int | None = None
    if launcher_status == "cap_hit":
        bail = st.emit_bailed("cap_hit")
    elif wrapper_rc == WRAPPER_VALIDATION_RC:
        bail = st.emit_bailed("wrapper-validation-failure")
    elif retry:
        dirty = _git_stdout(st.repo_root, "status", "--porcelain")
        index_lock = st.repo_root / ".git" / "index.lock"
        current_head = _git_stdout(st.repo_root, "rev-parse", "HEAD")
        if dirty or index_lock.exists() or current_head != st.baseline_sha:
            bail = st.emit_bailed("dirty-state-after-timeout")
        else:
            wrapper_rc, kv, _ = _run_launcher(st)
            if kv.get("STATUS", "") == "cap_hit":
                bail = st.emit_bailed("cap_hit")
            elif wrapper_rc == WRAPPER_VALIDATION_RC:
                bail = st.emit_bailed("wrapper-validation-failure")
    if bail is not None:
        return bail, None
    exit_code, outcome = _step2_evaluate_launcher_result(st, wrapper_rc, kv)
    if exit_code is not None:
        return exit_code, outcome
    return None, outcome


def _step2_load_manifest(st: DispatchState) -> tuple[int | None, dict | None, str]:
    if not st.manifest_path.is_file() or st.manifest_path.stat().st_size == 0:
        return st.emit_bailed("manifest-missing"), None, ""
    shutil.copyfile(st.manifest_path, st.manifest_raw_path)
    raw_obj = _json_load(st.manifest_raw_path)
    status = raw_obj.get("status", "") if isinstance(raw_obj, dict) and isinstance(raw_obj.get("status", ""), str) else ""
    schema_version = raw_obj.get("schema_version", "") if isinstance(raw_obj, dict) else ""
    if schema_version and str(schema_version) != "1":
        return st.emit_bailed("manifest-schema-invalid"), None, status
    if str(schema_version) != "1":
        return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj), None, status
    if status not in {"complete", "needs_qa", "bailed"}:
        return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj), None, status
    assert isinstance(raw_obj, dict)
    return None, raw_obj, status


def _step2_validate_needs_qa_schema(st: DispatchState, raw_obj: dict) -> int | None:
    nq = raw_obj.get("needs_qa")
    questions = nq.get("questions") if isinstance(nq, dict) else None
    if not (isinstance(questions, list) and questions):
        repaired = False
        qa_obj = _json_load(st.qa_pending_path)
        if isinstance(qa_obj, dict) and isinstance(qa_obj.get("items"), list) and qa_obj["items"]:
            repaired_questions: list[dict[str, str]] = []
            for idx, item in enumerate(qa_obj["items"]):
                if isinstance(item, dict):
                    parts = [f"{label}: {item[key]}" for key, label in (("area", "Area"), ("risk", "Risk"), ("suggested_check", "Suggested check")) if item.get(key)]
                    repaired_questions.append({"id": f"q{idx + 1}", "text": ". ".join(parts)})
            if repaired_questions:
                _write_text_atomic(path=st.qa_pending_path, text=json.dumps({"questions": repaired_questions}) + "\n")
                repaired = True
        if not repaired:
            return st.emit_bailed("manifest-schema-invalid")
    qa_obj = _json_load(st.qa_pending_path)
    if not (isinstance(qa_obj, dict) and isinstance(qa_obj.get("questions"), list) and qa_obj["questions"]):
        return st.emit_bailed("qa-pending-missing")
    return None


def _step2_validate_manifest_schema(st: DispatchState, raw_obj: dict, status: str) -> int | None:
    if status == "complete":
        if not _complete_schema_valid(raw_obj):
            return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj)
    elif status == "needs_qa":
        return _step2_validate_needs_qa_schema(st, raw_obj)
    elif status == "bailed" and (not isinstance(raw_obj.get("bail_reason"), str) or not raw_obj["bail_reason"]):
        return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj)
    return None


def _step2_post_manifest_safety(st: DispatchState, status: str) -> int | None:
    from larch.implement import dispatch_step2 as step2

    if status != "bailed":
        reason = step2._post_implementer_safety_reason(st)
        if reason:
            return st.emit_bailed(reason)
        step2._normalize_scout(st)
    return None


def _step2_commit_complete_manifest(st: DispatchState, raw_obj: dict) -> tuple[int | None, int]:
    from larch.implement.dispatch_step2 import _append_warning, _plan_coverage_uncovered_paths, _working_tree_touched_paths_and_failures

    invalid = _validate_manifest_paths(st=st, obj=raw_obj)
    if invalid:
        return st.emit_bailed(invalid), 0
    touched, touch_probe_failures = _working_tree_touched_paths_and_failures(st.repo_root)
    uncovered_plan_path_count = 0
    if touched is None:
        _append_warning(st=st, text="Step 7a.1 — skipped working-tree touched-path diagnostics because git probe(s) failed: " + ", ".join(touch_probe_failures))
    else:
        declared = {item.get("path") for item in raw_obj.get("files_touched", []) if isinstance(item, dict)} | {p for p in raw_obj.get("tests_added_or_modified", []) if isinstance(p, str)}
        missing = sorted(p for p in touched if p and p not in declared)
        if missing:
            _append_warning(st=st, text=f"- **Step 7a.1 — {len(missing)} working-tree path(s) not declared in manifest files_touched/tests_added_or_modified (may include pre-existing dirty files). First 5**: " + ", ".join(missing[:5]))
    uncovered = _plan_coverage_uncovered_paths(st=st, touched=touched)
    if uncovered:
        uncovered_plan_path_count = len(uncovered)
        _append_warning(st=st, text=f"- **Step 7a.1 — {len(uncovered)} explicit plan-listed path(s) untouched by the working-tree delta before dispatcher commit. First 10**: " + ", ".join(uncovered[:10]))
    commit_msg = redact.redact_secrets_only(str(raw_obj["commit_message"]))
    commit_msg_file = st.tmpdir / f"{st.tool_tag}-commit-message.txt"
    _write_text_atomic(path=commit_msg_file, text=commit_msg)
    commit_stderr = st.tmpdir / f"{st.tool_tag}-commit-stderr.txt"
    add = subprocess.run(
        [GIT_BIN, "-C", str(st.repo_root), "add", "-A"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
    )
    if add.returncode != 0:
        commit_stderr.write_text(add.stderr or "git add failed", encoding="utf-8", errors="replace")
        with contextlib.suppress(OSError):
            st.manifest_path.unlink()
        with contextlib.suppress(OSError):
            st.manifest_raw_path.unlink()
        return st.emit_bailed("commit-failed"), uncovered_plan_path_count
    commit = subprocess.run(
        [GIT_BIN, "-C", str(st.repo_root), "commit", "-F", str(commit_msg_file)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
    )
    if commit.returncode != 0:
        commit_stderr.write_text(commit.stderr, encoding="utf-8", errors="replace")
        with contextlib.suppress(OSError):
            st.manifest_path.unlink()
        with contextlib.suppress(OSError):
            st.manifest_raw_path.unlink()
        return st.emit_bailed("commit-failed"), uncovered_plan_path_count
    with contextlib.suppress(OSError):
        commit_stderr.unlink()
    _invoke_cli(["run-log", "flush"], cwd=st.repo_root)
    return None, uncovered_plan_path_count


def _step2_finalize_manifest(st: DispatchState, raw_obj: dict, status: str) -> int | None:
    from larch.implement import dispatch_step2 as step2

    sanitized = step2._sanitize_manifest_obj(raw_obj)
    _write_text_atomic(path=st.manifest_path, text=json.dumps(sanitized, indent=2, sort_keys=False) + "\n")
    if status == "complete":
        oos_obs = raw_obj.get("oos_observations")
        oos_nonempty = isinstance(oos_obs, list) and bool(oos_obs)
        reason = step2._materialize_oos(st, oos_observations_nonempty=oos_nonempty)
        if reason:
            return st.emit_bailed(reason)
    return None


def _step2_emit_status_kv(
    *,
    st: DispatchState,
    status: str,
    raw_obj: dict,
    warn_nonzero: bool,
    uncovered_plan_path_count: int,
) -> None:
    if status == "complete":
        _emit_kv(key="STATUS", value="complete")
        _emit_kv(key="TOOL", value=st.tool_tag)
        _emit_kv(key="MANIFEST", value=str(st.manifest_path))
        _emit_kv(key="TRANSCRIPT", value=str(st.transcript_path))
        _emit_kv(key="SIDECAR_LOG", value=str(st.sidecar_log))
        _emit_kv(key="SCOUT_CODER_MANIFEST", value=str(st.scout_coder_manifest))
        _emit_kv(key="SCOUT_CODER_STATUS", value=st.scout_status)
        if warn_nonzero and st.nonzero_exit_warn_token:
            _emit_kv(key=st.nonzero_exit_warn_token, value="true")
        if uncovered_plan_path_count:
            _emit_kv(key="WARN_PLAN_FILES_UNTOUCHED", value="true")
            _emit_kv(key="WARN_PLAN_FILES_UNTOUCHED_COUNT", value=uncovered_plan_path_count)
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="forbidden")
    elif status == "needs_qa":
        _emit_kv(key="STATUS", value="needs_qa")
        _emit_kv(key="TOOL", value=st.tool_tag)
        _emit_kv(key="MANIFEST", value=str(st.manifest_path))
        _emit_kv(key="QA_PENDING", value=str(st.qa_pending_path))
        _emit_kv(key="TRANSCRIPT", value=str(st.transcript_path))
        _emit_kv(key="SIDECAR_LOG", value=str(st.sidecar_log))
        _emit_kv(key="SCOUT_CODER_MANIFEST", value=str(st.scout_coder_manifest))
        _emit_kv(key="SCOUT_CODER_STATUS", value=st.scout_status)
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="forbidden")
    else:
        reason = str(raw_obj.get("bail_reason") or st.bailed_no_reason_token)
        reason = re.sub(r"\s+", " ", "".join(ch for ch in reason if ch >= " " and ch != "\x7f")).strip()[:200] or st.bailed_no_reason_token
        _emit_kv(key="STATUS", value="bailed")
        _emit_kv(key="REASON", value=reason)
        _emit_kv(key="TOOL", value=st.tool_tag)
        _emit_kv(key="MANIFEST", value=str(st.manifest_path))
        _emit_kv(key="TRANSCRIPT", value=str(st.transcript_path))
        _emit_kv(key="SIDECAR_LOG", value=str(st.sidecar_log))
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="forbidden")


@dataclass
class _Step2FlowContext:
    st: DispatchState
    outcome: _LauncherOutcome
    raw_obj: dict
    status: str
    uncovered_plan_path_count: int = 0


def _step2_flow_setup(args: argparse.Namespace) -> int | DispatchState:
    rc = _validate_step2_coder_args(args)
    if rc is not None:
        return rc
    exit_code, tmpdir = _step2_setup_tmpdir_env(args)
    if exit_code is not None:
        return exit_code
    assert tmpdir is not None
    fallback_rc = _step2_maybe_claude_fallback(args, tmpdir)
    if fallback_rc is not None:
        return fallback_rc
    exit_code, st = _step2_build_dispatch_state(args, tmpdir)
    if exit_code is not None:
        return exit_code
    assert st is not None
    for guard in (_step2_record_spawn_metadata, _step2_validate_spawn_branch, _step2_handle_resume):
        guard_rc = guard(st)
        if guard_rc is not None:
            return guard_rc
    _step2_prepare_launch_artifacts(st)
    return st


def _step2_flow_launch_and_load(st: DispatchState) -> int | _Step2FlowContext:
    launch_rc, outcome = _step2_run_launcher_with_retry(st)
    if launch_rc is not None:
        return launch_rc
    assert outcome is not None
    load_rc, raw_obj, status = _step2_load_manifest(st)
    if load_rc is not None:
        return load_rc
    assert raw_obj is not None
    return _Step2FlowContext(st=st, outcome=outcome, raw_obj=raw_obj, status=status)


def _step2_flow_prelaunch(args: argparse.Namespace) -> int | _Step2FlowContext:
    setup = _step2_flow_setup(args)
    if isinstance(setup, int):
        return setup
    loaded = _step2_flow_launch_and_load(setup)
    if isinstance(loaded, int):
        return loaded
    return loaded


def _step2_flow_finalize(ctx: _Step2FlowContext) -> int:
    schema_rc = _step2_validate_manifest_schema(ctx.st, ctx.raw_obj, ctx.status)
    if schema_rc is not None:
        return schema_rc
    safety_rc = _step2_post_manifest_safety(ctx.st, ctx.status)
    if safety_rc is not None:
        return safety_rc
    if ctx.status == "complete":
        commit_rc, ctx.uncovered_plan_path_count = _step2_commit_complete_manifest(ctx.st, ctx.raw_obj)
        if commit_rc is not None:
            return commit_rc
    finalize_rc = _step2_finalize_manifest(ctx.st, ctx.raw_obj, ctx.status)
    if finalize_rc is not None:
        return finalize_rc
    _step2_emit_status_kv(
        st=ctx.st,
        status=ctx.status,
        raw_obj=ctx.raw_obj,
        warn_nonzero=ctx.outcome.warn_nonzero,
        uncovered_plan_path_count=ctx.uncovered_plan_path_count,
    )
    return 0


def run_step2_dispatch_flow(args: argparse.Namespace) -> int:
    pre = _step2_flow_prelaunch(args)
    if isinstance(pre, int):
        return pre
    assert isinstance(pre, _Step2FlowContext)
    return _step2_flow_finalize(pre)
