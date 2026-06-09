"""Design-log PR checks-only CI wait, rerun, and admin merge helper."""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import ci_monitor
import config
import gh
import logging_util
import proc
import redact
import retry
from proc import CommandResult, Runner

SleepFn = Callable[[float], None]


@dataclass(frozen=True)
class DesignLogMergeResult:
    ok: bool
    detail: str = ""
    already_merged: bool = False


@dataclass(frozen=True)
class FailedRunRerunClass:
    kind: str
    detail: str = ""


def _ci_wait_poll_budget() -> int:
    return max(1, math.ceil(config.CI_WAIT_TIMEOUT_SEC / config.CI_WAIT_POLL_INTERVAL_SEC))


def _detail(text: str, *, limit: int = 500) -> str:
    cleaned = redact.redact(text).replace("\r", " ").replace("\n", " ").strip()
    return cleaned[:limit]


def _classify_failed_run_for_rerun(
    runner: Runner,
    *,
    run_id: str,
    repo: str,
    cwd: str | None,
) -> FailedRunRerunClass:
    try:
        logs = ci_monitor.collect_failed_logs(runner, run_id=run_id, repo=repo, cwd=cwd)
    except Exception as exc:  # pylint: disable=broad-except
        return FailedRunRerunClass("error", _detail(f"collect failed logs raised: {exc}"))
    if logs.state == "ready":
        if retry.is_transient_net_signature(logs.text):
            return FailedRunRerunClass("ready_transient", "failed logs contain transient signature")
        return FailedRunRerunClass("ready_no_signature", "failed logs ready without transient signature")
    if logs.state == "in_progress":
        return FailedRunRerunClass("not_ready", "failed logs not ready")
    return FailedRunRerunClass("error", _detail(logs.text or f"failed logs state {logs.state}"))


def _pr_already_merged(runner: Runner, *, pr: int, repo: str, cwd: str | None) -> bool:
    try:
        pr_info = gh.pr_view(runner, pr, repo=repo, cwd=cwd)
    except Exception:  # pylint: disable=broad-except
        return False
    return pr_info.state.upper() == "MERGED"


def _required_checks_green_guard(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    cwd: str | None,
    sleep_fn: SleepFn,
) -> DesignLogMergeResult:
    max_wait_polls = _ci_wait_poll_budget()
    wait_polls = 0
    while True:
        if _pr_already_merged(runner, pr=pr, repo=repo, cwd=cwd):
            return DesignLogMergeResult(ok=True, already_merged=True, detail="PR already merged")
        try:
            status, failed_run_id = ci_monitor.checks_status(
                runner,
                pr=pr,
                repo=repo,
                empty_checks_grace=0,
                required=True,
                cwd=cwd,
                sleep_fn=sleep_fn,
            )
        except Exception as exc:  # pylint: disable=broad-except
            status = "pending"
            failed_run_id = None
            last_detail = f"required checks read error: {exc}"
        else:
            last_detail = f"required checks status {status}"
        if status == "pass":
            return DesignLogMergeResult(ok=True, detail="required checks passed")
        if status in {"pending", "empty", "NO_CHECKS", ""}:
            wait_polls += 1
            if wait_polls > max_wait_polls:
                return DesignLogMergeResult(ok=False, detail=_detail(f"required checks did not become green: {last_detail}"))
            sleep_fn(float(config.CI_WAIT_POLL_INTERVAL_SEC))
            continue
        if status == "fail":
            suffix = f" (run {failed_run_id})" if failed_run_id else ""
            return DesignLogMergeResult(ok=False, detail=f"required checks failed{suffix}")
        return DesignLogMergeResult(ok=False, detail=_detail(f"required checks non-pass status: {status}"))


def _merge_with_transient_retry(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    merge_cwd: str | None,
    sleep_fn: SleepFn,
) -> DesignLogMergeResult:
    def attempt() -> tuple[CommandResult, int, str]:
        result = gh.pr_merge(
            runner,
            pr,
            repo=repo,
            merge_method="squash",
            admin=True,
            delete_branch=True,
            cwd=merge_cwd,
        )
        return result, result.returncode, result.stdout + result.stderr

    retried = retry.with_transient_retry(attempt, sleeper=sleep_fn)
    result = retried.value
    if retried.last_returncode == 0 and result.returncode == 0:
        return DesignLogMergeResult(ok=True, detail="merge succeeded")
    return DesignLogMergeResult(
        ok=False,
        detail=_detail(
            f"gh pr merge failed after {retried.attempts} attempt(s) "
            f"(rc={retried.last_returncode}): {result.stdout}{result.stderr}",
        ),
    )


def run_design_log_ci_merge(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    cwd: str | None = None,
    merge_cwd: str | None = None,
    sleep_fn: SleepFn = time.sleep,
) -> DesignLogMergeResult:
    failed_run_reruns = 0
    checks_wait_polls = 0
    log_ready_wait_polls = 0
    post_rerun_settle_wait_polls = 0
    post_rerun_failed_run_id: str | None = None
    max_wait_polls = _ci_wait_poll_budget()
    last_log_class = FailedRunRerunClass("not_ready", "not classified")

    while True:
        if _pr_already_merged(runner, pr=pr, repo=repo, cwd=cwd):
            return DesignLogMergeResult(ok=True, already_merged=True, detail="PR already merged")

        try:
            status, failed_run_id = ci_monitor.checks_status(
                runner,
                pr=pr,
                repo=repo,
                empty_checks_grace=0,
                required=True,
                cwd=cwd,
                sleep_fn=sleep_fn,
            )
        except Exception as exc:  # pylint: disable=broad-except
            status = "pending"
            failed_run_id = None
            last_status_detail = f"required checks read error: {exc}"
        else:
            last_status_detail = f"required checks status {status}"

        if status == "pass":
            post_rerun_failed_run_id = None
            post_rerun_settle_wait_polls = 0
            guard = _required_checks_green_guard(
                runner,
                pr=pr,
                repo=repo,
                cwd=cwd,
                sleep_fn=sleep_fn,
            )
            if not guard.ok:
                return guard
            if guard.already_merged:
                return DesignLogMergeResult(ok=True, already_merged=True, detail=guard.detail)
            return _merge_with_transient_retry(
                runner,
                pr=pr,
                repo=repo,
                merge_cwd=merge_cwd,
                sleep_fn=sleep_fn,
            )

        if status in {"pending", "empty", "NO_CHECKS", ""}:
            checks_wait_polls += 1
            if checks_wait_polls > max_wait_polls:
                return DesignLogMergeResult(ok=False, detail=_detail(f"required-check wait timed out: {last_status_detail}"))
            sleep_fn(float(config.CI_WAIT_POLL_INTERVAL_SEC))
            continue

        if status == "fail":
            checks_wait_polls = 0
            if post_rerun_failed_run_id is not None:
                if failed_run_id == post_rerun_failed_run_id:
                    if post_rerun_settle_wait_polls < max_wait_polls:
                        post_rerun_settle_wait_polls += 1
                        sleep_fn(float(config.CI_WAIT_POLL_INTERVAL_SEC))
                        continue
                    return DesignLogMergeResult(
                        ok=False,
                        detail=f"failed check stayed on pre-rerun run id {post_rerun_failed_run_id}",
                    )
                post_rerun_failed_run_id = None
                post_rerun_settle_wait_polls = 0

            if not failed_run_id:
                return DesignLogMergeResult(ok=False, detail="required check failed without an Actions run id")
            if failed_run_reruns >= config.CI_MONITOR_TRANSIENT_RERUN_MAX:
                return DesignLogMergeResult(
                    ok=False,
                    detail=f"failed-run rerun budget exhausted after run {failed_run_id}",
                )

            last_log_class = _classify_failed_run_for_rerun(
                runner,
                run_id=failed_run_id,
                repo=repo,
                cwd=cwd,
            )
            if last_log_class.kind in {"not_ready", "error"} and log_ready_wait_polls < max_wait_polls:
                log_ready_wait_polls += 1
                sleep_fn(float(config.CI_WAIT_POLL_INTERVAL_SEC))
                continue

            rerun = ci_monitor.rerun_failed(runner, run_id=failed_run_id, repo=repo, cwd=cwd)
            if rerun.submitted or rerun.already_running:
                failed_run_reruns += 1
                checks_wait_polls = 0
                log_ready_wait_polls = 0
                post_rerun_settle_wait_polls = 0
                post_rerun_failed_run_id = failed_run_id
                sleep_fn(float(config.CI_WAIT_POLL_INTERVAL_SEC))
                continue
            return DesignLogMergeResult(
                ok=False,
                detail=_detail(
                    f"failed-run rerun was not submitted for run {failed_run_id}; "
                    f"logs={last_log_class.kind}; error={rerun.error or 'unknown'}",
                ),
            )

        return DesignLogMergeResult(ok=False, detail=_detail(f"required checks fail-closed on status {status}"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Wait/merge a design-log PR through required checks")
    _ = parser.add_argument("--pr-number", type=int, required=True)
    _ = parser.add_argument("--repo", default=None)
    _ = parser.add_argument("--base-remote", default="origin")
    _ = parser.add_argument("--base-ref", default="main")
    _ = parser.add_argument("--cwd", default=None)
    _ = parser.add_argument("--merge-cwd", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    runner = proc
    repo_arg = args.repo
    if repo_arg:
        if not gh.validate_repo_slug(repo_arg):
            print("ERROR: invalid --repo; expected OWNER/REPO", file=sys.stderr, flush=True)
            return 2
        repo = repo_arg
    else:
        repo = gh.resolve_repo(runner, cwd=args.merge_cwd or args.cwd)
        if not repo:
            print("ERROR: could not resolve repository; pass --repo OWNER/REPO", file=sys.stderr, flush=True)
            return 2

    logging_util.quiet_init(argv0="design-log-ship.py")
    result = run_design_log_ci_merge(
        runner,
        pr=args.pr_number,
        repo=repo,
        cwd=args.cwd,
        merge_cwd=args.merge_cwd,
    )
    logging_util.emit_kv("PUBLISH_OK", "true" if result.ok else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
