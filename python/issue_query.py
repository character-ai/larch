# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
"""Issue state, field, and context query helpers."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
import gh
import logging_util
import proc
import redact
from errors import ShipError
from proc import CommandResult, Runner

_VALID_CONTEXT_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_CONTEXT_MISSING_VALUE_RC = 1
_CONTEXT_USAGE_RC = 2


@dataclass(frozen=True)
class IssueState:
    state: str
    url: str
    is_pr: bool



def _flat(text: str) -> str:
    redacted = redact.redact(text)
    return re.sub(r"[ \t]+", " ", redacted.replace("\r", " ").replace("\n", " ")).strip()


def _emit_failed(message: str) -> None:
    logging_util.emit_kv(key="FAILED", value="true")
    logging_util.emit_kv(key="ERROR", value=message)


def _bool_text(value: bool) -> str:  # noqa: FBT001 - bool value is the data being formatted, not a behavior flag.
    return "true" if value else "false"


def _raise_gh_failure(result: CommandResult) -> None:
    if result.returncode != 0:
        raise ShipError(f"gh issue view failed: {_flat(result.stdout + result.stderr)}")


def issue_state(runner: Runner, issue: str, *, repo: str | None) -> IssueState:
    result = gh.issue_view_state_url_read(runner, issue, repo=repo)
    _raise_gh_failure(result)
    try:
        data: object = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ShipError(f"gh issue view failed: JSON parse failed: {exc}") from exc
    if not isinstance(data, dict):
        raise ShipError("gh issue view failed: JSON payload was not an object")
    state = str(data.get("state", ""))
    url = str(data.get("url", ""))
    return IssueState(state=state, url=url, is_pr="/pull/" in url)


def issue_info(runner: Runner, issue: str, field: str, *, repo: str | None) -> str:
    if field not in {"state", "url"}:
        return ""
    try:
        result = gh.issue_view_field_read(runner, issue, field, repo=repo)
        if result.returncode != 0:
            return ""
        data: object = json.loads(result.stdout or "{}")
        if not isinstance(data, dict):
            return ""
        value: object | None = data.get(field)
        return value if isinstance(value, str) else str(value or "")
    except Exception:
        return ""


def issue_context(runner: Runner, issue: str, *, repo: str, tmpdir: str | Path) -> tuple[Path, Path]:
    result = gh.issue_view_title_body_read(runner, issue, repo=repo)
    _raise_gh_failure(result)
    try:
        data: object = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ShipError(f"gh issue view failed: JSON parse failed: {exc}") from exc
    if not isinstance(data, dict):
        raise ShipError("gh issue view failed: JSON payload was not an object")
    title: object | None = data.get("title")
    body: object | None = data.get("body")
    tmpdir_path = Path(tmpdir)
    try:
        tmpdir_path.mkdir(parents=True, exist_ok=True)
        title_tmp = tmpdir_path / "upstream-issue-title.txt.tmp"
        body_tmp = tmpdir_path / "upstream-issue-body.txt.tmp"
        title_file = tmpdir_path / "upstream-issue-title.txt"
        body_file = tmpdir_path / "upstream-issue-body.txt"
        title_tmp.write_text(title if isinstance(title, str) else str(title or ""), encoding="utf-8")
        body_tmp.write_text(body if isinstance(body, str) else str(body or ""), encoding="utf-8")
        title_tmp.replace(title_file)
        body_tmp.replace(body_file)
    except OSError as exc:
        raise ShipError(f"issue context write failed: {exc}") from exc
    return title_file, body_file


def _parse_state_args(argv: list[str]) -> tuple[str, str | None, str | None]:
    issue = ""
    repo: str | None = None
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--issue":
            if idx + 1 >= len(argv) or argv[idx + 1].startswith("--"):
                return issue, repo, "--issue requires a value"
            issue = argv[idx + 1]
            idx += 2
        elif token == "--repo":
            if idx + 1 >= len(argv) or argv[idx + 1].startswith("--"):
                return issue, repo, "--repo requires a value"
            repo = argv[idx + 1]
            idx += 2
        else:
            return issue, repo, f"unknown flag: {token}"
    if not issue:
        return issue, repo, "--issue is required"
    if not issue.isdigit():
        return issue, repo, "--issue must be numeric"
    return issue, repo, None


def _resolve_optional_repo(repo: str | None) -> str | None:
    if repo:
        return repo
    return gh.resolve_repo(proc)


def issue_state_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="get-issue-state.sh")
    issue, repo, error = _parse_state_args(argv)
    if error:
        _emit_failed(error)
        return 1
    resolved = _resolve_optional_repo(repo)
    try:
        state = issue_state(proc, issue, repo=resolved)
    except ShipError as exc:
        _emit_failed(str(exc))
        return 1
    logging_util.emit_kv(key="STATE", value=state.state)
    logging_util.emit_kv(key="URL", value=state.url)
    logging_util.emit_kv(key="IS_PR", value=_bool_text(state.is_pr))
    return 0


def _parse_value_args(argv: list[str]) -> tuple[dict[str, str], bool, bool]:
    values = {"issue": "", "field": "", "repo": ""}
    idx = 0
    unknown = False
    while idx < len(argv):
        token = argv[idx]
        if token in {"--issue", "--field", "--repo"}:
            if idx + 1 >= len(argv):
                return values, True, unknown
            values[token.removeprefix("--")] = argv[idx + 1]
            idx += 2
        else:
            unknown = True
            idx += 1
    return values, False, unknown


def issue_info_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="get-issue-info.sh")
    values, missing_value, unknown = _parse_value_args(argv)
    if missing_value:
        return 1
    if unknown or not values["issue"] or not values["field"] or values["field"] not in {"state", "url"}:
        logging_util.emit_kv(key="VALUE", value="")
        return 0
    repo = values["repo"] or gh.resolve_repo(proc)
    logging_util.emit_kv(key="VALUE", value=issue_info(proc, values["issue"], values["field"], repo=repo))
    return 0


def _usage() -> str:
    return "Usage: get-issue-context.sh --issue N --repo OWNER/REPO --tmpdir PATH"


def _parse_context_args(argv: list[str]) -> tuple[dict[str, str], int, bool]:
    values = {"issue": "", "repo": "", "tmpdir": ""}
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--help":
            return values, 0, True
        if token in {"--issue", "--repo", "--tmpdir"}:
            if idx + 1 >= len(argv):
                return values, _CONTEXT_MISSING_VALUE_RC, False
            values[token.removeprefix("--")] = argv[idx + 1]
            idx += 2
        else:
            return values, _CONTEXT_USAGE_RC, False
    if not values["issue"] or not values["repo"] or not values["tmpdir"]:
        return values, _CONTEXT_USAGE_RC, False
    if not re.fullmatch(r"[1-9][0-9]*", values["issue"]):
        return values, _CONTEXT_USAGE_RC, False
    if not _VALID_CONTEXT_REPO_RE.fullmatch(values["repo"]):
        return values, _CONTEXT_USAGE_RC, False
    if not values["tmpdir"]:
        return values, _CONTEXT_USAGE_RC, False
    return values, -1, False


def issue_context_main(argv: list[str]) -> int:
    values, status, help_requested = _parse_context_args(argv)
    if help_requested:
        print(_usage())
        return 0
    if status == _CONTEXT_MISSING_VALUE_RC:
        return _CONTEXT_MISSING_VALUE_RC
    if status == _CONTEXT_USAGE_RC:
        print(_usage(), file=sys.stderr)
        return _CONTEXT_USAGE_RC
    logging_util.quiet_init(argv0="get-issue-context.sh")
    try:
        title_file, body_file = issue_context(
            proc,
            values["issue"],
            repo=values["repo"],
            tmpdir=values["tmpdir"],
        )
    except ShipError as exc:
        _emit_failed(_flat(str(exc)))
        return 1
    logging_util.emit_kv(key="TITLE_FILE", value=str(title_file))
    logging_util.emit_kv(key="BODY_FILE", value=str(body_file))
    return 0
