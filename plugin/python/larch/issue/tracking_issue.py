# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Tracking-issue lifecycle helpers the larch runtime calls in process.

The six `tracking-issue` commands moved to the Rust owner in #8175. What stays
here is the library the Python `/design` and `/implement` flows still call
directly: the lifecycle rename core, the implementation-lease transitions, the
marker-keyed comment upsert, the pull-request disposition footers, and the
adoption sentinel reader.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from larch.core import config
from larch.git import gh
from larch.issue import issue_wire
from larch.issue import issue_mutation
from larch.issue.title_match import detect_lifecycle_prefix, strip_lifecycle_prefix
from larch.core import redact
from larch.errors import ShipError
from larch.core.proc import CommandResult, Runner
from larch.core.retry import with_transient_retry

LIFECYCLE_MARKER_PREFIX = "<!-- larch:lifecycle-marker:"

_MARKER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_COMMENT_URL_RE = re.compile(r"(https?://[^\s]+#issuecomment-(\d+))")

# Refusal codes the surviving library raises through CliFailure: 1 for a
# validated rejection and 2 for a transport or content-state failure. The Rust
# `tracking-issue` verbs publish the same two plus 3 for a compose-time
# redaction that failed closed.


@dataclass(frozen=True)
class RenameOutput:
    renamed: bool
    new_title: str


@dataclass(frozen=True)
class ImplementationLeaseRun:
    """Repository identity for one implementation-lease mutation."""

    issue: str
    repo: str
    run_id: str
    cwd: str | None = None


@dataclass(frozen=True)
class UpsertSummaryOutput:
    comment_id: str
    comment_url: str
    updated: bool


@dataclass(frozen=True)
class SentinelReadResult:
    issue_number: str
    run_id: str
    adopted: str


class RedactionFailure(ShipError):
    """Compose-time redaction failed closed."""


class CliFailure(Exception):
    """Expected CLI failure with a contract envelope."""

    def __init__(self, message: str, exit_code: int, *, stderr: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.stderr = stderr


def _truncate_with_prefix(*, prefix: str, tail: str) -> str:
    budget = max(config.TRACKING_TITLE_MAX_LEN - len(prefix), 0)
    if len(prefix) + len(tail) <= config.TRACKING_TITLE_MAX_LEN:
        return f"{prefix}{tail}"
    return f"{prefix}{tail[:budget]}"


def _redact_compose(text: str, *, context: str) -> str:
    redacted = redact.redact(text)
    if "[content truncated" in redacted:
        raise RedactionFailure(f"redaction failed for {context}")
    return redacted.rstrip("\n")


def _redact_summary_body(text: str) -> str:
    redacted = redact.redact_tmpdir_paths(text)
    redacted = redact.redact_secrets_only(redacted)
    if "[content truncated" in redacted:
        raise RedactionFailure("redaction failed for tracking-issue summary")
    return redacted.rstrip("\n")


def _redact_gh_error(text: str) -> str:
    try:
        redacted = redact.redact(text)
    except Exception:
        return "gh failure: redaction unavailable"
    if "[content truncated" in redacted:
        return "gh failure: redaction unavailable"
    return redacted.replace("\n", " ").replace("\r", " ")[:500].strip() or "gh failure"


def _resolve_repo_or_fail(runner: Runner, repo: str | None, *, cwd: str | None = None) -> str:
    if repo:
        if not gh.validate_repo_slug(repo):
            raise CliFailure("invalid repo: expected OWNER/REPO", 1)
        return repo
    resolved = gh.resolve_repo(runner, cwd=cwd)
    if not resolved:
        raise CliFailure("could not determine repo", 2)
    return resolved


def _require_numeric_issue(value: str) -> str:
    if not value or not value.isdigit():
        raise CliFailure("invalid issue: expected numeric issue", 1)
    return value


def _validate_tracking_state(state: str) -> None:
    if state not in config.TRACKING_ISSUE_PREFIX_BY_STATE:
        raise CliFailure(
            f"invalid --state: {state} (expected designing|designed|implementing|done|stalled)",
            1,
        )


def _raw_comment_url(stdout: str) -> tuple[str, str] | None:
    match = _COMMENT_URL_RE.search(stdout)
    if match is None:
        return None
    return match.group(2), match.group(1)


def _comment_url_from_result(result: CommandResult) -> str:
    text = result.stdout.strip()
    if text.startswith("http"):
        return text
    try:
        data_obj: object = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return ""
    data = cast("dict[str, object]", data_obj) if isinstance(data_obj, dict) else {}
    url = data.get("html_url", "")
    return url if isinstance(url, str) else ""


def _retry_gh(result_fn: Callable[[], CommandResult]) -> CommandResult:
    def attempt() -> tuple[CommandResult, int, str]:
        result = result_fn()
        return result, result.returncode, result.stdout + result.stderr

    return with_transient_retry(attempt).value


def _read_text_file(path: str, *, label: str, require_nonempty: bool) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        raise CliFailure(f"{label} file not found: {path}", 1)
    content = file_path.read_text(encoding="utf-8")
    if require_nonempty and content.strip() == "":
        raise CliFailure("empty body" if label == "body" else f"empty {label}", 1)
    return content


def rename_with_details(
    runner: Runner,
    issue: str,
    state: str,
    *,
    repo: str,
    current_title: str,
    cwd: str | None = None,
) -> RenameOutput:
    """Shell-parity rename core shared by public adapter and CLI."""
    _require_numeric_issue(issue)
    _validate_tracking_state(state)
    target_prefix = config.TRACKING_ISSUE_PREFIX_BY_STATE[state]
    raw_tail = strip_lifecycle_prefix(current_title)
    redacted_tail = _redact_compose(raw_tail, context="tracking-issue title")
    new_title = _truncate_with_prefix(prefix=target_prefix, tail=redacted_tail)

    current_redacted = _redact_compose(current_title, context="tracking-issue title")
    current_prefix = detect_lifecycle_prefix(current_redacted)
    current_canonical = _truncate_with_prefix(prefix=current_prefix, tail=strip_lifecycle_prefix(current_redacted))
    if new_title == current_canonical:
        return RenameOutput(renamed=False, new_title=new_title)

    try:
        _ = issue_mutation.update_title(
            runner, repository=repo, issue=issue, title=new_title, cwd=cwd
        )
    except ShipError as exc:
        raise CliFailure(_redact_gh_error(str(exc)), 2) from exc
    return RenameOutput(renamed=True, new_title=new_title)


def _lease_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def initialize_implementation_lease(
    runner: Runner,
    *,
    run: ImplementationLeaseRun,
    branch: str,
    head_sha: str,
) -> issue_wire.ImplementationLeaseMarker:
    """Create and read-verify the lease before lifecycle adoption."""
    from larch.issue import migration_governance  # noqa: PLC0415 - receipt parser imports tracking mutation only lazily

    snapshot = issue_mutation.read_snapshot(
        runner, repository=run.repo, issue=run.issue, cwd=run.cwd
    )
    verdict = migration_governance.evaluate_governance_gate(
        runner,
        issue=run.issue,
        repo=run.repo,
        body=snapshot.body,
        repo_root=Path(run.cwd).resolve() if run.cwd else Path.cwd(),
        cwd=run.cwd,
        head_sha=head_sha,
    )
    if not verdict.ok:
        reasons = ",".join(verdict.blocking_reasons) or "unknown"
        raise ShipError(f"implementation-lease-admission-refused:{reasons}")
    receipt = migration_governance.parse_receipt(body=snapshot.body)
    if receipt is None:
        raise ShipError("implementation-lease-plan-receipt-missing")
    existing = issue_wire.parse_implementation_lease(body=snapshot.body)
    if existing is not None and existing.run_id != run.run_id:
        raise ShipError("implementation-lease-run-mismatch")
    lease = issue_wire.ImplementationLeaseMarker(
        run_id=run.run_id,
        branch=branch,
        base=receipt.base_sha,
        plan=receipt.plan_sha256,
        updated_at=_lease_timestamp(),
    )
    body = issue_wire.upsert_implementation_lease(body=snapshot.body, lease=lease)
    mutation = issue_mutation.update_implementation_lease(
        runner,
        repository=run.repo,
        issue=run.issue,
        body=body,
        run_id=run.run_id,
        expected_snapshot=snapshot,
        cwd=run.cwd,
    )
    verified = issue_wire.parse_implementation_lease(body=mutation.after.body)
    if verified != lease:
        raise ShipError("implementation-lease-readback-mismatch")
    post_verdict = migration_governance.evaluate_governance_gate(
        runner,
        issue=run.issue,
        repo=run.repo,
        body=mutation.after.body,
        repo_root=Path(run.cwd).resolve() if run.cwd else Path.cwd(),
        cwd=run.cwd,
        head_sha=head_sha,
    )
    if not post_verdict.ok:
        reasons = ",".join(post_verdict.blocking_reasons) or "unknown"
        terminal_error = ""
        try:
            _ = rename_terminal_with_lease(runner, "stalled", run=run)
        except ShipError as exc:
            terminal_error = f":terminal-update-failed:{exc}"
        raise ShipError(
            f"implementation-lease-post-admission-refused:{reasons}{terminal_error}"
        )
    return lease


def refresh_implementation_lease(
    runner: Runner,
    *,
    issue: str,
    repo: str,
    run_id: str,
    cwd: str | None = None,
) -> issue_wire.ImplementationLeaseMarker:
    """Refresh only the exact run-owned lease through the mutation owner."""
    snapshot = issue_mutation.read_snapshot(
        runner, repository=repo, issue=issue, cwd=cwd
    )
    existing = issue_wire.parse_implementation_lease(body=snapshot.body)
    if existing is None or existing.run_id != run_id:
        raise ShipError("implementation-lease-run-mismatch")
    lease = issue_wire.ImplementationLeaseMarker(
        run_id=existing.run_id,
        branch=existing.branch,
        base=existing.base,
        plan=existing.plan,
        updated_at=_lease_timestamp(),
    )
    body = issue_wire.upsert_implementation_lease(body=snapshot.body, lease=lease)
    mutation = issue_mutation.update_implementation_lease(
        runner,
        repository=repo,
        issue=issue,
        body=body,
        run_id=run_id,
        expected_snapshot=snapshot,
        cwd=cwd,
    )
    verified = issue_wire.parse_implementation_lease(body=mutation.after.body)
    if verified != lease:
        raise ShipError("implementation-lease-readback-mismatch")
    return lease


def rename_terminal_with_lease(
    runner: Runner,
    state: str,
    *,
    run: ImplementationLeaseRun,
) -> RenameOutput:
    """Atomically clear active title state and refresh the same run's lease."""
    _require_numeric_issue(run.issue)
    _validate_tracking_state(state)
    snapshot = issue_mutation.read_snapshot(
        runner, repository=run.repo, issue=run.issue, cwd=run.cwd
    )
    existing = issue_wire.parse_implementation_lease(body=snapshot.body)
    if existing is None or existing.run_id != run.run_id:
        raise ShipError("implementation-lease-run-mismatch")
    target_prefix = config.TRACKING_ISSUE_PREFIX_BY_STATE[state]
    tail = _redact_compose(
        strip_lifecycle_prefix(snapshot.title), context="tracking-issue title"
    )
    new_title = _truncate_with_prefix(prefix=target_prefix, tail=tail)
    lease = issue_wire.ImplementationLeaseMarker(
        run_id=existing.run_id,
        branch=existing.branch,
        base=existing.base,
        plan=existing.plan,
        updated_at=_lease_timestamp(),
    )
    body = issue_wire.upsert_implementation_lease(body=snapshot.body, lease=lease)
    mutation = issue_mutation.update_implementation_lease(
        runner,
        repository=run.repo,
        issue=run.issue,
        body=body,
        run_id=run.run_id,
        title=new_title,
        expected_snapshot=snapshot,
        cwd=run.cwd,
    )
    if issue_wire.parse_implementation_lease(body=mutation.after.body) != lease:
        raise ShipError("implementation-lease-readback-mismatch")
    return RenameOutput(renamed=new_title != snapshot.title, new_title=new_title)


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
    try:
        return rename_with_details(
            runner,
            issue,
            state,
            repo=repo,
            current_title=current_title,
            cwd=cwd,
        ).new_title
    except CliFailure as exc:
        raise ShipError(exc.message) from exc


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
        body = f"{LIFECYCLE_MARKER_PREFIX}{lifecycle_marker} -->\n{body}"
    redacted = _redact_compose(body, context="tracking-issue comment")
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
    redacted = _redact_compose(full_body, context="tracking-issue comment")
    comment_id = gh.find_issue_comment_id_by_marker(runner, issue, marker, repo=repo, cwd=cwd)
    if comment_id is None:
        result = gh.issue_comment(runner, issue, redacted, repo=repo, cwd=cwd)
        if result.returncode != 0:
            msg = f"gh issue comment failed ({result.returncode})"
            raise ShipError(msg)
        return
    if comment_id < 0:
        msg = f"multiple tracking comments found for marker {marker!r}"
        raise ShipError(msg)
    result = gh.issue_comment_patch(runner, comment_id, redacted, repo=repo, cwd=cwd)
    if result.returncode != 0:
        msg = f"gh issue comment patch failed ({result.returncode})"
        raise ShipError(msg)


def upsert_marker_comment(
    runner: Runner,
    issue: str,
    marker: str,
    body: str,
    *,
    repo: str,
    comment_id: int | None = None,
    cwd: str | None = None,
) -> tuple[str, bool]:
    """Upsert an issue comment with an explicit full marker."""
    full_body = f"{marker}\n{body}"
    redacted = _redact_compose(full_body, context="tracking-issue comment")
    if comment_id is None:
        found = gh.find_issue_comment_id_by_marker(runner, issue, marker, repo=repo, cwd=cwd)
        if found is not None and found < 0:
            msg = f"multiple tracking comments found for marker {marker!r}"
            raise ShipError(msg)
        comment_id = found
    if comment_id is None:
        result = _retry_gh(lambda: gh.issue_comment(runner, issue, redacted, repo=repo, cwd=cwd))
        if result.returncode != 0:
            msg = f"gh issue comment failed ({result.returncode})"
            raise ShipError(msg)
        return _comment_url_from_result(result), False
    result = _retry_gh(lambda: gh.issue_comment_patch(runner, comment_id, redacted, repo=repo, cwd=cwd))
    if result.returncode != 0:
        msg = f"gh issue comment patch failed ({result.returncode})"
        raise ShipError(msg)
    return _comment_url_from_result(result), True


def upsert_summary(
    runner: Runner,
    issue: str,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> None:
    _upsert_marker_comment(runner, issue, _upsert_marker("final-summary"), body, repo=repo, cwd=cwd)


def upsert_marker_summary(
    runner: Runner,
    *,
    issue: str,
    marker: str,
    content_file: str,
    repo: str | None,
) -> UpsertSummaryOutput:
    """Upsert a caller-owned marker summary and return its typed outcome."""
    return _upsert_summary_cli(
        runner, issue=issue, marker=marker, content_file=content_file,
        repo=repo, comment_id=None,
    )


def upsert_token_report(
    runner: Runner,
    issue: str,
    body: str,
    *,
    repo: str,
    cwd: str | None = None,
) -> None:
    _upsert_marker_comment(runner, issue, _upsert_marker("token-report"), body, repo=repo, cwd=cwd)


def _drop_issue_footer(*, body: str, issue_number: int) -> str:
    needles = {f"Closes #{issue_number}", f"Part of #{issue_number}"}
    lines = body.rstrip().splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[-1].strip() in needles:
        lines.pop()
    return "\n".join(lines).rstrip()


def link_pr_closes(*, body: str, issue_number: int) -> str:
    """Ensure the PR body has a footer-style Closes #N line."""
    needle = f"Closes #{issue_number}"
    nonblank_lines = [line.strip() for line in body.splitlines() if line.strip()]
    if nonblank_lines and nonblank_lines[-1] == needle:
        return body
    stripped = _drop_issue_footer(body=body, issue_number=issue_number)
    return stripped.rstrip() + f"\n\n{needle}\n"


def link_pr_part_of(*, body: str, issue_number: int) -> str:
    """Ensure the PR body has a footer-style Part of #N line."""
    needle = f"Part of #{issue_number}"
    nonblank_lines = [line.strip() for line in body.splitlines() if line.strip()]
    if nonblank_lines and nonblank_lines[-1] == needle:
        return body
    stripped = _drop_issue_footer(body=body, issue_number=issue_number)
    return stripped.rstrip() + f"\n\n{needle}\n"


def link_pr_for_disposition(*, body: str, issue_number: int, partial: bool = False) -> str:
    if partial:
        return link_pr_part_of(body=body, issue_number=issue_number)
    return link_pr_closes(body=body, issue_number=issue_number)


def _read_sentinel(path: str) -> tuple[str, str, str]:
    sentinel = Path(path)
    if not sentinel.is_file():
        raise CliFailure(f"sentinel file not found: {path}", 1)
    try:
        content = sentinel.read_text(encoding="utf-8")
    except OSError:
        raise CliFailure(f"sentinel file not readable: {path}", 1) from None
    content = content.removeprefix("\ufeff")

    def first_value(key: str) -> str:
        prefix = f"{key}="
        for line in content.split("\n"):
            if line.startswith(prefix):
                return line[len(prefix) :].removesuffix("\r")
        return ""

    issue_number = first_value("ISSUE_NUMBER")
    run_id = first_value("RUN_ID")
    adopted = first_value("ADOPTED")
    if issue_number and not issue_number.isdigit():
        raise CliFailure("invalid ISSUE_NUMBER in sentinel: ISSUE_NUMBER: 'malformed-value-omitted'", 1)
    if run_id and not _RUN_ID_RE.match(run_id):
        raise CliFailure("invalid RUN_ID in sentinel: RUN_ID: 'malformed-value-omitted'", 1)
    if adopted and adopted not in {"true", "false"}:
        raise CliFailure("invalid ADOPTED value in sentinel: ADOPTED: 'malformed-value-omitted'", 1)
    return issue_number, run_id, adopted


def read_sentinel(path: str) -> SentinelReadResult:
    """Parse an adoption sentinel into a frozen result with named fields."""
    issue_number, run_id, adopted = _read_sentinel(path)
    return SentinelReadResult(issue_number=issue_number, run_id=run_id, adopted=adopted)


def _validate_marker_shape(marker: str) -> None:
    if not (marker.startswith("<!-- larch:") and marker.endswith(" -->")) or "\n" in marker or "\r" in marker:
        raise CliFailure(f"invalid marker: {marker}", 1, stderr=True)


def _find_summary_comment_ids(runner: Runner, issue: str, marker: str, *, repo: str) -> list[int]:
    result = gh.issue_comments_list_read(runner, issue, repo=repo)
    if result.returncode != 0:
        raise CliFailure(f"gh api comments fetch failed: {_redact_gh_error(result.stderr)}", 2, stderr=True)
    try:
        rows_obj = gh.loads_json_paginated_list(result.stdout or "[]")
    except ShipError as exc:
        raise CliFailure(str(exc), 2, stderr=True) from exc
    ids: list[int] = []
    for row_obj in rows_obj:
        if not isinstance(row_obj, dict):
            continue
        body_obj = row_obj.get("body")
        body = body_obj if isinstance(body_obj, str) else str(body_obj or "")
        first_line = body.split("\n", 1)[0].removeprefix("\ufeff").removesuffix("\r") if body else ""
        if first_line == marker:
            try:
                ids.append(int(str(row_obj.get("id"))))
            except (TypeError, ValueError):
                continue
    return ids


def _upsert_summary_cli(
    runner: Runner,
    *,
    issue: str,
    marker: str,
    content_file: str,
    repo: str | None,
    comment_id: str | None,
) -> UpsertSummaryOutput:
    _require_numeric_issue(issue)
    _validate_marker_shape(marker)
    if comment_id is not None and (not comment_id.isdigit()):
        raise CliFailure(f"invalid comment id: {comment_id}", 1, stderr=True)
    content = _read_text_file(content_file, label="content", require_nonempty=False)
    body = _redact_summary_body(f"{marker}\n\n{content}")
    resolved = _resolve_repo_or_fail(runner, repo)
    ids = [int(comment_id)] if comment_id is not None else _find_summary_comment_ids(runner, issue, marker, repo=resolved)
    if not ids:
        result = gh.issue_comment_with_retry(runner, issue, body, repo=resolved)
        if result.returncode != 0:
            raise CliFailure(f"gh issue comment failed: {_redact_gh_error(result.stderr)}", 2, stderr=True)
        parsed = _raw_comment_url(result.stdout)
        return UpsertSummaryOutput(
            comment_id=parsed[0] if parsed is not None else "",
            comment_url=parsed[1] if parsed is not None else _comment_url_from_result(result),
            updated=False,
        )
    if len(ids) > 1:
        flat = ",".join(str(value) for value in ids)
        raise CliFailure(f"multiple summary comments found for marker (ids: {flat})", 2, stderr=True)
    result = _retry_gh(lambda: gh.issue_comment_patch(runner, ids[0], body, repo=resolved))
    if result.returncode != 0:
        raise CliFailure(f"gh api comment patch failed: {_redact_gh_error(result.stderr)}", 2, stderr=True)
    return UpsertSummaryOutput(comment_id=str(ids[0]), comment_url=_comment_url_from_result(result), updated=True)


