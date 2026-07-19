"""Typed, freshness-checked ownership of GitHub issue field mutations.

The GitHub adapter remains a thin transport layer.  This module owns the
compare-and-swap, in-flight body protection, outbound redaction, and read-back
postcondition required by every title, body, label, and named-block write.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Final, cast

from larch.core import redact
from larch.core.proc import Runner
from larch.errors import ShipError
from larch.git import gh
from larch.issue import issue_blocks
from larch.core import config
from larch.issue.title_match import LIFECYCLE_PREFIXES, detect_lifecycle_prefix

_MANAGED_BUSY_STATES: Final = ("designing", "implementing", "stalled", "done")
_MANAGED_PREFIXES: Final = frozenset(config.TRACKING_ISSUE_PREFIX_BY_STATE.values())
_BUSY_PREFIXES: Final = frozenset(
    [config.TRACKING_ISSUE_PREFIX_BY_STATE[state].strip() for state in _MANAGED_BUSY_STATES]
    + [prefix.strip() for prefix in LIFECYCLE_PREFIXES if prefix not in _MANAGED_PREFIXES]
)
_UPDATED_AT_RE: Final = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class MutationField(StrEnum):
    TITLE = "title"
    BODY = "body"
    LABELS = "labels"
    NAMED_BLOCK = "named-block"


class ProtectedIssueMutation(ShipError):
    """Stable fail-closed error for every rejected or unverifiable mutation."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"protected-issue-mutation:{reason}")
        self.reason = reason


@dataclass(frozen=True)
class IssueSnapshot:
    repository: str
    issue: str
    title: str
    body: str
    labels: frozenset[str]
    state: str
    updated_at: str


@dataclass(frozen=True)
class ImplementationLease:
    """Optional identity binding a protected marker mutation to one run."""

    run_id: str
    marker: str


@dataclass(frozen=True)
class IssueMutationRequest:
    repository: str
    issue: str
    expected_updated_at: str
    expected_state: str
    fields: frozenset[MutationField]
    title: str | None = None
    body: str | None = None
    labels: frozenset[str] | None = None
    marker: str | None = None
    lease: ImplementationLease | None = None


@dataclass(frozen=True)
class VerifiedIssueMutation:
    before: IssueSnapshot
    after: IssueSnapshot
    fields: frozenset[MutationField]


def _failure(reason: str) -> ProtectedIssueMutation:
    return ProtectedIssueMutation(reason)


def _as_snapshot(*, repository: str, issue: str, stdout: str) -> IssueSnapshot:
    try:
        value: object = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise _failure("invalid-read-back") from exc
    if not isinstance(value, dict):
        raise _failure("invalid-read-back")
    payload = cast("dict[str, object]", value)
    labels_value = payload.get("labels")
    if not isinstance(labels_value, list):
        raise _failure("invalid-read-back")
    labels: set[str] = set()
    for item in cast("list[object]", labels_value):
        if not isinstance(item, dict):
            raise _failure("invalid-read-back")
        row = cast("dict[str, object]", item)
        name = row.get("name")
        if not isinstance(name, str):
            raise _failure("invalid-read-back")
        labels.add(name)
    title, body, state, updated_at = (
        payload.get("title"),
        payload.get("body"),
        payload.get("state"),
        payload.get("updatedAt"),
    )
    if (
        not isinstance(title, str)
        or not isinstance(body, str)
        or not isinstance(state, str)
        or not isinstance(updated_at, str)
    ):
        raise _failure("invalid-read-back")
    if not _UPDATED_AT_RE.fullmatch(updated_at):
        raise _failure("invalid-read-back")
    return IssueSnapshot(
        repository=repository,
        issue=issue,
        title=title,
        body=body,
        labels=frozenset(labels),
        state=state,
        updated_at=updated_at,
    )


def read_snapshot(
    runner: Runner, *, repository: str, issue: str, cwd: str | None = None
) -> IssueSnapshot:
    if not gh.validate_repo_slug(repository) or not issue.isdecimal() or issue == "0":
        raise _failure("invalid-identity")
    result = gh.issue_mutation_snapshot_read(runner, issue, repo=repository, cwd=cwd)
    if result.returncode != 0:
        raise _failure("read-failed")
    return _as_snapshot(repository=repository, issue=issue, stdout=result.stdout)


def request_for_snapshot(  # noqa: PLR0913 - mutation request mirrors the fixed GitHub field contract.
    snapshot: IssueSnapshot,
    *,
    fields: frozenset[MutationField],
    title: str | None = None,
    body: str | None = None,
    labels: frozenset[str] | None = None,
    marker: str | None = None,
    lease: ImplementationLease | None = None,
) -> IssueMutationRequest:
    return IssueMutationRequest(
        repository=snapshot.repository,
        issue=snapshot.issue,
        expected_updated_at=snapshot.updated_at,
        expected_state=snapshot.state,
        fields=fields,
        title=title,
        body=body,
        labels=labels,
        marker=marker,
        lease=lease,
    )


def _validate_request(request: IssueMutationRequest) -> None:  # noqa: C901 - each branch rejects one invalid request shape.
    if not gh.validate_repo_slug(request.repository) or not request.issue.isdecimal() or request.issue == "0":
        raise _failure("invalid-identity")
    if not _UPDATED_AT_RE.fullmatch(request.expected_updated_at) or not request.expected_state:
        raise _failure("invalid-expected-identity")
    if not request.fields:
        raise _failure("missing-allowed-field")
    if MutationField.NAMED_BLOCK in request.fields:
        if request.fields != frozenset({MutationField.NAMED_BLOCK}) or not request.marker or request.body is None:
            raise _failure("invalid-named-block-request")
    elif request.marker is not None or request.lease is not None:
        raise _failure("unexpected-marker-or-lease")
    if (MutationField.TITLE in request.fields) != (request.title is not None):
        raise _failure("invalid-title-request")
    if MutationField.NAMED_BLOCK not in request.fields and (
        (MutationField.BODY in request.fields) != (request.body is not None)
    ):
        raise _failure("invalid-body-request")
    if (MutationField.LABELS in request.fields) != (request.labels is not None):
        raise _failure("invalid-label-request")
    if MutationField.NAMED_BLOCK not in request.fields and request.body is not None and MutationField.BODY not in request.fields:
        raise _failure("invalid-body-request")
    if request.lease is not None and (not request.lease.run_id or request.lease.marker != request.marker):
        raise _failure("invalid-lease")


def _is_protected(snapshot: IssueSnapshot) -> bool:
    prefix = detect_lifecycle_prefix(snapshot.title).strip().upper()
    return prefix in _BUSY_PREFIXES


def _only_named_block_changed(*, before: str, after: str, marker: str) -> bool:
    old_outer, old_error = issue_blocks.strip_named_block(body=before, marker=marker)
    new_outer, new_error = issue_blocks.strip_named_block(body=after, marker=marker)
    if old_error != "" or new_error != "":
        return False
    if old_outer.rstrip() == new_outer.rstrip():
        return True
    if marker != "plan":
        return False
    # Plan writes may also refresh the adjacent plan-receipt without counting
    # as a foreign body edit (M5 receipt persistence).
    from larch.issue import migration_governance  # noqa: PLC0415 - lint-layering: ok plan-receipt strip owned by migration_governance; avoid import cycle at module load

    old_norm = migration_governance.strip_plan_receipt_lines(body=old_outer)
    new_norm = migration_governance.strip_plan_receipt_lines(body=new_outer)
    return old_norm.rstrip() == new_norm.rstrip()


def _redact_body(body: str) -> str:
    try:
        redacted = redact.redact_secrets_only(body)
    except Exception as exc:  # pragma: no cover - defensive redaction boundary
        raise _failure("redaction-failed") from exc
    if "[content truncated" in redacted:
        raise _failure("redaction-failed")
    return redacted


def _redact_title(title: str) -> str:
    return _redact_body(title).rstrip("\r\n")


def _verify_authorized_body_change(request: IssueMutationRequest, before: IssueSnapshot) -> str | None:
    body = request.body
    if body is None:
        return None
    redacted_body = _redact_body(body)
    if MutationField.NAMED_BLOCK not in request.fields:
        if _is_protected(before):
            raise _failure("protected-body")
        return redacted_body
    assert request.marker is not None
    if not _only_named_block_changed(before=before.body, after=redacted_body, marker=request.marker):
        raise _failure("foreign-marker-or-body-change")
    if _is_protected(before) and request.lease is None:
        raise _failure("missing-lease")
    return redacted_body


def _same_identity(before: IssueSnapshot, request: IssueMutationRequest) -> bool:
    return before.updated_at == request.expected_updated_at and before.state == request.expected_state


def _perform_write(
    runner: Runner,
    *,
    request: IssueMutationRequest,
    before: IssueSnapshot,
    body: str | None,
    cwd: str | None,
) -> None:
    title = request.title if MutationField.TITLE in request.fields else None
    if title is not None or body is not None:
        result = gh.issue_edit(
            runner, request.issue, repo=request.repository, title=title, body=body, cwd=cwd
        )
        if result.returncode != 0:
            raise _failure("write-failed")
    if MutationField.LABELS in request.fields:
        assert request.labels is not None
        for label in sorted(before.labels - request.labels):
            result = gh.issue_label_remove(runner, request.issue, label, repo=request.repository, cwd=cwd)
            if result.returncode != 0:
                raise _failure("write-failed")
        for label in sorted(request.labels - before.labels):
            result = gh.issue_label_add(runner, request.issue, label, repo=request.repository, cwd=cwd)
            if result.returncode != 0:
                raise _failure("write-failed")


def _postcondition(after: IssueSnapshot, request: IssueMutationRequest, body: str | None) -> bool:
    if MutationField.TITLE in request.fields and after.title != request.title:
        return False
    if (MutationField.BODY in request.fields or MutationField.NAMED_BLOCK in request.fields) and after.body != body:
        return False
    return not (MutationField.LABELS in request.fields and after.labels != request.labels)


def _would_change(before: IssueSnapshot, request: IssueMutationRequest, body: str | None) -> bool:
    return any(
        (
            MutationField.TITLE in request.fields and before.title != request.title,
            (MutationField.BODY in request.fields or MutationField.NAMED_BLOCK in request.fields)
            and before.body != body,
            MutationField.LABELS in request.fields and before.labels != request.labels,
        )
    )


def apply(
    runner: Runner, request: IssueMutationRequest, *, cwd: str | None = None
) -> VerifiedIssueMutation:
    """Apply exactly the requested fields and prove the postcondition by read-back."""
    _validate_request(request)
    before = read_snapshot(runner, repository=request.repository, issue=request.issue, cwd=cwd)
    if not _same_identity(before, request):
        raise _failure("stale-identity")
    body = _verify_authorized_body_change(request, before)
    title = _redact_title(request.title) if request.title is not None else None
    request = replace(request, title=title)
    if not _would_change(before, request, body):
        return VerifiedIssueMutation(before=before, after=before, fields=request.fields)
    try:
        _perform_write(runner, request=request, before=before, body=body, cwd=cwd)
    except ProtectedIssueMutation:
        # A transport failure can arrive after GitHub accepted an idempotent
        # field replacement. Reconcile once by read-back instead of retrying a
        # mutation whose outcome is uncertain.
        after = read_snapshot(runner, repository=request.repository, issue=request.issue, cwd=cwd)
        if after.updated_at > before.updated_at and _postcondition(after, request, body):
            return VerifiedIssueMutation(before=before, after=after, fields=request.fields)
        raise
    after = read_snapshot(runner, repository=request.repository, issue=request.issue, cwd=cwd)
    if after.updated_at <= before.updated_at:
        raise _failure("non-fresh-read-back")
    if not _postcondition(after, request, body):
        raise _failure("postcondition-failed")
    return VerifiedIssueMutation(before=before, after=after, fields=request.fields)


def update_title(
    runner: Runner, *, repository: str, issue: str, title: str, cwd: str | None = None
) -> VerifiedIssueMutation:
    snapshot = read_snapshot(runner, repository=repository, issue=issue, cwd=cwd)
    return apply(
        runner,
        request_for_snapshot(
            snapshot, fields=frozenset({MutationField.TITLE}), title=title
        ),
        cwd=cwd,
    )


def update_body(
    runner: Runner, *, repository: str, issue: str, body: str, cwd: str | None = None
) -> VerifiedIssueMutation:
    snapshot = read_snapshot(runner, repository=repository, issue=issue, cwd=cwd)
    return apply(
        runner,
        request_for_snapshot(
            snapshot, fields=frozenset({MutationField.BODY}), body=body
        ),
        cwd=cwd,
    )


def update_labels(
    runner: Runner,
    *,
    repository: str,
    issue: str,
    labels: frozenset[str],
    cwd: str | None = None,
) -> VerifiedIssueMutation:
    snapshot = read_snapshot(runner, repository=repository, issue=issue, cwd=cwd)
    return apply(
        runner,
        request_for_snapshot(
            snapshot, fields=frozenset({MutationField.LABELS}), labels=labels
        ),
        cwd=cwd,
    )


def update_named_block(  # noqa: PLR0913 - named-block identity and lease are deliberately explicit.
    runner: Runner,
    *,
    repository: str,
    issue: str,
    marker: str,
    body: str,
    lease: ImplementationLease | None = None,
    cwd: str | None = None,
) -> VerifiedIssueMutation:
    snapshot = read_snapshot(runner, repository=repository, issue=issue, cwd=cwd)
    return apply(
        runner,
        request_for_snapshot(
            snapshot,
            fields=frozenset({MutationField.NAMED_BLOCK}),
            body=body,
            marker=marker,
            lease=lease,
        ),
        cwd=cwd,
    )
