# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Python entrypoints for /issue helper surfaces.

`issue parse-input`, `issue allocate-candidates`, `issue list-issues`, and
`issue fetch-issue-details` moved to the Rust owner in #8168, and
`issue create-one`, `issue write-sentinel`, and `issue cleanup-failed`
followed in #8169. `parse_issue_input` stays because it is not a command: it is
the in-process grammar ``larch.issue.file_oos``, ``larch.issue.umbrella``, and
``larch.issue.learn_from_bugs`` still call directly, and those modules migrate
with their own command leaves.

What remains here is the dependency-edge half of the module: `issue
add-blocked-by` and `issue add-sub-issue`, which migrate under #8170.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable

from larch.core import config
from larch.core import logging_util
from larch.core import proc
from larch.design.plan_grammar import balanced_fence_line_indices
from larch.errors import ShipError
from larch.git import gh
from larch.core.redact import redact_secrets_outbound
from larch.state import session_env as _session_env

# Fast path only: a match skips a read-back. Never the sole authority for
# success, because GitHub's real duplicate-relation prose matches nothing here.
IDEMPOTENT_RE = re.compile(r"already (exists|tracked|added)|duplicate dependency", re.IGNORECASE)
THIRD_ATTEMPT = 2
OOS_HEADING_RE = re.compile(r"^###[ \t]+OOS_[0-9]+:[ \t]+(.+)$")
PLAIN_HEADING_RE = re.compile(r"^###[ \t]+(.+)$")
DESC_RE = re.compile(r"^-[ \t]+\*\*Description\*\*:[ \t]*(.*)$")
# FINDING-block OOS (review pipeline) uses `**Concern**` for the body and
# `**Reviewer(s)**` for attribution; treat them as Description/Reviewer
# equivalents so review-surfaced accepted OOS file with a non-empty body (#5260).
CONCERN_RE = re.compile(r"^-[ \t]+\*\*Concern\*\*:[ \t]*(.*)$")
REVIEWER_RE = re.compile(r"^-[ \t]+\*\*Reviewer(?:\(s\))?\*\*:[ \t]+(.+)$")
VOTE_RE = re.compile(r"^-[ \t]+\*\*Vote tally\*\*:[ \t]+(.+)$")
PHASE_RE = re.compile(r"^-[ \t]+\*\*Phase\*\*:[ \t]+(.+)$")


def _gh_read(argv: list[str], *, cwd: str | None = None) -> proc.CommandResult:
    return gh.command(proc, argv, timeout=config.CI_STATUS_QUERY_TIMEOUT_SEC, cwd=cwd)


def warn(message: str) -> None:
    print(message, file=sys.stderr)


def _flat_error(*, text: str, limit: int = 500) -> str:
    return " ".join(redact_secrets_outbound(text).split())[:limit]


@dataclass(frozen=True)
class ParsedItem:
    title: str
    body: str
    reviewer: str = ""
    vote: str = ""
    phase: str = ""
    malformed: bool = False


@dataclass(frozen=True)
class BlockedByResult:
    """The outcome of adding one native GitHub blocked-by relationship."""

    client: str
    blocker: str
    added: bool
    error: str = ""
    exit_code: int = 0


@dataclass(frozen=True)
class SubIssueResult:
    """The verified outcome of adding one direct native sub-issue link."""

    parent: str
    child: str
    added: bool
    error: str = ""
    exit_code: int = 0


# Mutable parser state: methods update current_* / pending_* / items in place while scanning.
@dataclass
class ParseState:
    current_title: str = ""
    current_body: str = ""
    current_reviewer: str = ""
    current_vote: str = ""
    current_phase: str = ""
    in_body: bool = False
    current_mode: str = ""
    parse_mode: str = "generic"
    pending_heading: str = ""
    pending_body: str = ""
    items: list[ParsedItem] = field(default_factory=list)

    def fold_pending(self) -> None:
        if not self.pending_heading:
            return
        if self.current_body:
            self.current_body += "\n" + self.pending_heading
        else:
            self.current_body = self.pending_heading
        if self.pending_body:
            self.current_body += "\n" + self.pending_body
        self.pending_heading = ""
        self.pending_body = ""

    def emit_current(self, *, force_malformed: bool = False) -> None:
        if not self.current_title:
            self.reset()
            return
        malformed = force_malformed or not self.current_body
        self.items.append(
            ParsedItem(
                self.current_title,
                self.current_body,
                self.current_reviewer,
                self.current_vote,
                self.current_phase,
                malformed,
            ),
        )
        self.reset()

    def split_pending(self) -> None:
        if not self.pending_heading:
            return
        pending_heading = self.pending_heading
        pending_body = self.pending_body
        self.pending_heading = ""
        self.pending_body = ""
        if self.current_title:
            self.items.append(
                ParsedItem(
                    self.current_title,
                    self.current_body,
                    self.current_reviewer,
                    self.current_vote,
                    self.current_phase,
                    malformed=True,
                ),
            )
        self.current_title = ""
        self.current_body = ""
        self.current_reviewer = ""
        self.current_vote = ""
        self.current_phase = ""
        self.in_body = False
        self.current_mode = ""
        match = PLAIN_HEADING_RE.match(pending_heading)
        if match:
            self.items.append(ParsedItem(match.group(1), pending_body, malformed=not bool(pending_body)))

    def reset(self) -> None:
        self.current_title = ""
        self.current_body = ""
        self.current_reviewer = ""
        self.current_vote = ""
        self.current_phase = ""
        self.in_body = False
        self.current_mode = ""
        self.pending_heading = ""
        self.pending_body = ""

    def consume_oos_field(self, line: str) -> bool:
        """Consume an OOS metadata/body field line, returning True on a match.

        `**Concern**` is treated as a Description-equivalent and `**Reviewer(s)**`
        as a Reviewer-equivalent so FINDING-block accepted OOS still capture a
        body instead of dropping it (#5260).
        """
        if match := DESC_RE.match(line):
            self.fold_pending()
            self.current_body = match.group(1)
            self.in_body = True
            return True
        if match := CONCERN_RE.match(line):
            self.fold_pending()
            inline = match.group(1)
            if not self.current_body:
                self.current_body = inline
            elif inline:
                self.current_body += "\n" + inline
            self.in_body = True
            return True
        if match := REVIEWER_RE.match(line):
            self.fold_pending()
            self.current_reviewer = match.group(1)
            self.in_body = False
            return True
        if match := VOTE_RE.match(line):
            self.fold_pending()
            self.current_vote = match.group(1)
            self.in_body = False
            return True
        if match := PHASE_RE.match(line):
            self.fold_pending()
            self.current_phase = match.group(1)
            self.in_body = False
            return True
        return False


def parse_issue_input(text: str) -> tuple[list[ParsedItem], str]:
    state = ParseState()
    lines = text.splitlines()
    fenced_lines = balanced_fence_line_indices(lines)
    for index, line in enumerate(lines):
        in_fence = index in fenced_lines
        if not in_fence and (match := OOS_HEADING_RE.match(line)):
            if state.current_mode == "generic" and state.in_body and state.current_body.strip():
                state.current_body += "\n" + line
            else:
                new_title = match.group(1)
                state.split_pending()
                state.emit_current()
                state.current_title = new_title
                # Default to body capture so an OOS block with no `- **Description**:`
                # line still accumulates its content instead of dropping it (#5260).
                # A following `- **Reviewer(s)**:`/`- **Vote tally**:`/`- **Phase**:`
                # line still flips this back off as metadata.
                state.in_body = True
                state.current_mode = "oos"
                state.parse_mode = "oos"
        elif not in_fence and (match := PLAIN_HEADING_RE.match(line)):
            if state.current_mode == "oos" and state.in_body:
                if not state.pending_heading:
                    state.pending_heading = line
                elif state.pending_body:
                    state.pending_body += "\n" + line
                else:
                    state.pending_body = line
            else:
                state.emit_current()
                state.current_title = match.group(1)
                state.in_body = True
                state.current_mode = "generic"
        elif not in_fence and state.current_mode == "oos" and state.consume_oos_field(line):
            pass
        elif state.in_body:
            if state.pending_heading:
                if state.pending_body:
                    state.pending_body += "\n" + line
                else:
                    state.pending_body = line
            elif state.current_body:
                state.current_body += "\n" + line
            else:
                state.current_body = line
    state.split_pending()
    state.emit_current()
    return state.items, state.parse_mode


def _resolve_repo() -> str:
    return gh.resolve_repo(proc) or ""


def _positive_int(value: str) -> bool:
    return value.isdigit() and int(value) > 0


def _blocked_failure(*, client: str, blocker: str, message: str, code: int = 2) -> BlockedByResult:
    try:
        error_text = _flat_error(text=message)
    except Exception as exc:  # pragma: no cover - defensive seam for tests
        return BlockedByResult(client=client, blocker=blocker, added=False, error=f"redaction:{exc}", exit_code=3)
    return BlockedByResult(client=client, blocker=blocker, added=False, error=error_text, exit_code=code)


def _blocked_by_read_back(*, client: str, blocker: str, repo: str) -> bool:
    """Report whether the live blocked-by set of ``client`` contains ``blocker``.

    Fail closed: a transport failure or a malformed payload proves nothing, so
    it reports absence and the caller surfaces the original mutation error.
    """
    result = gh.issue_blocked_by_read(proc, client, repo=repo)
    if result.returncode != 0:
        return False
    try:
        rows: list[object] = gh.loads_json_paginated_list(result.stdout)
    except ShipError:
        return False
    return any(isinstance(row, dict) and str(row.get("number") or "") == blocker for row in rows)


def add_blocked_by(  # noqa: PLR0913 - CLI mutation authorization inputs remain explicit at the boundary.
    *,
    client: str,
    blocker: str,
    blocker_id: str = "",
    repo: str = "",
    context_file: Path | None = None,
    operator_invoked: bool = False,
    run_id: str = "",
    trusted_root: Path | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> BlockedByResult:
    """Add one dependency edge with the CLI's retry and idempotency contract."""
    if not _positive_int(value=client) or not _positive_int(value=blocker):
        return _blocked_failure(client=client, blocker=blocker, message="client-issue and blocker-issue must be positive integers", code=1)
    if blocker_id and not _positive_int(value=blocker_id):
        return _blocked_failure(client=client, blocker=blocker, message="blocker-id must be a positive integer when provided", code=1)
    authorized, auth_reason = _session_env.check_live_mutation_auth(
        context_file=context_file,
        operator_mode=operator_invoked,
        run_id=run_id,
        trusted_root=trusted_root,
    )
    if not authorized:
        return _blocked_failure(
            client=client,
            blocker=blocker,
            message=f"{config.LIVE_MUTATION_REFUSAL_REASON}:{auth_reason}",
            code=config.EXIT_MUTATION_REFUSED,
        )
    if not repo:
        repo = _resolve_repo()
        if not repo:
            return _blocked_failure(client=client, blocker=blocker, message="could not determine repo")
    if not blocker_id:
        lookup = _gh_read(["api", f"/repos/{repo}/issues/{blocker}", "--jq", ".id"])
        blocker_id = lookup.stdout.strip()
        if lookup.returncode != 0:
            return _blocked_failure(client=client, blocker=blocker, message=f"blocker-id lookup failed for #{blocker}: {lookup.stderr}")
        if not _positive_int(value=blocker_id):
            return _blocked_failure(client=client, blocker=blocker, message=f"blocker-id lookup returned non-numeric id for #{blocker}: '{blocker_id}'")
    body = json.dumps({"issue_id": int(blocker_id)})
    last_error = "unknown error"
    for attempt in range(3):
        if attempt == 1:
            sleep_fn(10)
        elif attempt == THIRD_ATTEMPT:
            sleep_fn(30)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=tempfile.gettempdir(), delete=False) as tmp:
            tmp.write(body)
            tmp_path = tmp.name
        try:
            result = gh.command(proc, ["api", f"/repos/{repo}/issues/{client}/dependencies/blocked_by", "-X", "POST", "--input", tmp_path])
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        err = result.stderr or result.stdout
        if result.returncode == 0:
            return BlockedByResult(client=client, blocker=blocker, added=True)
        if re.search(r"HTTP 404|status 404|404 Not Found", err, re.IGNORECASE):
            return _blocked_failure(client=client, blocker=blocker, message=f"feature-unavailable: {err}")
        if re.search(r"HTTP 422", err, re.IGNORECASE):
            # A 422 is deterministic, so retrying it cannot change the outcome.
            # Decide it from the live edge set, never from GitHub's error prose;
            # IDEMPOTENT_RE is only a fast path that skips the read-back.
            if IDEMPOTENT_RE.search(err) or _blocked_by_read_back(client=client, blocker=blocker, repo=repo):
                return BlockedByResult(client=client, blocker=blocker, added=True)
            return _blocked_failure(client=client, blocker=blocker, message=err)
        last_error = err
    return _blocked_failure(client=client, blocker=blocker, message=f"all 3 attempts failed: {last_error}")


def emit_blocked_by_result(result: BlockedByResult) -> int:
    """Emit the stable CLI KV contract for :func:`add_blocked_by`."""
    if result.added:
        logging_util.emit_kv(key="BLOCKED_BY_ADDED", value="true")
    else:
        if result.exit_code == config.EXIT_MUTATION_REFUSED:
            logging_util.emit_kv(key=config.LIVE_MUTATION_REFUSAL_STATUS, value="true")
        logging_util.emit_kv(key="BLOCKED_BY_FAILED", value="true")
    logging_util.emit_kv(key="CLIENT", value=result.client)
    logging_util.emit_kv(key="BLOCKER", value=result.blocker)
    if result.error:
        logging_util.emit_kv(key="ERROR", value=logging_util.sanitize_diagnostic_line(result.error))
    return result.exit_code


def add_blocked_by_main(argv: list[str], sleep_fn: Callable[[float], None] = time.sleep) -> int:
    values: dict[str, str] = {}
    flags: set[str] = set()
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in {"--client-issue", "--blocker-issue", "--blocker-id", "--repo", "--context-file", "--run-id", "--trusted-root"} and index + 1 < len(argv):
            values[arg] = argv[index + 1]
            index += 2
        elif arg == "--operator-invoked":
            flags.add(arg)
            index += 1
        else:
            warn(f"Unknown option: {arg}")
            return 1
    client = values.get("--client-issue", "")
    blocker = values.get("--blocker-issue", "")
    if not client or not blocker:
        warn("Usage: add-blocked-by --client-issue N --blocker-issue M [--blocker-id ID] [--repo OWNER/REPO] [--operator-invoked | --context-file PATH --run-id ID --trusted-root PATH]")
        return 1
    return emit_blocked_by_result(
        add_blocked_by(
            client=client,
            blocker=blocker,
            blocker_id=values.get("--blocker-id", ""),
            repo=values.get("--repo", ""),
            context_file=Path(values["--context-file"]) if "--context-file" in values else None,
            operator_invoked="--operator-invoked" in flags,
            run_id=values.get("--run-id", ""),
            trusted_root=Path(values["--trusted-root"]) if "--trusted-root" in values else None,
            sleep_fn=sleep_fn,
        )
    )


def _sub_issue_failure(*, parent: str, child: str, message: str, code: int = 2) -> SubIssueResult:
    return SubIssueResult(
        parent=parent,
        child=child,
        added=False,
        error=_flat_error(text=message),
        exit_code=code,
    )


def _sub_issue_read_back(*, parent: str, child: str, repo: str) -> bool:
    result = gh.issue_sub_issues_read(proc, parent, repo=repo)
    if result.returncode != 0:
        return False
    try:
        # The read paginates, so a parent past one page emits concatenated
        # arrays that plain json.loads rejects as a false "relation absent".
        rows: list[object] = gh.loads_json_paginated_list(result.stdout)
    except ShipError:
        return False
    return any(isinstance(row, dict) and str(row.get("number") or "") == child for row in rows)


def add_sub_issue(  # noqa: PLR0913 - CLI mutation authorization inputs remain explicit at the boundary.
    *,
    parent: str,
    child: str,
    child_id: str = "",
    repo: str = "",
    context_file: Path | None = None,
    operator_invoked: bool = False,
    run_id: str = "",
    trusted_root: Path | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> SubIssueResult:
    """Add a direct sub-issue relation, then prove it by a fresh read-back."""
    if not _positive_int(value=parent) or not _positive_int(value=child):
        return _sub_issue_failure(parent=parent, child=child, message="parent-issue and child-issue must be positive integers", code=1)
    if child_id and not _positive_int(value=child_id):
        return _sub_issue_failure(parent=parent, child=child, message="child-id must be a positive integer when provided", code=1)
    authorized, auth_reason = _session_env.check_live_mutation_auth(
        context_file=context_file,
        operator_mode=operator_invoked,
        run_id=run_id,
        trusted_root=trusted_root,
    )
    if not authorized:
        return _sub_issue_failure(parent=parent, child=child, message=f"{config.LIVE_MUTATION_REFUSAL_REASON}:{auth_reason}", code=config.EXIT_MUTATION_REFUSED)
    if not repo:
        repo = _resolve_repo()
    if not repo:
        return _sub_issue_failure(parent=parent, child=child, message="could not determine repo")
    if not child_id:
        lookup = _gh_read(["api", f"/repos/{repo}/issues/{child}", "--jq", ".id"])
        child_id = lookup.stdout.strip()
        if lookup.returncode != 0 or not _positive_int(value=child_id):
            return _sub_issue_failure(parent=parent, child=child, message=f"child-id lookup failed for #{child}: {lookup.stderr or child_id}")
    return _add_sub_issue_with_retry(parent=parent, child=child, child_id=child_id, repo=repo, sleep_fn=sleep_fn)


def _add_sub_issue_with_retry(
    *,
    parent: str,
    child: str,
    child_id: str,
    repo: str,
    sleep_fn: Callable[[float], None],
) -> SubIssueResult:
    """Add the relation with bounded retries, then prove it by a fresh read-back."""
    last_error = "unknown error"
    for attempt in range(3):
        if attempt == 1:
            sleep_fn(10)
        elif attempt == THIRD_ATTEMPT:
            sleep_fn(30)
        result = gh.issue_add_sub_issue(proc, parent, int(child_id), repo=repo)
        detail = result.stderr or result.stdout
        # A 422 is deterministic, so retrying it cannot change the outcome. Let
        # the read-back decide it, never GitHub's error prose: it reports the
        # duplicate-relation case as success and leaves a genuine conflict, such
        # as a child already parented elsewhere, failing with GitHub's message.
        if result.returncode == 0 or re.search(r"HTTP 422", detail, re.IGNORECASE):
            if _sub_issue_read_back(parent=parent, child=child, repo=repo):
                return SubIssueResult(parent=parent, child=child, added=True)
            if result.returncode == 0:
                return _sub_issue_failure(parent=parent, child=child, message="sub-issue relation read-back failed")
            return _sub_issue_failure(parent=parent, child=child, message=detail)
        if re.search(r"HTTP 404|status 404|404 Not Found", detail, re.IGNORECASE):
            return _sub_issue_failure(parent=parent, child=child, message=f"feature-unavailable: {detail}")
        last_error = detail
    return _sub_issue_failure(parent=parent, child=child, message=f"all 3 attempts failed: {last_error}")


def emit_sub_issue_result(result: SubIssueResult) -> int:
    if result.added:
        logging_util.emit_kv(key="SUB_ISSUE_ADDED", value="true")
    else:
        if result.exit_code == config.EXIT_MUTATION_REFUSED:
            logging_util.emit_kv(key=config.LIVE_MUTATION_REFUSAL_STATUS, value="true")
        logging_util.emit_kv(key="SUB_ISSUE_FAILED", value="true")
    logging_util.emit_kv(key="PARENT", value=result.parent)
    logging_util.emit_kv(key="CHILD", value=result.child)
    if result.error:
        logging_util.emit_kv(key="ERROR", value=logging_util.sanitize_diagnostic_line(result.error))
    return result.exit_code


def add_sub_issue_main(argv: list[str], sleep_fn: Callable[[float], None] = time.sleep) -> int:
    values: dict[str, str] = {}
    flags: set[str] = set()
    index = 0
    value_flags = {"--parent-issue", "--child-issue", "--child-id", "--repo", "--context-file", "--run-id", "--trusted-root"}
    while index < len(argv):
        arg = argv[index]
        if arg in value_flags and index + 1 < len(argv):
            values[arg] = argv[index + 1]
            index += 2
        elif arg == "--operator-invoked":
            flags.add(arg)
            index += 1
        else:
            warn(f"Unknown option: {arg}")
            return 1
    parent = values.get("--parent-issue", "")
    child = values.get("--child-issue", "")
    if not parent or not child:
        warn("Usage: add-sub-issue --parent-issue N --child-issue M [--child-id ID] [--repo OWNER/REPO]")
        return 1
    return emit_sub_issue_result(add_sub_issue(
        parent=parent,
        child=child,
        child_id=values.get("--child-id", ""),
        repo=values.get("--repo", ""),
        context_file=Path(values["--context-file"]) if "--context-file" in values else None,
        operator_invoked="--operator-invoked" in flags,
        run_id=values.get("--run-id", ""),
        trusted_root=Path(values["--trusted-root"]) if "--trusted-root" in values else None,
        sleep_fn=sleep_fn,
    ))
