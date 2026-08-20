# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false, reportUnusedImport=false
"""Checks relay, commit-route core, steps 4-6 composites, step 5 review/resume."""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch import io as larch_io
from larch.bgjob import model as bgjob_model
from larch.core import proc
from larch.core import redact
from larch.core import rust_runtime
from larch.core.repo_roots import larch_entrypoint
from larch.errors import ShipError
from larch.implement import ship
from larch.implement import scope_disposition
from larch.implement.self_edit_log import file_sha256, read_self_edits
from larch.implement.dispatch_helpers import (
    _emit_kv,
    _forward_child_output_to_stderr,
    _invoke_larch,
    _read_kv_file,
    _rehydrate_larch_triplet,
    _rehydrate_plugin_root,
    _run,
    _tmpdir_from_env,
    _write_bytes_atomic,
    _write_text_atomic,
    GIT_BIN,
    porcelain_status_paths_z,
)
from larch.implement.dispatch_helpers import _resolve_repo_root as _resolve_repo_root  # noqa: PLC0414 - re-exported for test monkeypatching  # pylint: disable=useless-import-alias  # re-exported for test monkeypatching
from larch.implement.dispatch_helpers import _invoke_cli as _invoke_cli  # noqa: PLC0414 - re-exported for test monkeypatching
from larch.implement.dispatch_leg import (
    _CHECKS_DEADLINE_MS,
    _COMMIT_ROUTE_DEADLINE_MS,
    _COMMIT_ROUTE_FAILURE_LOG_MAX,
    _COMMIT_ROUTE_SUCCESS_OUTCOMES,
    _STEP5_RESUME_COMMIT_RELAY_KEYS,
    _run_leg_with_timeout,
    _timeout_stderr,
    _timeout_stdout,
    CommitRouteOutcome,
)
from larch.implement.dispatch_helpers import _derive_pathspec_via_recovery_paths
from larch.implement.dispatch_helpers import _current_cli_path
from larch.report.progress_file import resolve_owned_run_id


_STEP6_CHECKS_STEP = "implement-step6-checks"


@dataclass(frozen=True)
class BgjobRequest:
    tmpdir: Path
    step: str
    budget_s: int
    verb: str
    public_args: tuple[str, ...]
    merge_result_env: Path
    initial_merge_rows: tuple[tuple[str, str], ...] = ()


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
    owner = bgjob_model.owner_identity_from_env(
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


def _run_adapter(
    spec: bgjob_model.JobSpec,
    *,
    repo_root: Path | None = None,
    clear_on_fresh: Path | None = None,
    replace_completed_result: bool = False,
    input_fingerprint: str = "",
) -> int:
    try:
        argv = [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "bgjob",
            "adapt",
            "--step",
            spec.step,
            "--tmpdir",
            str(spec.tmpdir),
            "--run-id",
            spec.run_id,
            "--budget-s",
            str(spec.budget_s),
            "--log-dir",
            str(spec.log_dir),
        ]
        if spec.owner.recorded is not None:
            argv.extend(("--owner-pid", str(spec.owner.recorded.pid)))
        for sentinel in spec.sentinel_paths:
            argv.extend(("--sentinel", str(sentinel)))
        if spec.merge_result_env is not None:
            argv.extend(("--merge-result-env", str(spec.merge_result_env)))
        for key, value in spec.initial_merge_rows:
            argv.extend(("--initial-merge-row", f"{key}={value}"))
        if clear_on_fresh is not None:
            argv.extend(("--clear-on-fresh", str(clear_on_fresh)))
        if replace_completed_result:
            argv.append("--replace-completed-result")
        if input_fingerprint:
            argv.extend(("--input-fingerprint", input_fingerprint))
        argv.extend(("--", *spec.command))
        result = proc.run(argv, cwd=str(repo_root) if repo_root is not None else None)
    except (OSError, RuntimeError, ValueError):
        print("BGJOB_ERROR=invalid-input")
        return 2
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def _checks_step_for_site(site: str) -> tuple[str, int]:
    if site == "step3":
        return "implement-step3-checks", 15600
    if site == "step5-self-review":
        return "implement-checks-step5-self-review", 14700
    if site == "step6":
        return _STEP6_CHECKS_STEP, 10800
    return f"implement-checks-{site}", 10800


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
    # claude_fallback / --self-implement runs have no implementer manifest.json by
    # design (Steps 9a/9a.1 consume an in-memory equivalent). Pass None when no
    # manifest is present so resolve_implement_manifest searches and returns None
    # instead of raising on an explicit missing path (issue #7197).
    manifest_path: Path | None = implement_tmpdir / "manifest.json"
    if not manifest_path.is_file():
        codex_manifest = implement_tmpdir / "codex-step2-out" / "manifest.json"
        manifest_path = codex_manifest if codex_manifest.is_file() else None
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


def _parse_whitespace_kv_line(line: str) -> dict[str, str]:
    return larch_io.parse_kv(
        "\n".join(line.split()),
        duplicate_policy="first",
        key_pattern=r"[A-Z0-9_]+",
    )


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
    result = _invoke_larch(
        [
            "implement",
            "checks-result-identity",
            "resolve-repo-root",
            "--implement-tmpdir",
            str(implement_tmpdir),
        ]
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or "resolve-repo-root failed"
        raise ShipError(f"checks-commit-route: {detail.removeprefix('ERROR=')}")
    root = larch_io.kv_value(text=result.stdout or "", key="REPO_ROOT", first_match=True).strip()
    if not root:
        raise ShipError("checks-commit-route: REPO_ROOT missing from resolve-repo-root")
    return Path(root)


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
        label=f"checks_run_relevant:{checks_site}",
        cwd=root,
        env=env,
        runtime="larch",
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
    refresh_step3_self_edits: bool = False


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
        parsed = larch_io.parse_kv(line, duplicate_policy="first")
        if parsed and next(iter(parsed)) in allowed:
            print(line)


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
    result = _invoke_larch(
        [
            "run-log",
            "append-failure",
            "--log",
            str(implement_tmpdir / "execution-issues.md"),
            "--site",
            display_site,
            "--tool",
            "scripts/larch.sh review-and-fix commit-fixes --stage-all",
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
        result = _invoke_larch(
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
    commit_result = _invoke_larch(["review-and-fix", "commit-fixes", "--stage-all"])
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
    result = rust_runtime.checkpoint_probe(
        proc, step_prefix="7.r", short_name="commit (review)", forked_target=forked_target,
    )
    for line in result.stdout.splitlines():
        if line:
            print(line)
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    return result.exit_code


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
    return list(porcelain_status_paths_z(stdout))


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
    print(f"⏩ 4: commit (impl) status=skip reason={reason} sha={commit_sha} elapsed=0s", file=sys.stderr)
    return "noop", "COMMIT_ROUTE_OUTCOME=noop\nCOMMIT_OUTCOME=noop\n"


def _step4_commit_seed_from_files(
    *,
    message_path: Path,
    pathspec: Path,
    refresh_step3_self_edits: bool = False,
) -> Step4CommitSeed | None:
    if not _path_readable_nonempty(message_path):
        return None
    message = _read_redacted_message(message_path)
    if not message or not _path_readable_nonempty(pathspec):
        return None
    return Step4CommitSeed(
        message=message,
        pathspec=pathspec,
        refresh_step3_self_edits=refresh_step3_self_edits,
    )


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
        return _step4_commit_seed_from_files(
            message_path=implementation_message,
            pathspec=implementation_paths,
            refresh_step3_self_edits=True,
        )
    if dispatcher_commit_complete:
        return _step4_dispatcher_committed_seed(implement_tmpdir)
    return None


def _step4_pathspec_with_step3_self_edits(
    *,
    implement_tmpdir: Path,
    pathspec: Path,
    repo_root: Path,
) -> tuple[Path | None, bool]:
    """Union still-attributed Step 3 edits into the frozen implementation pathspec.

    The implementation pathspec comes from Step 2.4, before a Step 3 repair-loop
    can run lint-fix. Only dirty paths whose current content still matches an
    attribution record are added; unrelated concurrent changes remain outside
    the commit route.
    """
    result = _run([GIT_BIN, "status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if result.returncode != 0:
        return None, False
    dirty_paths = set(_porcelain_status_paths_z(result.stdout))
    if not dirty_paths:
        return pathspec, True
    eligible_sources = {"lint-fix:step3", "pre-commit-autofix"}
    self_edit_paths = {
        record.path
        for record in read_self_edits(implement_tmpdir)
        if record.source in eligible_sources
        and record.path in dirty_paths
        and not Path(record.path).is_absolute()
        and ".." not in Path(record.path).parts
        and file_sha256(repo_root, record.path) == record.post_sha256
    }
    paths = sorted(set(_read_nul_pathspec(pathspec)) | self_edit_paths)
    if not self_edit_paths:
        return pathspec, True
    refreshed_pathspec = implement_tmpdir / "step4-commit-paths.nul"
    _write_bytes_atomic(
        path=refreshed_pathspec,
        data=b"".join(path.encode("utf-8", "surrogateescape") + b"\0" for path in paths),
    )
    return refreshed_pathspec, True


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
    result = _invoke_larch(
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
    pathspec = seed.pathspec
    if seed.refresh_step3_self_edits:
        repo_root = _resolve_repo_root()
        if repo_root is None:
            return "seed-failed", "COMMIT_ROUTE_OUTCOME=seed-failed\n"
        pathspec, refresh_ok = _step4_pathspec_with_step3_self_edits(
            implement_tmpdir=implement_tmpdir,
            pathspec=pathspec,
            repo_root=repo_root,
        )
        if not refresh_ok or pathspec is None:
            return "seed-failed", "COMMIT_ROUTE_OUTCOME=seed-failed\n"
    if _pathspec_clean_relative_to_head(pathspec):
        noop_reason = "dispatcher-committed" if dispatcher_commit_complete else "already-committed"
        return _step4_noop(noop_reason)

    result = _run_leg_with_timeout(
        argv=[
            "implement",
            "commit",
            "--message",
            seed.message,
            "--pathspec-from-file",
            str(pathspec),
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
    scope = proc.run(
        [
            str(larch_entrypoint(Path(__file__).resolve().parents[3])),
            "dirty-tree",
            "scope-check",
            "--plan-file",
            str(implement_tmpdir / "plan.txt"),
            "--paths-file",
            str(final_paths),
        ],
        cwd=str(repo_root),
    )
    if scope.returncode != 0:
        if scope.stdout:
            sys.stderr.write(scope.stdout)
        if scope.stderr:
            sys.stderr.write(scope.stderr)
        sys.stderr.flush()
        _emit_kv(key="BAIL_REASON", value="recovery-out-of-scope")
        return scope.returncode or 1
    return 0


def _run_4r_rebase_checkpoint(forked_target: str) -> int:
    result = rust_runtime.checkpoint_probe(
        proc, step_prefix="4.r", short_name="commit (impl)", forked_target=forked_target,
    )
    for line in result.stdout.splitlines():
        if line:
            print(line)
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    _emit_kv(key="NEXT_ACTION", value="continue")
    return result.exit_code


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
        print("> **🔶 /implement 7: commit (review)**", file=sys.stderr)
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
