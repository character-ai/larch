"""Idempotent PR ensure flow (parity with create-pr.sh)."""

from __future__ import annotations

from dataclasses import dataclass

import gh
import git
import pr_body
import push
import tracking_issue
from errors import ShipError
from proc import Runner
from retry import with_transient_retry
from run_context import RunContext


@dataclass(frozen=True)
class PrResult:
    number: int
    url: str
    status: str
    title: str = ""
    exit_code: int = 0


@dataclass(frozen=True)
class CreateBranchResult:
    status: str
    branch: str
    base: str
    exit_code: int


def _issue_number(issue: str) -> int:
    if not issue.strip().isdigit():
        msg = "invalid issue number for PR ensure"
        raise ShipError(msg)
    return int(issue)


def ensure_pr(
    runner: Runner,
    ctx: RunContext,
    body: str,
    *,
    title: str,
    cwd: str | None = None,
    base: str | None = None,
) -> PrResult:
    """Create or reuse an open PR for the current branch."""
    if ctx.repo_unavailable:
        return PrResult(number=0, url="", status="local-only")
    issue_num = _issue_number(ctx.issue)
    push.assert_clean_worktree(runner, cwd=cwd)
    existing = gh.pr_for_branch(runner, ctx.branch, repo=ctx.repo, cwd=cwd)
    if existing is not None and existing.state == "OPEN":
        _push_existing_pr(runner, ctx, cwd=cwd)
        linked = tracking_issue.link_pr_closes(body, issue_num)
        if linked != body:
            pr_body.update_pr_body(
                runner,
                existing.number,
                linked,
                repo=ctx.repo,
                cwd=cwd,
            )
        return PrResult(
            number=existing.number,
            url=existing.url,
            status="existing",
        )
    push_result = push.push_branch(runner, ctx, cwd=cwd)
    if push_result.status != "pushed":
        msg = "branch push failed before PR create"
        raise ShipError(msg)
    linked_body = tracking_issue.link_pr_closes(body, issue_num)
    created, was_created = gh.pr_create(
        runner,
        repo=ctx.repo,
        branch=ctx.branch,
        title=title,
        body=linked_body,
        draft=ctx.draft,
        cwd=cwd,
        base=base,
    )
    status = "created" if was_created else "existing"
    return PrResult(number=created.number, url=created.url, status=status)


def _push_existing_pr(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> None:
    remote = push.select_push_remote(runner, ctx, cwd=cwd)
    def attempt() -> tuple[object, int, str]:
        result = git.push_set_upstream(runner, remote, "HEAD", cwd=cwd)
        combined = result.stdout + result.stderr
        return result, result.returncode, combined

    retried = with_transient_retry(attempt)
    if retried.value.returncode == 0:  # type: ignore[union-attr]
        return
    recovery = git.force_push_recovery(runner, branch=None, remote=remote, cwd=cwd)
    if not recovery.pushed:
        msg = f"force-push recovery failed: {recovery.status}"
        raise ShipError(msg)


def create_branch(
    runner: Runner,
    *,
    branch: str,
    base_remote: str = "origin",
    base_ref: str = "main",
    check: bool = False,
    cwd: str | None = None,
) -> CreateBranchResult:
    if not branch or not branch.startswith("sergey-zhupanov/"):
        return CreateBranchResult("invalid", branch, f"{base_remote}/{base_ref}", 2)
    err = git.validate_base_remote_ref(base_remote, base_ref)
    if err is not None:
        return CreateBranchResult("invalid", branch, f"{base_remote}/{base_ref}", 2)
    if check:
        exists = git.try_rev_parse(runner, branch, cwd=cwd)
        return CreateBranchResult(
            "exists" if exists else "absent",
            branch,
            f"{base_remote}/{base_ref}",
            0 if exists else 1,
        )
    fetch = git.fetch(runner, base_remote, base_ref, cwd=cwd)
    if fetch.returncode != 0:
        return CreateBranchResult("fetch_failed", branch, f"{base_remote}/{base_ref}", 1)
    result = runner.run(["git", "checkout", "-B", branch, f"{base_remote}/{base_ref}"], cwd=cwd)
    if result.returncode != 0:
        return CreateBranchResult("create_failed", branch, f"{base_remote}/{base_ref}", 1)
    return CreateBranchResult("created", branch, f"{base_remote}/{base_ref}", 0)


def create_pr_parity(
    runner: Runner,
    *,
    repo: str,
    branch: str,
    title: str,
    body: str,
    base: str | None = None,
    draft: bool = False,
    cwd: str | None = None,
) -> PrResult:
    existing = gh.pr_for_branch(runner, branch, repo=repo, cwd=cwd)
    if existing is not None and existing.state.upper() == "OPEN":
        return PrResult(
            number=existing.number,
            url=existing.url,
            status="existing",
            title=title,
            exit_code=0,
        )
    pushed = push.push_current_branch(runner, cwd=cwd, sleeper=lambda _seconds: None)
    if pushed.exit_code != 0:
        return PrResult(0, "", "push_failed", title, 2)
    created, was_created = gh.pr_create(
        runner,
        repo=repo,
        branch=branch,
        title=title,
        body=body,
        base=base,
        draft=draft,
        cwd=cwd,
    )
    return PrResult(
        number=created.number,
        url=created.url,
        status="created" if was_created else "existing",
        title=title,
        exit_code=0,
    )
