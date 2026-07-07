# pyright: reportUnusedCallResult=false
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
from datetime import datetime
from typing import Final, cast
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import argparse
import sys
from larch.core import config
from larch.core import redact
from larch.errors import ShipError, TransientNetworkError
from larch.core.proc import CommandResult, Runner
from larch.core.retry import RetryResult, is_transient_net_signature, with_transient_retry
from larch.core import proc


class GhReadTimeout(ShipError):
    """A gh read subprocess exceeded its per-call timeout (exit EXIT_TIMEOUT).

    Subclasses ShipError so existing broad handlers still catch it, while callers
    that thread a timeout (e.g. the CI monitor poll loop) can distinguish a hung
    query from an ordinary non-zero read and route it to a status-failure bail.
    """


@dataclass(frozen=True)
class PullRequest:
    number: int
    url: str
    state: str
    head_ref: str
    merged_at: str | None = None
    merge_state_status: str | None = None
    title: str = ""


@dataclass(frozen=True)
class WorkflowRun:
    database_id: int
    status: str
    conclusion: str | None
    head_sha: str = ""
    event: str = ""


@dataclass(frozen=True)
class WorkflowRunListFilters:
    repo: str
    branch: str | None = None
    workflow: str | None = None
    event: str | None = None
    status: str | None = None
    commit: str | None = None
    limit: int = 5
    cwd: str | None = None


@dataclass(frozen=True)
class FailedJob:
    name: str
    conclusion: str


@dataclass(frozen=True)
class MergeState:
    merge_state_status: str
    head_ref_oid: str


@dataclass(frozen=True)
class PrCheck:
    name: str
    state: str
    bucket: str


@dataclass(frozen=True)
class BodyUpdateResult:
    updated: bool
    error: str
    exit_code: int


def _gh(
    runner: Runner,
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    timeout: float | None = None,
) -> CommandResult:
    return runner.run(["gh", *argv], cwd=cwd, timeout=timeout)


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


def loads_json_paginated_list(text: str) -> list[object]:
    """Parse one or more concatenated gh paginated JSON arrays."""
    return _loads_json_paginated_list(text, context="paginated list")


def _loads_json_paginated_list(text: str, *, context: str) -> list[object]:
    stripped = (text or "").strip()
    if not stripped:
        return []
    try:
        return _as_json_list(_loads_json(stripped, context=context), context=context)
    except ShipError:
        pass
    decoder = json.JSONDecoder()
    merged: list[object] = []
    idx = 0
    length = len(stripped)
    while idx < length:
        while idx < length and stripped[idx].isspace():
            idx += 1
        if idx >= length:
            break
        try:
            page, end = decoder.raw_decode(stripped, idx)
        except json.JSONDecodeError as exc:
            msg = f"gh JSON parse failed ({context}): {exc}"
            raise ShipError(msg) from exc
        merged.extend(_as_json_list(page, context=context))
        idx = end
    return merged


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


def _fail_closed_redacted(text: str, *, context: str) -> str:
    redacted = redact.redact(text)
    if "[content truncated" in redacted:
        msg = f"redaction failed for {context}"
        raise ShipError(msg)
    return redacted


@contextmanager
def _body_file_args(body: str, *, redact_body: bool = True) -> Generator[tuple[str, str], None, None]:
    redacted = _fail_closed_redacted(body, context="gh body file") if redact_body else body
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


def _effective_read_timeout(timeout: float | None) -> float | None:
    return timeout if timeout is not None else config.CI_STATUS_QUERY_TIMEOUT_SEC


def _retry_read(
    runner: Runner,
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    timeout: float | None = None,
) -> CommandResult:
    """Retry reads on transient net failures; return last result (may be non-zero).

    Every gh read is bounded by the caller-supplied timeout or the shared default.
    A timed-out read returns exit ``EXIT_TIMEOUT`` with no transient signature, so
    it is not retried here.
    """
    effective_timeout = _effective_read_timeout(timeout)

    def attempt() -> tuple[CommandResult, int, str]:
        res = _gh(runner, argv, cwd=cwd, timeout=effective_timeout)
        return res, res.returncode, _combined(res)

    retried: RetryResult[CommandResult] = with_transient_retry(attempt)
    return retried.value


def pr_view_field_read(
    runner: Runner,
    number: int | str,
    field: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
        runner,
        ["pr", "view", str(number), "--repo", repo, "--json", field],
        cwd=cwd,
    )


def pr_view_read(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
    timeout: float | None = None,
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
            "number,url,state,headRefName,mergedAt,mergeStateStatus",
        ],
        cwd=cwd,
        timeout=timeout,
    )


def pr_view(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
    timeout: float | None = None,
) -> PullRequest:
    effective_timeout = _effective_read_timeout(timeout)
    result = pr_view_read(runner, number, repo=repo, cwd=cwd, timeout=timeout)
    if effective_timeout is not None and result.returncode == config.EXIT_TIMEOUT:
        msg = f"gh pr view timed out after {effective_timeout:.0f}s ({' '.join(result.argv)})"
        raise GhReadTimeout(msg)
    if result.returncode != 0:
        _raise_read_failure(result)
    data = _as_json_object(_loads_json(result.stdout, context="pr view"), context="pr view")
    return _pull_request_from_json(data, context="pr view")


def pr_view_body(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> str | None:
    """Return the PR body text, or None when gh cannot read it."""
    result = _retry_read(
        runner,
        ["pr", "view", str(number), "--repo", repo, "--json", "body"],
        cwd=cwd,
    )
    if result.returncode != 0:
        return None
    try:
        data = _as_json_object(_loads_json(result.stdout, context="pr view body"), context="pr view body")
    except ShipError:
        return None
    body = data.get("body")
    if body is None:
        return ""
    return str(body)


def _pull_request_from_json(data: Mapping[str, object], *, context: str) -> PullRequest:
    _require_json_keys(
        data,
        ("number", "url", "state", "headRefName"),
        context=context,
    )
    merged_raw = data.get("mergedAt")
    merged_at = str(merged_raw) if merged_raw else None
    merge_state_raw = data.get("mergeStateStatus")
    merge_state_status = str(merge_state_raw) if merge_state_raw else None
    return PullRequest(
        number=_as_int(data["number"], context=context, field="number"),
        url=str(data["url"]),
        state=str(data["state"]),
        head_ref=str(data["headRefName"]),
        merged_at=merged_at,
        merge_state_status=merge_state_status,
        title=str(data.get("title") or ""),
    )


def pr_view_current_read(
    runner: Runner,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
        runner,
        [
            "pr",
            "view",
            "--repo",
            repo,
            "--json",
            "number,url,state,headRefName",
        ],
        cwd=cwd,
    )


def pr_for_branch_read(
    runner: Runner,
    branch: str,
    *,
    repo: str | None,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["pr", "list"]
    if repo:
        argv.extend(["--repo", repo])
    argv.extend(
        [
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number,url,state,headRefName,title",
            "--limit",
            "1",
        ],
    )
    return _retry_read(runner, argv, cwd=cwd)


def pr_list_open_read(
    runner: Runner,
    *,
    repo: str,
    cwd: str | None = None,
    limit: int = 200,
) -> CommandResult:
    """Read open PRs (``number``, ``title``, ``headRefName``) for reconciliation sweeps."""
    return _retry_read(
        runner,
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--json",
            "number,title,headRefName",
            "--limit",
            str(limit),
        ],
        cwd=cwd,
    )


def pr_for_branch(
    runner: Runner,
    branch: str,
    *,
    repo: str | None,
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
        title=str(row.get("title") or ""),
    )


def _is_create_conflict(text: str) -> bool:
    return "pull request for branch" in text and "already exists" in text


_PR_CONFLICT_URL_RE = re.compile(r"https?://[^\s]+/pull/\d+")
_PR_URL_MIN_PARTS = 4
_REPO_SLUG_PARTS = 2


def _repo_matches_pr_url(*, repo: str | None, url: str) -> bool:
    if repo is None:
        return True
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < _PR_URL_MIN_PARTS or parts[2].lower() != "pull":
        return False
    repo_parts = repo.split("/")
    if len(repo_parts) != _REPO_SLUG_PARTS:
        return False
    return parts[0].lower() == repo_parts[0].lower() and parts[1].lower() == repo_parts[1].lower()


def _candidate_from_pr_url(url: str, *, branch: str) -> PullRequest | None:
    number_match = re.search(r"/(\d+)$", url)
    if number_match is None:
        return None
    return PullRequest(
        number=int(number_match.group(1)),
        url=url,
        state="OPEN",
        head_ref=branch,
    )


def _validate_recovered_pr(
    runner: Runner,
    candidate: PullRequest,
    *,
    repo: str | None,
    branch: str,
    cwd: str | None,
    allow_unverified: bool = False,
) -> PullRequest | None:
    if not _repo_matches_pr_url(repo=repo, url=candidate.url):
        return None
    if repo is None:
        return candidate
    try:
        viewed = pr_view(runner, candidate.number, repo=repo, cwd=cwd)
    except TransientNetworkError:
        raise
    except ShipError:
        if allow_unverified:
            return candidate
        return None
    state = viewed.state.upper()
    if state == "MERGED":
        return viewed
    if viewed.head_ref != branch:
        return None
    if state != "OPEN":
        return None
    return viewed


def _recover_pr_from_urls(
    runner: Runner,
    urls: Sequence[str],
    *,
    branch: str,
    repo: str | None,
    cwd: str | None,
    allow_unverified: bool = False,
) -> PullRequest | None:
    for url in reversed(list(urls)):
        candidate = _candidate_from_pr_url(url, branch=branch)
        if candidate is None:
            continue
        validated = _validate_recovered_pr(
            runner,
            candidate,
            repo=repo,
            branch=branch,
            cwd=cwd,
            allow_unverified=allow_unverified,
        )
        if validated is not None:
            return validated
    return None


def _recover_pr_from_create_output(
    runner: Runner,
    stdout: str,
    stderr: str,
    *,
    branch: str,
    repo: str | None,
    cwd: str | None,
) -> PullRequest | None:
    for urls in (
        _PR_CONFLICT_URL_RE.findall(stdout),
        _PR_CONFLICT_URL_RE.findall(stderr),
    ):
        if not urls:
            continue
        recovered = _recover_pr_from_urls(
            runner,
            urls,
            branch=branch,
            repo=repo,
            cwd=cwd,
        )
        if recovered is not None:
            return recovered
    return None


def _recover_pr_from_conflict_text(
    runner: Runner,
    text: str,
    *,
    branch: str,
    repo: str | None,
    cwd: str | None,
) -> PullRequest | None:
    matches = _PR_CONFLICT_URL_RE.findall(text)
    if not matches:
        return None
    return _recover_pr_from_urls(
        runner,
        matches,
        branch=branch,
        repo=repo,
        cwd=cwd,
        allow_unverified=True,
    )


def pr_create(
    runner: Runner,
    *,
    repo: str | None,
    branch: str,
    title: str,
    body: str,
    base: str | None = None,
    assignee: str | None = "@me",
    draft: bool = False,
    cwd: str | None = None,
) -> tuple[PullRequest, bool]:
    existing = pr_for_branch(runner, branch, repo=repo, cwd=cwd)
    if existing is not None:
        return existing, False
    with _body_file_args(body) as (body_flag, body_path):
        argv = [
            "pr",
            "create",
            "--head",
            branch,
            "--title",
            _redact_gh_scalar(title),
            body_flag,
            body_path,
        ]
        if repo:
            argv[2:2] = ["--repo", repo]
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
            except TransientNetworkError:
                raise
            except ShipError:
                recovered = None
            if recovered is not None:
                return recovered, False
            recovered = _recover_pr_from_conflict_text(
                runner,
                conflict_text,
                branch=branch,
                repo=repo,
                cwd=cwd,
            )
            if recovered is not None:
                return recovered, False
        _ = _ensure_success(result)
    try:
        recovered = pr_for_branch(runner, branch, repo=repo, cwd=cwd)
    except TransientNetworkError:
        raise
    except ShipError:
        recovered = None
    if recovered is not None:
        return recovered, True
    recovered = _recover_pr_from_create_output(
        runner,
        result.stdout,
        result.stderr,
        branch=branch,
        repo=repo,
        cwd=cwd,
    )
    if recovered is not None:
        return recovered, True
    msg = "gh pr create succeeded, but the created PR could not be resolved"
    raise ShipError(msg)


def pr_merge(
    runner: Runner,
    number: int,
    *,
    repo: str,
    merge_method: str = "squash",
    admin: bool = False,
    delete_branch: bool = False,
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
    argv = [
        "pr",
        "merge",
        str(number),
        "--repo",
        repo,
        flag,
    ]
    if admin:
        argv.append("--admin")
    if delete_branch:
        argv.append("--delete-branch")
    return _gh(runner, argv, cwd=cwd)


def pr_merge_state_read(
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
            "mergeStateStatus,headRefOid",
        ],
        cwd=cwd,
    )


def pr_merge_state(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> MergeState:
    result = pr_merge_state_read(runner, number, repo=repo, cwd=cwd)
    if result.returncode != 0:
        _raise_read_failure(result)
    data = _as_json_object(
        _loads_json(result.stdout, context="pr merge state"),
        context="pr merge state",
    )
    status = str(data.get("mergeStateStatus") or "")
    head_oid = str(data.get("headRefOid") or "")
    return MergeState(merge_state_status=status, head_ref_oid=head_oid)


def pr_checks_read(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
    required: bool = False,
) -> CommandResult:
    argv = [
        "pr",
        "checks",
        str(number),
        "--repo",
        repo,
        "--json",
        "name,state,bucket,link",
    ]
    if required:
        argv.append("--required")
    return _retry_read(runner, argv, cwd=cwd)


_CHECKS_JSON_BLOCKING_BUCKETS: Final = frozenset({"fail", "pending"})
_PR_CHECKS_DETAIL_MAX_LENGTH: Final = 240
_PR_CHECKS_DETAIL_ROW_LIMIT: Final = 5


def _pr_checks_json_rows(stdout: str) -> list[dict[str, object]] | None:
    try:
        rows_obj = _as_json_list(
            _loads_json(stdout or "[]", context="pr checks"),
            context="pr checks",
        )
        return [_as_json_object(row_obj, context="pr checks row") for row_obj in rows_obj]
    except ShipError:
        return None


def _pr_check_bucket(row: Mapping[str, object]) -> str:
    return str(row.get("bucket") or "").lower()


def _pr_check_name(row: Mapping[str, object]) -> str:
    name = _compact_pr_checks_detail(str(row.get("name") or "unnamed check"), max_length=80)
    return name or "unnamed check"


def _compact_pr_checks_detail(text: str, *, max_length: int = _PR_CHECKS_DETAIL_MAX_LENGTH) -> str:
    compact = re.sub(r"\s+", " ", _redact_gh_scalar(text)).strip()
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 3].rstrip() + "..."


def _blocking_pr_check_rows(rows: Sequence[Mapping[str, object]]) -> list[str]:
    entries = [
        f"{_pr_check_name(row)}={_pr_check_bucket(row)}"
        for row in rows
        if _pr_check_bucket(row) in _CHECKS_JSON_BLOCKING_BUCKETS
    ]
    limited = entries[:_PR_CHECKS_DETAIL_ROW_LIMIT]
    if len(entries) > len(limited):
        limited.append(f"+{len(entries) - len(limited)} more")
    return limited


def _format_blocking_pr_check_rows(rows: Sequence[Mapping[str, object]]) -> str:
    entries = _blocking_pr_check_rows(rows)
    if not entries:
        return ""
    return _compact_pr_checks_detail("blocking checks: " + ", ".join(entries))


def _pr_checks_json_all_pass(stdout: str) -> bool | None:
    """Return True/False when JSON is parseable; None when JSON path unusable."""
    rows = _pr_checks_json_rows(stdout)
    if rows is None:
        return None
    if not rows:
        return False
    return not _blocking_pr_check_rows(rows)


def pr_checks_text_read(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
    required: bool = False,
) -> CommandResult:
    argv = ["pr", "checks", str(number), "--repo", repo]
    if required:
        argv.append("--required")
    return _retry_read(runner, argv, cwd=cwd)


_CHECKS_TEXT_BAD_RE = re.compile(
    r"\b(fail|pending|in_progress|in progress|queued)\b",
    re.IGNORECASE,
)


def _pr_checks_text_all_pass(text: str) -> bool:
    if not text.strip():
        return False
    return _CHECKS_TEXT_BAD_RE.search(text) is None


def _pr_checks_text_not_ready_detail(text: str) -> str:
    if not text.strip():
        return "no PR checks returned"
    for line in text.splitlines():
        if _CHECKS_TEXT_BAD_RE.search(line):
            return _compact_pr_checks_detail(f"blocking check line: {line}")
    return "no blocking PR checks found in text output"


def pr_checks_not_ready_detail(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> str:
    result = pr_checks_read(runner, number, repo=repo, cwd=cwd)
    rows = _pr_checks_json_rows(result.stdout)
    if rows is not None:
        if not rows:
            return "no PR checks returned"
        json_detail = _format_blocking_pr_check_rows(rows)
        if json_detail:
            return json_detail
        return "no fail or pending PR checks remain"

    text_result = pr_checks_text_read(runner, number, repo=repo, cwd=cwd)
    if text_result.returncode != 0 and (
        is_transient_net_signature(_combined(text_result))
        or not text_result.stdout.strip()
    ):
        return "unable to read PR checks"
    return _pr_checks_text_not_ready_detail(text_result.stdout)


def pr_review_decision(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> str:
    """Return reviewDecision for a PR ('REVIEW_REQUIRED', 'APPROVED', 'CHANGES_REQUESTED', or '')."""
    result = _retry_read(
        runner,
        ["pr", "view", str(number), "--repo", repo, "--json", "reviewDecision"],
        cwd=cwd,
    )
    if result.returncode != 0:
        return ""
    try:
        data = _as_json_object(_loads_json(result.stdout, context="pr reviewDecision"), context="pr reviewDecision")
        value = data.get("reviewDecision")
        return str(value) if value else ""
    except ShipError:
        return ""


def pr_checks_all_pass(
    runner: Runner,
    number: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> bool:
    result = pr_checks_read(runner, number, repo=repo, cwd=cwd)
    if result.returncode == 0:
        json_pass = _pr_checks_json_all_pass(result.stdout)
        if json_pass is not None:
            return json_pass
    elif is_transient_net_signature(_combined(result)):
        return False
    text_result = pr_checks_text_read(runner, number, repo=repo, cwd=cwd)
    if text_result.returncode != 0:
        if is_transient_net_signature(_combined(text_result)):
            return False
        return _pr_checks_text_all_pass(text_result.stdout)
    return _pr_checks_text_all_pass(text_result.stdout)


def pr_edit_body(
    runner: Runner,
    number: int,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    with _body_file_args(body) as (body_flag, body_path):
        return _gh(
            runner,
            [
                "pr",
                "edit",
                str(number),
                "--repo",
                repo,
                body_flag,
                body_path,
            ],
            cwd=cwd,
        )


def _workflow_run_from_json(data: Mapping[str, object], *, context: str) -> WorkflowRun:
    _require_json_keys(data, ("databaseId", "status"), context=context)
    return WorkflowRun(
        database_id=_as_int(data["databaseId"], context=context, field="databaseId"),
        status=str(data["status"]),
        conclusion=_optional_str(data.get("conclusion")),
        head_sha=str(data.get("headSha") or ""),
        event=str(data.get("event") or ""),
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


def run_list_filtered_read(
    runner: Runner,
    filters: WorkflowRunListFilters,
) -> CommandResult:
    """Read workflow runs through a typed, additive filter surface."""
    argv = [
        "run",
        "list",
        "--repo",
        filters.repo,
        "--limit",
        str(filters.limit),
        "--json",
        "databaseId,status,conclusion,headSha,event",
    ]
    if filters.branch is not None:
        argv.extend(["--branch", filters.branch])
    if filters.workflow is not None:
        argv.extend(["--workflow", filters.workflow])
    if filters.event is not None:
        argv.extend(["--event", filters.event])
    if filters.status is not None:
        argv.extend(["--status", filters.status])
    if filters.commit is not None:
        argv.extend(["--commit", filters.commit])
    return _retry_read(runner, argv, cwd=filters.cwd)


def run_list_filtered(
    runner: Runner,
    filters: WorkflowRunListFilters,
) -> tuple[WorkflowRun, ...]:
    """Return filtered workflow runs with head SHA and event metadata."""
    result = run_list_filtered_read(runner, filters)
    if result.returncode != 0:
        _raise_read_failure(result)
    rows_obj = _as_json_list(
        _loads_json(result.stdout or "[]", context="run list filtered"),
        context="run list filtered",
    )
    runs: list[WorkflowRun] = []
    for row_obj in rows_obj:
        row = _as_json_object(row_obj, context="run list filtered row")
        runs.append(_workflow_run_from_json(row, context="run list filtered"))
    return tuple(runs)


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
        runs.append(_workflow_run_from_json(row, context="run list"))
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
    return _workflow_run_from_json(data, context="run view")


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


def parse_failed_jobs_json(stdout: str) -> tuple[FailedJob, ...]:
    """Parse failed jobs from a single ``gh run view --json jobs`` payload."""
    payload = _as_json_object(
        _loads_json(stdout, context="failed jobs"),
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
    return parse_failed_jobs_json(result.stdout)


_HARNESS_JOB_NAME_RE = re.compile(r"^test-harnesses \((\d+)\)$")


def _job_wall_clock_seconds(*, started: object, completed: object) -> float | None:
    """Return ``completed - started`` in seconds, or None when unusable.

    Non-string stamps, unparseable timestamps, and non-positive deltas (a
    not-yet-completed job reports a zero-value ``completedAt``) all yield None
    so the caller skips that job rather than recording a bogus duration.
    ``datetime.fromisoformat`` parses the trailing ``Z`` natively on Python 3.11+
    (this repo's floor), so no offset normalization is needed.
    """
    if not isinstance(started, str) or not isinstance(completed, str):
        return None
    try:
        start = datetime.fromisoformat(started)
        end = datetime.fromisoformat(completed)
    except ValueError:
        return None
    seconds = (end - start).total_seconds()
    return seconds if seconds > 0 else None


def parse_job_durations_json(stdout: str) -> dict[int, float]:
    """Parse ``{shard: wall_clock_seconds}`` from a ``gh run view --json jobs`` payload.

    Keys are the shard index parsed from ``test-harnesses (N)`` job names; values
    are ``completedAt - startedAt`` in seconds. Jobs whose name does not match the
    matrix pattern, or that lack usable timestamps, are skipped. Accepts the
    camelCase stamps emitted by ``gh run view --json jobs`` and the snake_case
    stamps from the raw ``/jobs`` REST payload.
    """
    payload = _as_json_object(
        _loads_json(stdout, context="job durations"),
        context="job durations",
    )
    jobs_raw = payload.get("jobs", [])
    if not isinstance(jobs_raw, list):
        msg = "gh JSON missing required keys ['jobs'] (job durations)"
        raise ShipError(msg)
    jobs = cast("list[object]", jobs_raw)
    durations: dict[int, float] = {}
    for job_obj in jobs:
        if not isinstance(job_obj, dict):
            continue
        job = cast("dict[str, object]", job_obj)
        name = job.get("name")
        if not isinstance(name, str):
            continue
        name_match = _HARNESS_JOB_NAME_RE.match(name)
        if name_match is None:
            continue
        started = job.get("startedAt") or job.get("started_at")
        completed = job.get("completedAt") or job.get("completed_at")
        seconds = _job_wall_clock_seconds(started=started, completed=completed)
        if seconds is None:
            continue
        durations[int(name_match.group(1))] = seconds
    return durations


def job_durations(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> dict[int, float]:
    """Return ``{shard: wall_clock_seconds}`` for ``test-harnesses (N)`` jobs.

    Reuses the ``gh run view --json jobs`` read behind ``failed_jobs_read`` and
    derives each shard's real CI wall-clock from its ``startedAt``/``completedAt``
    stamps. Raises ``ShipError`` / ``TransientNetworkError`` on a failed read.
    """
    result = failed_jobs_read(runner, run_id, repo=repo, cwd=cwd)
    if result.returncode != 0:
        _raise_read_failure(result)
    return parse_job_durations_json(result.stdout)


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


def run_log_read(
    runner: Runner,
    run_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    """Download the full combined log for a workflow run (gh run view --log)."""
    return _retry_read(runner, ["run", "view", str(run_id), "--log", "--repo", repo], cwd=cwd)


def run_list_successful_read(
    runner: Runner,
    *,
    repo: str,
    branch: str | None = None,
    workflow: str | None = None,
    limit: int = 5,
    cwd: str | None = None,
) -> CommandResult:
    """List successful workflow runs with optional branch and workflow filters."""
    argv = [
        "run",
        "list",
        "--repo",
        repo,
        "--status",
        "success",
        "--limit",
        str(limit),
        "--json",
        "databaseId,status,conclusion",
    ]
    if branch is not None:
        argv.extend(["--branch", branch])
    if workflow is not None:
        argv.extend(["--workflow", workflow])
    return _retry_read(runner, argv, cwd=cwd)


def run_list_successful(
    runner: Runner,
    *,
    repo: str,
    branch: str | None = None,
    workflow: str | None = None,
    limit: int = 5,
    cwd: str | None = None,
) -> tuple[WorkflowRun, ...]:
    """Return successful workflow runs (typed), optionally filtered by branch/workflow."""
    result = run_list_successful_read(
        runner, repo=repo, branch=branch, workflow=workflow, limit=limit, cwd=cwd
    )
    if result.returncode != 0:
        _raise_read_failure(result)
    rows_obj = _as_json_list(
        _loads_json(result.stdout or "[]", context="run list successful"),
        context="run list successful",
    )
    runs: list[WorkflowRun] = []
    for row_obj in rows_obj:
        row = _as_json_object(row_obj, context="run list successful row")
        runs.append(_workflow_run_from_json(row, context="run list successful"))
    return tuple(runs)


def workflow_dispatch(
    runner: Runner,
    workflow: str,
    *,
    repo: str,
    ref: str,
    cwd: str | None = None,
) -> CommandResult:
    """Trigger a workflow_dispatch event on a branch (gh workflow run)."""
    return _gh(
        runner,
        ["workflow", "run", workflow, "--repo", repo, "--ref", ref],
        cwd=cwd,
    )


def api_read(
    runner: Runner,
    args: Sequence[str],
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(runner, ["api", *args], cwd=cwd)


def issue_comments_list_read(
    runner: Runner,
    issue: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
        runner,
        ["api", f"/repos/{repo}/issues/{issue}/comments", "--paginate"],
        cwd=cwd,
    )


def issue_blocked_by_read(
    runner: Runner,
    issue: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
        runner,
        ["api", f"repos/{repo}/issues/{issue}/dependencies/blocked_by", "--paginate"],
        cwd=cwd,
    )


def issue_blocking_read(
    runner: Runner,
    issue: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _retry_read(
        runner,
        ["api", f"repos/{repo}/issues/{issue}/dependencies/blocking", "--paginate"],
        cwd=cwd,
    )


def _issue_view_read(
    runner: Runner,
    issue: str,
    fields: str,
    *,
    repo: str | None = None,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["issue", "view", str(issue), "--json", fields]
    if repo:
        argv.extend(["--repo", repo])
    return _retry_read(runner, argv, cwd=cwd)


def issue_view_state_url_read(
    runner: Runner,
    issue: str,
    *,
    repo: str | None = None,
    cwd: str | None = None,
) -> CommandResult:
    return _issue_view_read(runner, issue, "state,url", repo=repo, cwd=cwd)


def issue_view_field_read(
    runner: Runner,
    issue: str,
    field: str,
    *,
    repo: str | None = None,
    cwd: str | None = None,
) -> CommandResult:
    return _issue_view_read(runner, issue, field, repo=repo, cwd=cwd)


def issue_view_title_body_read(
    runner: Runner,
    issue: str,
    *,
    repo: str | None = None,
    cwd: str | None = None,
) -> CommandResult:
    return _issue_view_read(runner, issue, "title,body", repo=repo, cwd=cwd)


def find_issue_comment_id_by_marker(
    runner: Runner,
    issue: str,
    marker: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> int | None:
    """Return comment id, None when absent, -1 when multiple match (bash parity)."""
    result = issue_comments_list_read(runner, issue, repo=repo, cwd=cwd)
    if result.returncode != 0:
        msg = f"gh api comments fetch failed ({result.returncode})"
        raise ShipError(msg)
    rows_obj = _loads_json_paginated_list(result.stdout or "[]", context="issue comments")
    ids: list[int] = []
    for row_obj in rows_obj:
        row = _as_json_object(row_obj, context="issue comment row")
        body_obj = row.get("body")
        body = body_obj if isinstance(body_obj, str) else str(body_obj or "")
        first_line = (
            body.split("\n", 1)[0].removeprefix("\ufeff").rstrip("\r")
            if body
            else ""
        )
        if first_line == marker:
            ids.append(_as_int(row["id"], context="issue comments", field="id"))
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]
    return -1


def issue_comment_delete(
    runner: Runner,
    comment_id: int,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    def attempt() -> tuple[CommandResult, int, str]:
        result = _gh(
            runner,
            ["api", f"/repos/{repo}/issues/comments/{comment_id}", "-X", "DELETE"],
            cwd=cwd,
        )
        return result, result.returncode, _combined(result)

    return with_transient_retry(attempt).value


def issue_comment_patch(
    runner: Runner,
    comment_id: int,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    redacted = _fail_closed_redacted(body, context="gh issue comment patch")
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as handle:
        _ = handle.write(json.dumps({"body": redacted}))
        path = handle.name
    try:
        return _gh(
            runner,
            [
                "api",
                f"/repos/{repo}/issues/comments/{comment_id}",
                "-X",
                "PATCH",
                "--input",
                path,
            ],
            cwd=cwd,
        )
    finally:
        Path(path).unlink(missing_ok=True)



def issue_create(
    runner: Runner,
    *,
    repo: str | None,
    title: str,
    body: str,
    cwd: str | None = None,
    redact_body: bool = True,
) -> CommandResult:
    argv = ["issue", "create", "--title", _redact_gh_scalar(title)]
    if repo:
        argv.extend(["--repo", repo])
    with _body_file_args(body, redact_body=redact_body) as (body_flag, body_path):
        argv.extend([body_flag, body_path])
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


def issue_comment_with_retry(
    runner: Runner,
    issue: str,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    def attempt() -> tuple[CommandResult, int, str]:
        result = issue_comment(runner, issue, body, repo=repo, cwd=cwd)
        return result, result.returncode, _combined(result)

    return with_transient_retry(attempt).value


def issue_labels_list(
    runner: Runner,
    issue: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> list[str]:
    result = _retry_read(
        runner,
        [
            "issue",
            "view",
            issue,
            "--repo",
            repo,
            "--json",
            "labels",
            "--jq",
            ".labels[].name",
        ],
        cwd=cwd,
    )
    if result.returncode != 0:
        raise ShipError(_combined(result) or f"gh issue labels failed ({result.returncode})")
    return [line for line in result.stdout.splitlines() if line]


def issue_label_add(
    runner: Runner,
    issue: str,
    label: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    def attempt() -> tuple[CommandResult, int, str]:
        result = _gh(
            runner,
            ["issue", "edit", issue, "--repo", repo, "--add-label", label],
            cwd=cwd,
        )
        return result, result.returncode, _combined(result)

    return with_transient_retry(attempt).value


def issue_label_remove(
    runner: Runner,
    issue: str,
    label: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    def attempt() -> tuple[CommandResult, int, str]:
        result = _gh(
            runner,
            ["issue", "edit", issue, "--repo", repo, "--remove-label", label],
            cwd=cwd,
        )
        return result, result.returncode, _combined(result)

    return with_transient_retry(attempt).value


def label_create(
    runner: Runner,
    label: str,
    *,
    repo: str,
    color: str = "D73A4A",
    description: str = "",
    cwd: str | None = None,
) -> CommandResult:
    return _gh(
        runner,
        [
            "label",
            "create",
            label,
            "--repo",
            repo,
            "--color",
            color,
            "--description",
            description,
        ],
        cwd=cwd,
    )



def issue_view_body(
    runner: Runner,
    issue: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> str:
    result = _retry_read(
        runner,
        ["issue", "view", issue, "--repo", repo, "--json", "body"],
        cwd=cwd,
    )
    if result.returncode != 0:
        msg = _combined(result) or f"gh issue view failed ({result.returncode})"
        raise ShipError(msg)
    data = _as_json_object(_loads_json(result.stdout, context="issue view body"), context="issue view body")
    body = data.get("body")
    if body is None:
        return ""
    if isinstance(body, str):
        return body
    msg = "gh JSON field 'body' is not a string (issue view body)"
    raise ShipError(msg)


def repo_name_with_owner_read(runner: Runner, *, cwd: str | None = None) -> CommandResult:
    return _retry_read(
        runner,
        ["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=cwd,
    )


def resolve_repo_gh_only(runner: Runner, *, cwd: str | None = None) -> str | None:
    result = repo_name_with_owner_read(runner, cwd=cwd)
    if result.returncode != 0:
        return None
    candidate = result.stdout.strip()
    return candidate if validate_repo_slug(candidate) else None


def issue_edit_body_with_retry(
    runner: Runner,
    issue: str,
    redacted_body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        delete=False,
    ) as handle:
        _ = handle.write(redacted_body)
        path = handle.name
    try:
        def attempt() -> tuple[CommandResult, int, str]:
            result = _gh(
                runner,
                ["issue", "edit", issue, "--repo", repo, "--body-file", path],
                cwd=cwd,
            )
            return result, result.returncode, _combined(result)

        retried: RetryResult[CommandResult] = with_transient_retry(attempt)
        result = retried.value
        if result.returncode != 0:
            raise ShipError(_combined(result) or f"gh issue edit failed ({result.returncode})")
        return result
    finally:
        Path(path).unlink(missing_ok=True)


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


_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


def validate_repo_slug(value: str) -> bool:
    if not value or "\n" in value or "\r" in value:
        return False
    if value.startswith(("--", "/")) or "../" in value or "\\" in value:
        return False
    return _REPO_RE.fullmatch(value) is not None


def remote_repo(
    runner: Runner,
    remote_or_url: str,
    *,
    cwd: str | None = None,
) -> str | None:
    if "://" in remote_or_url or "@" in remote_or_url:
        url = remote_or_url
    else:
        result = runner.run(["git", "remote", "get-url", remote_or_url], cwd=cwd)
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
    url = url.rstrip("/")
    url = url.removesuffix(".git")
    url = url.rstrip("/")
    match = re.match(r"^git@github[.]com:([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)$", url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    match = re.match(
        r"^(?:https?|ssh|git)://(?:[^@]+@)?github[.]com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)$",
        url,
    )
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return None


def resolve_repo(runner: Runner, *, cwd: str | None = None) -> str | None:
    result = repo_name_with_owner_read(runner, cwd=cwd)
    candidate = result.stdout.strip() if result.returncode == 0 else ""
    if not candidate:
        candidate = remote_repo(runner, "origin", cwd=cwd) or ""
    return candidate if validate_repo_slug(candidate) else None


def pr_edit_body_file(
    runner: Runner,
    pr_number: str,
    body_file: str,
    *,
    repo: str | None = None,
    cwd: str | None = None,
) -> BodyUpdateResult:
    if not Path(body_file).is_file():
        return BodyUpdateResult(updated=False, error=f"body file not found: {body_file}", exit_code=2)

    argv = ["gh", "pr", "edit", pr_number]
    if repo:
        argv.extend(["--repo", repo])
    argv.extend(["--body-file", body_file])

    def attempt() -> tuple[CommandResult, int, str]:
        result = runner.run(argv, cwd=cwd)
        return result, result.returncode, result.stdout + result.stderr

    retried: RetryResult[CommandResult] = with_transient_retry(attempt)
    result = retried.value
    if result.returncode == 0:
        return BodyUpdateResult(updated=True, error="", exit_code=0)
    output = redact.redact(result.stdout + result.stderr).replace("\n", " ").strip()
    return BodyUpdateResult(
        updated=False,
        error=f"gh pr edit failed (exit {result.returncode}): {output}",
        exit_code=2,
    )


def run_log_failed_read(
    runner: Runner,
    run_id: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> CommandResult:
    return _gh(
        runner,
        ["run", "view", run_id, "--repo", repo, "--log-failed"],
        cwd=cwd,
        timeout=_effective_read_timeout(None),
    )


def run_logs_failed(
    runner: Runner,
    run_id: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> tuple[str, int]:
    pointer = (
        f"--- CI log (run {run_id}, repo {repo}): failed-job log shown. "
        f"Full log: https://github.com/{repo}/actions/runs/{run_id} ---"
    )
    result = run_log_failed_read(runner, run_id, repo=repo, cwd=cwd)
    combined = result.stdout + result.stderr
    text = f"{pointer}\n"
    if combined:
        text += combined
        if not combined.endswith("\n"):
            text += "\n"
    if result.returncode != 0 and "is still in progress; logs will be available" in combined:
        return text, 3
    if result.returncode != 0:
        return text, 1
    return text, 0


def extract_closes_issue(body: str) -> str:
    match = re.search(r"Closes #([0-9]+)", body)
    return match.group(1) if match else ""


def extract_closes_issue_from_current_pr(
    runner: Runner,
    *,
    repo: str,
    cwd: str | None = None,
) -> str:
    result = _retry_read(
        runner,
        ["pr", "view", "--repo", repo, "--json", "body", "--jq", ".body"],
        cwd=cwd,
    )
    if result.returncode != 0:
        return ""
    return extract_closes_issue(result.stdout)


# CLI entrypoints migrated from gh_cli.py.
def resolve_repo_main(argv: list[str]) -> int:
    if argv:
        print(f"resolve-repo.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    repo = resolve_repo(proc)
    if not repo:
        print("ERROR=could not resolve repo (gh repo view + git remote both failed)", file=sys.stderr)
        return 1
    print(repo)
    return 0


def remote_repo_main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: github-remote-repo.sh <remote-name-or-url>", file=sys.stderr)
        return 2
    repo = remote_repo(proc, argv[0])
    if not repo:
        print("github-remote-repo.sh: cannot parse remote", file=sys.stderr)
        return 2
    print(repo)
    return 0


def run_logs_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py gh run-logs")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    text, rc = run_logs_failed(proc, args.run_id, repo=args.repo)
    sys.stdout.write(text)
    return rc


def workflow_path_main(_argv: list[str]) -> int:
    print("unknown")
    return 0
