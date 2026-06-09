# pyright: reportUnusedCallResult=false
"""Thin CLI entrypoints for CI helper primitives."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import ci_monitor
import logging_util
import proc


def _emit_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


def _parse(parser: argparse.ArgumentParser, argv: list[str], usage_exit: int) -> argparse.Namespace | int:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return usage_exit


def _status_error_kv() -> None:
    _emit_kv("CI_STATUS", "error")
    _emit_kv("BEHIND_COUNT", 0)
    _emit_kv("FAILED_RUN_ID", "")
    _emit_kv("CONFLICTED", "false")


def status_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci status")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--empty-checks-grace", default=0, type=int)
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
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
    _emit_kv("CI_STATUS", status.status)
    _emit_kv("BEHIND_COUNT", status.behind_count)
    _emit_kv("FAILED_RUN_ID", status.failed_run_id or "")
    _emit_kv("CONFLICTED", str(status.conflicted).lower())
    return 0


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
    decision = ci_monitor.decide(
        ci_monitor.CiStatus(
            status=args.ci_status,
            behind_count=args.behind_count,
            failed_run_id=args.failed_run_id or None,
            conflicted=args.conflicted.lower() == "true",
        ),
        iteration=args.iteration,
        rebase_count=args.rebase_count,
        fix_attempts=args.fix_attempts,
    )
    _emit_kv("ACTION", decision.action)
    _emit_kv("BAIL_REASON", decision.bail_reason or "")
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
    parser.add_argument("--empty-checks-grace", default=0, type=int)
    parser.add_argument("--iteration", default=0, type=int)
    parser.add_argument("--rebase-count", default=0, type=int)
    parser.add_argument("--fix-attempts", default=0, type=int)
    parser.add_argument("--timeout", default=1800, type=float)
    parser.add_argument("--output-file", default="")
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
        return args

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
        bail_reason="ci-wait.sh exited unexpectedly",
    )
    elapsed = 0
    trap_exit = 0

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
        if output_file and out_path is not None:
            lines = _wait_output_lines(
                status,
                decision,
                iteration=args.iteration,
                elapsed=elapsed,
            )
            text = "\n".join(lines) + "\n"
            if _publish_wait_output(text, output_file):
                done_path = out_path.with_name(out_path.name + ".done")
                try:
                    _ = done_path.write_text(f"{trap_exit}\n", encoding="utf-8")
                except OSError:
                    pass
            return 0

    lines = _wait_output_lines(
        status,
        decision,
        iteration=args.iteration,
        elapsed=elapsed,
    )
    sys.stdout.write("\n".join(lines) + "\n")
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
    args = _parse(parser, argv, 1)
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
    fixable_set = set(classified.fixable)
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
    _emit_kv("FAILED_JOBS_COUNT", classified.count)
    _emit_kv("FAILED_JOBS_FIXABLE", fixable)
    _emit_kv("FAILED_JOBS_UNFIXABLE", unfixable)
    return 0


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
    _emit_kv("BEHIND_COUNT", count)
    return 0


def rerun_failed_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci rerun-failed")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", required=True)
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
        return args
    result = ci_monitor.rerun_failed(proc, run_id=args.run_id, repo=args.repo)
    _emit_kv("RERUN_SUBMITTED", str(result.submitted).lower())
    _emit_kv("ALREADY_RUNNING", str(result.already_running).lower())
    _emit_kv("ERROR", result.error or "")
    return 0
