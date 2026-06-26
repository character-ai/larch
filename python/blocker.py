# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
"""Issue blocker discovery helpers."""

from __future__ import annotations

import json
import re
from typing import cast

import gh
from larch.core import logging_util
from larch.core import proc
from larch.core.proc import Runner

_KEYWORD_RE = re.compile(
    r"(?:Depends on|Blocked by|Blocked on|Requires|Needs)[ \t]+#([0-9]+)(?:[^0-9]|$)",
    re.IGNORECASE,
)
_CODE_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_MARKDOWN_PREFIX_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?")
_EXAMPLE_PREFIX_RE = re.compile(r"^(?:example|examples|e\.g\.|eg\.|for example|sample)\b", re.IGNORECASE)
_NEGATION_RE = re.compile(r"\b(?:does\s+not|do\s+not|did\s+not|not|no|never|without)\b", re.IGNORECASE)
_NEGATION_SCOPE_BOUNDARY_RE = re.compile(r"(?:[.;:!?]|\b(?:and|but|however|then|yet)\b)", re.IGNORECASE)


def _has_scoped_negation(prefix: str) -> bool:
    clause = _NEGATION_SCOPE_BOUNDARY_RE.split(prefix)[-1]
    return _NEGATION_RE.search(clause) is not None


def parse_prose_blockers(text: str) -> list[int]:
    """Extract blocker issue numbers from one prose document, failing open."""
    try:
        refs: set[int] = set()
        in_fence = False
        for raw_line in (text or "").splitlines():
            if _CODE_FENCE_RE.match(raw_line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            line = re.sub(r"`[^`\n]*`", "", raw_line).replace("*", "").replace("_", "")
            line = _MARKDOWN_PREFIX_RE.sub("", line).strip()
            if not line or line.startswith("<!--") or _EXAMPLE_PREFIX_RE.match(line):
                continue
            for match in _KEYWORD_RE.finditer(line):
                prefix = line[: match.start()]
                if _has_scoped_negation(prefix):
                    continue
                refs.add(int(match.group(1)))
        return sorted(refs)
    except Exception:
        return []


def native_open_blockers(runner: Runner, issue: str, *, repo: str) -> list[int]:
    """Return open native GitHub dependency blockers, failing open."""
    try:
        result = gh.issue_blocked_by_read(runner, str(issue), repo=repo)
        if result.returncode != 0:
            return []
        rows = gh.loads_json_paginated_list(result.stdout)
        refs: set[int] = set()
        for row_obj in rows:
            if not isinstance(row_obj, dict):
                continue
            row = cast("dict[str, object]", row_obj)
            if str(row.get("state", "")).lower() != "open":
                continue
            number = row.get("number")
            if isinstance(number, int):
                refs.add(number)
            elif isinstance(number, str) and number.isdigit():
                refs.add(int(number))
        return sorted(refs)
    except Exception:
        return []


def _body_from_issue_json(text: str) -> str:
    data: object = json.loads(text or "{}")
    if not isinstance(data, dict):
        return ""
    body: object | None = data.get("body")
    return body if isinstance(body, str) else str(body or "")


def _comment_bodies(text: str) -> list[str]:
    rows = gh.loads_json_paginated_list(text or "[]")
    bodies: list[str] = []
    for row_obj in rows:
        if not isinstance(row_obj, dict):
            continue
        row = cast("dict[str, object]", row_obj)
        body = row.get("body")
        bodies.append(body if isinstance(body, str) else str(body or ""))
    return bodies


def prose_open_blockers(runner: Runner, issue: str, *, repo: str) -> list[int]:
    """Return open prose blockers from issue body and comments, failing open."""
    refs: set[int] = set()
    body_text = ""
    try:
        body_result = gh.issue_view_title_body_read(runner, str(issue), repo=repo)
        if body_result.returncode == 0:
            body_text = _body_from_issue_json(body_result.stdout)
    except Exception:
        body_text = ""
    refs.update(parse_prose_blockers(body_text))
    comment_bodies: list[str] = []
    try:
        comments_result = gh.issue_comments_list_read(runner, str(issue), repo=repo)
        if comments_result.returncode == 0:
            comment_bodies = _comment_bodies(comments_result.stdout)
    except Exception:
        comment_bodies = []
    for body in comment_bodies:
        refs.update(parse_prose_blockers(body))
    if str(issue).isdigit():
        refs.discard(int(issue))
    open_refs: set[int] = set()
    for ref in sorted(refs):
        try:
            state_result = gh.issue_view_state_url_read(runner, str(ref), repo=repo)
            if state_result.returncode != 0:
                continue
            state_data: object = json.loads(state_result.stdout or "{}")
            if isinstance(state_data, dict) and str(state_data.get("state", "")).lower() == "open":
                open_refs.add(ref)
        except Exception:  # noqa: S112 - per-ref state lookup is fail-open.
            continue
    return sorted(open_refs)


def all_open_blockers(runner: Runner, issue: str, *, repo: str) -> list[int]:
    """Return native blockers first, falling back to prose when native is empty."""
    native = native_open_blockers(runner, issue, repo=repo)
    if native:
        return native
    return prose_open_blockers(runner, issue, repo=repo)


def _parse_all_open_args(argv: list[str]) -> tuple[str, str | None]:
    issue = ""
    repo: str | None = None
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--issue":
            if idx + 1 >= len(argv):
                return "", repo
            issue = argv[idx + 1]
            idx += 2
        elif token == "--repo":
            if idx + 1 >= len(argv):
                return issue, None
            repo = argv[idx + 1]
            idx += 2
        else:
            idx += 1
    return issue, repo


def all_open_blockers_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="blocker-helpers.sh")
    issue, repo = _parse_all_open_args(argv)
    if not issue:
        logging_util.emit_kv(key="BLOCKERS", value="")
        return 0
    resolved = repo or gh.resolve_repo(proc)
    if not resolved:
        logging_util.emit_kv(key="BLOCKERS", value="")
        return 0
    blockers = all_open_blockers(proc, issue, repo=resolved)
    logging_util.emit_kv(key="BLOCKERS", value=" ".join(str(blocker) for blocker in blockers))
    return 0
