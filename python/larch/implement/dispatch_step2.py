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
from dataclasses import dataclass
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
from larch.implement.dispatch_step2_flow import run_step2_dispatch_flow
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


@dataclass(frozen=True)
class _RunDispatchLockJob:
    tmpdir: Path
    child: list[str]
    plugin_root: str
    args: argparse.Namespace
    codex_binary_found: str
    cursor_binary_found: str


def _validate_run_dispatch_args(args: argparse.Namespace, tmpdir: Path) -> int | None:
    session_env = tmpdir / "session-env.sh"
    feature_file = tmpdir / "feature-description.txt"
    plan_file = tmpdir / "plan.txt"
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or _session_get(file=session_env, key="LARCH_CLAUDE_PLUGIN_ROOT", default="") or str(_PLUGIN_ROOT)
    error: str | None = None
    if not tmpdir.is_dir():
        error = f"implement run-dispatch: --implement-tmpdir not a directory: {tmpdir}"
    elif not session_env.is_file():
        error = f"implement run-dispatch: session-env not readable: {session_env}"
    elif not feature_file.is_file():
        error = f"implement run-dispatch: feature file not found: {feature_file}"
    elif not plan_file.is_file():
        error = f"implement run-dispatch: plan file not found at conventional path: {plan_file}"
    elif args.answers and not Path(args.answers).is_file():
        error = f"implement run-dispatch: --answers path does not exist: {args.answers}"
    elif not Path(plugin_root).is_dir():
        error = f"implement run-dispatch: plugin root not a directory: {plugin_root}"
    if error is not None:
        _err(error)
        return 2
    return None


def _build_run_dispatch_child(
    *,
    tmpdir: Path,
    plugin_root: str,
    args: argparse.Namespace,
    session_env: Path,
) -> list[str]:
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
        str(tmpdir / "plan.txt"),
        "--feature-file",
        str(tmpdir / "feature-description.txt"),
        "--coder",
        args.coder,
        "--cursor-binary-found",
        cursor_binary_found,
        "--codex-binary-found",
        codex_binary_found,
    ]
    if args.answers:
        child.extend(["--answers", args.answers])
    return child


def _run_dispatch_locked(job: _RunDispatchLockJob) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = job.plugin_root
    env["IMPLEMENT_TMPDIR"] = str(job.tmpdir)
    lock_path = job.tmpdir / "dispatch.lock"
    lock_fd = None
    try:
        lock_fd = lock_path.open("w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        if lock_fd is not None:
            lock_fd.close()
        if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
            raise _RunDispatchLockError("implement run-dispatch: another dispatch is already running in this tmpdir") from exc
        raise _RunDispatchLockError(f"implement run-dispatch: failed to acquire dispatch lock: {exc}") from exc
    try:
        _rehydrate_larch_triplet(job.tmpdir)
        telemetry_marked = False
        if not job.args.answers:
            telemetry_marked = _maybe_mark_step2_telemetry(
                tmpdir=job.tmpdir,
                plugin_root=Path(job.plugin_root),
                env=env,
                coder=job.args.coder,
                codex_binary_found=job.codex_binary_found,
                cursor_binary_found=job.cursor_binary_found,
                write_sentinel=False,
            )
        result = subprocess.run(job.child, text=True, capture_output=True, env=env, check=False)
        if _child_stdout_is_claude_fallback(result.stdout):
            _clear_external_dispatch_seed(job.tmpdir)
            repo_root = _resolve_repo_root()
            if repo_root is None:
                raise _RunDispatchLockError("implement run-dispatch: git rev-parse --show-toplevel failed after claude_fallback")
            rc = _capture_prelaunch_porcelain(repo_root=repo_root, implement_tmpdir=job.tmpdir)
            if rc != 0:
                raise _RunDispatchLockError("implement run-dispatch: prelaunch porcelain capture failed after claude_fallback", rc)
        if telemetry_marked and not (job.tmpdir / ".step2-telemetry-marked").is_file():
            _write_step2_telemetry_sentinel(job.tmpdir)
        return result
    finally:
        lock_fd.close()


class _RunDispatchLockError(Exception):
    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def run_dispatch_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement run-dispatch")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--coder", required=True)
    parser.add_argument("--answers", default="")
    args = parser.parse_args(argv)
    tmp_arg = Path(args.implement_tmpdir)
    tmpdir = tmp_arg.resolve()
    if (rc := _validate_run_dispatch_args(args, tmp_arg)) is not None:
        return rc
    session_env = tmpdir / "session-env.sh"
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or _session_get(file=session_env, key="LARCH_CLAUDE_PLUGIN_ROOT", default="") or str(_PLUGIN_ROOT)
    child = _build_run_dispatch_child(tmpdir=tmpdir, plugin_root=plugin_root, args=args, session_env=session_env)
    codex_binary_found = _binary_available(session_env=session_env, key="CODEX_BINARY_FOUND", binary="codex")
    cursor_binary_found = _binary_available(session_env=session_env, key="CURSOR_BINARY_FOUND", binary="cursor")
    try:
        result = _run_dispatch_locked(
            _RunDispatchLockJob(
                tmpdir=tmpdir,
                child=child,
                plugin_root=plugin_root,
                args=args,
                codex_binary_found=codex_binary_found,
                cursor_binary_found=cursor_binary_found,
            )
        )
    except _RunDispatchLockError as exc:
        _err(str(exc))
        return exc.exit_code
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


def step2_dispatch_main(argv: list[str] | None = None) -> int:
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
    return run_step2_dispatch_flow(args)
