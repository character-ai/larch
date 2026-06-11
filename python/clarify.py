# pyright: reportUnusedCallResult=false
"""Clarification round-trip helpers for issue-anchored plans."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple, NoReturn, cast

import gh
import logging_util
import proc
import redact
from errors import ShipError
from proc import CommandResult, Runner

LABEL_NAME = "needs-design-clarification"
LABEL_COLOR = "D73A4A"
LABEL_DESCRIPTION = "Issue plan requires clarification before /implement can proceed"

_MARKER_RE = re.compile(
    r"^\s*<!--\s+larch:clarify-(request|response)\s+id=([1-9][0-9]*)\s*-->\s*$"
)
_COMMENT_ID_RE = re.compile(r"issuecomment-([0-9]+)")
_DUPLICATE_LABEL_RE = re.compile(r"already exists|already been taken", re.IGNORECASE)


class ClarifyState(NamedTuple):
    state: str
    last_request_id: str
    last_response_id: str


class ClarifyCommentResult(NamedTuple):
    posted: bool
    comment_id: str
    comment_url: str
    marker: str


class ClarifyLabelResult(NamedTuple):
    changed: bool
    action: str
    label: str


class _ArgparseExit(Exception):
    def __init__(self, status: int) -> None:
        self.status = status


class _ClarifyValidationError(Exception):
    def __init__(self, token: str) -> None:
        self.token = token


class _ClarifyRepoResolutionError(Exception):
    pass


class _ClarifyParser(argparse.ArgumentParser):
    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if message:
            self._print_message(message, sys.stderr)
        raise _ArgparseExit(status)

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _parser(prog: str, usage: str) -> _ClarifyParser:
    return _ClarifyParser(prog=prog, usage=usage, add_help=True)


def _bool_text(value: bool) -> str:  # noqa: FBT001
    return "true" if value else "false"


def _is_positive_int_text(value: object) -> bool:
    text = "" if value is None else str(value)
    return text.isdigit() and text != "0"


def _validate_positive_issue_for_cli(value: object, *, verb: str) -> bool:
    if _is_positive_int_text(value):
        return True
    print(f"clarify-{verb}.sh: --issue must be a positive integer", file=sys.stderr)
    return False


def _resolve_repo_for_clarify(
    runner: Runner,
    repo: str | None,
    *,
    cwd: str | None = None,
) -> str:
    if repo:
        if not gh.validate_repo_slug(repo):
            raise _ClarifyValidationError("invalid-repo")
        return repo
    result = runner.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=cwd,
    )
    candidate = result.stdout.strip() if result.returncode == 0 else ""
    if not candidate:
        raise _ClarifyRepoResolutionError
    if not gh.validate_repo_slug(candidate):
        raise _ClarifyValidationError("invalid-repo")
    return candidate


def _kv_safe_text(text: str) -> str:
    return text.strip().replace("\r", " ").replace("\n", " ")


def _redact_gh_error(text: str) -> str:
    try:
        redacted = redact.redact(text)
    except Exception:
        return "gh stderr redaction failed"
    if "[content truncated" in redacted:
        return "gh stderr redaction unavailable"
    flat = redacted.replace("\r", " ").replace("\n", " ")
    return flat[:500]


def _emit_failed(error: str) -> None:
    logging_util.emit_kv("FAILED", "true")
    logging_util.emit_kv("ERROR", error)


def _emit_state(result: ClarifyState) -> None:
    logging_util.emit_kv("STATE", result.state)
    logging_util.emit_kv("LAST_REQUEST_ID", result.last_request_id)
    logging_util.emit_kv("LAST_RESPONSE_ID", result.last_response_id)


def _emit_comment(result: ClarifyCommentResult) -> None:
    logging_util.emit_kv("POSTED", _bool_text(result.posted))
    logging_util.emit_kv("COMMENT_ID", result.comment_id)
    logging_util.emit_kv("COMMENT_URL", result.comment_url)
    logging_util.emit_kv("MARKER", result.marker)


def _emit_label(result: ClarifyLabelResult) -> None:
    logging_util.emit_kv("CHANGED", _bool_text(result.changed))
    logging_util.emit_kv("ACTION", result.action)
    logging_util.emit_kv("LABEL", result.label)


def _combined(result: CommandResult) -> str:
    return result.stdout + result.stderr


def _ensure_positive_text(value: object, *, validation_error: str) -> str:
    text = "" if value is None else str(value)
    if not _is_positive_int_text(text):
        raise _ClarifyValidationError(validation_error)
    return text


def _flatten_json_value(value: object) -> list[dict[str, object]]:
    if isinstance(value, dict):
        return [cast("dict[str, object]", value)]
    if not isinstance(value, list):
        msg = "gh JSON parse failed (issue comments): expected array"
        raise ShipError(msg)
    items = cast("list[object]", value)
    rows: list[dict[str, object]] = []
    for item in items:
        if isinstance(item, list):
            rows.extend(_flatten_json_value(cast("list[object]", item)))
        elif isinstance(item, dict):
            rows.append(cast("dict[str, object]", item))
        else:
            msg = "gh JSON parse failed (issue comments): expected object rows"
            raise ShipError(msg)
    return rows


def _comment_rows_from_stdout(stdout: str) -> list[dict[str, object]]:
    stripped = (stdout or "").strip()
    if not stripped:
        return []
    decoder = json.JSONDecoder()
    rows: list[dict[str, object]] = []
    idx = 0
    while idx < len(stripped):
        while idx < len(stripped) and stripped[idx].isspace():
            idx += 1
        if idx >= len(stripped):
            break
        try:
            value, end = decoder.raw_decode(stripped, idx)
        except json.JSONDecodeError as exc:
            msg = f"gh JSON parse failed (issue comments): {exc}"
            raise ShipError(msg) from exc
        rows.extend(_flatten_json_value(value))
        idx = end
    return rows


def _events_from_comments(rows: list[dict[str, object]]) -> list[tuple[str, int]]:
    events: list[tuple[str, int]] = []
    for row in rows:
        body_obj = row.get("body")
        body = body_obj if isinstance(body_obj, str) else str(body_obj or "")
        first_line = body.split("\n", 1)[0].removeprefix("\ufeff").rstrip("\r") if body else ""
        match = _MARKER_RE.fullmatch(first_line)
        if match is None:
            continue
        events.append((match.group(1), int(match.group(2))))
    return events


def _evaluate_events(events: list[tuple[str, int]]) -> ClarifyState:
    ambiguous = False
    max_so_far = 0
    last_req = ""
    last_req_idx = -1
    last_resp = ""
    request_counts: dict[int, int] = {}
    response_counts: dict[int, int] = {}

    for idx, (kind, marker_id) in enumerate(events):
        if marker_id < max_so_far:
            ambiguous = True
        max_so_far = max(max_so_far, marker_id)
        if kind == "request":
            request_counts[marker_id] = request_counts.get(marker_id, 0) + 1
            last_req = str(marker_id)
            last_req_idx = idx
        else:
            response_counts[marker_id] = response_counts.get(marker_id, 0) + 1
            last_resp = str(marker_id)

    if any(count > 1 for count in request_counts.values()):
        ambiguous = True
    if any(count > 1 for count in response_counts.values()):
        ambiguous = True

    for idx, (kind, marker_id) in enumerate(events):
        if kind != "response":
            continue
        seen = any(prev_kind == "request" and prev_id == marker_id for prev_kind, prev_id in events[:idx])
        if not seen:
            ambiguous = True

    max_all = max((marker_id for _, marker_id in events), default=0)

    if ambiguous:
        return ClarifyState("ambiguous", last_req, last_resp)
    if not last_req:
        return ClarifyState("clean", "", "")

    rid = int(last_req)
    has_match = any(
        kind == "response" and marker_id == rid for kind, marker_id in events[last_req_idx + 1 :]
    )
    if not has_match:
        return ClarifyState("awaiting-response", str(rid), last_resp)

    gap_unsat = any(
        request_counts.get(marker_id, 0) > 0 and response_counts.get(marker_id, 0) == 0
        for marker_id in range(1, rid)
    )
    if gap_unsat:
        return ClarifyState("ambiguous", str(rid), last_resp)
    if rid == max_all:
        return ClarifyState("response-pending", str(rid), last_resp)
    return ClarifyState("ambiguous", str(rid), last_resp)


def clarify_state(
    runner: Runner,
    issue: str,
    *,
    repo: str | None,
    cwd: str | None = None,
) -> ClarifyState:
    issue_text = _ensure_positive_text(issue, validation_error="invalid-issue")
    resolved_repo = _resolve_repo_for_clarify(runner, repo, cwd=cwd)
    result = gh.issue_comments_list_read(runner, issue_text, repo=resolved_repo, cwd=cwd)
    if result.returncode != 0:
        raise ShipError(_combined(result) or f"gh api comments fetch failed ({result.returncode})")
    return _evaluate_events(_events_from_comments(_comment_rows_from_stdout(result.stdout)))


def _read_content_file(content_file: str) -> str:
    path = Path(content_file)
    if not path.is_file() or not os.access(path, os.R_OK):
        raise _ClarifyValidationError(f"content file not found: {content_file}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise _ClarifyValidationError(f"content file is not valid utf-8: {content_file}") from exc
    except OSError as exc:
        raise _ClarifyValidationError(f"content file not found: {content_file}") from exc


def clarify_comment_post(
    runner: Runner,
    issue: str,
    kind: str,
    comment_id: str,
    content_file: str,
    *,
    repo: str | None,
    cwd: str | None = None,
) -> ClarifyCommentResult:
    issue_text = _ensure_positive_text(issue, validation_error="invalid-issue")
    if kind not in {"request", "response"}:
        raise _ClarifyValidationError("invalid-kind")
    comment_id_text = _ensure_positive_text(comment_id, validation_error="invalid-id")
    content = _read_content_file(content_file)
    resolved_repo = _resolve_repo_for_clarify(runner, repo, cwd=cwd)
    marker_line = f"<!-- larch:clarify-{kind} id={comment_id_text} -->"
    body = f"{marker_line}\n{content}"
    redacted_body = redact.redact(body)
    if "[content truncated" in redacted_body:
        raise ShipError("redaction failed")
    result = gh.issue_comment_with_retry(
        runner,
        issue_text,
        redacted_body,
        repo=resolved_repo,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise ShipError(_combined(result) or f"gh issue comment failed ({result.returncode})")
    stripped = result.stdout.strip()
    match = _COMMENT_ID_RE.search(stripped)
    parsed_id = match.group(1) if match else ""
    return ClarifyCommentResult(
        posted=True,
        comment_id=parsed_id,
        comment_url=_kv_safe_text(stripped),
        marker=marker_line,
    )


def clarify_label(
    runner: Runner,
    issue: str,
    action: str,
    *,
    repo: str | None,
    create_if_missing: bool = False,
    cwd: str | None = None,
) -> ClarifyLabelResult:
    issue_text = _ensure_positive_text(issue, validation_error="invalid-issue")
    if action not in {"add", "remove"}:
        raise _ClarifyValidationError("invalid-action")
    resolved_repo = _resolve_repo_for_clarify(runner, repo, cwd=cwd)
    labels = gh.issue_labels_list(runner, issue_text, repo=resolved_repo, cwd=cwd)
    has_label = any(label == LABEL_NAME for label in labels)

    if action == "add":
        if has_label:
            return ClarifyLabelResult(changed=False, action=action, label=LABEL_NAME)
        if create_if_missing:
            create_result = gh.label_create(
                runner,
                LABEL_NAME,
                repo=resolved_repo,
                color=LABEL_COLOR,
                description=LABEL_DESCRIPTION,
                cwd=cwd,
            )
            if create_result.returncode != 0 and _DUPLICATE_LABEL_RE.search(_combined(create_result)) is None:
                raise ShipError(_combined(create_result) or "gh label create failed")
        add_result = gh.issue_label_add(runner, issue_text, LABEL_NAME, repo=resolved_repo, cwd=cwd)
        if add_result.returncode != 0:
            raise ShipError(_combined(add_result) or "gh issue label add failed")
        return ClarifyLabelResult(changed=True, action=action, label=LABEL_NAME)

    if not has_label:
        return ClarifyLabelResult(changed=False, action=action, label=LABEL_NAME)
    remove_result = gh.issue_label_remove(runner, issue_text, LABEL_NAME, repo=resolved_repo, cwd=cwd)
    if remove_result.returncode != 0:
        raise ShipError(_combined(remove_result) or "gh issue label remove failed")
    return ClarifyLabelResult(changed=True, action=action, label=LABEL_NAME)


def _runtime_error_text(exc: BaseException) -> str:
    return _redact_gh_error(str(exc))


def _parse_state_args(argv: list[str]) -> argparse.Namespace | None:
    parser = _parser(
        "clarify state",
        "clarify state --issue <N> [--repo OWNER/REPO]",
    )
    parser.add_argument("--issue")
    parser.add_argument("--repo")
    try:
        args = parser.parse_args(argv)
    except _ArgparseExit as exc:
        raise SystemExit(exc.status) from None
    if not args.issue:
        parser.print_usage(sys.stderr)
        raise SystemExit(1)
    return args


def clarify_state_main(argv: list[str]) -> int:
    try:
        args = _parse_state_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    logging_util.quiet_init(argv0="clarify-state.sh")
    if args is None or not _validate_positive_issue_for_cli(args.issue, verb="state"):
        return 1
    try:
        result = clarify_state(proc, args.issue, repo=args.repo)
    except _ClarifyValidationError as exc:
        _emit_failed(exc.token)
        return 1
    except _ClarifyRepoResolutionError:
        _emit_failed("could not determine repo")
        return 2
    except ShipError as exc:
        _emit_failed(_runtime_error_text(exc))
        return 2
    _emit_state(result)
    return 0


def _parse_comment_args(argv: list[str]) -> argparse.Namespace | None:
    parser = _parser(
        "clarify comment-post",
        "clarify comment-post --issue <N> --kind request|response --id <N> "
        "--content-file <path> [--repo OWNER/REPO]",
    )
    parser.add_argument("--issue")
    parser.add_argument("--kind")
    parser.add_argument("--id")
    parser.add_argument("--content-file")
    parser.add_argument("--repo")
    try:
        args = parser.parse_args(argv)
    except _ArgparseExit as exc:
        raise SystemExit(exc.status) from None
    if not args.issue or not args.kind or not args.id or not args.content_file:
        parser.print_usage(sys.stderr)
        raise SystemExit(1)
    return args


def clarify_comment_post_main(argv: list[str]) -> int:
    try:
        args = _parse_comment_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    logging_util.quiet_init(argv0="clarify-comment-post.sh")
    if args is None or not _validate_positive_issue_for_cli(args.issue, verb="comment-post"):
        return 1
    try:
        result = clarify_comment_post(
            proc,
            args.issue,
            args.kind,
            args.id,
            args.content_file,
            repo=args.repo,
        )
    except _ClarifyValidationError as exc:
        _emit_failed(exc.token)
        return 1
    except _ClarifyRepoResolutionError:
        _emit_failed("could not determine repo")
        return 2
    except ShipError as exc:
        _emit_failed(_runtime_error_text(exc))
        return 2
    _emit_comment(result)
    return 0


def _parse_label_args(argv: list[str]) -> argparse.Namespace | None:
    parser = _parser(
        "clarify label",
        "clarify label --issue <N> --action add|remove [--create-if-missing] "
        "[--repo OWNER/REPO]",
    )
    parser.add_argument("--issue")
    parser.add_argument("--action")
    parser.add_argument("--repo")
    parser.add_argument("--create-if-missing", action="store_true")
    try:
        args = parser.parse_args(argv)
    except _ArgparseExit as exc:
        raise SystemExit(exc.status) from None
    if not args.issue or not args.action:
        parser.print_usage(sys.stderr)
        raise SystemExit(1)
    return args


def clarify_label_main(argv: list[str]) -> int:
    try:
        args = _parse_label_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    logging_util.quiet_init(argv0="clarify-label.sh")
    if args is None or not _validate_positive_issue_for_cli(args.issue, verb="label"):
        return 1
    if args.action not in {"add", "remove"}:
        print("clarify-label.sh: --action must be add or remove", file=sys.stderr)
        return 1
    try:
        result = clarify_label(
            proc,
            args.issue,
            args.action,
            repo=args.repo,
            create_if_missing=bool(args.create_if_missing),
        )
    except _ClarifyValidationError as exc:
        _emit_failed(exc.token)
        return 1
    except _ClarifyRepoResolutionError:
        _emit_failed("could not determine repo")
        return 2
    except ShipError as exc:
        _emit_failed(_runtime_error_text(exc))
        return 2
    _emit_label(result)
    return 0
