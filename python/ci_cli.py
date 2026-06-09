# pyright: reportUnusedCallResult=false
"""Thin CLI entrypoints for CI helper primitives."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import ci_monitor
import proc


def _emit_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


def _parse(parser: argparse.ArgumentParser, argv: list[str], usage_exit: int) -> argparse.Namespace | int:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return usage_exit


def status_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci status")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--empty-checks-grace", default=0, type=int)
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
        _emit_kv("CI_STATUS", "error")
        _emit_kv("BEHIND_COUNT", 0)
        _emit_kv("FAILED_RUN_ID", "")
        _emit_kv("CONFLICTED", "false")
        return args
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
    parser.add_argument("--ci-status", required=True)
    parser.add_argument("--behind-count", required=True, type=int)
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
    lines = [
        f"CI_STATUS={status.status}",
        f"BEHIND_COUNT={status.behind_count}",
        f"FAILED_RUN_ID={status.failed_run_id or ''}",
        f"CONFLICTED={str(status.conflicted).lower()}",
        f"ACTION={decision.action}",
        f"BAIL_REASON={decision.bail_reason or ''}",
    ]
    text = "\n".join(lines) + "\n"
    if args.output_file:
        out = Path(args.output_file)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(out)
        out.with_name(out.name + ".done").write_text("", encoding="utf-8")
    sys.stdout.write(text)
    return 0 if decision.action != "bail" else 1


def failed_jobs_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci failed-jobs")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", required=True)
    args = _parse(parser, argv, 1)
    if isinstance(args, int):
        return args
    jobs, state = ci_monitor.read_failed_jobs(proc, run_id=args.run_id, repo=args.repo)
    classified = ci_monitor.classify_failed_jobs(jobs)
    _emit_kv("FAILED_JOBS_STATUS", state)
    _emit_kv("FAILED_JOB_COUNT", classified.count)
    _emit_kv("FIXABLE_JOBS", ",".join(f"{j.name}:{j.shard}" if j.shard else j.name for j in classified.fixable))
    _emit_kv("UNFIXABLE_JOBS", ",".join(f"{j.name}:{j.shard}" if j.shard else j.name for j in classified.unfixable))
    print(json.dumps({"jobs": [j.__dict__ for j in classified.jobs]}))
    return 0


def behind_count_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ci behind-count")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--no-fetch", action="store_true")
    args = _parse(parser, argv, 2)
    if isinstance(args, int):
        return args
    print(ci_monitor.behind_count(proc, base_remote=args.base_remote, base_ref=args.base_ref, fetch=not args.no_fetch))
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
    _emit_kv("RERUN_ALREADY_RUNNING", str(result.already_running).lower())
    _emit_kv("ERROR", result.error or "")
    return 0
