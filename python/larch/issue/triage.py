"""Fail-closed helpers for the /triage issue-investigation skill."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, TextIO, cast
from urllib.parse import urlparse

from larch.core import proc, redact
from larch.core.proc import CommandResult, Runner
from larch.git import gh
from larch.state.session_env import check_live_mutation_auth

EXIT_USAGE: Final = 2
EXIT_AUTHORIZATION: Final = 3
EXIT_STALE: Final = 4
EXIT_PROTECTED: Final = 5
EXIT_REDACTION: Final = 6
EXIT_MUTATION: Final = 7
EXIT_POSTCONDITION: Final = 8

TRIAGE_MARKER_START: Final = "<!-- larch:triage:start -->"
TRIAGE_MARKER_END: Final = "<!-- larch:triage:end -->"
_TRIAGE_COMMENT_PREFIX: Final = "<!-- larch:triage-verdict:"
_REPO_RE: Final = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")
_SHA_RE: Final = re.compile(r"[0-9a-fA-F]{40}")
_PULL_REF_RE: Final = re.compile(r"refs/pull/([1-9][0-9]*)/head")
_UPDATED_AT_RE: Final = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_LARCH_MARKER_RE: Final = re.compile(r"<!--\s*larch:[\s\S]*?-->", re.IGNORECASE)
_EMAIL_RE: Final = re.compile(
    r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])"
)
_URL_RE: Final = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
_LIFECYCLE_PREFIX_RE: Final = re.compile(
    r"^\[(?:IMPLEMENTING|DONE|DESIGNING|DESIGNED|STALLED|IN PROGRESS|PLANNED)\]\s+",
    re.IGNORECASE,
)
_PROTECTED_MARKER_RE: Final = re.compile(r"<!--\s*larch:", re.IGNORECASE)
_SECURITY_RE: Final = re.compile(
    r"\b(?:credential(?:s)?|secret(?:s)?|api[ -]?key|auth(?:entication|orization)? bypass|"
    r"remote code execution|\brce\b|sql injection|command injection|vulnerabilit(?:y|ies)|"
    r"private key|token exposure)\b",
    re.IGNORECASE,
)
_MAX_EVIDENCE_BYTES: Final = 64 * 1024
_MAX_PROBE_BYTES: Final = 16 * 1024
_TRIAGE_TMP_PREFIX: Final = "claude-triage-"
_LS_REMOTE_FIELD_COUNT: Final = 2
_TMP_ROOT: Final = Path("/tmp")  # noqa: S108 - /triage policy requires canonical /tmp


@dataclass(frozen=True)
class IssueSnapshot:  # pylint: disable=too-many-instance-attributes  # GitHub fields stay named
    """Typed issue state used by every compare-and-swap boundary."""

    number: int
    repo: str
    title: str
    body: str
    state: str
    state_reason: str
    url: str
    updated_at: str
    labels: tuple[str, ...]
    comments: tuple[str, ...]


@dataclass(frozen=True)
class InspectRequest:
    """Validated immutable-ref evidence request."""

    repo_root: Path
    ref: str
    path: PurePosixPath | None
    max_bytes: int


@dataclass(frozen=True)
class CloseRequest:
    """Validated close-verdict mutation inputs."""

    issue: int
    repo: str
    verdict: str
    artifact_text: str
    canonical: int | None


class TriageError(Exception):
    """A user-safe triage failure with a stable exit class."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _flat(text: str) -> str:
    return (
        redact.redact_outbound(text)
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()[:1000]
    )


def _failure(kind: str, message: str, *, stream: TextIO | None = None) -> None:
    output = sys.stderr if stream is None else stream
    print(f"TRIAGE_FAILURE={kind}", file=output)
    print(f"ERROR={_flat(message)}", file=output)


def _json_object(result: CommandResult, *, context: str) -> dict[str, object]:
    if result.returncode != 0:
        raise TriageError(
            f"{context} failed: {result.stderr or result.stdout}",
            EXIT_MUTATION,
        )
    try:
        payload: object = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise TriageError(
            f"{context} returned invalid JSON: {exc}", EXIT_POSTCONDITION
        ) from exc
    if not isinstance(payload, dict):
        raise TriageError(
            f"{context} returned a non-object payload", EXIT_POSTCONDITION
        )
    return cast("dict[str, object]", payload)


def _named_values(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    values: list[str] = []
    for raw in cast("list[dict[str, object] | str]", value):
        if isinstance(raw, dict) and isinstance(raw.get(field), str):
            values.append(str(raw[field]))
        elif isinstance(raw, str):
            values.append(raw)
    return tuple(values)


def _issue_snapshot(runner: Runner, *, issue: int, repo: str) -> IssueSnapshot:
    result = runner.run(
        [
            "gh",
            "issue",
            "view",
            str(issue),
            "--repo",
            repo,
            "--json",
            "number,title,body,state,stateReason,url,updatedAt,labels,comments",
        ],
    )
    data = _json_object(result, context="issue snapshot")
    number_raw = data.get("number", 0)
    try:
        if not isinstance(number_raw, int | str):
            raise TypeError
        number = int(number_raw)
    except (TypeError, ValueError) as exc:
        raise TriageError(
            "issue snapshot has an invalid number", EXIT_POSTCONDITION
        ) from exc
    snapshot = IssueSnapshot(
        number=number,
        repo=repo,
        title=str(data.get("title") or ""),
        body=str(data.get("body") or ""),
        state=str(data.get("state") or "").upper(),
        state_reason=str(data.get("stateReason") or "").upper(),
        url=str(data.get("url") or ""),
        updated_at=str(data.get("updatedAt") or ""),
        labels=_named_values(data.get("labels", []), field="name"),
        comments=_named_values(data.get("comments", []), field="body"),
    )
    if snapshot.number != issue or not snapshot.updated_at:
        raise TriageError(
            "issue snapshot is missing required identity fields", EXIT_POSTCONDITION
        )
    parsed_url = urlparse(snapshot.url)
    expected_suffix = f"/{repo}/issues/{issue}"
    if parsed_url.path.rstrip("/") != expected_suffix:
        raise TriageError(
            "issue snapshot repository or issue identity did not match", EXIT_PROTECTED
        )
    return snapshot


def _contains_security_content(
    snapshot: IssueSnapshot, *, comments: tuple[str, ...] = ()
) -> bool:
    if any(
        label.casefold() in {"security", "vulnerability"} for label in snapshot.labels
    ):
        return True
    return _SECURITY_RE.search(
        "\n".join((snapshot.title, snapshot.body, *snapshot.comments, *comments))
    ) is not None


def _comment_bodies(runner: Runner, *, issue: int, repo: str) -> tuple[str, ...]:
    """Read every issue comment for security and idempotency checks."""
    result = gh.issue_comments_list_read(runner, str(issue), repo=repo)
    if result.returncode != 0:
        raise TriageError("issue comments could not be read", EXIT_PROTECTED)
    try:
        rows = gh.loads_json_paginated_list(result.stdout)
    except gh.ShipError as exc:
        raise TriageError("issue comments returned invalid JSON", EXIT_PROTECTED) from exc
    bodies: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise TriageError("issue comments returned a malformed row", EXIT_PROTECTED)
        body = cast("dict[str, object]", row).get("body")
        bodies.append(body if isinstance(body, str) else str(body or ""))
    return tuple(bodies)


def _triage_span(body: str) -> tuple[int, int] | None:
    starts = [
        match.start() for match in re.finditer(re.escape(TRIAGE_MARKER_START), body)
    ]
    ends = [match.end() for match in re.finditer(re.escape(TRIAGE_MARKER_END), body)]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise TriageError("malformed helper-owned triage block", EXIT_PROTECTED)
    return starts[0], ends[0]


def _has_protected_state(snapshot: IssueSnapshot, *, allow_stale_title: bool) -> bool:
    if snapshot.state != "OPEN":
        return True
    if any("clarif" in label.casefold() for label in snapshot.labels):
        return True
    body_without_triage = snapshot.body
    span = _triage_span(snapshot.body)
    if span is not None:
        body_without_triage = (
            snapshot.body[: span[0]]
            + snapshot.body[
                span[0] + len(TRIAGE_MARKER_START) : span[1] - len(TRIAGE_MARKER_END)
            ]
            + snapshot.body[span[1] :]
        )
    if _PROTECTED_MARKER_RE.search(body_without_triage):
        return True
    return (
        not allow_stale_title and _LIFECYCLE_PREFIX_RE.match(snapshot.title) is not None
    )


def _private_url(url: str) -> bool:
    host = (urlparse(url.rstrip(".,;:!?")).hostname or "").casefold()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(
        (".internal", ".local")
    ):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        pass
    return False


def sanitize_outbound(text: str, *, allow_triage_block: bool = False) -> str:
    """Redact outbound issue prose and neutralize control markers."""
    source = text
    content = source
    if allow_triage_block and (
        TRIAGE_MARKER_START in source or TRIAGE_MARKER_END in source
    ):
        span = _triage_span(source)
        if span is None or source[: span[0]].strip() or source[span[1] :].strip():
            raise TriageError(
                "triage artifact must contain only one validated triage block",
                EXIT_REDACTION,
            )
        content = source[
            span[0] + len(TRIAGE_MARKER_START) : span[1] - len(TRIAGE_MARKER_END)
        ]
    content = _LARCH_MARKER_RE.sub(
        lambda match: match.group(0).replace("<!--", "<!--\u200b", 1), content
    )
    content = _EMAIL_RE.sub("<REDACTED-PII>", content)
    content = _URL_RE.sub(
        lambda match: (
            "<INTERNAL-URL>" if _private_url(match.group(0)) else match.group(0)
        ),
        content,
    )
    content = redact.redact_outbound(content)
    if any(pattern.search(content) for pattern in (_EMAIL_RE,)):
        raise TriageError(
            "outbound PII redaction could not be verified", EXIT_REDACTION
        )
    if allow_triage_block:
        return f"{TRIAGE_MARKER_START}\n{content.strip()}\n{TRIAGE_MARKER_END}"
    return content


def _canonical_tmp_root(value: str) -> Path:
    root = Path(value)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise TriageError(
            "triage root must be an existing regular directory", EXIT_USAGE
        )
    resolved = root.resolve()
    tmp_root = _TMP_ROOT.resolve()
    if resolved.parent != tmp_root or not resolved.name.startswith(_TRIAGE_TMP_PREFIX):
        raise TriageError(
            "triage root must be a canonical /tmp/claude-triage-* directory", EXIT_USAGE
        )
    return resolved


def _artifact(path_value: str, *, root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise TriageError(
            "triage artifact must be a regular non-symlink file", EXIT_USAGE
        )
    resolved = path.resolve()
    if resolved.parent != root:
        raise TriageError(
            "triage artifact escaped the canonical triage root", EXIT_USAGE
        )
    return resolved


def _check_snapshot(
    runner: Runner,
    snapshot: IssueSnapshot,
    *,
    expected: str,
    verdict: str,
    artifact_text: str,
) -> None:
    if snapshot.updated_at != expected:
        raise TriageError("issue changed since the expected snapshot", EXIT_STALE)
    comments = _comment_bodies(runner, issue=snapshot.number, repo=snapshot.repo)
    if _contains_security_content(snapshot, comments=comments) or _SECURITY_RE.search(
        artifact_text
    ):
        raise TriageError(
            "security-sensitive issue cannot be mutated publicly", EXIT_PROTECTED
        )
    close_verdict = verdict in {"already-fixed", "invalid", "duplicate"}
    if _has_protected_state(snapshot, allow_stale_title=close_verdict):
        raise TriageError("issue has protected lifecycle state", EXIT_PROTECTED)


def _mutate(runner: Runner, argv: list[str], *, action: str) -> None:
    result = runner.run(argv)
    if result.returncode != 0:
        raise TriageError(
            f"{action} failed: {result.stderr or result.stdout}", EXIT_MUTATION
        )


def _replace_triage_block(original: str, block: str) -> str:
    span = _triage_span(original)
    if span is None:
        separator = (
            "" if not original else ("\n" if original.endswith("\n") else "\n\n")
        )
        return f"{original}{separator}{block}\n"
    return f"{original[: span[0]]}{block}{original[span[1] :]}"


def _read_after_mutation(
    runner: Runner,
    *,
    issue: int,
    repo: str,
    previous: IssueSnapshot,
) -> IssueSnapshot:
    current = _issue_snapshot(runner, issue=issue, repo=repo)
    if current.updated_at == previous.updated_at:
        raise TriageError(
            "mutation did not advance the issue snapshot", EXIT_POSTCONDITION
        )
    return current


def _valid_apply(
    runner: Runner,
    *,
    issue: int,
    repo: str,
    snapshot: IssueSnapshot,
    artifact_text: str,
) -> IssueSnapshot:
    block = sanitize_outbound(artifact_text, allow_triage_block=True)
    new_body = _replace_triage_block(snapshot.body, block)
    if new_body == snapshot.body:
        return snapshot
    snapshot = _recheck_valid_snapshot(
        runner, snapshot=snapshot, issue=issue, repo=repo
    )
    body_result = gh.issue_edit(
        runner,
        str(issue),
        repo=repo,
        body=new_body,
    )
    if body_result.returncode != 0:
        raise TriageError(
            f"triage body update failed: {body_result.stderr or body_result.stdout}",
            EXIT_MUTATION,
        )
    current = _read_after_mutation(runner, issue=issue, repo=repo, previous=snapshot)
    if (
        current.body != new_body
        or current.title != snapshot.title
        or current.state != "OPEN"
    ):
        raise TriageError(
            "triage body update failed exact read-back", EXIT_POSTCONDITION
        )
    return current


def _canonical_duplicate(
    runner: Runner, *, issue: int, canonical: int, repo: str
) -> None:
    if canonical == issue:
        raise TriageError(
            "canonical duplicate must differ from the triaged issue", EXIT_USAGE
        )
    duplicate = _issue_snapshot(runner, issue=canonical, repo=repo)
    if duplicate.number != canonical or duplicate.state != "OPEN":
        raise TriageError("canonical duplicate could not be verified", EXIT_PROTECTED)


def _recheck_close_snapshot(
    runner: Runner,
    *,
    snapshot: IssueSnapshot,
    request: CloseRequest,
) -> IssueSnapshot:
    current = _issue_snapshot(runner, issue=request.issue, repo=request.repo)
    if current.updated_at != snapshot.updated_at:
        raise TriageError("issue changed before the next mutation", EXIT_STALE)
    comments = _comment_bodies(runner, issue=current.number, repo=request.repo)
    if _contains_security_content(current, comments=comments):
        raise TriageError(
            "security-sensitive issue cannot be mutated publicly", EXIT_PROTECTED
        )
    if _has_protected_state(current, allow_stale_title=True):
        raise TriageError("issue has protected lifecycle state", EXIT_PROTECTED)
    return current


def _recheck_valid_snapshot(
    runner: Runner, *, snapshot: IssueSnapshot, issue: int, repo: str
) -> IssueSnapshot:
    current = _issue_snapshot(runner, issue=issue, repo=repo)
    if current.updated_at != snapshot.updated_at:
        raise TriageError("issue changed before the next mutation", EXIT_STALE)
    comments = _comment_bodies(runner, issue=current.number, repo=repo)
    if _contains_security_content(current, comments=comments):
        raise TriageError(
            "security-sensitive issue cannot be mutated publicly", EXIT_PROTECTED
        )
    if _has_protected_state(current, allow_stale_title=False):
        raise TriageError("issue has protected lifecycle state", EXIT_PROTECTED)
    return current


def _ensure_verification_comment(
    runner: Runner,
    *,
    snapshot: IssueSnapshot,
    request: CloseRequest,
    marker: str,
    marked_comment: str,
) -> IssueSnapshot:
    comments = _comment_bodies(runner, issue=request.issue, repo=request.repo)
    if marked_comment in comments:
        return snapshot
    if any(existing.startswith(marker) for existing in comments):
        raise TriageError(
            "conflicting triage verdict marker already exists", EXIT_POSTCONDITION
        )
    snapshot = _recheck_close_snapshot(
        runner,
        snapshot=snapshot,
        request=request,
    )
    comment_result = gh.issue_comment(
        runner,
        str(request.issue),
        marked_comment,
        repo=request.repo,
    )
    if comment_result.returncode != 0:
        raise TriageError(
            "triage verification comment failed: "
            f"{comment_result.stderr or comment_result.stdout}",
            EXIT_MUTATION,
        )
    current = _read_after_mutation(
        runner, issue=request.issue, repo=request.repo, previous=snapshot
    )
    current_comments = _comment_bodies(runner, issue=request.issue, repo=request.repo)
    if marked_comment not in current_comments:
        raise TriageError("triage comment failed exact read-back", EXIT_POSTCONDITION)
    return current


def _restore_stale_title(
    runner: Runner,
    *,
    snapshot: IssueSnapshot,
    request: CloseRequest,
) -> IssueSnapshot:
    restored_title = snapshot.title
    while _LIFECYCLE_PREFIX_RE.match(restored_title):
        restored_title = _LIFECYCLE_PREFIX_RE.sub("", restored_title, count=1)
    if restored_title == snapshot.title:
        return snapshot
    snapshot = _recheck_close_snapshot(
        runner,
        snapshot=snapshot,
        request=request,
    )
    _mutate(
        runner,
        [
            "gh",
            "issue",
            "edit",
            str(request.issue),
            "--repo",
            request.repo,
            "--title",
            restored_title,
        ],
        action="triage title restoration",
    )
    current = _read_after_mutation(
        runner, issue=request.issue, repo=request.repo, previous=snapshot
    )
    if current.title != restored_title:
        raise TriageError(
            "title restoration failed exact read-back", EXIT_POSTCONDITION
        )
    return current


def _close_apply(
    runner: Runner,
    *,
    snapshot: IssueSnapshot,
    request: CloseRequest,
) -> IssueSnapshot:
    if request.verdict == "duplicate":
        if request.canonical is None:
            raise TriageError(
                "duplicate verdict requires --canonical-duplicate", EXIT_USAGE
            )
        _canonical_duplicate(
            runner,
            issue=request.issue,
            canonical=request.canonical,
            repo=request.repo,
        )
        snapshot = _recheck_close_snapshot(
            runner,
            snapshot=snapshot,
            request=request,
        )
    marker = f"{_TRIAGE_COMMENT_PREFIX}{request.verdict} -->"
    comment = sanitize_outbound(request.artifact_text)
    if (
        request.verdict == "duplicate"
        and request.canonical is not None
        and f"#{request.canonical}" not in comment
    ):
        comment = f"Duplicate of #{request.canonical}.\n\n{comment}"
    marked_comment = f"{marker}\n{comment.strip()}"
    snapshot = _ensure_verification_comment(
        runner,
        snapshot=snapshot,
        request=request,
        marker=marker,
        marked_comment=marked_comment,
    )
    snapshot = _restore_stale_title(
        runner,
        snapshot=snapshot,
        request=request,
    )
    snapshot = _recheck_close_snapshot(
        runner,
        snapshot=snapshot,
        request=request,
    )
    _mutate(
        runner,
        [
            "gh",
            "issue",
            "close",
            str(request.issue),
            "--repo",
            request.repo,
            "--reason",
            "not planned",
        ],
        action="triage issue close",
    )
    current = _read_after_mutation(
        runner,
        issue=request.issue,
        repo=request.repo,
        previous=snapshot,
    )
    if current.state != "CLOSED" or current.state_reason not in {"NOT_PLANNED", ""}:
        raise TriageError(
            "issue close failed state/reason read-back", EXIT_POSTCONDITION
        )
    return current


def _apply_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="triage apply")
    _ = parser.add_argument("issue", type=int)
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument(
        "--verdict",
        required=True,
        choices=("valid", "already-fixed", "duplicate", "invalid", "inconclusive"),
    )
    _ = parser.add_argument("--expected-updated-at", required=True)
    _ = parser.add_argument("--triage-root", required=True)
    _ = parser.add_argument("--body-file")
    _ = parser.add_argument("--comment-file")
    _ = parser.add_argument("--canonical-duplicate", type=int)
    _ = parser.add_argument("--operator-invoked", action="store_true")
    return parser


def apply_main(argv: list[str]) -> int:
    """Apply one verified verdict with per-mutation compare-and-swap checks."""
    try:
        args = _apply_parser().parse_args(argv)
        if args.issue < 1 or _REPO_RE.fullmatch(args.repo) is None:
            raise TriageError("issue and repository arguments are invalid", EXIT_USAGE)
        if _UPDATED_AT_RE.fullmatch(args.expected_updated_at) is None:
            raise TriageError(
                "--expected-updated-at must be an ISO-8601 UTC timestamp", EXIT_USAGE
            )
        if args.verdict == "inconclusive":
            print("TRIAGE_VERDICT=inconclusive")
            print("ISSUE_UPDATED=false")
            print("TRIAGE_FAILURE=none")
            return 0
        auth_ok, auth_reason = check_live_mutation_auth(
            context_file=None,
            operator_mode=bool(args.operator_invoked),
        )
        if not auth_ok:
            raise TriageError(
                f"live mutation authorization refused: {auth_reason}",
                EXIT_AUTHORIZATION,
            )
        root = _canonical_tmp_root(args.triage_root)
        selected_file = args.body_file if args.verdict == "valid" else args.comment_file
        if not selected_file:
            raise TriageError(
                "verdict requires the matching body/comment artifact", EXIT_USAGE
            )
        artifact = _artifact(selected_file, root=root)
        artifact_text = artifact.read_text(encoding="utf-8", errors="replace")
        snapshot = _issue_snapshot(proc, issue=args.issue, repo=args.repo)
        _check_snapshot(
            proc,
            snapshot,
            expected=args.expected_updated_at,
            verdict=args.verdict,
            artifact_text=artifact_text,
        )
        if args.verdict == "valid":
            final = _valid_apply(
                proc,
                issue=args.issue,
                repo=args.repo,
                snapshot=snapshot,
                artifact_text=artifact_text,
            )
        else:
            final = _close_apply(
                proc,
                snapshot=snapshot,
                request=CloseRequest(
                    issue=args.issue,
                    repo=args.repo,
                    verdict=args.verdict,
                    artifact_text=artifact_text,
                    canonical=args.canonical_duplicate,
                ),
            )
        updated = final != snapshot
        print(f"TRIAGE_VERDICT={args.verdict}")
        print(f"ISSUE_UPDATED={'true' if updated else 'false'}")
        print("TRIAGE_FAILURE=none")
        print(f"UPDATED_AT={final.updated_at}")
        return 0
    except TriageError as exc:
        failure = {
            EXIT_AUTHORIZATION: "authorization",
            EXIT_STALE: "stale-snapshot",
            EXIT_PROTECTED: "protected-state",
            EXIT_REDACTION: "redaction",
            EXIT_MUTATION: "mutation",
            EXIT_POSTCONDITION: "postcondition",
        }.get(exc.exit_code, "validation")
        _failure(failure, str(exc))
        print("ISSUE_UPDATED=false")
        return exc.exit_code
    except SystemExit:
        return EXIT_USAGE
    except OSError as exc:
        _failure("validation", str(exc))
        print("ISSUE_UPDATED=false")
        return EXIT_USAGE


def _git(runner: Runner, request: InspectRequest, *args: str) -> CommandResult:
    return runner.run(["git", "-C", str(request.repo_root), *args])


def _validate_evidence_path(value: str) -> PurePosixPath:
    if not value or "\x00" in value or "\\" in value:
        raise TriageError("evidence path is invalid", EXIT_USAGE)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("-"):
        raise TriageError(
            "evidence path must be a bounded repository-relative path", EXIT_USAGE
        )
    if not (value.startswith("larch-logs/") or len(path.parts) >= 1):
        raise TriageError("evidence path is outside allowed evidence roots", EXIT_USAGE)
    return path


def _origin_slug(request: InspectRequest, runner: Runner) -> str:
    result = _git(runner, request, "remote", "get-url", "origin")
    if result.returncode != 0:
        raise TriageError("fixed origin remote is unavailable", EXIT_POSTCONDITION)
    value = result.stdout.strip()
    patterns = (
        re.compile(
            r"(?:https://github\.com/|git@github\.com:)([^/\s]+/[^/\s]+?)(?:\.git)?$"
        ),
        re.compile(r"^ssh://git@github\.com/([^/\s]+/[^/\s]+?)(?:\.git)?$"),
    )
    for pattern in patterns:
        match = pattern.match(value)
        if match and _REPO_RE.fullmatch(match.group(1)):
            return match.group(1)
    raise TriageError(
        "origin is not a validated GitHub repository remote", EXIT_POSTCONDITION
    )


def _ensure_commit(
    request: InspectRequest,
    runner: Runner,
    *,
    sha: str,
    unavailable_message: str,
) -> str:
    if _git(runner, request, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0:
        return sha
    fetched = _git(runner, request, "fetch", "--no-tags", "origin", sha)
    verified = _git(runner, request, "cat-file", "-e", f"{sha}^{{commit}}")
    if fetched.returncode != 0 or verified.returncode != 0:
        raise TriageError(unavailable_message, EXIT_POSTCONDITION)
    return sha


def _resolve_main(request: InspectRequest, runner: Runner) -> tuple[str, str]:
    listed = _git(
        runner, request, "ls-remote", "--exit-code", "origin", "refs/heads/main"
    )
    fields = listed.stdout.strip().split()
    if (
        listed.returncode != 0
        or len(fields) != _LS_REMOTE_FIELD_COUNT
        or _SHA_RE.fullmatch(fields[0]) is None
        or fields[1] != "refs/heads/main"
    ):
        raise TriageError(
            "exact origin refs/heads/main could not be resolved", EXIT_POSTCONDITION
        )
    sha = _ensure_commit(
        request,
        runner,
        sha=fields[0].lower(),
        unavailable_message="immutable main object is unavailable",
    )
    return sha, "refs/heads/main"


def _resolve_pull(request: InspectRequest, runner: Runner) -> tuple[str, str]:
    fetched = _git(runner, request, "fetch", "--no-tags", "origin", request.ref)
    if fetched.returncode != 0:
        raise TriageError("cited pull-request ref is unavailable", EXIT_POSTCONDITION)
    resolved = _git(runner, request, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    sha = resolved.stdout.strip().lower()
    if resolved.returncode != 0 or _SHA_RE.fullmatch(sha) is None:
        raise TriageError(
            "cited pull-request ref did not resolve immutably", EXIT_POSTCONDITION
        )
    return sha, request.ref


def _resolve_ref(request: InspectRequest, runner: Runner) -> tuple[str, str]:
    if request.ref in {"main", "refs/heads/main"}:
        return _resolve_main(request, runner)
    if _SHA_RE.fullmatch(request.ref):
        sha = request.ref.lower()
        return (
            _ensure_commit(
                request,
                runner,
                sha=sha,
                unavailable_message="cited immutable commit is unavailable",
            ),
            sha,
        )
    if _PULL_REF_RE.fullmatch(request.ref):
        return _resolve_pull(request, runner)
    raise TriageError(
        "ref must be main, a full commit SHA, or refs/pull/<N>/head", EXIT_USAGE
    )


def _inspect_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="triage inspect")
    _ = parser.add_argument("--repo-root", default=".")
    _ = parser.add_argument("--ref", default="refs/heads/main")
    _ = parser.add_argument("--path")
    _ = parser.add_argument("--max-bytes", type=int, default=_MAX_EVIDENCE_BYTES)
    return parser


def inspect_main(argv: list[str]) -> int:
    """Resolve and read evidence only through an immutable fixed-origin ref."""
    try:
        args = _inspect_parser().parse_args(argv)
        repo_root = Path(args.repo_root).resolve()
        if not repo_root.is_dir():
            raise TriageError("--repo-root is not a directory", EXIT_USAGE)
        path = _validate_evidence_path(args.path) if args.path else None
        if args.max_bytes < 1 or args.max_bytes > _MAX_EVIDENCE_BYTES:
            raise TriageError(
                "--max-bytes is outside the supported evidence cap", EXIT_USAGE
            )
        request = InspectRequest(
            repo_root=repo_root, ref=args.ref, path=path, max_bytes=args.max_bytes
        )
        slug = _origin_slug(request, proc)
        sha, source_ref = _resolve_ref(request, proc)
        print("EVIDENCE_STATUS=ok")
        print(f"REPOSITORY={slug}")
        print(f"IMMUTABLE_SHA={sha}")
        print(f"SOURCE_REF={source_ref}")
        if path is None:
            print("EVIDENCE_TRUNCATED=false")
            return 0
        shown = _git(proc, request, "show", f"{sha}:{path.as_posix()}")
        if shown.returncode != 0:
            raise TriageError(
                "evidence path is missing from the immutable commit", EXIT_POSTCONDITION
            )
        encoded = shown.stdout.encode("utf-8", errors="replace")
        truncated = len(encoded) > request.max_bytes
        content = encoded[: request.max_bytes].decode("utf-8", errors="replace")
        print(f"EVIDENCE_PATH={path.as_posix()}")
        print(f"EVIDENCE_TRUNCATED={'true' if truncated else 'false'}")
        print("EVIDENCE_CONTENT_BEGIN")
        print(
            redact.redact_outbound(content), end="" if content.endswith("\n") else "\n"
        )
        print("EVIDENCE_CONTENT_END")
        return 0
    except TriageError as exc:
        print("EVIDENCE_STATUS=gap")
        print(f"EVIDENCE_GAP={_flat(str(exc))}")
        return exc.exit_code
    except SystemExit:
        return EXIT_USAGE


def _probe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="triage probe")
    _ = parser.add_argument("--name", required=True)
    _ = parser.add_argument("--arg", action="append", default=[])
    _ = parser.add_argument("--max-bytes", type=int, default=_MAX_PROBE_BYTES)
    return parser


def _safe_probe_argv(
    name: str, values: list[str]
) -> tuple[list[str], dict[str, str] | None]:
    if any(re.search(r"[;&|`$<>\n\r]", value) for value in values):
        raise TriageError("probe arguments contain forbidden shell syntax", EXIT_USAGE)
    if name == "python-version" and not values:
        return [sys.executable, "--version"], _scrubbed_env()
    if name == "git-version" and not values:
        return ["git", "--version"], _scrubbed_env()
    if (
        name == "codex-model-readonly"
        and len(values) == 1
        and re.fullmatch(r"[A-Za-z0-9._-]+", values[0])
    ):
        return [
            "codex",
            "exec",
            "--sandbox",
            "read-only",
            "--model",
            values[0],
            "Reply with OK only.",
        ], _scrubbed_env()
    raise TriageError(
        "probe name or arguments are not in the fixed read-only allowlist", EXIT_USAGE
    )


def _scrubbed_env() -> dict[str, str]:
    blocked = re.compile(
        r"(?:TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|PROXY)", re.IGNORECASE
    )
    return {
        key: value for key, value in os.environ.items() if blocked.search(key) is None
    }


def probe_main(argv: list[str]) -> int:
    """Run a fixed, no-shell, bounded and credential-scrubbed reproduction probe."""
    try:
        args = _probe_parser().parse_args(argv)
        if args.max_bytes < 1 or args.max_bytes > _MAX_PROBE_BYTES:
            raise TriageError(
                "--max-bytes is outside the supported probe cap", EXIT_USAGE
            )
        command, env = _safe_probe_argv(args.name, list(args.arg))
        result = proc.run(command, env=env, timeout=30)
        combined = f"{result.stdout}{result.stderr}"
        encoded = combined.encode("utf-8", errors="replace")
        truncated = len(encoded) > args.max_bytes
        output = encoded[: args.max_bytes].decode("utf-8", errors="replace")
        print(
            "PROBE_STATUS=completed"
            if result.returncode == 0
            else "PROBE_STATUS=failed"
        )
        print(f"PROBE_EXIT_CODE={result.returncode}")
        print(f"PROBE_TRUNCATED={'true' if truncated else 'false'}")
        print("PROBE_OUTPUT_BEGIN")
        print(sanitize_outbound(output), end="" if output.endswith("\n") else "\n")
        print("PROBE_OUTPUT_END")
        return 0 if result.returncode == 0 else EXIT_POSTCONDITION
    except TriageError as exc:
        print("PROBE_STATUS=rejected")
        print(f"PROBE_FAILURE={_flat(str(exc))}")
        return exc.exit_code
    except SystemExit:
        return EXIT_USAGE
