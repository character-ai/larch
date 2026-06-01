"""Tracking-issue lifecycle helpers."""

from __future__ import annotations

import re

import config
import gh
import redact
from errors import ShipError
from proc import Runner

_MARKER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_LIFECYCLE_PREFIX_RE = re.compile(
    r"^\[(?:DESIGNING|DESIGNED|IMPLEMENTING|DONE|STALLED|IN PROGRESS|PLANNED)\] ",
)


def _redact_title(title: str) -> str:
    redacted = redact.redact(title)
    if "[content truncated" in redacted:
        msg = "redaction failed for tracking-issue title"
        raise ShipError(msg)
    return redacted.rstrip("\n")


def _compose_title(current_title: str, state: str) -> str:
    if state not in config.TRACKING_ISSUE_PREFIX_BY_STATE:
        msg = f"unknown tracking issue state: {state!r}"
        raise ShipError(msg)
    stripped = _LIFECYCLE_PREFIX_RE.sub("", current_title, count=1)
    prefix = config.TRACKING_ISSUE_PREFIX_BY_STATE[state]
    composed = f"{prefix}{stripped}"
    if len(composed) <= config.TRACKING_TITLE_MAX_LEN:
        return composed
    tail_budget = config.TRACKING_TITLE_MAX_LEN - len(prefix)
    return prefix + stripped[:tail_budget]


def rename(
    runner: Runner,
    issue: str,
    state: str,
    *,
    repo: str,
    current_title: str,
    cwd: str | None = None,
) -> str:
    """Strip one lifecycle prefix and prepend the new state prefix."""
    new_title = _compose_title(current_title, state)
    if new_title == current_title:
        return current_title
    redacted = _redact_title(new_title)
    prefix = config.TRACKING_ISSUE_PREFIX_BY_STATE[state]
    stripped = _LIFECYCLE_PREFIX_RE.sub("", redacted, count=1)
    tail_budget = config.TRACKING_TITLE_MAX_LEN - len(prefix)
    if len(stripped) > tail_budget:
        redacted = prefix + stripped[:tail_budget]
    result = gh.issue_edit(
        runner,
        issue,
        repo=repo,
        title=redacted,
        cwd=cwd,
    )
    if result.returncode != 0:
        msg = f"gh issue edit rename failed ({result.returncode})"
        raise ShipError(msg)
    return redacted


def append_comment(
    runner: Runner,
    issue: str,
    body: str,
    *,
    repo: str,
    lifecycle_marker: str | None = None,
    cwd: str | None = None,
) -> None:
    if lifecycle_marker is not None:
        if "--" in lifecycle_marker or not _MARKER_RE.match(lifecycle_marker):
            msg = "invalid lifecycle marker"
            raise ShipError(msg)
        body = f"<!-- larch:lifecycle-marker:{lifecycle_marker} -->\n{body}"
    redacted = redact.redact(body)
    if "[content truncated" in redacted:
        msg = "redaction failed for tracking-issue comment"
        raise ShipError(msg)
    result = gh.issue_comment(runner, issue, redacted, repo=repo, cwd=cwd)
    if result.returncode != 0:
        msg = f"gh issue comment failed ({result.returncode})"
        raise ShipError(msg)


def _upsert_marker(marker: str) -> str:
    return f"<!-- larch:{marker} -->"


def _upsert_marker_comment(
    runner: Runner,
    issue: str,
    marker: str,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> None:
    full_body = f"{marker}\n{body}"
    redacted = redact.redact(full_body)
    if "[content truncated" in redacted:
        msg = "redaction failed for tracking-issue comment"
        raise ShipError(msg)
    comment_id = gh.find_issue_comment_id_by_marker(
        runner,
        issue,
        marker,
        repo=repo,
        cwd=cwd,
    )
    if comment_id is None:
        result = gh.issue_comment(runner, issue, redacted, repo=repo, cwd=cwd)
        if result.returncode != 0:
            msg = f"gh issue comment failed ({result.returncode})"
            raise ShipError(msg)
        return
    if comment_id < 0:
        msg = f"multiple tracking comments found for marker {marker!r}"
        raise ShipError(msg)
    result = gh.issue_comment_patch(
        runner,
        comment_id,
        redacted,
        repo=repo,
        cwd=cwd,
    )
    if result.returncode != 0:
        msg = f"gh issue comment patch failed ({result.returncode})"
        raise ShipError(msg)


def upsert_summary(
    runner: Runner,
    issue: str,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> None:
    _upsert_marker_comment(
        runner,
        issue,
        _upsert_marker("final-summary"),
        body,
        repo=repo,
        cwd=cwd,
    )


def upsert_token_report(
    runner: Runner,
    issue: str,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> None:
    _upsert_marker_comment(
        runner,
        issue,
        _upsert_marker("token-report"),
        body,
        repo=repo,
        cwd=cwd,
    )


def link_pr_closes(body: str, issue_number: int) -> str:
    """Ensure Closes #N appears in the PR body."""
    needle = f"Closes #{issue_number}"
    if needle in body:
        return body
    return body.rstrip() + f"\n\n{needle}\n"
