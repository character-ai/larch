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

import design_lifecycle
import design_pause
import gh
import larch_io
import logging_util
import proc
import redact
from errors import ShipError
from proc import CommandResult, Runner

LABEL_NAME = "needs-design-clarification"
LABEL_COLOR = "D73A4A"
LABEL_DESCRIPTION = "Issue plan requires clarification before /implement can proceed"
CLARIFY_ENV_ALLOW = frozenset({"CLAUDE_PLUGIN_ROOT", "DESIGN_TMPDIR", "SESSION_ID", "ISSUE_NUMBER", "REPO"})
ROUTE_STATE_ALLOW = frozenset({"REPO"})
REQUEST_STATE_ALLOW = frozenset(
    {"REQUEST_ID", "REQUEST_BODY_FILE", "PLAN_FILE", "RESPONSE_FILE", "ISSUE_NUMBER", "REPO"}
)

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


class ClarifyCommentFetchResult(NamedTuple):
    fetched: bool
    comment_id: str
    body_file: str


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


def _parser(*, prog: str, usage: str) -> _ClarifyParser:
    return _ClarifyParser(prog=prog, usage=usage, add_help=True)


def _bool_text(value: bool) -> str:  # noqa: FBT001 - bool value is the data being formatted, not a behavior flag.
    return "true" if value else "false"


def _is_positive_int_text(value: object) -> bool:
    text = "" if value is None else str(value)
    return text.isdigit() and text != "0"


def _validate_positive_issue_for_cli(*, value: object, verb: str) -> bool:
    if _is_positive_int_text(value):
        return True
    print(f"clarify-{verb}.sh: --issue must be a positive integer", file=sys.stderr)
    return False


def _resolve_repo_for_clarify(
    *, runner: Runner,
    repo: str | None,
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


def _emit_comment_fetch(result: ClarifyCommentFetchResult) -> None:
    logging_util.emit_kv("FETCHED", _bool_text(result.fetched))
    logging_util.emit_kv("COMMENT_ID", result.comment_id)
    logging_util.emit_kv("BODY_FILE", result.body_file)


def _emit_label(result: ClarifyLabelResult) -> None:
    logging_util.emit_kv("CHANGED", _bool_text(result.changed))
    logging_util.emit_kv("ACTION", result.action)
    logging_util.emit_kv("LABEL", result.label)


def _combined(result: CommandResult) -> str:
    return result.stdout + result.stderr


def _ensure_positive_text(*, value: object, validation_error: str) -> str:
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
    *, runner: Runner,
    issue: str,
    repo: str | None,
    cwd: str | None = None,
) -> ClarifyState:
    issue_text = _ensure_positive_text(value=issue, validation_error="invalid-issue")
    resolved_repo = _resolve_repo_for_clarify(runner=runner, repo=repo, cwd=cwd)
    result = gh.issue_comments_list_read(runner, issue_text, repo=resolved_repo, cwd=cwd)
    if result.returncode != 0:
        raise ShipError(_combined(result) or f"gh api comments fetch failed ({result.returncode})")
    return _evaluate_events(_events_from_comments(_comment_rows_from_stdout(result.stdout)))


def _write_text_file(*, path_text: str, content: str) -> None:
    path = Path(path_text)
    if path.is_dir():
        raise _ClarifyValidationError("write-target-directory")
    if path.is_symlink():
        raise _ClarifyValidationError("write-target-symlink")
    try:
        larch_io.atomic_write(path, content, prefix=f".{path.name}.")
    except OSError as exc:
        raise _ClarifyValidationError("write-failed") from exc


def clarify_comment_fetch(
    *, runner: Runner,
    issue: str,
    comment_id: str,
    out_file: str,
    repo: str | None,
    cwd: str | None = None,
) -> ClarifyCommentFetchResult:
    issue_text = _ensure_positive_text(value=issue, validation_error="invalid-issue")
    comment_id_text = _ensure_positive_text(value=comment_id, validation_error="invalid-id")
    resolved_repo = _resolve_repo_for_clarify(runner=runner, repo=repo, cwd=cwd)
    result = gh.issue_comments_list_read(runner, issue_text, repo=resolved_repo, cwd=cwd)
    if result.returncode != 0:
        raise ShipError(_combined(result) or f"gh api comments fetch failed ({result.returncode})")
    marker_line = f"<!-- larch:clarify-request id={comment_id_text} -->"
    for row in _comment_rows_from_stdout(result.stdout):
        body_obj = row.get("body")
        body = body_obj if isinstance(body_obj, str) else str(body_obj or "")
        first_line, sep, remainder = body.partition("\n")
        normalized = first_line.removeprefix("\ufeff").rstrip("\r")
        match = _MARKER_RE.fullmatch(normalized)
        if match is None or match.group(1) != "request" or match.group(2) != comment_id_text:
            continue
        row_id = row.get("id", "")
        _write_text_file(path_text=out_file, content=remainder if sep else "")
        return ClarifyCommentFetchResult(
            fetched=True,
            comment_id=str(row_id or ""),
            body_file=out_file,
        )
    raise _ClarifyValidationError(f"request comment not found: {marker_line}")


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
    *, runner: Runner,
    issue: str,
    kind: str,
    comment_id: str,
    content_file: str,
    repo: str | None,
    cwd: str | None = None,
) -> ClarifyCommentResult:
    issue_text = _ensure_positive_text(value=issue, validation_error="invalid-issue")
    if kind not in {"request", "response"}:
        raise _ClarifyValidationError("invalid-kind")
    comment_id_text = _ensure_positive_text(value=comment_id, validation_error="invalid-id")
    content = _read_content_file(content_file)
    resolved_repo = _resolve_repo_for_clarify(runner=runner, repo=repo, cwd=cwd)
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
    *, runner: Runner,
    issue: str,
    action: str,
    repo: str | None,
    create_if_missing: bool = False,
    cwd: str | None = None,
) -> ClarifyLabelResult:
    issue_text = _ensure_positive_text(value=issue, validation_error="invalid-issue")
    if action not in {"add", "remove"}:
        raise _ClarifyValidationError("invalid-action")
    resolved_repo = _resolve_repo_for_clarify(runner=runner, repo=repo, cwd=cwd)
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
        prog="clarify state",
        usage="clarify state --issue <N> [--repo OWNER/REPO]",
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
    if args is None or not _validate_positive_issue_for_cli(value=args.issue, verb="state"):
        return 1
    try:
        result = clarify_state(runner=proc, issue=args.issue, repo=args.repo)
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
        prog="clarify comment-post",
        usage="clarify comment-post --issue <N> --kind request|response --id <N> "
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


def _parse_comment_fetch_args(argv: list[str]) -> argparse.Namespace | None:
    parser = _parser(
        prog="clarify comment-fetch",
        usage="clarify comment-fetch --issue <N> --id <N> --out <path> [--repo OWNER/REPO]",
    )
    parser.add_argument("--issue")
    parser.add_argument("--id")
    parser.add_argument("--out")
    parser.add_argument("--repo")
    try:
        args = parser.parse_args(argv)
    except _ArgparseExit as exc:
        raise SystemExit(exc.status) from None
    if not args.issue or not args.id or not args.out:
        parser.print_usage(sys.stderr)
        raise SystemExit(1)
    return args


def clarify_comment_fetch_main(argv: list[str]) -> int:
    try:
        args = _parse_comment_fetch_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    logging_util.quiet_init(argv0="clarify-comment-fetch.sh")
    if args is None or not _validate_positive_issue_for_cli(value=args.issue, verb="comment-fetch"):
        return 1
    try:
        result = clarify_comment_fetch(
            runner=proc,
            issue=args.issue,
            comment_id=args.id,
            out_file=args.out,
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
    _emit_comment_fetch(result)
    return 0


def clarify_comment_post_main(argv: list[str]) -> int:
    try:
        args = _parse_comment_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    logging_util.quiet_init(argv0="clarify-comment-post.sh")
    if args is None or not _validate_positive_issue_for_cli(value=args.issue, verb="comment-post"):
        return 1
    try:
        result = clarify_comment_post(
            runner=proc,
            issue=args.issue,
            kind=args.kind,
            comment_id=args.id,
            content_file=args.content_file,
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
        prog="clarify label",
        usage="clarify label --issue <N> --action add|remove [--create-if-missing] "
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
    if args is None or not _validate_positive_issue_for_cli(value=args.issue, verb="label"):
        return 1
    if args.action not in {"add", "remove"}:
        print("clarify-label.sh: --action must be add or remove", file=sys.stderr)
        return 1
    try:
        result = clarify_label(
            runner=proc,
            issue=args.issue,
            action=args.action,
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


class DesignClarifyArgs(NamedTuple):
    session_env_path: str
    claude_pid: str
    phase: str
    issue: str


def _design_clarify_usage() -> None:
    print("Usage: design-clarify.sh --phase fetch|publish --issue N", file=sys.stderr)


def _fail_usage(message: str) -> NoReturn:
    print(f"design-clarify.sh: {message}", file=sys.stderr)
    raise SystemExit(2)


def _validate_positive_int(*, label: str, value: str) -> str:
    if not value or not value.isdigit() or value == "0":
        _fail_usage(f"{label} must be a positive integer")
    return value


def _parse_design_clarify_args(argv: list[str]) -> DesignClarifyArgs:
    data: dict[str, str] = {"--session-env-path": "", "--claude-pid": "", "--phase": "", "--issue": ""}
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token in data:
            if idx + 1 >= len(argv):
                _fail_usage(f"{token} requires a value")
            data[token] = argv[idx + 1]
            idx += 2
            continue
        if token in {"-h", "--help"}:
            _design_clarify_usage()
            raise SystemExit(0)
        _design_clarify_usage()
        _fail_usage(f"unknown option: {token}")
    if not data["--phase"]:
        _design_clarify_usage()
        _fail_usage("--phase is required")
    if data["--phase"] not in {"fetch", "publish"}:
        _fail_usage("--phase must be fetch or publish")
    if not data["--issue"]:
        _design_clarify_usage()
        _fail_usage("--issue is required")
    _validate_positive_int(label="--issue", value=data["--issue"])
    if data["--claude-pid"]:
        _validate_positive_int(label="--claude-pid", value=data["--claude-pid"])
    return DesignClarifyArgs(
        session_env_path=data["--session-env-path"],
        claude_pid=data["--claude-pid"],
        phase=data["--phase"],
        issue=data["--issue"],
    )


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _cli_cmd(plugin_root: Path, *args: str) -> list[str]:
    return [sys.executable, str(plugin_root / "python" / "cli.py"), *args]


def _build_driver_env(args: DesignClarifyArgs) -> tuple[dict[str, str], Path, Path]:
    env: dict[str, str] = {key: os.environ[key] for key in CLARIFY_ENV_ALLOW if key in os.environ}
    env.update(
        design_lifecycle._load_source_env(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            path=args.session_env_path,
            allow_keys=CLARIFY_ENV_ALLOW,
            claude_pid=args.claude_pid,
        )
    )
    if not env.get("CLAUDE_PLUGIN_ROOT"):
        env["CLAUDE_PLUGIN_ROOT"] = str(_plugin_root())
    design_tmpdir = design_lifecycle._require_design_tmpdir(env=env)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    env["DESIGN_TMPDIR"] = str(design_tmpdir)
    env["ISSUE_NUMBER"] = args.issue
    return env, design_tmpdir, Path(env["CLAUDE_PLUGIN_ROOT"])


def _write_result_env(*, path: str | Path, rows: list[tuple[str, str]]) -> None:
    destination = Path(path)
    if destination.is_symlink():
        raise _ClarifyValidationError(f"refusing symlink result env: {destination}")
    for _key, value in rows:
        if "\n" in value or "\r" in value:
            raise _ClarifyValidationError("refusing result env value with newline")
    larch_io.atomic_write(destination, larch_io.format_kvs(rows), prefix=f".{destination.name}.")


def _read_result_env(*, path: str | Path, allow_keys: frozenset[str]) -> dict[str, str]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise OSError(f"result env is not a regular file: {source}")
    return dict(design_lifecycle.phase_driver_read_result_env(path=source, allow_keys=allow_keys))


def _load_route_state_repo(*, env: dict[str, str], design_tmpdir: Path) -> bool:
    if env.get("REPO"):
        return True
    route_state = design_tmpdir / ".design-step0-route-state.env"
    if not route_state.exists():
        return True
    try:
        env.update(_read_result_env(path=route_state, allow_keys=ROUTE_STATE_ALLOW))
    except OSError:
        return False
    return True


def _validate_design_repo(repo: str) -> None:
    if repo and not gh.validate_repo_slug(repo):
        _fail_usage("invalid --repo")


def _write_text(*, path: Path, text: str) -> None:
    larch_io.write_text(path, text)


def _run_cli(
    plugin_root: Path,
    env: dict[str, str],
    *args: str,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
) -> CommandResult:
    result = proc.run(_cli_cmd(plugin_root, *args), env={**os.environ, **env})
    if stdout_path is not None:
        _write_text(path=stdout_path, text=result.stdout)
    if stderr_path is not None:
        _write_text(path=stderr_path, text=result.stderr)
    return result


def _append_clarify_failure(
    *, plugin_root: Path,
    design_tmpdir: Path,
    env: dict[str, str],
    site: str,
    tool: str,
    exit_code: int,
    output_file: Path,
) -> None:
    # Single-line argv mirrors design_lifecycle._append_failure to avoid R0801
    # duplicate-code collision with decompose._append_failure's multi-line form.
    _ = _run_cli(plugin_root, env, "run-log", "append-failure", "--log", str(design_tmpdir / "execution-issues.md"), "--site", site, "--tool", tool, "--exit-code", str(exit_code), "--category", "Warnings", "--output-file", str(output_file), "--redact")


def _stage_failed_clarify(
    *, plugin_root: Path,
    design_tmpdir: Path,
    env: dict[str, str],
    exit_code: int,
    detail_log: Path,
) -> None:
    if not detail_log.is_file():
        detail_log.write_text("clarify failure\n", encoding="utf-8")
    stdout_log = design_tmpdir / "design-clarify-stage.stdout.log"
    stderr_log = design_tmpdir / "design-clarify-stage.stderr.log"
    # Single-line argv avoids an R0801 duplicate-code collision with
    # test_design_lifecycle._stage_args's multi-line form (mirrors the
    # _append_clarify_failure single-line convention above).
    rc = design_lifecycle.capture_contract_stream_to_paths(
        design_lifecycle.stage_terminal_state_core,
        stdout_log,
        stderr_log,
        ["--design-tmpdir", str(design_tmpdir), "--outcome", "failed-clarify", "--step", "clarify", "--phase", "clarify-loop", "--site", "clarify-loop", "--trigger", "failed", "--bail-reason", "clarify-hard-halt", "--exit-code", str(exit_code), "--source-script", "clarify-loop", "--summary-outcome", "failed-clarify", "--failure-detail-log", str(detail_log)],
    )
    if rc != 0:
        _append_clarify_failure(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            env=env,
            site="design Step 0b clarify fetch",
            tool="design-stage-terminal-state.sh",
            exit_code=rc,
            output_file=stderr_log,
        )


def _parse_publish_ok(text: str) -> str:
    value = ""
    for line in text.splitlines():
        if line.startswith("PUBLISH_OK="):
            value = line.split("=", 1)[1]
    return value


def _emit_design_kvs(rows: list[tuple[str, str]]) -> None:
    for key, value in rows:
        print(f"{key}={value}")


def _fetch_failure(
    *, plugin_root: Path,
    design_tmpdir: Path,
    env: dict[str, str],
    status: str,
    detail_log: Path,
    exit_code: int = 1,
    extra_rows: list[tuple[str, str]] | None = None,
) -> int:
    rows = [("CLARIFY_FETCH_STATUS", status)]
    if extra_rows:
        rows.extend(extra_rows)
    rows.append(("SUMMARY_OUTCOME", "failed-clarify"))
    _write_result_env(path=design_tmpdir / ".design-clarify-fetch-result.env", rows=rows)
    _stage_failed_clarify(plugin_root=plugin_root, design_tmpdir=design_tmpdir, env=env, exit_code=exit_code, detail_log=detail_log)
    _emit_design_kvs(rows)
    return 1


def _publish_failure(
    *, design_tmpdir: Path,
    status: str,
    summary: str = "failed-clarify",
    extra_rows: list[tuple[str, str]] | None = None,
) -> int:
    rows = [("CLARIFY_PUBLISH_STATUS", status)]
    if extra_rows:
        rows.extend(extra_rows)
    rows.append(("SUMMARY_OUTCOME", summary))
    _write_result_env(path=design_tmpdir / ".design-clarify-publish-result.env", rows=rows)
    _emit_design_kvs(rows)
    return 1


def _handle_design_clarify_fetch(
    *, args: DesignClarifyArgs,
    env: dict[str, str],
    design_tmpdir: Path,
    plugin_root: Path,
) -> int:
    request_body_file = design_tmpdir / "clarify-request.md"
    plan_file = design_tmpdir / "clarify-plan.md"
    response_file = design_tmpdir / "clarify-response.md"
    repo = env.get("REPO") or None
    try:
        state = clarify_state(runner=proc, issue=args.issue, repo=repo)
    except (ShipError, _ClarifyValidationError, _ClarifyRepoResolutionError, RuntimeError) as exc:
        detail = design_tmpdir / "clarify-state.stderr"
        detail.write_text(_runtime_error_text(exc), encoding="utf-8")
        return _fetch_failure(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            env=env,
            status="state-failed",
            detail_log=detail,
            exit_code=1,
        )
    if state.state != "awaiting-response" or not state.last_request_id:
        detail = design_tmpdir / "clarify-fetch.failure.log"
        detail.write_text(f"unexpected clarify state: {state.state or '<empty>'}\n", encoding="utf-8")
        return _fetch_failure(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            env=env,
            status="unexpected-state",
            detail_log=detail,
            extra_rows=[("STATE", state.state)],
        )
    try:
        fetch = clarify_comment_fetch(
            runner=proc,
            issue=args.issue,
            comment_id=state.last_request_id,
            out_file=str(request_body_file),
            repo=repo,
        )
    except (ShipError, _ClarifyValidationError, _ClarifyRepoResolutionError, RuntimeError) as exc:
        detail = design_tmpdir / "clarify-comment-fetch.stderr"
        detail.write_text(_runtime_error_text(exc), encoding="utf-8")
        return _fetch_failure(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            env=env,
            status="fetch-failed",
            detail_log=detail,
            exit_code=1,
        )
    if not fetch.fetched:
        detail = design_tmpdir / "clarify-comment-fetch.stderr"
        detail.write_text("clarify comment fetch did not fetch\n", encoding="utf-8")
        return _fetch_failure(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            env=env,
            status="fetch-failed",
            detail_log=detail,
            exit_code=1,
        )
    rows = [
        ("CLARIFY_FETCH_STATUS", "ok"),
        ("REQUEST_ID", state.last_request_id),
        ("REQUEST_BODY_FILE", str(request_body_file)),
        ("PLAN_FILE", str(plan_file)),
        ("RESPONSE_FILE", str(response_file)),
        ("ISSUE_NUMBER", args.issue),
    ]
    if env.get("REPO"):
        rows.append(("REPO", env["REPO"]))
    request_rows = rows[1:]
    _write_result_env(path=design_tmpdir / ".design-clarify-request.env", rows=request_rows)
    _write_result_env(path=design_tmpdir / ".design-clarify-fetch-result.env", rows=rows)
    _emit_design_kvs(rows)
    return 0


def _publish_artifact_ok(path_text: str) -> bool:
    path = Path(path_text)
    try:
        return not path.is_symlink() and path.is_file() and os.access(path, os.R_OK) and path.stat().st_size > 0
    except OSError:
        return False


def _handle_design_clarify_publish(
    *, args: DesignClarifyArgs,
    env: dict[str, str],
    design_tmpdir: Path,
    plugin_root: Path,
) -> int:
    request_state_env = design_tmpdir / ".design-clarify-request.env"
    try:
        request = _read_result_env(path=request_state_env, allow_keys=REQUEST_STATE_ALLOW)
    except OSError:
        return _publish_failure(design_tmpdir=design_tmpdir, status="missing-request-state")
    request_id = request.get("REQUEST_ID", "")
    _validate_positive_int(label="REQUEST_ID", value=request_id)
    if request.get("ISSUE_NUMBER", "") != args.issue:
        return _publish_failure(design_tmpdir=design_tmpdir, status="issue-mismatch")
    if "REPO" in request:
        env["REPO"] = request["REPO"]
    _validate_design_repo(env.get("REPO", ""))
    plan_file = request.get("PLAN_FILE", "")
    response_file = request.get("RESPONSE_FILE", "")
    if not _publish_artifact_ok(plan_file) or not _publish_artifact_ok(response_file):
        return _publish_failure(design_tmpdir=design_tmpdir, status="missing-artifact")

    redacted_plan = design_tmpdir / "clarify-plan.redacted.md"
    try:
        redacted = redact.redact_secrets_only(Path(plan_file).read_text(encoding="utf-8", errors="replace"))
    except (OSError, RuntimeError):
        return _publish_failure(design_tmpdir=design_tmpdir, status="redact-failed", summary="failed-plan-write")
    redacted_plan.write_text(redacted, encoding="utf-8")
    if not redacted_plan.is_file() or redacted_plan.stat().st_size == 0:
        return _publish_failure(design_tmpdir=design_tmpdir, status="redact-empty", summary="failed-plan-write")

    repo_args = ["--repo", env["REPO"]] if env.get("REPO") else []
    plan_write = _run_cli(
        plugin_root,
        env,
        "named-block",
        "write",
        "--marker",
        "plan",
        "--issue",
        args.issue,
        "--content-file",
        str(redacted_plan),
        *repo_args,
        stdout_path=design_tmpdir / "clarify-plan-write.stdout",
        stderr_path=design_tmpdir / "clarify-plan-write.stderr",
    )
    if plan_write.returncode != 0:
        (design_tmpdir / "clarify-plan-write.failure.log").write_text(
            "plan-block write failed\n",
            encoding="utf-8",
        )
        return _publish_failure(
            design_tmpdir=design_tmpdir,
            status="plan-write-failed",
            summary="failed-plan-write",
            extra_rows=[("PLAN_WRITE_OK", "false")],
        )

    publish_ok = "false"
    session_id = env.get("SESSION_ID", "")
    if session_id:
        publish = _run_cli(
            plugin_root,
            env,
            "design",
            "log-publish",
            "--design-tmpdir",
            str(design_tmpdir),
            "--run-id",
            session_id,
            "--issue",
            args.issue,
            *repo_args,
            stdout_path=design_tmpdir / "design-log-publish.stdout",
            stderr_path=design_tmpdir / "design-log-publish.failure.log",
        )
        parsed_publish_ok = _parse_publish_ok(publish.stdout)
        if publish.returncode == 0 and parsed_publish_ok == "true":
            publish_ok = "true"
        else:
            failure_exit = publish.returncode if publish.returncode != 0 else 1
            _append_clarify_failure(
                plugin_root=plugin_root,
                design_tmpdir=design_tmpdir,
                env=env,
                site="design Step 0b clarify publish",
                tool="design-log-publish.sh",
                exit_code=failure_exit,
                output_file=design_tmpdir / "design-log-publish.failure.log",
            )
    else:
        print("\n**⚠ /design: SESSION_ID missing; skipping design log publish**")

    try:
        posted = clarify_comment_post(
            runner=proc,
            issue=args.issue,
            kind="response",
            comment_id=request_id,
            content_file=response_file,
            repo=env.get("REPO") or None,
        )
        (design_tmpdir / "clarify-comment-post.stdout").write_text(
            "\n".join(
                [
                    f"POSTED={_bool_text(posted.posted)}",
                    f"COMMENT_ID={posted.comment_id}",
                    f"COMMENT_URL={posted.comment_url}",
                    f"MARKER={posted.marker}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    except (ShipError, _ClarifyValidationError, _ClarifyRepoResolutionError, RuntimeError) as exc:
        (design_tmpdir / "clarify-comment-post.stderr").write_text(_runtime_error_text(exc), encoding="utf-8")
        return _publish_failure(
            design_tmpdir=design_tmpdir,
            status="comment-post-failed",
            extra_rows=[("PLAN_WRITE_OK", "true"), ("PUBLISH_OK", publish_ok)],
        )

    try:
        label = clarify_label(runner=proc, issue=args.issue, action="remove", repo=env.get("REPO") or None)
        (design_tmpdir / "clarify-label-remove.stdout").write_text(
            "\n".join(
                [
                    f"CHANGED={_bool_text(label.changed)}",
                    f"ACTION={label.action}",
                    f"LABEL={label.label}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    except (ShipError, _ClarifyValidationError, _ClarifyRepoResolutionError, RuntimeError) as exc:
        (design_tmpdir / "clarify-label-remove.stderr").write_text(_runtime_error_text(exc), encoding="utf-8")
        return _publish_failure(
            design_tmpdir=design_tmpdir,
            status="label-remove-failed",
            extra_rows=[("PLAN_WRITE_OK", "true"), ("PUBLISH_OK", publish_ok)],
        )

    renamed = ""
    if session_id and publish_ok == "true":
        rename = _run_cli(
            plugin_root,
            env,
            "tracking-issue",
            "rename",
            "--issue",
            args.issue,
            "--state",
            "designing",
            *repo_args,
            stdout_path=design_tmpdir / "clarify-rename.stdout",
            stderr_path=design_tmpdir / "clarify-rename.stderr",
        )
        if rename.returncode == 0:
            for line in rename.stdout.splitlines():
                if line.startswith("RENAMED="):
                    renamed = line.split("=", 1)[1]
        else:
            renamed = "false"
            _append_clarify_failure(
                plugin_root=plugin_root,
                design_tmpdir=design_tmpdir,
                env=env,
                site="design Step 0b clarify rename",
                tool="python/cli.py tracking-issue rename",
                exit_code=rename.returncode,
                output_file=design_tmpdir / "clarify-rename.stderr",
            )

    rows = [
        ("CLARIFY_PUBLISH_STATUS", "ok"),
        ("PLAN_WRITE_OK", "true"),
        ("PUBLISH_OK", publish_ok),
        ("RENAMED", renamed),
        ("SUMMARY_OUTCOME", "cancelled-clarify"),
    ]
    _write_result_env(path=design_tmpdir / ".design-clarify-publish-result.env", rows=rows)
    _emit_design_kvs(rows)
    return 0


def design_clarify_main(argv: list[str]) -> int:
    try:
        args = _parse_design_clarify_args(argv)
        env, design_tmpdir, plugin_root = _build_driver_env(args)
        route_state_ok = _load_route_state_repo(env=env, design_tmpdir=design_tmpdir)
        if not route_state_ok:
            route_state_log = design_tmpdir / "clarify-route-state.failure.log"
            route_state_log.write_text("could not read route state sidecar\n", encoding="utf-8")
            if args.phase == "fetch":
                return _fetch_failure(
                    plugin_root=plugin_root,
                    design_tmpdir=design_tmpdir,
                    env=env,
                    status="route-state-read-failed",
                    detail_log=route_state_log,
                    exit_code=1,
                )
            return _publish_failure(design_tmpdir=design_tmpdir, status="route-state-read-failed")
        _validate_design_repo(env.get("REPO", ""))
        if (design_tmpdir / ".pause-requested").is_file():
            pause_args = ["--design-tmpdir", str(design_tmpdir), "--issue", args.issue]
            if env.get("REPO"):
                pause_args.extend(["--repo", env["REPO"]])
            return design_pause.pause_save_main(pause_args)
        if args.phase == "fetch":
            return _handle_design_clarify_fetch(args=args, env=env, design_tmpdir=design_tmpdir, plugin_root=plugin_root)
        return _handle_design_clarify_publish(args=args, env=env, design_tmpdir=design_tmpdir, plugin_root=plugin_root)
    except SystemExit as exc:
        return int(exc.code or 0)
    except _ClarifyValidationError as exc:
        print(f"design-clarify.sh: {exc}", file=sys.stderr)
        return 2
