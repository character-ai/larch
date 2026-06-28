# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Step 2 dispatch: run-dispatch launcher and step2-dispatch orchestrator."""

from __future__ import annotations

import argparse
import contextlib
import errno
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from larch.core import logging_util
from larch.core import redact
from larch.issue import issue_wire
from larch.implement.dispatch_helpers import (
    _binary_available,
    _child_stdout_is_claude_fallback,
    _capture_prelaunch_porcelain,
    _emit_kv,
    _err,
    _git,
    _git_stdout,
    _invoke_cli,
    _maybe_mark_step2_telemetry,
    _parse_kv,
    _rehydrate_larch_triplet,
    _resolve_repo_root,
    _run,
    _session_get,
    _write_step2_telemetry_sentinel,
    _write_text_atomic,
    GIT_BIN,
    RESUME_CAP,
    WRAPPER_VALIDATION_RC,
    _PLUGIN_ROOT,
    _SAFE_CODERS,
)
from larch.implement.dispatch_ship_seed import _clear_external_dispatch_seed
from larch.implement.dispatch_manifest import (
    DispatchState,
    _clear_external_scout_state,
    _complete_schema_valid,
    _emit_manifest_invalid_or_recover,
    _json_load,
    _manifest_complete_salvageable,
    _materialize_oos,
    _normalize_scout,
    _post_implementer_safety_reason,
    _sanitize_manifest_obj,
    _validate_manifest_paths,
    _write_prelaunch_baseline,
)


def run_dispatch_main(argv: list[str] | None = None) -> int:  # noqa: C901,PLR0911,PLR0912,PLR0915,RUF100
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement run-dispatch")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--coder", required=True)
    parser.add_argument("--answers", default="")
    args = parser.parse_args(argv)
    tmp_arg = Path(args.implement_tmpdir)
    if not tmp_arg.is_dir():
        _err(f"implement run-dispatch: --implement-tmpdir not a directory: {tmp_arg}")
        return 2
    tmpdir = tmp_arg.resolve()
    session_env = tmpdir / "session-env.sh"
    feature_file = tmpdir / "feature-description.txt"
    plan_file = tmpdir / "plan.txt"
    if not session_env.is_file():
        _err(f"implement run-dispatch: session-env not readable: {session_env}")
        return 2
    if not feature_file.is_file():
        _err(f"implement run-dispatch: feature file not found: {feature_file}")
        return 2
    if not plan_file.is_file():
        _err(f"implement run-dispatch: plan file not found at conventional path: {plan_file}")
        return 2
    if args.answers and not Path(args.answers).is_file():
        _err(f"implement run-dispatch: --answers path does not exist: {args.answers}")
        return 2
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or _session_get(file=session_env, key="LARCH_CLAUDE_PLUGIN_ROOT", default="") or str(_PLUGIN_ROOT)
    if not Path(plugin_root).is_dir():
        _err(f"implement run-dispatch: plugin root not a directory: {plugin_root}")
        return 2
    cursor_binary_found = _binary_available(session_env=session_env, key="CURSOR_BINARY_FOUND", binary="cursor")
    codex_binary_found = _binary_available(session_env=session_env, key="CODEX_BINARY_FOUND", binary="codex")
    child = [
        sys.executable,
        str(Path(plugin_root) / "python" / "cli.py"),
        "implement",
        "step2-dispatch",
        "--tmpdir",
        str(tmpdir),
        "--plan-file",
        str(plan_file),
        "--feature-file",
        str(feature_file),
        "--coder",
        args.coder,
        "--cursor-binary-found",
        cursor_binary_found,
        "--codex-binary-found",
        codex_binary_found,
    ]
    if args.answers:
        child.extend(["--answers", args.answers])
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = plugin_root
    env["IMPLEMENT_TMPDIR"] = str(tmpdir)
    lock_path = tmpdir / "dispatch.lock"
    lock_fd = None
    try:
        lock_fd = lock_path.open("w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        if lock_fd is not None:
            lock_fd.close()
        if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            _err("implement run-dispatch: another dispatch is already running in this tmpdir")
        else:
            _err(f"implement run-dispatch: failed to acquire dispatch lock: {exc}")
        return 2
    try:
        _rehydrate_larch_triplet(tmpdir)
        telemetry_marked = False
        if not args.answers:
            telemetry_marked = _maybe_mark_step2_telemetry(
                tmpdir=tmpdir,
                plugin_root=Path(plugin_root),
                env=env,
                coder=args.coder,
                codex_binary_found=codex_binary_found,
                cursor_binary_found=cursor_binary_found,
                write_sentinel=False,
            )
        result = subprocess.run(child, text=True, capture_output=True, env=env, check=False)
        if _child_stdout_is_claude_fallback(result.stdout):
            _clear_external_dispatch_seed(tmpdir)
            repo_root = _resolve_repo_root()
            if repo_root is None:
                _err("implement run-dispatch: git rev-parse --show-toplevel failed after claude_fallback")
                return 2
            rc = _capture_prelaunch_porcelain(repo_root=repo_root, implement_tmpdir=tmpdir)
            if rc != 0:
                _err("implement run-dispatch: prelaunch porcelain capture failed after claude_fallback")
                return rc
        if telemetry_marked and not (tmpdir / ".step2-telemetry-marked").is_file():
            _write_step2_telemetry_sentinel(tmpdir)
    finally:
        lock_fd.close()
    if result.stdout:
        stream = logging_util.contract_stream()
        stream.write(result.stdout)
        stream.flush()
    if result.stderr:
        _err(result.stderr.rstrip("\n"))
    return result.returncode


def _dispatch_state(*, args: argparse.Namespace, repo_root: Path, tmpdir: Path, plugin_root: Path) -> DispatchState:
    tool = args.coder
    manifest_path = tmpdir / "manifest.json"
    qa_pending_path = tmpdir / "qa-pending.json"
    transcript = tmpdir / f"{tool}-impl-transcript.txt"
    launch_scout = tmpdir / "scout-coder-manifest.json"
    if tool == "codex":
        out_dir = tmpdir / "codex-step2-out"
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = out_dir / "manifest.json"
        qa_pending_path = out_dir / "qa-pending.json"
        transcript = out_dir / f"{tool}-impl-transcript.txt"
        launch_scout = out_dir / "scout-coder-manifest.json"
    return DispatchState(
        repo_root=repo_root,
        tmpdir=tmpdir,
        plan_file=Path(args.plan_file),
        feature_file=Path(args.feature_file),
        coder=tool,
        cursor_present=args.cursor_present or "false",
        cursor_binary_found=args.cursor_binary_found or "",
        codex_binary_found=args.codex_binary_found or "",
        answers_file=Path(args.answers) if args.answers else None,
        plugin_root=plugin_root,
        tool_tag=tool,
        manifest_path=manifest_path,
        manifest_raw_path=tmpdir / "manifest-raw.json",
        qa_pending_path=qa_pending_path,
        transcript_path=transcript,
        sidecar_log=tmpdir / f"{tool}-impl.log",
        scout_coder_manifest=tmpdir / "scout-coder-manifest.json",
        launch_scout_manifest=launch_scout,
        external_scout_marker=tmpdir / "step2-external-scout-eligible.txt",
        baseline_file=tmpdir / "step2-baseline.txt",
        prelaunch_porcelain=tmpdir / "step2-prelaunch-porcelain.nul",
        postlaunch_porcelain=tmpdir / "step2-postlaunch-porcelain.nul",
        prelaunch_digests=tmpdir / "step2-prelaunch-content-digests.txt",
        prelaunch_index_flag=tmpdir / "step2-prelaunch-index.env",
        recovery_paths_file=tmpdir / "step2-recovery-paths.nul",
        resume_count_file=tmpdir / f"{tool}-resume-count.txt",
        spawn_branch_file=tmpdir / "step2-spawn-branch.txt",
        spawn_coder_file=tmpdir / "step2-spawn-coder.txt",
        runtime_failure_token=f"{tool}-runtime-failure",
        bailed_no_reason_token=f"{tool}-bailed-no-reason",
        requires_head_unchanged=(tool == "cursor"),
        nonzero_exit_warn_token="WARN_CODEX_NONZERO_EXIT" if tool == "codex" else "",
    )


def _launcher_args(st: DispatchState) -> list[str]:
    args = [
        "agent",
        f"launch-{st.tool_tag}-implement",
        "--transcript-path",
        str(st.transcript_path),
        "--sidecar-log",
        str(st.sidecar_log),
        "--manifest-path",
        str(st.manifest_path),
        "--qa-pending-path",
        str(st.qa_pending_path),
        "--scout-manifest-path",
        str(st.launch_scout_manifest),
        "--plan-file",
        str(st.plan_file),
        "--feature-file",
        str(st.feature_file),
        "--agent-prompt",
        str(st.plugin_root / "agents" / f"{st.tool_tag}-implementer.md"),
        "--timeout",
        "7200",
    ]
    cap = os.environ.get("LARCH_TOKEN_BUDGET_CAP_IMPLEMENT", "")
    if cap:
        args.extend(["--token-budget-cap", cap])
    if st.answers_file is not None:
        args.extend(["--answers-file", str(st.answers_file)])
    return args


def _run_launcher(st: DispatchState) -> tuple[int, dict[str, str], str]:
    result = _invoke_cli(_launcher_args(st), cwd=st.repo_root)
    out = (result.stdout or "")[:65536]
    return result.returncode, _parse_kv(out), out + (result.stderr or "")


def _append_warning(*, st: DispatchState, text: str) -> None:
    # exec_issue_detail counts/renders only lines that start with "- "; normalize
    # plain warning text to a bullet so it is not dropped from the final summary.
    entry = text if text.startswith("- ") else f"- {text}"
    _invoke_cli(["run-log", "append-entry", "--log", str(st.tmpdir / "execution-issues.md"), "--category", "Warnings", "--entry", entry])


def _working_tree_touched_paths_and_failures(repo_root: Path) -> tuple[set[str] | None, list[str]]:
    probes = [
        ("git diff --name-only HEAD", ("diff", "--name-only", "HEAD")),
        ("git ls-files --others --exclude-standard", ("ls-files", "--others", "--exclude-standard")),
    ]
    touched: set[str] = set()
    failures: list[str] = []
    for label, args in probes:
        result = _git(repo_root, *args)
        if result.returncode != 0:
            failures.append(label)
            continue
        touched.update(line for line in str(result.stdout).splitlines() if line)
    if failures:
        return None, failures
    return touched, []


def _working_tree_touched_paths(repo_root: Path) -> set[str] | None:
    touched, _failures = _working_tree_touched_paths_and_failures(repo_root)
    return touched


def _explicit_plan_scope_paths(plan_text: str) -> list[str]:
    return issue_wire.extract_scope_paths(plan_text=plan_text, use_fallback=False, include_optional=False)


def _plan_coverage_uncovered_paths(*, st: DispatchState, touched: set[str] | None) -> list[str] | None:
    if touched is None:
        return None
    try:
        plan_text = st.plan_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _append_warning(st=st, text=f"Step 7a.1 — could not read plan file for plan-file coverage: {st.plan_file}: {exc}")
        return None
    explicit = _explicit_plan_scope_paths(plan_text)
    if not explicit:
        return []
    return sorted(path for path in explicit if path not in touched)


def step2_dispatch_main(argv: list[str] | None = None) -> int:  # noqa: C901,PLR0911,PLR0912,PLR0915,RUF100
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement step2-dispatch")
    parser.add_argument("--tmpdir", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--feature-file", required=True)
    parser.add_argument("--coder", default="")
    parser.add_argument("--codex-available", default="")
    parser.add_argument("--cursor-present", default="")
    parser.add_argument("--codex-present", default="")
    parser.add_argument("--cursor-available", default="")
    parser.add_argument("--codex-binary-found", default="")
    parser.add_argument("--cursor-binary-found", default="")
    parser.add_argument("--answers", default="")
    args = parser.parse_args(argv)

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
    tmpdir_raw = Path(args.tmpdir)
    if not tmpdir_raw.is_dir():
        _err(f"implement step2-dispatch: --tmpdir not a directory: {tmpdir_raw}")
        return 2
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
        return 2
    if not Path(args.feature_file).is_file():
        _err(f"implement step2-dispatch: --feature-file not found: {args.feature_file}")
        return 2
    if args.coder == "claude":
        _clear_external_scout_state(tmpdir)
        _emit_kv(key="STATUS", value="claude_fallback")
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
        return 0
    session_env = tmpdir / "session-env.sh"
    if not args.cursor_binary_found:
        args.cursor_binary_found = _binary_available(session_env=session_env, key="CURSOR_BINARY_FOUND", binary="cursor")
    if not args.codex_binary_found:
        args.codex_binary_found = _binary_available(session_env=session_env, key="CODEX_BINARY_FOUND", binary="codex")
    if args.coder == "cursor" and args.cursor_binary_found != "true":
        _clear_external_scout_state(tmpdir)
        _emit_kv(key="STATUS", value="claude_fallback")
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
        return 0
    if args.coder == "codex" and args.codex_binary_found != "true":
        _clear_external_scout_state(tmpdir)
        _emit_kv(key="STATUS", value="claude_fallback")
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
        return 0

    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("LARCH_CLAUDE_PLUGIN_ROOT") or _PLUGIN_ROOT).resolve()
    repo_result = _run(["git", "rev-parse", "--show-toplevel"])
    if repo_result.returncode != 0 or not repo_result.stdout.strip():
        _err("implement step2-dispatch: must be invoked from within a git working tree (git rev-parse --show-toplevel failed)")
        return 2
    repo_root = Path(repo_result.stdout.strip()).resolve()
    st = _dispatch_state(args=args, repo_root=repo_root, tmpdir=tmpdir, plugin_root=plugin_root)
    if not (plugin_root / "agents" / f"{st.tool_tag}-implementer.md").is_file():
        _err(f"implement step2-dispatch: agent prompt missing: {plugin_root / 'agents' / (st.tool_tag + '-implementer.md')}")
        return 2

    if st.spawn_coder_file.is_file():
        if st.spawn_coder_file.read_text(encoding="utf-8", errors="replace").strip() != st.coder:
            return st.emit_bailed("coder-mismatch-tmpdir-reuse")
    else:
        _write_text_atomic(path=st.spawn_coder_file, text=st.coder + "\n")
    if not st.baseline_file.is_file():
        _write_text_atomic(path=st.baseline_file, text=_git_stdout(repo_root, "rev-parse", "HEAD") + "\n")
    st.baseline_sha = st.baseline_file.read_text(encoding="utf-8", errors="replace").strip()
    if not st.spawn_branch_file.is_file():
        _write_text_atomic(path=st.spawn_branch_file, text=_git_stdout(repo_root, "symbolic-ref", "-q", "--short", "HEAD") + "\n")
    st.spawn_branch = st.spawn_branch_file.read_text(encoding="utf-8", errors="replace").strip()
    session_env = tmpdir / "session-env.sh"
    parent_issue = tmpdir / "parent-issue.md"
    issue_from_parent = _session_get(file=parent_issue, key="ISSUE_NUMBER", default="") if parent_issue.is_file() else ""
    forked_target = _session_get(file=session_env, key="FORKED_TARGET", default="false") if session_env.is_file() else "false"
    issue_anchored = bool(issue_from_parent) or session_env.is_file()
    if forked_target != "true" and issue_anchored and (not st.spawn_branch or st.spawn_branch == "HEAD"):
        return st.emit_bailed("detached-head-prohibited")
    if forked_target != "true" and issue_anchored and st.spawn_branch in {"main", "master"}:
        return st.emit_bailed("main-branch-prohibited")

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

    for path in (st.manifest_path, st.manifest_raw_path, st.qa_pending_path, st.transcript_path, st.sidecar_log, st.launch_scout_manifest):
        with contextlib.suppress(OSError):
            path.unlink()
    _clear_external_scout_state(tmpdir)
    _write_prelaunch_baseline(st)

    wrapper_rc, kv, _ = _run_launcher(st)
    if wrapper_rc == WRAPPER_VALIDATION_RC:
        return st.emit_bailed("wrapper-validation-failure")
    launcher_exit = kv.get("LAUNCHER_EXIT", "99")
    manifest_written = kv.get("MANIFEST_WRITTEN", "false")
    launcher_status = kv.get("STATUS", "")
    if launcher_status == "cap_hit":
        return st.emit_bailed("cap_hit")
    if (wrapper_rc != 0 or manifest_written != "true" or launcher_exit != "0") and manifest_written != "true":
        dirty = _git_stdout(repo_root, "status", "--porcelain")
        index_lock = repo_root / ".git" / "index.lock"
        current_head = _git_stdout(repo_root, "rev-parse", "HEAD")
        if dirty or index_lock.exists() or current_head != st.baseline_sha:
            return st.emit_bailed("dirty-state-after-timeout")
        wrapper_rc, kv, _ = _run_launcher(st)
        if wrapper_rc == WRAPPER_VALIDATION_RC:
            return st.emit_bailed("wrapper-validation-failure")
        launcher_exit = kv.get("LAUNCHER_EXIT", "99")
        manifest_written = kv.get("MANIFEST_WRITTEN", "false")
        launcher_status = kv.get("STATUS", "")
        if launcher_status == "cap_hit":
            return st.emit_bailed("cap_hit")
    if wrapper_rc != 0:
        return st.emit_bailed(st.runtime_failure_token)
    if manifest_written != "true":
        return st.emit_bailed(st.runtime_failure_token)
    warn_nonzero = False
    if launcher_exit != "0":
        if st.coder == "codex" and _manifest_complete_salvageable(st.manifest_path):
            warn_nonzero = True
            _append_warning(st=st, text=f"Step 4 — {st.tool_tag} exited non-zero (LAUNCHER_EXIT={launcher_exit}) after atomically writing a complete manifest; not discarding it — continuing to validation/commit ({st.nonzero_exit_warn_token}=true). A self-verification step likely failed after the implementation work completed.")
        else:
            return st.emit_bailed(st.runtime_failure_token)

    if not st.manifest_path.is_file() or st.manifest_path.stat().st_size == 0:
        return st.emit_bailed("manifest-missing")
    shutil.copyfile(st.manifest_path, st.manifest_raw_path)
    raw_obj = _json_load(st.manifest_raw_path)
    status = raw_obj.get("status", "") if isinstance(raw_obj, dict) and isinstance(raw_obj.get("status", ""), str) else ""
    schema_version = raw_obj.get("schema_version", "") if isinstance(raw_obj, dict) else ""
    if schema_version and str(schema_version) != "1":
        return st.emit_bailed("manifest-schema-invalid")
    if str(schema_version) != "1":
        return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj)
    if status not in {"complete", "needs_qa", "bailed"}:
        return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj)
    assert isinstance(raw_obj, dict)
    if status == "complete":
        if not _complete_schema_valid(raw_obj):
            return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj)
    elif status == "needs_qa":
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
    elif status == "bailed" and (not isinstance(raw_obj.get("bail_reason"), str) or not raw_obj["bail_reason"]):
        return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj)

    if status != "bailed":
        reason = _post_implementer_safety_reason(st)
        if reason:
            return st.emit_bailed(reason)
        _normalize_scout(st)

    uncovered_plan_path_count = 0
    if status == "complete":
        invalid = _validate_manifest_paths(st=st, obj=raw_obj)
        if invalid:
            return st.emit_bailed(invalid)
        touched, touch_probe_failures = _working_tree_touched_paths_and_failures(repo_root)
        if touched is None:
            _append_warning(st=st, text="Step 7a.1 — skipped working-tree touched-path diagnostics because git probe(s) failed: " + ", ".join(touch_probe_failures))
        else:
            # Diagnostic-only undeclared path warning.
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
            [GIT_BIN, "-C", str(repo_root), "add", "-A"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
        )
        if add.returncode != 0:
            commit_stderr.write_text(add.stderr or "git add failed", encoding="utf-8", errors="replace")
            with contextlib.suppress(OSError):
                st.manifest_path.unlink()
            with contextlib.suppress(OSError):
                st.manifest_raw_path.unlink()
            return st.emit_bailed("commit-failed")
        commit = subprocess.run(
            [GIT_BIN, "-C", str(repo_root), "commit", "-F", str(commit_msg_file)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
        )
        if commit.returncode != 0:
            commit_stderr.write_text(commit.stderr, encoding="utf-8", errors="replace")
            with contextlib.suppress(OSError):
                st.manifest_path.unlink()
            with contextlib.suppress(OSError):
                st.manifest_raw_path.unlink()
            return st.emit_bailed("commit-failed")
        with contextlib.suppress(OSError):
            commit_stderr.unlink()
        _invoke_cli(["run-log", "flush"], cwd=repo_root)

    sanitized = _sanitize_manifest_obj(raw_obj)
    _write_text_atomic(path=st.manifest_path, text=json.dumps(sanitized, indent=2, sort_keys=False) + "\n")
    if status == "complete":
        oos_obs = raw_obj.get("oos_observations")
        oos_nonempty = isinstance(oos_obs, list) and bool(oos_obs)
        reason = _materialize_oos(st, oos_observations_nonempty=oos_nonempty)
        if reason:
            return st.emit_bailed(reason)

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
    return 0
