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

from larch import io as larch_io
from larch.agents._launch_failure import detect_codex_cli_gate, is_quota_failure
from larch.agents._types import CodexGateDetail
from larch.bgjob import model as bgjob_model
from larch.core import config
from larch.core import architectural_guidelines
from larch.core import logging_util
from larch.core.repo_roots import repo_root_probe
from larch.calibration import difficulty
from larch.core import redact
from larch.issue import issue_wire
from larch.issue import migration_governance
from larch.core import proc
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
from larch.implement import dispatch_helpers, scope_disposition
from larch.errors import ShipError
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
    _require_architectural_acknowledgment,
    _sanitize_manifest_obj,
    _validate_manifest_paths,
    _write_prelaunch_baseline,
)
from larch.implement.dispatch_recovery import RecoveryPorcelainInputs, compute_recovery_paths

_ASCII_CONTROL_MAX = 31
_ASCII_DELETE = 127
_ARCH_KNOWLEDGE_SNAPSHOT = "step2-architectural-knowledge.env"
_PRIOR_ATTEMPT_REASON = "prior-attempt-unfinalized"
_COMPLETION_RETRY_STATE_INVALID = "completion-retry-state-invalid"
_COMPLETION_RETRY_STATE_STALE = "completion-retry-state-stale"


def _publish_bgjob_envelope(*, tmpdir: Path, path: str, text: str) -> bool:
    """Publish the child envelope for daemon result-env merging.

    The adapter pre-creates this path. Validate it again here because the child
    must never write an arbitrary caller-controlled path while it owns a live
    dispatch.
    """
    candidate = Path(path)
    try:
        merge_env = bgjob_model.validate_merge_result_env(path=candidate, tmpdir=tmpdir)
        larch_io.trusted_atomic_write(path=merge_env, text=text, root=tmpdir)
    except (OSError, ValueError):
        return False
    return True


def run_dispatch_main(argv: list[str] | None = None) -> int:  # noqa: C901,PLR0911,PLR0912,PLR0915,RUF100
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement run-dispatch")
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--coder", required=True)
    parser.add_argument("--answers", default="")
    parser.add_argument("--difficulty", choices=("", *config.DIFFICULTY_TIERS), default="")
    parser.add_argument("--bgjob-child", action="store_true")
    parser.add_argument("--merge-result-env", default="")
    args = parser.parse_args(argv)
    if args.bgjob_child != bool(args.merge_result_env):
        _err("implement run-dispatch: --bgjob-child and --merge-result-env must be supplied together")
        return 2
    raw_tmpdir = args.implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not raw_tmpdir:
        _err("implement run-dispatch: --implement-tmpdir is required or IMPLEMENT_TMPDIR must be set")
        return 2
    tmp_arg = Path(raw_tmpdir)
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
    difficulty_arg = args.difficulty or difficulty.resolve_step2_effective_difficulty(tmpdir)
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
    if difficulty_arg:
        child.extend(["--difficulty", difficulty_arg])
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
    if args.bgjob_child and result.returncode == 0 and not _publish_bgjob_envelope(
        tmpdir=tmpdir, path=args.merge_result_env, text=result.stdout
    ):
        _err("implement run-dispatch: could not publish bgjob result envelope")
        return 2
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
        completion_retry_state_file=tmpdir / "step2-completion-retry-state.env",
        completion_retry_feedback_file=tmpdir / "step2-completion-retry.md",
        spawn_branch_file=tmpdir / "step2-spawn-branch.txt",
        spawn_coder_file=tmpdir / "step2-spawn-coder.txt",
        runtime_failure_token=f"{tool}-runtime-failure",
        bailed_no_reason_token=f"{tool}-bailed-no-reason",
        requires_head_unchanged=(tool == "cursor"),
        nonzero_exit_warn_token="WARN_CODEX_NONZERO_EXIT" if tool == "codex" else "",
        difficulty=args.difficulty,
    )


def _external_implementer_prompt_path(*, plugin_root: Path, tool_tag: str) -> Path:
    return plugin_root / "skills" / "implement" / "prompts" / f"{tool_tag}-implementer.md"


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
        str(_external_implementer_prompt_path(plugin_root=st.plugin_root, tool_tag=st.tool_tag)),
        "--timeout",
        "7200",
    ]
    cap = os.environ.get("LARCH_TOKEN_BUDGET_CAP_IMPLEMENT", "")
    if cap:
        args.extend(["--token-budget-cap", cap])
    if st.tool_tag in {"codex", "cursor"} and st.difficulty:
        args.extend(["--difficulty", st.difficulty])
    if st.answers_file is not None:
        args.extend(["--answers-file", str(st.answers_file)])
    completion_retry_feedback = getattr(st, "completion_retry_feedback_file", None)
    if completion_retry_feedback is not None and completion_retry_feedback.is_file():
        args.extend(["--completion-retry-file", str(completion_retry_feedback)])
    return args


def _run_launcher(st: DispatchState) -> tuple[int, dict[str, str], str]:
    result = _invoke_cli(_launcher_args(st), cwd=st.repo_root)
    stdout = result.stdout or ""
    return result.returncode, _parse_kv(stdout[:65536]), stdout + (result.stderr or "")


def _completion_retry_state(st: DispatchState) -> tuple[int, str] | None:
    """Return retry state only when its bounded wire record is valid."""
    if not st.completion_retry_state_file.exists():
        return 0, ""
    try:
        raw = larch_io.read_trusted_text(
            st.completion_retry_state_file, root=st.tmpdir, errors="replace"
        )
        data = larch_io.parse_kv(raw, skip_comments=True, cr_strip="strip")
    except (OSError, ValueError):
        return None
    count_text = data.get("COMPLETION_RETRY_COUNT", "")
    fingerprint = data.get("PLAN_COVERAGE_FINGERPRINT", "")
    if not count_text.isdigit() or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        return None
    count = int(count_text)
    if not 0 < count <= config.IMPLEMENT_COMPLETION_RETRY_CAP:
        return None
    return count, fingerprint


def _completion_retry_args(*, args: argparse.Namespace) -> list[str]:
    retry_args = [
        "--tmpdir", args.tmpdir,
        "--plan-file", args.plan_file,
        "--feature-file", args.feature_file,
        "--coder", args.coder,
        "--completion-retry",
    ]
    for name in ("cursor_present", "codex_binary_found", "cursor_binary_found"):
        value = getattr(args, name)
        if value:
            retry_args.extend([f"--{name.replace('_', '-')}", value])
    if args.difficulty:
        retry_args.extend(["--difficulty", args.difficulty])
    return retry_args


def _retry_incomplete_completion(
    *, args: argparse.Namespace, st: DispatchState, coverage: scope_disposition.PlanCoverage
) -> int | None:
    """Re-dispatch a proven-incomplete coder result, bounded by configuration."""
    state = _completion_retry_state(st)
    if state is None:
        return st.emit_bailed(_COMPLETION_RETRY_STATE_INVALID)
    count, _fingerprint = state
    if count >= config.IMPLEMENT_COMPLETION_RETRY_CAP:
        _append_warning(
            st=st,
            text=(
                "Step 2 completion retries exhausted after "
                f"{count} retry attempt(s); retaining the required scope-disposition gate."
            ),
        )
        return None
    next_count = count + 1
    feedback_lines = [
        "# Completion retry",
        "",
        "The previous implementation attempt declared completion, but "
        "independent plan coverage found required work incomplete.",
        "Preserve compatible existing edits and finish the remaining plan scope. "
        "Do not declare completion until all required work is complete.",
        "",
        f"Retry attempt: {next_count} of {config.IMPLEMENT_COMPLETION_RETRY_CAP}",
        "",
        "## Required plan paths still untouched",
        "",
    ]
    feedback_lines.extend(f"- `{path}`" for path in coverage.untouched_paths)
    if coverage.todos_left:
        feedback_lines.extend(["", "## Blocking deferred work reported by the prior attempt", ""])
        feedback_lines.extend(f"- {item}" for item in coverage.todos_left)
    larch_io.trusted_atomic_write(
        st.completion_retry_state_file,
        f"COMPLETION_RETRY_COUNT={next_count}\n"
        f"PLAN_COVERAGE_FINGERPRINT={coverage.fingerprint}\n",
        root=st.tmpdir,
    )
    _write_text_atomic(
        path=st.completion_retry_feedback_file, text="\n".join(feedback_lines) + "\n"
    )
    _append_warning(
        st=st,
        text=(
            "Step 2 independently found incomplete plan coverage; "
            f"re-dispatching {st.tool_tag} for completion retry {next_count}/{config.IMPLEMENT_COMPLETION_RETRY_CAP}."
        ),
    )
    return step2_dispatch_main(_completion_retry_args(args=args))


def _append_warning(*, st: DispatchState, text: str) -> None:
    # exec_issue_detail counts/renders only lines that start with "- "; normalize
    # plain warning text to a bullet so it is not dropped from the final summary.
    entry = text if text.startswith("- ") else f"- {text}"
    _invoke_cli(["run-log", "append-entry", "--log", str(st.tmpdir / "execution-issues.md"), "--category", "Warnings", "--entry", entry])


def _snapshot_architectural_knowledge_required(tmpdir: Path, repo_root: Path) -> bool:
    snapshot = tmpdir / _ARCH_KNOWLEDGE_SNAPSHOT
    if snapshot.is_file():
        value = larch_io.read_kv(
            path=snapshot,
            key="ARCHITECTURAL_KNOWLEDGE_REQUIRED",
            default="",
            first_match=True,
            on_error_default=True,
        )
        if value in {"true", "false"}:
            return value == "true"
    return architectural_guidelines.architectural_knowledge_required(repo_root=repo_root)


def _append_architectural_knowledge_warnings(st: DispatchState) -> None:
    for result in (
        architectural_guidelines.read_invariants(repo_root=st.repo_root),
        architectural_guidelines.read_guidelines(repo_root=st.repo_root),
    ):
        if result.status == "invalid" and result.warning:
            _append_warning(st=st, text=f"Step 2 architectural knowledge omitted: {result.warning}")


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


def _read_design_difficulty_prior(tmpdir: Path) -> str:
    prior = tmpdir / "difficulty-prior.env"
    return larch_io.read_kv(path=prior, key="DESIGN_DIFFICULTY", default="", first_match=True, on_error_default=True)


def _step2_panel_skipped(tmpdir: Path) -> str:
    requested = larch_io.read_kv(path=tmpdir / "run-flags.sh", key="SELF_REVIEW_REQUESTED", default="false", first_match=True, on_error_default=True)
    return "self-review" if requested == "true" else ""


def _model_value_safe(value: str) -> str:
    text = value.strip()
    if not text or any(ord(char) <= _ASCII_CONTROL_MAX or ord(char) == _ASCII_DELETE for char in text):
        return "unknown"
    return text


def _first_model_value(*, session_env: Path, keys: tuple[str, ...], default: str) -> str:
    for key in keys:
        if key in os.environ and os.environ[key].strip():
            return os.environ[key]
    for key in keys:
        value = _session_get(file=session_env, key=key, default="").strip()
        if value:
            return value
    return default


def _resolve_implement_rater_model(*, tool: str, session_env: Path, difficulty_tier: str = "") -> str:
    if tool == "cursor":
        value = _first_model_value(
            session_env=session_env,
            keys=(config.ENV_LARCH_CURSOR_MODEL, config.ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL),
            default=config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY.get(difficulty_tier, config.CURSOR_DEFAULT_MODEL),
        )
    elif tool == "codex":
        tier_model = config.CODEX_IMPLEMENT_MODEL_BY_DIFFICULTY.get(difficulty_tier, config.CODEX_DEFAULT_MODEL)
        value = _first_model_value(
            session_env=session_env,
            keys=(config.ENV_LARCH_CODEX_MODEL, config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL),
            default=tier_model,
        )
    else:
        value = "unknown"
    return _model_value_safe(value)


def _codex_gate_after_launch(*, st: DispatchState, launcher_capture: str) -> CodexGateDetail | None:
    if st.coder != "codex" or _manifest_complete_salvageable(st.manifest_path):
        return None
    diagnostics: list[str] = [launcher_capture]
    for path in (st.sidecar_log, st.transcript_path):
        try:
            if path.is_file():
                diagnostics.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    model = _resolve_implement_rater_model(
        tool="codex",
        session_env=st.tmpdir / "session-env.sh",
        difficulty_tier=st.difficulty,
    )
    return detect_codex_cli_gate("\n".join(diagnostics), fallback_model=model)


def _codex_gate_dispatch_result(*, st: DispatchState, detail: CodexGateDetail) -> int:
    dirty = _git_stdout(st.repo_root, "status", "--porcelain")
    current_head = _git_stdout(st.repo_root, "rev-parse", "HEAD")
    index_lock = st.repo_root / ".git" / "index.lock"
    if dirty or index_lock.exists() or current_head != st.baseline_sha:
        return st.emit_bailed(detail.message)
    _ensure_step2_baseline(st.tmpdir)
    _clear_external_scout_state(st.tmpdir)
    _emit_kv(key="STATUS", value="claude_fallback")
    _emit_kv(key="REASON", value=detail.message)
    _emit_kv(key="TOOL", value=st.tool_tag)
    _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
    return 0


def _write_step2_difficulty_record(*, st: DispatchState, manifest: dict[str, object], changed_paths: set[str] | None) -> None:
    rating = manifest.get("difficulty")
    if not isinstance(rating, dict):
        return
    raw = st.tmpdir / "implement-difficulty-rating.raw.json"
    paths = st.tmpdir / "difficulty-changed-paths.txt"
    out = st.tmpdir / difficulty.DIFFICULTY_RECORD_BASENAME
    _write_text_atomic(path=raw, text=json.dumps(rating, separators=(",", ":")) + "\n")
    if changed_paths is not None:
        _write_text_atomic(path=paths, text="".join(f"{path}\n" for path in sorted(changed_paths)))
    args = [
        "difficulty",
        "write-record",
        "--output",
        str(out),
        "--rater",
        "implement",
        "--rater-tool",
        st.tool_tag,
        "--rater-model",
        _resolve_implement_rater_model(tool=st.tool_tag, session_env=st.tmpdir / "session-env.sh", difficulty_tier=st.difficulty),
        "--raw-rating-file",
        str(raw),
        "--implement-raw-rating-file",
        str(raw),
        "--fallback-tier",
        "MODERATE",
        "--fallback-rationale",
        "dispatcher fallback rating",
    ]
    prior = _read_design_difficulty_prior(st.tmpdir)
    if difficulty.tier_valid(prior):
        args.extend(["--design-tier", prior])
    if paths.is_file():
        args.extend(["--changed-paths-file", str(paths)])
    skipped = _step2_panel_skipped(st.tmpdir)
    if skipped:
        args.extend(["--panel-skipped", skipped])
    result = _invoke_cli(args, cwd=st.repo_root)
    if result.returncode == 0 and out.is_file():
        _invoke_cli([
            "run-log",
            "write",
            "--log-root",
            str(st.tmpdir / "larch-logs"),
            "--skill",
            "implement",
            "--run-id",
            larch_io.read_kv(path=st.tmpdir / "parent-issue.md", key="RUN_ID", default="", first_match=True, on_error_default=True),
            "--batch",
            "difficulty-rating",
            "--input-file",
            str(out),
        ], cwd=st.repo_root)


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


def _ensure_step2_baseline(tmpdir: Path) -> None:
    baseline_file = tmpdir / "step2-baseline.txt"
    if baseline_file.is_file():
        return
    head = _run([GIT_BIN, "rev-parse", "HEAD"])
    if head.returncode == 0 and head.stdout.strip():
        _write_text_atomic(path=baseline_file, text=head.stdout.strip() + "\n")


def _prior_attempt_unfinalized(st: DispatchState) -> bool:
    """Detect edits from an interrupted external dispatch before re-baselining.

    A normal Q/A redispatch shares the original prelaunch snapshot.  Only a
    content delta relative to that snapshot is unsafe: it could be an external
    implementer's stranded changes, so a second launch must not claim it as
    pre-existing work.
    """
    if st.answers_file is not None or not st.prelaunch_porcelain.is_file() or not st.prelaunch_digests.is_file():
        return False
    if dispatch_helpers._capture_postlaunch_porcelain(  # noqa: SLF001 - shared dispatcher recovery snapshot helper
        repo_root=st.repo_root, implement_tmpdir=st.tmpdir
    ) != 0:
        return True
    try:
        return compute_recovery_paths(
            repo_root=st.repo_root,
            tmpdir=st.tmpdir,
            porcelain=RecoveryPorcelainInputs(
                prelaunch_porcelain=st.prelaunch_porcelain,
                postlaunch_porcelain=st.postlaunch_porcelain,
                prelaunch_digests=st.prelaunch_digests,
            ),
            out_file=st.recovery_paths_file,
        )
    except (OSError, ValueError):
        return True


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
    parser.add_argument("--completion-retry", action="store_true")
    parser.add_argument("--difficulty", choices=("", *config.DIFFICULTY_TIERS), default="")
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
    tmpdir_value = str(args.tmpdir) or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    tmpdir_raw = Path(tmpdir_value)
    if not tmpdir_raw.is_dir():
        _err(f"implement step2-dispatch: --tmpdir not a directory: {tmpdir_raw}")
        return 2
    tmpdir = tmpdir_raw.resolve()
    if not args.difficulty:
        args.difficulty = difficulty.resolve_step2_effective_difficulty(tmpdir)
    os.environ[config.ENV_IMPLEMENT_TMPDIR] = str(tmpdir)
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
    repo_result = repo_root_probe(run=_run)
    repo_root: Path | None = None
    if repo_result.returncode == 0 and repo_result.stdout.strip():
        repo_root = Path(repo_result.stdout.strip()).resolve()
        larch_io.trusted_atomic_write(
            tmpdir / "repo-root.txt", str(repo_root) + "\n", root=tmpdir
        )
    if args.coder == "claude":
        _ensure_step2_baseline(tmpdir)
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
        _ensure_step2_baseline(tmpdir)
        _clear_external_scout_state(tmpdir)
        _emit_kv(key="STATUS", value="claude_fallback")
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
        return 0
    if args.coder == "codex" and args.codex_binary_found != "true":
        _ensure_step2_baseline(tmpdir)
        _clear_external_scout_state(tmpdir)
        _emit_kv(key="STATUS", value="claude_fallback")
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
        return 0

    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("LARCH_CLAUDE_PLUGIN_ROOT") or _PLUGIN_ROOT).resolve()
    if repo_root is None:
        _err("implement step2-dispatch: must be invoked from within a git working tree (git rev-parse --show-toplevel failed)")
        return 2
    st = _dispatch_state(args=args, repo_root=repo_root, tmpdir=tmpdir, plugin_root=plugin_root)
    completion_retry_state = _completion_retry_state(st)
    if completion_retry_state is None:
        return st.emit_bailed(_COMPLETION_RETRY_STATE_INVALID)
    completion_retry_count, completion_retry_fingerprint = completion_retry_state
    if args.completion_retry:
        if not completion_retry_count or not st.completion_retry_feedback_file.is_file():
            return st.emit_bailed(_COMPLETION_RETRY_STATE_INVALID)
        try:
            retry_coverage = scope_disposition.compute_coverage(
                tmpdir=st.tmpdir,
                repo_root=st.repo_root,
                plan_file=st.plan_file,
                manifest_path=st.manifest_path,
            )
        except ShipError:
            return st.emit_bailed(_COMPLETION_RETRY_STATE_STALE)
        if retry_coverage.fingerprint != completion_retry_fingerprint:
            return st.emit_bailed(_COMPLETION_RETRY_STATE_STALE)
    _append_architectural_knowledge_warnings(st)
    prompt_path = _external_implementer_prompt_path(plugin_root=plugin_root, tool_tag=st.tool_tag)
    if not prompt_path.is_file():
        _err(f"implement step2-dispatch: external implementer prompt missing: {prompt_path}")
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

    if not args.completion_retry and _prior_attempt_unfinalized(st):
        return st.emit_bailed(_PRIOR_ATTEMPT_REASON)

    for path in (st.manifest_path, st.manifest_raw_path, st.qa_pending_path, st.transcript_path, st.sidecar_log, st.launch_scout_manifest):
        with contextlib.suppress(OSError):
            path.unlink()
    _clear_external_scout_state(tmpdir)
    issue_number = _session_get(file=session_env, key="ISSUE_NUMBER", default="") if session_env.is_file() else ""
    if not issue_number:
        issue_number = issue_from_parent
    repo_slug = _session_get(file=session_env, key="REPO", default="") if session_env.is_file() else ""
    if issue_number and repo_slug:
        try:
            body = migration_governance.read_issue_body(
                proc, issue=issue_number, repo=repo_slug, cwd=str(repo_root)
            )
            gate = migration_governance.evaluate_governance_gate(
                proc,
                issue=issue_number,
                repo=repo_slug,
                body=body,
                repo_root=repo_root,
                cwd=str(repo_root),
            )
        except ShipError as exc:
            _err(f"implement step2-dispatch: migration governance read failed: {exc}")
            return st.emit_bailed("migration-governance-read-failed")
        if not gate.ok:
            _err(migration_governance.format_gate_refusal(site="implement step2-dispatch", verdict=gate))
            return st.emit_bailed("migration-governance-stale")
    _write_prelaunch_baseline(st)

    wrapper_rc, kv, launcher_capture = _run_launcher(st)
    if wrapper_rc == WRAPPER_VALIDATION_RC:
        return st.emit_bailed("wrapper-validation-failure")
    launcher_exit = kv.get("LAUNCHER_EXIT", "99")
    manifest_written = kv.get("MANIFEST_WRITTEN", "false")
    launcher_status = kv.get("STATUS", "")
    if launcher_status == "cap_hit":
        return st.emit_bailed("cap_hit")
    gate_detail = _codex_gate_after_launch(st=st, launcher_capture=launcher_capture)
    if gate_detail is not None and not _manifest_complete_salvageable(st.manifest_path):
        return _codex_gate_dispatch_result(st=st, detail=gate_detail)
    if (wrapper_rc != 0 or manifest_written != "true" or launcher_exit != "0") and manifest_written != "true":
        dirty = _git_stdout(repo_root, "status", "--porcelain")
        index_lock = repo_root / ".git" / "index.lock"
        current_head = _git_stdout(repo_root, "rev-parse", "HEAD")
        if dirty or index_lock.exists() or current_head != st.baseline_sha:
            return st.emit_bailed("dirty-state-after-timeout")
        wrapper_rc, kv, launcher_capture = _run_launcher(st)
        if wrapper_rc == WRAPPER_VALIDATION_RC:
            return st.emit_bailed("wrapper-validation-failure")
        launcher_exit = kv.get("LAUNCHER_EXIT", "99")
        manifest_written = kv.get("MANIFEST_WRITTEN", "false")
        launcher_status = kv.get("STATUS", "")
        if launcher_status == "cap_hit":
            return st.emit_bailed("cap_hit")
        gate_detail = _codex_gate_after_launch(st=st, launcher_capture=launcher_capture)
        if gate_detail is not None:
            return _codex_gate_dispatch_result(st=st, detail=gate_detail)
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
    raw_is_dict = isinstance(raw_obj, dict)
    if status in {"complete", "needs_qa"} and raw_is_dict and _snapshot_architectural_knowledge_required(tmpdir, repo_root) and not _require_architectural_acknowledgment(raw_obj):
        return st.emit_bailed("architectural-acknowledgment-missing")
    schema_version = raw_obj.get("schema_version", "") if isinstance(raw_obj, dict) else ""
    if schema_version and str(schema_version) != "1":
        return st.emit_bailed("manifest-schema-invalid")
    if str(schema_version) != "1":
        return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj)
    if status not in {"complete", "needs_qa", "bailed"}:
        return _emit_manifest_invalid_or_recover(st=st, status=status, raw_obj=raw_obj)
    assert raw_is_dict
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

    plan_coverage: scope_disposition.PlanCoverage | None = None
    uncovered_plan_path_count = 0
    if status == "complete":
        invalid = _validate_manifest_paths(st=st, obj=raw_obj)
        if invalid:
            return st.emit_bailed(invalid)
        touched, touch_probe_failures = _working_tree_touched_paths_and_failures(repo_root)
        if touched is None:
            _append_warning(st=st, text="Step 7a.1 — plan coverage compute failed closed because git probe(s) failed: " + ", ".join(touch_probe_failures))
            return st.emit_bailed("plan-coverage-compute-failed")
        # Diagnostic-only undeclared path warning.
        declared = {item.get("path") for item in raw_obj.get("files_touched", []) if isinstance(item, dict)} | {p for p in raw_obj.get("tests_added_or_modified", []) if isinstance(p, str)}
        missing = sorted(p for p in touched if p and p not in declared)
        if missing:
            _append_warning(st=st, text=f"- **Step 7a.1 — {len(missing)} working-tree path(s) not declared in manifest files_touched/tests_added_or_modified (may include pre-existing dirty files). First 5**: " + ", ".join(missing[:5]))
        _write_step2_difficulty_record(st=st, manifest=raw_obj, changed_paths=touched)
        try:
            plan_coverage = scope_disposition.compute_and_write_coverage(
                tmpdir=st.tmpdir,
                repo_root=st.repo_root,
                plan_file=st.plan_file,
                manifest_path=st.manifest_path,
            )
        except ShipError as exc:
            _append_warning(st=st, text=f"Step 7a.1 — plan coverage compute failed closed: {exc}")
            return st.emit_bailed("plan-coverage-compute-failed")
        if plan_coverage.disposition_required and (
            is_quota_failure(tool=st.coder, sidecar=st.sidecar_log)
            or is_quota_failure(tool=st.coder, sidecar=st.transcript_path)
        ):
            return st.emit_bailed("quota")
        if plan_coverage.disposition_required:
            retry_result = _retry_incomplete_completion(args=args, st=st, coverage=plan_coverage)
            if retry_result is not None:
                return retry_result
        uncovered = list(plan_coverage.untouched_paths)
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
        commit_args = [GIT_BIN, "-C", str(repo_root), "commit", "-F", str(commit_msg_file)]
        commit = subprocess.run(
            commit_args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
        )
        if commit.returncode != 0:
            retry_add = subprocess.run(  # lint-subprocess-via-runner: ok retry of the baselined dispatcher git add-A; same DEVNULL/PIPE split as the initial add
                [GIT_BIN, "-C", str(repo_root), "add", "-A"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
            )
            if retry_add.returncode != 0:
                commit_stderr.write_text(retry_add.stderr or "git add failed", encoding="utf-8", errors="replace")
                with contextlib.suppress(OSError):
                    st.manifest_path.unlink()
                with contextlib.suppress(OSError):
                    st.manifest_raw_path.unlink()
                return st.emit_bailed("commit-failed")
            commit = subprocess.run(  # lint-subprocess-via-runner: ok retry of the baselined dispatcher git commit; same DEVNULL/PIPE split as the initial commit
                commit_args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
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
        if plan_coverage is not None:
            _emit_kv(key="PLAN_COVERAGE_TOTAL", value=plan_coverage.total)
            _emit_kv(key="PLAN_COVERAGE_TOUCHED", value=plan_coverage.touched)
            _emit_kv(key="PLAN_COVERAGE_UNTOUCHED", value=plan_coverage.untouched)
            _emit_kv(key="PLAN_COVERAGE_UNTOUCHED_PERCENT", value=plan_coverage.untouched_percent)
            _emit_kv(key="PLAN_COVERAGE_BAND", value=plan_coverage.band)
            _emit_kv(key="PLAN_COVERAGE_FILE", value=plan_coverage.coverage_file)
            _emit_kv(key="PLAN_COVERAGE_UNTOUCHED_FILE", value=plan_coverage.untouched_file)
            _emit_kv(key="TODOS_LEFT_COUNT", value=plan_coverage.todos_left_count)
            _emit_kv(key="TODOS_LEFT_FILE", value=plan_coverage.todos_file)
            _emit_kv(key="PLAN_COVERAGE_DISPOSITION_REQUIRED", value=str(plan_coverage.disposition_required).lower())
            _emit_kv(key="PLAN_FIDELITY_FORCED", value=str(plan_coverage.plan_fidelity_forced).lower())
        completion_retry_state = _completion_retry_state(st)
        if completion_retry_state is None:
            return st.emit_bailed(_COMPLETION_RETRY_STATE_INVALID)
        completion_retry_count, _completion_retry_fingerprint = completion_retry_state
        if completion_retry_count:
            _emit_kv(key="CODER_COMPLETION_RETRIES", value=completion_retry_count)
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
