"""Top-level ship-pr Python driver and CLI."""
# ruff: noqa: E402

from __future__ import annotations

import json
import sys


def _version_supported(version_info: object) -> bool:
    return tuple(version_info) >= (3, 11)  # type: ignore[arg-type]


if not _version_supported(sys.version_info):
    _VERSION_ERROR = "Python ship driver requires Python 3.11 or newer"
    print(
        json.dumps(
            {
                "detail": _VERSION_ERROR,
                "failed_run_id": "",
                "merge_result": "",
                "needs_user_reason": "",
                "outcome": "STALLED",
                "pr_number": None,
                "pr_url": "",
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    print(f"ERROR: {_VERSION_ERROR}", file=sys.stderr)
    raise SystemExit(4)

import argparse
import os
import re
import traceback
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO, cast

import checks
import ci_monitor
import config
import finalize
import gh
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
from errors import NeedsUserInput, PrePushConflictHandoff, ShipError, Stalled, TransientNetworkError
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


@dataclass(frozen=True)
class ResumePlan:
    start: str
    iteration: int
    rebase_count: int
    fix_attempts: int
    transient_retries: int
    pr_number: int | None
    pr_url: str
    merge_result: str
    branch_name: str
    repo: str
    durable: run_logs.DurableFlags
    detail: str = ""


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
        for token in (
            config.NEEDS_USER_CI_FIX_EXHAUSTED,
            config.NEEDS_USER_FIRST_FIXER_NON_HEALTH,
            config.NEEDS_USER_OOS_FILING,
            config.NEEDS_USER_FIX_ATTEMPTS_EXHAUSTED,
            "local-unfixable",
        ):
            if reason == token or reason.startswith((f"{token}:", f"{token}\n")):
                reason = token
                break
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
    if isinstance(exc, ShipError):
        return ShipResult(Outcome.STALLED, detail=str(exc))
    raise exc


def _breadcrumb(step: str, detail: str = "") -> None:
    suffix = f": {detail}" if detail else ""
    logging_util.BreadcrumbWriter().emit(f"ship.py: {step}{suffix}")


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


def oos_observation_count(manifest_path: Path) -> int | None:
    """Return manifest oos_observations length, or None for malformed/OOS-invalid JSON."""
    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    data = cast("dict[str, object]", loaded)
    observations = data.get("oos_observations")
    if isinstance(observations, list):
        return len(cast("list[object]", observations))
    if "oos_observations" in data:
        return None
    return 0


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



def resolve_oos_accepted_design_path(tmpdir: Path) -> Path:
    """Resolve accepted design OOS path in bash checkpoint order."""
    design_tmpdir = os.environ.get("DESIGN_TMPDIR", "")
    if design_tmpdir:
        design_path = Path(design_tmpdir) / "oos-accepted-design.md"
        if design_path.is_file():
            return design_path
    exported = tmpdir / "design-export" / "oos-accepted-design.md"
    if exported.is_file():
        return exported
    return tmpdir / "oos-accepted-design.md"


def _append_execution_tool_failure(
    runner: Runner,
    ctx: RunContext,
    *,
    site: str,
    tool: str,
    exit_code: int,
    output_file: Path,
    cwd: str | None,
) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "append-tool-failure.sh"
    if script.is_file():
        _ = runner.run(
            [
                "bash",
                str(script),
                "--log",
                str(Path(ctx.tmpdir) / "execution-issues.md"),
                "--site",
                site,
                "--tool",
                tool,
                "--exit-code",
                str(exit_code),
                "--category",
                "Tool Failures",
                "--output-file",
                str(output_file),
                "--redact",
            ],
            cwd=cwd,
        )
    log_path = Path(ctx.tmpdir) / "execution-issues.md"
    existing = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
    if tool not in existing:
        bullet = f"- **Step {site}**: {tool} failed with exit {exit_code}; see {output_file}\n"
        if "### Tool Failures\n" in existing:
            updated = existing.rstrip() + "\n" + bullet
        else:
            sep = "" if not existing else "\n"
            updated = existing.rstrip() + sep + "### Tool Failures\n" + bullet
        _ = log_path.write_text(updated, encoding="utf-8")


def _materialize_manifest_oos(runner: Runner, ctx: RunContext, *, cwd: str | None) -> ShipResult | None:
    manifest_path = Path(ctx.manifest_path) if ctx.manifest_path else None
    if manifest_path is None or not manifest_path.is_file():
        return None
    manifest_oos_count = oos_observation_count(manifest_path)
    materialize_failure_blocks = manifest_oos_count is None or manifest_oos_count > 0
    if materialize_failure_blocks:
        _write_ship_state(ctx.with_(oos_pending=True), phase="pr-create")
    script = (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "implement"
        / "scripts"
        / "materialize-manifest-oos.sh"
    )
    result = runner.run(
        [
            "bash",
            str(script),
            "--manifest-path",
            str(manifest_path),
            "--implement-tmpdir",
            ctx.tmpdir,
        ],
        cwd=cwd,
    )
    if result.returncode == 0:
        return None
    stderr_log = Path(ctx.tmpdir) / "materialize-manifest-oos.log"
    _ = stderr_log.write_text(result.stderr or result.stdout, encoding="utf-8")
    _append_execution_tool_failure(
        runner,
        ctx,
        site="pr-create",
        tool="materialize-manifest-oos.sh",
        exit_code=result.returncode,
        output_file=stderr_log,
        cwd=cwd,
    )
    if not materialize_failure_blocks:
        return None
    return ShipResult(
        Outcome.NEEDS_USER_INPUT,
        needs_user_reason=config.NEEDS_USER_OOS_FILING,
        detail=config.NEEDS_USER_OOS_FILING,
    )


def _oos_gate(runner: Runner, ctx: RunContext, *, cwd: str | None) -> ShipResult | None:
    tmpdir = Path(ctx.tmpdir)
    design_path = resolve_oos_accepted_design_path(tmpdir)
    accepted = tuple(
        str(path)
        for path in (
            tmpdir / "oos-accepted-review.md",
            tmpdir / "oos-accepted-main-agent.md",
            design_path,
        )
        if path.is_file()
    )
    created = tmpdir / "oos-issues-created.md"
    run_id = ctx.run_id
    if not run_id:
        session_id = tmpdir / "session-id"
        if session_id.is_file():
            run_id = session_id.read_text(encoding="utf-8").strip()
    run_dir_ndjson = tmpdir / "larch-logs" / "implement" / run_id / "oos-issues.ndjson" if run_id else Path()
    if not run_dir_ndjson.is_file():
        candidates = sorted((tmpdir / "larch-logs" / "implement").glob("*/oos-issues.ndjson"))
        if len(candidates) == 1:
            run_dir_ndjson = candidates[0]
        elif len(candidates) > 1 and not run_id:
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason=config.NEEDS_USER_OOS_FILING,
                detail=config.NEEDS_USER_OOS_FILING,
            )
    commit_messages = ""
    base_remote = "upstream" if ctx.forked or ctx.forked_target else "origin"
    commit_range = f"{base_remote}/main..HEAD"
    merge_base = runner.run(["git", "merge-base", "HEAD", f"{base_remote}/main"], cwd=cwd)
    if merge_base.returncode == 0 and merge_base.stdout.strip():
        commit_range = f"{merge_base.stdout.strip()}..HEAD"
    messages = runner.run(["git", "log", "--format=%B", commit_range], cwd=cwd)
    if messages.returncode == 0:
        commit_messages = messages.stdout
    non_sec = oos.count_non_security(accepted)
    if (
        non_sec > 0
        and not (ctx.forked or ctx.forked_target or ctx.repo_unavailable)
        and not run_dir_ndjson.is_file()
    ):
        _write_ship_state(ctx.with_(oos_pending=True), phase="pr-create")
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason=config.NEEDS_USER_OOS_FILING,
            detail=config.NEEDS_USER_OOS_FILING,
        )
    disposition = oos.disposition_ok(
        runner,
        accepted_files=accepted,
        filed_urls_files=(str(created),) if created.is_file() else (),
        filed_urls_strict_files=(str(design_path),) if design_path.is_file() else (),
        oos_issues_ndjson=str(run_dir_ndjson) if run_dir_ndjson.is_file() else None,
        commit_range_messages=commit_messages,
        forked=ctx.forked or ctx.forked_target,
        repo_unavailable=ctx.repo_unavailable,
    )
    if disposition.ok:
        _write_ship_state(ctx.with_(oos_pending=False), phase="pr-create")
        return None
    _write_ship_state(ctx.with_(oos_pending=True), phase="pr-create")
    return ShipResult(
        Outcome.NEEDS_USER_INPUT,
        needs_user_reason=config.NEEDS_USER_OOS_FILING,
        detail=config.NEEDS_USER_OOS_FILING,
    )


def _pending_oos_gate(runner: Runner, ctx: RunContext, *, cwd: str | None) -> ShipResult | None:
    security_oos = Path(ctx.tmpdir) / "security-oos-observations.md"
    if security_oos.is_file() and security_oos.stat().st_size > 0:
        _write_ship_state(ctx.with_(oos_pending=True), phase="pr-create")
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason=config.NEEDS_USER_OOS_FILING,
            detail=config.NEEDS_USER_OOS_FILING,
        )
    return _oos_gate(runner, ctx, cwd=cwd)


def _postmerge_should_flush(ctx: RunContext) -> bool:
    return bool(
        ctx.run_id
        and ctx.pr_number is not None
        and not ctx.repo_unavailable
        and ctx.pr_closed
    )


def _write_terminal_state(
    ctx: RunContext,
    result: Outcome,
    step: str,
    *,
    iteration: int = 0,
    rebase_count: int = 0,
    fix_attempts: int = 0,
    transient_retries: int = 0,
) -> None:
    finalize.write_finalize_state(
        ctx.with_(stall_tracking=result is Outcome.STALLED, stall_step=step),
        Path(ctx.tmpdir) / "finalize-state.sh",
    )
    _ = step
    phase = "done" if result is Outcome.OK else "stalled"
    _write_ship_state(
        ctx,
        phase=phase,
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
        transient_retries=transient_retries,
    )


def _state_bool(*, value: bool) -> str:
    return "true" if value else "false"


def _write_ship_state(
    ctx: RunContext,
    *,
    phase: str,
    iteration: int = 0,
    rebase_count: int = 0,
    fix_attempts: int = 0,
    transient_retries: int = 0,
    resume_phase: str | None = None,
    caller_kind: str | None = None,
    extra_fields: dict[str, str] | None = None,
) -> None:
    if not ctx.state_file:
        return
    path = Path(ctx.state_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    if resume_phase is None:
        resume_phase = run_logs.read_state_kv(ctx.state_file, "RESUME_PHASE") if path.is_file() else ""
    if caller_kind is None:
        caller_kind = run_logs.read_state_kv(ctx.state_file, "CALLER_KIND") if path.is_file() else ""
    fields = {
        "PHASE": phase,
        "BRANCH_NAME": ctx.branch_name or ctx.branch,
        "ISSUE_NUMBER": ctx.issue_number or ctx.issue,
        "RUN_ID": ctx.run_id,
        "REPO": ctx.repo,
        "REPO_UNAVAILABLE": _state_bool(value=ctx.repo_unavailable),
        "FORKED_TARGET": _state_bool(value=ctx.forked_target or ctx.forked),
        "IMPLEMENT_TMPDIR": ctx.tmpdir,
        "MANIFEST_PATH": ctx.manifest_path,
        "MERGE": _state_bool(value=ctx.merge),
        "DRAFT": _state_bool(value=ctx.draft),
        "PR_CLOSED": _state_bool(value=ctx.pr_closed),
        "PR_NUMBER": "" if ctx.pr_number is None else str(ctx.pr_number),
        "PR_URL": ctx.pr_url,
        "PR_TITLE": ctx.pr_title,
        "MERGE_RESULT": ctx.merge_result,
        "OOS_PENDING": _state_bool(value=ctx.oos_pending),
        "REBASE_COUNT": str(rebase_count),
        "FIX_ATTEMPTS": str(fix_attempts),
        "ITERATION": str(iteration),
        "TRANSIENT_RETRIES": str(transient_retries),
        "RESUME_PHASE": resume_phase,
        "CALLER_KIND": caller_kind,
    }
    if extra_fields:
        fields.update(extra_fields)
    for key, value in fields.items():
        if "\n" in str(value) or "\r" in str(value):
            raise ShipError(f"invalid newline in ship state value: {key}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    _ = tmp.write_text("".join(f"{key}={value}\n" for key, value in fields.items()), encoding="utf-8")
    _ = tmp.replace(path)


def _try_current_branch(runner: Runner, *, cwd: str | None) -> str:
    try:
        return git.current_branch(runner, cwd=cwd)
    except Exception:  # pylint: disable=broad-except
        return ""


def _fresh_resume_plan(
    durable: run_logs.DurableFlags,
    *,
    branch_name: str = "",
    repo: str = "",
    counters: run_logs.ResumeCounters | None = None,
    detail: str = "",
) -> ResumePlan:
    counters = counters or run_logs.ResumeCounters(0, 0, 0, 0)
    return ResumePlan(
        start="fresh",
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        pr_number=None,
        pr_url="",
        merge_result="",
        branch_name=branch_name,
        repo=repo,
        durable=durable,
        detail=detail,
    )


def _resume_from_state(
    start: str,
    counters: run_logs.ResumeCounters,
    durable: run_logs.DurableFlags,
    *,
    pr_number: int | None,
    pr_url: str,
    merge_result: str,
    branch_name: str,
    repo: str,
    detail: str = "",
) -> ResumePlan:
    return ResumePlan(
        start=start,
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        pr_number=pr_number,
        pr_url=pr_url,
        merge_result=merge_result,
        branch_name=branch_name,
        repo=repo,
        durable=durable,
        detail=detail,
    )


def _state_bool_text(value: str) -> bool:
    return value.strip() == "true"


def _valid_merge_result(value: str) -> str:
    return value if value in config.POST_MERGE_MERGE_RESULTS else config.MERGE_RESULT_DRIVER_ALREADY_MERGED


def _resume_plan(ctx: RunContext, runner: Runner, *, cwd: str | None) -> ResumePlan:
    counters = run_logs.read_resume_counters(ctx.state_file)
    durable = run_logs.read_durable_flags(ctx.state_file, ctx)
    if not ctx.state_file or not Path(ctx.state_file).is_file():
        return _fresh_resume_plan(durable, repo=ctx.repo)

    state_phase = run_logs.read_state_kv(ctx.state_file, "PHASE")
    resume_phase = run_logs.read_state_kv(ctx.state_file, "RESUME_PHASE")
    state_branch = run_logs.read_state_kv(ctx.state_file, "BRANCH_NAME").strip()
    state_repo = run_logs.read_state_kv(ctx.state_file, "REPO").strip() or ctx.repo
    pr_url = run_logs.read_state_kv(ctx.state_file, "PR_URL") or ctx.pr_url
    merge_result = run_logs.read_state_kv(ctx.state_file, "MERGE_RESULT")

    if resume_phase == "ship-pr-rrr-phase14":
        return _resume_from_state(
            "blocked-rebase-continuation",
            counters,
            durable,
            pr_number=run_logs.parse_pr_number(ctx.state_file, ctx.pr_number),
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=state_branch or ctx.branch_name or ctx.branch,
            repo=state_repo,
            detail="Python ship driver cannot resume rebase-conflict continuation",
        )

    current_branch = _try_current_branch(runner, cwd=cwd)
    expected_branch = state_branch or ctx.branch_name or ctx.branch
    if not current_branch:
        return _resume_from_state(
            "blocked-checkout-mismatch",
            counters,
            durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=expected_branch,
            repo=state_repo,
            detail=f"cannot verify current checkout branch; expected {expected_branch or '<unknown>'}",
        )
    if expected_branch and current_branch != expected_branch:
        return _resume_from_state(
            "blocked-checkout-mismatch",
            counters,
            durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=expected_branch,
            repo=state_repo,
            detail=f"checkout branch mismatch: expected {expected_branch}, current {current_branch}",
        )
    if current_branch in {"main", "master"} and not durable.forked_target and not durable.forked:
        return _resume_from_state(
            "blocked-checkout-mismatch",
            counters,
            durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=current_branch,
            repo=state_repo,
            detail=f"refusing to resume on protected branch {current_branch}",
        )
    gh_skipped = durable.repo_unavailable or durable.forked or durable.forked_target
    if not expected_branch and gh_skipped:
        return _resume_from_state(
            "blocked-checkout-mismatch",
            counters,
            durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=current_branch,
            repo=state_repo,
            detail="cannot verify gh-skipped resume branch anchor",
        )

    branch_name = current_branch
    pr_number = run_logs.parse_pr_number(ctx.state_file, ctx.pr_number)
    if pr_number is None and not durable.repo_unavailable:
        return _fresh_resume_plan(
            durable,
            branch_name=branch_name,
            repo=state_repo,
            counters=counters,
            detail="missing or invalid PR_NUMBER",
        )

    if not gh_skipped:
        if pr_number is None:
            return _fresh_resume_plan(durable, branch_name=branch_name, repo=state_repo, counters=counters)
        try:
            viewed = gh.pr_view(runner, pr_number, repo=state_repo, cwd=cwd)
        except Exception:  # pylint: disable=broad-except
            return _fresh_resume_plan(
                durable,
                branch_name=branch_name,
                repo=state_repo,
                counters=counters,
                detail="gh pr view failed",
            )
        if viewed.head_ref != branch_name:
            return _fresh_resume_plan(
                durable,
                branch_name=branch_name,
                repo=state_repo,
                counters=counters,
                detail=f"PR head {viewed.head_ref} does not match checkout {branch_name}",
            )
        state = viewed.state.upper()
        if state == "MERGED":
            start = "done" if state_phase == "done" else "merged"
            return _resume_from_state(
                start,
                counters,
                durable,
                pr_number=viewed.number,
                pr_url=viewed.url or pr_url,
                merge_result=_valid_merge_result(merge_result),
                branch_name=branch_name,
                repo=state_repo,
            )
        if state == "OPEN":
            return _resume_from_state(
                "open-pr",
                counters,
                durable,
                pr_number=viewed.number,
                pr_url=viewed.url or pr_url,
                merge_result=merge_result,
                branch_name=branch_name,
                repo=state_repo,
            )
        return _fresh_resume_plan(
            durable,
            branch_name=branch_name,
            repo=state_repo,
            counters=counters,
            detail=f"PR state {viewed.state} is not resumable",
        )

    local_merged = (
        _state_bool_text(run_logs.read_state_kv(ctx.state_file, "PR_CLOSED"))
        or state_phase == "postmerge"
        or merge_result in config.POST_MERGE_MERGE_RESULTS
    )
    if state_phase == "done":
        return _resume_from_state(
            "done",
            counters,
            durable,
            pr_number=pr_number,
            pr_url=pr_url,
            merge_result=_valid_merge_result(merge_result),
            branch_name=branch_name,
            repo=state_repo,
        )
    if local_merged:
        return _resume_from_state(
            "merged",
            counters,
            durable,
            pr_number=pr_number,
            pr_url=pr_url,
            merge_result=_valid_merge_result(merge_result),
            branch_name=branch_name,
            repo=state_repo,
        )
    if pr_number is not None or durable.repo_unavailable:
        return _resume_from_state(
            "open-pr",
            counters,
            durable,
            pr_number=pr_number,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=branch_name,
            repo=state_repo,
        )
    return _fresh_resume_plan(durable, branch_name=branch_name, repo=state_repo, counters=counters)


def _hydrate_resume_context(ctx: RunContext, resume: ResumePlan) -> RunContext:
    return ctx.with_(
        branch=resume.branch_name or ctx.branch,
        branch_name=resume.branch_name or ctx.branch_name or ctx.branch,
        repo=resume.repo or ctx.repo,
        pr_number=resume.pr_number,
        pr_url=resume.pr_url,
        merge_result=resume.merge_result,
        repo_unavailable=resume.durable.repo_unavailable,
        forked_target=resume.durable.forked_target,
        forked=resume.durable.forked,
        merge=resume.durable.merge,
        draft=resume.durable.draft,
        oos_pending=_state_bool_text(run_logs.read_state_kv(ctx.state_file, "OOS_PENDING")),
    )


def _hydrate_fresh_context(ctx: RunContext, resume: ResumePlan) -> RunContext:
    changes: dict[str, object] = {
        "repo": resume.repo or ctx.repo,
        "repo_unavailable": resume.durable.repo_unavailable,
        "forked_target": resume.durable.forked_target,
        "forked": resume.durable.forked,
        "merge": resume.durable.merge,
        "draft": resume.durable.draft,
    }
    if resume.branch_name:
        changes["branch"] = resume.branch_name
        changes["branch_name"] = resume.branch_name
    return ctx.with_(**changes)


def _monitor_persisted_counters(
    *,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
    monitor: ci_monitor.MonitorResult,
) -> tuple[int, int, int, int]:
    return (
        iteration,
        rebase_count,
        fix_attempts,
        transient_retries + (1 if monitor.transient_rerun_attempted else 0),
    )


def _state_file_under_tmpdir(ctx: RunContext) -> bool:
    if not ctx.state_file:
        return True
    try:
        state_path = Path(ctx.state_file).resolve(strict=False)
        tmpdir = Path(ctx.tmpdir).resolve(strict=False)
    except OSError:
        return False
    return state_path == tmpdir or tmpdir in state_path.parents


def _tmpdir_under_allowed_root(tmpdir: str) -> bool:
    if not tmpdir:
        return False
    path = Path(tmpdir)
    if ".." in path.parts:
        return False
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    cache_root = finalize.cache_sessions_root()
    allowed_roots = (
        Path("/tmp").resolve(strict=False),  # noqa: S108 - parity allowlist for session tmpdirs.
        Path("/private/tmp").resolve(strict=False),
        Path("/var/folders").resolve(strict=False),
        Path("/private/var/folders").resolve(strict=False),
        cache_root.resolve(strict=False),
    )
    return any(resolved == root or root in resolved.parents for root in allowed_roots)


def run_postmerge_phase(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> ShipResult:
    sentinel = Path(ctx.tmpdir) / "post-merge-sentinel"
    _ = sentinel.write_text(f"MERGE_RESULT={ctx.merge_result}\n", encoding="utf-8")
    post = finalize.postmerge(runner, ctx, cwd=cwd)
    state_ctx = ctx.with_(
        pr_closed=ctx.pr_closed or post.outcome is Outcome.OK,
        stall_tracking=post.outcome is Outcome.STALLED,
        stall_step=post.status if post.outcome is Outcome.STALLED else ctx.stall_step,
    )
    finalize.write_finalize_state(state_ctx, Path(ctx.tmpdir) / "finalize-state.sh")
    if post.outcome is Outcome.OK and _postmerge_should_flush(state_ctx):
        _ = run_logs.load_or_recover_manifest(state_ctx)
        skip = run_logs.flush_logs_post(state_ctx, merge_result=state_ctx.merge_result, runner=runner)
        if skip.skipped:
            return ShipResult(Outcome.STALLED, detail=f"post-merge flush skipped: {skip.reason}")
    if post.outcome is not Outcome.OK:
        return ShipResult(post.outcome, detail=post.detail or post.status)
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
        if not _tmpdir_under_allowed_root(ctx.tmpdir):
            return ShipResult(Outcome.STALLED, detail="invalid tmpdir")
        if not _state_file_under_tmpdir(ctx):
            return ShipResult(Outcome.STALLED, detail="invalid state_file")
        codex_present = ctx.codex_present or bool(os.environ.get("CODEX") or os.environ.get("CODEX_HOME") or ctx.tool_label == "codex")
        cursor_present = ctx.cursor_present or bool(os.environ.get("CURSOR") or os.environ.get("CURSOR_AUTH_ARGS") or ctx.tool_label == "cursor")
        base_ref = "main"
        resume = _resume_plan(ctx, runner, cwd=repo_root)
        if resume.start == "blocked-rebase-continuation":
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason="unsupported-rebase-continuation",
                detail=resume.detail,
                pr_number=resume.pr_number,
                pr_url=resume.pr_url,
            )
        if resume.start == "blocked-checkout-mismatch":
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason="checkout-mismatch",
                detail=resume.detail,
            )
        if resume.start == "done":
            return ShipResult(
                Outcome.OK,
                pr_number=resume.pr_number,
                pr_url=resume.pr_url,
                merge_result=resume.merge_result,
                detail="already done",
            )
        if resume.start == "merged":
            working = _hydrate_resume_context(ctx, resume).with_(pr_closed=True)
            _write_ship_state(
                working,
                phase="postmerge",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
            _breadcrumb("post-merge")
            post = run_postmerge_phase(runner, working, cwd=repo_root)
            if post.outcome is Outcome.OK:
                _write_ship_state(
                    working,
                    phase="done",
                    iteration=resume.iteration,
                    rebase_count=resume.rebase_count,
                    fix_attempts=resume.fix_attempts,
                    transient_retries=resume.transient_retries,
                )
            return ShipResult(
                post.outcome,
                pr_number=working.pr_number,
                pr_url=working.pr_url,
                merge_result=working.merge_result,
                detail=post.detail,
            )

        if resume.start == "fresh":
            fresh_context = _hydrate_fresh_context(ctx, resume)
            _write_ship_state(
                fresh_context,
                phase="checks",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
            _breadcrumb("checks", "Lint&Tests")
            checks_result = checks.run_checks_phase(
                runner,
                tmpdir=fresh_context.tmpdir,
                repo_root=repo_root,
                codex_present=codex_present,
                cursor_present=cursor_present,
                site="step6",
                checks_site="step6",
                fix_site="ship-pr-ci-initial",
            )
            if checks_result.outcome is not Outcome.OK:
                _write_terminal_state(
                    fresh_context,
                    checks_result.outcome,
                    checks_result.detail or "checks",
                    iteration=resume.iteration,
                    rebase_count=resume.rebase_count,
                    fix_attempts=resume.fix_attempts,
                    transient_retries=resume.transient_retries,
                )
                return _step_result_to_ship(checks_result)

            _write_ship_state(
                fresh_context,
                phase="pr-prep",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
            _breadcrumb("pr-prep", "postbump/Flush+Push")
            postbump = finalize.postbump(runner, fresh_context, cwd=repo_root)
            if postbump.outcome is not Outcome.OK:
                finalize.write_finalize_state(
                    fresh_context.with_(stall_tracking=postbump.outcome is Outcome.STALLED, stall_step=postbump.status),
                    Path(fresh_context.tmpdir) / "finalize-state.sh",
                )
                return ShipResult(postbump.outcome, detail=postbump.detail or postbump.status)

            pr_context = fresh_context
        else:
            pr_context = _hydrate_resume_context(ctx, resume)

        _write_ship_state(
            pr_context,
            phase="pr-create",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        _breadcrumb("pr-create", "PR")
        body = pr_body.compose_pr_body(
            summary=_summary_from_manifest(pr_context),
            mermaid=pr_context.mermaid,
            test_plan=pr_context.test_plan or "- [ ] `make py-lint`\n- [ ] `make py-test`\n",
            issue_number=int(pr_context.issue_number or pr_context.issue) if (pr_context.issue_number or pr_context.issue).isdigit() else None,
        )
        if resume.start == "fresh":
            materialize_result = _materialize_manifest_oos(runner, pr_context, cwd=repo_root)
            if materialize_result is not None:
                return materialize_result
            oos_result = _pending_oos_gate(runner, pr_context, cwd=repo_root)
            if oos_result is not None:
                return oos_result
        elif pr_context.oos_pending or _state_bool_text(run_logs.read_state_kv(pr_context.state_file, "OOS_PENDING")):
            oos_result = _pending_oos_gate(runner, pr_context, cwd=repo_root)
            if oos_result is not None:
                return oos_result

        title = _pr_title(pr_context, runner, cwd=repo_root)
        ensured = pr.ensure_pr(runner, pr_context, body, title=title, cwd=repo_root, base=base_ref)
        working = pr_context.with_(
            pr_number=ensured.number or pr_context.pr_number,
            pr_url=ensured.url or pr_context.pr_url,
            pr_title=title,
            pr_closed=False,
        )
        _write_ship_state(
            working,
            phase="ci-initial" if working.merge and not working.draft else "done",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        if resume.start == "fresh":
            try:
                run_logs.write_final_report_comment(runner, working)
            except ShipError as exc:
                _breadcrumb("warning", str(exc))
        if not working.merge or working.draft or working.forked or working.forked_target or working.repo_unavailable:
            finalize.write_finalize_state(working, Path(working.tmpdir) / "finalize-state.sh")
            _write_ship_state(
                working,
                phase="done",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
            return ShipResult(
                Outcome.OK,
                pr_number=working.pr_number,
                pr_url=working.pr_url,
                detail=ensured.status,
            )

        base_remote = "upstream" if working.forked or working.forked_target else "origin"
        iteration = resume.iteration if resume.start == "open-pr" else 0
        rebase_count = resume.rebase_count if resume.start == "open-pr" else 0
        fix_attempts = resume.fix_attempts if resume.start == "open-pr" else 0
        transient_retries = resume.transient_retries if resume.start == "open-pr" else 0
        while True:
            _write_ship_state(
                working,
                phase="ci-initial",
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
            )
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
                cwd=repo_root,
            )
            if monitor.result.outcome is not Outcome.OK:
                persisted = _monitor_persisted_counters(
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    monitor=monitor,
                )
                _write_terminal_state(
                    working,
                    monitor.result.outcome,
                    monitor.result.detail or "ci-monitor",
                    iteration=persisted[0],
                    rebase_count=persisted[1],
                    fix_attempts=persisted[2],
                    transient_retries=persisted[3],
                )
                return _step_result_to_ship(
                    monitor.result,
                    failed_run_id=monitor.failed_run_id or "",
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                )
            if monitor.action not in {"merge", "already_merged"}:
                if iteration >= config.SHIP_MERGE_LOOP_MAX_ITERATIONS:
                    _write_terminal_state(
                        working,
                        Outcome.STALLED,
                        "merge-loop-iteration-cap",
                        iteration=iteration,
                        rebase_count=rebase_count,
                        fix_attempts=fix_attempts,
                        transient_retries=transient_retries,
                    )
                    return ShipResult(
                        Outcome.STALLED,
                        pr_number=working.pr_number,
                        pr_url=working.pr_url,
                        detail="merge loop iteration cap reached",
                    )
                if monitor.goto_rebase:
                    _write_ship_state(
                        working,
                        phase="rebase",
                        iteration=iteration,
                        rebase_count=rebase_count,
                        fix_attempts=fix_attempts,
                        transient_retries=transient_retries,
                    )
                    _breadcrumb("rebase", "Flush+Push")
                    pre_rebase = run_logs.flush_logs_pre(runner, working.with_(state_file=None), cwd=repo_root)
                    if pre_rebase.skipped and pre_rebase.reason not in config.REFRESH_SKIP_MERGE_OK:
                        _write_terminal_state(
                            working,
                            Outcome.STALLED,
                            "pre-rebase",
                            iteration=iteration,
                            rebase_count=rebase_count,
                            fix_attempts=fix_attempts,
                            transient_retries=transient_retries,
                        )
                        return ShipResult(
                            Outcome.STALLED,
                            detail=f"pre-rebase flush skipped: {pre_rebase.reason}",
                        )
                    try:
                        _ = rebase.rebase_and_push(
                            runner,
                            repo=working.repo,
                            run_id=working.run_id,
                            cwd=repo_root,
                            tmpdir=working.tmpdir,
                            base_remote=base_remote,
                            base_ref=base_ref,
                            allow_conflict_fix=True,
                            enable_pre_push_handoff=True,
                        )
                    except PrePushConflictHandoff as exc:
                        _write_ship_state(
                            working,
                            phase="rebase",
                            iteration=iteration,
                            rebase_count=rebase_count,
                            fix_attempts=fix_attempts,
                            transient_retries=transient_retries,
                            resume_phase=exc.resume_phase,
                            caller_kind=exc.caller_kind,
                            extra_fields={"CONFLICT_FILES": exc.conflict_csv},
                        )
                        raise
                    rebase_count += 1
                if monitor.transient_rerun_attempted:
                    transient_retries += 1
                if monitor.did_fixing:
                    fix_attempts += 1
                if (
                    monitor.action == "wait"
                    or monitor.goto_rebase
                    or monitor.did_fixing
                    or monitor.transient_rerun_attempted
                ):
                    iteration += 1
                _write_ship_state(
                    working,
                    phase="ci-initial",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                continue

            _breadcrumb("merge")
            merged = merge.merge_pr(runner, working, cwd=repo_root, post_flush=False)
            if merged.result in {config.MERGE_RESULT_CI_NOT_READY, config.MERGE_RESULT_MAIN_ADVANCED}:
                iteration += 1
                _write_ship_state(
                    working,
                    phase="ci-initial",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                continue
            pr_closed = merged.result in config.POST_MERGE_MERGE_RESULTS
            working = working.with_(
                merge_result=merged.result,
                pr_closed=pr_closed,
            )
            _write_ship_state(
                working,
                phase="postmerge" if pr_closed else "merge",
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
            )
            if merged.result == config.MERGE_RESULT_ERROR:
                finalize.write_finalize_state(
                    working.with_(stall_tracking=True, stall_step="merge"),
                    Path(working.tmpdir) / "finalize-state.sh",
                )
                return ShipResult(
                    Outcome.STALLED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    merge_result=merged.result,
                    detail=merged.error,
                )
            if merged.result not in config.POST_MERGE_MERGE_RESULTS:
                finalize.write_finalize_state(
                    working.with_(stall_tracking=True, stall_step="merge"),
                    Path(working.tmpdir) / "finalize-state.sh",
                )
                return ShipResult(
                    Outcome.STALLED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    merge_result=merged.result,
                    detail=merged.error or f"merge did not complete: {merged.result}",
                )
            _breadcrumb("post-merge")
            post = run_postmerge_phase(runner, working, cwd=repo_root)
            if post.outcome is Outcome.OK:
                _write_ship_state(
                    working,
                    phase="done",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
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


def _close_contract_stream(stream: TextIO) -> None:
    if stream is not sys.stdout:
        with suppress(Exception):
            stream.close()


def emit_result(ctx: RunContext, result: ShipResult) -> None:
    payload = _redacted_result_payload(result)
    stream = logging_util.contract_stream()
    try:
        print(json.dumps(payload, sort_keys=True), file=stream)
        stream.flush()
    finally:
        _close_contract_stream(stream)
    if ctx.run_id and _tmpdir_under_allowed_root(ctx.tmpdir):
        try:
            journal = logging_util.JsonlJournal(_journal_path(ctx), ctx.run_id)
            _ = journal.append(config.JOURNAL_EVENT_SHIP_RESULT, **payload)
        except OSError as exc:
            logging_util.BreadcrumbWriter().emit(f"ship.py: journal append skipped: {exc}")


def _redacted_result_payload(result: ShipResult) -> dict[str, Any]:
    payload = result.to_json_dict()
    for key in ("needs_user_reason", "failed_run_id", "pr_url", "merge_result", "detail"):
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
    _ = parser.add_argument("--state-file")
    _ = parser.add_argument("--tool-label")
    _ = parser.add_argument("--merge")
    _ = parser.add_argument("--draft")
    _ = parser.add_argument("--forked")
    _ = parser.add_argument("--repo-unavailable")
    _ = parser.add_argument("--no-admin-fallback")
    _ = parser.add_argument("--no-logs-commit", nargs="?", const="true", default=None)
    _ = parser.add_argument("--expected-session-id")
    _ = parser.add_argument("--expected-tmpdir-basename-prefix")
    return parser


def _state_file_kv(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    try:
        return finalize.read_finalize_state(path)
    except ShipError:
        return {}


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _first_present(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, int):
            if value != 0:
                return str(value)
            continue
        text = str(value)
        if text:
            return text
    return ""


def _slug_from_detail(detail: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", detail.strip().lower()).strip("-")
    return slug[:80] or "stalled"


def _fill_if_empty(data: dict[str, str], key: str, *values: object) -> None:
    if data.get(key):
        return
    value = _first_present(*values)
    if value:
        data[key] = value


def _persist_stall_metadata_if_needed(ctx: RunContext, result: ShipResult, tmpdir: Path) -> None:
    if result.outcome is not Outcome.STALLED:
        return
    if not _tmpdir_under_allowed_root(str(tmpdir)):
        return
    path = tmpdir / "finalize-state.sh"
    try:
        data = finalize.read_finalize_state(path)
        if _truthy(data.get("STALL_TRACKING", "")):
            return
        state = _state_file_kv(ctx.state_file)
        _fill_if_empty(data, "BRANCH_NAME", state.get("BRANCH_NAME"), ctx.branch)
        _fill_if_empty(data, "ISSUE_NUMBER", state.get("ISSUE_NUMBER"), ctx.issue_number, ctx.issue)
        _fill_if_empty(data, "REPO", state.get("REPO"), ctx.repo)
        _fill_if_empty(data, "RUN_ID", state.get("RUN_ID"), ctx.run_id)
        _fill_if_empty(data, "PR_NUMBER", result.pr_number, state.get("PR_NUMBER"), ctx.pr_number)
        _fill_if_empty(data, "PR_URL", result.pr_url, state.get("PR_URL"), ctx.pr_url)
        _fill_if_empty(data, "PR_TITLE", state.get("PR_TITLE"), ctx.pr_title)
        _fill_if_empty(data, "MERGE_RESULT", result.merge_result, state.get("MERGE_RESULT"), ctx.merge_result)
        _fill_if_empty(data, "FORKED_TARGET", state.get("FORKED_TARGET"), "true" if ctx.forked else "false")
        _fill_if_empty(data, "REPO_UNAVAILABLE", state.get("REPO_UNAVAILABLE"), "true" if ctx.repo_unavailable else "false")
        _fill_if_empty(data, "DRAFT", state.get("DRAFT"), "true" if ctx.draft else "false")
        _fill_if_empty(data, "MERGE", state.get("MERGE"), "true" if ctx.merge else "false")
        data["STALL_TRACKING"] = "true"
        _fill_if_empty(data, "STALL_STEP", state.get("STALL_STEP"), ctx.stall_step, _slug_from_detail(result.detail))
        finalize.write_finalize_state_merged(path, data)
    except Exception as exc:
        with suppress(Exception):
            logging_util.BreadcrumbWriter().emit(f"ship.py: stall metadata gap-fill skipped: {exc}")


def _ctx_from_args(args: argparse.Namespace) -> RunContext:
    env_ctx = RunContext.from_env()
    changes: dict[str, object] = {}
    for arg_name, field_name in (
        ("branch", "branch"),
        ("issue", "issue"),
        ("issue", "issue_number"),
        ("repo", "repo"),
        ("run_id", "run_id"),
        ("tmpdir", "tmpdir"),
        ("manifest_path", "manifest_path"),
        ("state_file", "state_file"),
        ("tool_label", "tool_label"),
        ("expected_session_id", "expected_session_id"),
        ("expected_tmpdir_basename_prefix", "expected_tmpdir_basename_prefix"),
    ):
        value = getattr(args, arg_name)
        if value not in (None, ""):
            changes[field_name] = value
    for arg_name, field_name in (
        ("merge", "merge"),
        ("draft", "draft"),
        ("forked", "forked"),
        ("repo_unavailable", "repo_unavailable"),
        ("no_admin_fallback", "no_admin_fallback"),
    ):
        value = getattr(args, arg_name)
        if value is not None:
            changes[field_name] = str(value).strip().lower() in {"1", "true", "yes", "on"}
    if args.no_logs_commit is not None:
        changes["no_logs_commit"] = str(args.no_logs_commit).strip().lower() in {"1", "true", "yes", "on"}
    return env_ctx.with_(**changes)


def main(argv: list[str] | None = None) -> int:
    ctx = RunContext.from_env(env={})
    result: ShipResult
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code == 0:
            return 0
        result = ShipResult(Outcome.INTERNAL_ERROR, detail=f"argparse failed with exit {code}")
        with suppress(Exception):
            emit_result(ctx, result)
        return config.OUTCOME_EXIT_MAP[Outcome.INTERNAL_ERROR]
    try:
        ctx = _ctx_from_args(args)
        if _tmpdir_under_allowed_root(ctx.tmpdir):
            os.environ[config.ENV_IMPLEMENT_TMPDIR] = ctx.tmpdir
            logging_util.quiet_init(argv0="ship.py")
        result = run_ship(ctx, runner=proc, cwd=str(Path.cwd()))
    except Exception as exc:  # top-level contract envelope
        logging_util.BreadcrumbWriter().emit(
            f"ship.py: internal error\n{traceback.format_exc()}",
        )
        result = ShipResult(Outcome.INTERNAL_ERROR, detail=f"{type(exc).__name__}: {exc}")
    try:
        _persist_stall_metadata_if_needed(ctx, result, Path(ctx.tmpdir))
    except Exception as exc:
        with suppress(Exception):
            logging_util.BreadcrumbWriter().emit(f"ship.py: stall metadata gap-fill skipped: {exc}")
    emit_result(ctx, result)
    return config.OUTCOME_EXIT_MAP[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
