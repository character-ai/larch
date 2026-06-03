"""Top-level ship-pr Python driver and CLI."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import checks
import ci_monitor
import config
import finalize
import git
import logging_util
import merge
import oos
import pr
import pr_body
import proc
import rebase
import run_logs
from errors import NeedsUserInput, ShipError, Stalled, TransientNetworkError
from outcomes import Outcome, StepResult
from proc import Runner
from run_context import RunContext


@dataclass(frozen=True)
class ShipResult:
    outcome: Outcome
    needs_user_reason: str = ""
    failed_run_id: str = ""
    pr_number: int | None = None
    pr_url: str = ""
    merge_result: str = ""
    detail: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "needs_user_reason": self.needs_user_reason,
            "failed_run_id": self.failed_run_id,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "merge_result": self.merge_result,
            "detail": self.detail,
        }


def _step_result_to_ship(
    step: StepResult,
    *,
    failed_run_id: str = "",
    pr_number: int | None = None,
    pr_url: str = "",
    merge_result: str = "",
) -> ShipResult:
    reason = ""
    detail = step.detail
    if step.outcome is Outcome.NEEDS_USER_INPUT:
        reason = detail or "needs-user-input"
        if reason.startswith(config.NEEDS_USER_CI_FIX_EXHAUSTED):
            reason = config.NEEDS_USER_CI_FIX_EXHAUSTED
    return ShipResult(
        step.outcome,
        needs_user_reason=reason,
        failed_run_id=failed_run_id,
        pr_number=pr_number,
        pr_url=pr_url,
        merge_result=merge_result,
        detail=detail,
    )


def _error_to_result(exc: Exception) -> ShipResult:
    if isinstance(exc, TransientNetworkError):
        return ShipResult(Outcome.TRANSIENT, detail=str(exc))
    if isinstance(exc, NeedsUserInput):
        return ShipResult(Outcome.NEEDS_USER_INPUT, needs_user_reason=str(exc), detail=str(exc))
    if isinstance(exc, Stalled):
        return ShipResult(Outcome.STALLED, detail=str(exc))
    return ShipResult(Outcome.STALLED, detail=str(exc))


def _summary_from_manifest(ctx: RunContext) -> str:
    if ctx.summary:
        return ctx.summary
    manifest_path = Path(ctx.manifest_path)
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            data = cast("dict[str, object]", loaded)
            bullets_obj = data.get("summary_bullets")
            if isinstance(bullets_obj, list) and bullets_obj:
                bullets = [item for item in cast("list[object]", bullets_obj) if isinstance(item, str)]
                return "\n".join(f"- {item}" for item in bullets) + "\n"
    return "- Implement requested changes.\n"


def _pr_title(ctx: RunContext, runner: Runner, *, cwd: str | None) -> str:
    if ctx.pr_title:
        return ctx.pr_title
    subject = git.log_subject(runner, "HEAD", cwd=cwd)
    return subject or f"Implement issue #{ctx.issue_number or ctx.issue}"


def _oos_gate(runner: Runner, ctx: RunContext) -> ShipResult | None:
    tmpdir = Path(ctx.tmpdir)
    accepted = tuple(
        str(path)
        for path in (
            tmpdir / "oos-accepted-review.md",
            tmpdir / "oos-accepted-main-agent.md",
            tmpdir / "oos-accepted-design.md",
        )
        if path.is_file()
    )
    created = tmpdir / "oos-issues-created.md"
    disposition = oos.disposition_ok(
        runner,
        accepted_files=accepted,
        filed_urls_files=(str(created),) if created.is_file() else (),
        forked=ctx.forked or ctx.forked_target,
        repo_unavailable=ctx.repo_unavailable,
    )
    if disposition.ok:
        return None
    return ShipResult(
        Outcome.NEEDS_USER_INPUT,
        needs_user_reason=config.NEEDS_USER_OOS_FILING,
        detail=config.NEEDS_USER_OOS_FILING,
    )


def _postmerge_should_flush(ctx: RunContext) -> bool:
    return bool(
        ctx.run_id
        and ctx.pr_number is not None
        and not ctx.repo_unavailable
        and ctx.pr_closed
    )


def run_postmerge_phase(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> ShipResult:
    post = finalize.postmerge(runner, ctx, cwd=cwd)
    if post.outcome is not Outcome.OK:
        return ShipResult(post.outcome, detail=post.detail or post.status)
    if _postmerge_should_flush(ctx):
        _ = run_logs.load_or_recover_manifest(ctx)
        skip = run_logs.flush_logs_post(ctx, merge_result=ctx.merge_result, runner=runner)
        if skip.skipped:
            return ShipResult(Outcome.STALLED, detail=f"post-merge flush skipped: {skip.reason}")
    finalize.write_finalize_state(ctx, Path(ctx.tmpdir) / "finalize-state.sh")
    return ShipResult(
        Outcome.OK,
        pr_number=ctx.pr_number,
        pr_url=ctx.pr_url,
        merge_result=ctx.merge_result,
    )


def run_ship(
    ctx: RunContext,
    *,
    runner: Runner = proc,
    cwd: str | None = None,
) -> ShipResult:
    try:
        repo_root = cwd or str(Path.cwd())
        checks_result = checks.run_checks_phase(
            runner,
            tmpdir=ctx.tmpdir,
            repo_root=repo_root,
            codex_present=True,
            cursor_present=True,
            site="step6",
            checks_site="step6",
            fix_site="ship-pr-ci-initial",
        )
        if checks_result.outcome is not Outcome.OK:
            return _step_result_to_ship(checks_result)

        postbump = finalize.postbump(runner, ctx, cwd=cwd)
        if postbump.outcome is not Outcome.OK:
            return ShipResult(postbump.outcome, detail=postbump.detail or postbump.status)

        body = pr_body.compose_pr_body(
            summary=_summary_from_manifest(ctx),
            mermaid=ctx.mermaid,
            test_plan=ctx.test_plan or "- [ ] `make py-lint`\n- [ ] `make py-test`\n",
            issue_number=int(ctx.issue_number or ctx.issue) if (ctx.issue_number or ctx.issue).isdigit() else None,
        )
        oos_result = _oos_gate(runner, ctx)
        if oos_result is not None:
            return oos_result

        pre = run_logs.flush_logs_pre(runner, ctx.with_(state_file=None), cwd=repo_root)
        if pre.skipped and pre.reason not in config.REFRESH_SKIP_MERGE_OK:
            return ShipResult(Outcome.STALLED, detail=f"pre-push flush skipped: {pre.reason}")

        title = _pr_title(ctx, runner, cwd=cwd)
        ensured = pr.ensure_pr(runner, ctx, body, title=title, cwd=cwd)
        working = ctx.with_(
            pr_number=ensured.number or None,
            pr_url=ensured.url,
            pr_closed=False,
        )
        if not working.merge or working.draft or working.forked or working.repo_unavailable:
            finalize.write_finalize_state(working, Path(working.tmpdir) / "finalize-state.sh")
            return ShipResult(
                Outcome.OK,
                pr_number=working.pr_number,
                pr_url=working.pr_url,
                detail=ensured.status,
            )

        iteration = 0
        rebase_count = 0
        fix_attempts = 0
        transient_retries = 0
        while True:
            monitor = ci_monitor.monitor(
                runner,
                pr=working.pr_number or 0,
                repo=working.repo,
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
                plan_file=working.plan_file or None,
                cwd=cwd,
            )
            if monitor.result.outcome is not Outcome.OK:
                return _step_result_to_ship(
                    monitor.result,
                    failed_run_id=monitor.failed_run_id or "",
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                )
            if monitor.action in {"merge", "already_merged"}:
                break
            if monitor.goto_rebase:
                _ = rebase.rebase_and_push(
                    runner,
                    repo=working.repo,
                    run_id=working.run_id,
                    cwd=cwd,
                    tmpdir=working.tmpdir,
                )
                rebase_count += 1
            if monitor.did_fixing:
                fix_attempts += 1
            iteration += 1

        merged = merge.merge_pr(runner, working, cwd=cwd, post_flush=False)
        pr_closed = merged.result in config.POST_MERGE_MERGE_RESULTS
        working = working.with_(
            merge_result=merged.result,
            pr_closed=pr_closed,
        )
        if merged.result == config.MERGE_RESULT_ERROR:
            finalize.write_finalize_state(working, Path(working.tmpdir) / "finalize-state.sh")
            return ShipResult(
                Outcome.STALLED,
                pr_number=working.pr_number,
                pr_url=working.pr_url,
                merge_result=merged.result,
                detail=merged.error,
            )
        post = run_postmerge_phase(runner, working, cwd=cwd)
        return ShipResult(
            post.outcome,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            merge_result=working.merge_result,
            detail=post.detail,
        )
    except (NeedsUserInput, ShipError, Stalled, TransientNetworkError) as exc:
        return _error_to_result(exc)


def _journal_path(ctx: RunContext) -> Path:
    return Path(
        config.PATH_JSONL_JOURNAL_TEMPLATE.format(
            tmpdir=ctx.tmpdir or ".",
            run_id=ctx.run_id or "unknown",
        ),
    )


def emit_result(ctx: RunContext, result: ShipResult) -> None:
    payload = result.to_json_dict()
    if ctx.run_id:
        journal = logging_util.JsonlJournal(_journal_path(ctx), ctx.run_id)
        _ = journal.append(config.JOURNAL_EVENT_SHIP_RESULT, **payload)
    print(json.dumps(payload, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Python ship-pr driver")
    _ = parser.add_argument("--branch", default=os.environ.get("BRANCH_NAME", ""))
    _ = parser.add_argument("--issue", default=os.environ.get("ISSUE_NUMBER", ""))
    _ = parser.add_argument("--repo", default=os.environ.get("REPO", ""))
    _ = parser.add_argument("--run-id", default=os.environ.get("RUN_ID", ""))
    _ = parser.add_argument("--tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
    _ = parser.add_argument("--manifest-path", default=os.environ.get("MANIFEST_PATH", ""))
    _ = parser.add_argument("--tool-label", default=os.environ.get("TOOL_LABEL", "codex"))
    _ = parser.add_argument("--merge", default=os.environ.get("MERGE", "true"))
    _ = parser.add_argument("--draft", default=os.environ.get("DRAFT", "false"))
    _ = parser.add_argument("--forked", default=os.environ.get("FORKED_TARGET", "false"))
    _ = parser.add_argument("--repo-unavailable", default=os.environ.get("REPO_UNAVAILABLE", "false"))
    _ = parser.add_argument("--no-admin-fallback", default=os.environ.get("NO_ADMIN_FALLBACK", "false"))
    return parser


def _ctx_from_args(args: argparse.Namespace) -> RunContext:
    env_ctx = RunContext.from_env()
    return env_ctx.with_(
        branch=args.branch,
        branch_name=args.branch,
        issue=args.issue,
        issue_number=args.issue,
        repo=args.repo,
        run_id=args.run_id,
        tmpdir=args.tmpdir,
        manifest_path=args.manifest_path,
        tool_label=args.tool_label,
        merge=str(args.merge).lower() == "true",
        draft=str(args.draft).lower() == "true",
        forked=str(args.forked).lower() == "true",
        forked_target=str(args.forked).lower() == "true",
        repo_unavailable=str(args.repo_unavailable).lower() == "true",
        no_admin_fallback=str(args.no_admin_fallback).lower() == "true",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ctx = _ctx_from_args(args)
    result = run_ship(ctx, runner=proc, cwd=str(Path.cwd()))
    emit_result(ctx, result)
    return config.OUTCOME_EXIT_MAP[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
