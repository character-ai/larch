# pyright: reportUnusedCallResult=false
"""Idempotent PR ensure flow (parity with pr create)."""

from __future__ import annotations

import re
from dataclasses import dataclass

import argparse
import sys
import gh
import git
import pr_body
import push
import tracking_issue
from pathlib import Path
from errors import ShipError
from proc import CommandResult, Runner
from retry import with_transient_retry
from run_context import RunContext
import logging_util
import proc


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
    branch: str = ""
    base: str = ""
    exit_code: int = 0
    current_branch: str = ""
    is_main: bool = False
    is_user_branch: bool = False
    user_prefix: str = ""
    branch_name: str = ""
    action: str = ""


def _issue_number(issue: str) -> int:
    if not issue.strip().isdigit():
        msg = "invalid issue number for PR ensure"
        raise ShipError(msg)
    return int(issue)


def ensure_pr(
    *,
    runner: Runner,
    ctx: RunContext,
    body: str,
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
        _push_existing_pr(runner=runner, ctx=ctx, cwd=cwd)
        linked = tracking_issue.link_pr_closes(body, issue_num)
        remote_body = gh.pr_view_body(runner, existing.number, repo=ctx.repo, cwd=cwd)
        guidelines_changed = remote_body is not None and pr_body.architectural_guidelines_section(
            remote_body
        ) != pr_body.architectural_guidelines_section(linked)
        if linked != body or guidelines_changed:
            pr_body.update_pr_body(
                runner=runner,
                number=existing.number,
                body=linked,
                repo=ctx.repo,
                cwd=cwd,
            )
        return PrResult(
            number=existing.number,
            url=existing.url,
            status="existing",
        )
    push_result = push.push_branch(runner=runner, ctx=ctx, cwd=cwd)
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
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str | None = None,
) -> None:
    remote = push.select_push_remote(_runner=runner, _ctx=ctx, cwd=cwd)
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


def _derive_user_prefix(runner: Runner, *, cwd: str | None) -> str:
    result = runner.run(["git", "config", "user.name"], cwd=cwd)
    raw = result.stdout.strip() if result.returncode == 0 else ""
    if not raw:
        return "dev"
    sanitized = re.sub(r"[^a-z0-9-]", "", raw.lower().replace(" ", "-"))[:20].rstrip("-")
    return sanitized or "dev"


def check_branch_state(
    runner: Runner,
    *,
    cwd: str | None = None,
) -> CreateBranchResult:
    """Report current branch state (pr create-branch --check parity)."""
    user_prefix = _derive_user_prefix(runner, cwd=cwd)
    current = git.try_current_branch(runner, cwd=cwd) or ""
    is_main = not current or current == "main"
    is_user_branch = bool(current and current.startswith(f"{user_prefix}/"))
    return CreateBranchResult(
        status="checked",
        current_branch=current,
        is_main=is_main,
        is_user_branch=is_user_branch,
        user_prefix=user_prefix,
        exit_code=0,
    )


def create_branch(
    runner: Runner,
    *,
    branch: str,
    base_remote: str = "origin",
    base_ref: str = "main",
    check: bool = False,
    cwd: str | None = None,
) -> CreateBranchResult:
    if check:
        return check_branch_state(runner, cwd=cwd)
    user_prefix = _derive_user_prefix(runner, cwd=cwd)
    base = f"{base_remote}/{base_ref}"
    if not branch or not branch.startswith(f"{user_prefix}/"):
        return CreateBranchResult("invalid", branch, base, exit_code=2)
    err = git.validate_base_remote_ref(base_remote, base_ref)
    if err is not None:
        return CreateBranchResult("invalid", branch, base, exit_code=2)
    if git.local_branch_exists(runner, branch, cwd=cwd):
        return CreateBranchResult("exists", branch, base, exit_code=1)
    def attempt_fetch() -> tuple[CommandResult, int, str]:
        result = git.fetch(runner, base_remote, base_ref, cwd=cwd)
        return result, result.returncode, result.stdout + result.stderr

    fetch = with_transient_retry(attempt_fetch).value
    if fetch.returncode != 0:
        return CreateBranchResult("fetch_failed", branch, base, exit_code=2)
    result = runner.run(["git", "checkout", "-b", branch, base], cwd=cwd)
    if result.returncode != 0:
        return CreateBranchResult("create_failed", branch, base, exit_code=2)
    return CreateBranchResult(
        status="created",
        branch_name=branch,
        action="created",
        branch=branch,
        base=base,
        exit_code=0,
    )


def _pr_title_from_github(
    runner: Runner,
    *,
    number: int,
    repo: str | None,
    fallback: str,
    cwd: str | None,
) -> str:
    argv = [
        "gh",
        "pr",
        "view",
        str(number),
        "--json",
        "title",
        "-q",
        ".title",
    ]
    if repo:
        argv[4:4] = ["--repo", repo]
    result = runner.run(argv, cwd=cwd)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return fallback


def _push_open_pr_branch(
    runner: Runner,
    *,
    branch: str,
    cwd: str | None,
) -> bool:
    try:
        push.assert_clean_worktree(runner, cwd=cwd)
    except ShipError:
        return False
    push_result = runner.run(["git", "push", "-u", "origin", "HEAD"], cwd=cwd)
    if push_result.returncode == 0:
        return True
    _ = git.fetch(runner, "origin", branch, cwd=cwd)
    _ = runner.run(
        ["git", "branch", "--set-upstream-to", f"origin/{branch}", branch],
        cwd=cwd,
    )
    recovery = git.force_push_recovery(
        runner,
        branch=branch,
        cwd=cwd,
    )
    return recovery.pushed


def create_pr_parity(
    runner: Runner,
    *,
    repo: str | None,
    branch: str,
    title: str,
    body: str,
    base: str | None = None,
    draft: bool = False,
    cwd: str | None = None,
) -> PrResult:
    current = git.try_current_branch(runner, cwd=cwd)
    if not current:
        return PrResult(0, "", "push_failed", title, exit_code=2)
    if branch != current:
        return PrResult(0, "", "push_failed", title, exit_code=2)
    try:
        push.assert_clean_worktree(runner, cwd=cwd)
    except ShipError:
        return PrResult(0, "", "push_failed", title, exit_code=1)
    existing = gh.pr_for_branch(runner, branch, repo=repo, cwd=cwd)
    if existing is not None and existing.state.upper() == "OPEN":
        if not _push_open_pr_branch(runner, branch=branch, cwd=cwd):
            return PrResult(0, "", "push_failed", title, exit_code=1)
        pr_title = _pr_title_from_github(
            runner,
            number=existing.number,
            repo=repo,
            fallback=title,
            cwd=cwd,
        )
        return PrResult(
            number=existing.number,
            url=existing.url,
            status="existing",
            title=pr_title,
            exit_code=0,
        )
    push_result = runner.run(["git", "push", "-u", "origin", "HEAD"], cwd=cwd)
    if push_result.returncode != 0:
        return PrResult(0, "", "push_failed", title, exit_code=1)
    # Parity with pr create / compose_pr_body: redact the body fail-closed
    # before it leaves the process. `cli.py pr create` is dormant today (the
    # live ship path uses compose_pr_body/ensure_pr), but a future caller wiring
    # it as the create path must not exfiltrate secrets or session tmpdir paths.
    # A redaction-truncation ShipError propagates to create_main's except
    # handler, which fails closed with PR_STATUS=error.
    created, was_created = gh.pr_create(
        runner,
        repo=repo,
        branch=branch,
        title=title,
        body=pr_body.redact_pr_body(body),
        base=base,
        draft=draft,
        cwd=cwd,
    )
    pr_title = created.title or title
    if not was_created and not created.title:
        pr_title = _pr_title_from_github(
            runner,
            number=created.number,
            repo=repo,
            fallback=title,
            cwd=cwd,
        )
    return PrResult(
        number=created.number,
        url=created.url,
        status="created" if was_created else "existing",
        title=pr_title,
        exit_code=0,
    )


# CLI entrypoints migrated from pr_cli.py.
def _emit_kv(*, key: str, value: object) -> None:
    logging_util.emit_kv(key, str(value))


def _parse(*, parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def create_branch_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr create-branch")
    parser.add_argument("--branch", default="")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 2
    if args.check:
        result = check_branch_state(proc)
        _emit_kv(key="CURRENT_BRANCH", value=result.current_branch)
        _emit_kv(key="IS_MAIN", value=str(result.is_main).lower())
        _emit_kv(key="IS_USER_BRANCH", value=str(result.is_user_branch).lower())
        _emit_kv(key="USER_PREFIX", value=result.user_prefix)
        return result.exit_code
    if not args.branch:
        print("create-branch.sh: --branch is required", file=sys.stderr)
        return 2
    result = create_branch(
        proc,
        branch=args.branch,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
    )
    if result.exit_code == 0:
        _emit_kv(key="BRANCH_NAME", value=result.branch_name)
        _emit_kv(key="ACTION", value=result.action)
    else:
        print(f"create-branch.sh: {result.status}: {result.branch}", file=sys.stderr)
    return result.exit_code


def _validate_repo_arg(repo: str, *, script: str) -> int | None:
    if not gh.validate_repo_slug(repo):
        print(
            f"{script}: --repo must be OWNER/REPO using GitHub owner/repo characters",
            file=sys.stderr,
        )
        return 2
    return None


def create_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr create")
    parser.add_argument("--repo", default=None)
    parser.add_argument("--branch", default=None)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--base", default=None)
    parser.add_argument("--draft", action="store_true")
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 1
    repo = args.repo or gh.resolve_repo(proc)
    if repo:
        repo_err = _validate_repo_arg(repo, script="create-pr.sh")
        if repo_err is not None:
            return repo_err
    branch = args.branch or git.try_current_branch(proc) or ""
    if not branch:
        print("create-pr.sh: not on a branch (detached HEAD)", file=sys.stderr)
        return 2
    try:
        with Path(args.body_file).open(encoding="utf-8") as handle:
            body = handle.read()
    except OSError as exc:
        print(f"create-pr.sh: cannot read body file: {exc}", file=sys.stderr)
        return 2
    try:
        result = create_pr_parity(
            proc,
            repo=repo,
            branch=branch,
            title=args.title,
            body=body,
            base=args.base,
            draft=args.draft,
        )
    except Exception as exc:  # pylint: disable=broad-except
        _emit_kv(key="PR_STATUS", value="error")
        _emit_kv(key="PR_NUMBER", value=0)
        _emit_kv(key="PR_URL", value="")
        _emit_kv(key="PR_TITLE", value=args.title)
        print(str(exc), file=sys.stderr)
        return 2
    _emit_kv(key="PR_NUMBER", value=result.number)
    _emit_kv(key="PR_URL", value=result.url)
    _emit_kv(key="PR_TITLE", value=result.title)
    _emit_kv(key="PR_STATUS", value=result.status)
    return result.exit_code


def body_update_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr body-update")
    parser.add_argument("--pr", required=True)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--body-file", required=True)
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 2
    if args.repo:
        repo_err = _validate_repo_arg(args.repo, script="gh-pr-body-update.sh")
        if repo_err is not None:
            return repo_err
    result = gh.pr_edit_body_file(proc, args.pr, args.body_file, repo=args.repo)
    _emit_kv(key="UPDATED", value=str(result.updated).lower())
    _emit_kv(key="ERROR", value=result.error)
    return result.exit_code


def checks_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr checks")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 1
    repo_err = _validate_repo_arg(args.repo, script="gh-pr-checks.sh")
    if repo_err is not None:
        return repo_err
    result = gh.pr_checks_text_read(proc, args.pr, repo=args.repo)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def closes_issue_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py pr closes-issue")
    parser.add_argument("--body-file", default=None)
    parser.add_argument("--repo", default=None)
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 1
    if args.body_file:
        try:
            with Path(args.body_file).open(encoding="utf-8") as handle:
                print(gh.extract_closes_issue(handle.read()))
        except OSError:
            print()
        return 0
    if args.repo:
        repo_err = _validate_repo_arg(args.repo, script="gh-pr-closes-issue.sh")
        if repo_err is not None:
            return repo_err
    repo = args.repo or gh.resolve_repo(proc) or ""
    if not repo:
        print()
        return 0
    print(gh.extract_closes_issue_from_current_pr(proc, repo=repo))
    return 0
