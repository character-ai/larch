"""Wrapper-env, session helpers, pause/capture, and phase-driver result-env writers."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Sequence

from larch import io as larch_io
from larch.core.ctx import Ctx
from larch.design import design_pause
from larch.state import session_env

from larch.design.design_step0_env import _load_source_env

PHASE_RESULT_ENV_ALLOW_KEYS = {
    "ACCEPTED_COUNT",
    "AGGREGATOR_STATUS",
    "BASELINE_DIFF_LINES",
    "BASELINE_PLAN_LINES",
    "DEDUP_RC",
    "DEGRADED_PANEL",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
    "DIFF_ADDED",
    "DIFF_DELETED",
    "DIFF_LINES",
    "DRIFT_DIFF_RATIO",
    "DRIFT_MULTIPLE",
    "DRIFT_PLAN_RATIO",
    "DRIFT_TRIGGER_FIRED",
    "EMIT_PLAN_STATUS",
    "ERROR",
    "FINAL_ROUND_NUM",
    "IMPORTANT_ACCEPTED_COUNT",
    "LOOP_STATUS",
    "MECHANICAL_CHURN",
    "NEXT_ACTION",
    "OOS_SKIP_BREADCRUMB",
    "PANEL_PRUNED_EMPTY",
    "PARTITION_REQUESTED",
    "PLAN_LINES",
    "PLAN_REVIEW_CONTINUE_REASON",
    "PLAN_SIZE_STATUS",
    "POSTPLAN_EMIT_STATUS",
    "POSTPLAN_RC",
    "REASON",
    "REVIEW_ROUND_COUNT",
    "ROUND_NUM",
    "ROUNDS_COMPLETED",
    "SCOPE_ANCHOR_FILE",
    "SIZE_TRIGGER_FIRED",
    "SNAPSHOT_STATUS",
    "SETTLE_NEXT_ACTION",
    "SOFT_ADVISORY",
    "STEP3_REVIEW_LOOP_STATUS",
    "STEP3_REVIEW_CAP_REACHED",
    "STEP3_REVIEW_ROUND_NUM",
    "TALLY_PLAN_REVIEW_STATUS",
    "TRIGGER_REASONS",
    "VALIDATE_DEFECT_COUNT",
    "VALIDATE_LOG_FILE",
    "VALIDATE_MISSING_SCRIPT_COUNT",
    "VALIDATE_SKIPPED_COUNT",
    "VALIDATE_STATUS",
    "VALIDATE_UNSAFE_TOKEN_COUNT",
    "VOTING_TALLY_FILE",
    "WARN",
}


_WRAPPER_ENV_DEFAULTS: dict[str, str] = {
    "CLAUDE_PLUGIN_ROOT": "",
    "MODE": "",
    "SITE": "",
    "SUMMARY_OUTCOME": "",
    "SKIP_VALIDATE": "",
    **session_env.COMMON_DESIGN_ENV_DEFAULTS,
    "POSITIONAL_KIND": "",
    "POSITIONAL_VALUE": "",
    "partition_requested": "false",
    "brainstorm_requested": "false",
    "approve_requested": "false",
    "skip_approve_requested": "false",
    "no_dedup_requested": "false",
    "run_id": "",
    **session_env.VALIDATOR_STATUS_ENV_DEFAULTS,
    "PUBLISH_OK": "",
    "PLAN_WRITE_OK": "",
    "STANDALONE_HEAVY_FAILED": "",
    "CLEANUP_ELIGIBLE": "",
}

_SESSION_ENV_ALLOWLIST = frozenset(_WRAPPER_ENV_DEFAULTS) | {
    "LARCH_AUTO_MODE",
    "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT",
    "LARCH_TIMING_LEDGER",
    "LARCH_TOKEN_SESSION_ID",
    "LARCH_CLAUDE_SOURCE_FILE",
    "PREV_IMPLEMENT_TMPDIR",
    "LARCH_DYNAMIC_ARCHETYPES_MAX",
    "LARCH_RUN_ID",
    "LARCH_CLAUDE_PLUGIN_ROOT",
    "LARCH_DESIGN_DRAFTER",
    "LARCH_DESIGN_PLAN_MODEL",
    "LARCH_DESIGN_DRIFT_MULTIPLE",
}


# Mutable builder: the argv parser sets fields on the instance as it scans.
@dataclass
class WrapperArgs:
    session_env_path: str = ""
    claude_pid: str = ""
    plugin_root: str = ""
    mode: str = ""
    site: str = ""
    snapshot_original: bool = False
    outcome: str = ""
    skip_validate: bool = False
    write_completion_only: bool = False
    include_step2b: bool = False
    write_step2b_completion_only: bool = False
    step3_review_loop_status: str = ""
    loop_status: str = ""
    validator_target_file: str = ""
    validate_log_file: str = ""
    validate_defect_count: str = ""
    validate_unsafe_token_count: str = ""
    validate_skipped_count: str = ""
    operator_cancel: bool = False
    public_argv_words: list[str] | None = None


@dataclass(frozen=True)
class PostplanResult:
    postplan_rc: int
    stdout_lines: str
    status: str
    inline_retry_scheduled: bool = False


@dataclass(frozen=True)
class PostplanPaths:
    design_tmpdir: Path
    completed_dir: Path
    step2b5_done: Path
    step2b_done: Path
    inline_retry_done: Path
    inline_retry_pending: Path
    fallback_used: Path
    plan_source: Path
    plan_summary: Path

    @classmethod
    def from_design_tmpdir(cls, design_tmpdir: Path) -> PostplanPaths:
        root = design_tmpdir.resolve()
        completed = root / ".completed"
        return cls(
            design_tmpdir=root,
            completed_dir=completed,
            step2b5_done=completed / "step-2b.5",
            step2b_done=completed / "step-2b",
            inline_retry_done=root / ".step2b-postplan-inline-retry-done",
            inline_retry_pending=root / ".step2b-postplan-inline-retry-pending",
            fallback_used=root / ".step2b-postplan-fallback-used",
            plan_source=root / ".step2b-plan-source",
            plan_summary=root / "plan-summary.md",
        )


@dataclass(frozen=True)
class PostplanDecision:
    postplan_rc: int
    status: str
    rows: tuple[str, ...]
    touches: tuple[Path, ...]
    writes: tuple[tuple[Path, str], ...]
    unlinks: tuple[Path, ...]
    clear_scout_manifests: bool = False
    pause_save: bool = False
    fatal_stderr: str = ""
    print_captured_before_return: bool = False
    print_stdout_before_system_exit: bool = False
    inline_retry_scheduled: bool = False


def _valid_var_name(value: str) -> bool:
    if not value or value[0].isdigit():
        return False
    return all(ch.isalnum() or ch == "_" for ch in value)


def _quote_single(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _parse_common_wrapper_args(argv: Sequence[str]) -> WrapperArgs:
    args = list(argv)
    out = WrapperArgs(public_argv_words=[])
    value_flags = session_env.WRAPPER_VALUE_FLAGS
    bool_flags: dict[str, str] = {
        "--snapshot-original": "snapshot_original",
        "--skip-validate": "skip_validate",
        "--write-completion-only": "write_completion_only",
        "--include-step2b": "include_step2b",
        "--write-step2b-completion-only": "write_step2b_completion_only",
        "--operator-cancel": "operator_cancel",
    }
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--":
            out.public_argv_words = args[i + 1 :]
            break
        if token in value_flags:
            if i + 1 >= len(args):
                raise ValueError(f"{token} requires a value")
            setattr(out, value_flags[token], args[i + 1])
            i += 2
            continue
        if token in bool_flags:
            setattr(out, bool_flags[token], True)
            i += 1
            continue
        # Forward-compatible no-op parsing for retired generated wrapper args.
        # Unknown flags with a following value consume that value; bare flags are
        # ignored. Behavior-bearing flags above are bound explicitly.
        if token.startswith("--") and i + 1 < len(args) and not args[i + 1].startswith("--"):
            i += 2
        else:
            i += 1
    return out


def _parse_session_env_line(raw: str) -> tuple[str, str] | None:
    return session_env.parse_allowlisted_env_line(
        raw=raw,
        allowlist=_SESSION_ENV_ALLOWLIST,
        name_validator=_valid_var_name,
        reject_newline_rhs=True,
    )


def _load_session_env(path: str) -> dict[str, str]:
    if not path:
        return {}
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        return {}
    env: dict[str, str] = {}
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return env
    for raw in text.splitlines():
        pair = _parse_session_env_line(raw)
        if pair is not None:
            env[pair[0]] = pair[1]
    return env


def _rehydrate_wrapper_env(parsed: WrapperArgs) -> dict[str, str]:
    merged: dict[str, str] = {key: os.environ.get(key, default) for key, default in _WRAPPER_ENV_DEFAULTS.items()}
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        merged["CLAUDE_PLUGIN_ROOT"] = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    merged.update(_load_source_env(path=parsed.session_env_path, allow_keys=_SESSION_ENV_ALLOWLIST, claude_pid=parsed.claude_pid))
    if parsed.plugin_root:
        merged["CLAUDE_PLUGIN_ROOT"] = parsed.plugin_root
    if parsed.mode:
        merged["MODE"] = parsed.mode
    if parsed.site:
        merged["SITE"] = parsed.site
    if parsed.outcome:
        merged["SUMMARY_OUTCOME"] = parsed.outcome
    if parsed.skip_validate:
        merged["SKIP_VALIDATE"] = "1"
    if parsed.step3_review_loop_status:
        merged["STEP3_REVIEW_LOOP_STATUS"] = parsed.step3_review_loop_status
    if parsed.loop_status:
        merged["LOOP_STATUS"] = parsed.loop_status
    if parsed.validator_target_file:
        merged["_validator_target_file"] = parsed.validator_target_file
    if parsed.validate_log_file:
        merged["VALIDATE_LOG_FILE"] = parsed.validate_log_file
    if parsed.validate_defect_count:
        merged["VALIDATE_DEFECT_COUNT"] = parsed.validate_defect_count
    if parsed.validate_unsafe_token_count:
        merged["VALIDATE_UNSAFE_TOKEN_COUNT"] = parsed.validate_unsafe_token_count
    if parsed.validate_skipped_count:
        merged["VALIDATE_SKIPPED_COUNT"] = parsed.validate_skipped_count
    return session_env.finalize_wrapper_env(merged)


def _design_require_plugin_root() -> int:
    rc = session_env.require_plugin_root()
    if rc != 0:
        return rc
    os.environ["CLAUDE_PLUGIN_ROOT"] = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    return 0


def _design_tmpdir(ctx: Ctx | None = None) -> Path:
    return Path(ctx.design_tmpdir if ctx is not None else os.environ.get("DESIGN_TMPDIR", ""))


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _write_text(*, path: Path, text: str) -> None:
    larch_io.write_text(path=path, text=text)


def _exact_line_file(*, path: Path, expected: str) -> bool:
    try:
        return path.read_text(encoding="utf-8", errors="replace").rstrip("\n") == expected
    except OSError:
        return False


def _call_pause_save(*, design_tmpdir: Path, ctx: Ctx | None = None) -> int:
    args = ["--design-tmpdir", str(design_tmpdir), "--issue", ctx.issue_number if ctx is not None else os.environ.get("ISSUE_NUMBER", "")]
    repo = ctx.repo if ctx is not None else os.environ.get("REPO", "")
    if repo:
        args.extend(["--repo", repo])
    return design_pause.pause_save_main(args)


def _call_pause_save_captured(*, design_tmpdir: Path, ctx: Ctx | None = None) -> tuple[int, str, str]:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        rc = _call_pause_save(design_tmpdir=design_tmpdir, ctx=ctx)
    return int(rc), stdout_buf.getvalue(), stderr_buf.getvalue()


def _pause_save_stdout_ok(stdout: str) -> bool:
    return any(line == "PAUSE_OK=true" for line in stdout.splitlines())


def _print_pause_save_capture(stdout: str, stderr: str) -> None:
    _print_text(stdout)
    if stderr:
        print(stderr, end="", file=sys.stderr)


def _run_pause_save_terminal(*, design_tmpdir: Path, ctx: Ctx | None = None) -> int:
    rc, stdout, stderr = _call_pause_save_captured(design_tmpdir=design_tmpdir, ctx=ctx)
    _print_pause_save_capture(stdout, stderr)
    if not _pause_save_stdout_ok(stdout):
        return 1
    return rc


def _maybe_timing_mark(*, label: str, ctx: Ctx | None = None) -> None:
    plugin_root = ctx.claude_plugin_root if ctx is not None else os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root or plugin_root == "${CLAUDE_PLUGIN_ROOT}":
        return
    env = ctx.subprocess_env(overrides={"LARCH_TIMING_SKILL": "design"}) if ctx is not None else os.environ.copy()
    env["LARCH_TIMING_SKILL"] = "design"
    with contextlib.suppress(OSError):
        subprocess.run(
            [sys.executable, str(Path(plugin_root) / "python" / "cli.py"), "timing", "mark", label],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _capture_stdout(*, callable_obj: Callable[..., int], argv: Sequence[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = callable_obj(list(argv))
    return int(rc), buf.getvalue()


def _capture_stdout_stderr(*, callable_obj: Callable[..., int], argv: Sequence[str], stderr_path: Path) -> tuple[int, str]:
    buf = io.StringIO()
    try:
        with stderr_path.open("w", encoding="utf-8") as err, contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            try:
                rc = callable_obj(list(argv))
                return int(rc), buf.getvalue()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                return code, buf.getvalue()
            except BaseException:
                err.write(traceback.format_exc())
                return 1, buf.getvalue()
    except OSError:
        return 1, buf.getvalue()


def _print_text(text: str) -> None:
    if text:
        print(text, end="" if text.endswith("\n") else "\n")
