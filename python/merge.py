"""PR merge orchestration (parity with merge-pr.sh)."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass

import config
import gh
import git
import redact
import run_logs
from proc import Runner
from retry import with_transient_retry
from run_context import RunContext

_BUMP_SUBJECT_RE = re.compile(r"^Bump version to ([0-9]+\.[0-9]+\.[0-9]+)$")
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass(frozen=True)
class MergeResult:
    result: str
    error: str = ""


def redact_merge_diagnostic(text: str) -> str:
    """Port merge-pr.sh redact_merge_diagnostic."""
    if not text:
        return ""
    redacted = redact.redact_outbound(text)
    if "[content truncated" in redacted:
        return "merge diagnostic redaction unavailable"
    one_line = redacted.replace("\n", " ")
    return one_line[: config.MERGE_DIAGNOSTIC_MAX_LEN]


def merge_pr(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> MergeResult:
    """Classify merge into one of eight merge-pr.sh MERGE_RESULT literals."""
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

    pre = run_logs.flush_logs_pre(runner, ctx, cwd=cwd)
    if pre.skipped and pre.reason == "commit-failed":
        return MergeResult(result=config.MERGE_RESULT_ERROR, error="flush_logs_pre commit failed")
    if pre.skipped and pre.reason not in config.REFRESH_SKIP_MERGE_OK:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=f"flush_logs_pre skipped: {pre.reason}",
        )

    pr_num = ctx.pr_number
    state = _refresh_pr_info(runner, pr_num, ctx.repo, cwd=cwd)
    if state.merge_state_status == "BEHIND":
        _post_flush(ctx)
        return MergeResult(result=config.MERGE_RESULT_MAIN_ADVANCED, error="")
    if not state.merge_state_status or state.merge_state_status == "UNKNOWN":
        state = _retry_unknown(
            runner,
            pr_num,
            ctx.repo,
            max_retries=config.MERGE_PR_INITIAL_UNKNOWN_RETRIES,
            sleeper=sleeper,
            cwd=cwd,
        )
    if state.merge_state_status == "BEHIND":
        _post_flush(ctx)
        return MergeResult(result=config.MERGE_RESULT_MAIN_ADVANCED, error="")
    if not state.merge_state_status or state.merge_state_status == "UNKNOWN":
        _post_flush(ctx)
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=(
                "could not read mergeStateStatus from gh pr view "
                f"after {config.MERGE_PR_INITIAL_UNKNOWN_RETRIES} retries"
            ),
        )

    if not gh.pr_checks_all_pass(runner, pr_num, repo=ctx.repo, cwd=cwd):
        _post_flush(ctx)
        return MergeResult(
            result=config.MERGE_RESULT_CI_NOT_READY,
            error="CI checks are not all passing",
        )

    if state.merge_state_status not in config.ADMIN_ELIGIBLE_MERGE_STATES:
        _post_flush(ctx)
        return MergeResult(
            result=config.MERGE_RESULT_MAIN_ADVANCED,
            error=f"Branch mergeStateStatus is {state.merge_state_status}",
        )

    head_match = _ensure_head_matches_pr(
        runner,
        ctx,
        state,
        sleeper=sleeper,
        cwd=cwd,
    )
    if isinstance(head_match, MergeResult):
        _post_flush(ctx)
        return head_match

    version_outcome = _version_race_gate(runner, cwd=cwd)
    if version_outcome is not None:
        _post_flush(ctx)
        return version_outcome

    merge_outcome = _attempt_merge(runner, ctx, pr_num, cwd=cwd)
    _post_flush(ctx)
    return merge_outcome


def _post_flush(ctx: RunContext) -> None:
    _ = run_logs.flush_logs_post(ctx)


def _refresh_pr_info(
    runner: Runner,
    pr_num: int,
    repo: str,
    *,
    cwd: str | None,
) -> gh.MergeState:
    def attempt() -> tuple[gh.MergeState, int, str]:
        result = gh.pr_merge_state_read(runner, pr_num, repo=repo, cwd=cwd)
        combined = result.stdout + result.stderr
        if result.returncode != 0:
            return gh.MergeState("", ""), result.returncode, combined
        try:
            data = json.loads(result.stdout or "{}")
            status = str(data.get("mergeStateStatus") or "")
            oid = str(data.get("headRefOid") or "")
            return gh.MergeState(status, oid), 0, combined
        except json.JSONDecodeError:
            return gh.MergeState("", ""), 1, combined

    retried = with_transient_retry(attempt)
    return retried.value


def _retry_unknown(
    runner: Runner,
    pr_num: int,
    repo: str,
    *,
    max_retries: int,
    sleeper: Callable[[float], None],
    cwd: str | None,
) -> gh.MergeState:
    state = gh.MergeState("", "")
    for _ in range(max_retries):
        sleeper(5.0)
        state = _refresh_pr_info(runner, pr_num, repo, cwd=cwd)
        if state.merge_state_status and state.merge_state_status != "UNKNOWN":
            return state
    return state


def _ensure_head_matches_pr(
    runner: Runner,
    ctx: RunContext,
    state: gh.MergeState,
    *,
    sleeper: Callable[[float], None],
    cwd: str | None,
) -> MergeResult | gh.MergeState | None:
    local_head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    if not local_head or local_head == state.head_ref_oid:
        return state
    if not state.head_ref_oid:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="could not resolve PR head OID via gh pr view",
        )
    if not _flush_recoverable(runner, state.head_ref_oid, cwd=cwd):
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=(
                f"local HEAD ({local_head}) does not match PR head OID "
                f"({state.head_ref_oid}); refusing to evaluate same-version gate"
            ),
        )
    recovery = git.force_push_recovery(
        runner,
        branch=ctx.branch,
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
    state = _refresh_pr_info(runner, pr_num, ctx.repo, cwd=cwd)
    local_head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    if not local_head or local_head != state.head_ref_oid:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="local HEAD does not match PR head OID after force-push recovery",
        )
    if state.merge_state_status == "BEHIND":
        return MergeResult(result=config.MERGE_RESULT_MAIN_ADVANCED, error="")
    if not state.merge_state_status or state.merge_state_status == "UNKNOWN":
        state = _retry_unknown(
            runner,
            pr_num,
            ctx.repo,
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
    if state.merge_state_status == "BEHIND":
        return MergeResult(result=config.MERGE_RESULT_MAIN_ADVANCED, error="")
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
    runner: Runner,
    pr_head_oid: str,
    *,
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
    paths = [line for line in diff.stdout.splitlines() if line]
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
    fetch = git.fetch(runner, "origin", "main", cwd=cwd)
    if fetch.returncode != 0:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="git fetch origin main failed; cannot verify same-version race",
        )
    subjects = git.log_subjects(runner, "origin/main..HEAD", cwd=cwd)
    bump_subject = ""
    for subj in subjects.subjects:
        if _BUMP_SUBJECT_RE.match(subj):
            bump_subject = subj
            break
    if not bump_subject:
        return None
    match = _BUMP_SUBJECT_RE.match(bump_subject)
    if not match:
        return None
    local_version = match.group(1)
    origin_version = _origin_plugin_version(runner, cwd=cwd)
    if not _SEMVER_RE.match(origin_version):
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error=f"could not parse origin/main published version (got: {origin_version!r})",
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
    fetch2 = git.fetch(runner, "origin", "main", cwd=cwd)
    if fetch2.returncode != 0:
        return MergeResult(
            result=config.MERGE_RESULT_ERROR,
            error="git fetch origin main failed (pre-merge re-fetch)",
        )
    premerge_version = _origin_plugin_version(runner, cwd=cwd)
    if _SEMVER_RE.match(premerge_version) and premerge_version == local_version:
        return MergeResult(
            result=config.MERGE_RESULT_VERSION_ALREADY_PUBLISHED,
            error=(
                f"origin/main HEAD already bumped to {local_version} "
                "(pre-merge re-fetch); rebase and re-bump"
            ),
        )
    return None


def _origin_plugin_version(runner: Runner, *, cwd: str | None) -> str:
    result = git.show_file(runner, "origin/main:.claude-plugin/plugin.json", cwd=cwd)
    if result.returncode != 0:
        return ""
    try:
        data = json.loads(result.stdout)
        return str(data.get("version") or "")
    except json.JSONDecodeError:
        return ""


def _attempt_merge(
    runner: Runner,
    ctx: RunContext,
    pr_num: int,
    *,
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
        return MergeResult(
            result=config.MERGE_RESULT_POLICY_DENIED,
            error=f"branch protection denied merge; --no-admin-fallback set: {diag}",
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
    return MergeResult(
        result=config.MERGE_RESULT_ADMIN_FAILED,
        error=f"Admin merge failed: {admin_diag}; fallback merge failed: {plain_diag}",
    )
