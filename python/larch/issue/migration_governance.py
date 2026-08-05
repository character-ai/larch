"""Plan blocker parity and base-scope freshness receipts (M4/M5).

Owns canonical blocker-field parsing, native parity, receipt grammar, hashes,
and freshness verdicts. Callers share one verifier and one input canonicalization.
"""
# pylint: disable=cyclic-import  # accepted: persist_plan_receipt mutates via issue_mutation; plan CAS strips receipts via this module (both function-level).

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import sys
import tempfile
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

from larch import io as larch_io
from larch.core import config, proc, redact, repo_roots
from larch.core.proc import CommandResult, Runner
from larch.design import plan_grammar
from larch.errors import ShipError
from larch.git import gh, git
from larch.issue import issue_block, issue_blocks, issue_wire, open_rows
from larch.issue.issue_blocks import parse_named_block

_CODE_FENCE_RE: Final = re.compile(r"^\s*(?:```|~~~)")
_NATIVE_BLOCKER_LINE_RE: Final = re.compile(
    r"^[ \t]*Native blockers?:[ \t]+(.+?)[ \t]*$"
)
_ISSUE_REF_RE: Final = re.compile(r"#([1-9][0-9]*)")
_RECEIPT_RE: Final = re.compile(
    r"^[ \t]*<!--[ \t]+larch:plan-receipt[ \t]+v1[ \t]+"
    r"plan_sha256=([0-9a-f]{64})[ \t]+"
    r"base_sha=([0-9a-f]{40})[ \t]+"
    r"blockers_sha256=([0-9a-f]{64})[ \t]+"
    r"owners_sha256=([0-9a-f]{64})[ \t]+-->[ \t]*\r?$"
)
_SHA256_HEX_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_SHA1_HEX_RE: Final = re.compile(r"^[0-9a-f]{40}$")
_SHARED_OWNER_PATTERN: Final = (
    r"(?:launchers?|adapters?|registries|registry|resolvers?|clients?|state[ -]machines?)"
)
_OWNER_MODIFIER_PATTERN: Final = (
    r"(?:(?!(?:against|current|existing|for|from|in|into|on|through|to|using|via|with)\b)"
    r"[A-Za-z0-9_-]+[ \t]+)"
)
_OWNER_DECLARATION_SUFFIX_PATTERN: Final = (
    r"(?=[ \t]*(?:$|[,(:]|\b(?:and|as|backs|becomes|class|component|for|handles|"
    r"implementation|is|layer|library|module|owns|package|provides|replaces|routes|"
    r"service|that|to|type|which|will|with)\b))"
)
_SHARED_OWNER_CREATION_RE: Final = re.compile(
    rf"(?:\b(?:add(?:s|ed|ing)?|build(?:s|ing)?|built|creat(?:e|es|ed|ing)|"
    rf"defin(?:e|es|ed|ing)|establish(?:es|ed|ing)?|introduc(?:e|es|ed|ing))\b"
    rf"[ \t]+(?:(?:an?|the)[ \t]+)?(?:{_OWNER_MODIFIER_PATTERN}){{0,5}}"
    rf"{_SHARED_OWNER_PATTERN}\b{_OWNER_DECLARATION_SUFFIX_PATTERN}"
    rf"|\bnew[ \t]+(?:{_OWNER_MODIFIER_PATTERN}){{0,4}}{_SHARED_OWNER_PATTERN}\b"
    rf"{_OWNER_DECLARATION_SUFFIX_PATTERN}"
    rf"|\b{_SHARED_OWNER_PATTERN}\b[^.!?;\n]{{0,64}}?"
    r"\b(?:(?:is|are|gets?)[ \t]+|will[ \t]+be[ \t]+)"
    r"(?:added|built|created|defined|established|introduced)\b)",
    re.IGNORECASE,
)
_OWNER_CREATION_CLAUSE_RE: Final = re.compile(
    r"(?:[.!?;]+|\n[ \t]*\n|,[ \t]+(?:and|but|however)\b|\b(?:but|however)\b)",
    re.IGNORECASE,
)
_NEGATED_CREATION_RE: Final = re.compile(
    r"\b(?:neither|never|no|not|without)\b",
    re.IGNORECASE,
)
_NEGATED_CREATION_PREFIX_RE: Final = re.compile(
    r"(?:\b(?:neither|never|no|not|without)\b(?:[ \t]+[A-Za-z0-9_-]+){0,2}"
    r"|\bno[ \t]+need[ \t]+(?:for|to)(?:[ \t]+(?:an?|the))?)[ \t]*$",
    re.IGNORECASE,
)
_IMPLEMENTING_PREFIX: Final = config.TRACKING_ISSUE_PREFIX_BY_STATE["implementing"]
_LEASE_STALE_HOURS: Final = 12
_REUSE_OWNER_ROW_PARTS: Final = 4
_REPOSITORY_RE: Final = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_LEAF_TITLE_RE: Final = re.compile(r"\[LEAF OF [#]?[1-9][0-9]*\]", re.IGNORECASE)
_FINDING_ISSUE_RE: Final = re.compile(r"\bissue=#([1-9][0-9]*)\b")
_REGISTRY_PATH: Final = Path("crates/larch-lint/data/command-registry.toml")
_AUDIT_ISSUE_FIELDS: Final = ("number", "title", "state", "body", "updatedAt")
_COUNT_KEYS: Final = config.MIGRATION_AUDIT_COUNT_KEYS
_FINDING_CATEGORY_ORDER: Final = {
    "invalid_plan": 0,
    "missing_or_stale_blocker": 1,
    "owner_admission": 2,
    "active_owner_conflict": 3,
    "stale_implementation_lease": 4,
    "registry_state_violation": 5,
    "missing_caller_surface": 6,
    "python_retirement_violation": 7,
    "clean_install_coverage_gap": 8,
    "production_runtime_escape_hatch": 9,
}

REASON_MISSING_NATIVE: Final = "missing-native-blocker-edge"
REASON_UNDOCUMENTED_NATIVE: Final = "undocumented-native-blocker-edge"
REASON_CLOSED_RETAINED: Final = "closed-blocker-edge-retained"
REASON_BLOCKER_READ_UNAVAILABLE: Final = "blocker-read-unavailable"
REASON_STALE_PLAN_BODY: Final = "stale-plan-body"
REASON_STALE_PLAN_BASE_SCOPE: Final = "stale-plan-base-scope"
REASON_STALE_BLOCKER_SNAPSHOT: Final = "stale-blocker-snapshot"
REASON_STALE_OWNER_SNAPSHOT: Final = "stale-owner-snapshot"
REASON_MISSING_OWNER_BLOCK: Final = "missing-owner-block"
REASON_OWNER_SCAN_UNAVAILABLE: Final = "owner-scan-unavailable"
REASON_REUSE_SOURCE_UNAVAILABLE: Final = "reuse-source-unavailable"

BLOCKING_PARITY_REASONS: Final = frozenset(
    {
        REASON_MISSING_NATIVE,
        REASON_UNDOCUMENTED_NATIVE,
        REASON_BLOCKER_READ_UNAVAILABLE,
    }
)
RECEIPT_STALE_REASONS: Final = frozenset(
    {
        REASON_STALE_PLAN_BODY,
        REASON_STALE_PLAN_BASE_SCOPE,
        REASON_STALE_BLOCKER_SNAPSHOT,
        REASON_STALE_OWNER_SNAPSHOT,
    }
)


_OWNER_ROW_MIN_PARTS: Final = 2
_BLOCKING_PARITY_PREFIXES: Final = (
    f"{REASON_MISSING_NATIVE} ",
    f"{REASON_UNDOCUMENTED_NATIVE} ",
)


def _is_blocking_parity_reason(reason: str) -> bool:
    return reason == REASON_BLOCKER_READ_UNAVAILABLE or reason.startswith(
        _BLOCKING_PARITY_PREFIXES
    )


@dataclass(frozen=True)
class BlockerSnapshotRow:
    """Canonical blocker identity used for hashing and parity."""

    number: int
    state: str
    updated_at: str


@dataclass(frozen=True)
class PlanReceipt:
    """Parsed ``larch:plan-receipt`` v1 identity."""

    plan_sha256: str
    base_sha: str
    blockers_sha256: str
    owners_sha256: str


@dataclass(frozen=True)
class ParityVerdict:
    """Native blocker parity result. ``closed-*-retained`` is report-only."""

    reasons: tuple[str, ...]

    @property
    def blocking(self) -> bool:
        """True when any reason blocks migration admission."""
        return any(_is_blocking_parity_reason(reason) for reason in self.reasons)

    @property
    def report_only(self) -> tuple[str, ...]:
        """Closed retained edges that must not block admission."""
        return tuple(
            reason
            for reason in self.reasons
            if reason.startswith(f"{REASON_CLOSED_RETAINED} ")
        )


@dataclass(frozen=True)
class FreshnessVerdict:
    """Receipt freshness result against live plan, blockers, owners, and base scope."""

    reasons: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """True when the receipt matches live inputs."""
        return not self.reasons


@dataclass(frozen=True)
class OwnerAdmissionVerdict:
    """Owner grammar, reuse-source, conflict, and report-only lease results."""

    reasons: tuple[str, ...] = ()
    report_only: tuple[str, ...] = ()
    cleanup_commands: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.reasons


@dataclass(frozen=True)
class LeaseAuditFinding:
    """One report-only stale implementation lease."""

    token: str
    cleanup_command: str


@dataclass(frozen=True, order=True)
class CommandAuditKey:
    """One normalized command selector passed to the Rust registry audit."""

    domain: str
    verb: str


@dataclass(frozen=True)
class CommandAuditIssue:
    """Canonical issue evidence for migration-issue command parity."""

    number: int
    state: str
    executable_leaf: bool
    command: CommandAuditKey | None
    plan_commands: tuple[CommandAuditKey, ...]


@dataclass(frozen=True)
class MigrationIssueSnapshot:
    """One immutable issue row used by every aggregate check."""

    number: int
    title: str
    state: str
    body: str
    updated_at: str


@dataclass(frozen=True)
class DependencySnapshot:
    """One issue's native blocked-by numbers from a single transport read."""

    issue: int
    blockers: tuple[int, ...]


@dataclass(frozen=True)
class MigrationAuditSnapshot:
    """Immutable GitHub and repository identity shared across the audit."""

    repository: str
    chief_issue: int
    snapshot_timestamp: str
    head_sha: str
    open_issues: tuple[MigrationIssueSnapshot, ...]
    referenced_issues: tuple[MigrationIssueSnapshot, ...]
    dependencies: tuple[DependencySnapshot, ...]
    open_pr_branches: frozenset[str]
    tracked_paths: frozenset[str]


@dataclass(frozen=True)
class AggregateFinding:
    """One stable aggregate finding with bounded, non-secret evidence."""

    category: str
    reason: str
    issue: int | None = None
    cleanup_command: str | None = None

    def sort_key(self) -> tuple[int, int, str, str]:
        return (
            _FINDING_CATEGORY_ORDER[self.category],
            self.issue or 0,
            self.reason,
            self.cleanup_command or "",
        )

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "category": self.category,
            "issue": self.issue,
            "reason": self.reason,
        }
        if self.cleanup_command is not None:
            payload["cleanup_command"] = self.cleanup_command
        return payload


@dataclass(frozen=True)
class IssueAuditEvidence:
    """Stable per-issue result without title, body, comments, or credentials."""

    number: int
    plan_valid: bool | None
    finding_reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "number": self.number,
            "plan_valid": self.plan_valid,
            "finding_reasons": list(self.finding_reasons),
        }


@dataclass(frozen=True)
class MigrationAuditReport:
    """Schema-v1 aggregate report."""

    repository: str
    chief_issue: int
    snapshot_timestamp: str
    counts: tuple[tuple[str, int], ...]
    findings: tuple[AggregateFinding, ...]
    issues: tuple[IssueAuditEvidence, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": config.MIGRATION_AUDIT_SCHEMA_VERSION,
            "repository": self.repository,
            "chief_issue": self.chief_issue,
            "snapshot_timestamp": self.snapshot_timestamp,
            "counts": dict(self.counts),
            "findings": [finding.as_dict() for finding in self.findings],
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class MigrationAuditArgs:
    """Validated command arguments."""

    repository: str
    chief_issue: int
    output: Path | None
    table_output: str


class MigrationAuditError(ShipError):
    """Invocation or required-evidence failure (exit 2)."""


@dataclass(frozen=True)
class GovernanceGateVerdict:
    """Combined blocker-parity and receipt-freshness gate used at all four sites."""

    parity: ParityVerdict
    freshness: FreshnessVerdict
    owners: OwnerAdmissionVerdict = OwnerAdmissionVerdict()

    @property
    def ok(self) -> bool:
        """True when parity is non-blocking and the receipt is fresh."""
        return (not self.parity.blocking) and self.freshness.ok and self.owners.ok

    @property
    def blocking_reasons(self) -> tuple[str, ...]:
        """Operator-visible blocking tokens from parity and freshness."""
        blocking = [
            reason for reason in self.parity.reasons if _is_blocking_parity_reason(reason)
        ]
        blocking.extend(self.freshness.reasons)
        blocking.extend(self.owners.reasons)
        return tuple(blocking)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_state(raw: object) -> str:
    return str(raw or "").strip().lower()


def parse_native_blocker_refs(*, body: str) -> tuple[int, ...]:
    """Parse exact ``Native blocker:`` / ``Native blockers:`` fields fence-aware."""
    refs: set[int] = set()
    in_fence = False
    for raw_line in (body or "").splitlines():
        if _CODE_FENCE_RE.match(raw_line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _NATIVE_BLOCKER_LINE_RE.match(raw_line)
        if match is None:
            continue
        for ref in _ISSUE_REF_RE.finditer(match.group(1)):
            refs.add(int(ref.group(1)))
    return tuple(sorted(refs))


def parse_owner_rows(*, body: str) -> tuple[str, ...]:
    """Return exact owner rows through the canonical wire parser."""
    return issue_wire.parse_owner_block(body=body).raw_rows


def build_command_audit_issue(
    *,
    number: int,
    state: str,
    executable_leaf: bool,
    body: str,
    registry_commands: Sequence[CommandAuditKey],
) -> CommandAuditIssue:
    """Build typed Rust audit evidence through canonical issue parsers."""
    normalized_state = _normalize_state(state)
    if number <= 0 or normalized_state not in {"open", "closed"}:
        raise ShipError("invalid-command-audit-issue")
    parsed_owner = issue_wire.parse_owner_block(body=body)
    command = (
        CommandAuditKey(parsed_owner.block.domain, parsed_owner.block.verb)
        if parsed_owner.block is not None
        else None
    )
    plan_inner, malformed = parse_named_block(body=body, marker="plan")
    plan_commands: tuple[CommandAuditKey, ...] = ()
    if not malformed and plan_inner is not None:
        plan_commands = tuple(
            sorted(
                {
                    selector
                    for selector in registry_commands
                    if _plan_mentions_command(plan_inner=plan_inner, selector=selector)
                }
            )
        )
    return CommandAuditIssue(
        number=number,
        state=normalized_state,
        executable_leaf=executable_leaf,
        command=command,
        plan_commands=plan_commands,
    )


def _plan_mentions_command(*, plan_inner: str, selector: CommandAuditKey) -> bool:
    expression = re.compile(
        rf"(?<![a-z0-9-]){re.escape(selector.domain)}[ \t]+{re.escape(selector.verb)}(?![a-z0-9-])"
    )
    return expression.search(plan_inner) is not None


def render_command_audit_input(
    *, rows: Sequence[CommandAuditIssue], rollout_enabled: bool
) -> str:
    """Render stable schema-v1 JSON for ``command-registry audit``."""
    by_number: dict[int, CommandAuditIssue] = {}
    for row in rows:
        if row.number in by_number:
            raise ShipError("duplicate-command-audit-issue")
        by_number[row.number] = row
    payload: dict[str, object] = {
        "schema_version": 1,
        "rollout_enabled": rollout_enabled,
        "issues": [
            {
                "number": row.number,
                "state": row.state,
                "executable_leaf": row.executable_leaf,
                "command": (
                    {"domain": row.command.domain, "verb": row.command.verb}
                    if row.command is not None
                    else None
                ),
                "plan_commands": [
                    {"domain": command.domain, "verb": command.verb}
                    for command in row.plan_commands
                ],
            }
            for row in sorted(by_number.values(), key=lambda item: item.number)
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def owner_keys_from_rows(*, rows: Sequence[str]) -> tuple[str, ...]:
    """Extract CREATE/REUSE owner keys from exact owner rows."""
    keys: set[str] = set()
    for row in rows:
        parts = row.split("\t")
        if len(parts) < _OWNER_ROW_MIN_PARTS:
            continue
        kind = parts[0]
        if kind not in {"CREATE", "REUSE"}:
            continue
        key = parts[1]
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key) is not None:
            keys.add(key)
    return tuple(sorted(keys))


def hash_plan_block(*, plan_inner: str) -> str:
    """Hash exact plan-block inner bytes."""
    return _sha256_text(plan_inner)


def hash_blocker_rows(*, rows: Sequence[BlockerSnapshotRow]) -> str:
    """Hash sorted blocker number/state/updatedAt rows."""
    canonical = "\n".join(
        f"{row.number}\t{row.state}\t{row.updated_at}"
        for row in sorted(rows, key=lambda item: item.number)
    )
    return _sha256_text(canonical)


def hash_owner_rows(*, rows: Sequence[str]) -> str:
    """Hash sorted unique exact owner rows."""
    return _sha256_text("\n".join(sorted(set(rows))))


def render_receipt(*, receipt: PlanReceipt) -> str:
    if (
        _SHA256_HEX_RE.fullmatch(receipt.plan_sha256) is None
        or _SHA1_HEX_RE.fullmatch(receipt.base_sha) is None
        or _SHA256_HEX_RE.fullmatch(receipt.blockers_sha256) is None
        or _SHA256_HEX_RE.fullmatch(receipt.owners_sha256) is None
    ):
        raise ShipError("invalid-plan-receipt-fields")
    return (
        "<!-- larch:plan-receipt v1 "
        f"plan_sha256={receipt.plan_sha256} "
        f"base_sha={receipt.base_sha} "
        f"blockers_sha256={receipt.blockers_sha256} "
        f"owners_sha256={receipt.owners_sha256} -->"
    )


def parse_receipt(*, body: str) -> PlanReceipt | None:
    """Return the sole unfenced plan receipt, or None when absent/ambiguous."""
    lines = (body or "").splitlines()
    fenced = plan_grammar.balanced_fence_line_indices(list(lines))
    found: list[PlanReceipt] = []
    for idx, line in enumerate(lines):
        if idx in fenced:
            continue
        match = _RECEIPT_RE.match(line)
        if match is None:
            continue
        found.append(
            PlanReceipt(
                plan_sha256=match.group(1),
                base_sha=match.group(2),
                blockers_sha256=match.group(3),
                owners_sha256=match.group(4),
            )
        )
    if len(found) != 1:
        return None
    return found[0]


def strip_adjacent_plan_receipts(*, body: str) -> str:
    """Remove plan-receipt lines immediately after the plan end marker.

    Used when upserting a receipt next to the plan block.
    """
    lines = body.splitlines(keepends=True)
    span = issue_blocks.classify_named_block_lines(lines=lines, marker="plan")
    if span.malformed or span.start is None or span.end is None:
        return body
    kept: list[str] = list(lines[: span.end + 1])
    idx = span.end + 1
    while idx < len(lines):
        raw = lines[idx]
        bare = raw.rstrip("\r\n")
        if bare.strip() == "":
            kept.append(raw)
            idx += 1
            continue
        if _RECEIPT_RE.match(bare) is not None:
            idx += 1
            continue
        break
    kept.extend(lines[idx:])
    return "".join(kept)


def strip_plan_receipt_lines(*, body: str) -> str:
    """Remove every unfenced plan-receipt line.

    Used by the mutation owner when comparing plan named-block outers so an
    adjacent receipt refresh is not treated as a foreign body edit.
    """
    lines = body.splitlines(keepends=True)
    fenced = plan_grammar.balanced_fence_line_indices(
        [line.rstrip("\r\n") for line in lines]
    )
    kept: list[str] = []
    for idx, line in enumerate(lines):
        if idx in fenced:
            kept.append(line)
            continue
        if _RECEIPT_RE.match(line.rstrip("\r\n")) is not None:
            continue
        kept.append(line)
    return "".join(kept)


def upsert_receipt(*, body: str, receipt: PlanReceipt) -> str:
    """Insert or replace the receipt immediately after the plan block."""
    lines = body.splitlines(keepends=True)
    span = issue_blocks.classify_named_block_lines(lines=lines, marker="plan")
    if span.malformed:
        raise ShipError(f"plan-block-malformed:{span.malformed}")
    if span.start is None or span.end is None:
        raise ShipError("plan-block-missing")
    receipt_line = render_receipt(receipt=receipt) + "\n"
    prefix = list(lines[: span.end + 1])
    idx = span.end + 1
    # Drop an existing adjacent receipt (and one blank line immediately before it).
    while idx < len(lines):
        bare = lines[idx].rstrip("\r\n")
        if bare.strip() == "":
            # Peek whether a receipt follows the blank run.
            peek = idx + 1
            while peek < len(lines) and lines[peek].rstrip("\r\n").strip() == "":
                peek += 1
            if peek < len(lines) and _RECEIPT_RE.match(lines[peek].rstrip("\r\n")) is not None:
                idx = peek + 1
                continue
            break
        if _RECEIPT_RE.match(bare) is not None:
            idx += 1
            continue
        break
    return "".join([*prefix, receipt_line, *lines[idx:]])


def compare_blocker_parity(
    *,
    body_rows: Sequence[BlockerSnapshotRow],
    native_rows: Sequence[BlockerSnapshotRow],
) -> ParityVerdict:
    """Compare open body refs to live native edges in both directions."""
    body_numbers = {row.number for row in body_rows}
    open_body = {row.number for row in body_rows if row.state == "open"}
    open_native = {row.number for row in native_rows if row.state == "open"}
    reasons: list[str] = [
        *(
            f"{REASON_MISSING_NATIVE} issue=#{number}"
            for number in sorted(open_body)
            if number not in open_native
        ),
        *(
            f"{REASON_UNDOCUMENTED_NATIVE} issue=#{number}"
            for number in sorted(open_native)
            if number not in body_numbers
        ),
        *(
            f"{REASON_CLOSED_RETAINED} issue=#{row.number}"
            for row in sorted(native_rows, key=lambda item: item.number)
            if row.state != "open"
        ),
    ]
    return ParityVerdict(reasons=tuple(reasons))


def _loads_json_object(text: str, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(text or "null")
    except json.JSONDecodeError as exc:
        raise issue_block.DependencyReadError(f"{context}: invalid JSON") from exc
    if not isinstance(payload, dict):
        raise issue_block.DependencyReadError(f"{context}: expected object")
    return cast("dict[str, object]", payload)


def _heading_path_token(raw: str) -> str:
    stripped = raw.strip()
    backtick_matches = list(re.finditer(r"`([^`]+)`", stripped))
    if backtick_matches:
        return backtick_matches[0].group(1).strip()
    parts = stripped.split()
    if not parts:
        return ""
    return re.sub(r"\(.*$", "", parts[0]).strip()


def _path_has_unsafe_shape(path: str) -> bool:
    if not path or path.strip() != path:
        return True
    if path.startswith("~"):
        return True
    candidate = Path(path)
    if candidate.is_absolute():
        return True
    parts = candidate.parts
    if not parts or parts[0] == "..":
        return True
    return any(part == ".." for part in parts)


def _is_glob_path(path: str) -> bool:
    return any(char in path for char in "*?[")


def _issue_freshness_row(
    runner: Runner, issue: int, *, repo: str, cwd: str | None
) -> BlockerSnapshotRow:
    result = gh.issue_view_field_read(
        runner, str(issue), "number,state,updatedAt", repo=repo, cwd=cwd
    )
    if result.returncode != 0:
        raise issue_block.DependencyReadError(
            f"issue freshness read failed for #{issue}"
        )
    data = _loads_json_object(result.stdout, context=f"issue #{issue} freshness")
    number_raw = data.get("number", issue)
    if isinstance(number_raw, bool):
        raise issue_block.DependencyReadError(
            f"issue freshness number invalid for #{issue}"
        )
    if isinstance(number_raw, int):
        number = number_raw
    elif isinstance(number_raw, str):
        try:
            number = int(number_raw)
        except ValueError as exc:
            raise issue_block.DependencyReadError(
                f"issue freshness number invalid for #{issue}"
            ) from exc
    else:
        raise issue_block.DependencyReadError(
            f"issue freshness number invalid for #{issue}"
        )
    state = _normalize_state(data.get("state"))
    updated_at = data.get("updatedAt")
    if not state or not isinstance(updated_at, str) or not updated_at:
        raise issue_block.DependencyReadError(
            f"issue freshness fields missing for #{issue}"
        )
    return BlockerSnapshotRow(number=number, state=state, updated_at=updated_at)


def load_blocker_snapshot(
    runner: Runner,
    *,
    issue: str,
    repo: str,
    body: str,
    cwd: str | None = None,
) -> tuple[tuple[BlockerSnapshotRow, ...], ParityVerdict]:
    """Load native edges + body-ref freshness rows and compute parity."""
    body_refs = parse_native_blocker_refs(body=body)
    try:
        native = issue_block.read_blocked_by_dependencies(
            runner, issue, repo=repo, cwd=cwd
        )
    except issue_block.DependencyReadError:
        return (), ParityVerdict(reasons=(REASON_BLOCKER_READ_UNAVAILABLE,))
    native_rows = tuple(
        BlockerSnapshotRow(
            number=row.number, state=row.state, updated_at=row.updated_at
        )
        for row in native
    )
    by_number: dict[int, BlockerSnapshotRow] = {row.number: row for row in native_rows}
    try:
        for ref in body_refs:
            if ref not in by_number:
                by_number[ref] = _issue_freshness_row(
                    runner, ref, repo=repo, cwd=cwd
                )
    except issue_block.DependencyReadError:
        return (), ParityVerdict(reasons=(REASON_BLOCKER_READ_UNAVAILABLE,))
    rows = tuple(sorted(by_number.values(), key=lambda item: item.number))
    body_rows = tuple(by_number[ref] for ref in body_refs if ref in by_number)
    parity = compare_blocker_parity(body_rows=body_rows, native_rows=native_rows)
    return rows, parity


def _tracked_paths_at_sha(
    runner: Runner, *, sha: str, cwd: str
) -> frozenset[str]:
    result = runner.run(["git", "ls-tree", "-r", "--name-only", "-z", sha], cwd=cwd)
    if result.returncode != 0:
        raise ShipError("base-scope-ls-tree-failed")
    raw = result.stdout
    if not raw:
        return frozenset()
    parts = raw.split("\0")
    return frozenset(part for part in parts if part)


def _blob_oid_at_sha(
    runner: Runner, *, sha: str, path: str, cwd: str
) -> str:
    result = runner.run(["git", "ls-tree", "-z", sha, "--", path], cwd=cwd)
    if result.returncode != 0:
        raise ShipError("base-scope-blob-lookup-failed")
    payload = result.stdout.split("\0", 1)[0].strip()
    if not payload:
        return "MISSING"
    # format: <mode> <type> <oid>\t<name>
    try:
        meta, _name = payload.split("\t", 1)
        oid = meta.split()[2]
    except (IndexError, ValueError) as exc:
        raise ShipError("base-scope-blob-parse-failed") from exc
    if not oid:
        return "MISSING"
    return oid


def declared_scope_paths(*, plan_inner: str, tracked: frozenset[str]) -> tuple[str, ...]:
    """Resolve plan headings to concrete tracked paths (globs expanded)."""
    paths: set[str] = set()
    for heading in plan_grammar.iter_plan_headings(plan_inner):
        token = _heading_path_token(heading.path)
        if not token or _path_has_unsafe_shape(token):
            continue
        if _is_glob_path(token):
            paths.update(
                path for path in tracked if fnmatch.fnmatchcase(path, token)
            )
            continue
        paths.add(token)
    return tuple(sorted(paths))


def compute_base_scope_fingerprint(
    runner: Runner,
    *,
    sha: str,
    plan_inner: str,
    owner_keys: Sequence[str],
    cwd: str,
) -> str:
    """Fingerprint declared files and owner keys at ``sha``."""
    if _SHA1_HEX_RE.fullmatch(sha) is None:
        raise ShipError("invalid-base-sha")
    tracked = _tracked_paths_at_sha(runner, sha=sha, cwd=cwd)
    scope_paths = declared_scope_paths(plan_inner=plan_inner, tracked=tracked)
    file_lines = [
        f"{path}\t{_blob_oid_at_sha(runner, sha=sha, path=path, cwd=cwd)}"
        for path in scope_paths
    ]
    owner_lines = [f"owner\t{key}" for key in sorted(set(owner_keys))]
    return _sha256_text("\n".join([*file_lines, *owner_lines]))


def validate_receipt_freshness(
    runner: Runner,
    *,
    body: str,
    repo_root: Path,
    blocker_rows: Sequence[BlockerSnapshotRow],
    head_sha: str | None = None,
) -> FreshnessVerdict:
    """Validate the persisted receipt against live inputs (I-Stale-1)."""
    receipt = parse_receipt(body=body)
    if receipt is None:
        return FreshnessVerdict(reasons=(REASON_STALE_PLAN_BODY,))
    plan_inner, malformed = parse_named_block(body=body, marker="plan")
    if malformed or plan_inner is None:
        return FreshnessVerdict(reasons=(REASON_STALE_PLAN_BODY,))
    reasons: list[str] = []
    if hash_plan_block(plan_inner=plan_inner) != receipt.plan_sha256:
        reasons.append(REASON_STALE_PLAN_BODY)
    owner_rows = parse_owner_rows(body=body)
    if hash_owner_rows(rows=owner_rows) != receipt.owners_sha256:
        reasons.append(REASON_STALE_OWNER_SNAPSHOT)
    if hash_blocker_rows(rows=blocker_rows) != receipt.blockers_sha256:
        reasons.append(REASON_STALE_BLOCKER_SNAPSHOT)
    cwd = str(repo_root)
    try:
        current_head = head_sha or git.rev_parse(runner, "HEAD", cwd=cwd)
        base_fp = compute_base_scope_fingerprint(
            runner,
            sha=receipt.base_sha,
            plan_inner=plan_inner,
            owner_keys=owner_keys_from_rows(rows=owner_rows),
            cwd=cwd,
        )
        head_fp = compute_base_scope_fingerprint(
            runner,
            sha=current_head,
            plan_inner=plan_inner,
            owner_keys=owner_keys_from_rows(rows=owner_rows),
            cwd=cwd,
        )
    except (ShipError, OSError):
        reasons.append(REASON_STALE_PLAN_BASE_SCOPE)
    else:
        if base_fp != head_fp:
            reasons.append(REASON_STALE_PLAN_BASE_SCOPE)
    return FreshnessVerdict(reasons=tuple(reasons))


def _migration_section_text(*, plan_inner: str) -> str:
    """Return the fence-aware migration section without trailing plan metadata."""
    in_migration = False
    migration_lines: list[str] = []
    for event in plan_grammar.iter_heading_events(plan_inner):
        if event.generic_level_two:
            in_migration = event.text.strip().casefold() == "## breaking changes and migration"
            continue
        if in_migration:
            stripped: str = event.text.strip()
            if any(
                stripped.startswith(f"{key}:")
                for key in plan_grammar.TRAILER_KEYS
            ) or stripped.casefold().startswith("confidence:"):
                break
            migration_lines.append(event.text)
    return "\n".join(migration_lines).strip()


def _creation_is_negated(*, clause: str, match: re.Match[str]) -> bool:
    """Return whether local prose negates one candidate creation declaration."""
    prefix: str = clause[: match.start()].rsplit(",", maxsplit=1)[-1]
    return (
        _NEGATED_CREATION_PREFIX_RE.search(prefix) is not None
        or _NEGATED_CREATION_RE.search(match.group(0)) is not None
    )


def _clause_creates_shared_owner(*, clause: str) -> bool:
    """Return whether one prose clause affirmatively creates a shared owner."""
    normalized: str = " ".join(clause.split())
    for match in _SHARED_OWNER_CREATION_RE.finditer(normalized):
        if not _creation_is_negated(clause=normalized, match=match):
            return True
    return False


def migration_requires_owner_block(*, plan_inner: str) -> bool:
    """Return whether migration prose declares a new shared runtime owner."""
    migration_text: str = _migration_section_text(plan_inner=plan_inner)
    return any(
        _clause_creates_shared_owner(clause=clause)
        for clause in _OWNER_CREATION_CLAUSE_RE.split(migration_text)
        if clause.strip()
    )


def _reuse_source_snapshot(
    runner: Runner, *, issue: int, repo: str, cwd: str | None
) -> tuple[str, str] | None:
    result = gh.issue_view_field_read(
        runner, str(issue), "body,state", repo=repo, cwd=cwd
    )
    if result.returncode != 0:
        return None
    try:
        loaded: object = json.loads(result.stdout or "null")
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    payload = cast("dict[str, object]", loaded)
    body = payload.get("body")
    state = payload.get("state")
    if not isinstance(body, str) or not isinstance(state, str):
        return None
    return body, state.casefold()


def _validate_reuse_sources(
    runner: Runner,
    *,
    block: issue_wire.OwnerBlock,
    body: str,
    repo: str,
    cwd: str | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    native_refs = frozenset(parse_native_blocker_refs(body=body))
    for owner in block.owners:
        if owner.kind != "REUSE" or owner.source_issue is None:
            continue
        source = _reuse_source_snapshot(
            runner, issue=owner.source_issue, repo=repo, cwd=cwd
        )
        if source is None:
            reasons.append(
                f"{REASON_REUSE_SOURCE_UNAVAILABLE} owner={owner.owner_key} issue=#{owner.source_issue}"
            )
            continue
        source_body, source_state = source
        parsed = issue_wire.parse_owner_block(body=source_body)
        receipt = parse_receipt(body=source_body)
        creates: set[str] = set()
        if parsed.block is not None:
            creates = {row.owner_key for row in parsed.block.owners if row.kind == "CREATE"}
        snapshot_ok = (
            receipt is not None
            and receipt.owners_sha256 == hash_owner_rows(rows=parsed.raw_rows)
            and owner.owner_key in creates
        )
        if not snapshot_ok:
            reasons.append(
                f"reuse-owner-snapshot-invalid owner={owner.owner_key} issue=#{owner.source_issue}"
            )
        if source_state == "open" and owner.source_issue not in native_refs:
            reasons.append(
                f"reuse-missing-native-blocker owner={owner.owner_key} issue=#{owner.source_issue}"
            )
    return tuple(reasons)


def _active_owner_conflicts(
    *, issue: int, block: issue_wire.OwnerBlock, active_rows: Sequence[open_rows.OpenIssueRow]
) -> tuple[str, ...]:
    creates = {row.owner_key for row in block.owners if row.kind == "CREATE"}
    conflicts: set[tuple[str, int]] = set()
    for active in active_rows:
        lease = issue_wire.parse_implementation_lease(body=active.body)
        terminal = active.title.startswith(
            (
                config.TRACKING_ISSUE_PREFIX_BY_STATE["done"],
                config.TRACKING_ISSUE_PREFIX_BY_STATE["stalled"],
            )
        )
        active_or_pending = active.title.startswith(_IMPLEMENTING_PREFIX) or (
            lease is not None and not terminal
        )
        if active.number == issue or not active_or_pending:
            continue
        parsed = issue_wire.parse_owner_block(body=active.body)
        active_keys = (
            {row.owner_key for row in parsed.block.owners}
            if parsed.block is not None
            else set(owner_keys_from_rows(rows=parsed.raw_rows))
        )
        for key in creates & active_keys:
            conflicts.add((key, active.number))
    return tuple(
        f"active-owner-conflict owner={key} issue=#{number}"
        for key, number in sorted(conflicts)
    )


def _open_pr_branches(
    runner: Runner, *, repo: str, cwd: str | None
) -> frozenset[str] | None:
    result = gh.pr_list_open_read(runner, repo=repo, cwd=cwd, limit=10000)
    if result.returncode != 0:
        return None
    try:
        payload: object = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    branches: set[str] = set()
    for item in cast("list[object]", payload):
        if not isinstance(item, dict):
            return None
        branch = cast("dict[str, object]", item).get("headRefName")
        if not isinstance(branch, str) or not branch:
            return None
        branches.add(branch)
    return frozenset(branches)


def audit_stale_implementation_leases(
    runner: Runner,
    *,
    repo: str,
    active_rows: Sequence[open_rows.OpenIssueRow],
    now: datetime | None = None,
    cwd: str | None = None,
) -> tuple[LeaseAuditFinding, ...]:
    """Report stale leases with no matching open PR. Never mutates GitHub."""
    open_branches = _open_pr_branches(runner, repo=repo, cwd=cwd)
    if open_branches is None:
        return ()
    return audit_stale_implementation_leases_snapshot(
        repo=repo,
        active_rows=active_rows,
        open_pr_branches=open_branches,
        now=now,
    )


def audit_stale_implementation_leases_snapshot(
    *,
    repo: str,
    active_rows: Sequence[open_rows.OpenIssueRow],
    open_pr_branches: frozenset[str],
    now: datetime | None = None,
) -> tuple[LeaseAuditFinding, ...]:
    """Evaluate leases from a caller-owned immutable issue and PR snapshot."""
    current = now or datetime.now(UTC)
    findings: list[LeaseAuditFinding] = []
    for row in active_rows:
        if not row.title.startswith(_IMPLEMENTING_PREFIX):
            continue
        lease = issue_wire.parse_implementation_lease(body=row.body)
        if lease is None or lease.branch in open_pr_branches:
            continue
        try:
            updated = datetime.strptime(
                lease.updated_at, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=UTC)
        except ValueError:
            continue
        age_hours = int((current - updated).total_seconds() // 3600)
        if age_hours < _LEASE_STALE_HOURS:
            continue
        findings.append(
            LeaseAuditFinding(
                token=f"stale-implementation-lease issue=#{row.number} age_hours={age_hours}",
                cleanup_command=(
                    "python3 python/cli.py tracking-issue rename "
                    f"--issue {row.number} --state stalled --repo {repo} --run-id {lease.run_id}"
                ),
            )
        )
    return tuple(findings)


def evaluate_owner_admission(
    runner: Runner,
    *,
    issue: str,
    repo: str,
    body: str,
    cwd: str | None = None,
) -> OwnerAdmissionVerdict:
    """Validate owner bytes, REUSE sources, and active CREATE conflicts."""
    plan_inner, malformed = parse_named_block(body=body, marker="plan")
    if malformed or plan_inner is None:
        return OwnerAdmissionVerdict()
    parsed = issue_wire.parse_owner_block(body=body)
    reasons: list[str] = []
    if parsed.defects:
        reasons.extend(f"owner-block-invalid defect={defect}" for defect in parsed.defects)
    if migration_requires_owner_block(plan_inner=plan_inner) and parsed.block is None:
        reasons.append(REASON_MISSING_OWNER_BLOCK)
    if parsed.block is None:
        return OwnerAdmissionVerdict(reasons=tuple(reasons))
    reasons.extend(
        _validate_reuse_sources(
            runner, block=parsed.block, body=body, repo=repo, cwd=cwd
        )
    )
    try:
        active_rows = open_rows.open_issue_rows_read(runner, repo=repo)
    except ShipError:
        reasons.append(REASON_OWNER_SCAN_UNAVAILABLE)
        return OwnerAdmissionVerdict(reasons=tuple(reasons))
    reasons.extend(
        _active_owner_conflicts(
            issue=int(issue), block=parsed.block, active_rows=active_rows
        )
    )
    findings = audit_stale_implementation_leases(
        runner, repo=repo, active_rows=active_rows, cwd=cwd
    )
    return OwnerAdmissionVerdict(
        reasons=tuple(dict.fromkeys(reasons)),
        report_only=tuple(finding.token for finding in findings),
        cleanup_commands=tuple(finding.cleanup_command for finding in findings),
    )


def evaluate_governance_gate(  # noqa: PLR0913 - shared gate identity is deliberately explicit across workflow consumers
    runner: Runner,
    *,
    issue: str,
    repo: str,
    body: str,
    repo_root: Path,
    cwd: str | None = None,
    head_sha: str | None = None,
) -> GovernanceGateVerdict:
    """Verify lease admission and the preflight, Step 2, rebase, and PR gates."""
    rows, parity = load_blocker_snapshot(
        runner, issue=issue, repo=repo, body=body, cwd=cwd
    )
    if parity.reasons == (REASON_BLOCKER_READ_UNAVAILABLE,):
        return GovernanceGateVerdict(
            parity=parity,
            freshness=FreshnessVerdict(reasons=()),
        )
    freshness = validate_receipt_freshness(
        runner,
        body=body,
        repo_root=repo_root,
        blocker_rows=rows,
        head_sha=head_sha,
    )
    owners = evaluate_owner_admission(
        runner, issue=issue, repo=repo, body=body, cwd=cwd
    )
    return GovernanceGateVerdict(parity=parity, freshness=freshness, owners=owners)


def build_receipt_for_body(  # noqa: PLR0913 - receipt identity inputs are deliberately explicit
    runner: Runner,
    *,
    issue: str,
    repo: str,
    body: str,
    repo_root: Path,
    base_sha: str | None = None,
    cwd: str | None = None,
) -> tuple[PlanReceipt, ParityVerdict]:
    """Compute the receipt that should accompany the current plan body."""
    plan_inner, malformed = parse_named_block(body=body, marker="plan")
    if malformed or plan_inner is None:
        raise ShipError("plan-block-missing-for-receipt")
    rows, parity = load_blocker_snapshot(
        runner, issue=issue, repo=repo, body=body, cwd=cwd
    )
    if parity.reasons == (REASON_BLOCKER_READ_UNAVAILABLE,):
        raise ShipError(REASON_BLOCKER_READ_UNAVAILABLE)
    owner_rows = parse_owner_rows(body=body)
    resolved_base = base_sha or git.rev_parse(runner, "HEAD", cwd=str(repo_root))
    if _SHA1_HEX_RE.fullmatch(resolved_base) is None:
        raise ShipError("invalid-base-sha")
    receipt = PlanReceipt(
        plan_sha256=hash_plan_block(plan_inner=plan_inner),
        base_sha=resolved_base,
        blockers_sha256=hash_blocker_rows(rows=rows),
        owners_sha256=hash_owner_rows(rows=owner_rows),
    )
    return receipt, parity


def persist_plan_receipt(
    runner: Runner,
    *,
    issue: str,
    repo: str,
    repo_root: Path,
    cwd: str | None = None,
) -> PlanReceipt:
    """Write and read-verify the receipt immediately after plan publication."""
    from larch.issue import issue_mutation  # noqa: PLC0415 - lazy: avoid cycle with issue_mutation plan-receipt strip

    snapshot = issue_mutation.read_snapshot(
        runner, repository=repo, issue=issue, cwd=cwd
    )
    receipt, parity = build_receipt_for_body(
        runner,
        issue=issue,
        repo=repo,
        body=snapshot.body,
        repo_root=repo_root,
        cwd=cwd,
    )
    _ = parity  # closed retained edges stay report-only at publish time
    updated_body = upsert_receipt(body=snapshot.body, receipt=receipt)
    if updated_body == snapshot.body:
        verified = parse_receipt(body=snapshot.body)
        if verified != receipt:
            raise ShipError("plan-receipt-readback-mismatch")
        return receipt
    # Prefer named-block mutation so [DESIGNING] issues can refresh the adjacent
    # receipt with the plan marker lease; fall back to body mutation otherwise.
    try:
        verified_mutation = issue_mutation.update_named_block(
            runner,
            repository=repo,
            issue=issue,
            marker="plan",
            body=updated_body,
            lease=issue_wire.named_block_lease(marker="plan"),
            cwd=cwd,
        )
    except issue_mutation.ProtectedIssueMutation:
        verified_mutation = issue_mutation.update_body(
            runner,
            repository=repo,
            issue=issue,
            body=updated_body,
            cwd=cwd,
        )
    verified = parse_receipt(body=verified_mutation.after.body)
    if verified != receipt:
        raise ShipError("plan-receipt-readback-mismatch")
    return receipt


def format_gate_refusal(*, site: str, verdict: GovernanceGateVerdict) -> str:
    """Render a single-line operator refusal for a failed governance gate."""
    tokens = ",".join(verdict.blocking_reasons) or "unknown"
    return f"**❌ {site}: {config.MIGRATION_GOVERNANCE_BLOCKED_DETAIL_MARKER} `{tokens}`.**"


def read_issue_body(
    runner: Runner, *, issue: str, repo: str, cwd: str | None = None
) -> str:
    """Read the issue body through the typed GitHub adapter."""
    result = gh.issue_view_field_read(
        runner, issue, "body", repo=repo or None, cwd=cwd
    )
    if result.returncode != 0:
        raise ShipError("issue-body-read-failed")
    try:
        payload: object = json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        raise ShipError("issue-body-read-failed") from exc
    if not isinstance(payload, Mapping):
        raise ShipError("issue-body-read-failed")
    body = cast("Mapping[str, object]", payload).get("body")
    return body if isinstance(body, str) else ""


def _positive_issue_number(value: object, *, context: str) -> int:
    if isinstance(value, bool):
        raise MigrationAuditError(f"{context}: invalid issue number")
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return int(value)
    raise MigrationAuditError(f"{context}: invalid issue number")


def _parse_migration_issue(value: object, *, context: str) -> MigrationIssueSnapshot:
    if not isinstance(value, Mapping):
        raise MigrationAuditError(f"{context}: issue row is not an object")
    row = cast("Mapping[str, object]", value)
    number = _positive_issue_number(row.get("number"), context=context)
    title = row.get("title")
    state = row.get("state")
    body = row.get("body")
    updated_at = row.get("updatedAt")
    if not all(isinstance(item, str) for item in (title, state, body, updated_at)):
        raise MigrationAuditError(f"{context}: issue row omitted required fields")
    normalized_state = cast("str", state).casefold()
    if normalized_state not in {"open", "closed"}:
        raise MigrationAuditError(f"{context}: issue row has invalid state")
    return MigrationIssueSnapshot(
        number=number,
        title=cast("str", title),
        state=normalized_state,
        body=cast("str", body),
        updated_at=cast("str", updated_at),
    )


def _chief_reference_present(*, body: str, chief_issue: int) -> bool:
    patterns = (
        rf"Chief[ \t]+umbrella:[ \t]*#{chief_issue}(?![0-9])",
        rf"#{chief_issue}[ \t]+Chief[ \t]+Umbrella(?![0-9])",
    )
    return any(re.search(pattern, body, re.IGNORECASE) is not None for pattern in patterns)


def _is_executable_leaf(issue: MigrationIssueSnapshot, *, chief_issue: int) -> bool:
    return (
        issue.state == "open"
        and _LEAF_TITLE_RE.search(issue.title) is not None
        and _chief_reference_present(body=issue.body, chief_issue=chief_issue)
    )


def _dependency_numbers_from_result(
    result: CommandResult, *, issue: int
) -> tuple[int, ...]:
    if result.returncode != 0:
        raise MigrationAuditError(f"issue #{issue}: blocked-by read failed")
    try:
        rows = gh.loads_json_paginated_list(result.stdout)
    except ShipError as exc:
        raise MigrationAuditError(
            f"issue #{issue}: blocked-by read returned invalid JSON"
        ) from exc
    numbers: set[int] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise MigrationAuditError(f"issue #{issue}: blocked-by row is not an object")
        number = _positive_issue_number(
            cast("Mapping[str, object]", row).get("number"),
            context=f"issue #{issue} blocked-by row",
        )
        if number in numbers:
            raise MigrationAuditError(f"issue #{issue}: duplicate blocked-by row #{number}")
        numbers.add(number)
    return tuple(sorted(numbers))


def _reuse_source_refs(*, body: str) -> tuple[int, ...]:
    parsed = issue_wire.parse_owner_block(body=body)
    refs: set[int] = set()
    for row in parsed.raw_rows:
        parts = row.split("\t")
        if (
            len(parts) == _REUSE_OWNER_ROW_PARTS
            and parts[0] == "REUSE"
            and re.fullmatch(r"#[1-9][0-9]*", parts[2]) is not None
        ):
            refs.add(int(parts[2][1:]))
    return tuple(sorted(refs))


def _read_referenced_issue(
    runner: Runner, *, repository: str, issue: int, cwd: str
) -> MigrationIssueSnapshot:
    result = gh.issue_view_field_read(
        runner, str(issue), ",".join(_AUDIT_ISSUE_FIELDS), repo=repository, cwd=cwd
    )
    if result.returncode != 0:
        raise MigrationAuditError(f"issue #{issue}: required evidence unavailable")
    try:
        payload: object = json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        raise MigrationAuditError(f"issue #{issue}: required evidence is invalid JSON") from exc
    return _parse_migration_issue(payload, context=f"issue #{issue}")


def _open_issue_rows_for_snapshot(
    issues: Sequence[MigrationIssueSnapshot],
) -> tuple[open_rows.OpenIssueRow, ...]:
    return tuple(
        open_rows.OpenIssueRow(
            number=issue.number,
            title=issue.title,
            state=issue.state,
            labels=(),
            body=issue.body,
        )
        for issue in issues
    )


def load_migration_audit_snapshot(
    runner: Runner,
    *,
    repository: str,
    chief_issue: int,
    repo_root: Path,
    now: datetime | None = None,
) -> MigrationAuditSnapshot:
    """Fetch each required GitHub and repository evidence row at most once."""
    cwd = str(repo_root)
    current = now or datetime.now(UTC)
    timestamp = current.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        raw_open = gh.issue_list_read(
            runner,
            repo=repository,
            state="open",
            fields=_AUDIT_ISSUE_FIELDS,
            limit=open_rows.ISSUE_LIST_LIMIT,
            cwd=cwd,
        )
    except (OSError, ShipError) as exc:
        raise MigrationAuditError("open issue snapshot unavailable") from exc
    open_issues = tuple(
        sorted(
            (
                _parse_migration_issue(value, context="open issue snapshot")
                for value in raw_open
            ),
            key=lambda item: item.number,
        )
    )
    if len({issue.number for issue in open_issues}) != len(open_issues):
        raise MigrationAuditError("open issue snapshot contains duplicates")
    leaves = tuple(
        issue
        for issue in open_issues
        if _is_executable_leaf(issue, chief_issue=chief_issue)
    )
    dependencies: list[DependencySnapshot] = []
    required_refs: set[int] = set()
    for leaf in leaves:
        result = gh.issue_blocked_by_read(
            runner, str(leaf.number), repo=repository, cwd=cwd
        )
        blockers = _dependency_numbers_from_result(result, issue=leaf.number)
        dependencies.append(DependencySnapshot(issue=leaf.number, blockers=blockers))
        required_refs.update(blockers)
        required_refs.update(parse_native_blocker_refs(body=leaf.body))
        required_refs.update(_reuse_source_refs(body=leaf.body))
    open_numbers = {issue.number for issue in open_issues}
    referenced_issues = tuple(
        _read_referenced_issue(
            runner, repository=repository, issue=number, cwd=cwd
        )
        for number in sorted(required_refs - open_numbers)
    )
    open_pr_branches = _open_pr_branches(runner, repo=repository, cwd=cwd)
    if open_pr_branches is None:
        raise MigrationAuditError("open pull request snapshot unavailable")
    try:
        head_sha = git.rev_parse(runner, "HEAD", cwd=cwd)
        tracked_paths = frozenset(git.ls_files(runner, cwd=cwd))
    except (OSError, ShipError) as exc:
        raise MigrationAuditError("repository snapshot unavailable") from exc
    if _SHA1_HEX_RE.fullmatch(head_sha) is None:
        raise MigrationAuditError("repository snapshot has invalid HEAD")
    return MigrationAuditSnapshot(
        repository=repository,
        chief_issue=chief_issue,
        snapshot_timestamp=timestamp,
        head_sha=head_sha,
        open_issues=open_issues,
        referenced_issues=referenced_issues,
        dependencies=tuple(sorted(dependencies, key=lambda item: item.issue)),
        open_pr_branches=open_pr_branches,
        tracked_paths=tracked_paths,
    )


def _issues_by_number(
    snapshot: MigrationAuditSnapshot,
) -> dict[int, MigrationIssueSnapshot]:
    return {
        issue.number: issue
        for issue in (*snapshot.open_issues, *snapshot.referenced_issues)
    }


def _blocker_rows(
    *,
    numbers: Sequence[int],
    issues: Mapping[int, MigrationIssueSnapshot],
    context: str,
) -> tuple[BlockerSnapshotRow, ...]:
    rows: list[BlockerSnapshotRow] = []
    for number in sorted(set(numbers)):
        issue = issues.get(number)
        if issue is None:
            raise MigrationAuditError(f"{context}: issue #{number} evidence unavailable")
        rows.append(
            BlockerSnapshotRow(
                number=number, state=issue.state, updated_at=issue.updated_at
            )
        )
    return tuple(rows)


def _validate_reuse_sources_snapshot(
    *,
    block: issue_wire.OwnerBlock,
    body: str,
    issues: Mapping[int, MigrationIssueSnapshot],
) -> tuple[str, ...]:
    reasons: list[str] = []
    native_refs = frozenset(parse_native_blocker_refs(body=body))
    for owner in block.owners:
        if owner.kind != "REUSE" or owner.source_issue is None:
            continue
        source = issues.get(owner.source_issue)
        if source is None:
            reasons.append(
                f"{REASON_REUSE_SOURCE_UNAVAILABLE} owner={owner.owner_key} issue=#{owner.source_issue}"
            )
            continue
        parsed = issue_wire.parse_owner_block(body=source.body)
        receipt = parse_receipt(body=source.body)
        creates: set[str] = (
            {row.owner_key for row in parsed.block.owners if row.kind == "CREATE"}
            if parsed.block is not None
            else set()
        )
        if not (
            receipt is not None
            and receipt.owners_sha256 == hash_owner_rows(rows=parsed.raw_rows)
            and owner.owner_key in creates
        ):
            reasons.append(
                f"reuse-owner-snapshot-invalid owner={owner.owner_key} issue=#{owner.source_issue}"
            )
        if source.state == "open" and owner.source_issue not in native_refs:
            reasons.append(
                f"reuse-missing-native-blocker owner={owner.owner_key} issue=#{owner.source_issue}"
            )
    return tuple(reasons)


def _registry_commands(*, repo_root: Path) -> tuple[CommandAuditKey, ...]:
    path = repo_root / _REGISTRY_PATH
    try:
        text = larch_io.read_trusted_text(path, root=repo_root, reject_cr=True)
        payload = cast("Mapping[str, object]", tomllib.loads(text))
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        raise MigrationAuditError("command registry evidence unavailable") from exc
    raw_commands_value = payload.get("commands")
    if not isinstance(raw_commands_value, list):
        raise MigrationAuditError("command registry evidence is malformed")
    raw_commands = cast("list[object]", raw_commands_value)
    commands: set[CommandAuditKey] = set()
    for raw_value in raw_commands:
        if not isinstance(raw_value, Mapping):
            raise MigrationAuditError("command registry evidence is malformed")
        raw = cast("Mapping[str, object]", raw_value)
        domain = raw.get("domain")
        verb = raw.get("verb")
        if not isinstance(domain, str) or not isinstance(verb, str):
            raise MigrationAuditError("command registry evidence is malformed")
        commands.add(CommandAuditKey(domain=domain, verb=verb))
    if len(commands) != len(raw_commands):
        raise MigrationAuditError("command registry evidence contains duplicates")
    return tuple(sorted(commands))


def _safe_lint_findings(result: CommandResult, *, context: str) -> tuple[str, ...]:
    if result.returncode == 0:
        if result.stdout.strip() or result.stderr.strip():
            raise MigrationAuditError(f"{context}: clean result emitted unexpected output")
        return ()
    if result.returncode != 1 or result.stderr.strip():
        detail = redact.redact_secrets_only(result.stderr or result.stdout).strip()
        raise MigrationAuditError(f"{context}: required evidence failed: {detail[:500]}")
    findings: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        safe = redact.redact_secrets_only(line).strip()
        if "[content truncated" in safe:
            raise MigrationAuditError(f"{context}: evidence redaction failed")
        findings.append(safe)
    if not findings:
        raise MigrationAuditError(f"{context}: finding exit omitted findings")
    return tuple(sorted(set(findings)))


def _classify_registry_finding(reason: str) -> str:
    if "clean-install-coverage-missing" in reason:
        return "clean_install_coverage_gap"
    if "python-entrypoint-still-" in reason:
        return "python_retirement_violation"
    if reason.startswith(("production caller ", "ledger caller ")) or "production caller inventory" in reason:
        return "missing_caller_surface"
    return "registry_state_violation"


def _finding_issue_number(reason: str) -> int | None:
    match = _FINDING_ISSUE_RE.search(reason)
    return int(match.group(1)) if match is not None else None


def collect_repository_audit_findings(
    runner: Runner,
    *,
    snapshot: MigrationAuditSnapshot,
    repo_root: Path,
) -> tuple[AggregateFinding, ...]:
    """Invoke the canonical Rust lint owners without Cargo or target paths."""
    larch_binary = shutil.which("larch")
    if larch_binary is None:
        raise MigrationAuditError("required larch executable is unavailable on PATH")
    root = str(repo_root)
    registry_result = runner.run(
        [larch_binary, "lint", "--root", root, "rule", "command-registry"], cwd=root
    )
    registry_lines = _safe_lint_findings(registry_result, context="command-registry audit")
    runtime_result = runner.run(
        [larch_binary, "lint", "--root", root, "rule", "production-cargo-run"],
        cwd=root,
    )
    runtime_lines = _safe_lint_findings(runtime_result, context="production-runtime audit")
    commands = _registry_commands(repo_root=repo_root)
    issue_rows = tuple(
        build_command_audit_issue(
            number=issue.number,
            state=issue.state,
            executable_leaf=_is_executable_leaf(issue, chief_issue=snapshot.chief_issue),
            body=issue.body,
            registry_commands=commands,
        )
        for issue in (*snapshot.open_issues, *snapshot.referenced_issues)
    )
    audit_input = render_command_audit_input(rows=issue_rows, rollout_enabled=True)
    system_tmp = Path(tempfile.gettempdir()).resolve()
    try:
        with tempfile.TemporaryDirectory(prefix="larch-migration-audit-", dir=system_tmp) as temp_dir:
            audit_path = Path(temp_dir) / "command-audit.json"
            larch_io.trusted_atomic_write(audit_path, audit_input, root=temp_dir)
            issue_result = runner.run(
                [
                    larch_binary,
                    "lint",
                    "--root",
                    root,
                    "command-registry",
                    "audit",
                    "--input",
                    str(audit_path),
                ],
                cwd=root,
            )
            issue_lines = _safe_lint_findings(
                issue_result, context="migration-issue command audit"
            )
    except OSError as exc:
        raise MigrationAuditError("command audit temporary evidence failed") from exc
    findings = [
        AggregateFinding(
            category=_classify_registry_finding(reason),
            reason=reason,
            issue=_finding_issue_number(reason),
        )
        for reason in (*registry_lines, *issue_lines)
    ]
    findings.extend(
        AggregateFinding(category="production_runtime_escape_hatch", reason=reason)
        for reason in runtime_lines
    )
    return tuple(sorted(findings, key=AggregateFinding.sort_key))


def _append_owner_findings(
    *,
    issue: MigrationIssueSnapshot,
    issues: Mapping[int, MigrationIssueSnapshot],
    active_rows: Sequence[open_rows.OpenIssueRow],
    findings: list[AggregateFinding],
) -> None:
    plan_inner, malformed = parse_named_block(body=issue.body, marker="plan")
    if malformed or plan_inner is None:
        return
    parsed = issue_wire.parse_owner_block(body=issue.body)
    reasons = [f"owner-block-invalid defect={defect}" for defect in parsed.defects]
    if migration_requires_owner_block(plan_inner=plan_inner) and parsed.block is None:
        reasons.append(REASON_MISSING_OWNER_BLOCK)
    if parsed.block is not None:
        reasons.extend(
            _validate_reuse_sources_snapshot(
                block=parsed.block, body=issue.body, issues=issues
            )
        )
        reasons.extend(
            _active_owner_conflicts(
                issue=issue.number, block=parsed.block, active_rows=active_rows
            )
        )
    for reason in dict.fromkeys(reasons):
        category = (
            "active_owner_conflict"
            if reason.startswith("active-owner-conflict ")
            else "owner_admission"
        )
        findings.append(AggregateFinding(category=category, reason=reason, issue=issue.number))


def build_migration_audit_report(
    runner: Runner,
    *,
    snapshot: MigrationAuditSnapshot,
    repo_root: Path,
    repository_findings: Sequence[AggregateFinding] = (),
) -> MigrationAuditReport:
    """Compose M1-M14 results from one immutable snapshot."""
    issues = _issues_by_number(snapshot)
    dependencies = {row.issue: row.blockers for row in snapshot.dependencies}
    leaves = tuple(
        issue
        for issue in snapshot.open_issues
        if _is_executable_leaf(issue, chief_issue=snapshot.chief_issue)
    )
    active_rows = _open_issue_rows_for_snapshot(snapshot.open_issues)
    findings: list[AggregateFinding] = list(repository_findings)
    plan_validity: dict[int, bool] = {}
    for leaf in leaves:
        plan_result = issue_wire.validate_issue_plan(
            issue_body=leaf.body,
            repo_root=repo_root,
            tracked_paths=snapshot.tracked_paths,
        )
        plan_validity[leaf.number] = plan_result.ok
        findings.extend(
            AggregateFinding(category="invalid_plan", reason=defect, issue=leaf.number)
            for defect in plan_result.defects
        )
        native_numbers = dependencies.get(leaf.number)
        if native_numbers is None:
            raise MigrationAuditError(f"issue #{leaf.number}: dependency snapshot unavailable")
        body_numbers = parse_native_blocker_refs(body=leaf.body)
        all_numbers = tuple(sorted({*native_numbers, *body_numbers}))
        all_rows = _blocker_rows(
            numbers=all_numbers, issues=issues, context=f"issue #{leaf.number}"
        )
        by_number = {row.number: row for row in all_rows}
        native_rows = tuple(by_number[number] for number in native_numbers)
        body_rows = tuple(by_number[number] for number in body_numbers)
        parity = compare_blocker_parity(body_rows=body_rows, native_rows=native_rows)
        freshness = validate_receipt_freshness(
            runner,
            body=leaf.body,
            repo_root=repo_root,
            blocker_rows=all_rows,
            head_sha=snapshot.head_sha,
        )
        findings.extend(
            AggregateFinding(
                category="missing_or_stale_blocker", reason=reason, issue=leaf.number
            )
            for reason in (*parity.reasons, *freshness.reasons)
        )
        _append_owner_findings(
            issue=leaf, issues=issues, active_rows=active_rows, findings=findings
        )
    lease_findings = audit_stale_implementation_leases_snapshot(
        repo=snapshot.repository,
        active_rows=active_rows,
        open_pr_branches=snapshot.open_pr_branches,
        now=datetime.strptime(snapshot.snapshot_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=UTC
        ),
    )
    findings.extend(
        AggregateFinding(
            category="stale_implementation_lease",
            reason=finding.token,
            issue=_finding_issue_number(finding.token),
            cleanup_command=finding.cleanup_command,
        )
        for finding in lease_findings
    )
    ordered_findings = tuple(sorted(set(findings), key=AggregateFinding.sort_key))
    counts: dict[str, int] = dict.fromkeys(_COUNT_KEYS, 0)
    counts["executable_leaves"] = len(leaves)
    counts["valid_plans"] = sum(plan_validity.values())
    category_counts = {
        "missing_or_stale_blocker": "missing_or_stale_blockers",
        "active_owner_conflict": "active_owner_conflicts",
        "stale_implementation_lease": "stale_implementation_leases",
        "registry_state_violation": "registry_state_violations",
        "missing_caller_surface": "missing_caller_surfaces",
        "python_retirement_violation": "python_retirement_violations",
        "clean_install_coverage_gap": "clean_install_coverage_gaps",
        "production_runtime_escape_hatch": "production_runtime_escape_hatches",
    }
    for finding in ordered_findings:
        count_key = category_counts.get(finding.category)
        if count_key is not None:
            counts[count_key] += 1
    evidence_numbers = sorted(
        set(plan_validity)
        | {finding.issue for finding in ordered_findings if finding.issue is not None}
    )
    evidence = tuple(
        IssueAuditEvidence(
            number=number,
            plan_valid=plan_validity.get(number),
            finding_reasons=tuple(
                finding.reason for finding in ordered_findings if finding.issue == number
            ),
        )
        for number in evidence_numbers
    )
    return MigrationAuditReport(
        repository=snapshot.repository,
        chief_issue=snapshot.chief_issue,
        snapshot_timestamp=snapshot.snapshot_timestamp,
        counts=tuple((key, counts[key]) for key in _COUNT_KEYS),
        findings=ordered_findings,
        issues=evidence,
    )


def render_migration_audit_json(*, report: MigrationAuditReport) -> str:
    """Render compact deterministic schema-v1 JSON."""
    return json.dumps(report.as_dict(), sort_keys=True, separators=(",", ":")) + "\n"


def render_migration_audit_table(*, report: MigrationAuditReport) -> str:
    """Render the concise human count table."""
    labels = {key: key.replace("_", " ") for key in _COUNT_KEYS}
    width = max(len(label) for label in labels.values())
    lines = ["Migration governance audit", ""]
    lines.extend(
        f"{labels[key].ljust(width)}  {value}" for key, value in report.counts
    )
    return "\n".join(lines) + "\n"


def _parse_migration_audit_args(argv: Sequence[str]) -> MigrationAuditArgs:
    parser = argparse.ArgumentParser(prog="larch issue migration-audit")
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--chief", required=True, type=int)
    _ = parser.add_argument("--output")
    _ = parser.add_argument(
        "--table-output", choices=config.MIGRATION_AUDIT_TABLE_OUTPUTS, default="stderr"
    )
    args = parser.parse_args(list(argv))
    repository = str(args.repo)
    chief_issue = int(args.chief)
    raw_output = Path(args.output) if args.output else None
    output = raw_output.parent.resolve() / raw_output.name if raw_output else None
    table_output = str(args.table_output)
    if _REPOSITORY_RE.fullmatch(repository) is None:
        raise MigrationAuditError("--repo must be exactly owner/name")
    if chief_issue <= 0:
        raise MigrationAuditError("--chief must be a positive issue number")
    if output is None and table_output == "stdout":
        raise MigrationAuditError(
            "--table-output stdout requires --output so stdout stays machine-readable"
        )
    return MigrationAuditArgs(
        repository=repository,
        chief_issue=chief_issue,
        output=output,
        table_output=table_output,
    )


def migration_audit_main(argv: list[str]) -> int:
    """Run the read-only aggregate. Exit 0 clean, 1 findings, or 2 unavailable."""
    try:
        args = _parse_migration_audit_args(argv)
        repo_root = repo_roots.consumer_repo_root(runner=proc)
        if repo_root is None:
            raise MigrationAuditError("repository root unavailable")
        snapshot = load_migration_audit_snapshot(
            proc,
            repository=args.repository,
            chief_issue=args.chief_issue,
            repo_root=repo_root,
        )
        repository_findings = collect_repository_audit_findings(
            proc, snapshot=snapshot, repo_root=repo_root
        )
        report = build_migration_audit_report(
            proc,
            snapshot=snapshot,
            repo_root=repo_root,
            repository_findings=repository_findings,
        )
        if git.rev_parse(proc, "HEAD", cwd=str(repo_root)) != snapshot.head_sha:
            raise MigrationAuditError("repository changed during audit")
        rendered = render_migration_audit_json(report=report)
        if args.output is None:
            _ = sys.stdout.write(rendered)
        else:
            larch_io.atomic_write(
                path=args.output,
                text=rendered,
                create_parent=False,
                mode=0o600,
                prefix=f".{args.output.name}.",
                nofollow=True,
            )
        table = render_migration_audit_table(report=report)
        if args.table_output == "stderr":
            _ = sys.stderr.write(table)
        elif args.table_output == "stdout":
            _ = sys.stdout.write(table)
        return config.MIGRATION_AUDIT_EXIT_FINDINGS if report.findings else config.EXIT_OK
    except (ShipError, OSError, ValueError) as exc:
        detail = redact.redact_secrets_only(str(exc)).replace("\n", " ").strip()
        print(f"ERROR: migration-audit: {detail[:500]}", file=sys.stderr)
        return config.MIGRATION_AUDIT_EXIT_UNAVAILABLE


# Re-export CommandResult for typed test doubles without importing proc at call sites.
__all__ = [
    "BLOCKING_PARITY_REASONS",
    "REASON_BLOCKER_READ_UNAVAILABLE",
    "REASON_CLOSED_RETAINED",
    "REASON_MISSING_NATIVE",
    "REASON_MISSING_OWNER_BLOCK",
    "REASON_OWNER_SCAN_UNAVAILABLE",
    "REASON_REUSE_SOURCE_UNAVAILABLE",
    "REASON_STALE_BLOCKER_SNAPSHOT",
    "REASON_STALE_OWNER_SNAPSHOT",
    "REASON_STALE_PLAN_BASE_SCOPE",
    "REASON_STALE_PLAN_BODY",
    "REASON_UNDOCUMENTED_NATIVE",
    "RECEIPT_STALE_REASONS",
    "AggregateFinding",
    "BlockerSnapshotRow",
    "CommandAuditIssue",
    "CommandAuditKey",
    "CommandResult",
    "DependencySnapshot",
    "FreshnessVerdict",
    "GovernanceGateVerdict",
    "IssueAuditEvidence",
    "LeaseAuditFinding",
    "MigrationAuditError",
    "MigrationAuditReport",
    "MigrationAuditSnapshot",
    "MigrationIssueSnapshot",
    "OwnerAdmissionVerdict",
    "ParityVerdict",
    "PlanReceipt",
    "audit_stale_implementation_leases",
    "audit_stale_implementation_leases_snapshot",
    "build_command_audit_issue",
    "build_migration_audit_report",
    "build_receipt_for_body",
    "collect_repository_audit_findings",
    "compare_blocker_parity",
    "compute_base_scope_fingerprint",
    "declared_scope_paths",
    "evaluate_governance_gate",
    "evaluate_owner_admission",
    "format_gate_refusal",
    "hash_blocker_rows",
    "hash_owner_rows",
    "hash_plan_block",
    "load_blocker_snapshot",
    "load_migration_audit_snapshot",
    "migration_audit_main",
    "migration_requires_owner_block",
    "owner_keys_from_rows",
    "parse_native_blocker_refs",
    "parse_owner_rows",
    "parse_receipt",
    "persist_plan_receipt",
    "read_issue_body",
    "render_command_audit_input",
    "render_migration_audit_json",
    "render_migration_audit_table",
    "render_receipt",
    "strip_adjacent_plan_receipts",
    "strip_plan_receipt_lines",
    "upsert_receipt",
    "validate_receipt_freshness",
]
