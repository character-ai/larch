"""Typed gh CLI operations with per-operation retry policy.

Read helpers retry transient failures via ``with_transient_retry`` and return
the last ``CommandResult`` (including after retry exhaustion). Typed parsers
raise ``TransientNetworkError`` (with ``result`` set) or ``ShipError`` on
non-zero reads; use ``*_read`` helpers when the last result must be inspected.
Mutating helpers return the last ``CommandResult`` without retry.
"""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from typing import cast
from dataclasses import dataclass
from pathlib import Path

import redact
from errors import ShipError, TransientNetworkError
from proc import CommandResult, Runner
from retry import RetryResult, is_transient_net_signature, with_transient_retry


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


def _redact_gh_scalar(text: str) -> str:
    """Redact a single gh CLI field without redact()'s line-oriented trailing newline."""
    redacted = redact.redact(text)
    if text and not text.endswith("\n") and redacted.endswith("\n"):
        return redacted[:-1]
    return redacted


def _ensure_success(result: CommandResult) -> CommandResult:
    if result.returncode != 0:
        msg = f"gh command failed ({result.returncode}): {' '.join(result.argv)}"
        raise ShipError(msg)
    return result


def _raise_read_failure(result: CommandResult) -> None:
    msg = f"gh command failed ({result.returncode}): {' '.join(result.argv)}"
    if is_transient_net_signature(_combined(result)):
        raise TransientNetworkError(msg, result=result)
    raise ShipError(msg)


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


def _loads_json(text: str, *, context: str) -> object:
    try:
        return json.loads(text or "null")
    except json.JSONDecodeError as exc:
        msg = f"gh JSON parse failed ({context}): {exc}"
        raise ShipError(msg) from exc


def _as_json_object(data: object, *, context: str) -> dict[str, object]:
    if not isinstance(data, dict):
        msg = f"gh JSON parse failed ({context}): expected object"
        raise ShipError(msg)
    return cast("dict[str, object]", data)


def _as_json_list(data: object, *, context: str) -> list[object]:
    if not isinstance(data, list):
        msg = f"gh JSON parse failed ({context}): expected array"
        raise ShipError(msg)
    return cast("list[object]", data)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_int(value: object, *, context: str, field: str) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        msg = f"gh JSON field {field!r} is not an int ({context})"
        raise ShipError(msg) from exc


@contextmanager
def _body_file_args(body: str) -> Generator[tuple[str, str], None, None]:
    redacted = redact.redact(body)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        delete=False,
    ) as handle:
        _ = handle.write(redacted)
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
    """Retry reads on transient net failures; return last result (may be non-zero)."""
    def attempt() -> tuple[CommandResult, int, str]:
        res = _gh(runner, argv, cwd=cwd)
        return res, res.returncode, _combined(res)

    retried: RetryResult[CommandResult] = with_transient_retry(attempt)
    return retried.value


def pr_view_read(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
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
    )


def pr_view(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> PullRequest:
    result = pr_view_read(runner, number, repo=repo, cwd=cwd)
    if result.returncode != 0:
        _raise_read_failure(result)
    data = _as_json_object(_loads_json(result.stdout, context="pr view"), context="pr view")
    _require_json_keys(
        data,
        ("number", "url", "state", "headRefName"),
        context="pr view",
    )
    return PullRequest(
        number=_as_int(data["number"], context="pr view", field="number"),
        url=str(data["url"]),
        state=str(data["state"]),
        head_ref=str(data["headRefName"]),
    )


def pr_for_branch_read(
    runner: Runner,
    branch: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
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
    )


def pr_for_branch(
    runner: Runner,
    branch: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> PullRequest | None:
    result = pr_for_branch_read(runner, branch, repo=repo, cwd=cwd)
    if result.returncode != 0:
        _raise_read_failure(result)
    rows_obj = _as_json_list(
        _loads_json(result.stdout or "[]", context="pr list"),
        context="pr list",
    )
    if not rows_obj:
        return None
    row = _as_json_object(rows_obj[0], context="pr list row")
    _require_json_keys(
        row,
        ("number", "url", "state", "headRefName"),
        context="pr list",
    )
    return PullRequest(
        number=_as_int(row["number"], context="pr list", field="number"),
        url=str(row["url"]),
        state=str(row["state"]),
        head_ref=str(row["headRefName"]),
    )


def _is_create_conflict(text: str) -> bool:
    return "pull request for branch" in text and "already exists" in text


_PR_CONFLICT_URL_RE = re.compile(r"https?://[^\s]+/pull/\d+")


def _recover_pr_from_conflict_text(text: str, *, branch: str) -> PullRequest | None:
    matches = _PR_CONFLICT_URL_RE.findall(text)
    if not matches:
        return None
    url = matches[-1]
    number_match = re.search(r"/(\d+)$", url)
    if number_match is None:
        return None
    return PullRequest(
        number=int(number_match.group(1)),
        url=url,
        state="OPEN",
        head_ref=branch,
    )


def pr_create(
    runner: Runner,
    *,
    repo: str,
    branch: str,
    title: str,
    body: str,
    base: str | None = None,
    assignee: str | None = "@me",
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
            _redact_gh_scalar(title),
            body_flag,
            body_path,
            "--json",
            "number,url,state,headRefName",
        ]
        if assignee is not None:
            argv.extend(["--assignee", assignee])
        if base is not None:
            argv.extend(["--base", base])
        if draft:
            argv.append("--draft")
        result = _gh(runner, argv, cwd=cwd)
    if result.returncode != 0:
        if _is_create_conflict(_combined(result)):
            conflict_text = _combined(result)
            try:
                recovered = pr_for_branch(runner, branch, repo=repo, cwd=cwd)
            except (ShipError, TransientNetworkError):
                recovered = None
            if recovered is not None:
                return recovered
            recovered = _recover_pr_from_conflict_text(
                conflict_text,
                branch=branch,
            )
            if recovered is not None:
                return recovered
        _ = _ensure_success(result)
    data = _as_json_object(
        _loads_json(result.stdout, context="pr create"),
        context="pr create",
    )
    _require_json_keys(
        data,
        ("number", "url", "state", "headRefName"),
        context="pr create",
    )
    return PullRequest(
        number=_as_int(data["number"], context="pr create", field="number"),
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
    flag_map = {
        "squash": "--squash",
        "merge": "--merge",
        "rebase": "--rebase",
    }
    flag = flag_map.get(merge_method)
    if flag is None:
        msg = f"unknown merge_method: {merge_method!r}"
        raise ShipError(msg)
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


def run_list_read(
    runner: Runner,
    *,
    repo: str,
    branch: str,
    limit: int = 5,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
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
    )


def run_list(
    runner: Runner,
    *,
    repo: str,
    branch: str,
    limit: int = 5,
    cwd: str | None = None,
) -> tuple[WorkflowRun, ...]:
    result = run_list_read(runner, repo=repo, branch=branch, limit=limit, cwd=cwd)
    if result.returncode != 0:
        _raise_read_failure(result)
    rows_obj = _as_json_list(
        _loads_json(result.stdout or "[]", context="run list"),
        context="run list",
    )
    runs: list[WorkflowRun] = []
    for row_obj in rows_obj:
        row = _as_json_object(row_obj, context="run list row")
        _require_json_keys(
            row,
            ("databaseId", "status"),
            context="run list",
        )
        runs.append(
            WorkflowRun(
                database_id=_as_int(row["databaseId"], context="run list", field="databaseId"),
                status=str(row["status"]),
                conclusion=_optional_str(row.get("conclusion")),
            ),
        )
    return tuple(runs)


def run_view_read(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
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
    )


def run_view(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> WorkflowRun:
    result = run_view_read(runner, run_id, repo=repo, cwd=cwd)
    if result.returncode != 0:
        _raise_read_failure(result)
    data = _as_json_object(_loads_json(result.stdout, context="run view"), context="run view")
    _require_json_keys(data, ("databaseId", "status"), context="run view")
    return WorkflowRun(
        database_id=_as_int(data["databaseId"], context="run view", field="databaseId"),
        status=str(data["status"]),
        conclusion=_optional_str(data.get("conclusion")),
    )


def failed_jobs_read(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
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
    )


def failed_jobs(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> tuple[FailedJob, ...]:
    result = failed_jobs_read(runner, run_id, repo=repo, cwd=cwd)
    if result.returncode != 0:
        _raise_read_failure(result)
    payload = _as_json_object(
        _loads_json(result.stdout, context="failed jobs"),
        context="failed jobs",
    )
    jobs_raw = payload.get("jobs", [])
    if not isinstance(jobs_raw, list):
        msg = "gh JSON missing required keys ['jobs'] (failed jobs)"
        raise ShipError(msg)
    jobs = cast("list[object]", jobs_raw)
    failed: list[FailedJob] = []
    for job_obj in jobs:
        if not isinstance(job_obj, dict):
            continue
        job = cast("dict[str, object]", job_obj)
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
        argv.extend(["--title", _redact_gh_scalar(title)])
    if body is not None:
        with _body_file_args(body) as (body_flag, body_path):
            argv.extend([body_flag, body_path])
            return _gh(runner, argv, cwd=cwd)
    return _gh(runner, argv, cwd=cwd)
