"""Plan blocker parity and base-scope freshness receipts (M4/M5).

Owns canonical blocker-field parsing, native parity, receipt grammar, hashes,
and freshness verdicts. Callers share one verifier and one input canonicalization.
"""
# pylint: disable=cyclic-import  # accepted: persist_plan_receipt mutates via issue_mutation; plan CAS strips receipts via this module (both function-level).

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

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
_SHARED_OWNER_RE: Final = re.compile(
    r"\b(?:launchers?|adapters?|registries|registry|resolvers?|clients?|state[ -]machines?)\b",
    re.IGNORECASE,
)
_IMPLEMENTING_PREFIX: Final = "[IMPLEMENTING] "
_LEASE_STALE_HOURS: Final = 12

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


def migration_requires_owner_block(*, plan_inner: str) -> bool:
    """Return whether migration prose declares a new shared runtime owner."""
    events = list(plan_grammar.iter_heading_events(plan_inner))
    in_migration = False
    migration_lines: list[str] = []
    for event in events:
        if event.generic_level_two:
            in_migration = event.text.strip().casefold() == "## breaking changes and migration"
            continue
        if in_migration:
            if any(
                event.text.strip().startswith(f"{key}:")
                for key in plan_grammar.TRAILER_KEYS
            ):
                break
            migration_lines.append(event.text)
    migration_text = "\n".join(migration_lines).strip()
    if not migration_text or migration_text.casefold().rstrip(".") in {"none", "no migration"}:
        return False
    return _SHARED_OWNER_RE.search(plan_inner) is not None


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
        creates = {
            row.owner_key
            for row in parsed.block.owners
            if parsed.block is not None and row.kind == "CREATE"
        } if parsed.block is not None else set()
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
        terminal = active.title.startswith(("[DONE] ", "[STALLED] "))
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
        if isinstance(item, dict):
            branch = cast("dict[str, object]", item).get("headRefName")
            if isinstance(branch, str) and branch:
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
    current = now or datetime.now(UTC)
    findings: list[LeaseAuditFinding] = []
    for row in active_rows:
        if not row.title.startswith(_IMPLEMENTING_PREFIX):
            continue
        lease = issue_wire.parse_implementation_lease(body=row.body)
        if lease is None or lease.branch in open_branches:
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


def evaluate_governance_gate(  # noqa: PLR0913 - shared gate identity is deliberately explicit across four call sites
    runner: Runner,
    *,
    issue: str,
    repo: str,
    body: str,
    repo_root: Path,
    cwd: str | None = None,
    head_sha: str | None = None,
) -> GovernanceGateVerdict:
    """Shared verifier used by preflight, Step 2, post-rebase, and pre-PR."""
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
    run_id = os.environ.get("RUN_ID", "").strip()
    lease = (
        issue_mutation.ImplementationLease(run_id=run_id, marker="plan")
        if run_id
        else None
    )
    try:
        verified_mutation = issue_mutation.update_named_block(
            runner,
            repository=repo,
            issue=issue,
            marker="plan",
            body=updated_body,
            lease=lease,
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
    return f"**❌ {site}: migration governance blocked: `{tokens}`.**"


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
    "BlockerSnapshotRow",
    "CommandResult",
    "FreshnessVerdict",
    "GovernanceGateVerdict",
    "LeaseAuditFinding",
    "OwnerAdmissionVerdict",
    "ParityVerdict",
    "PlanReceipt",
    "audit_stale_implementation_leases",
    "build_receipt_for_body",
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
    "migration_requires_owner_block",
    "owner_keys_from_rows",
    "parse_native_blocker_refs",
    "parse_owner_rows",
    "parse_receipt",
    "persist_plan_receipt",
    "read_issue_body",
    "render_receipt",
    "strip_adjacent_plan_receipts",
    "strip_plan_receipt_lines",
    "upsert_receipt",
    "validate_receipt_freshness",
]
