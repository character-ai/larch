"""Typed gh CLI operations with per-operation retry policy."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import redact
from errors import ShipError
from proc import CommandResult, Runner
from retry import RetryResult, with_transient_retry


@dataclass(frozen=True)
class PullRequest:
    number: int
    url: str
    state: str
    head_ref: str


@dataclass(frozen=True)
class WorkflowRun:
    database_id: int
    status: str
    conclusion: str | None


@dataclass(frozen=True)
class FailedJob:
    name: str
    conclusion: str


def _gh(runner: Runner, argv: Sequence[str], *, cwd: str | None = None) -> CommandResult:
    return runner.run(["gh", *argv], cwd=cwd)


def _combined(result: CommandResult) -> str:
    return result.stdout + result.stderr


def _ensure_success(result: CommandResult) -> CommandResult:
    if result.returncode != 0:
        msg = f"gh command failed ({result.returncode}): {' '.join(result.argv)}"
        raise ShipError(msg)
    return result


def _require_json_keys(
    data: Mapping[str, object],
    keys: Sequence[str],
    *,
    context: str,
) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        msg = f"gh JSON missing required keys {missing!r} ({context})"
        raise ShipError(msg)


@contextmanager
def _body_file_args(body: str) -> Iterator[tuple[str, str]]:
    redacted = redact.redact(body)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        delete=False,
    ) as handle:
        handle.write(redacted)
        path = handle.name
    try:
        yield "--body-file", path
    finally:
        Path(path).unlink(missing_ok=True)


def _retry_read(
    runner: Runner,
    argv: Sequence[str],
    *,
    cwd: str | None = None,
) -> CommandResult:
    def attempt() -> tuple[CommandResult, int, str]:
        res = _gh(runner, argv, cwd=cwd)
        return res, res.returncode, _combined(res)

    retried: RetryResult[CommandResult] = with_transient_retry(attempt)
    return retried.value


def pr_view(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> PullRequest:
    result = _ensure_success(
        _retry_read(
            runner,
            [
                "pr",
                "view",
                str(number),
                "--repo",
                repo,
                "--json",
                "number,url,state,headRefName",
            ],
            cwd=cwd,
        ),
    )
    data = json.loads(result.stdout)
    _require_json_keys(
        data,
        ("number", "url", "state", "headRefName"),
        context="pr view",
    )
    return PullRequest(
        number=int(data["number"]),
        url=str(data["url"]),
        state=str(data["state"]),
        head_ref=str(data["headRefName"]),
    )


def pr_for_branch(
    runner: Runner,
    branch: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> PullRequest | None:
    result = _ensure_success(
        _retry_read(
            runner,
            [
                "pr",
                "list",
                "--repo",
                repo,
                "--head",
                branch,
                "--state",
                "open",
                "--json",
                "number,url,state,headRefName",
                "--limit",
                "1",
            ],
            cwd=cwd,
        ),
    )
    rows = json.loads(result.stdout or "[]")
    if not rows:
        return None
    row = rows[0]
    _require_json_keys(
        row,
        ("number", "url", "state", "headRefName"),
        context="pr list",
    )
    return PullRequest(
        number=int(row["number"]),
        url=str(row["url"]),
        state=str(row["state"]),
        head_ref=str(row["headRefName"]),
    )


def _is_create_conflict(text: str) -> bool:
    return "pull request for branch" in text and "already exists" in text


def pr_create(
    runner: Runner,
    *,
    repo: str,
    branch: str,
    title: str,
    body: str,
    draft: bool = False,
    cwd: str | None = None,
) -> PullRequest:
    existing = pr_for_branch(runner, branch, repo=repo, cwd=cwd)
    if existing is not None:
        return existing
    with _body_file_args(body) as (body_flag, body_path):
        argv = [
            "pr",
            "create",
            "--repo",
            repo,
            "--head",
            branch,
            "--title",
            title,
            body_flag,
            body_path,
            "--json",
            "number,url,state,headRefName",
        ]
        if draft:
            argv.append("--draft")
        result = _gh(runner, argv, cwd=cwd)
    if result.returncode != 0:
        if _is_create_conflict(_combined(result)):
            recovered = pr_for_branch(runner, branch, repo=repo, cwd=cwd)
            if recovered is not None:
                return recovered
        _ensure_success(result)
    data = json.loads(result.stdout)
    _require_json_keys(
        data,
        ("number", "url", "state", "headRefName"),
        context="pr create",
    )
    return PullRequest(
        number=int(data["number"]),
        url=str(data["url"]),
        state=str(data["state"]),
        head_ref=str(data["headRefName"]),
    )


def pr_merge(
    runner: Runner,
    number: int,
    *,
    repo: str,
    merge_method: str = "squash",
    cwd: str | None = None,
) -> CommandResult:
    flag = {
        "squash": "--squash",
        "merge": "--merge",
        "rebase": "--rebase",
    }.get(merge_method, "--squash")
    return _gh(
        runner,
        [
            "pr",
            "merge",
            str(number),
            "--repo",
            repo,
            flag,
        ],
        cwd=cwd,
    )


def run_list(
    runner: Runner,
    *,
    repo: str,
    branch: str,
    limit: int = 5,
    cwd: str | None = None,
) -> tuple[WorkflowRun, ...]:
    result = _ensure_success(
        _retry_read(
            runner,
            [
                "run",
                "list",
                "--repo",
                repo,
                "--branch",
                branch,
                "--limit",
                str(limit),
                "--json",
                "databaseId,status,conclusion",
            ],
            cwd=cwd,
        ),
    )
    rows = json.loads(result.stdout or "[]")
    runs: list[WorkflowRun] = []
    for row in rows:
        _require_json_keys(
            row,
            ("databaseId", "status"),
            context="run list",
        )
        runs.append(
            WorkflowRun(
                database_id=int(row["databaseId"]),
                status=str(row["status"]),
                conclusion=row.get("conclusion"),  # type: ignore[arg-type]
            ),
        )
    return tuple(runs)


def run_view(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> WorkflowRun:
    result = _ensure_success(
        _retry_read(
            runner,
            [
                "run",
                "view",
                str(run_id),
                "--repo",
                repo,
                "--json",
                "databaseId,status,conclusion",
            ],
            cwd=cwd,
        ),
    )
    data = json.loads(result.stdout)
    _require_json_keys(data, ("databaseId", "status"), context="run view")
    return WorkflowRun(
        database_id=int(data["databaseId"]),
        status=str(data["status"]),
        conclusion=data.get("conclusion"),
    )


def failed_jobs(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> tuple[FailedJob, ...]:
    result = _ensure_success(
        _retry_read(
            runner,
            [
                "run",
                "view",
                str(run_id),
                "--repo",
                repo,
                "--json",
                "jobs",
            ],
            cwd=cwd,
        ),
    )
    payload = json.loads(result.stdout)
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        msg = "gh JSON missing required keys ['jobs'] (failed jobs)"
        raise ShipError(msg)
    failed: list[FailedJob] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("conclusion") != "failure":
            continue
        _require_json_keys(job, ("name",), context="failed jobs")
        failed.append(
            FailedJob(name=str(job["name"]), conclusion=str(job.get("conclusion", ""))),
        )
    return tuple(failed)


def run_rerun(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    failed_only: bool = True,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["run", "rerun", str(run_id), "--repo", repo]
    if failed_only:
        argv.append("--failed")
    return _gh(runner, argv, cwd=cwd)


def issue_comment(
    runner: Runner,
    issue: str,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    with _body_file_args(body) as (body_flag, body_path):
        return _gh(
            runner,
            ["issue", "comment", issue, "--repo", repo, body_flag, body_path],
            cwd=cwd,
        )


def issue_edit(
    runner: Runner,
    issue: str,
    *,
    repo: str,
    title: str | None = None,
    body: str | None = None,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["issue", "edit", issue, "--repo", repo]
    if title is not None:
        argv.extend(["--title", title])
    if body is not None:
        with _body_file_args(body) as (body_flag, body_path):
            argv.extend([body_flag, body_path])
            return _gh(runner, argv, cwd=cwd)
    return _gh(runner, argv, cwd=cwd)
