"""Design-log PR checks-only CI wait, rerun, and admin merge helper."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

import ci_monitor
from larch.core import config
from larch.git import gh
from larch.core import logging_util
from larch.core import proc
from larch.core import redact
from larch.core import retry
from larch.core.proc import CommandResult, Runner

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
        if ci_monitor.is_transient_failed_log(logs):
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
            # required=True is load-bearing; poll_ci defaults required=False.
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
    log_ready_wait_run_id: str | None = None
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

            if failed_run_id != log_ready_wait_run_id:
                log_ready_wait_polls = 0
                log_ready_wait_run_id = failed_run_id

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
            if last_log_class.kind != "ready_transient":
                return DesignLogMergeResult(
                    ok=False,
                    detail=_detail(
                        f"required check failed (non-transient): "
                        f"run={failed_run_id} logs={last_log_class.kind}",
                    ),
                )

            rerun = ci_monitor.rerun_failed(runner, run_id=failed_run_id, repo=repo, cwd=cwd)
            if rerun.submitted or rerun.already_running:
                failed_run_reruns += 1
                checks_wait_polls = 0
                log_ready_wait_polls = 0
                log_ready_wait_run_id = None
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


class DesignLogSweepError(RuntimeError):
    """Raised when the design-log reconciliation sweep cannot enumerate PRs."""


@dataclass(frozen=True)
class DesignLogSweepItem:
    pr: int
    title: str
    outcome: str
    detail: str = ""


# Default page size for `gh pr list`. The open-PR set this sweep reconciles is
# small; 200 is a generous ceiling that still fits one page.
_SWEEP_PR_LIST_LIMIT = 200

# Head-branch namespace the /design log-publish flow pushes to
# (`larch-logs/design-<run_id>`). Requiring this prefix in addition to the
# `chore(larch-logs): ` title prefix keeps the admin-merge sweep from acting on
# a PR that merely spoofs the title on an unrelated branch.
_DESIGN_LOG_BRANCH_PREFIX = "larch-logs/"


def _list_design_log_prs(
    runner: Runner,
    *,
    repo: str,
) -> list[tuple[int, str]]:
    """Return ``(number, title)`` for open automated larch-logs PRs.

    A PR qualifies only when its title carries the ``chore(larch-logs): ``
    subject prefix **and** its head branch sits under ``larch-logs/``: the
    two markers the /design log-publish flow always stamps together.
    """
    read = gh.pr_list_open_read(runner, repo=repo, limit=_SWEEP_PR_LIST_LIMIT)
    if read.returncode != 0:
        raise DesignLogSweepError(_detail(f"gh pr list failed: {read.stderr or read.stdout}"))
    try:
        parsed: object = json.loads(read.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise DesignLogSweepError(_detail(f"could not parse gh pr list output: {exc}")) from exc
    if not isinstance(parsed, list):
        raise DesignLogSweepError("gh pr list did not return a JSON array")
    prs: list[tuple[int, str]] = []
    for row in cast("list[object]", parsed):
        if not isinstance(row, dict):
            continue
        row_map = cast("dict[str, object]", row)
        number = row_map.get("number")
        title = row_map.get("title", "")
        head_ref = row_map.get("headRefName", "")
        if not isinstance(number, int) or not isinstance(title, str) or not isinstance(head_ref, str):
            continue
        if title.startswith(config.TRANSPARENT_LARCH_LOGS_SUBJECT_PREFIX) and head_ref.startswith(_DESIGN_LOG_BRANCH_PREFIX):
            prs.append((number, title))
    return prs


def _classify_design_log_pr(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    sleep_fn: SleepFn,
) -> tuple[str, str]:
    """Classify a design-log PR without merging (``--dry-run`` path)."""
    if _pr_already_merged(runner, pr=pr, repo=repo, cwd=None):
        return ("already-merged", "PR already merged")
    try:
        status, failed_run_id = ci_monitor.checks_status(
            runner,
            pr=pr,
            repo=repo,
            empty_checks_grace=0,
            required=True,
            cwd=None,
            sleep_fn=sleep_fn,
        )
    except Exception as exc:  # pylint: disable=broad-except
        return ("skipped-not-green", _detail(f"required checks read error: {exc}"))
    if status == "pass":
        return ("would-merge", "required checks passed")
    suffix = f" (run {failed_run_id})" if failed_run_id else ""
    return ("skipped-not-green", _detail(f"required checks status {status}{suffix}"))


def _merge_design_log_pr_if_green(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    sleep_fn: SleepFn,
) -> tuple[str, str]:
    """Admin-merge a single design-log PR when its required checks are green.

    Evaluates the PR once (no long CI poll): a PR whose required checks are not
    yet green is left for a later sweep rather than blocked on. The merge itself
    is admin-squash, bypassing only the review gate the automated PR can never
    satisfy; the no-bypass CI ruleset still guards against merging red CI.
    """
    if _pr_already_merged(runner, pr=pr, repo=repo, cwd=None):
        return ("already-merged", "PR already merged")
    try:
        status, failed_run_id = ci_monitor.checks_status(
            runner,
            pr=pr,
            repo=repo,
            empty_checks_grace=0,
            required=True,
            cwd=None,
            sleep_fn=sleep_fn,
        )
    except Exception as exc:  # pylint: disable=broad-except
        return ("skipped-not-green", _detail(f"required checks read error: {exc}"))
    if status != "pass":
        suffix = f" (run {failed_run_id})" if failed_run_id else ""
        return ("skipped-not-green", _detail(f"required checks status {status}{suffix}"))
    merge = _merge_with_transient_retry(
        runner,
        pr=pr,
        repo=repo,
        merge_cwd=None,
        sleep_fn=sleep_fn,
    )
    if merge.ok:
        return ("merged", merge.detail)
    # The detached /design waiter this sweep backstops may merge the same PR in
    # the window between the green check and our merge; treat that race as a
    # success rather than a false merge-failed (and a spurious sweep exit 1).
    if _pr_already_merged(runner, pr=pr, repo=repo, cwd=None):
        return ("already-merged", "PR merged concurrently")
    return ("merge-failed", merge.detail)


def run_design_log_sweep(
    runner: Runner,
    *,
    repo: str,
    dry_run: bool = False,
    sleep_fn: SleepFn = time.sleep,
) -> list[DesignLogSweepItem]:
    """Reconcile open ``chore(larch-logs):`` PRs by admin-merging the green ones.

    Each PR is evaluated once (no 30-minute CI poll): already-merged PRs are
    skipped, PRs whose required checks are green are admin-squash-merged, and
    PRs whose checks are still pending or failing are left for a later sweep.
    This is the durable backstop for the best-effort detached merge waiter
    spawned at /design log-publish time, which does not reliably survive the
    session that launched it. PR reads and the merge run under the operator's
    ambient ``gh`` auth and working directory; the sweep targets remote PRs by
    explicit ``--repo``, so no worktree ``cwd`` threading is needed.
    """
    prs = _list_design_log_prs(runner, repo=repo)
    items: list[DesignLogSweepItem] = []
    for pr_number, title in prs:
        if dry_run:
            outcome, detail = _classify_design_log_pr(
                runner,
                pr=pr_number,
                repo=repo,
                sleep_fn=sleep_fn,
            )
        else:
            outcome, detail = _merge_design_log_pr_if_green(
                runner,
                pr=pr_number,
                repo=repo,
                sleep_fn=sleep_fn,
            )
        items.append(DesignLogSweepItem(pr=pr_number, title=title, outcome=outcome, detail=detail))
    return items


def _emit_sweep_report(items: list[DesignLogSweepItem], *, dry_run: bool) -> int:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.outcome] = counts.get(item.outcome, 0) + 1
        line = f"design-log-sweep: PR #{item.pr} {item.outcome}"
        if item.detail:
            line += f" - {item.detail}"
        print(line, flush=True)
    logging_util.emit_kv(key="SWEEP_DRY_RUN", value="true" if dry_run else "false")
    logging_util.emit_kv(key="SWEEP_TOTAL", value=str(len(items)))
    logging_util.emit_kv(key="SWEEP_MERGED", value=str(counts.get("merged", 0)))
    logging_util.emit_kv(key="SWEEP_ALREADY_MERGED", value=str(counts.get("already-merged", 0)))
    logging_util.emit_kv(key="SWEEP_WOULD_MERGE", value=str(counts.get("would-merge", 0)))
    logging_util.emit_kv(key="SWEEP_SKIPPED", value=str(counts.get("skipped-not-green", 0)))
    logging_util.emit_kv(key="SWEEP_FAILED", value=str(counts.get("merge-failed", 0)))
    return 1 if counts.get("merge-failed", 0) else 0


def build_sweep_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile open design-log PRs: admin-merge the ones with green required checks",
    )
    _ = parser.add_argument("--repo", default=None)
    _ = parser.add_argument("--dry-run", action="store_true")
    return parser


def sweep_main(argv: list[str] | None = None) -> int:
    parser = build_sweep_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    runner: Runner = proc
    repo_arg = args.repo
    if repo_arg:
        if not gh.validate_repo_slug(repo_arg):
            print("ERROR: invalid --repo; expected OWNER/REPO", file=sys.stderr, flush=True)
            return 2
        repo = repo_arg
    else:
        repo = gh.resolve_repo(runner)
        if not repo:
            print("ERROR: could not resolve repository; pass --repo OWNER/REPO", file=sys.stderr, flush=True)
            return 2

    logging_util.quiet_init(argv0="design-log-ship.py")
    try:
        items = run_design_log_sweep(
            runner,
            repo=repo,
            dry_run=args.dry_run,
        )
    except DesignLogSweepError as exc:
        print(f"ERROR: design-log-sweep failed: {exc}", file=sys.stderr, flush=True)
        return 2
    return _emit_sweep_report(items, dry_run=args.dry_run)


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

    runner: Runner = proc
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
    logging_util.emit_kv(key="PUBLISH_OK", value="true" if result.ok else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
