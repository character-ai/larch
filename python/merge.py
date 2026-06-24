# pyright: reportUnusedCallResult=false
"""PR merge orchestration (parity with merge pr)."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

import argparse
import tempfile
import config
import gh
import git
import logging_util
import redact
import run_logs
from errors import ShipError
from proc import Runner
from retry import with_transient_retry
from run_context import RunContext
import proc

@dataclass(frozen=True)
class MergeResult:
    result: str
    error: str = ""


_BUMP_SUBJECT_RE = re.compile(r"^Bump version to ([0-9]+\.[0-9]+\.[0-9]+)$")
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_MERGE_CONFLICT_SIGNALS = (
    "merge conflicts",
    "cannot be cleanly created",
)


def redact_merge_diagnostic(text: str) -> str:
    """Port merge pr redact_merge_diagnostic."""
    if not text:
        return ""
    redacted = redact.redact_outbound(text)
    if "[content truncated" in redacted:
        return "merge diagnostic redaction unavailable"
    one_line = redacted.replace("\n", " ")
    return one_line[: config.MERGE_DIAGNOSTIC_MAX_LEN]


def _has_merge_conflict_signal(error: str | None) -> bool:
    lowered = (error or "").lower()
    return any(signal in lowered for signal in _MERGE_CONFLICT_SIGNALS)


def merge_pr(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str | None = None,
    sleeper: Callable[[float], None] | None = None,
    post_flush: bool = True,
) -> MergeResult:
    """Classify merge into one of eight merge pr MERGE_RESULT literals."""
    if sleeper is None:
        sleeper = time.sleep
    if not ctx.merge:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=config.MERGE_SKIP_NOT_REQUESTED,
        )
    if ctx.draft:
        return MergeResult(result=config.MERGE_RESULT_ERROR, error=config.MERGE_SKIP_DRAFT)
    if ctx.forked:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=config.MERGE_SKIP_FORKED,
        )
    if ctx.repo_unavailable:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=config.MERGE_SKIP_REPO_UNAVAILABLE,
        )
    if ctx.pr_number is None:
        return MergeResult(result=config.MERGE_RESULT_ERROR, error="pr_number required")

    terminal = _merge_noop_if_pr_closed(runner=runner, ctx=ctx, cwd=cwd, post_flush=post_flush)
    if terminal is not None:
        return terminal

    pr_num = ctx.pr_number
    state = _refresh_pr_info(runner=runner, pr_num=pr_num, repo=ctx.repo, cwd=cwd)
    if not state.merge_state_status or state.merge_state_status == "UNKNOWN":
        state = _retry_unknown(
            runner=runner,
            pr_num=pr_num,
            repo=ctx.repo,
            max_retries=config.MERGE_PR_INITIAL_UNKNOWN_RETRIES,
            sleeper=sleeper,
            cwd=cwd,
        )
    if not state.merge_state_status or state.merge_state_status == "UNKNOWN":
        post_err = _post_flush(runner=runner, ctx=ctx, merge_result=config.MERGE_RESULT_ERROR) if post_flush else None
        if post_err is not None:
            return post_err
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=(
                "could not read mergeStateStatus from gh pr view "
                f"after {config.MERGE_PR_INITIAL_UNKNOWN_RETRIES} retries"
            ),
        )

    if not gh.pr_checks_all_pass(runner, pr_num, repo=ctx.repo, cwd=cwd):
        post_err = _post_flush(runner=runner, ctx=ctx, merge_result=config.MERGE_RESULT_CI_NOT_READY) if post_flush else None
        if post_err is not None:
            return post_err
        return MergeResult(
            result=config.MERGE_RESULT_CI_NOT_READY,
            error="CI checks are not all passing",
        )

    if state.merge_state_status not in config.ADMIN_ELIGIBLE_MERGE_STATES:
        post_err = _post_flush(runner=runner, ctx=ctx, merge_result=config.MERGE_RESULT_MAIN_ADVANCED) if post_flush else None
        if post_err is not None:
            return post_err
        return MergeResult(
            result=config.MERGE_RESULT_MAIN_ADVANCED,
            error=f"Branch mergeStateStatus is {state.merge_state_status}",
        )

    head_match = _ensure_head_matches_pr(
        runner=runner,
        ctx=ctx,
        state=state,
        sleeper=sleeper,
        cwd=cwd,
    )
    if isinstance(head_match, MergeResult):
        post_err = _post_flush(runner=runner, ctx=ctx, merge_result=head_match.result) if post_flush else None
        if post_err is not None:
            return post_err
        return head_match
    if head_match is not None:
        state = head_match

    race = _version_race_gate(runner, cwd=cwd)
    if race is not None:
        post_err = _post_flush(runner=runner, ctx=ctx, merge_result=race.result) if post_flush else None
        if post_err is not None:
            return post_err
        return race

    merge_outcome = _attempt_merge(runner=runner, ctx=ctx, pr_num=pr_num, cwd=cwd)
    if post_flush:
        post_err = _post_flush(runner=runner, ctx=ctx, merge_result=merge_outcome.result)
        if post_err is not None:
            return post_err
    return merge_outcome


def _post_flush(
    *,
    runner: Runner,
    ctx: RunContext,
    merge_result: str,
) -> MergeResult | None:
    try:
        skip = run_logs.flush_logs_post(
            ctx,
            merge_result=merge_result,
            runner=runner,
        )
    except ShipError as exc:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=redact_merge_diagnostic(str(exc)),
        )
    if skip.skipped and skip.reason == "redaction-failed":
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="redaction failed during post-merge run-log flush",
        )
    if skip.skipped and skip.reason == run_logs.REFRESH_SKIP_RECOVERY_FAILED:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=f"post-merge run-log flush skipped: {skip.reason}",
        )
    if skip.skipped:
        logging_util.BreadcrumbWriter().emit(f"merge: post-merge flush skipped: {skip.reason}")
    return None


def _merge_noop_if_pr_closed(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str | None,
    post_flush: bool = True,
) -> MergeResult | None:
    """Idempotent re-entry when the PR is already merged."""
    pr_num = ctx.pr_number
    if pr_num is None:
        return None
    try:
        pr = gh.pr_view(runner, pr_num, repo=ctx.repo, cwd=cwd)
    except ShipError as exc:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=redact_merge_diagnostic(
                f"gh pr view failed during merge-state probe: {exc}",
            ),
        )
    if pr.state == "MERGED" or pr.merged_at:
        merge_result = run_logs.read_state_kv(ctx.state_file, "MERGE_RESULT")
        if merge_result == config.MERGE_RESULT_ADMIN_MERGED:
            outcome = MergeResult(result=config.MERGE_RESULT_ADMIN_MERGED, error="")
        elif merge_result == config.MERGE_RESULT_MERGED:
            outcome = MergeResult(result=config.MERGE_RESULT_MERGED, error="")
        else:
            outcome = MergeResult(result=config.MERGE_RESULT_MERGED, error="")
        if post_flush:
            post_err = _post_flush(runner=runner, ctx=ctx, merge_result=outcome.result)
            if post_err is not None:
                return post_err
        return outcome
    if pr.state == "CLOSED":
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="PR is closed but was not merged; refusing merge noop",
        )
    return None


def _refresh_pr_info(
    *,
    runner: Runner,
    pr_num: int,
    repo: str,
    cwd: str | None,
) -> gh.MergeState:
    def attempt() -> tuple[gh.MergeState, int, str]:
        result = gh.pr_merge_state_read(runner, pr_num, repo=repo, cwd=cwd)
        combined = result.stdout + result.stderr
        if result.returncode != 0:
            return gh.MergeState("", ""), result.returncode, combined
        try:
            data: Any = json.loads(result.stdout or "{}")
            status = str(data.get("mergeStateStatus") or "")
            oid = str(data.get("headRefOid") or "")
            return gh.MergeState(status, oid), 0, combined
        except json.JSONDecodeError:
            return gh.MergeState("", ""), 1, combined

    retried = with_transient_retry(attempt)
    return retried.value


def _retry_unknown(
    *,
    runner: Runner,
    pr_num: int,
    repo: str,
    max_retries: int,
    sleeper: Callable[[float], None],
    cwd: str | None,
) -> gh.MergeState:
    state = gh.MergeState("", "")
    for _ in range(max_retries):
        sleeper(5.0)
        state = _refresh_pr_info(runner=runner, pr_num=pr_num, repo=repo, cwd=cwd)
        if state.merge_state_status and state.merge_state_status != "UNKNOWN":
            return state
    return state


def _poll_head_oid_match(
    *,
    runner: Runner,
    ctx: RunContext,
    pr_num: int,
    local_head: str,
    sleeper: Callable[[float], None],
    cwd: str | None,
) -> gh.MergeState:
    state = gh.MergeState("", "")
    for attempt in range(config.MERGE_PR_POST_PUSH_UNKNOWN_RETRIES):
        state = _refresh_pr_info(runner=runner, pr_num=pr_num, repo=ctx.repo, cwd=cwd)
        if state.head_ref_oid == local_head:
            return state
        if attempt + 1 < config.MERGE_PR_POST_PUSH_UNKNOWN_RETRIES:
            sleeper(5.0)
    return state


def _ensure_head_matches_pr(
    *,
    runner: Runner,
    ctx: RunContext,
    state: gh.MergeState,
    sleeper: Callable[[float], None],
    cwd: str | None,
) -> MergeResult | gh.MergeState | None:
    local_head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    if not local_head:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="could not resolve local HEAD via git rev-parse",
        )
    if local_head == state.head_ref_oid:
        return state
    if not state.head_ref_oid:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="could not resolve PR head OID via gh pr view",
        )
    if not _flush_recoverable(runner=runner, pr_head_oid=state.head_ref_oid, cwd=cwd):
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=(
                f"local HEAD ({local_head}) does not match PR head OID "
                f"({state.head_ref_oid}); refusing to evaluate same-version gate"
            ),
        )
    recovery = git.force_push_recovery(
        runner,
        branch=None,
        expected_remote_oid=state.head_ref_oid,
        cwd=cwd,
        sleeper=sleeper,
    )
    if not recovery.pushed:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=(
                f"flush recovery force-push failed (status={recovery.status})"
            ),
        )
    pr_num = ctx.pr_number
    if pr_num is None:
        return MergeResult(result=config.MERGE_RESULT_ERROR, error="pr_number required")
    local_head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    if not local_head:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="could not resolve local HEAD after force-push recovery",
        )
    state = _poll_head_oid_match(runner=runner, ctx=ctx, pr_num=pr_num, local_head=local_head, sleeper=sleeper, cwd=cwd)
    if local_head != state.head_ref_oid:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="local HEAD does not match PR head OID after force-push recovery",
        )
    if not state.merge_state_status or state.merge_state_status == "UNKNOWN":
        state = _retry_unknown(
            runner=runner,
            pr_num=pr_num,
            repo=ctx.repo,
            max_retries=config.MERGE_PR_POST_PUSH_UNKNOWN_RETRIES,
            sleeper=sleeper,
            cwd=cwd,
        )
    if not state.merge_state_status or state.merge_state_status == "UNKNOWN":
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=(
                "mergeStateStatus still UNKNOWN after post-force-push retries "
                f"(state={state.merge_state_status!r})"
            ),
        )
    if not gh.pr_checks_all_pass(runner, pr_num, repo=ctx.repo, cwd=cwd):
        return MergeResult(
            result=config.MERGE_RESULT_CI_NOT_READY,
            error="CI checks are not all passing after force-push recovery",
        )
    if state.merge_state_status not in config.ADMIN_ELIGIBLE_MERGE_STATES:
        return MergeResult(
            result=config.MERGE_RESULT_MAIN_ADVANCED,
            error=f"Branch mergeStateStatus is {state.merge_state_status} after force-push recovery",
        )
    return state


def _flush_recoverable(
    *,
    runner: Runner,
    pr_head_oid: str,
    cwd: str | None,
) -> bool:
    subjects = git.try_log_subjects(runner, f"{pr_head_oid}..HEAD", cwd=cwd)
    if not subjects.subjects:
        return False
    if len(subjects.subjects) > config.FLUSH_RECOVERY_MAX_COMMITS:
        return False
    if any(
        not subj.startswith(config.FLUSH_COMMIT_SUBJECT_PREFIX)
        for subj in subjects.subjects
    ):
        return False
    diff = git.diff_name_only(runner, pr_head_oid, "HEAD", cwd=cwd)
    if diff.returncode != 0:
        return False
    paths: list[str] = [line for line in diff.stdout.splitlines() if line]
    if not paths:
        return False
    if any(not path.startswith("larch-logs/") for path in paths):
        return False
    return git.is_ancestor(runner, pr_head_oid, "HEAD", cwd=cwd)


def _version_race_gate(
    runner: Runner,
    *,
    cwd: str | None,
) -> MergeResult | None:
    fetch = runner.run(["git", "fetch", "origin", "main", "--quiet"], cwd=cwd)
    if fetch.returncode != 0:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="git fetch origin main failed; cannot verify same-version race",
        )
    bump_subject = _bump_subject(runner, cwd=cwd)
    if not bump_subject:
        return None
    match = _BUMP_SUBJECT_RE.fullmatch(bump_subject)
    if match is None:
        return None
    local_version = match.group(1)
    origin_version = _origin_plugin_version(runner, cwd=cwd)
    if not _SEMVER_RE.fullmatch(origin_version):
        sanitized = origin_version.replace("\n", " ")
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=f"could not parse origin/main published version (got: '{sanitized}')",
        )
    if origin_version == local_version:
        return MergeResult(
            result=config.MERGE_RESULT_VERSION_ALREADY_PUBLISHED,
            error=f"origin/main HEAD already bumped to {local_version}; rebase and re-bump",
        )
    if not git.is_ancestor(runner, "origin/main", "HEAD", cwd=cwd):
        return MergeResult(
            result=config.MERGE_RESULT_MAIN_ADVANCED,
            error="origin/main advanced to a different version; rebase needed",
        )
    premerge = runner.run(["git", "fetch", "origin", "main", "--quiet"], cwd=cwd)
    if premerge.returncode != 0:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="git fetch origin main failed (pre-merge re-fetch)",
        )
    premerge_origin_version = _origin_plugin_version(runner, cwd=cwd)
    if _SEMVER_RE.fullmatch(premerge_origin_version) and premerge_origin_version == local_version:
        return MergeResult(
            result=config.MERGE_RESULT_VERSION_ALREADY_PUBLISHED,
            error=f"origin/main HEAD already bumped to {local_version} (pre-merge re-fetch); rebase and re-bump",
        )
    return None


def _bump_subject(runner: Runner, *, cwd: str | None) -> str:
    result = runner.run(["git", "log", "--format=%s", "origin/main..HEAD"], cwd=cwd)
    if result.returncode != 0:
        return ""
    for line in result.stdout.splitlines():
        if _BUMP_SUBJECT_RE.fullmatch(line):
            return line
    return ""


def _origin_plugin_version(runner: Runner, *, cwd: str | None) -> str:
    result = runner.run(["git", "show", "origin/main:.claude-plugin/plugin.json"], cwd=cwd)
    if result.returncode != 0:
        return ""
    try:
        data: Any = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict):
        return ""
    typed = cast("dict[str, object]", data)
    value: object | None = typed.get("version")
    return str(value or "")


def _maybe_review_required(
    *,
    runner: Runner,
    ctx: RunContext,
    pr_num: int,
    outcome: MergeResult,
    cwd: str | None,
) -> MergeResult:
    if outcome.result not in {
        config.MERGE_RESULT_ADMIN_FAILED,
        config.MERGE_RESULT_POLICY_DENIED,
    }:
        return outcome
    if (
        outcome.result == config.MERGE_RESULT_ADMIN_FAILED
        and _has_merge_conflict_signal(outcome.error)
    ):
        return MergeResult(
            result=config.MERGE_RESULT_MAIN_ADVANCED,
            error=outcome.error,
        )
    review_decision = gh.pr_review_decision(runner, pr_num, repo=ctx.repo, cwd=cwd)
    if review_decision != "REVIEW_REQUIRED":
        return outcome
    if ctx.no_admin_fallback:
        return MergeResult(
            result=config.MERGE_RESULT_REVIEW_REQUIRED,
            error="PR requires approving review; --no-admin-fallback is set",
        )
    return MergeResult(
        result=config.MERGE_RESULT_REVIEW_REQUIRED,
        error=f"PR requires approving review; admin merge failed: {outcome.error}",
    )


def _attempt_merge(
    *,
    runner: Runner,
    ctx: RunContext,
    pr_num: int,
    cwd: str | None,
) -> MergeResult:
    if ctx.no_admin_fallback:
        result = gh.pr_merge(
            runner,
            pr_num,
            repo=ctx.repo,
            merge_method="squash",
            admin=False,
            cwd=cwd,
        )
        if result.returncode == 0:
            return MergeResult(result=config.MERGE_RESULT_MERGED, error="")
        diag = redact_merge_diagnostic(result.stderr + result.stdout)
        return _maybe_review_required(
            runner=runner,
            ctx=ctx,
            pr_num=pr_num,
            outcome=MergeResult(
                result=config.MERGE_RESULT_POLICY_DENIED,
                error=f"branch protection denied merge; --no-admin-fallback set: {diag}",
            ),
            cwd=cwd,
        )

    admin = gh.pr_merge(
        runner,
        pr_num,
        repo=ctx.repo,
        merge_method="squash",
        admin=True,
        cwd=cwd,
    )
    if admin.returncode == 0:
        return MergeResult(result=config.MERGE_RESULT_ADMIN_MERGED, error="")
    admin_diag = redact_merge_diagnostic(admin.stderr + admin.stdout)

    plain = gh.pr_merge(
        runner,
        pr_num,
        repo=ctx.repo,
        merge_method="squash",
        admin=False,
        cwd=cwd,
    )
    if plain.returncode == 0:
        return MergeResult(result=config.MERGE_RESULT_MERGED, error="")
    plain_diag = redact_merge_diagnostic(plain.stderr + plain.stdout)
    return _maybe_review_required(
        runner=runner,
        ctx=ctx,
        pr_num=pr_num,
        outcome=MergeResult(
            result=config.MERGE_RESULT_ADMIN_FAILED,
            error=f"Admin merge failed: {admin_diag}; fallback merge failed: {plain_diag}",
        ),
        cwd=cwd,
    )


# CLI entrypoint migrated from merge_cli.py.
def _emit_kv(*, key: str, value: object) -> None:
    logging_util.emit_kv(key, str(value))


def pr_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py merge pr")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--no-admin-fallback", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    ctx = RunContext(
        branch="",
        issue="",
        repo=args.repo,
        run_id="",
        tmpdir=tempfile.gettempdir(),
        merge=True,
        draft=False,
        forked=False,
        manifest_path="",
        tool_label="codex",
        no_admin_fallback=args.no_admin_fallback,
        repo_unavailable=False,
        pr_number=args.pr,
        no_logs_commit=True,
    )
    result = merge_pr(runner=proc, ctx=ctx, post_flush=False)
    _emit_kv(key="MERGE_RESULT", value=result.result)
    _emit_kv(key="ERROR", value=result.error)
    return 0
