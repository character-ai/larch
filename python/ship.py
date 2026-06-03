"""Top-level ship-pr Python driver and CLI."""

from __future__ import annotations

import argparse
import contextlib
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
import redact
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
    issue = ctx.issue_number or ctx.issue
    prefix = f"Fixes #{issue}: " if issue and str(issue).isdigit() else ""
    if ctx.pr_title:
        title = ctx.pr_title
        return title if not prefix or title.startswith(prefix) else f"{prefix}{title}"
    subject = git.log_subject(runner, "HEAD", cwd=cwd)
    if subject.startswith(config.FLUSH_COMMIT_SUBJECT_PREFIX):
        subject = ""
    title = subject or f"Implement issue #{issue or ctx.issue}"
    return title if not prefix or title.startswith(prefix) else f"{prefix}{title}"


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
    run_dir_ndjson = tmpdir / "larch-logs" / "implement" / ctx.run_id / "oos-issues.ndjson"
    commit_messages = ""
    if ctx.run_id:
        messages = runner.run(["git", "log", "--format=%s", "origin/main..HEAD"], cwd=None)
        if messages.returncode == 0:
            commit_messages = messages.stdout
    disposition = oos.disposition_ok(
        runner,
        accepted_files=accepted,
        filed_urls_files=(str(created),) if created.is_file() else (),
        oos_issues_ndjson=str(run_dir_ndjson) if run_dir_ndjson.is_file() else None,
        commit_range_messages=commit_messages,
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


def _write_terminal_state(ctx: RunContext, result: Outcome, step: str) -> None:
    finalize.write_finalize_state(
        ctx.with_(stall_tracking=result is Outcome.STALLED, stall_step=step),
        Path(ctx.tmpdir) / "finalize-state.sh",
    )


def run_postmerge_phase(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> ShipResult:
    state_ctx = ctx.with_(pr_closed=True)
    finalize.write_finalize_state(state_ctx, Path(ctx.tmpdir) / "finalize-state.sh")
    sentinel = Path(ctx.tmpdir) / "post-merge-sentinel"
    _ = sentinel.write_text(f"MERGE_RESULT={ctx.merge_result}\n", encoding="utf-8")
    post = finalize.postmerge(runner, ctx, cwd=cwd)
    if post.outcome is not Outcome.OK:
        return ShipResult(post.outcome, detail=post.detail or post.status)
    if _postmerge_should_flush(ctx):
        _ = run_logs.load_or_recover_manifest(ctx)
        skip = run_logs.flush_logs_post(ctx, merge_result=ctx.merge_result, runner=runner)
        if skip.skipped:
            return ShipResult(Outcome.STALLED, detail=f"post-merge flush skipped: {skip.reason}")
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
        codex_present = bool(os.environ.get("CODEX") or os.environ.get("CODEX_HOME") or ctx.tool_label == "codex")
        cursor_present = bool(os.environ.get("CURSOR") or os.environ.get("CURSOR_AUTH_ARGS") or ctx.tool_label == "cursor")
        base_remote = "upstream" if ctx.forked or ctx.forked_target else "origin"
        base_ref = "main"
        checks_result = checks.run_checks_phase(
            runner,
            tmpdir=ctx.tmpdir,
            repo_root=repo_root,
            codex_present=codex_present,
            cursor_present=cursor_present,
            site="step6",
            checks_site="step6",
            fix_site="ship-pr-ci-initial",
        )
        if checks_result.outcome is not Outcome.OK:
            _write_terminal_state(ctx, checks_result.outcome, checks_result.detail or "checks")
            return _step_result_to_ship(checks_result)

        postbump = finalize.postbump(runner, ctx, cwd=repo_root)
        if postbump.outcome is not Outcome.OK:
            finalize.write_finalize_state(
                ctx.with_(stall_tracking=postbump.outcome is Outcome.STALLED, stall_step=postbump.status),
                Path(ctx.tmpdir) / "finalize-state.sh",
            )
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
            _write_terminal_state(ctx, Outcome.STALLED, "pre-push")
            return ShipResult(Outcome.STALLED, detail=f"pre-push flush skipped: {pre.reason}")

        title = _pr_title(ctx, runner, cwd=cwd)
        ensured = pr.ensure_pr(runner, ctx, body, title=title, cwd=cwd)
        working = ctx.with_(
            pr_number=ensured.number or None,
            pr_url=ensured.url,
            pr_title=title,
            pr_closed=False,
        )
        with contextlib.suppress(ShipError):
            run_logs.write_final_report_comment(runner, working)
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
                base_remote=base_remote,
                base_ref=base_ref,
                plan_file=working.plan_file or None,
                cwd=cwd,
            )
            if monitor.result.outcome is not Outcome.OK:
                _write_terminal_state(
                    working,
                    monitor.result.outcome,
                    monitor.result.detail or "ci-monitor",
                )
                return _step_result_to_ship(
                    monitor.result,
                    failed_run_id=monitor.failed_run_id or "",
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                )
            if monitor.action not in {"merge", "already_merged"}:
                if monitor.goto_rebase:
                    pre_rebase = run_logs.flush_logs_pre(runner, working.with_(state_file=None), cwd=repo_root)
                    if pre_rebase.skipped and pre_rebase.reason not in config.REFRESH_SKIP_MERGE_OK:
                        _write_terminal_state(working, Outcome.STALLED, "pre-rebase")
                        return ShipResult(
                            Outcome.STALLED,
                            detail=f"pre-rebase flush skipped: {pre_rebase.reason}",
                        )
                    _ = rebase.rebase_and_push(
                        runner,
                        repo=working.repo,
                        run_id=working.run_id,
                        cwd=repo_root,
                        tmpdir=working.tmpdir,
                        base_remote=base_remote,
                        base_ref=base_ref,
                    )
                    rebase_count += 1
                if monitor.transient_rerun_attempted:
                    transient_retries += 1
                if monitor.did_fixing:
                    fix_attempts += 1
                iteration += 1
                continue

            merged = merge.merge_pr(runner, working, cwd=cwd, post_flush=False)
            if merged.result in {config.MERGE_RESULT_CI_NOT_READY, config.MERGE_RESULT_MAIN_ADVANCED}:
                iteration += 1
                continue
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
            if merged.result not in config.POST_MERGE_MERGE_RESULTS:
                finalize.write_finalize_state(working, Path(working.tmpdir) / "finalize-state.sh")
                return ShipResult(
                    Outcome.STALLED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    merge_result=merged.result,
                    detail=merged.error or f"merge did not complete: {merged.result}",
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
    payload = _redacted_result_payload(result)
    if ctx.run_id:
        journal = logging_util.JsonlJournal(_journal_path(ctx), ctx.run_id)
        _ = journal.append(config.JOURNAL_EVENT_SHIP_RESULT, **payload)
    print(json.dumps(payload, sort_keys=True))


def _redacted_result_payload(result: ShipResult) -> dict[str, Any]:
    payload = result.to_json_dict()
    for key in ("needs_user_reason", "failed_run_id", "merge_result", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            redacted = redact.redact_outbound(value)
            payload[key] = "redacted" if "[content truncated" in redacted else redacted
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Python ship-pr driver")
    _ = parser.add_argument("--branch")
    _ = parser.add_argument("--issue")
    _ = parser.add_argument("--repo")
    _ = parser.add_argument("--run-id")
    _ = parser.add_argument("--tmpdir")
    _ = parser.add_argument("--manifest-path")
    _ = parser.add_argument("--tool-label")
    _ = parser.add_argument("--merge")
    _ = parser.add_argument("--draft")
    _ = parser.add_argument("--forked")
    _ = parser.add_argument("--repo-unavailable")
    _ = parser.add_argument("--no-admin-fallback")
    _ = parser.add_argument("--no-logs-commit", action="store_true", default=None)
    return parser


def _ctx_from_args(args: argparse.Namespace) -> RunContext:
    env_ctx = RunContext.from_env()
    changes: dict[str, object] = {}
    for arg_name, field_name in (
        ("branch", "branch"),
        ("branch", "branch_name"),
        ("issue", "issue"),
        ("issue", "issue_number"),
        ("repo", "repo"),
        ("run_id", "run_id"),
        ("tmpdir", "tmpdir"),
        ("manifest_path", "manifest_path"),
        ("tool_label", "tool_label"),
    ):
        value = getattr(args, arg_name)
        if value not in (None, ""):
            changes[field_name] = value
    for arg_name, field_name in (
        ("merge", "merge"),
        ("draft", "draft"),
        ("forked", "forked"),
        ("forked", "forked_target"),
        ("repo_unavailable", "repo_unavailable"),
        ("no_admin_fallback", "no_admin_fallback"),
    ):
        value = getattr(args, arg_name)
        if value is not None:
            changes[field_name] = str(value).strip().lower() in {"1", "true", "yes", "on"}
    if args.no_logs_commit is True:
        changes["no_logs_commit"] = True
    return env_ctx.with_(**changes)


def main(argv: list[str] | None = None) -> int:
    ctx = RunContext.from_env()
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        ctx = _ctx_from_args(args)
        result = run_ship(ctx, runner=proc, cwd=str(Path.cwd()))
    except Exception as exc:
        result = _error_to_result(exc)
    emit_result(ctx, result)
    return config.OUTCOME_EXIT_MAP[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
