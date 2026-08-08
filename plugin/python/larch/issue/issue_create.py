# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Python entrypoints for /issue helper surfaces.

`issue parse-input`, `issue allocate-candidates`, `issue list-issues`, and
`issue fetch-issue-details` moved to the Rust owner in #8168. `parse_issue_input`
stays because it is not that command: it is the in-process grammar
``larch.issue.file_oos``, ``larch.issue.umbrella``, and
``larch.issue.learn_from_bugs`` still call directly, and those modules migrate
with their own command leaves.
"""

from __future__ import annotations

import datetime as _dt
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
URL_RE = re.compile(r"https?://[^\s]+/issues/[0-9]+")


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
class CreateIssueResult:
    """The durable outcome of one GitHub issue creation request."""

    title: str = ""
    number: str = ""
    url: str = ""
    issue_id: str = ""
    error: str = ""
    duplicate: bool = False
    labels: tuple[str, ...] = ()
    dry_run: bool = False
    exit_code: int = 0


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


@dataclass(frozen=True)
class CleanupResult:
    """The best-effort outcome of closing an orphaned issue."""

    issue: str
    closed: bool
    error: str = ""


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


def _parse_create_args(argv: list[str]) -> tuple[dict[str, object], str | None]:
    args: dict[str, object] = {"labels": []}
    index = 0
    while index < len(argv):
        arg = argv[index]
        needs_value = {"--title", "--title-prefix", "--label", "--body", "--body-file", "--repo", "--context-file", "--run-id", "--trusted-root"}
        if arg in needs_value:
            if index + 1 >= len(argv):
                return args, f"{arg} requires a value"
            value = argv[index + 1]
            if arg == "--title":
                args["title"] = value
            elif arg == "--title-prefix":
                args["title_prefix"] = value
            elif arg == "--label":
                labels = args["labels"]
                assert isinstance(labels, list)
                labels.append(value)
            elif arg in {"--body", "--body-file"}:
                args["body_file"] = value
            elif arg == "--repo":
                args["repo"] = value
            elif arg == "--context-file":
                args["context_file"] = value
            elif arg == "--run-id":
                args["run_id"] = value
            elif arg == "--trusted-root":
                args["trusted_root"] = value
            index += 2
        elif arg == "--dry-run":
            args["dry_run"] = True
            index += 1
        elif arg == "--operator-invoked":
            args["operator_invoked"] = True
            index += 1
        else:
            return args, f"Unknown option: {arg}"
    return args, None


def _resolve_repo() -> str:
    return gh.resolve_repo(proc) or ""


def _valid_labels(repo: str, labels: list[str], *, dry_run: bool) -> list[str]:
    valid: list[str] = []
    for label in labels:
        if not repo and dry_run:
            valid.append(label)
            continue
        result = _gh_read(
            ["label", "list", "--repo", repo, "--search", label, "--json", "name", "--jq", ".[].name"],
        )
        if result.returncode == 0 and label in result.stdout.splitlines():
            valid.append(label)
        else:
            warn(f"WARN: label '{label}' does not exist in {repo}, skipping")
    return valid


def _normalize_title_prefix(*, title: str, title_prefix: str) -> str:
    if not title_prefix:
        return title
    stripped = title
    if stripped.lower().startswith(title_prefix.lower()):
        stripped = stripped[len(title_prefix) :].lstrip()
    return f"{title_prefix} {stripped}"


def _is_oos_issue_body(body_content: str) -> bool:
    heading = "## Out-of-Scope Observation"
    return body_content == heading or body_content.startswith(f"{heading}\n")


def _issue_failed(message: str, *, code: int = 2, title: str = "") -> CreateIssueResult:
    try:
        error = _flat_error(text=message)
    except Exception as exc:  # pragma: no cover - defensive seam for redaction failures
        error = f"redaction:{exc}"
    return CreateIssueResult(title=title, error=error, exit_code=code)


def _create_one_body_content(parsed: dict[str, object]) -> tuple[str, CreateIssueResult | None]:
    body_file = str(parsed.get("body_file") or "")
    if not body_file:
        return "", None
    path = Path(body_file)
    if not path.is_file():
        return "", _issue_failed(f"body file not found: {body_file}", code=1)
    body_content = path.read_text(encoding="utf-8")
    if not body_content:
        return "", None
    try:
        redacted_body = redact_secrets_outbound(body_content)
    except Exception as exc:  # pragma: no cover - defensive seam for tests
        return "", _issue_failed(f"redaction:{exc}", code=3)
    return redacted_body, None


def _parse_issue_json(output: str) -> tuple[str, str, str] | None:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None
    number = str(data.get("number") or "")
    url = str(data.get("url") or "")
    issue_id = str(data.get("id") or "")
    if not number or not url or not issue_id:
        return None
    if not number.isdigit() or not _positive_int(value=issue_id):
        return None
    return number, url, issue_id


def _issue_create_json_status(output: str) -> str:
    try:
        data: object = json.loads(output)
    except json.JSONDecodeError:
        return "fallback"
    if not isinstance(data, dict) or not all(key in data for key in ("number", "url", "id")):
        return "fallback"
    if _parse_issue_json(output) is not None:
        return "ok"
    number = str(data.get("number") or "")
    url = str(data.get("url") or "")
    issue_id = str(data.get("id") or "")
    if not number or not url or not issue_id:
        return "empty_fields"
    if number.isdigit() and url:
        return "resolve_id"
    return "empty_fields"


def _parse_created_url(output: str) -> tuple[str, str] | None:
    match = URL_RE.search(output)
    if not match:
        return None
    url = match.group(0)
    number = url.rsplit("/", 1)[-1]
    if not number.isdigit():
        return None
    return number, url


def _rollback_orphan(repo: str, number: str, url: str, *, close_error: str = "") -> None:
    close = gh.issue_close(proc, number, repo=repo, reason="not planned")
    if close.returncode == 0:
        warn(f"ROLLBACK: closed orphan issue #{number} after id-lookup failure")
        return
    detail = _flat_error(text=close_error or close.stderr or close.stdout)
    warn(f"ROLLBACK_FAILED: could not close orphan issue #{number} ({url}): {detail}. Manually close.")


def _resolve_created_issue_id(*, repo: str, number: str, url: str, final_title: str) -> CreateIssueResult:
    lookup = _gh_read(["api", f"/repos/{repo}/issues/{number}", "--jq", ".id"])
    issue_id = lookup.stdout.strip()
    if lookup.returncode == 0 and _positive_int(value=issue_id):
        return CreateIssueResult(title=final_title, number=number, url=url, issue_id=issue_id)
    if lookup.returncode == 0 and issue_id and not _positive_int(value=issue_id):
        _rollback_orphan(repo, number, url, close_error=lookup.stderr)
        return _issue_failed(f"id-lookup returned non-numeric id for #{number} (output: {_flat_error(text=lookup.stderr or issue_id)})", title=final_title)
    _rollback_orphan(repo, number, url, close_error=lookup.stderr)
    return _issue_failed(f"id-lookup failed for #{number} after create: {_flat_error(text=lookup.stderr)}", title=final_title)


def _resolve_created_from_output(*, repo: str, output: str, final_title: str) -> CreateIssueResult:
    parsed = _parse_created_url(output)
    if not parsed:
        return _issue_failed(f"gh issue create did not emit a URL (output: {_flat_error(text=output)})", title=final_title)
    number, url = parsed
    lookup = _gh_read(["api", f"/repos/{repo}/issues/{number}", "--jq", ".id"])
    issue_id = lookup.stdout.strip()
    if lookup.returncode == 0 and _positive_int(value=issue_id):
        return CreateIssueResult(title=final_title, number=number, url=url, issue_id=issue_id)
    if lookup.returncode == 0 and issue_id and not _positive_int(value=issue_id):
        _rollback_orphan(repo, number, url, close_error=lookup.stderr)
        return _issue_failed(f"id-lookup returned non-numeric id for #{number} (output: {_flat_error(text=lookup.stderr or issue_id)})", title=final_title)
    _rollback_orphan(repo, number, url, close_error=lookup.stderr)
    return _issue_failed(f"id-lookup failed for #{number} after create: {_flat_error(text=lookup.stderr)}", title=final_title)


def _create_fallback(*, repo: str, gh_args: list[str], final_title: str) -> CreateIssueResult:
    created = gh.command(proc, gh_args)
    if created.returncode != 0:
        return _issue_failed(_flat_error(text=created.stderr), title=final_title)
    return _resolve_created_from_output(repo=repo, output=created.stdout, final_title=final_title)


def create_one(parsed: dict[str, object]) -> CreateIssueResult:
    """Create one issue through the typed in-process API."""
    title = str(parsed.get("title") or "")
    if not title:
        return _issue_failed("--title is required", code=1)
    try:
        title = redact_secrets_outbound(title)
    except Exception as exc:  # pragma: no cover - defensive seam for tests
        return _issue_failed(f"redaction:{exc}", code=3)
    dry_run = bool(parsed.get("dry_run"))
    title_prefix = str(parsed.get("title_prefix") or "")
    final_title = _normalize_title_prefix(title=title, title_prefix=title_prefix)
    labels_obj = parsed.get("labels")
    labels = tuple(str(label) for label in labels_obj) if isinstance(labels_obj, list) else ()
    if dry_run:
        return CreateIssueResult(title=final_title, labels=labels, dry_run=True)
    body_content, body_error = _create_one_body_content(parsed)
    if body_error is not None:
        return body_error
    if not title_prefix and _is_oos_issue_body(body_content):
        final_title = _normalize_title_prefix(title=title, title_prefix="[OOS]")
    context_file_str = str(parsed.get("context_file") or "")
    operator_invoked = bool(parsed.get("operator_invoked"))
    if not dry_run:
        ctx = Path(context_file_str) if context_file_str else None
        authorized, auth_reason = _session_env.check_live_mutation_auth(
            context_file=ctx,
            operator_mode=operator_invoked,
            run_id=str(parsed.get("run_id") or ""),
            trusted_root=Path(str(parsed["trusted_root"])) if parsed.get("trusted_root") else None,
        )
        if not authorized:
            return _issue_failed(
                f"{config.LIVE_MUTATION_REFUSAL_REASON}:{auth_reason}",
                code=config.EXIT_MUTATION_REFUSED,
                title=final_title,
            )
    repo = str(parsed.get("repo") or "")
    if not repo:
        repo = _resolve_repo()
        if not repo and not dry_run:
            return _issue_failed("could not determine repo", title=final_title)
    valid_labels = _valid_labels(repo, list(labels), dry_run=dry_run)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=tempfile.gettempdir(), delete=False) as body_tmp:
        body_tmp.write(body_content)
        body_tmp_path = body_tmp.name
    try:
        gh_args = ["issue", "create", "--repo", repo, "--title", final_title, "--body-file", body_tmp_path]
        for label in valid_labels:
            gh_args.extend(["--label", label])
        result = gh.command(proc, [*gh_args, "--json", "id,number,url"])
        unknown_json = bool(re.search(r"unknown flag|unknown option|flag provided but not defined", result.stderr, re.IGNORECASE)) and "--json" in result.stderr
        if result.returncode == 0:
            json_status = _issue_create_json_status(result.stdout)
            if json_status == "ok":
                number, url, issue_id = _parse_issue_json(result.stdout) or ("", "", "")
                return CreateIssueResult(title=final_title, number=number, url=url, issue_id=issue_id, labels=tuple(valid_labels))
            if json_status == "resolve_id":
                data = json.loads(result.stdout)
                return _resolve_created_issue_id(
                    repo=repo,
                    number=str(data.get("number") or ""),
                    url=str(data.get("url") or ""),
                    final_title=final_title,
                )
            if json_status == "empty_fields":
                redacted_output = _flat_error(text=result.stdout)
                return _issue_failed(f"gh issue create returned JSON with empty field(s) (output: {redacted_output})", title=final_title)
            return _resolve_created_from_output(repo=repo, output=result.stdout, final_title=final_title)
        if unknown_json:
            return _create_fallback(repo=repo, gh_args=gh_args, final_title=final_title)
        return _issue_failed(_flat_error(text=result.stderr), title=final_title)
    finally:
        Path(body_tmp_path).unlink(missing_ok=True)


def emit_create_issue_result(result: CreateIssueResult) -> int:
    """Emit the stable CLI KV contract for :func:`create_one`."""
    if result.exit_code:
        if result.exit_code == config.EXIT_MUTATION_REFUSED:
            logging_util.emit_kv(key=config.LIVE_MUTATION_REFUSAL_STATUS, value="true")
        logging_util.emit_kv(key="ISSUE_FAILED", value="true")
        logging_util.emit_kv(key="ISSUE_ERROR", value=logging_util.sanitize_diagnostic_line(result.error))
        return result.exit_code
    if result.dry_run:
        logging_util.emit_kv(key="DRY_RUN", value="true")
        logging_util.emit_kv(key="DRY_RUN_TITLE", value=result.title)
        logging_util.emit_kv(key="ISSUE_TITLE", value=result.title)
        if result.labels:
            logging_util.emit_kv(key="DRY_RUN_LABELS", value=",".join(result.labels))
        return 0
    logging_util.emit_kv(key="ISSUE_NUMBER", value=result.number)
    logging_util.emit_kv(key="ISSUE_URL", value=result.url)
    logging_util.emit_kv(key="ISSUE_ID", value=result.issue_id)
    logging_util.emit_kv(key="ISSUE_TITLE", value=result.title)
    return 0


def create_one_main(argv: list[str]) -> int:
    parsed, error = _parse_create_args(argv)
    if error:
        warn(error)
        return 1
    return emit_create_issue_result(create_one(parsed))


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


def write_sentinel_main(argv: list[str]) -> int:
    values: dict[str, str] = {}
    dry_run = False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in {"--path", "--issues-created", "--issues-deduplicated", "--issues-failed"}:
            if index + 1 >= len(argv) or not argv[index + 1]:
                logging_util.emit_kv(key="ERROR", value=logging_util.sanitize_diagnostic_line(f"Missing value for {arg}"), stream=sys.stderr)
                return 1
            values[arg] = argv[index + 1]
            index += 2
        elif arg == "--dry-run":
            dry_run = True
            index += 1
        else:
            logging_util.emit_kv(key="ERROR", value=logging_util.sanitize_diagnostic_line(f"Unknown argument: {arg}"), stream=sys.stderr)
            return 1
    path = values.get("--path", "")
    if not path:
        logging_util.emit_kv(key="ERROR", value="Missing required argument: --path", stream=sys.stderr)
        return 1
    counts = [values.get("--issues-created", ""), values.get("--issues-deduplicated", ""), values.get("--issues-failed", "")]
    if any(not value for value in counts):
        logging_util.emit_kv(key="ERROR", value="Missing required arguments: --issues-created, --issues-deduplicated, --issues-failed", stream=sys.stderr)
        return 1
    if not Path(path).is_absolute():
        logging_util.emit_kv(key="ERROR", value=logging_util.sanitize_diagnostic_line(f"--path must be absolute: {path}"), stream=sys.stderr)
        return 1
    if ".." in Path(path).parts:
        logging_util.emit_kv(key="ERROR", value=logging_util.sanitize_diagnostic_line(f"--path must not contain '..': {path}"), stream=sys.stderr)
        return 1
    if any(not value.isdigit() for value in counts):
        logging_util.emit_kv(key="ERROR", value="Counter values must be non-negative integers", stream=sys.stderr)
        return 1
    if dry_run:
        print("WROTE=false REASON=dry_run", file=sys.stderr)
        return 0
    if int(values["--issues-failed"]) > 0:
        print("WROTE=false REASON=failures", file=sys.stderr)
        return 0
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(target.parent), prefix=f"{target.name}.tmp.", delete=False) as tmp:
        tmp.write("ISSUE_SENTINEL_VERSION=1\n")
        tmp.write(f"ISSUES_CREATED={values['--issues-created']}\n")
        tmp.write(f"ISSUES_DEDUPLICATED={values['--issues-deduplicated']}\n")
        tmp.write(f"ISSUES_FAILED={values['--issues-failed']}\n")
        tmp.write(f"TIMESTAMP={timestamp}\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)
    print("WROTE=true", file=sys.stderr)
    return 0


def cleanup_failed(*, issue: str, repo: str = "") -> CleanupResult:
    """Best-effort cleanup used after a partially-created OOS batch."""
    if not issue.isdigit():
        return CleanupResult(issue=issue, closed=False, error="invalid or missing --issue-number")
    if not repo:
        repo = _resolve_repo()
        if not repo:
            return CleanupResult(issue=issue, closed=False, error="could not determine repo")
    result = gh.issue_close(proc, issue, repo=repo, reason="not planned")
    if result.returncode == 0:
        return CleanupResult(issue=issue, closed=True)
    return CleanupResult(issue=issue, closed=False, error=_flat_error(text=result.stderr))


def emit_cleanup_result(result: CleanupResult) -> int:
    """Emit the stable CLI KV contract for :func:`cleanup_failed`."""
    logging_util.emit_kv(key="CLOSED", value=result.closed)
    logging_util.emit_kv(key="ISSUE", value=result.issue)
    if result.error:
        logging_util.emit_kv(key="ERROR", value=logging_util.sanitize_diagnostic_line(result.error))
    return 0


def cleanup_failed_main(argv: list[str]) -> int:
    issue = ""
    repo = ""
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--issue-number" and index + 1 < len(argv):
            issue = argv[index + 1]
            index += 2
        elif arg == "--repo" and index + 1 < len(argv):
            repo = argv[index + 1]
            index += 2
        else:
            warn(f"Unknown option: {arg}")
            return emit_cleanup_result(CleanupResult(issue=issue or "unknown", closed=False, error=f"unknown option: {arg}"))
    return emit_cleanup_result(cleanup_failed(issue=issue, repo=repo))
