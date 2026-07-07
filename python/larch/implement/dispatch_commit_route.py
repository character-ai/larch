# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Checks relay, commit-route core, steps 4-6 composites, step 5 review/resume."""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.core import config
from larch.core import redact
from larch.implement import checks
from larch.implement import ship
from larch.implement.bg_wait import _write_bg_wait_marker
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
    _resolve_repo_root,
    _run,
    _run_cli_forward,
    _tmpdir_from_env,
    _write_bytes_atomic,
    _write_text_atomic,
    GIT_BIN,
)
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


def _write_terminal_sentinel(*, tmpdir: Path, sentinel: str) -> None:
    path = tmpdir / sentinel
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")


@contextlib.contextmanager
def _bg_wait_marker(*, tmpdir: Path, step: str, timeout_s: int, terminal_sentinel: str):
    _write_bg_wait_marker(tmpdir=tmpdir, step=step, timeout_s=timeout_s)
    try:
        yield
    finally:
        _write_terminal_sentinel(tmpdir=tmpdir, sentinel=terminal_sentinel)
        with contextlib.suppress(OSError):
            (tmpdir / ".bg-wait-active").unlink()


@contextlib.contextmanager
def _optional_bg_wait_marker(*, tmpdir: Path, marker: tuple[str, int, str] | None):
    if marker is None:
        yield
        return
    step, timeout_s, terminal_sentinel = marker
    with _bg_wait_marker(tmpdir=tmpdir, step=step, timeout_s=timeout_s, terminal_sentinel=terminal_sentinel):
        yield


def _checks_commit_route_marker(checks_site: str) -> tuple[str, int, str] | None:
    if checks_site == "step5-self-review":
        return config.CHECKS_COMMIT_ROUTE_MARKER_STEP5_SELF_REVIEW, 14700, ".completed/step-5-self-review-terminal"
    return None


def _clear_step3_bg_wait_sidecars(implement_tmpdir: Path) -> None:
    with contextlib.suppress(OSError):
        (implement_tmpdir / ".completed" / "step-3-terminal").unlink()
    with contextlib.suppress(OSError):
        (implement_tmpdir / "bg-poll-guard-probe-denials.step-3-terminal.count").unlink()


def step5_review_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-5-review").parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _invoke_cli(["timing", "telemetry-mark", "--implement-tmpdir", str(implement_tmpdir), "--label", "Step 5: code review"])
    dynamic_cap = _read_session_key_default(implement_tmpdir=implement_tmpdir, key="LARCH_DYNAMIC_ARCHETYPES_MAX", default="") or os.environ.get("LARCH_DYNAMIC_ARCHETYPES_MAX", "") or "1"
    if dynamic_cap not in {"0", "1"}:
        print(f"ERROR: Step 5 banner dynamic_archetypes_cap is non-integer or out of range: {dynamic_cap}", file=sys.stderr)
        return 2
    os.environ["LARCH_DYNAMIC_ARCHETYPES_MAX"] = dynamic_cap
    round_cap = "2"
    print(f"> **🔶 /implement 5: code review: review-and-fix step5 --mode loop, up to {round_cap} rounds; round 1 full paired reviewer panel; round 2 pruned on round-1 productivity; prune-to-empty converges; no round-5 re-probe; dynamic-archetypes cap={dynamic_cap}**")
    return _run_cli_forward(["review-and-fix", "step5", "--implement-tmpdir", str(implement_tmpdir), "--mode", "loop", "--starting-round", "1"])


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


def _run_relevant_checks_for_site(
    *,
    implement_tmpdir: Path,
    checks_site: str,
    deadline_ms: int,
) -> tuple[dict[str, str], bool]:
    result = _run_leg_with_timeout(
        argv=["checks", "run-relevant", "--site", checks_site, "--tmpdir", str(implement_tmpdir)],
        deadline_ms=deadline_ms,
        label=f"{checks.checks_run_relevant_main.__name__}:{checks_site}",
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
    result = _invoke_cli(
        [
            "run-log",
            "append-failure",
            "--log",
            str(implement_tmpdir / "execution-issues.md"),
            "--site",
            site_name,
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
    marker = _checks_commit_route_marker(args.checks_site)
    if args.checks_site == "step3":
        _clear_step3_bg_wait_sidecars(implement_tmpdir)
    with _optional_bg_wait_marker(tmpdir=implement_tmpdir, marker=marker):
        return _checks_commit_route_main_impl(args, implement_tmpdir)


def _checks_commit_route_main_impl(  # noqa: C901,PLR0911,RUF100
    args: argparse.Namespace, implement_tmpdir: Path
) -> int:
    captured, timed_out = _run_relevant_checks_for_site(
        implement_tmpdir=implement_tmpdir,
        checks_site=args.checks_site,
        deadline_ms=args.checks_deadline_ms,
    )
    _relay_checks_stdout(captured)
    if timed_out or not _checks_pass(captured):
        _emit_kv(key="NEXT_ACTION", value="checks-failed")
        return 0
    if args.emit_step7_breadcrumb:
        print("> **🔶 /implement 7: commit (review)**")
    if args.commit_site == "step4":
        repo_root = _resolve_repo_root()
        if repo_root is None:
            print("checks-commit-route: git rev-parse --show-toplevel failed", file=sys.stderr)
            return 2
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
    with _bg_wait_marker(
        tmpdir=implement_tmpdir,
        step="implement-step5-resume",
        timeout_s=32700,
        terminal_sentinel=".completed/step-5-resume-terminal",
    ):
        return _checks_step5_resume_main_impl(args, implement_tmpdir)


def _checks_step5_resume_main_impl(args: argparse.Namespace, implement_tmpdir: Path) -> int:
    captured, timed_out = _run_relevant_checks_for_site(
        implement_tmpdir=implement_tmpdir,
        checks_site=args.checks_site,
        deadline_ms=args.checks_deadline_ms,
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
            return commit_result.returncode if commit_result.returncode != 0 else 1
        if commit_result.returncode != 0:
            return commit_result.returncode
        return None
    _step5_resume_relay_commit_kvs(commit_output)
    return commit_result.returncode if commit_result.returncode != 0 else 1


def step5_resume_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-5-resume")
    parser.add_argument("--final-round-num", required=True)
    parser.add_argument("--ready-to-commit", action="store_true")
    parser.add_argument("--record-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.final_round_num.isdigit():
        print("step-5-resume: --final-round-num must be numeric", file=sys.stderr)
        return 2
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    subprocess.run([sys.executable, str(_current_cli_path()), "timing", "mark", "Step 5: review handoff"], env={**os.environ, "DESIGN_TMPDIR": "", "LARCH_TIMING_SKILL": "implement"}, check=False)
    round_start_file = implement_tmpdir / f"round-{args.final_round_num}" / "round-start-s"
    if round_start_file.is_file():
        start_s = round_start_file.read_text(encoding="utf-8", errors="replace").strip()
        ledger = implement_tmpdir / "timing-ledger.tsv"
        needs_record = start_s.isdigit()
        if needs_record and ledger.is_file():
            round_decimal = str(int(args.final_round_num))
            for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
                cols = line.split("\t")
                if _step5_round_timing_row_exists(cols, round_decimal=round_decimal, start_s=start_s):
                    needs_record = False
                    break
        if needs_record and start_s.isdigit():
            _invoke_cli(["review-and-fix", "record-round-timing", "--implement-tmpdir", str(implement_tmpdir), "--round", args.final_round_num, "--start-s", start_s, "--end-s", str(int(time.time()))])
    if args.record_only:
        return 0
    if args.ready_to_commit or os.environ.get("STEP5_HANDOFF_READY_TO_COMMIT") == "true":
        commit_rc = _step5_resume_commit_phase()
        if commit_rc is not None:
            return commit_rc
    print("progress: type p (or progress) at any time")
    return _run_cli_forward(["review-and-fix", "step5", "--implement-tmpdir", str(implement_tmpdir), "--mode", "loop", "--starting-round", str(int(args.final_round_num) + 1)])


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


def step6_entry_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement step-6-entry")
    parser.add_argument("--forked-target", choices=("true", "false"), default="false")
    parser.add_argument("--force-checks", choices=("true", "false"), default="false")
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
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


def run_step_checks_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement run-step-checks")
    parser.add_argument("--site", required=True)
    args = parser.parse_args(argv)
    implement_tmpdir = _tmpdir_from_env()
    _rehydrate_plugin_root(implement_tmpdir)
    _rehydrate_larch_triplet(implement_tmpdir)
    command = ["checks", "run-relevant", "--site", args.site, "--tmpdir", str(implement_tmpdir)]
    if args.site == "step3":
        _clear_step3_bg_wait_sidecars(implement_tmpdir)
    return _run_cli_forward(command)


def step8_python_guard_main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="cli.py implement step-8-python-guard").parse_args(argv)
    if sys.version_info >= (3, 11):  # noqa: UP036 - intentional runtime guard; this module may execute under pre-3.11 interpreters.
        return 0
    print("ERROR: Python ship driver requires Python 3.11 or newer", file=sys.stderr)
    print('{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","ledger_dispatcher":"","ledger_exit_code":null,"ledger_failure_detail_log":"","ledger_phase":"","ledger_ready":false,"ledger_site":"","ledger_step":"","ledger_trigger":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}')
    return 4
