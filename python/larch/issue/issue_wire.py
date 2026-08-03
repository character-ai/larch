# pyright: reportUnusedCallResult=false
"""Issue-body wire helpers for plan blocks, named blocks, titles, and untrusted text."""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from larch.git import gh
from larch.issue import issue_blocks
from larch.issue import issue_mutation
from larch.issue.issue_blocks import classify_named_block_lines, parse_named_block, strip_named_block
from larch.design import plan_grammar
from larch.core import config
from larch.core import logging_util
from larch.core import proc
from larch.core import redact
from larch.errors import ShipError
from larch.core.proc import Runner

_ALLOWED_MARKERS = {"plan", "design-pause"}
_MALFORMED_TOKENS = {
    "multiple-start",
    "multiple-end",
    "start-without-end",
    "end-without-start",
    "end-before-start",
}

# Byte-compatible with the legacy title-eligibility shell helper.
ARCHIVAL_JQ_FILTER = 'select((.title // "" | ascii_downcase | sub("^[[:space:]]+"; "")) as $t | (($t | startswith("research ")) or ($t | startswith("[research] ")) or ($t | startswith("investigate ")) or ($t | startswith("[investigate] ")) or ($t | test("^\\[.*report\\] "))) | not)'
ARCHIVAL_REPORT_RE = re.compile(r"^\[.*report\] ", re.IGNORECASE)
_LIFECYCLE_REJECT_STATES = (
    "IMPLEMENTING",
    "DONE",
    "DESIGNING",
    "DESIGNED",
    *config.DEBATE_TITLE_STATES,
)
LIFECYCLE_REJECT_RE = re.compile(
    rf"^\[({'|'.join(_LIFECYCLE_REJECT_STATES)})\]",
    re.IGNORECASE,
)
BRAINSTORM_RE = re.compile(r"^brainstorm([^A-Za-z]|$)", re.IGNORECASE)
_SCOPE_PATH_FALLBACK = ["skills/design/SKILL.md"]
_LIFECYCLE_INSERT_PREFIXES = (
    *config.DEBATE_TITLE_STATES,
    "DESIGNING",
    "DESIGNED",
    "IMPLEMENTING",
    "DONE",
    "STALLED",
    "IN PROGRESS",
    "PLANNED",
)
_OWNERS_START = "<!-- larch:owners:start -->"
_OWNERS_END = "<!-- larch:owners:end -->"
_OWNER_KEY_RE: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMAND_PART_RE: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SYMBOL_RE: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")
_ASCII_CONTROL_BOUND: Final = 32
_COMMAND_PARTS: Final = 3
_CREATE_PARTS: Final = 3
_REUSE_PARTS: Final = 4
_LEASE_RE: Final = re.compile(
    r"^<!-- larch:implementation-lease v1 "
    r"run_id=([A-Za-z0-9][A-Za-z0-9._-]{0,127}) "
    r"branch=([^\s]+) base=([0-9a-f]{40}) plan=([0-9a-f]{64}) "
    r"updated_at=(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) -->$"
)
_BRANCH_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


@dataclass(frozen=True)
class OwnerRow:
    """One canonical owner-block declaration."""

    kind: str
    owner_key: str
    target: str
    source_issue: int | None = None

    def render(self) -> str:
        if self.kind == "CREATE":
            return f"CREATE\t{self.owner_key}\t{self.target}"
        assert self.source_issue is not None
        return f"REUSE\t{self.owner_key}\t#{self.source_issue}\t{self.target}"


@dataclass(frozen=True)
class OwnerBlock:
    """Validated owner-block command identity and declarations."""

    domain: str
    verb: str
    owners: tuple[OwnerRow, ...]

    def rows(self) -> tuple[str, ...]:
        return (f"COMMAND\t{self.domain}\t{self.verb}", *(row.render() for row in self.owners))


@dataclass(frozen=True)
class OwnerBlockParse:
    """Fail-closed owner-block parse result."""

    block: OwnerBlock | None
    defects: tuple[str, ...]
    raw_rows: tuple[str, ...]


@dataclass(frozen=True)
class ImplementationLeaseMarker:
    """Issue-body identity for one active implementation run."""

    run_id: str
    branch: str
    base: str
    plan: str
    updated_at: str


def _unfenced_line_indexes(lines: list[str]) -> frozenset[int]:
    fenced = plan_grammar.balanced_fence_line_indices(lines)
    return frozenset(index for index in range(len(lines)) if index not in fenced)


def _safe_repo_target(value: str) -> bool:
    if value.count("::") > 1:
        return False
    path_text, separator, symbol = value.rpartition("::")
    candidate = path_text if separator else value
    if not candidate or candidate != candidate.strip() or "\\" in candidate:
        return False
    path = Path(candidate)
    if path.is_absolute() or candidate.startswith(("~", "./")):
        return False
    if any(part in {"", ".", ".."} for part in path.parts):
        return False
    if any(ord(char) < _ASCII_CONTROL_BOUND or char == "\x7f" for char in candidate):
        return False
    return not separator or _SYMBOL_RE.fullmatch(symbol) is not None


def _parse_owner_row(*, row: str, defects: list[str]) -> OwnerRow | None:
    parts = row.split("\t")
    if parts[0] == "COMMAND":
        return None
    if len(parts) == _CREATE_PARTS and parts[0] == "CREATE":
        _, key, target = parts
        source_issue = None
    elif len(parts) == _REUSE_PARTS and parts[0] == "REUSE" and re.fullmatch(r"#[1-9][0-9]*", parts[2]):
        _, key, source, target = parts
        source_issue = int(source[1:])
    else:
        defects.append("invalid-owner-row")
        return None
    if _OWNER_KEY_RE.fullmatch(key) is None:
        defects.append("invalid-owner-key")
    if not _safe_repo_target(target):
        defects.append("unsafe-owner-target")
    return OwnerRow(parts[0], key, target, source_issue)


def _owner_block_rows(*, lines: list[str]) -> tuple[tuple[str, ...] | None, str]:
    unfenced = _unfenced_line_indexes(lines)
    starts = [index for index, line in enumerate(lines) if index in unfenced and line == _OWNERS_START]
    ends = [index for index, line in enumerate(lines) if index in unfenced and line == _OWNERS_END]
    if not starts and not ends:
        return None, "absent"
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        return None, "malformed-owner-block"
    return tuple(lines[starts[0] + 1 : ends[0]]), ""


def _parse_owner_command(*, raw_rows: tuple[str, ...], defects: list[str]) -> tuple[str, str]:
    command_rows = [row for row in raw_rows if row.startswith("COMMAND\t")]
    if len(command_rows) != 1 or not raw_rows or raw_rows[0] not in command_rows:
        defects.append("invalid-owner-command")
        return "", ""
    command_parts = command_rows[0].split("\t")
    if len(command_parts) != _COMMAND_PARTS or _COMMAND_PART_RE.fullmatch(command_parts[1]) is None or _COMMAND_PART_RE.fullmatch(command_parts[2]) is None:
        defects.append("invalid-owner-command")
        return "", ""
    return command_parts[1], command_parts[2]


def _parse_owner_rows(*, raw_rows: tuple[str, ...], defects: list[str]) -> tuple[OwnerRow, ...]:
    owners = tuple(owner for row in raw_rows if (owner := _parse_owner_row(row=row, defects=defects)) is not None)
    if not owners:
        defects.append("missing-owner-row")
    if len({owner.owner_key for owner in owners}) != len(owners):
        defects.append("duplicate-owner-key")
    return owners


def parse_owner_block(*, body: str) -> OwnerBlockParse:
    """Parse and validate the sole unfenced canonical owner block."""
    lines = (body or "").splitlines()
    raw_rows, block_defect = _owner_block_rows(lines=lines)
    if block_defect == "absent":
        return OwnerBlockParse(block=None, defects=(), raw_rows=())
    if raw_rows is None:
        return OwnerBlockParse(block=None, defects=(block_defect,), raw_rows=())
    defects: list[str] = []
    if not raw_rows or any(not row for row in raw_rows):
        defects.append("invalid-owner-row")
    if len(set(raw_rows)) != len(raw_rows):
        defects.append("duplicate-owner-row")
    if tuple(sorted(raw_rows)) != raw_rows:
        defects.append("unsorted-owner-rows")
    domain, verb = _parse_owner_command(raw_rows=raw_rows, defects=defects)
    owners = _parse_owner_rows(raw_rows=raw_rows, defects=defects)
    unique_defects = tuple(dict.fromkeys(defects))
    if unique_defects:
        return OwnerBlockParse(block=None, defects=unique_defects, raw_rows=raw_rows)
    return OwnerBlockParse(
        block=OwnerBlock(domain=domain, verb=verb, owners=owners),
        defects=(),
        raw_rows=raw_rows,
    )


def render_owner_block(*, block: OwnerBlock) -> str:
    """Render a validated owner block with canonical sorted unique rows."""
    rows = block.rows()
    parsed = parse_owner_block(body="\n".join((_OWNERS_START, *rows, _OWNERS_END)))
    if parsed.block != block:
        raise ShipError("invalid-owner-block")
    return "\n".join((_OWNERS_START, *rows, _OWNERS_END)) + "\n"


def parse_implementation_lease(*, body: str) -> ImplementationLeaseMarker | None:
    """Return the sole unfenced implementation lease, or None."""
    lines = (body or "").splitlines()
    unfenced = _unfenced_line_indexes(lines)
    candidates = [
        line
        for index, line in enumerate(lines)
        if index in unfenced and line.startswith("<!-- larch:implementation-lease")
    ]
    if len(candidates) != 1:
        return None
    matches = [match for line in candidates if (match := _LEASE_RE.fullmatch(line))]
    if len(matches) != 1:
        return None
    match = matches[0]
    return ImplementationLeaseMarker(
        run_id=match.group(1), branch=match.group(2), base=match.group(3),
        plan=match.group(4), updated_at=match.group(5),
    )


def render_implementation_lease(*, lease: ImplementationLeaseMarker) -> str:
    """Render exact implementation-lease v1 bytes after field validation."""
    line = (
        "<!-- larch:implementation-lease v1 "
        f"run_id={lease.run_id} branch={lease.branch} base={lease.base} "
        f"plan={lease.plan} updated_at={lease.updated_at} -->"
    )
    branch_parts = lease.branch.split("/")
    branch_invalid = (
        _BRANCH_RE.fullmatch(lease.branch) is None
        or ".." in lease.branch
        or "@{" in lease.branch
        or "//" in lease.branch
        or any(not part or part.startswith(".") or part.endswith(".lock") for part in branch_parts)
    )
    if _LEASE_RE.fullmatch(line) is None or branch_invalid:
        raise ShipError("invalid-implementation-lease")
    try:
        datetime.strptime(lease.updated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ShipError("invalid-implementation-lease") from exc
    return line


def upsert_implementation_lease(*, body: str, lease: ImplementationLeaseMarker) -> str:
    """Append or replace the sole unfenced implementation lease."""
    rendered = render_implementation_lease(lease=lease)
    lines = body.splitlines(keepends=True)
    unfenced = _unfenced_line_indexes([line.rstrip("\r\n") for line in lines])
    malformed = [
        line
        for index, line in enumerate(lines)
        if index in unfenced
        and line.rstrip("\r\n").startswith("<!-- larch:implementation-lease")
        and _LEASE_RE.fullmatch(line.rstrip("\r\n")) is None
    ]
    if malformed:
        raise ShipError("malformed-implementation-lease")
    indexes = [
        index for index, line in enumerate(lines)
        if index in unfenced and _LEASE_RE.fullmatch(line.rstrip("\r\n")) is not None
    ]
    if len(indexes) > 1:
        raise ShipError("malformed-implementation-lease")
    if indexes:
        newline = "\r\n" if lines[indexes[0]].endswith("\r\n") else "\n"
        lines[indexes[0]] = rendered + newline
        return "".join(lines)
    separator = "" if not body or body.endswith(("\n", "\r")) else "\n"
    return f"{body}{separator}{rendered}\n"


def strip_implementation_lease(*, body: str) -> str:
    """Remove the sole unfenced implementation lease for CAS comparison."""
    lines = body.splitlines(keepends=True)
    unfenced = _unfenced_line_indexes([line.rstrip("\r\n") for line in lines])
    return "".join(
        line
        for index, line in enumerate(lines)
        if index not in unfenced
        or _LEASE_RE.fullmatch(line.rstrip("\r\n")) is None
    )


def named_block_marker_re(*, marker: str, kind: str) -> re.Pattern[str]:
    """Compatibility export for callers of the issue-body wire module."""
    return issue_blocks.named_block_marker_re(marker=marker, kind=kind)


class _DiagnosticArgumentParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: object | None = None) -> None:
        _ = file
        if message:
            logging_util.diagnostic(message)


def compose_named_block(*, marker: str, inner: str) -> str:
    stripped = inner.rstrip("\n")
    block = f"<!-- larch:{marker}:start -->\n"
    if stripped:
        block += stripped + "\n"
    return block + f"<!-- larch:{marker}:end -->\n"


def issue_plan_marker_defect(issue_body: str) -> str | None:
    """Return the M1 marker defect for an issue body, or None when exactly one block exists."""
    _inner, malformed = parse_named_block(body=issue_body, marker="plan")
    if malformed in {"multiple-start", "multiple-end"}:
        return "multiple-plan-blocks"
    if malformed or _inner is None:
        return "missing-plan-block"
    return None


def validate_issue_plan(
    *,
    issue_body: str,
    repo_root: Path,
    tracked_paths: frozenset[str] | None = None,
) -> plan_grammar.PlanValidationResult:
    """Validate issue-body markers plus the extracted executable plan contract."""
    marker_defect = issue_plan_marker_defect(issue_body)
    if marker_defect is not None:
        return plan_grammar.PlanValidationResult(defects=(marker_defect,))
    inner, _malformed = parse_named_block(body=issue_body, marker="plan")
    if inner is None:
        return plan_grammar.PlanValidationResult(defects=("missing-plan-block",))
    return plan_grammar.validate_plan_contract(
        plan_text=inner, repo_root=repo_root, tracked_paths=tracked_paths
    )


def neutralize_named_block_markers(*, text: str, marker: str) -> str:
    """Render named-block marker examples inert before embedding them in prose."""
    if marker not in _ALLOWED_MARKERS:
        msg = f"unsupported marker: {marker}"
        raise ValueError(msg)
    pattern = re.compile(
        rf"(^[ \t]*)<!--[ \t]+larch:{re.escape(marker)}:(?:start|end)[ \t]+-->[ \t]*$",
        re.MULTILINE,
    )
    return pattern.sub(lambda match: match.group(0).replace("<!--", "<!--\u200b", 1), text)


def _single_line_redacted(text: str) -> str:
    if not text:
        return ""
    redacted = redact.redact_secrets_only(text)
    if "[content truncated" in redacted:
        return "gh stderr redaction unavailable"
    return redacted.replace("\n", " ")[:500]


def _emit_failed(error: str) -> None:
    logging_util.emit_kv(key="FAILED", value="true")
    logging_util.emit_kv(key="ERROR", value=error)


def _resolve_issue_wire_repo(*, runner: Runner, explicit: str | None) -> tuple[str | None, str]:
    if explicit:
        return explicit, ""
    try:
        repo = gh.resolve_repo(runner)
    except ShipError:
        return None, "could not determine repo"
    if not repo:
        return None, "could not determine repo"
    return repo, ""


def _validate_positive_issue(*, prog: str, issue: str) -> bool:
    if not issue.isdecimal() or issue == "0":
        logging_util.diagnostic(f"{prog}: --issue must be a positive integer")
        return False
    return True


def _bool_str(value: object) -> str:
    return "true" if value else "false"


def _reject_empty_plan_content(*, marker: str, content: str) -> None:
    if marker == "plan" and not content.strip():
        raise ShipError("empty-plan-content")


def _verify_named_block_post_write(
    *,
    runner: Runner,
    marker: str,
    issue: str,
    repo: str,
    delete: bool,
) -> None:
    """Re-read the issue body and require a parseable unfenced named block.

    Fenced marker examples (decompose/split placeholders) are ignored by
    ``parse_named_block``, matching /implement preflight. A write that leaves
    only fenced markers must fail closed so /design cannot report success when
    /implement would still see ``BLOCK_PRESENT=false`` (#7402, #7212).
    """
    if delete:
        return
    verified_body = gh.issue_view_body(runner, issue, repo=repo)
    inner, malformed = parse_named_block(body=verified_body, marker=marker)
    if malformed:
        raise ShipError(f"post-write-verify-malformed:{malformed}")
    if inner is None:
        raise ShipError("post-write-verify-missing")
    if marker == "plan" and not inner.strip():
        raise ShipError("post-write-verify-empty")


def named_block_lease(*, marker: str) -> issue_mutation.ImplementationLease | None:
    """Build a named-block lease from the active or rehydrated run identity."""
    run_id = (
        os.environ.get("RUN_ID", "").strip()
        or os.environ.get(config.ENV_LARCH_RUN_ID, "").strip()
        or os.environ.get(config.ENV_SESSION_ID, "").strip()
    )
    return (
        issue_mutation.ImplementationLease(run_id=run_id, marker=marker)
        if run_id
        else None
    )


def named_block_write(
    *, runner: Runner,
    marker: str,
    issue: str,
    repo: str,
    content: str | None,
    delete: bool,
) -> dict[str, object]:
    if marker not in _ALLOWED_MARKERS:
        msg = f"unsupported marker: {marker}"
        raise ValueError(msg)
    current_body = gh.issue_view_body(runner, issue, repo=repo).rstrip("\n")
    _, malformed = parse_named_block(body=current_body, marker=marker)
    if malformed:
        return {"malformed": malformed}

    markers_present = parse_named_block(body=current_body, marker=marker)[0] is not None
    if delete:
        if markers_present:
            composed, strip_malformed = strip_named_block(body=current_body, marker=marker)
            if strip_malformed:
                return {"malformed": strip_malformed}
            mode = "removed"
        else:
            composed = current_body
            mode = "absent-noop"
    else:
        if content is None:
            msg = "content is required unless delete is true"
            raise ValueError(msg)
        _reject_empty_plan_content(marker=marker, content=content)
        block = compose_named_block(marker=marker, inner=content)
        if markers_present:
            _stripped, strip_malformed = strip_named_block(body=current_body, marker=marker)
            if strip_malformed:
                return {"malformed": strip_malformed}
            lines = current_body.splitlines(keepends=True)
            span = classify_named_block_lines(lines=lines, marker=marker)
            assert span.start is not None
            assert span.end is not None
            composed = "".join([*lines[: span.start], block, *lines[span.end + 1 :]])
            mode = "replaced"
        else:
            composed = block if not current_body else current_body + "\n\n" + block
            mode = "appended"

    if mode == "absent-noop":
        return {
            "written": False,
            "mode": mode,
            "markers_present": markers_present,
            "body_bytes": len(current_body.encode("utf-8")),
        }

    try:
        redacted_body = redact.redact_secrets_only(composed)
    except Exception as exc:  # pragma: no cover - defensive seam for monkeypatch tests
        msg = f"redaction:{exc}"
        raise ShipError(msg) from exc
    _ = issue_mutation.update_named_block(
        runner,
        repository=repo,
        issue=issue,
        marker=marker,
        body=redacted_body,
        lease=named_block_lease(marker=marker),
    )
    _verify_named_block_post_write(
        runner=runner, marker=marker, issue=issue, repo=repo, delete=delete,
    )
    return {
        "written": True,
        "mode": mode,
        "markers_present": markers_present,
        "body_bytes": len(redacted_body.encode("utf-8")),
    }


def _content_file_text(path: str) -> tuple[str | None, str]:
    p = Path(path)
    if not p.is_file():
        return None, f"content file not found: {path}"
    return p.read_text(encoding="utf-8", errors="replace"), ""


def _named_block_arg_parser(*, prog: str, include_marker: bool) -> argparse.ArgumentParser:
    parser = _DiagnosticArgumentParser(prog=prog, add_help=True)
    if include_marker:
        parser.add_argument("--marker", required=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--content-file")
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--repo")
    return parser


def _run_named_block_cli(*, argv: list[str], prog: str, marker_default: str | None) -> int:
    logging_util.quiet_init(argv0=prog)
    parser = _named_block_arg_parser(prog=prog, include_marker=marker_default is None)
    args = parser.parse_args(argv)
    marker = marker_default or args.marker
    if marker not in _ALLOWED_MARKERS:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", marker or ""):
            logging_util.diagnostic(f"{prog}: --marker must match ^[a-z0-9][a-z0-9-]*$")
            return 1
        logging_util.diagnostic(f"{prog}: unsupported marker: {marker}")
        return 1
    if not _validate_positive_issue(prog=prog, issue=args.issue):
        return 1
    if args.delete and args.content_file:
        logging_util.diagnostic(f"{prog}: --delete and --content-file are mutually exclusive")
        return 1
    if not args.delete and not args.content_file:
        parser.print_usage()
        return 1
    content = None
    if args.content_file:
        content, content_error = _content_file_text(args.content_file)
        if content_error:
            _emit_failed(content_error)
            return 1
    if args.repo and not gh.validate_repo_slug(args.repo):
        _emit_failed("invalid-repo")
        return 1
    runner: Runner = proc
    repo, repo_error = _resolve_issue_wire_repo(runner=runner, explicit=args.repo)
    if repo_error or repo is None:
        _emit_failed(repo_error or "could not determine repo")
        return 2
    if not gh.validate_repo_slug(repo):
        _emit_failed("invalid-repo")
        return 1
    try:
        result = named_block_write(runner=runner, marker=marker, issue=args.issue, repo=repo, content=content, delete=args.delete)
    except ShipError as exc:
        message = str(exc)
        if message.startswith("redaction:"):
            _emit_failed(message)
            return 3
        _emit_failed(_single_line_redacted(message))
        return 2
    malformed = result.get("malformed")
    if isinstance(malformed, str) and malformed:
        logging_util.emit_kv(key="MALFORMED", value=malformed)
        return 1
    logging_util.emit_kv(key="WRITTEN", value="true")
    logging_util.emit_kv(key="MODE", value=str(result["mode"]))
    logging_util.emit_kv(key="MARKERS_PRESENT", value=_bool_str(bool(result["markers_present"])))
    logging_util.emit_kv(key="BODY_BYTES", value=str(result["body_bytes"]))
    return 0


def named_block_write_main(argv: list[str]) -> int:
    return _run_named_block_cli(argv=argv, prog="named-block-write.sh", marker_default=None)


def plan_block_write_main(argv: list[str]) -> int:
    return _run_named_block_cli(argv=argv, prog="plan-block-write.sh", marker_default="plan")


def plan_block_read_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="plan-block-read.sh")
    parser = _DiagnosticArgumentParser(prog="plan-block-read.sh", add_help=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo")
    args = parser.parse_args(argv)
    if not _validate_positive_issue(prog="plan-block-read.sh", issue=args.issue):
        return 1
    out_path = Path(args.output)
    runner: Runner = proc
    repo, repo_error = _resolve_issue_wire_repo(runner=runner, explicit=args.repo)
    if repo_error or repo is None:
        out_path.write_text("", encoding="utf-8")
        _emit_failed(repo_error or "could not determine repo")
        return 2
    try:
        body = gh.issue_view_body(runner, args.issue, repo=repo)
    except ShipError as exc:
        out_path.write_text("", encoding="utf-8")
        _emit_failed(_single_line_redacted(str(exc)))
        return 2
    inner, malformed = parse_named_block(body=body, marker="plan")
    if malformed:
        out_path.write_text("", encoding="utf-8")
        logging_util.emit_kv(key="MALFORMED", value=malformed)
        return 1
    if inner is None:
        out_path.write_text("", encoding="utf-8")
        logging_util.emit_kv(key="BLOCK_PRESENT", value="false")
        return 0
    out_path.write_text(inner, encoding="utf-8")
    logging_util.emit_kv(key="BLOCK_PRESENT", value="true")
    logging_util.emit_kv(key="OUTPUT", value=args.output)
    return 0


def plan_block_strip_body_main(argv: list[str]) -> int:
    parser = _DiagnosticArgumentParser(prog="plan-block-strip-body.sh", add_help=True)
    parser.add_argument("--file")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        body = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
    except OSError as exc:
        logging_util.diagnostic(f"plan-block-strip-body.sh: {exc}")
        return 1
    stripped, malformed = strip_named_block(body=body, marker="plan")
    if malformed:
        if args.output:
            Path(args.output).write_text("", encoding="utf-8")
        logging_util.quiet_init(argv0="plan-block-strip-body.sh")
        logging_util.emit_kv(key="MALFORMED", value=malformed)
        return 1
    if args.output:
        Path(args.output).write_text(stripped, encoding="utf-8")
    else:
        sys.stdout.write(stripped)
    return 0


def extract_scope_paths(*, plan_text: str, use_fallback: bool = True, include_optional: bool = True) -> list[str]:
    events = list(plan_grammar.iter_heading_events(plan_text))
    has_scope_section = any(
        event.generic_level_two and re.match(r"^##\s+Files to modify(?:/create)?\s*$", event.text)
        for event in events
    )
    in_section = not has_scope_section
    seen: list[str] = []
    for event in events:
        line = event.text
        if re.match(r"^##\s+Files to modify(?:/create)?\s*$", line):
            in_section = True
            continue
        heading = event.heading
        if in_section and heading is not None:
            if heading.kind == "MAY_UPDATE" and not include_optional:
                continue
            tail = heading.path
            backtick_matches = list(re.finditer(r"`([^`]+)`", tail))
            candidates = [match.group(1).strip() for match in backtick_matches]
            if not candidates:
                parts = tail.split()
                candidates = [re.sub(r"\(.*$", "", parts[0]).strip()] if parts else []
            for path in candidates:
                if path and not path.startswith("+") and path not in seen:
                    seen.append(path)
            continue
        if has_scope_section and in_section and event.generic_level_two:
            break
    if seen:
        return seen
    if use_fallback:
        return list(_SCOPE_PATH_FALLBACK)
    return []


def plan_scope_paths_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="extract-plan-scope-paths.sh", add_help=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("-z", "--null", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if int(exc.code or 0) != 0 else 0
    path = Path(args.plan_file)
    if not path.is_file():
        print(f"extract-plan-scope-paths.sh: plan file not found: {args.plan_file}", file=sys.stderr)
        return 2
    try:
        paths = extract_scope_paths(plan_text=path.read_text(encoding="utf-8", errors="replace"))
    except OSError as exc:
        print(f"extract-plan-scope-paths.sh: {exc}", file=sys.stderr)
        return 2
    sep = "\0" if args.null else "\n"
    sys.stdout.write(sep.join(paths))
    if paths:
        sys.stdout.write(sep)
    return 0


def _trim_leading_ws(title: str) -> str:
    return title.lstrip()


def title_lifecycle_reject_marker(title: str) -> str | None:
    match = LIFECYCLE_REJECT_RE.match(_trim_leading_ws(title))
    if match is None:
        return None
    return f"[{match.group(1).upper()}]"


def title_has_archival_report_prefix(title: str) -> bool:
    return ARCHIVAL_REPORT_RE.match(_trim_leading_ws(title)) is not None


def title_starts_with_brainstorm(title: str) -> bool:
    return BRAINSTORM_RE.match(_trim_leading_ws(title)) is not None


def insert_signal_marker(*, title: str, marker: str) -> str:
    marker_block = f"[{marker}]"
    if not title:
        return marker_block
    rest = title
    while rest.startswith("["):
        close_space = rest.find("] ")
        if close_space < 0:
            break
        block = rest[: close_space + 1]
        if block == marker_block:
            return title
        rest = rest[close_space + 2 :]
    for prefix in _LIFECYCLE_INSERT_PREFIXES:
        block = f"[{prefix}] "
        if title[: len(block)].casefold() == block.casefold():
            # Preserve the title's original lifecycle-prefix spelling.
            return f"{title[: len(block) - 1]} [{marker}] {title[len(block) :]}"
    return f"[{marker}] {title}"


def _parse_title_marker_args(*, argv: list[str], want_marker: bool = False) -> tuple[str | None, str | None, int]:
    title: str | None = None
    marker: str | None = None
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--title":
            if idx + 1 >= len(argv):
                print("issue title: --title requires a value", file=sys.stderr)
                return None, None, 2
            title = argv[idx + 1]
            idx += 2
        elif arg.startswith("--title="):
            title = arg.split("=", 1)[1]
            idx += 1
        elif want_marker and arg == "--marker":
            if idx + 1 >= len(argv):
                print("issue title: --marker requires a value", file=sys.stderr)
                return None, None, 2
            marker = argv[idx + 1]
            idx += 2
        elif want_marker and arg.startswith("--marker="):
            marker = arg.split("=", 1)[1]
            idx += 1
        else:
            print(f"issue title: unknown option: {arg}", file=sys.stderr)
            return None, None, 2
    if title is None:
        print("issue title: --title is required", file=sys.stderr)
        return None, None, 2
    if want_marker and marker is None:
        print("issue title: --marker is required", file=sys.stderr)
        return None, None, 2
    return title, marker, 0


def issue_title_eligibility_main(argv: list[str]) -> int:
    title, _, rc = _parse_title_marker_args(argv=argv)
    if rc:
        return rc
    assert title is not None
    marker = title_lifecycle_reject_marker(title)
    print(f"LIFECYCLE_REJECT={_bool_str(marker is not None)}")
    if marker is not None:
        print(f"LIFECYCLE_MARKER={marker}")
    print(f"ARCHIVAL_REPORT={_bool_str(title_has_archival_report_prefix(title))}")
    print(f"BRAINSTORM={_bool_str(title_starts_with_brainstorm(title))}")
    return 0


def issue_title_archival_jq_main(argv: list[str]) -> int:
    if argv:
        print(f"issue title-archival-jq: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    print(ARCHIVAL_JQ_FILTER)
    return 0


def issue_insert_signal_marker_main(argv: list[str]) -> int:
    title, marker, rc = _parse_title_marker_args(argv=argv, want_marker=True)
    if rc:
        return rc
    assert title is not None
    assert marker is not None
    print(insert_signal_marker(title=title, marker=marker), end="")
    return 0


def xml_escape_attr(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def redact_untrusted_stream(text: str) -> str:
    return html.escape(redact.redact(text), quote=False)


def emit_untrusted_file_block(*, tag: str, path: Path) -> str:
    return f'<{tag} encoding="literal-redacted">\n{redact_untrusted_stream(path.read_text(encoding="utf-8", errors="replace"))}\n</{tag}>\n\n'


def emit_untrusted_content_block(*, tag: str, text: str) -> str:
    return f'<{tag} encoding="literal-redacted">\n{redact_untrusted_stream(text)}\n</{tag}>\n\n'


def untrusted_xml_escape_attr_main(argv: list[str]) -> int:
    if argv:
        print(f"untrusted xml-escape-attr: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    sys.stdout.write(xml_escape_attr(sys.stdin.read()))
    return 0


def untrusted_redact_stream_main(argv: list[str]) -> int:
    if argv:
        print(f"untrusted redact-stream: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    sys.stdout.write(redact_untrusted_stream(sys.stdin.read()))
    return 0


def untrusted_file_block_main(argv: list[str]) -> int:
    expected_arg_count = 2
    if len(argv) != expected_arg_count:
        print("untrusted file-block: usage: untrusted file-block TAG PATH", file=sys.stderr)
        return 2
    sys.stdout.write(emit_untrusted_file_block(tag=argv[0], path=Path(argv[1])))
    return 0


def untrusted_content_block_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="untrusted content-block", add_help=True)
    parser.add_argument("tag")
    parser.add_argument("--text")
    args = parser.parse_args(argv)
    text = args.text if args.text is not None else sys.stdin.read()
    sys.stdout.write(emit_untrusted_content_block(tag=args.tag, text=text))
    return 0
