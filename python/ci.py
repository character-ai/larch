# pyright: reportUnusedCallResult=false
"""Thin CLI entrypoints for CI helper primitives (ci)."""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import signal
import sys
import time
from pathlib import Path
from typing import cast

import ci_monitor
import ci_agentic_fix
import config
import git
import logging_util
import proc


def _emit_kv(key: str, value: object) -> None:
    logging_util.emit_kv(key, str(value))


def _parse(parser: argparse.ArgumentParser, argv: list[str], usage_exit: int) -> argparse.Namespace | int:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return usage_exit


def _status_error_kv() -> None:
    _emit_kv(key="CI_STATUS", value="error")
    _emit_kv(key="BEHIND_COUNT", value=0)
    _emit_kv(key="FAILED_RUN_ID", value="")
    _emit_kv(key="CONFLICTED", value="false")


def _usage_error(message: str) -> None:
    print(message, file=sys.stderr)


def _non_negative_int_error(name: str, value: float) -> str | None:
    if value < 0:
        return f"ERROR: --{name.replace('_', '-')} must be a non-negative integer, got: {value}"
    return None


def _base_ref_error(base_remote: str, base_ref: str) -> str | None:
    if git.validate_base_remote_ref(base_remote, base_ref) is None:
        return None
    return "ERROR: --base-remote/--base-ref contain unsupported characters"


def status_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci status")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--empty-checks-grace", default=config.CI_WAIT_EMPTY_CHECKS_GRACE_SEC, type=int)
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
        _status_error_kv()
        return 0
    err = _non_negative_int_error("empty_checks_grace", args.empty_checks_grace) or _base_ref_error(
        args.base_remote,
        args.base_ref,
    )
    if err is not None:
        _usage_error(err)
        _status_error_kv()
        return 0
    status = ci_monitor.gather_status(
        proc,
        pr=args.pr,
        repo=args.repo,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
        empty_checks_grace=args.empty_checks_grace,
    )
    _emit_kv(key="CI_STATUS", value=status.status)
    _emit_kv(key="BEHIND_COUNT", value=status.behind_count)
    _emit_kv(key="FAILED_RUN_ID", value=status.failed_run_id or "")
    _emit_kv(key="CONFLICTED", value=str(status.conflicted).lower())
    return 0


_VALID_CI_STATUS = frozenset({"pass", "fail", "pending", "merged", "error"})


def _decide_usage(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def decide_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci decide")
    parser.add_argument("--ci-status", "--status", dest="ci_status", required=True)
    parser.add_argument("--behind-count", "--behind", dest="behind_count", required=True, type=int)
    parser.add_argument("--failed-run-id", default="")
    parser.add_argument("--conflicted", default="false")
    parser.add_argument("--iteration", default=0, type=int)
    parser.add_argument("--rebase-count", default=0, type=int)
    parser.add_argument("--fix-attempts", default=0, type=int)
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
        return args
    if args.ci_status not in _VALID_CI_STATUS:
        return _decide_usage(
            f"ERROR: --status must be pass|fail|pending|merged|error, got: {args.ci_status}",
        )
    for name in ("behind_count", "iteration", "rebase_count", "fix_attempts"):
        value = getattr(args, name)
        if value < 0:
            return _decide_usage(
                f"ERROR: {name} must be a non-negative integer, got: {value}",
            )
    conflicted_raw = args.conflicted.lower()
    if conflicted_raw not in ("true", "false"):
        return _decide_usage(
            f"ERROR: --conflicted must be true or false, got: {args.conflicted}",
        )
    decision = ci_monitor.decide(
        ci_monitor.CiStatus(
            status=args.ci_status,
            behind_count=args.behind_count,
            failed_run_id=args.failed_run_id or None,
            conflicted=conflicted_raw == "true",
        ),
        iteration=args.iteration,
        rebase_count=args.rebase_count,
        fix_attempts=args.fix_attempts,
    )
    _emit_kv(key="ACTION", value=decision.action)
    _emit_kv(key="BAIL_REASON", value=decision.bail_reason or "")
    return 0


def _wait_output_lines(
    status: ci_monitor.CiStatus,
    decision: ci_monitor.Decision,
    *,
    iteration: int,
    elapsed: int,
) -> list[str]:
    return [
        f"ACTION={decision.action}",
        f"CI_STATUS={status.status}",
        f"BEHIND_COUNT={status.behind_count}",
        f"CONFLICTED={str(status.conflicted).lower()}",
        f"FAILED_RUN_ID={status.failed_run_id or ''}",
        f"BAIL_REASON={decision.bail_reason or ''}",
        f"ITERATION={iteration}",
        f"ELAPSED={elapsed}",
    ]


def _publish_wait_output(text: str, output_file: str) -> bool:
    out = Path(output_file)
    tmp = out.with_suffix(out.suffix + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(out)
    except OSError:
        return False
    return True


def wait_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci wait")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--empty-checks-grace", default=config.CI_WAIT_EMPTY_CHECKS_GRACE_SEC, type=int)
    parser.add_argument("--iteration", default=0, type=int)
    parser.add_argument("--rebase-count", default=0, type=int)
    parser.add_argument("--fix-attempts", default=0, type=int)
    parser.add_argument("--timeout", default=1800, type=int)
    parser.add_argument("--output-file", default="")
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
        return args

    for name in ("rebase_count", "fix_attempts", "iteration", "timeout", "empty_checks_grace"):
        err = _non_negative_int_error(name, getattr(args, name))
        if err is not None:
            _usage_error(err)
            return 1
    err = _base_ref_error(args.base_remote, args.base_ref)
    if err is not None:
        _usage_error(err)
        return 1

    output_file = args.output_file
    out_path: Path | None = Path(output_file) if output_file else None
    if out_path is not None:
        for stale in (
            out_path,
            out_path.with_name(out_path.name + ".done"),
            out_path.with_suffix(out_path.suffix + ".tmp"),
        ):
            stale.unlink(missing_ok=True)

    status = ci_monitor.CiStatus(
        status="pending",
        behind_count=0,
        failed_run_id=None,
        conflicted=False,
    )
    decision = ci_monitor.Decision(
        action="bail",
        bail_reason=config.CI_WAIT_BAIL_UNEXPECTED_EXIT,
    )
    elapsed = 0
    trap_exit = 0
    published = False
    old_signal_handlers: dict[int, signal.Handlers] = {}

    def _publish_trap_output() -> None:
        nonlocal published
        if published or out_path is None:
            return
        published = True
        lines = _wait_output_lines(
            status,
            decision,
            iteration=args.iteration,
            elapsed=elapsed,
        )
        text = "\n".join(lines) + "\n"
        if _publish_wait_output(text, output_file):
            done_path = out_path.with_name(out_path.name + ".done")
            with contextlib.suppress(OSError):
                _ = done_path.write_text(f"{trap_exit}\n", encoding="utf-8")

    if output_file:

        def _signal_handler(signum: int, _frame: object) -> None:
            nonlocal trap_exit
            trap_exit = 128 + signum
            _publish_trap_output()
            raise SystemExit(trap_exit)

        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            with contextlib.suppress(ValueError, OSError):
                old_signal_handlers[sig] = cast(
                    "signal.Handlers",
                    signal.signal(sig, _signal_handler),
                )

    try:
        started = time.monotonic()
        status, decision = ci_monitor.poll_ci(
            proc,
            pr=args.pr,
            repo=args.repo,
            base_remote=args.base_remote,
            base_ref=args.base_ref,
            empty_checks_grace=args.empty_checks_grace,
            iteration=args.iteration,
            rebase_count=args.rebase_count,
            fix_attempts=args.fix_attempts,
            timeout=args.timeout,
        )
        elapsed = int(time.monotonic() - started)
        trap_exit = 0
    except Exception:
        trap_exit = 1
        if not output_file:
            raise
    finally:
        if output_file:
            for sig, handler in old_signal_handlers.items():
                with contextlib.suppress(ValueError, OSError):
                    signal.signal(sig, handler)
            _publish_trap_output()

    if output_file:
        return 0

    for line in _wait_output_lines(
        status,
        decision,
        iteration=args.iteration,
        elapsed=elapsed,
    ):
        key, _, value = line.partition("=")
        _emit_kv(key=key, value=value)
    return 0


_JOB_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _failed_job_reason_token(job_name: str, *, malformed: bool) -> str:
    if malformed:
        return "malformed-job-name"
    if job_name in ("gitleaks", "trufflehog"):
        return "history-scan"
    return "unknown-job-name"


def failed_jobs_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci failed-jobs")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output-tsv", default="")
    args = _parse(parser, argv, 2)
    if isinstance(args, int):
        return args
    jobs, state = ci_monitor.read_failed_jobs(proc, run_id=args.run_id, repo=args.repo)
    if state == "in_progress":
        return 3
    if state == "error":
        return 1
    classified = ci_monitor.classify_failed_jobs(jobs)
    tsv_lines: list[str] = []
    fixable_tokens: list[str] = []
    unfixable_tokens: list[str] = []
    fixable_set: set[ci_monitor.JobClass] = set(classified.fixable)
    for row in classified.jobs:
        malformed = _JOB_NAME_RE.match(row.name) is None
        line = f"{row.name}\t{row.shard}\t{row.klass}"
        tsv_lines.append(line)
        token = f"{row.name}:{row.shard}" if row.shard else row.name
        if row in fixable_set:
            fixable_tokens.append(token)
        else:
            reason = _failed_job_reason_token(row.name, malformed=malformed)
            unfixable_tokens.append(f"{token}={reason}")
    if args.output_tsv:
        out = Path(args.output_tsv)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + f".tmp.{os.getpid()}")
        _ = tmp.write_text("\n".join(tsv_lines) + ("\n" if tsv_lines else ""), encoding="utf-8")
        tmp.replace(out)
    else:
        for line in tsv_lines:
            print(line)
    fixable = logging_util.sanitize_list(",".join(fixable_tokens))
    unfixable = logging_util.sanitize_list(",".join(unfixable_tokens))
    _emit_kv(key="FAILED_JOBS_COUNT", value=classified.count)
    _emit_kv(key="FAILED_JOBS_FIXABLE", value=fixable)
    _emit_kv(key="FAILED_JOBS_UNFIXABLE", value=unfixable)
    return 0


def agentic_fix_main(argv: list[str]) -> int:
    return ci_agentic_fix.main(argv)


def behind_count_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci behind-count")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--no-fetch", action="store_true")
    args = _parse(parser, argv, 2)
    if isinstance(args, int):
        return args
    count = ci_monitor.behind_count(
        proc,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
        fetch=not args.no_fetch,
    )
    _emit_kv(key="BEHIND_COUNT", value=count)
    return 0


def rerun_failed_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci rerun-failed")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", required=True)
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
        return args
    result = ci_monitor.rerun_failed(proc, run_id=args.run_id, repo=args.repo)
    _emit_kv(key="RERUN_SUBMITTED", value=str(result.submitted).lower())
    _emit_kv(key="ALREADY_RUNNING", value=str(result.already_running).lower())
    _emit_kv(key="ERROR", value=result.error or "")
    return 0
