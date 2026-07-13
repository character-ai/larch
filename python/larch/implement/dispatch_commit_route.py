# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false, reportUnusedImport=false
"""Checks relay, commit-route core, steps 4-6 composites, step 5 review/resume."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch import io as larch_io
from larch.bgjob import adapt as bgjob_adapt
from larch.bgjob import daemon as bgjob_daemon
from larch.bgjob import model as bgjob_model
from larch.bgjob import registry as bgjob_registry
from larch.core import config
from larch.core import redact
from larch.errors import ShipError
from larch.implement import checks
from larch.implement import checks_result_identity
from larch.implement import ship
from larch.implement import scope_disposition
from larch.implement.dispatch_helpers import (
    _current_cli_path,
    _emit_kv,
    _forward_child_output_to_stderr,
    _forward_result,
    _invoke_cli,
    _read_kv_file,
    _read_session_key_default,
    _rehydrate_larch_triplet,
    _rehydrate_plugin_root,
    _run,
    _run_cli_forward,
    _tmpdir_from_env,
    _write_bytes_atomic,
    _write_text_atomic,
    GIT_BIN,
)
from larch.implement.dispatch_helpers import _resolve_repo_root as _resolve_repo_root  # noqa: PLC0414 - re-exported for test monkeypatching  # pylint: disable=useless-import-alias  # re-exported for test monkeypatching
from larch.implement.dispatch_leg import (
    _CHECKS_DEADLINE_MS,
    _COMMIT_ROUTE_DEADLINE_MS,
    _COMMIT_ROUTE_FAILURE_LOG_MAX,
    _COMMIT_ROUTE_SUCCESS_OUTCOMES,
    _STEP5_RESUME_COMMIT_RELAY_KEYS,
    _STEP5_RESUME_DEADLINE_MS,
    _run_cli_capture,
    _run_leg_with_timeout,
    _timeout_stderr,
    _timeout_stdout,
    CommitRouteOutcome,
    TIMING_LEDGER_MIN_COLUMNS,
)
from larch.implement.dispatch_helpers import _derive_pathspec_via_recovery_paths
from larch.report.progress_file import resolve_owned_run_id


_STEP5_REVIEW_STEP = "implement-step5-review"
_STEP5_RESUME_STEP = "implement-step5-resume"
_STEP6_CHECKS_STEP = "implement-step6-checks"
_CHECKS_TERMINAL_ACTIONS = frozenset({"continue", "stall", "checks-failed", "skip-to-7a"})


@dataclass(frozen=True)
class BgjobRequest:
    tmpdir: Path
    step: str
    budget_s: int
    verb: str
    public_args: tuple[str, ...]
    merge_result_env: Path
    initial_merge_rows: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class IdentityChildRequest:
    tmpdir: Path
    step: str
    merge_env: Path
    launch: checks_result_identity.ChecksInputIdentity
    worker: Callable[[], int]
    allow_post_mutation: bool


def _bgjob_result_path(*, tmpdir: Path, step: str) -> Path:
    return bgjob_model.result_env_path(tmpdir=tmpdir, step=step)


def _safe_merge_env(*, tmpdir: Path, raw: str | Path) -> Path:
    bgjob_root = bgjob_model.bgjob_dir(tmpdir)
    if Path(raw).parent.resolve() == bgjob_root.resolve():
        bgjob_root.mkdir(parents=True, exist_ok=True)
    return bgjob_model.validate_merge_result_env(path=Path(raw), tmpdir=tmpdir)


def _bgjob_spec(request: BgjobRequest) -> bgjob_model.JobSpec:
    clone_path = Path.cwd().resolve()
    run_id = resolve_owned_run_id(explicit=None, tmpdir=request.tmpdir) or bgjob_model.default_run_id(
        tmpdir=request.tmpdir,
        clone_path=clone_path,
    )
    log_dir, _, _ = bgjob_model.log_paths(
        tmpdir=request.tmpdir,
        log_dir=None,
        step=request.step,
    )
    owner_pid = os.environ.get("LARCH_CLAUDE_PID")
    owner = bgjob_daemon.owner_identity_from_env(
        str(os.getppid()) if owner_pid is None else owner_pid
    )
    command = (
        sys.executable,
        str(_current_cli_path()),
        "implement",
        request.verb,
        *request.public_args,
    )
    return bgjob_model.JobSpec(
        step=request.step,
        tmpdir=request.tmpdir,
        log_dir=log_dir,
        budget_s=request.budget_s,
        command=command,
        run_id=run_id,
        owner=owner,
        merge_result_env=_safe_merge_env(
            tmpdir=request.tmpdir,
            raw=request.merge_result_env,
        ),
        initial_merge_rows=bgjob_model.validate_initial_merge_rows(
            request.initial_merge_rows
        ),
    )


def _run_adapter(spec: bgjob_model.JobSpec, *, repo_root: Path | None = None) -> int:
    try:
        if repo_root is None:
            return bgjob_adapt.start_or_reattach(spec)
        with contextlib.chdir(repo_root):
            return bgjob_adapt.start_or_reattach(spec)
    except bgjob_adapt.AdaptError as exc:
        print(f"BGJOB_ERROR={exc.token}")
        return 2
    except (OSError, RuntimeError, ValueError):
        print("BGJOB_ERROR=invalid-input")
        return 2


def _capture_worker(worker: Callable[[], int]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        rc = worker()
    return int(rc), output.getvalue()


def _stdout_is_merge_rows(text: str) -> bool:
    for line in text.splitlines():
        if not line:
            continue
        key, separator, _value = line.partition("=")
        if not separator or re.fullmatch(r"[A-Z0-9_]+", key) is None:
            return False
    return True


def _publish_child_output(*, tmpdir: Path, merge_env: Path, text: str) -> None:
    if not _stdout_is_merge_rows(text):
        raise ValueError("child output is not a KV stream")
    safe_path = _safe_merge_env(tmpdir=tmpdir, raw=merge_env)
    larch_io.trusted_atomic_write(
        path=safe_path,
        text=text if not text or text.endswith("\n") else f"{text}\n",
        root=tmpdir,
        mode=0o600,
    )


def _unlink_safe_file(*, path: Path, root: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("unsafe result file")
    _ = bgjob_model.ensure_under(path, root, label="result file")
    with contextlib.suppress(FileNotFoundError):
        path.unlink()
    if path.exists() or path.is_symlink():
        raise OSError("result file clear failed")


def _read_result_rows(*, path: Path, tmpdir: Path) -> dict[str, str] | None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("unsafe result file")
    _ = bgjob_model.ensure_under(path, tmpdir, label="result file")
    if not path.exists():
        return None
    return larch_io.read_kvs(
        path,
        first_wins=True,
        reject_cr=True,
        reject_symlink=True,
        key_pattern=r"^[A-Z0-9_]+$",
    )


def _live_registry_entry(*, tmpdir: Path, step: str) -> bgjob_model.RegistryEntry | None:
    _path, entry = bgjob_registry.read_for(tmpdir=tmpdir, step=step)
    if entry is None:
        return None
    if bgjob_registry.daemon_liveness(entry).live or bgjob_registry.child_liveness(entry).live:
        return entry
    return None


def _checks_step_for_site(site: str) -> tuple[str, int]:
    if site == "step3":
        return "implement-step3-checks", 15600
    if site == "step5-self-review":
        return "implement-checks-step5-self-review", 14700
    if site == "step6":
        return _STEP6_CHECKS_STEP, 10800
    return f"implement-checks-{site}", 10800


def _checks_launch_identity(*, tmpdir: Path) -> checks_result_identity.ChecksInputIdentity:
    repo_root = checks_result_identity.resolve_session_repo_root(tmpdir)
    return checks_result_identity.compute_identity(repo_root=repo_root)


def _prepare_checks_rejoin(
    *,
    tmpdir: Path,
    step: str,
    merge_env: Path,
    identity: checks_result_identity.ChecksInputIdentity,
) -> None:
    result_env = _bgjob_result_path(tmpdir=tmpdir, step=step)
    live_entry = _live_registry_entry(tmpdir=tmpdir, step=step)
    if live_entry is not None:
        seed = checks_result_identity.classify_live_seed(merge_env=merge_env, live=identity)
        if seed.state != config.CHECKS_RESULT_STATE_MATCHING:
            raise ValueError(f"live checks job identity mismatch: {seed.state}")
        completed = checks_result_identity.classify_completed_result(
            result_env=result_env,
            step=step,
            live=identity,
            terminal_actions=_CHECKS_TERMINAL_ACTIONS,
        )
        if completed.state not in {
            config.CHECKS_RESULT_STATE_MATCHING,
            config.CHECKS_RESULT_STATE_ABSENT,
        }:
            _unlink_safe_file(path=result_env, root=tmpdir)
        return
    completed = checks_result_identity.classify_completed_result(
        result_env=result_env,
        step=step,
        live=identity,
        terminal_actions=_CHECKS_TERMINAL_ACTIONS,
    )
    if completed.state == config.CHECKS_RESULT_STATE_MATCHING:
        return
    if completed.state == config.CHECKS_RESULT_STATE_UNSAFE:
        raise ValueError(completed.reason)
    _unlink_safe_file(path=result_env, root=tmpdir)
    _unlink_safe_file(path=merge_env, root=tmpdir)


def _identity_from_child_args(args: argparse.Namespace) -> checks_result_identity.ChecksInputIdentity:
    if not args.repo_root or not args.launch_head or not args.launch_fp or not args.launch_schema:
        raise checks_result_identity.ChecksIdentityError("launch identity args required in child mode")
    repo_root = checks_result_identity.validate_repo_root(args.repo_root)
    return checks_result_identity.ChecksInputIdentity(
        head_sha=args.launch_head,
        tree_fingerprint=args.launch_fp,
        fingerprint_schema=args.launch_schema,
        repo_root=repo_root,
    )


def _terminal_action_in_output(text: str) -> bool:
    return any(
        line.startswith("NEXT_ACTION=")
        and line.split("=", 1)[1] in _CHECKS_TERMINAL_ACTIONS
        for line in text.splitlines()
    )


def _publish_identity_child(request: IdentityChildRequest) -> int:
    try:
        _ = checks_result_identity.validate_child_identity(
            repo_root=request.launch.repo_root,
            expected=request.launch,
        )
    except checks_result_identity.ChecksIdentityError:
        rows = checks_result_identity.integrity_failure_rows(
            step=request.step,
            reason="pre-checks-identity-mismatch",
        )
        _publish_child_output(
            tmpdir=request.tmpdir,
            merge_env=request.merge_env,
            text=larch_io.format_kvs(rows),
        )
        return 1
    rc, output = _capture_worker(request.worker)
    try:
        if request.allow_post_mutation and _terminal_action_in_output(output):
            final_identity = checks_result_identity.compute_identity(
                repo_root=request.launch.repo_root
            )
        else:
            final_identity = checks_result_identity.validate_child_identity(
                repo_root=request.launch.repo_root,
                expected=request.launch,
            )
    except checks_result_identity.ChecksIdentityError:
        rows = checks_result_identity.integrity_failure_rows(
            step=request.step,
            reason="pre-publish-identity-mismatch",
        )
        _publish_child_output(
            tmpdir=request.tmpdir,
            merge_env=request.merge_env,
            text=larch_io.format_kvs(rows),
        )
        return 1
    merged = output
    if merged and not merged.endswith("\n"):
        merged += "\n"
    merged += larch_io.format_kvs(final_identity.as_rows())
    _publish_child_output(
        tmpdir=request.tmpdir,
        merge_env=request.merge_env,
        text=merged,
    )
    sys.stdout.write(output)
    return rc



def _relay_scope_coverage(implement_tmpdir: Path) -> int:
    plan_file = implement_tmpdir / "plan.txt"
    baseline_file = implement_tmpdir / "step2-baseline.txt"
    if not plan_file.is_file() or not baseline_file.is_file():
        return 0
    repo_root_file = implement_tmpdir / "repo-root.txt"
    try:
        repo_root = Path(
            larch_io.read_trusted_text(repo_root_file, root=implement_tmpdir).strip()
        ).resolve()
    except (OSError, ValueError):
        print("scope-disposition: persisted repository root is unavailable", file=sys.stderr)
        return 2
    if not repo_root.is_dir():
        print("scope-disposition: persisted repository root is not a directory", file=sys.stderr)
        return 2
    manifest_path = implement_tmpdir / "manifest.json"
    if not manifest_path.is_file():
        codex_manifest = implement_tmpdir / "codex-step2-out" / "manifest.json"
        if codex_manifest.is_file():
            manifest_path = codex_manifest
    try:
        coverage = scope_disposition.compute_and_write_coverage(
            tmpdir=implement_tmpdir,
            repo_root=repo_root,
            manifest_path=manifest_path,
        )
    except ShipError as exc:
        print(f"scope-disposition: coverage recompute failed: {exc}", file=sys.stderr)
        return 4
    _emit_kv(key="PLAN_COVERAGE_TOTAL", value=str(coverage.total))
    _emit_kv(key="PLAN_COVERAGE_TOUCHED", value=str(coverage.touched))
    _emit_kv(key="PLAN_COVERAGE_UNTOUCHED", value=str(coverage.untouched))
    _emit_kv(key="PLAN_COVERAGE_UNTOUCHED_PERCENT", value=str(coverage.untouched_percent))
    _emit_kv(key="PLAN_COVERAGE_BAND", value=coverage.band)
    _emit_kv(key="PLAN_COVERAGE_FILE", value=coverage.coverage_file)
    _emit_kv(key="PLAN_COVERAGE_UNTOUCHED_FILE", value=coverage.untouched_file)
    _emit_kv(key="TODOS_LEFT_COUNT", value=str(coverage.todos_left_count))
    _emit_kv(key="TODOS_LEFT_FILE", value=coverage.todos_file)
    _emit_kv(key="PLAN_COVERAGE_DISPOSITION_REQUIRED", value=str(coverage.disposition_required).lower())
    _emit_kv(key="PLAN_FIDELITY_FORCED", value=str(coverage.plan_fidelity_forced).lower())
    invalidated = scope_disposition.invalidate_stale_disposition(
        tmpdir=implement_tmpdir,
        repo_root=repo_root,
        manifest_path=manifest_path,
    )
    if invalidated.reason == "scope-disposition-stale":
        _emit_kv(key="PLAN_COVERAGE_DISPOSITION_INVALIDATED", value="true")
    return 0

def _write_terminal_sentinel(*, tmpdir: Path, sentinel: str) -> None:
    path = tmpdir / sentinel
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")



def step5_canonical_result_env_state(*, tmpdir: Path) -> str:
    """Classify only the canonical Step 5 review result grammar."""
    rows = _read_result_rows(
        path=_bgjob_result_path(tmpdir=tmpdir, step=_STEP5_REVIEW_STEP),
        tmpdir=tmpdir,
    )
    if rows is None:
        return "absent"
    required = {
        "STEP5_REVIEW_STATUS",
        "STALL_TRACKING",
        "STALL_REASON",
        "ROUNDS_COMPLETED",
        "FINAL_ROUND_NUM",
        "FINAL_REVIEW_AND_FIX_STATUS",
        "CODER_STATUS",
        "FILES_CHANGED_HINT",
        "EFFECTIVE_ROUND_CAP",
    }
    status = rows.get("STEP5_REVIEW_STATUS", "")
    if rows.get("STEP") != _STEP5_REVIEW_STEP or not required.issubset(rows):
        return "stale"
    if rows.get(config.BGJOB_RC_KEY) == "0" and status == "complete":
        return "complete"
    if status == "stall":
        return "stall"
    return "stale"


def step5_resume_result_env_state(*, tmpdir: Path) -> str:
    """Classify the distinct Step 5 resume result grammar."""
    rows = _read_result_rows(
        path=_bgjob_result_path(tmpdir=tmpdir, step=_STEP5_RESUME_STEP),
        tmpdir=tmpdir,
    )
    if rows is None:
        return "absent"
    if (
        rows.get("STEP") == _STEP5_RESUME_STEP
        and rows.get(config.BGJOB_RC_KEY) == "0"
        and rows.get("STEP5_REVIEW_STATUS") in {"complete", "stall"}
    ):
        return "complete"
    return "stale"


def _prepare_step5_result(*, tmpdir: Path, step: str, state: str) -> None:
    if state == "complete":
        return
    result = _bgjob_result_path(tmpdir=tmpdir, step=step)
    if result.exists() or result.is_symlink():
        _unlink_safe_file(path=result, root=tmpdir)


def _difficulty_override(tmpdir: Path) -> str:
    value = _read_kv_file(path=tmpdir / "run-flags.sh", key="DIFFICULTY_OVERRIDE", default="")
    return value if value in {"TRIVIAL", "MODERATE", "HARD"} else ""


def _step5_review_worker(implement_tmpdir: Path) -> int:
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    _invoke_cli(["timing", "telemetry-mark", "--implement-tmpdir", str(implement_tmpdir), "--label", "Step 5 — code review"])
    dynamic_cap = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="LARCH_DYNAMIC_ARCHETYPES_MAX", default="") or os.environ.get("LARCH_DYNAMIC_ARCHETYPES_MAX", "") or "1"
    if dynamic_cap not in {"0", "1"}:
        print(f"ERROR: Step 5 banner dynamic_archetypes_cap is non-integer or out of range: {dynamic_cap}", file=sys.stderr)
        return 2
    os.environ["LARCH_DYNAMIC_ARCHETYPES_MAX"] = dynamic_cap
    print(
        f"> **🔶 /implement 5: code review: review-and-fix step5 --mode loop, fixed tier cap 2; "
        "escalated rounds skip pruning; prune-to-empty converges; no round-5 re-probe; "
        f"dynamic-archetypes cap={dynamic_cap}**",
        file=sys.stderr,
    )
    command = [
        "review-and-fix",
        "step5",
        "--implement-tmpdir",
        str(implement_tmpdir),
        "--mode",
        "loop",
        "--starting-round",
        "1",
    ]
    difficulty = _difficulty_override(implement_tmpdir)
    if difficulty:
        command.extend(("--difficulty", difficulty))
    return _run_cli_forward(command)


def step5_review_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-5-review")
    parser.add_argument("--bgjob-child", action="store_true")
    parser.add_argument("--merge-result-env", default="")
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    if args.bgjob_child:
        if not args.merge_result_env:
            print("step-5-review: --merge-result-env is required in child mode", file=sys.stderr)
            return 2
        rc, output = _capture_worker(lambda: _step5_review_worker(implement_tmpdir))
        try:
            _publish_child_output(
                tmpdir=implement_tmpdir,
                merge_env=_safe_merge_env(tmpdir=implement_tmpdir, raw=args.merge_result_env),
                text=output,
            )
        except (OSError, UnicodeError, ValueError):
            return 2
        sys.stdout.write(output)
        return rc
    try:
        state = step5_canonical_result_env_state(tmpdir=implement_tmpdir)
        _prepare_step5_result(tmpdir=implement_tmpdir, step=_STEP5_REVIEW_STEP, state=state)
        merge_env = _safe_merge_env(
            tmpdir=implement_tmpdir,
            raw=implement_tmpdir / ".step5-review-result.env",
        )
        spec = _bgjob_spec(
            BgjobRequest(
                tmpdir=implement_tmpdir,
                step=_STEP5_REVIEW_STEP,
                budget_s=21600,
                verb="step-5-review",
                public_args=(),
                merge_result_env=merge_env,
            )
        )
    except (OSError, RuntimeError, UnicodeError, ValueError):
        print("BGJOB_ERROR=invalid-input")
        return 2
    return _run_adapter(spec)


def _step5_round_timing_row_exists(cols: list[str], *, round_decimal: str, start_s: str) -> bool:
    return (
        len(cols) >= TIMING_LEDGER_MIN_COLUMNS
        and cols[1] == "round"
        and cols[3] == "implement"
        and cols[4] == "Step 5: code review"
        and cols[5] == round_decimal
        and cols[6] == start_s
    )


def _parse_whitespace_kv_line(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for token in line.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key and re.fullmatch(r"[A-Z0-9_]+", key):
            values.setdefault(key, value)
    return values


def _checks_relay_line(captured: dict[str, str]) -> str:
    if captured.get("RELEVANT_CHECKS_SKIPPED") == "true":
        return f"RELEVANT_CHECKS_SKIPPED=true SITE={captured.get('SITE', '')}"
    if captured.get("RELEVANT_CHECKS_OK") == "true":
        line = (
            f"RELEVANT_CHECKS_OK=true SITE={captured.get('SITE', '')} "
            f"COVERAGE={captured.get('COVERAGE', '')} PHASE={captured.get('PHASE', '')}"
        )
        if captured.get("WARN"):
            line += f" WARN={captured['WARN']}"
        return line
    parts = ["STATUS=fail", f"FAILURE_REASON={captured.get('FAILURE_REASON', 'checks-failed')}"]
    parts.extend(f"{key}={captured[key]}" for key in ("EXIT_CODE", "PHASE", "DIGEST_FILE", "REDACTED_LOG_FILE") if captured.get(key))
    return " ".join(parts)


def _relay_checks_stdout(captured: dict[str, str]) -> None:
    print(_checks_relay_line(captured))


def _checks_pass(captured: dict[str, str]) -> bool:
    if captured.get("STATUS") == "fail":
        return False
    return captured.get("RELEVANT_CHECKS_OK") == "true" or captured.get("RELEVANT_CHECKS_SKIPPED") == "true"


def _session_validated_repo_root(implement_tmpdir: Path) -> Path:
    """Resolve persisted session REPO_ROOT; fail closed when absent or invalid."""
    from larch.implement.checks_result_identity import (  # noqa: PLC0415 - deferred import, only the session repo-root resolution path needs checks_result_identity
        ChecksIdentityError,
        resolve_session_repo_root,
    )

    try:
        return resolve_session_repo_root(implement_tmpdir)
    except ChecksIdentityError as exc:
        raise ShipError(f"checks-commit-route: {exc}") from exc


def _run_relevant_checks_for_site(
    *,
    implement_tmpdir: Path,
    checks_site: str,
    deadline_ms: int,
    repo_root: Path | None = None,
) -> tuple[dict[str, str], bool]:
    root = repo_root if repo_root is not None else _session_validated_repo_root(implement_tmpdir)
    env = {
        **os.environ,
        "IMPLEMENT_TMPDIR": str(implement_tmpdir),
        "CLAUDE_PROJECT_DIR": str(root),
        "REPO_ROOT": str(root),
    }
    result = _run_leg_with_timeout(
        argv=[
            "checks",
            "run-relevant",
            "--site",
            checks_site,
            "--tmpdir",
            str(implement_tmpdir),
            "--repo-root",
            str(root),
        ],
        deadline_ms=deadline_ms,
        label=f"{checks.checks_run_relevant_main.__name__}:{checks_site}",
        cwd=root,
        env=env,
    )
    if isinstance(result, subprocess.TimeoutExpired):
        return {
            "STATUS": "fail",
            "FAILURE_REASON": "checks-leg-timeout",
        }, True
    first_line = result.stdout.splitlines()[0] if result.stdout.splitlines() else ""
    captured = _parse_whitespace_kv_line(first_line)
    if not captured:
        captured = {
            "STATUS": "fail",
            "FAILURE_REASON": "checks-child-failed",
            "EXIT_CODE": str(result.returncode or 1),
        }
    elif result.returncode != 0:
        captured.pop("RELEVANT_CHECKS_OK", None)
        captured.pop("RELEVANT_CHECKS_SKIPPED", None)
        captured.setdefault("STATUS", "fail")
        captured.setdefault("FAILURE_REASON", "checks-child-failed")
        captured.setdefault("EXIT_CODE", str(result.returncode))
    return captured, False


@dataclass(frozen=True)
class CommitRouteSite:
    stall_step: str
    bail_reason: str
    failure_log_label: str
    porcelain_probe: bool


@dataclass(frozen=True)
class CommitRouteFailure:
    site_name: str
    site: CommitRouteSite
    exit_code: int
    reason: str
    stdout: str
    stderr: str = ""


@dataclass(frozen=True)
class Step4CommitSeed:
    message: str
    pathspec: Path | None
    noop_reason: str = ""


_COMMIT_ROUTE_SITES: dict[str, CommitRouteSite] = {
    "step5-self-review": CommitRouteSite(
        stall_step="5",
        bail_reason="review-fix-commit-failed",
        failure_log_label="Step 5: self-review commit failed",
        porcelain_probe=False,
    ),
    "step5-resume-handoff": CommitRouteSite(
        stall_step="5",
        bail_reason="resume-handoff-commit-failed",
        failure_log_label="Step 5: resume handoff commit failed",
        porcelain_probe=True,
    ),
    "step7": CommitRouteSite(
        stall_step="7",
        bail_reason="review-fix-commit-failed",
        failure_log_label="Step 7: review-fix commit failed",
        porcelain_probe=False,
    ),
}


def _parse_line_anchored_commit_kv(stdout: str, *, key: str) -> list[str]:
    prefix = f"{key}="
    return [line.removeprefix(prefix) for line in stdout.splitlines() if line.startswith(prefix)]


def _relay_commit_kvs(commit_output: str, *, include_next_action: bool = True) -> None:
    allowed = set(_STEP5_RESUME_COMMIT_RELAY_KEYS)
    if not include_next_action:
        allowed.discard("NEXT_ACTION")
    for line in commit_output.splitlines():
        if line.split("=", 1)[0] in allowed:
            print(line)


def _step5_resume_relay_commit_kvs(commit_output: str) -> None:
    _relay_commit_kvs(commit_output)


def _commit_route_failure_log_path(implement_tmpdir: Path, *, site: str) -> Path:
    safe_site = re.sub(r"[^A-Za-z0-9_.-]+", "-", site).strip("-") or "unknown"
    return implement_tmpdir / f"commit-route-{safe_site}.failure.log"


def _write_commit_route_failure_log(
    implement_tmpdir: Path,
    *,
    failure: CommitRouteFailure,
) -> Path:
    path = _commit_route_failure_log_path(implement_tmpdir, site=failure.site_name)
    text = (
        f"{failure.site.failure_log_label}\n"
        f"site={failure.site_name}\n"
        f"exit_code={failure.exit_code}\n"
        f"reason={failure.reason}\n"
        "\n"
        "stdout:\n"
        f"{failure.stdout}\n"
        "\n"
        "stderr:\n"
        f"{failure.stderr}\n"
    )
    if len(text) > _COMMIT_ROUTE_FAILURE_LOG_MAX:
        text = text[:_COMMIT_ROUTE_FAILURE_LOG_MAX] + "\n[truncated]\n"
    _write_text_atomic(path=path, text=text)
    return path


def _commit_route_log_failure(
    implement_tmpdir: Path,
    *,
    site_name: str,
    site: CommitRouteSite,
    exit_code: int,
    output_file: Path,
) -> None:
    # #7074: the append-failure emitter renders "**Step <site>: ...**", so passing
    # the machine key "step7" produced the doubled "Step step7". Strip the leading
    # "step" from these commit-route site keys (step7 -> 7, step5-self-review ->
    # 5-self-review) so the rendered bullet reads "Step 7:", not "Step step7:".
    display_site = site_name.removeprefix("step") or site_name
    result = _invoke_cli(
        [
            "run-log",
            "append-failure",
            "--log",
            str(implement_tmpdir / "execution-issues.md"),
            "--site",
            display_site,
            "--tool",
            "python/cli.py review-and-fix commit-fixes --stage-all",
            "--exit-code",
            str(exit_code),
            "--category",
            "Tool Failures",
            "--output-file",
            str(output_file),
            "--redact",
        ]
    )
    if result.returncode != 0:
        print(
            f"commit-route: failed to append redacted failure log for {site.failure_log_label}",
            file=sys.stderr,
        )
        _forward_child_output_to_stderr(result)


def _seed_durable_stall_state(
    implement_tmpdir: Path,
    *,
    stall_step: str,
    bail_reason: str,
) -> bool:
    state_file = implement_tmpdir / "ship-pr-state.sh"
    try:
        if state_file.is_symlink():
            print(f"commit-route: refusing symlinked ship state: {state_file}", file=sys.stderr)
            return False
        if state_file.is_file():
            text = state_file.read_text(encoding="utf-8", errors="replace")
            has_kv = re.search(r"^[A-Za-z_][A-Za-z0-9_]*=", text, re.MULTILINE) is not None
            if has_kv:
                ship._patch_ship_state_keys(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    state_file=state_file,
                    patch={
                        "STALL_TRACKING": "true",
                        "STALL_STEP": stall_step,
                        "BAIL_REASON": bail_reason,
                    },
                )
                return True
            if text.strip():
                print(f"commit-route: refusing malformed ship state: {state_file}", file=sys.stderr)
                return False
        result = _run_cli_capture(
            [
                "implement",
                "step-8-seed-initial",
                "--stall-tracking",
                "true",
                "--stall-step",
                stall_step,
                "--bail-reason",
                bail_reason,
            ]
        )
        _forward_child_output_to_stderr(result)
        return result.returncode == 0
    except Exception as exc:
        print(f"commit-route: durable stall seed failed: {exc}", file=sys.stderr)
        return False


def _commit_route_porcelain_gate() -> tuple[bool, str, str]:
    result = _run([GIT_BIN, "status", "--porcelain"])
    if result.returncode != 0:
        detail = result.stderr or result.stdout or "git status probe failed"
        return False, "git status probe failed", detail
    if result.stdout.strip():
        return False, "dirty tree after review fix commit", result.stdout
    return True, "", ""


def _commit_route_stall(
    implement_tmpdir: Path,
    *,
    failure: CommitRouteFailure,
    emit_next_action: bool = True,
) -> int | CommitRouteOutcome:
    failure_log = _write_commit_route_failure_log(
        implement_tmpdir,
        failure=failure,
    )
    _commit_route_log_failure(
        implement_tmpdir,
        site_name=failure.site_name,
        site=failure.site,
        exit_code=failure.exit_code,
        output_file=failure_log,
    )
    seeded = _seed_durable_stall_state(
        implement_tmpdir,
        stall_step=failure.site.stall_step,
        bail_reason=failure.site.bail_reason,
    )
    if not seeded:
        if not emit_next_action:
            _emit_kv(key="COMMIT_ROUTE_OUTCOME", value="seed-failed")
            _relay_commit_kvs(failure.stdout, include_next_action=False)
            return "seed-failed"
        return 1
    if not emit_next_action:
        _emit_kv(key="COMMIT_ROUTE_OUTCOME", value="seeded-stall")
        _relay_commit_kvs(failure.stdout, include_next_action=False)
        return "seeded-stall"
    _relay_commit_kvs(failure.stdout, include_next_action=False)
    _emit_kv(key="NEXT_ACTION", value="stall")
    return 0


def _commit_route_run(
    *,
    site_name: str,
    implement_tmpdir: Path,
    emit_next_action: bool = True,
) -> int | CommitRouteOutcome:
    site = _COMMIT_ROUTE_SITES[site_name]
    commit_result = _invoke_cli(["review-and-fix", "commit-fixes", "--stage-all"])
    commit_output = commit_result.stdout
    outcomes = _parse_line_anchored_commit_kv(commit_output, key="COMMIT_OUTCOME")
    if len(outcomes) != 1:
        return _commit_route_stall(
            implement_tmpdir,
            failure=CommitRouteFailure(
                site_name=site_name,
                site=site,
                exit_code=commit_result.returncode or 1,
                reason="missing or malformed COMMIT_OUTCOME",
                stdout=commit_output,
                stderr=commit_result.stderr,
            ),
            emit_next_action=emit_next_action,
        )
    outcome = outcomes[0]
    if outcome not in _COMMIT_ROUTE_SUCCESS_OUTCOMES:
        return _commit_route_stall(
            implement_tmpdir,
            failure=CommitRouteFailure(
                site_name=site_name,
                site=site,
                exit_code=commit_result.returncode or 1,
                reason=f"COMMIT_OUTCOME={outcome}",
                stdout=commit_output,
                stderr=commit_result.stderr,
            ),
            emit_next_action=emit_next_action,
        )
    if site.porcelain_probe:
        ok, reason, detail = _commit_route_porcelain_gate()
        if not ok:
            return _commit_route_stall(
                implement_tmpdir,
                failure=CommitRouteFailure(
                    site_name=site_name,
                    site=site,
                    exit_code=1,
                    reason=reason,
                    stdout=commit_output,
                    stderr=detail,
                ),
                emit_next_action=emit_next_action,
            )
    coverage_rc = _relay_scope_coverage(implement_tmpdir)
    if coverage_rc != 0:
        return coverage_rc if emit_next_action else "seed-failed"
    if not emit_next_action:
        _emit_kv(key="COMMIT_ROUTE_OUTCOME", value="continue")
        _relay_commit_kvs(commit_output, include_next_action=False)
        return "continue"
    _relay_commit_kvs(commit_output, include_next_action=False)
    _emit_kv(key="NEXT_ACTION", value="continue")
    return 0


def commit_route_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement commit-route")
    parser.add_argument("--site", choices=sorted(_COMMIT_ROUTE_SITES), required=True)
    parser.add_argument("--implement-tmpdir", default="")
    parser.add_argument("--emit-next-action", choices=("true", "false"), default="true")
    args = parser.parse_args(argv)
    raw_tmpdir = args.implement_tmpdir or os.environ.get("IMPLEMENT_TMPDIR", "")
    if not raw_tmpdir:
        print("IMPLEMENT_TMPDIR required", file=sys.stderr)
        return 2
    implement_tmpdir = Path(raw_tmpdir)
    if not implement_tmpdir.is_dir():
        print(f"commit-route: implement tmpdir not found: {implement_tmpdir}", file=sys.stderr)
        return 2
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    result = _commit_route_run(
        site_name=args.site,
        implement_tmpdir=implement_tmpdir,
        emit_next_action=args.emit_next_action == "true",
    )
    if isinstance(result, int):
        return result
    return 0 if result in {"continue", "seeded-stall"} else 1


def _run_commit_route_leg(
    *,
    site_name: str,
    implement_tmpdir: Path,
    deadline_ms: int,
) -> tuple[CommitRouteOutcome, str]:
    result = _run_leg_with_timeout(
        argv=[
            "implement",
            "commit-route",
            "--site",
            site_name,
            "--implement-tmpdir",
            str(implement_tmpdir),
            "--emit-next-action",
            "false",
        ],
        deadline_ms=deadline_ms,
        label=f"commit-route:{site_name}",
    )
    site = _COMMIT_ROUTE_SITES[site_name]
    if isinstance(result, subprocess.TimeoutExpired):
        stdout = _timeout_stdout(result)
        failure = CommitRouteFailure(
            site_name=site_name,
            site=site,
            exit_code=124,
            reason="commit-leg-timeout",
            stdout=stdout,
            stderr=_timeout_stderr(result),
        )
        failure_log = _write_commit_route_failure_log(implement_tmpdir, failure=failure)
        _commit_route_log_failure(
            implement_tmpdir,
            site_name=site_name,
            site=site,
            exit_code=124,
            output_file=failure_log,
        )
        seeded = _seed_durable_stall_state(
            implement_tmpdir,
            stall_step=site.stall_step,
            bail_reason=site.bail_reason,
        )
        return ("seeded-stall" if seeded else "seed-failed"), stdout
    outcomes = _parse_line_anchored_commit_kv(result.stdout, key="COMMIT_ROUTE_OUTCOME")
    if len(outcomes) != 1 or outcomes[0] not in {"continue", "seeded-stall", "seed-failed", "noop"}:
        return "seed-failed", result.stdout
    return cast("CommitRouteOutcome", outcomes[0]), result.stdout


def _run_7r_rebase_checkpoint(forked_target: str) -> int:
    result = _invoke_cli(["push", "checkpoint-probe", "7.r", "commit (review)", "--forked-target", forked_target])
    for line in result.stdout.splitlines():
        if line:
            print(line)
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    return result.returncode


_STEP4_COMMIT_SITE = CommitRouteSite(
    stall_step="4",
    bail_reason="implementation-commit-failed",
    failure_log_label="Step 4: implementation commit failed",
    porcelain_probe=False,
)


def _path_readable_nonempty(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and path.stat().st_size > 0
    except OSError:
        return False


def _read_redacted_message(path: Path) -> str:
    try:
        return redact.redact_secrets_only(path.read_text(encoding="utf-8", errors="replace")).strip()
    except OSError:
        return ""


def _read_nul_pathspec(path: Path) -> list[str]:
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    return [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p]


def _pathspec_clean_relative_to_head(pathspec_file: Path) -> bool:
    paths = _read_nul_pathspec(pathspec_file)
    if not paths:
        return False
    result = _run([GIT_BIN, "status", "--porcelain", "--", *paths])
    if result.returncode != 0:
        return False
    return not result.stdout.strip()


def _porcelain_status_paths_z(stdout: str) -> list[str]:
    items = stdout.split("\0")
    paths: list[str] = []
    idx = 0
    while idx < len(items):
        rec = items[idx]
        idx += 1
        if not rec:
            continue
        status = rec[:2]
        rel = rec[3:]
        if rel:
            paths.append(rel)
        if ("R" in status or "C" in status) and idx < len(items):
            old_rel = items[idx]
            idx += 1
            if old_rel:
                paths.append(old_rel)
    return sorted(dict.fromkeys(paths))


def _dispatcher_committed_dirty_pathspec(implement_tmpdir: Path) -> tuple[Path | None, bool]:
    result = _run([GIT_BIN, "status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if result.returncode != 0:
        return None, False
    paths = _porcelain_status_paths_z(result.stdout)
    if not paths:
        return None, True
    pathspec = implement_tmpdir / "dispatcher-committed-dirty-paths.nul"
    _write_bytes_atomic(
        path=pathspec,
        data=b"".join(path.encode("utf-8", "surrogateescape") + b"\0" for path in paths),
    )
    return pathspec, True


def _step4_noop(reason: str) -> tuple[CommitRouteOutcome, str]:
    commit_sha = ""
    commit = _run([GIT_BIN, "rev-parse", "--short", "HEAD"])
    if commit.returncode == 0 and commit.stdout.strip():
        commit_sha = commit.stdout.strip()
    print(f"⏩ 4: commit (impl) status=skip reason={reason} sha={commit_sha} elapsed=0s")
    return "noop", "COMMIT_ROUTE_OUTCOME=noop\nCOMMIT_OUTCOME=noop\n"


def _step4_commit_seed_from_files(*, message_path: Path, pathspec: Path) -> Step4CommitSeed | None:
    if not _path_readable_nonempty(message_path):
        return None
    message = _read_redacted_message(message_path)
    if not message or not _path_readable_nonempty(pathspec):
        return None
    return Step4CommitSeed(message=message, pathspec=pathspec)


def _step4_dispatcher_committed_seed(implement_tmpdir: Path) -> Step4CommitSeed | None:
    pathspec, status_ok = _dispatcher_committed_dirty_pathspec(implement_tmpdir)
    if not status_ok:
        return None
    if pathspec is None:
        return Step4CommitSeed(message="", pathspec=None, noop_reason="dispatcher-committed")
    return Step4CommitSeed(message="Apply post-dispatch checks fixes", pathspec=pathspec)


def _resolve_step4_commit_seed(*, implement_tmpdir: Path, dispatcher_commit_complete: bool) -> Step4CommitSeed | None:
    recovery_metadata = implement_tmpdir / "recovery-metadata.json"
    recovery_message = implement_tmpdir / "recovery-commit-message.txt"
    implementation_message = implement_tmpdir / "implementation-commit-message.txt"
    recovery_paths = implement_tmpdir / "step2-recovery-paths-final.nul"
    implementation_paths = implement_tmpdir / "implementation-commit-paths.nul"

    if _path_readable_nonempty(recovery_metadata):
        return _step4_commit_seed_from_files(message_path=recovery_message, pathspec=recovery_paths)
    if _path_readable_nonempty(implementation_message):
        return _step4_commit_seed_from_files(message_path=implementation_message, pathspec=implementation_paths)
    if dispatcher_commit_complete:
        return _step4_dispatcher_committed_seed(implement_tmpdir)
    return None


def _step4_commit_failure(
    implement_tmpdir: Path,
    *,
    exit_code: int,
    reason: str,
    stdout: str,
    stderr: str = "",
) -> CommitRouteOutcome:
    failure = CommitRouteFailure(
        site_name="step4",
        site=_STEP4_COMMIT_SITE,
        exit_code=exit_code,
        reason=reason,
        stdout=stdout,
        stderr=stderr,
    )
    failure_log = _write_commit_route_failure_log(implement_tmpdir, failure=failure)
    result = _invoke_cli(
        [
            "run-log",
            "append-failure",
            "--log",
            str(implement_tmpdir / "execution-issues.md"),
            "--site",
            "step4",
            "--tool",
            "python/cli.py implement commit",
            "--exit-code",
            str(exit_code),
            "--category",
            "Tool Failures",
            "--output-file",
            str(failure_log),
            "--redact",
        ]
    )
    if result.returncode != 0:
        _forward_child_output_to_stderr(result)
    seeded = _seed_durable_stall_state(
        implement_tmpdir,
        stall_step=_STEP4_COMMIT_SITE.stall_step,
        bail_reason=_STEP4_COMMIT_SITE.bail_reason,
    )
    return "seeded-stall" if seeded else "seed-failed"


def _run_step4_commit_leg(  # noqa: PLR0911,RUF100
    implement_tmpdir: Path,
    *,
    deadline_ms: int,
) -> tuple[CommitRouteOutcome, str]:
    seed_file = implement_tmpdir / "ship-seed-input.env"
    manifest_path = _read_kv_file(path=seed_file, key="MANIFEST_PATH", default="").strip()
    dispatcher_committed = _read_kv_file(path=seed_file, key="DISPATCHER_COMMITTED", default="").strip() == "true"
    dispatcher_commit_complete = bool(dispatcher_committed and manifest_path and _path_readable_nonempty(Path(manifest_path)))
    seed = _resolve_step4_commit_seed(
        implement_tmpdir=implement_tmpdir,
        dispatcher_commit_complete=dispatcher_commit_complete,
    )
    if seed is None:
        return "seed-failed", "COMMIT_ROUTE_OUTCOME=seed-failed\n"
    if seed.pathspec is None:
        return _step4_noop(seed.noop_reason)
    if _pathspec_clean_relative_to_head(seed.pathspec):
        noop_reason = "dispatcher-committed" if dispatcher_commit_complete else "already-committed"
        return _step4_noop(noop_reason)

    result = _run_leg_with_timeout(
        argv=[
            "implement",
            "commit",
            "--message",
            seed.message,
            "--pathspec-from-file",
            str(seed.pathspec),
            "--pathspec-file-nul",
        ],
        deadline_ms=deadline_ms,
        label="step4-implementation-commit",
        env={**os.environ, "IMPLEMENT_TMPDIR": str(implement_tmpdir)},
    )
    if isinstance(result, subprocess.TimeoutExpired):
        stdout = _timeout_stdout(result)
        outcome = _step4_commit_failure(
            implement_tmpdir,
            exit_code=124,
            reason="implementation-commit-timeout",
            stdout=stdout,
            stderr=_timeout_stderr(result),
        )
        return outcome, stdout

    committed = _parse_line_anchored_commit_kv(result.stdout, key="COMMITTED")
    if result.returncode == 0 and committed == ["true"]:
        return "continue", f"COMMIT_ROUTE_OUTCOME=continue\n{result.stdout}"
    outcome = _step4_commit_failure(
        implement_tmpdir,
        exit_code=result.returncode or 1,
        reason="implementation-commit-failed",
        stdout=result.stdout,
        stderr=result.stderr,
    )
    return outcome, f"COMMIT_ROUTE_OUTCOME={outcome}\n{result.stdout}"


def _run_step4_recovery_recompute(implement_tmpdir: Path, *, repo_root: Path) -> int:
    if not (implement_tmpdir / "recovery-metadata.json").is_file():
        return 0
    final_paths = implement_tmpdir / "step2-recovery-paths-final.nul"
    rc = _derive_pathspec_via_recovery_paths(
        implement_tmpdir=implement_tmpdir,
        repo_root=repo_root,
        out_file=final_paths,
    )
    if rc != 0:
        return rc
    scope = _invoke_cli(
        [
            "dirty-tree",
            "scope-check",
            "--plan-file",
            str(implement_tmpdir / "plan.txt"),
            "--paths-file",
            str(final_paths),
        ],
        cwd=repo_root,
    )
    if scope.returncode != 0:
        _forward_child_output_to_stderr(scope)
        _emit_kv(key="BAIL_REASON", value="recovery-out-of-scope")
        return scope.returncode or 1
    return 0


def _run_4r_rebase_checkpoint(forked_target: str) -> int:
    result = _invoke_cli(["push", "checkpoint-probe", "4.r", "commit (impl)", "--forked-target", forked_target])
    for line in result.stdout.splitlines():
        if line:
            print(line)
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    _emit_kv(key="NEXT_ACTION", value="continue")
    return result.returncode


def _run_step5_resume_leg(
    *,
    implement_tmpdir: Path,
    final_round_num: str,
    deadline_ms: int,
) -> tuple[int, str]:
    result = _run_leg_with_timeout(
        argv=[
            "implement",
            "step-5-resume",
            "--final-round-num",
            final_round_num,
            "--ready-to-commit",
            "--bgjob-child",
            "--merge-result-env",
            str(implement_tmpdir / "bgjob" / f"{_STEP5_RESUME_STEP}.merge.env"),
        ],
        deadline_ms=deadline_ms,
        label="step5-resume",
        env={**os.environ, "IMPLEMENT_TMPDIR": str(implement_tmpdir)},
    )
    if isinstance(result, subprocess.TimeoutExpired):
        return 124, _timeout_stdout(result)
    return result.returncode, result.stdout


def checks_commit_route_main(argv: list[str] | None = None) -> int:  # noqa: C901,PLR0911,RUF100
    parser = argparse.ArgumentParser(prog="cli.py implement checks-commit-route")
    parser.add_argument("--checks-site", required=True)
    commit_site_choices = sorted([*_COMMIT_ROUTE_SITES, "step4"])
    parser.add_argument("--commit-site", choices=commit_site_choices, required=True)
    parser.add_argument("--checks-deadline-ms", type=int, default=_CHECKS_DEADLINE_MS)
    parser.add_argument("--commit-deadline-ms", type=int, default=_COMMIT_ROUTE_DEADLINE_MS)
    parser.add_argument("--emit-step7-breadcrumb", action="store_true")
    parser.add_argument("--rebase-checkpoint-4r", action="store_true")
    parser.add_argument("--rebase-checkpoint-7r", action="store_true")
    parser.add_argument("--forked-target", choices=("true", "false"), default="false")
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    return _checks_commit_route_main_impl(args, implement_tmpdir)


def _checks_commit_route_main_impl(  # noqa: C901,PLR0911,PLR0912,RUF100
    args: argparse.Namespace, implement_tmpdir: Path
) -> int:
    try:
        repo_root = _session_validated_repo_root(implement_tmpdir)
    except ShipError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    captured, timed_out = _run_relevant_checks_for_site(
        implement_tmpdir=implement_tmpdir,
        checks_site=args.checks_site,
        deadline_ms=args.checks_deadline_ms,
        repo_root=repo_root,
    )
    _relay_checks_stdout(captured)
    if timed_out or not _checks_pass(captured):
        _emit_kv(key="NEXT_ACTION", value="checks-failed")
        return 0
    if args.emit_step7_breadcrumb:
        print("> **🔶 /implement 7: commit (review)**")
    if args.commit_site == "step4":
        recompute_rc = _run_step4_recovery_recompute(implement_tmpdir, repo_root=repo_root)
        if recompute_rc != 0:
            return recompute_rc
        outcome, commit_stdout = _run_step4_commit_leg(
            implement_tmpdir,
            deadline_ms=args.commit_deadline_ms,
        )
    else:
        outcome, commit_stdout = _run_commit_route_leg(
            site_name=args.commit_site,
            implement_tmpdir=implement_tmpdir,
            deadline_ms=args.commit_deadline_ms,
        )
    if commit_stdout:
        sys.stdout.write(commit_stdout)
        if not commit_stdout.endswith("\n"):
            sys.stdout.write("\n")
    if outcome in {"continue", "noop"}:
        coverage_rc = _relay_scope_coverage(implement_tmpdir)
        if coverage_rc != 0:
            return coverage_rc
        if args.commit_site == "step4" and args.rebase_checkpoint_4r:
            return _run_4r_rebase_checkpoint(args.forked_target)
        checkpoint_rc = 0
        if args.rebase_checkpoint_7r:
            checkpoint_rc = _run_7r_rebase_checkpoint(args.forked_target)
        _emit_kv(key="NEXT_ACTION", value="continue")
        return checkpoint_rc
    if outcome == "seeded-stall":
        _emit_kv(key="NEXT_ACTION", value="stall")
        return 0
    return 1


def checks_step5_resume_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement checks-step5-resume")
    parser.add_argument("--checks-site", required=True)
    parser.add_argument("--final-round-num", required=True)
    parser.add_argument("--checks-deadline-ms", type=int, default=_CHECKS_DEADLINE_MS)
    parser.add_argument("--resume-deadline-ms", type=int, default=_STEP5_RESUME_DEADLINE_MS)
    args = parser.parse_args(argv)
    if not args.final_round_num.isdigit():
        print("checks-step5-resume: --final-round-num must be numeric", file=sys.stderr)
        return 2
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    return _checks_step5_resume_main_impl(args, implement_tmpdir)


def _checks_step5_resume_main_impl(args: argparse.Namespace, implement_tmpdir: Path) -> int:
    try:
        repo_root = _session_validated_repo_root(implement_tmpdir)
    except ShipError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    captured, timed_out = _run_relevant_checks_for_site(
        implement_tmpdir=implement_tmpdir,
        checks_site=args.checks_site,
        deadline_ms=args.checks_deadline_ms,
        repo_root=repo_root,
    )
    _relay_checks_stdout(captured)
    if timed_out or not _checks_pass(captured):
        _emit_kv(key="NEXT_ACTION", value="checks-failed")
        return 0
    rc, resume_stdout = _run_step5_resume_leg(
        implement_tmpdir=implement_tmpdir,
        final_round_num=args.final_round_num,
        deadline_ms=args.resume_deadline_ms,
    )
    if resume_stdout:
        sys.stdout.write(resume_stdout)
        if not resume_stdout.endswith("\n"):
            sys.stdout.write("\n")
    return rc


def _step5_resume_commit_phase() -> int | None:
    """Run shared commit-route and relay its routing envelope."""
    commit_result = _invoke_cli(["implement", "commit-route", "--site", "step5-resume-handoff"])
    commit_output = commit_result.stdout
    next_actions = _parse_line_anchored_commit_kv(commit_output, key="NEXT_ACTION")
    if len(next_actions) == 1 and next_actions[0] in ("continue", "stall"):
        _emit_kv(key="NEXT_ACTION", value=next_actions[0])
        _relay_commit_kvs(commit_output, include_next_action=False)
        if next_actions[0] == "stall":
            return 0
        if commit_result.returncode != 0:
            return commit_result.returncode
        return None
    _step5_resume_relay_commit_kvs(commit_output)
    return commit_result.returncode if commit_result.returncode != 0 else 1


def _record_step5_handoff_timing(*, implement_tmpdir: Path, final_round_num: str) -> None:
    # lint-subprocess-via-runner: ok timing-mark needs custom DESIGN_TMPDIR/LARCH_TIMING_SKILL env; _invoke_cli does not support custom env
    subprocess.run([sys.executable, str(_current_cli_path()), "timing", "mark", "Step 5: review handoff"], env={**os.environ, "DESIGN_TMPDIR": "", "LARCH_TIMING_SKILL": "implement"}, check=False)
    round_start_file = implement_tmpdir / f"round-{final_round_num}" / "round-start-s"
    if round_start_file.is_file():
        start_s = round_start_file.read_text(encoding="utf-8", errors="replace").strip()
        ledger = implement_tmpdir / "timing-ledger.tsv"
        needs_record = start_s.isdigit()
        if needs_record and ledger.is_file():
            round_decimal = str(int(final_round_num))
            for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
                cols = line.split("\t")
                if _step5_round_timing_row_exists(cols, round_decimal=round_decimal, start_s=start_s):
                    needs_record = False
                    break
        if needs_record and start_s.isdigit():
            _invoke_cli(["review-and-fix", "record-round-timing", "--implement-tmpdir", str(implement_tmpdir), "--round", final_round_num, "--start-s", start_s, "--end-s", str(int(time.time()))])


def _step5_resume_worker(args: argparse.Namespace, implement_tmpdir: Path) -> int:
    _record_step5_handoff_timing(
        implement_tmpdir=implement_tmpdir,
        final_round_num=args.final_round_num,
    )
    if args.checks_site:
        return checks_step5_resume_main(
            ["--checks-site", args.checks_site, "--final-round-num", args.final_round_num]
        )
    if args.ready_to_commit or os.environ.get("STEP5_HANDOFF_READY_TO_COMMIT") == "true":
        commit_rc = _step5_resume_commit_phase()
        if commit_rc is not None:
            if commit_rc == 0:
                _emit_kv(key="STEP5_REVIEW_STATUS", value="stall")
            return commit_rc
    command = [
        "review-and-fix",
        "step5",
        "--implement-tmpdir",
        str(implement_tmpdir),
        "--mode",
        "loop",
        "--starting-round",
        str(int(args.final_round_num) + 1),
    ]
    difficulty = _difficulty_override(implement_tmpdir)
    if difficulty:
        command.extend(("--difficulty", difficulty))
    return _run_cli_forward(command)


def _step5_resume_child(args: argparse.Namespace, implement_tmpdir: Path) -> int:
    if not args.merge_result_env:
        print("step-5-resume: --merge-result-env is required in child mode", file=sys.stderr)
        return 2
    rc, output = _capture_worker(lambda: _step5_resume_worker(args, implement_tmpdir))
    try:
        _publish_child_output(
            tmpdir=implement_tmpdir,
            merge_env=_safe_merge_env(tmpdir=implement_tmpdir, raw=args.merge_result_env),
            text=output,
        )
    except (OSError, UnicodeError, ValueError):
        return 2
    sys.stdout.write(output)
    return rc


def step5_resume_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-5-resume")
    parser.add_argument("--final-round-num", required=True)
    parser.add_argument("--checks-site", default="")
    parser.add_argument("--ready-to-commit", action="store_true")
    parser.add_argument("--record-only", action="store_true")
    parser.add_argument("--bgjob-child", action="store_true")
    parser.add_argument("--merge-result-env", default="")
    args = parser.parse_args(argv)
    if not args.final_round_num.isdigit():
        print("step-5-resume: --final-round-num must be numeric", file=sys.stderr)
        return 2
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    if args.record_only:
        if args.bgjob_child:
            print("step-5-resume: --record-only cannot run in child mode", file=sys.stderr)
            return 2
        _record_step5_handoff_timing(
            implement_tmpdir=implement_tmpdir,
            final_round_num=args.final_round_num,
        )
        return 0
    if args.bgjob_child:
        return _step5_resume_child(args, implement_tmpdir)
    public_args = ["--final-round-num", args.final_round_num]
    if args.ready_to_commit:
        public_args.append("--ready-to-commit")
    if args.checks_site:
        public_args.extend(("--checks-site", args.checks_site))
    try:
        state = step5_resume_result_env_state(tmpdir=implement_tmpdir)
        _prepare_step5_result(tmpdir=implement_tmpdir, step=_STEP5_RESUME_STEP, state=state)
        merge_env = _safe_merge_env(
            tmpdir=implement_tmpdir,
            raw=implement_tmpdir / "bgjob" / f"{_STEP5_RESUME_STEP}.merge.env",
        )
        spec = _bgjob_spec(
            BgjobRequest(
                tmpdir=implement_tmpdir,
                step=_STEP5_RESUME_STEP,
                budget_s=32700,
                verb="step-5-resume",
                public_args=tuple(public_args),
                merge_result_env=merge_env,
            )
        )
    except (OSError, RuntimeError, UnicodeError, ValueError):
        print("BGJOB_ERROR=invalid-input")
        return 2
    return _run_adapter(spec)


def _run_step6_composite(*, forked_target: str) -> int:
    return checks_commit_route_main(
        [
            "--checks-site",
            "step6",
            "--commit-site",
            "step7",
            "--emit-step7-breadcrumb",
            "--rebase-checkpoint-7r",
            "--forked-target",
            forked_target,
        ]
    )


def _step6_entry_seed_stall(implement_tmpdir: Path) -> int:
    seeded = _seed_durable_stall_state(
        implement_tmpdir,
        stall_step="6",
        bail_reason=config.REVIEW_CHANGE_DETECTION_FAILED,
    )
    if not seeded:
        return 1
    _emit_kv(key="NEXT_ACTION", value="stall")
    return 0


def _step6_entry_worker(args: argparse.Namespace, implement_tmpdir: Path) -> int:
    (implement_tmpdir / ".review-boundary-passed").touch(exist_ok=True)
    if args.force_checks == "true":
        return _run_step6_composite(forked_target=args.forked_target)

    check_changes = _run_cli_capture(
        [
            "review-and-fix",
            "check-changes",
            "--baseline",
            str(implement_tmpdir / "pre-review-untracked.txt"),
            "--head-baseline",
            str(implement_tmpdir / "pre-review-head.txt"),
        ]
    )
    _forward_result(check_changes)
    files_changed_values = _parse_line_anchored_commit_kv(check_changes.stdout, key="FILES_CHANGED")
    if check_changes.returncode != 0 or len(files_changed_values) != 1 or files_changed_values[0] not in {"true", "false"}:
        return _step6_entry_seed_stall(implement_tmpdir)
    if files_changed_values[0] == "false":
        _emit_kv(key="NEXT_ACTION", value="skip-to-7a")
        return 0
    return _run_step6_composite(forked_target=args.forked_target)


def step6_entry_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-6-entry")
    parser.add_argument("--forked-target", choices=("true", "false"), default="false")
    parser.add_argument("--force-checks", choices=("true", "false"), default="false")
    parser.add_argument("--bgjob-child", action="store_true")
    parser.add_argument("--merge-result-env", default="")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--launch-head", default="")
    parser.add_argument("--launch-fp", default="")
    parser.add_argument("--launch-schema", default="")
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    if args.bgjob_child:
        try:
            merge_env = _safe_merge_env(tmpdir=implement_tmpdir, raw=args.merge_result_env)
            launch = _identity_from_child_args(args)
            _old_repo_root = os.environ.get("REPO_ROOT")
            _old_cpd = os.environ.get("CLAUDE_PROJECT_DIR")
            os.environ["REPO_ROOT"] = str(launch.repo_root)
            os.environ["CLAUDE_PROJECT_DIR"] = str(launch.repo_root)
            try:
                return _publish_identity_child(
                    IdentityChildRequest(
                        tmpdir=implement_tmpdir,
                        step=_STEP6_CHECKS_STEP,
                        merge_env=merge_env,
                        launch=launch,
                        worker=lambda: _step6_entry_worker(args, implement_tmpdir),
                        allow_post_mutation=True,
                    )
                )
            finally:
                if _old_repo_root is None:
                    os.environ.pop("REPO_ROOT", None)
                else:
                    os.environ["REPO_ROOT"] = _old_repo_root
                if _old_cpd is None:
                    os.environ.pop("CLAUDE_PROJECT_DIR", None)
                else:
                    os.environ["CLAUDE_PROJECT_DIR"] = _old_cpd
        except (OSError, RuntimeError, UnicodeError, ValueError):
            return 2
    public_args = (
        "--forked-target",
        args.forked_target,
        "--force-checks",
        args.force_checks,
    )
    try:
        identity = _checks_launch_identity(tmpdir=implement_tmpdir)
        merge_env = _safe_merge_env(
            tmpdir=implement_tmpdir,
            raw=implement_tmpdir / "bgjob" / f"{_STEP6_CHECKS_STEP}.merge.env",
        )
        _prepare_checks_rejoin(
            tmpdir=implement_tmpdir,
            step=_STEP6_CHECKS_STEP,
            merge_env=merge_env,
            identity=identity,
        )
        child_identity_args = (
            "--repo-root",
            str(identity.repo_root),
            "--launch-head",
            identity.head_sha,
            "--launch-fp",
            identity.tree_fingerprint,
            "--launch-schema",
            identity.fingerprint_schema,
        )
        spec = _bgjob_spec(
            BgjobRequest(
                tmpdir=implement_tmpdir,
                step=_STEP6_CHECKS_STEP,
                budget_s=15600,
                verb="step-6-entry",
                public_args=(*public_args, *child_identity_args),
                merge_result_env=merge_env,
                initial_merge_rows=tuple(identity.as_rows()),
            )
        )
    except (OSError, RuntimeError, UnicodeError, ValueError, checks_result_identity.ChecksIdentityError) as exc:
        print(f"step-6-entry: {exc}", file=sys.stderr)
        return 2
    return _run_adapter(spec, repo_root=identity.repo_root)


def _run_step_checks_worker(
    args: argparse.Namespace,
    implement_tmpdir: Path,
    repo_root: Path,
) -> int:
    if args.commit_site:
        command = [
            "--checks-site",
            args.site,
            "--commit-site",
            args.commit_site,
        ]
        if args.rebase_checkpoint_4r:
            command.append("--rebase-checkpoint-4r")
        command.extend(("--forked-target", args.forked_target))
        return checks_commit_route_main(command)
    command = [
        "checks",
        "run-relevant",
        "--site",
        args.site,
        "--tmpdir",
        str(implement_tmpdir),
        "--repo-root",
        str(repo_root),
    ]
    return _run_cli_forward(command, cwd=repo_root)


def run_step_checks_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement run-step-checks")
    parser.add_argument("--site", required=True)
    parser.add_argument("--commit-site", default="")
    parser.add_argument("--forked-target", choices=("true", "false"), default="false")
    parser.add_argument("--rebase-checkpoint-4r", action="store_true")
    parser.add_argument("--bgjob-child", action="store_true")
    parser.add_argument("--merge-result-env", default="")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--launch-head", default="")
    parser.add_argument("--launch-fp", default="")
    parser.add_argument("--launch-schema", default="")
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    step, budget_s = _checks_step_for_site(args.site)
    if args.bgjob_child:
        try:
            merge_env = _safe_merge_env(tmpdir=implement_tmpdir, raw=args.merge_result_env)
            launch = _identity_from_child_args(args)
            _old_repo_root = os.environ.get("REPO_ROOT")
            _old_cpd = os.environ.get("CLAUDE_PROJECT_DIR")
            os.environ["REPO_ROOT"] = str(launch.repo_root)
            os.environ["CLAUDE_PROJECT_DIR"] = str(launch.repo_root)
            try:
                return _publish_identity_child(
                    IdentityChildRequest(
                        tmpdir=implement_tmpdir,
                        step=step,
                        merge_env=merge_env,
                        launch=launch,
                        worker=lambda: _run_step_checks_worker(
                            args,
                            implement_tmpdir,
                            launch.repo_root,
                        ),
                        allow_post_mutation=bool(args.commit_site),
                    )
                )
            finally:
                if _old_repo_root is None:
                    os.environ.pop("REPO_ROOT", None)
                else:
                    os.environ["REPO_ROOT"] = _old_repo_root
                if _old_cpd is None:
                    os.environ.pop("CLAUDE_PROJECT_DIR", None)
                else:
                    os.environ["CLAUDE_PROJECT_DIR"] = _old_cpd
        except (OSError, RuntimeError, UnicodeError, ValueError):
            return 2
    try:
        identity = _checks_launch_identity(tmpdir=implement_tmpdir)
        merge_env = _safe_merge_env(
            tmpdir=implement_tmpdir,
            raw=implement_tmpdir / "bgjob" / f"{step}.merge.env",
        )
        _prepare_checks_rejoin(
            tmpdir=implement_tmpdir,
            step=step,
            merge_env=merge_env,
            identity=identity,
        )
        public_args = ["--site", args.site]
        if args.commit_site:
            public_args.extend(("--commit-site", args.commit_site))
        public_args.extend(("--forked-target", args.forked_target))
        if args.rebase_checkpoint_4r:
            public_args.append("--rebase-checkpoint-4r")
        public_args.extend(
            (
                "--repo-root",
                str(identity.repo_root),
                "--launch-head",
                identity.head_sha,
                "--launch-fp",
                identity.tree_fingerprint,
                "--launch-schema",
                identity.fingerprint_schema,
            )
        )
        spec = _bgjob_spec(
            BgjobRequest(
                tmpdir=implement_tmpdir,
                step=step,
                budget_s=budget_s,
                verb="run-step-checks",
                public_args=tuple(public_args),
                merge_result_env=merge_env,
                initial_merge_rows=tuple(identity.as_rows()),
            )
        )
    except (OSError, RuntimeError, UnicodeError, ValueError, checks_result_identity.ChecksIdentityError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return _run_adapter(spec, repo_root=identity.repo_root)

def step8_python_guard_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-8-python-guard").parse_args(argv)
    if sys.version_info >= (3, 11):  # noqa: UP036 - intentional runtime guard; this module may execute under pre-3.11 interpreters.
        return 0
    print("ERROR: Python ship driver requires Python 3.11 or newer", file=sys.stderr)
    print('{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","ledger_dispatcher":"","ledger_exit_code":null,"ledger_failure_detail_log":"","ledger_phase":"","ledger_ready":false,"ledger_site":"","ledger_step":"","ledger_trigger":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}')
    return 4
