# argparse add_argument() and file write_text()/write() results are intentionally discarded.
# pyright: reportUnusedCallResult=false
"""Mine closed issues for recurring root causes and propose preventions.

Backs the ``/learn-from-bugs`` skill. GitHub access goes through the
``larch.core.proc.Runner`` seam so the digest and coverage-index logic stay
unit-testable offline. The module never reads a full issue backlog into a model:
it compresses each body to a compact root-cause digest first (an average
bug-report body is dominated by an appended ``/design`` plan, which this drops),
so the synthesis step reads a small fraction of the raw tokens.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shlex
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Final, Literal, cast

from larch import io as larch_io
from larch.core import config
from larch.core.architectural_guidelines import (
    GUIDELINE_HEADING_RE,
    GUIDELINES_FILENAME,
    INVARIANT_HEADING_RE,
    INVARIANTS_FILENAME,
)
from larch.core.proc import CommandResult, ProcRunner, Runner
from larch.design import design_log_ship
from larch.errors import ShipError
from larch.git import gh, git
from larch.issue import issue_wire
from larch.issue.analyze_bugs import resolve_repo
from larch.issue.file_oos import file_conflict_deps
from larch.issue.issue_create import parse_issue_input
from larch.issue.title_match import BUG_PREFIX, bug_title_match
from larch.report import analysis_state

DEFAULT_SEARCH: Final = f"{BUG_PREFIX} in:title"
DEFAULT_STATE: Final = "closed"
DEFAULT_LIMIT: Final = 50

OriginKind = Literal["regression", "new-code", "spec-gap", "unknown"]
ORIGIN_KINDS: Final[tuple[OriginKind, ...]] = ("regression", "new-code", "spec-gap", "unknown")
UnknownOriginReason = Literal["no-classification-signal", "inconclusive"]
_UNKNOWN_ORIGIN_REASONS: Final[tuple[UnknownOriginReason, ...]] = (
    "no-classification-signal",
    "inconclusive",
)
_UNKNOWN_ORIGIN_REASON_LABELS: Final[Mapping[UnknownOriginReason, str]] = {
    "no-classification-signal": "no classification signal",
    "inconclusive": "signal present but inconclusive",
}
GuidelinesIndexStatus = Literal["missing", "empty", "indexed"]
_GUIDELINES_INDEX_STATUS_KEY: Final = "GUIDELINES_INDEX_STATUS"

# Per-section char caps for the compact digest.
SUMMARY_CAP: Final = 600
ROOT_CAUSE_CAP: Final = 1000
FIX_CAP: Final = 400
FREEFORM_CAP: Final = 1100
# A diagnostic prefix shorter than this means the body is only the appended plan;
# the bug's signal then lives in its title.
TITLE_ONLY_PREFIX_MAX: Final = 40
# Digest chunks stay below the 20k-token Read budget. The two-character estimate
# is deliberately conservative for JSONL diagnostics.
DIGEST_CHUNK_TOKEN_LIMIT: Final = 19_000
DIGEST_CHARS_PER_TOKEN_ESTIMATE: Final = 2
TABLE_MIN_DELIMITERS: Final = 2
TABLE_DOMINANCE_MULTIPLIER: Final = 2

# Diagnostic sections to keep, each with its cap. Deduped by the heading's first
# word so "root cause" and "root cause analysis" do not both land.
WANT_SECTIONS: Final = (
    ("summary", SUMMARY_CAP),
    ("impact", SUMMARY_CAP),
    ("classification", FIX_CAP),
    ("root cause analysis", ROOT_CAUSE_CAP),
    ("root cause", ROOT_CAUSE_CAP),
    ("suggested fix(es)", FIX_CAP),
    ("suggested fix", FIX_CAP),
    ("repro", FIX_CAP),
)

# Earliest match marks where the appended /design plan begins; everything before
# it is the diagnostic report we mine.
_BOUNDARY_PATTERNS: Final = (
    issue_wire.named_block_marker_re(marker="plan", kind="start"),
    re.compile(r"^##\s+Plan\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^##\s+Approach\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^###\s+(?:NEW|UPDATED|REWRITTEN|MAY_UPDATE):", re.IGNORECASE | re.MULTILINE
    ),
)
_HEADING_RE: Final = re.compile(r"^#{2,4}\s+(.+?)\s*$")
_BOLD_PSEUDO_HEADING_RE: Final = re.compile(
    r"^\*\*(?P<name>Impact|Classification|Repro)\*\*"
    r"(?:[ \t]*:[ \t]*|[ \t]*)(?P<body>.*)$",
    re.IGNORECASE,
)
_CLASSIFICATION_VALUE_RE: Final = re.compile(
    r"^\s*(?P<kind>[A-Z][A-Z0-9_]*)(?:\s*\([^\n)]*\))?\s*,\s*"
    r"owning\s+surface\s+(?P<surface>[A-Z][A-Z0-9_]*)\b",
    re.IGNORECASE,
)
_HARNESS_ROOT_CAUSE_CLASS_RE: Final = re.compile(
    r"\broot[- ]cause\s+class\s*(?::\s*)?`?(?P<kind>[A-Z][A-Z0-9_]*)`?\b",
    re.IGNORECASE,
)
_HARNESS_OWNING_SURFACE_RE: Final = re.compile(
    r"\bowning\s+surface\s*(?::\s*)?`?(?P<surface>[A-Z][A-Z0-9_]*)`?\b",
    re.IGNORECASE,
)
_FENCE_MARKER_RE: Final = re.compile(r"^(`{3,}|~{3,})(.*)$")
_UNMARKED_GUIDELINE_HEADING_RE: Final = re.compile(
    r"^#{2,3}\s+(?P<title>.+?)(?:\s+#+)?\s*$"
)
_DONE_PREFIX_RE: Final = re.compile(r"^\[DONE\]\s*")
_PROPOSAL_ID_RE: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TEST_NAME_RE: Final = re.compile(r"^test_[A-Za-z0-9_]+$")
_TEST_TARGET_SUFFIXES: Final = (".py", ".rs")
_FIX_TOKEN_RE: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CHECK_SYMBOL_RE: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BOX_DRAWING_CHAR_RE: Final = re.compile(r"[\u2500-\u257f]")

ProposalType = Literal["lint", "invariant", "guideline", "hook", "test", "fix"]
ProposalStatus = Literal["proposed", "adopted", "pending", "orphaned"]
AdoptionEvidence = Literal["target-verified", "issue-closed-only", "both"]
PROPOSAL_TYPES: Final = frozenset(
    {"lint", "invariant", "guideline", "hook", "test", "fix"}
)
PROPOSAL_STATUSES: Final = frozenset({"proposed", "adopted", "pending", "orphaned"})
ADOPTION_EVIDENCE_KINDS: Final[tuple[AdoptionEvidence, ...]] = (
    "target-verified",
    "issue-closed-only",
    "both",
)
REGISTRY_KEY_LENGTH: Final = 2

# Origin extraction: referenced residual markers (first match in source order wins).
# Supported PR spacing: "PR #N" and "PR#N" only.
# Two prose surfaces enumerate these phrases for reporters: the G-Md-4 entry in
# ARCHITECTURAL_GUIDELINES.md and the /bug body template in skills/bug/SKILL.md.
# Sweep all three surfaces together when the phrase set changes (G-Wire-3, G-Md-2).
_ORIGIN_REF_PATTERNS: Final = (
    re.compile(r"introduced\s+by\s+PR\s*#(\d+)", re.IGNORECASE),
    re.compile(r"introduced\s+by\s+#(\d+)", re.IGNORECASE),
    re.compile(r"introduced\s+in\s+#(\d+)", re.IGNORECASE),
    re.compile(r"incomplete\s+fix\s+of\s+#(\d+)", re.IGNORECASE),
    re.compile(r"persists\s+after\s+#(\d+)", re.IGNORECASE),
    re.compile(r"residual\s+of\s+#(\d+)", re.IGNORECASE),
)
_BARE_REGRESSION_RE: Final = re.compile(r"\bregression\b", re.IGNORECASE)
_SPEC_GAP_PHRASES: Final = ("never designed", "was never told", "no handling for")
_NEW_CODE_PHRASES: Final = ("first time this path ran", "newly added")
_CLASSIFICATION_ORIGIN_KINDS: Final[Mapping[str, OriginKind]] = {
    "IMPLEMENTATION_BUG": "new-code",
    "CONFIGURATION_GAP": "spec-gap",
    "DESIGN_GAP": "spec-gap",
}

PROSE_ONLY_MARKER: Final = "prose-only prevention: unlikely to stick"
_PROSE_ONLY_CITATIONS: Final = ("character-ai/larch#6746", "character-ai/larch#6747")
_MECHANICAL_ALT_RE: Final = re.compile(
    r"\b(?:lint|hook|invariant(?:[-\s]?test)?)\b|no mechanical alternative",
    re.IGNORECASE,
)
_SECTION2_HEADING_RE: Final = re.compile(
    r"^#{1,6}\s+.*root-cause clusters.*$|^\d+\.\s+\*\*Root-cause clusters\.\*\*",
    re.IGNORECASE | re.MULTILINE,
)
_NEXT_TOP_SECTION_RE: Final = re.compile(
    r"^#{1,3}\s+\d*\.?\s*(?:\*\*)?(?:Already covered|Proposed mechanical|Proposed architectural|"
    r"Proposed guideline|Proposed regression|Issues to file|Scope and cost)",
    re.IGNORECASE | re.MULTILINE,
)


class LearnFromBugsError(RuntimeError):
    """Raised when issue mining cannot proceed."""


@dataclass(frozen=True)
class Proposal:
    """One durable prevention proposal and its observed check-time evidence."""

    id: str
    type: ProposalType
    target: str
    run_date: str
    status: ProposalStatus
    filed_issue: int | None = None
    adoption_evidence: AdoptionEvidence | None = None

    def to_json(self, *, include_adoption_evidence: bool = False) -> dict[str, object]:
        """Serialize durable fields, optionally including check-time evidence."""
        payload: dict[str, object] = {
            "id": self.id,
            "type": self.type,
            "target": self.target,
            "run_date": self.run_date,
            "status": self.status,
            "filed_issue": self.filed_issue,
        }
        if include_adoption_evidence:
            payload["adoption_evidence"] = self.adoption_evidence
        return payload


@dataclass(frozen=True)
class LearnFromBugsState:
    """Durable marker for the latest successful ``/learn-from-bugs`` report."""

    run_date: str
    repo: str
    search: str
    state: str
    selected_count: int
    highest_closed_issue_number_scanned: int
    scan_started_at: str | None = None
    proposals: tuple[Proposal, ...] = ()
    schema_version: int = 2

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": 2,
            "run_date": self.run_date,
            "repo": self.repo,
            "search": self.search,
            "state": self.state,
            "selected_count": self.selected_count,
            "highest_closed_issue_number_scanned": self.highest_closed_issue_number_scanned,
            "proposals": [proposal.to_json() for proposal in self.proposals],
        }
        if self.scan_started_at is not None:
            payload["scan_started_at"] = self.scan_started_at
        return payload


@dataclass(frozen=True)
class Origin:
    """Best-effort bug origin classification for a digest record."""

    kind: OriginKind
    ref: int | None = None
    unknown_reason: UnknownOriginReason | None = None

    def to_json(self) -> dict[str, object]:
        return {"kind": self.kind, "ref": self.ref}


@dataclass(frozen=True)
class _OriginEvidence:
    """Origin classifier inputs plus whether the diagnostic supplied a signal."""

    sources: tuple[str, ...]
    has_classification_signal: bool


@dataclass(frozen=True)
class BugClass:
    """Machine-filed defect classification extracted from a digest."""

    kind: str
    surface: str

    def to_json(self) -> dict[str, str]:
        return {"kind": self.kind, "surface": self.surface}


@dataclass(frozen=True)
class BugDigest:
    number: int
    title: str
    closed_at: str
    url: str
    state: str
    structured: bool
    prefix_chars: int
    sections: Mapping[str, str]
    origin: Origin
    classification: BugClass | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "number": self.number,
            "title": self.title,
            "closed_at": self.closed_at,
            "url": self.url,
            "state": self.state,
            "structured": self.structured,
            "prefix_chars": self.prefix_chars,
            "sections": dict(self.sections),
            "origin": self.origin.to_json(),
        }
        if self.classification is not None:
            payload["class"] = self.classification.to_json()
        return payload


@dataclass(frozen=True)
class CoverageIndex:
    """The target repo's existing enforcement surface, for dedup in the report."""

    guidelines: tuple[tuple[str, str], ...]
    invariants: tuple[tuple[str, str], ...]
    python_lints: tuple[str, ...]
    script_lints: tuple[str, ...]
    guidelines_index_status: GuidelinesIndexStatus

    def to_json(self) -> dict[str, object]:
        return {
            "guidelines": [list(item) for item in self.guidelines],
            "invariants": [list(item) for item in self.invariants],
            "python_lints": list(self.python_lints),
            "script_lints": list(self.script_lints),
        }


@dataclass(frozen=True)
class PrepareRequest:
    search: str
    search_explicit: bool
    state: str
    limit: int
    repo_explicit: str
    out_dir: Path
    root: Path
    full: bool = False


def _runner() -> Runner:
    return ProcRunner()


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_path(root: Path) -> Path:
    """Return the repository-scoped mutable marker outside the run-log tree."""
    root_path: Path = root.expanduser()
    if not root_path.is_absolute():
        root_path = Path.cwd() / root_path
    root_path = root_path.resolve()
    return (
        analysis_state.repository_state_root(repo_root=root_path)
        / config.LEARN_FROM_BUGS_STATE_RELPATH
    )


def _int_field(payload: Mapping[str, object], key: str, default: int) -> int:
    raw = payload.get(key)
    if isinstance(raw, bool):
        return default
    if not isinstance(raw, (int, str)):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value


def _parse_date(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise LearnFromBugsError(f"invalid proposal {field}: {value!r}")
    try:
        if "T" not in value:
            date.fromisoformat(value)
        else:
            datetime.fromisoformat(
                value.removesuffix("Z") + ("+00:00" if value.endswith("Z") else "")
            )
    except ValueError as exc:
        raise LearnFromBugsError(f"invalid proposal {field}: {value!r}") from exc
    return value


def _normalized_relative_path(raw: str, suffixes: tuple[str, ...]) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute() or not raw or "\\" in raw:
        raise LearnFromBugsError(f"unsafe proposal target path: {raw!r}")
    if (
        any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.as_posix() != raw
    ):
        raise LearnFromBugsError(f"unsafe proposal target path: {raw!r}")
    if suffixes and candidate.suffix not in suffixes:
        raise LearnFromBugsError(f"unsupported proposal target path: {raw!r}")
    return candidate


def _safe_relative_path(root: Path, raw: str, suffixes: tuple[str, ...]) -> Path:
    candidate = _normalized_relative_path(raw, suffixes)
    resolved_root = root.expanduser().resolve()
    resolved = (resolved_root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise LearnFromBugsError(f"proposal target escapes analysis root: {raw!r}")
    return resolved


def _validate_architectural_target(target: str) -> tuple[str, str]:
    if target.count("#") != 1:
        raise LearnFromBugsError(f"invalid architectural target: {target!r}")
    path_target, fragment = target.split("#", 1)
    if not fragment or any(char in fragment for char in "\r\n"):
        raise LearnFromBugsError(f"invalid architectural target fragment: {target!r}")
    return path_target, fragment


def _validate_check_target(target: str, root: Path | None) -> tuple[str, str]:
    """Validate one repository-hosted check target and return its path and symbol."""
    raw_target = target.removeprefix("check:")
    if not target.startswith("check:") or raw_target.count("#") != 1:
        raise LearnFromBugsError(f"invalid check target: {target!r}")
    path_target, symbol = raw_target.split("#", 1)
    if _CHECK_SYMBOL_RE.fullmatch(symbol) is None:
        raise LearnFromBugsError(f"invalid check target symbol: {target!r}")
    _validate_path_target(path_target, (), root)
    return path_target, symbol


def _validate_path_target(
    raw: str, suffixes: tuple[str, ...], root: Path | None
) -> None:
    if root is None:
        _normalized_relative_path(raw, suffixes)
    else:
        _safe_relative_path(root, raw, suffixes)


def _validate_fix_or_hook_target(proposal_type: ProposalType, target: str) -> bool:
    if proposal_type == "fix":
        if not target.startswith("fix:") or _FIX_TOKEN_RE.fullmatch(target[4:]) is None:
            raise LearnFromBugsError(f"invalid fix target: {target!r}")
        return True
    if proposal_type == "hook":
        if (
            not target.startswith("hook:")
            or not target[5:]
            or any(char in target[5:] for char in "\r\n")
        ):
            raise LearnFromBugsError(f"invalid hook target: {target!r}")
        return True
    return False


def _validate_test_target(target: str, root: Path | None) -> None:
    """Validate a Python or Rust test target; redirect other symbol targets."""
    path_target, separator, test_name = target.partition("::")
    suffix = Path(path_target).suffix
    if separator and suffix not in _TEST_TARGET_SUFFIXES:
        _validate_path_target(path_target, (), root)
        if _CHECK_SYMBOL_RE.fullmatch(test_name) is None:
            raise LearnFromBugsError(f"invalid test function target: {target!r}")
        check_target = f"check:{path_target}#{test_name}"
        raise LearnFromBugsError(
            f"non-Python test function target: {target!r}; use {check_target!r}"
        )
    if separator:
        symbol_pattern = _TEST_NAME_RE if suffix == ".py" else _CHECK_SYMBOL_RE
        if symbol_pattern.fullmatch(test_name) is None:
            raise LearnFromBugsError(f"invalid test function target: {target!r}")
    _validate_path_target(path_target, _TEST_TARGET_SUFFIXES, root)


def _validate_target(
    proposal_type: ProposalType, target: str, root: Path | None = None
) -> None:
    if _validate_fix_or_hook_target(proposal_type, target):
        return
    if proposal_type in {"lint", "test"} and target.startswith("check:"):
        _validate_check_target(target, root)
    elif proposal_type == "lint" and target.startswith("registration:"):
        name = target.removeprefix("registration:")
        if _FIX_TOKEN_RE.fullmatch(name) is None:
            raise LearnFromBugsError(f"invalid lint registration target: {target!r}")
    elif proposal_type == "lint" and target.startswith("module:"):
        _validate_path_target(target.removeprefix("module:"), (".py",), root)
    elif proposal_type in {"invariant", "guideline"}:
        path_target, _fragment = _validate_architectural_target(target)
        _validate_path_target(path_target, (".md",), root)
    elif proposal_type == "test":
        _validate_test_target(target, root)
    else:
        raise LearnFromBugsError(f"invalid {proposal_type} target: {target!r}")


def _proposal_from_json(payload: object, *, root: Path | None = None) -> Proposal:
    if not isinstance(payload, dict):
        raise LearnFromBugsError("proposal record must be an object")
    typed = cast("dict[str, object]", payload)
    required = {"id", "type", "target", "run_date", "status", "filed_issue"}
    if not required.issubset(typed):
        missing = ", ".join(sorted(required - typed.keys()))
        raise LearnFromBugsError(f"proposal record missing fields: {missing}")
    proposal_id = str(typed["id"])
    proposal_type_raw = str(typed["type"])
    status_raw = str(typed["status"])
    if _PROPOSAL_ID_RE.fullmatch(proposal_id) is None:
        raise LearnFromBugsError(f"invalid proposal id: {proposal_id!r}")
    if proposal_type_raw not in PROPOSAL_TYPES:
        raise LearnFromBugsError(f"invalid proposal type: {proposal_type_raw!r}")
    if status_raw not in PROPOSAL_STATUSES:
        raise LearnFromBugsError(f"invalid proposal status: {status_raw!r}")
    proposal_type = cast("ProposalType", proposal_type_raw)
    status = cast("ProposalStatus", status_raw)
    target = str(typed["target"])
    _validate_target(proposal_type, target, root)
    filed_raw = typed["filed_issue"]
    if filed_raw is None:
        filed_issue = None
    elif (
        isinstance(filed_raw, bool) or not isinstance(filed_raw, int) or filed_raw <= 0
    ):
        raise LearnFromBugsError(f"invalid filed issue: {filed_raw!r}")
    else:
        filed_issue = filed_raw
    return Proposal(
        id=proposal_id,
        type=proposal_type,
        target=target,
        run_date=_parse_date(typed["run_date"], field="run_date"),
        status=status,
        filed_issue=filed_issue,
    )


def load_proposals_jsonl(path: Path, *, root: Path) -> tuple[Proposal, ...]:
    """Load and reconcile a complete proposal JSONL artifact."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise LearnFromBugsError(f"cannot read proposals file: {exc}") from exc
    proposals: list[Proposal] = []
    by_id: dict[str, Proposal] = {}
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LearnFromBugsError(
                f"invalid proposal JSONL line {line_number}: {exc}"
            ) from exc
        proposal = _proposal_from_json(raw, root=root)
        prior = by_id.get(proposal.id)
        if prior is None:
            by_id[proposal.id] = proposal
            proposals.append(proposal)
            continue
        if (prior.type, prior.target, prior.run_date) != (
            proposal.type,
            proposal.target,
            proposal.run_date,
        ):
            raise LearnFromBugsError(
                f"conflicting stable proposal content for {proposal.id}"
            )
        if (
            prior.filed_issue
            and proposal.filed_issue
            and prior.filed_issue != proposal.filed_issue
        ):
            raise LearnFromBugsError(f"conflicting filed issues for {proposal.id}")
        merged = Proposal(
            id=prior.id,
            type=prior.type,
            target=prior.target,
            run_date=prior.run_date,
            status=prior.status if prior.status != "proposed" else proposal.status,
            filed_issue=proposal.filed_issue or prior.filed_issue,
        )
        by_id[proposal.id] = merged
        proposals[proposals.index(prior)] = merged
    return tuple(proposals)


def _proposals_from_state(
    typed: dict[str, object], schema_version: str
) -> tuple[Proposal, ...] | None:
    proposals_raw = cast(
        "list[object]", typed.get("proposals", []) if schema_version == "2" else []
    )
    try:
        proposals = tuple(_proposal_from_json(item) for item in proposals_raw)
    except LearnFromBugsError:
        return None
    if len({proposal.id for proposal in proposals}) != len(proposals):
        return None
    return proposals


def _state_from_json(payload: object) -> LearnFromBugsState | None:
    if not isinstance(payload, dict):
        return None
    typed = cast("dict[str, object]", payload)
    schema_version = str(typed.get("schema_version") or "")
    run_date = str(typed.get("run_date") or "")
    repo = str(typed.get("repo") or "")
    proposals = _proposals_from_state(typed, schema_version)
    if (
        schema_version not in {"1", "2"}
        or not run_date
        or not repo
        or proposals is None
    ):
        return None
    scan_started_at_raw = typed.get("scan_started_at")
    scan_started_at = str(scan_started_at_raw or "") or None
    return LearnFromBugsState(
        run_date=run_date,
        scan_started_at=scan_started_at,
        highest_closed_issue_number_scanned=_int_field(
            typed, "highest_closed_issue_number_scanned", 0
        ),
        repo=repo,
        search=str(typed.get("search") or ""),
        state=str(typed.get("state") or ""),
        selected_count=_int_field(typed, "selected_count", 0),
        proposals=proposals,
    )


def read_state(path: Path) -> LearnFromBugsState | None:
    """Read a durable state marker, returning ``None`` when unusable."""
    try:
        larch_io.assert_no_symlink_path_or_ancestors(path)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return _state_from_json(payload)


def _read_existing_state(path: Path) -> LearnFromBugsState | None:
    """Read a missing state marker as absent and reject every unusable marker."""
    try:
        larch_io.assert_no_symlink_path_or_ancestors(path)
        exists = path.exists()
    except OSError as exc:
        raise LearnFromBugsError(f"cannot inspect state marker: {exc}") from exc
    state = read_state(path)
    if exists and state is None:
        raise LearnFromBugsError("existing state marker is invalid or unsupported")
    return state


def _read_repo_state(root: Path, repo: str) -> LearnFromBugsState | None:
    """Read the repository marker and reject state for another repository."""
    state = _read_existing_state(state_path(root))
    if state is not None and state.repo != repo:
        raise LearnFromBugsError(
            "--repo does not match the durable learn-from-bugs state repository"
        )
    return state


def write_state(path: Path, state: LearnFromBugsState) -> None:
    """Atomically write a durable state marker after symlink rejection."""
    larch_io.assert_no_symlink_path_or_ancestors(path)
    larch_io.atomic_write(
        path,
        json.dumps(state.to_json(), indent=2, sort_keys=True) + "\n",
        create_parent=True,
        prefix=f".{path.name}.",
        nofollow=True,
    )


def _highest_issue_number(issues: list[dict[str, object]]) -> int:
    numbers: list[int] = []
    for issue in issues:
        raw = issue.get("number")
        if isinstance(raw, bool):
            continue
        if not isinstance(raw, (int, str)):
            continue
        try:
            numbers.append(int(raw))
        except (TypeError, ValueError):
            continue
    return max(numbers) if numbers else 0


def _issue_number(issue: Mapping[str, object]) -> int | None:
    """Return a positive issue number when the GitHub row supplies one."""
    raw = issue.get("number")
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        return None
    try:
        number = int(raw)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _in_prior_scan_window(issue: Mapping[str, object], highest_scanned: int) -> bool:
    """Return whether an issue belongs to the durable marker's prior window."""
    number = _issue_number(issue)
    return number is not None and number <= highest_scanned


# --- Digest extraction (offline, pure) --------------------------------------


def diagnostic_prefix(body: str) -> str:
    """Return the body up to the appended ``/design`` plan, or the whole body."""
    cuts = [
        match.start()
        for pattern in _BOUNDARY_PATTERNS
        for match in [pattern.search(body)]
        if match
    ]
    return body[: min(cuts)] if cuts else body


def _lines_with_starts(text: str) -> list[tuple[int, str]]:
    """Return ``(absolute_start, line_without_newline)`` pairs matching ``splitlines``."""
    result: list[tuple[int, str]] = []
    start = 0
    length = len(text)
    while start < length:
        nl = text.find("\n", start)
        if nl < 0:
            result.append((start, text[start:]))
            break
        line = text[start:nl].removesuffix("\r")
        result.append((start, line))
        start = nl + 1
    return result


def _fenced_line_indices(lines: list[str]) -> set[int]:
    """Return indices of lines inside fenced code (exclusive of fence markers).

    An unclosed fence counts as fenced through the end of ``lines``. A closer
    must use the opener's marker character, be at least as long, and carry no
    info-string suffix.
    """
    fenced: set[int] = set()
    open_at: int | None = None
    open_char = ""
    open_len = 0
    for index, line in enumerate(lines):
        match = _FENCE_MARKER_RE.match(line.strip())
        if open_at is None:
            if match is None:
                continue
            marker = match.group(1)
            open_at = index
            open_char = marker[0]
            open_len = len(marker)
            continue
        if match is None:
            continue
        marker = match.group(1)
        suffix = match.group(2)
        if marker[0] == open_char and len(marker) >= open_len and suffix.strip() == "":
            fenced.update(range(open_at + 1, index))
            open_at = None
    if open_at is not None:
        fenced.update(range(open_at + 1, len(lines)))
    return fenced


def _iter_diagnostic_sections(prefix: str) -> list[tuple[str, str]]:
    """Yield ``(normalized_heading, body)`` in document order; duplicates preserved.

    In addition to Markdown headings, recognize the bold labels used by the
    machine-filed test-smarts defect template.
    """
    positioned = _lines_with_starts(prefix)
    lines = [line for _, line in positioned]
    fenced = _fenced_line_indices(lines)
    # (normalized_name, match_start, content_start)
    heads: list[tuple[str, int, int]] = []
    for index, (line_start, line) in enumerate(positioned):
        if index in fenced:
            continue
        match = _HEADING_RE.match(line)
        if match is not None:
            name = match.group(1).replace("`", "").strip().lower()
            heads.append((name, line_start, line_start + match.end()))
            continue
        pseudo_match = _BOLD_PSEUDO_HEADING_RE.match(line)
        if pseudo_match is None:
            continue
        name = pseudo_match.group("name").lower()
        heads.append((name, line_start, line_start + pseudo_match.start("body")))
    out: list[tuple[str, str]] = []
    for index, (name, _match_start, content_start) in enumerate(heads):
        end = heads[index + 1][1] if index + 1 < len(heads) else len(prefix)
        out.append((name, prefix[content_start:end].strip()))
    return out


def _split_sections(prefix: str) -> dict[str, str]:
    """Split a diagnostic prefix into heading-named sections, ignoring fenced headings.

    Duplicate headings collapse to the last body (digest retention path). Origin
    extraction uses :func:`_iter_diagnostic_sections` to preserve duplicates.
    """
    return dict(_iter_diagnostic_sections(prefix))


def _parse_classification(value: str) -> BugClass | None:
    """Return the typed class from a template ``Classification`` section."""
    match: re.Match[str] | None = _CLASSIFICATION_VALUE_RE.match(value)
    if match is None:
        return None
    return BugClass(
        kind=match.group("kind").upper(),
        surface=match.group("surface").upper(),
    )


def _parse_harness_classification(value: str) -> BugClass | None:
    """Return the typed class from explicit test-harness metadata markers."""
    lines: list[str] = value.splitlines()
    fenced: set[int] = _fenced_line_indices(lines)
    diagnostic_text: str = "\n".join(
        line for index, line in enumerate(lines) if index not in fenced
    )
    kind_match: re.Match[str] | None = _HARNESS_ROOT_CAUSE_CLASS_RE.search(
        diagnostic_text
    )
    if kind_match is None:
        return None
    surface_match: re.Match[str] | None = _HARNESS_OWNING_SURFACE_RE.search(
        diagnostic_text, kind_match.end()
    )
    if surface_match is None:
        return None
    return BugClass(
        kind=kind_match.group("kind").upper(),
        surface=surface_match.group("surface").upper(),
    )


def _is_table_row(line: str) -> bool:
    """Recognize a Markdown or box-drawing table row without parsing its cells."""
    stripped: str = line.strip()
    if not stripped:
        return False
    if (
        stripped.startswith("|")
        and stripped.endswith("|")
        and stripped.count("|") >= TABLE_MIN_DELIMITERS
    ):
        return True
    box_count: int = len(_BOX_DRAWING_CHAR_RE.findall(stripped))
    return box_count * TABLE_DOMINANCE_MULTIPLIER >= len(stripped) or (
        box_count >= TABLE_MIN_DELIMITERS
        and "\u2500" <= stripped[0] <= "\u257f"
        and "\u2500" <= stripped[-1] <= "\u257f"
    )


def _elide_table_runs(text: str) -> str:
    """Replace multi-line table runs with one bounded diagnostic marker."""
    lines: list[str] = text.splitlines()
    elided: list[str] = []
    index = 0
    while index < len(lines):
        if not _is_table_row(lines[index]):
            elided.append(lines[index])
            index += 1
            continue
        start = index
        while index < len(lines) and _is_table_row(lines[index]):
            index += 1
        count = index - start
        if count == 1:
            elided.extend(lines[start:index])
        else:
            elided.append(f"[table elided: {count} lines]")
    return "\n".join(elided)


def _squeeze(text: str, cap: int) -> str:
    collapsed = re.sub(r"\n{2,}", "\n", text).strip()
    return collapsed[:cap] + ("…" if len(collapsed) > cap else "")


def _pick_sections(prefix: str) -> tuple[dict[str, str], bool, BugClass | None]:
    """Return sections, structured state, and parsed class for one diagnostic prefix."""
    found: dict[str, str] = _split_sections(prefix)
    classification: BugClass | None = _parse_classification(
        found.get("classification", "")
    ) or _parse_harness_classification(prefix)
    picked: dict[str, str] = {}
    seen_roots: set[str] = set()
    for want, cap in WANT_SECTIONS:
        root = want.split()[0]
        if want in found and root not in seen_roots:
            picked[want] = _squeeze(found[want], cap)
            seen_roots.add(root)
    if picked:
        return picked, True, classification
    if len(prefix.strip()) < TITLE_ONLY_PREFIX_MAX:
        return {"_title_only": ""}, False, classification
    return (
        {"_freeform": _squeeze(_elide_table_runs(prefix), FREEFORM_CAP)},
        False,
        classification,
    )


def _has_structured_want_sections(ordered: Sequence[tuple[str, str]]) -> bool:
    """True when ``_pick_sections`` would retain at least one WANT heading."""
    names = {name for name, _body in ordered}
    return any(want in names for want, _cap in WANT_SECTIONS)


def _origin_evidence(*, title: str, prefix: str) -> _OriginEvidence:
    """Return origin-scan texts and whether the diagnostic supplied a signal."""
    ordered = _iter_diagnostic_sections(prefix)
    sources: list[str] = [title]
    sources.extend(body for name, body in ordered if name.startswith("root cause"))
    # `_title_only`: title only; never scan the empty value text.
    if not _has_structured_want_sections(ordered) and len(prefix.strip()) >= TITLE_ONLY_PREFIX_MAX:
        sources.append(prefix)
    return _OriginEvidence(
        sources=tuple(sources),
        has_classification_signal=any(
            name == "classification" or name.startswith("root cause")
            for name, _body in ordered
        ),
    )


def _first_referenced_origin(text: str) -> tuple[int, int] | None:
    """Return ``(match_start, issue_ref)`` for the earliest referenced marker."""
    best_start: int | None = None
    best_ref: int | None = None
    for pattern in _ORIGIN_REF_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        start = match.start()
        ref = int(match.group(1))
        if best_start is None or start < best_start:
            best_start = start
            best_ref = ref
    return None if best_start is None or best_ref is None else (best_start, best_ref)


def _first_referenced_across_sources(sources: Sequence[str]) -> int | None:
    """Return the first referenced issue number in title-then-body source order."""
    best_source_index: int | None = None
    best_match_start: int | None = None
    best_ref: int | None = None
    for source_index, source in enumerate(sources):
        referenced = _first_referenced_origin(source)
        if referenced is None:
            continue
        match_start, ref = referenced
        if best_source_index is None or (source_index, match_start) < (
            best_source_index,
            best_match_start,
        ):
            best_source_index = source_index
            best_match_start = match_start
            best_ref = ref
    return best_ref


def _phrase_in_sources(sources: Sequence[str], phrases: Sequence[str]) -> bool:
    for source in sources:
        lowered = source.lower()
        if any(phrase in lowered for phrase in phrases):
            return True
    return False


def classify_origin(
    *, title: str, body: str, classification: BugClass | None = None
) -> Origin:
    """Classify origin from title plus unsqueezed diagnostic allowlist bodies.

    Precedence is global across sources: any referenced marker (first in
    title-then-body order) beats bare ``regression``, which beats ``spec-gap``
    phrases, which beat ``new-code`` phrases, which default to ``unknown``.
    Parsed machine-filed classifications are an additional diagnostic source.
    """
    prefix = diagnostic_prefix(body)
    normalized_title = _DONE_PREFIX_RE.sub("", title)
    parsed_classification = classification or _parse_classification(
        _split_sections(prefix).get("classification", "")
    ) or _parse_harness_classification(prefix)
    evidence = _origin_evidence(title=normalized_title, prefix=prefix)
    sources = evidence.sources
    classification_origin = (
        None
        if parsed_classification is None
        else _CLASSIFICATION_ORIGIN_KINDS.get(parsed_classification.kind)
    )

    ref = _first_referenced_across_sources(sources)
    if ref is not None:
        return Origin(kind="regression", ref=ref)
    if any(_BARE_REGRESSION_RE.search(source) for source in sources):
        return Origin(kind="regression", ref=None)
    if _phrase_in_sources(sources, _SPEC_GAP_PHRASES) or classification_origin == "spec-gap":
        return Origin(kind="spec-gap", ref=None)
    if _phrase_in_sources(sources, _NEW_CODE_PHRASES) or classification_origin == "new-code":
        return Origin(kind="new-code", ref=None)
    return Origin(
        kind="unknown",
        ref=None,
        unknown_reason=(
            "inconclusive"
            if evidence.has_classification_signal or parsed_classification is not None
            else "no-classification-signal"
        ),
    )


def parse_zones(zones_csv: str) -> tuple[str, ...]:
    """Split and trim a comma-separated zone list; reject empties."""
    if not zones_csv.strip():
        raise LearnFromBugsError("--zones requires at least one non-empty zone name")
    zones: list[str] = []
    for part in zones_csv.split(","):
        name = part.strip()
        if not name:
            raise LearnFromBugsError("--zones contains an empty zone name")
        zones.append(name)
    return tuple(zones)


def render_zones_search(zones: Sequence[str]) -> str:
    """Render the topical OR-group GitHub query for zone names."""
    if not zones:
        raise LearnFromBugsError("--zones requires at least one non-empty zone name")
    joined = " OR ".join(zones)
    return f"{BUG_PREFIX} ({joined}) in:title,body"


def resolve_zone_search(
    zones_csv: str,
    *,
    has_explicit_search: bool = False,
    has_verbal_search: bool = False,
) -> str:
    """Resolve ``--zones`` into a search query; reject multi-source combinations."""
    if has_explicit_search:
        raise LearnFromBugsError("--zones cannot be combined with --search")
    if has_verbal_search:
        raise LearnFromBugsError("--zones cannot be combined with verbal search text")
    return render_zones_search(parse_zones(zones_csv))


def _pct_one_decimal(count: int, total: int) -> str:
    if total <= 0:
        return "0.0"
    return f"{(count * 100) / total:.1f}"


def render_origin_headline(digests: Sequence[BugDigest]) -> str:
    """Render the mandatory Section 2 origin-distribution headline block."""
    selected = len(digests)
    counts: dict[OriginKind, int] = dict.fromkeys(ORIGIN_KINDS, 0)
    unknown_reason_counts: dict[UnknownOriginReason, int] = dict.fromkeys(
        _UNKNOWN_ORIGIN_REASONS, 0
    )
    chains: list[str] = []
    suspect_chains: list[str] = []
    for digest in digests:
        counts[digest.origin.kind] = counts[digest.origin.kind] + 1
        if digest.origin.kind == "unknown":
            unknown_reason = digest.origin.unknown_reason or "inconclusive"
            unknown_reason_counts[unknown_reason] = unknown_reason_counts[unknown_reason] + 1
        if digest.origin.kind != "regression" or digest.origin.ref is None:
            continue
        chain = f"#{digest.origin.ref} -> #{digest.number}"
        if digest.origin.ref == digest.number:
            suspect_chains.append(f"{chain} (suspect: self-reference)")
        else:
            chains.append(chain)

    lines: list[str] = [
        f"#### Origin distribution (selected={selected})",
    ]
    for kind in ORIGIN_KINDS:
        count = counts[kind]
        lines.append(f"- {kind}: {count} ({_pct_one_decimal(count, selected)}%)")
    if counts["unknown"]:
        for reason in _UNKNOWN_ORIGIN_REASONS:
            count = unknown_reason_counts[reason]
            label = _UNKNOWN_ORIGIN_REASON_LABELS[reason]
            lines.append(f"  - {label}: {count} ({_pct_one_decimal(count, selected)}%)")
    lines.append("#### Referenced regression chains")
    if chains or suspect_chains:
        lines.extend(f"- {item}" for item in chains)
        lines.extend(f"- {item}" for item in suspect_chains)
    else:
        lines.append("(none)")
    regression_count = counts["regression"]
    lines.append("#### Regression ratio")
    if selected == 0:
        lines.append("n/a (0/0)")
    else:
        lines.append(
            f"{regression_count}/{selected} ({_pct_one_decimal(regression_count, selected)}%)"
        )
    return "\n".join(lines) + "\n"


def _section2_body(report: str) -> str:
    section_match = _SECTION2_HEADING_RE.search(report)
    if section_match is None:
        raise LearnFromBugsError("report missing Root-cause clusters section heading")
    section_body = report[section_match.end() :]
    next_section = _NEXT_TOP_SECTION_RE.search(section_body)
    if next_section is not None:
        return section_body[: next_section.start()]
    return section_body


def _require_headline_first(section_body: str, headline: str) -> None:
    needle = headline.strip()
    if not needle:
        raise LearnFromBugsError("origin headline is empty")
    headline_pos = section_body.find(needle)
    if headline_pos < 0:
        needle = needle.rstrip("\n")
        headline_pos = section_body.find(needle)
    if headline_pos < 0:
        raise LearnFromBugsError(
            "generated origin headline must appear verbatim as the first block in Section 2"
        )
    if section_body[:headline_pos].strip():
        raise LearnFromBugsError(
            "generated origin headline must appear before cluster rows in Section 2"
        )


def _validate_prose_only_markers(report: str) -> None:
    start = 0
    while True:
        idx = report.find(PROSE_ONLY_MARKER, start)
        if idx < 0:
            return
        window_start = max(0, idx - 400)
        window_end = min(len(report), idx + len(PROSE_ONLY_MARKER) + 800)
        window = report[window_start:window_end]
        for citation in _PROSE_ONLY_CITATIONS:
            if citation not in window:
                raise LearnFromBugsError(
                    f"prose-only marker requires citation {citation} near the marker"
                )
        if _MECHANICAL_ALT_RE.search(window) is None:
            raise LearnFromBugsError(
                "prose-only marker requires a named lint, hook, or invariant-test "
                "alternative, or an explicit no-mechanical-alternative statement"
            )
        start = idx + len(PROSE_ONLY_MARKER)


def validate_report_contract(*, report: str, expected_headline: str) -> None:
    """Validate Step 4 report grammar for the generated headline and prose-only markers.

    Raises ``LearnFromBugsError`` on the first contract defect.
    """
    _require_headline_first(_section2_body(report), expected_headline)
    _validate_prose_only_markers(report)


def build_digest(issue: Mapping[str, object]) -> BugDigest:
    """Compress one raw issue row (from ``gh issue list --json``) to a digest."""
    body = str(issue.get("body") or "")
    prefix = diagnostic_prefix(body)
    title = _DONE_PREFIX_RE.sub("", str(issue.get("title") or ""))
    sections, structured, classification = _pick_sections(prefix)
    origin = classify_origin(title=title, body=body, classification=classification)
    closed_at = str(issue.get("closedAt") or issue.get("closed_at") or "")[:10]
    number_raw = issue.get("number")
    number = (
        int(number_raw)
        if isinstance(number_raw, (int, str)) and str(number_raw).isdigit()
        else 0
    )
    return BugDigest(
        number=number,
        title=title,
        closed_at=closed_at,
        url=str(issue.get("url") or ""),
        state=str(issue.get("state") or ""),
        structured=structured,
        prefix_chars=len(prefix),
        sections=sections,
        origin=origin,
        classification=classification,
    )


def _serialize_digest(digest: BugDigest) -> str:
    """Serialize one digest record with an ASCII-safe character count."""
    return json.dumps(digest.to_json(), ensure_ascii=True) + "\n"


def _estimate_digest_tokens(serialized_chars: int) -> int:
    """Return a conservative token estimate for an ASCII-safe digest payload."""
    return (serialized_chars + DIGEST_CHARS_PER_TOKEN_ESTIMATE - 1) // DIGEST_CHARS_PER_TOKEN_ESTIMATE


def _write_digest_chunks(
    out_dir: Path, digests: Sequence[BugDigest]
) -> tuple[tuple[Path, ...], int]:
    """Write numbered JSONL chunks below the conservative Read-token budget."""
    records: list[str] = [_serialize_digest(digest) for digest in digests]
    chunk_char_limit = DIGEST_CHUNK_TOKEN_LIMIT * DIGEST_CHARS_PER_TOKEN_ESTIMATE
    chunks: list[list[str]] = [[]]
    chunk_chars = 0
    for record in records:
        if len(record) > chunk_char_limit:
            raise LearnFromBugsError("digest record exceeds the configured chunk token limit")
        if chunks[-1] and chunk_chars + len(record) > chunk_char_limit:
            chunks.append([])
            chunk_chars = 0
        chunks[-1].append(record)
        chunk_chars += len(record)

    paths: list[Path] = []
    for index, chunk in enumerate(chunks, start=1):
        path = out_dir / f"digest-{index:02d}.jsonl"
        larch_io.atomic_write(
            path,
            "".join(chunk),
            prefix=f".{path.name}.",
            nofollow=True,
        )
        paths.append(path)
    return tuple(paths), sum(len(record) for record in records)


# --- Issue listing (through the Runner seam) --------------------------------


_LEARN_ISSUE_LIST_FIELDS: Final = (
    "number",
    "title",
    "body",
    "closedAt",
    "url",
    "state",
)


def list_issues(
    runner: Runner, *, search: str, state: str, limit: int, repo: str
) -> list[dict[str, object]]:
    try:
        parsed = gh.issue_list_read(
            runner,
            repo=repo,
            state=state,
            fields=_LEARN_ISSUE_LIST_FIELDS,
            search=search,
            limit=limit,
        )
    except ShipError as exc:
        raise LearnFromBugsError(f"gh issue list failed: {exc}") from exc
    return [
        cast("dict[str, object]", row)
        for row in parsed
        if isinstance(row, dict)
    ]


# --- Coverage index (offline, pure) -----------------------------------------


def _scan_marked_ids_from_lines(
    lines: list[str], pattern: re.Pattern[str]
) -> tuple[tuple[str, str], ...]:
    fenced = _fenced_line_indices(lines)
    entries: list[tuple[str, str]] = []
    for index, line in enumerate(lines):
        if index in fenced:
            continue
        match = pattern.match(line)
        if match is not None:
            entries.append((match.group(1), match.group(2)))
    return tuple(entries)


def _scan_marked_ids(
    path: Path, pattern: re.Pattern[str]
) -> tuple[tuple[str, str], ...]:
    if not path.is_file():
        return ()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return _scan_marked_ids_from_lines(lines, pattern)


def _scan_guideline_entries(path: Path) -> tuple[tuple[str, str], ...]:
    """Read named guideline IDs, or generic h2/h3 headings when no IDs exist."""
    if not path.is_file():
        return ()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    marked = _scan_marked_ids_from_lines(lines, GUIDELINE_HEADING_RE)
    if marked:
        return marked
    fenced = _fenced_line_indices(lines)
    entries: list[tuple[str, str]] = []
    for index, line in enumerate(lines):
        if index in fenced:
            continue
        match = _UNMARKED_GUIDELINE_HEADING_RE.match(line)
        if match is not None:
            heading = match.group("title")
            entries.append((heading, heading))
    return tuple(entries)


def _guidelines_index_status(
    path: Path, entries: Sequence[tuple[str, str]]
) -> GuidelinesIndexStatus:
    if not path.is_file():
        return "missing"
    return "indexed" if entries else "empty"


def _scan_lint_names(directory: Path, glob: str, prefix: str) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    return tuple(
        sorted(
            path.stem for path in directory.glob(glob) if path.stem.startswith(prefix)
        )
    )


def coverage_index(root: Path) -> CoverageIndex:
    """Scan the repo root for existing guidelines, invariants, and lints."""
    guidelines_path = root / GUIDELINES_FILENAME
    guidelines = _scan_guideline_entries(guidelines_path)
    return CoverageIndex(
        guidelines=guidelines,
        invariants=_scan_marked_ids(
            root / INVARIANTS_FILENAME, INVARIANT_HEADING_RE
        ),
        python_lints=_scan_lint_names(
            root / "python" / "larch" / "lint", "lint_*.py", "lint_"
        ),
        script_lints=_scan_lint_names(root / "scripts", "lint-*", "lint-"),
        guidelines_index_status=_guidelines_index_status(guidelines_path, guidelines),
    )


# --- Orchestration cores + cli mains ----------------------------------------


def run_prepare(runner: Runner, request: PrepareRequest) -> dict[str, object]:
    """Fetch, digest, and coverage-index; write artifacts; return KV stats."""
    repo = resolve_repo(runner, request.repo_explicit)
    prior_state = _read_repo_state(request.root, repo)
    scan_started_at = _utc_now_iso()
    raw_issues: list[dict[str, object]] = list_issues(
        runner,
        search=request.search,
        state=request.state,
        limit=request.limit,
        repo=repo,
    )
    issues = [
        issue for issue in raw_issues if bug_title_match(str(issue.get("title") or ""))
    ]
    filtered_non_bug = len(raw_issues) - len(issues)
    prior_highest: int = (
        prior_state.highest_closed_issue_number_scanned if prior_state is not None else 0
    )
    issues_previously_scanned: int = (
        sum(_in_prior_scan_window(issue, prior_highest) for issue in issues)
        if prior_state is not None
        else 0
    )
    incremental: bool = (
        prior_state is not None and not request.full and not request.search_explicit
    )
    if incremental:
        issues = [
            issue for issue in issues if not _in_prior_scan_window(issue, prior_highest)
        ]
    highest_closed_issue_number_scanned = _highest_issue_number(raw_issues)
    digests = [build_digest(issue) for issue in issues]
    out_dir = request.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir = out_dir.resolve()
    digest_paths, digest_chars = _write_digest_chunks(out_dir, digests)
    coverage = coverage_index(request.root)
    coverage_path = out_dir / "coverage-index.json"
    larch_io.atomic_write(
        coverage_path,
        json.dumps(coverage.to_json(), indent=2) + "\n",
        prefix=f".{coverage_path.name}.",
        nofollow=True,
    )
    headline = render_origin_headline(digests)
    headline_path = out_dir / "origin-headline.md"
    larch_io.atomic_write(
        headline_path,
        headline,
        prefix=f".{headline_path.name}.",
        nofollow=True,
    )
    structured = sum(1 for digest in digests if digest.structured)
    return {
        "RUN_DIR": str(out_dir),
        "DIGEST_PATH": str(digest_paths[0]),
        "DIGEST_PATHS": tuple(str(path) for path in digest_paths),
        "COVERAGE_INDEX_PATH": str(coverage_path),
        "ORIGIN_HEADLINE_PATH": str(headline_path),
        "REPO": repo,
        "SEARCH": request.search,
        "STATE": request.state,
        "SCAN_STARTED_AT": scan_started_at,
        "HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED": highest_closed_issue_number_scanned,
        "ISSUES_SELECTED": len(digests),
        "ISSUES_PREVIOUSLY_SCANNED": issues_previously_scanned,
        "INCREMENTAL": str(incremental).lower(),
        "ISSUES_FILTERED_NON_BUG": filtered_non_bug,
        "STRUCTURED": structured,
        "FREEFORM_OR_TITLE_ONLY": len(digests) - structured,
        "DIGEST_CHARS": digest_chars,
        "DIGEST_TOKENS_EST": _estimate_digest_tokens(digest_chars),
        "GUIDELINES_INDEXED": len(coverage.guidelines),
        _GUIDELINES_INDEX_STATUS_KEY: coverage.guidelines_index_status,
        "INVARIANTS_INDEXED": len(coverage.invariants),
        "PYTHON_LINTS_INDEXED": len(coverage.python_lints),
        "SCRIPT_LINTS_INDEXED": len(coverage.script_lints),
    }


def _print_kv(pairs: Mapping[str, object]) -> None:
    for key, value in pairs.items():
        print(f"{key}={value}")


def _print_prepare_kv(pairs: Mapping[str, object]) -> None:
    """Emit the prepare grammar, preserving one ``DIGEST_PATH`` per chunk."""
    for key, value in pairs.items():
        if key == "DIGEST_PATH":
            digest_paths = cast("tuple[str, ...]", pairs["DIGEST_PATHS"])
            for path in digest_paths:
                print(f"DIGEST_PATH={path}")
        elif key != "DIGEST_PATHS":
            print(f"{key}={value}")


def prepare_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="learn-from-bugs prepare", allow_abbrev=False)
    parser.add_argument("--search", default=DEFAULT_SEARCH)
    parser.add_argument("--state", default=DEFAULT_STATE)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--repo", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--full", action="store_true")
    search_explicit: bool = any(
        token == "--search" or token.startswith("--search=") for token in argv
    )
    args = parser.parse_args(argv)
    request = PrepareRequest(
        search=args.search,
        search_explicit=search_explicit,
        state=args.state,
        limit=args.limit,
        repo_explicit=args.repo,
        out_dir=Path(args.out),
        root=Path(args.root),
        full=args.full,
    )
    _print_prepare_kv(run_prepare(_runner(), request))
    return 0


def coverage_index_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="learn-from-bugs coverage-index")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    coverage = coverage_index(Path(args.root))
    payload = json.dumps(coverage.to_json(), indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


def _lint_target_adopted(proposal: Proposal, root: Path) -> bool:
    if proposal.target.startswith("module:"):
        return _safe_relative_path(
            root, proposal.target.removeprefix("module:"), (".py",)
        ).is_file()
    name = proposal.target.removeprefix("registration:")
    cli_path = _safe_relative_path(root, "python/larch/cli.py", (".py",))
    text = cli_path.read_text(encoding="utf-8") if cli_path.is_file() else ""
    try:
        module = ast.parse(text)
    except SyntaxError:
        return False
    for node in module.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        if not any(
            isinstance(target, ast.Name) and target.id == "_REGISTRY"
            for target in targets
        ) or not isinstance(node.value, ast.Dict):
            continue
        for key in node.value.keys:
            if not isinstance(key, ast.Tuple) or len(key.elts) != REGISTRY_KEY_LENGTH:
                continue
            domain, command = key.elts
            if (
                isinstance(domain, ast.Constant)
                and domain.value == "lint"
                and isinstance(command, ast.Constant)
                and command.value == name
            ):
                return True
    return False


def _architectural_target_adopted(proposal: Proposal, root: Path) -> bool:
    raw_path, fragment = _validate_architectural_target(proposal.target)
    path = _safe_relative_path(root, raw_path, (".md",))
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    fenced = _fenced_line_indices(lines)
    for index, line in enumerate(lines):
        if index in fenced or not line.startswith("#"):
            continue
        heading = line.lstrip("#").strip()
        identifier = heading.split(":", 1)[0]
        if fragment in {heading, identifier}:
            return True
    return False


def _symbol_target_adopted(path: Path, symbol: str) -> bool:
    """Return whether one exact identifier occurs in a repository file."""
    return re.search(
        rf"\b{re.escape(symbol)}\b", path.read_text(encoding="utf-8")
    ) is not None


def _test_target_adopted(proposal: Proposal, root: Path) -> bool:
    raw_path, separator, test_name = proposal.target.partition("::")
    path = _safe_relative_path(root, raw_path, _TEST_TARGET_SUFFIXES)
    if not path.is_file():
        return False
    if not separator:
        return True
    if path.suffix == ".rs":
        return _symbol_target_adopted(path, test_name)
    return (
        re.search(
            rf"^def\s+{re.escape(test_name)}\s*\(",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        is not None
    )


def _normalized_hook_command(command: str, root: Path) -> str:
    for prefix in ("${CLAUDE_PLUGIN_ROOT}/", "$CLAUDE_PLUGIN_ROOT/"):
        if command.startswith(prefix):
            command = command.removeprefix(prefix)
            break
    command_path = Path(command)
    try:
        return command_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return command_path.as_posix()


def _hook_value_matches(value: object, token: str, root: Path, key: str = "") -> bool:
    if isinstance(value, dict):
        return any(
            _hook_value_matches(item, token, root, str(name)) for name, item in value.items()  # type: ignore[reportUnknownArgumentType, reportUnknownVariableType, reportUnknownLambdaType]  # reason: dict.items() yields Unknown in recursive type checker
        )
    if isinstance(value, list):
        return any(
            _hook_value_matches(item, token, root, key) for item in value  # type: ignore[reportUnknownArgumentType, reportUnknownVariableType]  # reason: list iteration yields Unknown in recursive type checker
        )
    if isinstance(value, str):
        if key == "matcher":
            return value == token
        if key == "command":
            try:
                arguments = shlex.split(value) if value.strip() else []
            except ValueError:
                arguments = []
            return any(
                _normalized_hook_command(argument, root) == token
                for argument in arguments
            )
    return False


def _hook_target_adopted(proposal: Proposal, root: Path) -> bool:
    hooks_path = _safe_relative_path(root, "hooks/hooks.json", (".json",))
    if not hooks_path.is_file():
        return False
    try:
        hooks_payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LearnFromBugsError(f"invalid hooks configuration: {exc}") from exc
    return _hook_value_matches(
        hooks_payload, proposal.target.removeprefix("hook:"), root
    )


def _check_target_adopted(proposal: Proposal, root: Path) -> bool:
    """Return whether an exact repository-hosted check symbol exists."""
    raw_path, symbol = _validate_check_target(proposal.target, root)
    path = _safe_relative_path(root, raw_path, ())
    if not path.is_file():
        return False
    return _symbol_target_adopted(path, symbol)


def _repository_target_adopted(proposal: Proposal, root: Path) -> bool:
    checkers = {
        "lint": _lint_target_adopted,
        "invariant": _architectural_target_adopted,
        "guideline": _architectural_target_adopted,
        "hook": _hook_target_adopted,
        "test": _test_target_adopted,
    }
    if proposal.type == "fix":
        return False
    if proposal.target.startswith("check:"):
        return _check_target_adopted(proposal, root)
    return checkers[proposal.type](proposal, root)


def _filed_issue_status(
    runner: Runner, proposal: Proposal, repo: str
) -> ProposalStatus | None:
    """Return a decisive filed-issue status, or None when closure is not decisive about adoption."""
    assert proposal.filed_issue is not None
    result = gh.command(runner,  # lint-subprocess-via-runner: ok local gh issue view with JSON response
        [
            "issue",
            "view",
            str(proposal.filed_issue),
            "--repo",
            repo,
            "--json",
            "number,state,stateReason",
        ]
    )
    if result.returncode != 0:
        raise LearnFromBugsError(result.stderr.strip() or "gh issue view failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LearnFromBugsError(f"gh issue view returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LearnFromBugsError("gh issue view returned mismatched issue data")
    typed = cast("dict[str, object]", payload)
    if not isinstance(typed.get("number"), int) or typed.get("number") != proposal.filed_issue:  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # reason: typed.get() on dict[str, object] yields Unknown
        raise LearnFromBugsError("gh issue view returned mismatched issue data")
    state = str(typed.get("state") or "").upper()  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # reason: typed.get() on dict[str, object] yields Unknown
    reason = str(typed.get("stateReason") or "").upper()  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # reason: typed.get() on dict[str, object] yields Unknown
    if state == "OPEN":
        return "pending"
    if state != "CLOSED":
        raise LearnFromBugsError("gh issue view returned an unknown issue state")
    if reason == "NOT_PLANNED":
        return "orphaned"
    if reason == "COMPLETED":
        return "adopted"
    if reason == "DUPLICATE":
        return None
    raise LearnFromBugsError("gh issue view returned an unknown closed issue reason")


def _adoption_evidence(
    *,
    status: ProposalStatus,
    target_verified: bool,
    filed_issue_status: ProposalStatus | None,
) -> AdoptionEvidence | None:
    """Classify the evidence supporting an adopted proposal's current status."""
    if status != "adopted":
        return None
    if target_verified and filed_issue_status == "adopted":
        return "both"
    if target_verified:
        return "target-verified"
    if filed_issue_status == "adopted":
        return "issue-closed-only"
    raise LearnFromBugsError("adopted proposal has no adoption evidence")


def check_proposals(
    runner: Runner, proposals: tuple[Proposal, ...], root: Path, repo: str
) -> tuple[Proposal, ...]:
    """Refresh proposal lifecycle status against GitHub and repository evidence."""
    checked: list[Proposal] = []
    for proposal in proposals:
        _validate_target(proposal.type, proposal.target, root)
        target_verified: bool = _repository_target_adopted(proposal, root)
        filed_issue_status: ProposalStatus | None = None
        status: ProposalStatus
        if proposal.filed_issue is not None:
            filed_issue_status = _filed_issue_status(runner, proposal, repo)
        if filed_issue_status is not None:
            status = filed_issue_status
        elif target_verified:
            status = "adopted"
        elif proposal.status in {"adopted", "orphaned"}:
            status = "orphaned"
        else:
            status = "pending"
        checked.append(
            Proposal(
                id=proposal.id,
                type=proposal.type,
                target=proposal.target,
                run_date=proposal.run_date,
                status=status,
                filed_issue=proposal.filed_issue,
                adoption_evidence=_adoption_evidence(
                    status=status,
                    target_verified=target_verified,
                    filed_issue_status=filed_issue_status,
                ),
            )
        )
    return tuple(checked)


def render_adoption_summary(
    proposals: tuple[Proposal, ...], today: date | None = None
) -> str:
    """Render deterministic proposal adoption statistics."""
    adopted = sorted(
        (item for item in proposals if item.status == "adopted"),
        key=lambda item: (item.run_date, item.id),
    )
    counts = {
        status: sum(item.status == status for item in proposals)
        for status in ("adopted", "pending", "orphaned")
    }
    evidence_counts: dict[AdoptionEvidence, int] = {
        kind: sum(
            item.status == "adopted" and item.adoption_evidence == kind
            for item in proposals
        )
        for kind in ADOPTION_EVIDENCE_KINDS
    }
    unavailable_evidence = len(adopted) - sum(evidence_counts.values())
    evidence_parts: list[str] = [
        f"{evidence_counts[kind]} {kind}"
        for kind in ADOPTION_EVIDENCE_KINDS
        if evidence_counts[kind]
    ]
    if unavailable_evidence:
        evidence_parts.append(f"{unavailable_evidence} unavailable")
    evidence_rollup: str = ", ".join(evidence_parts)
    denominator = sum(counts.values())
    rate = 0.0 if denominator == 0 else counts["adopted"] / denominator * 100
    adopted_line = f"- Adopted: {counts['adopted']}"
    if evidence_rollup:
        adopted_line += f" ({evidence_rollup})"
    lines = [
        "## Proposal adoption",
        "",
        adopted_line,
        f"- Pending: {counts['pending']}",
        f"- Orphaned: {counts['orphaned']}",
        f"- Adoption rate: {rate:.1f}%",
    ]
    lines.extend(["", "### Adoption evidence", ""])
    if not adopted:
        lines.append("None.")
    else:
        for proposal in adopted:
            evidence = proposal.adoption_evidence or "unavailable"
            lines.append(f"- `{proposal.id}`: `{evidence}`")
    pending = sorted(
        (item for item in proposals if item.status == "pending"),
        key=lambda item: (item.run_date, item.id),
    )
    lines.extend(["", "### Oldest pending", ""])
    if not pending:
        lines.append("None.")
        return "\n".join(lines) + "\n"
    current = today or datetime.now(UTC).date()
    for proposal in pending[:5]:
        age = max(0, (current - date.fromisoformat(proposal.run_date[:10])).days)
        lines.append(f"- `{proposal.id}`: {age} days, `{proposal.target}`")
    return "\n".join(lines) + "\n"


def pending_proposal_by_id(
    proposals: tuple[Proposal, ...], proposal_id: str
) -> Proposal | None:
    """Return a matching unresolved proposal for residual deduplication."""
    for proposal in proposals:
        if proposal.id == proposal_id and proposal.status in {"proposed", "pending"}:
            return proposal
    return None


def reconcile_proposals(
    prior: tuple[Proposal, ...],
    residuals: tuple[Proposal, ...],
    base: tuple[Proposal, ...] = (),
) -> tuple[Proposal, ...]:
    """Three-way merge published state with this run's refreshed residuals.

    ``prior`` is the freshly fetched default-branch state, ``residuals`` is this
    run's refreshed history plus any genuinely new proposals, and ``base`` is the
    state as this run observed it at scan start. When a published status still
    equals its scan-start base, this run's refresh is applied; when it has
    diverged from base, a concurrent publication changed it and the published
    status is kept. An empty ``base`` preserves the prior keep-published
    behavior.
    """
    base_status_by_id = {proposal.id: proposal.status for proposal in base}
    out = list(prior)
    positions = {proposal.id: index for index, proposal in enumerate(out)}
    for residual in residuals:
        index = positions.get(residual.id)
        if index is None:
            positions[residual.id] = len(out)
            out.append(residual)
            continue
        historical = out[index]
        if (historical.type, historical.target, historical.run_date) != (
            residual.type,
            residual.target,
            residual.run_date,
        ):
            raise LearnFromBugsError(
                f"conflicting stable proposal content for {residual.id}"
            )
        if (
            historical.filed_issue
            and residual.filed_issue
            and historical.filed_issue != residual.filed_issue
        ):
            raise LearnFromBugsError(f"conflicting filed issues for {residual.id}")
        scan_start_status = base_status_by_id.get(residual.id)
        published_unchanged = (
            scan_start_status is not None and historical.status == scan_start_status
        )
        status = residual.status if published_unchanged else historical.status
        out[index] = Proposal(
            id=historical.id,
            type=historical.type,
            target=historical.target,
            run_date=historical.run_date,
            status=status,
            filed_issue=historical.filed_issue or residual.filed_issue,
        )
    return tuple(out)


def check_proposals_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="learn-from-bugs check-proposals", allow_abbrev=False
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--proposals-out", required=True)
    parser.add_argument("--adoption-out", required=True)
    parser.add_argument("--base-proposals-out")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    state = _read_repo_state(root, args.repo)
    proposals = () if state is None else state.proposals
    checked = check_proposals(_runner(), proposals, root, args.repo)
    raw_proposals_out = Path(args.proposals_out).expanduser()
    proposals_out = raw_proposals_out.parent.resolve() / raw_proposals_out.name
    raw_adoption_out = Path(args.adoption_out).expanduser()
    adoption_out = raw_adoption_out.parent.resolve() / raw_adoption_out.name
    larch_io.atomic_write(
        proposals_out,
        "".join(
            json.dumps(item.to_json(include_adoption_evidence=True)) + "\n"
            for item in checked
        ),
        prefix=f".{proposals_out.name}.",
        nofollow=True,
    )
    larch_io.atomic_write(
        adoption_out,
        render_adoption_summary(checked),
        prefix=f".{adoption_out.name}.",
        nofollow=True,
    )
    rows: dict[str, object] = {
        "PROPOSALS_COUNT": len(checked),
        "PROPOSALS_ADOPTED": sum(item.status == "adopted" for item in checked),
        "PROPOSALS_PENDING": sum(item.status == "pending" for item in checked),
        "PROPOSALS_ORPHANED": sum(item.status == "orphaned" for item in checked),
        "CHECKED_PROPOSALS_PATH": str(proposals_out),
        "ADOPTION_SUMMARY_PATH": str(adoption_out),
    }
    if args.base_proposals_out:
        # Persist the pre-refresh (scan-start) proposals so that ``write-state``
        # can three-way merge and keep this run's refreshed statuses without
        # clobbering genuinely concurrent publications.
        raw_base_out = Path(args.base_proposals_out).expanduser()
        base_out = raw_base_out.parent.resolve() / raw_base_out.name
        larch_io.atomic_write(
            base_out,
            "".join(json.dumps(item.to_json()) + "\n" for item in proposals),
            prefix=f".{base_out.name}.",
            nofollow=True,
        )
        rows["BASE_PROPOSALS_PATH"] = str(base_out)
    _print_kv(rows)
    return 0


def read_state_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="learn-from-bugs read-state", allow_abbrev=False
    )
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    path = state_path(Path(args.root))
    state = read_state(path)
    if state is None:
        _print_kv(
            {
                "LEARN_FROM_BUGS_STATE_FOUND": "false",
                "STATE_RELPATH": config.LEARN_FROM_BUGS_STATE_RELPATH,
                "STATE_PATH": str(path),
            }
        )
        return 0
    rows: dict[str, object] = {
        "LEARN_FROM_BUGS_STATE_FOUND": "true",
        "STATE_RELPATH": config.LEARN_FROM_BUGS_STATE_RELPATH,
        "STATE_PATH": str(path),
        "RUN_DATE": state.run_date,
        "REPO": state.repo,
        "SEARCH": state.search,
        "STATE": state.state,
        "SELECTED_COUNT": state.selected_count,
        "HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED": state.highest_closed_issue_number_scanned,
        "SCHEMA_VERSION": state.schema_version,
        "PROPOSAL_COUNT": len(state.proposals),
    }
    if state.scan_started_at:
        rows["SCAN_STARTED_AT"] = state.scan_started_at
    _print_kv(rows)
    return 0


def write_state_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="learn-from-bugs write-state", allow_abbrev=False
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--search", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--selected-count", type=int, required=True)
    parser.add_argument(
        "--highest-closed-issue-number-scanned", type=int, required=True
    )
    parser.add_argument("--run-date", required=True)
    parser.add_argument("--scan-started-at", required=True)
    parser.add_argument("--proposals-file")
    parser.add_argument("--base-proposals-file")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    path = state_path(root)
    try:
        snapshot = analysis_state.read_snapshot(path)
    except analysis_state.AnalysisStateError as exc:
        raise LearnFromBugsError(str(exc)) from exc
    existing = _read_existing_state(path)
    if args.proposals_file:
        proposals = load_proposals_jsonl(Path(args.proposals_file), root=root)
        if existing is not None:
            # The state branch starts from a freshly fetched default branch.
            # Three-way merge against the scan-start base so this run's refreshed
            # lifecycle statuses survive, while statuses that diverged from base
            # (genuinely concurrent publications) are retained.
            base_proposals: tuple[Proposal, ...] = ()
            if args.base_proposals_file:
                base_proposals = load_proposals_jsonl(
                    Path(args.base_proposals_file), root=root
                )
            proposals = reconcile_proposals(
                existing.proposals, proposals, base_proposals
            )
    elif existing is not None and existing.proposals:
        raise LearnFromBugsError("--proposals-file is required to preserve proposal history")
    else:
        proposals = ()
    state = LearnFromBugsState(
        run_date=args.run_date,
        scan_started_at=args.scan_started_at,
        highest_closed_issue_number_scanned=args.highest_closed_issue_number_scanned,
        repo=args.repo,
        search=args.search,
        state=args.state,
        selected_count=args.selected_count,
        proposals=proposals,
    )
    payload = json.dumps(state.to_json(), indent=2, sort_keys=True) + "\n"
    try:
        digest = analysis_state.write_bytes(
            path, payload.encode("utf-8"), expected_digest=snapshot.digest
        )
    except analysis_state.AnalysisStateError as exc:
        raise LearnFromBugsError(str(exc)) from exc
    _print_kv(
        {
            "STATE_RELPATH": config.LEARN_FROM_BUGS_STATE_RELPATH,
            "STATE_PATH": str(path),
            "RUN_DATE": state.run_date,
            "SCAN_STARTED_AT": state.scan_started_at or "",
            "HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED": state.highest_closed_issue_number_scanned,
            "SCHEMA_VERSION": state.schema_version,
            "PROPOSAL_COUNT": len(state.proposals),
            "STATE_DIGEST": digest,
        }
    )
    return 0


def verify_origin_main(argv: list[str]) -> int:
    """Fail closed unless the checkout's ``origin`` remote identifies ``--repo``.

    The state-publication fence pushes and admin-merges through ``origin`` on the
    ``--repo`` given to ``gh``. This guard mechanically confirms that ``origin``
    and ``--repo`` name the same GitHub repository before any branch is created,
    so a ``--root`` whose origin points elsewhere cannot land the state branch in
    one repository while a stale same-named PR is reused on another.
    """
    parser = argparse.ArgumentParser(
        prog="learn-from-bugs verify-origin", allow_abbrev=False
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    origin = gh.remote_repo(_runner(), "origin", cwd=str(root))
    if origin is None:
        raise LearnFromBugsError(
            "state publication requires the origin remote to resolve to a GitHub "
            "OWNER/REPO slug"
        )
    if origin.lower() != args.repo.lower():
        raise LearnFromBugsError(
            f"origin remote {origin!r} does not identify publication repository "
            f"{args.repo!r}"
        )
    _print_kv(
        {
            "ORIGIN_REPO": origin,
            "PUBLICATION_REPO": args.repo,
            "ORIGIN_MATCHES_REPO": "true",
        }
    )
    return 0


def resolve_zones_main(argv: list[str]) -> int:
    """Emit ``RESOLVED_SEARCH=<query>`` for a valid ``--zones`` value."""
    parser = argparse.ArgumentParser(prog="learn-from-bugs resolve-zones", allow_abbrev=False)
    parser.add_argument("--zones", required=True)
    parser.add_argument(
        "--has-explicit-search",
        action="store_true",
        help="Set when --search was also present; forces a multi-source rejection.",
    )
    parser.add_argument(
        "--has-verbal-search",
        action="store_true",
        help="Set when verbal search text was also present; forces a multi-source rejection.",
    )
    args = parser.parse_args(argv)
    try:
        query = resolve_zone_search(
            args.zones,
            has_explicit_search=bool(args.has_explicit_search),
            has_verbal_search=bool(args.has_verbal_search),
        )
    except LearnFromBugsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print_kv({"RESOLVED_SEARCH": query})
    return 0


def validate_report_main(argv: list[str]) -> int:
    """Validate a Step 4 report against the prepared origin headline."""
    parser = argparse.ArgumentParser(prog="learn-from-bugs validate-report", allow_abbrev=False)
    parser.add_argument("--report", required=True)
    parser.add_argument("--headline", required=True)
    args = parser.parse_args(argv)
    report_path = Path(args.report)
    headline_path = Path(args.headline)
    if not report_path.is_file():
        print(f"report not found: {report_path}", file=sys.stderr)
        return 2
    if not headline_path.is_file():
        print(f"headline not found: {headline_path}", file=sys.stderr)
        return 2
    report = report_path.read_text(encoding="utf-8", errors="replace")
    headline = headline_path.read_text(encoding="utf-8", errors="replace")
    try:
        validate_report_contract(report=report, expected_headline=headline)
    except LearnFromBugsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print_kv({"REPORT_CONTRACT": "pass"})
    return 0


def _read_filing_tsv(path: Path, *, label: str) -> list[tuple[int, str]]:
    """Read one bounded filing TSV without normalizing malformed rows."""
    if path.is_symlink() or not path.is_file():
        raise LearnFromBugsError(f"{label} is not a regular file: {path}")
    if path.stat().st_size > config.ISSUE_INTRA_BATCH_DEPS_MAX_BYTES:
        raise LearnFromBugsError(
            f"{label} exceeds {config.ISSUE_INTRA_BATCH_DEPS_MAX_BYTES} bytes: {path}"
        )
    text: str = larch_io.read_text(path, errors="strict", reject_cr=True)
    lines: list[str] = text.splitlines()
    if len(lines) > config.ISSUE_INTRA_BATCH_DEPS_MAX_ROWS:
        raise LearnFromBugsError(
            f"{label} exceeds {config.ISSUE_INTRA_BATCH_DEPS_MAX_ROWS} rows"
        )
    return list(enumerate(lines, start=1))


def _proposal_batch_map(path: Path, *, item_count: int) -> dict[str, int]:
    """Parse ``proposal-id<TAB>batch-item`` rows with complete item coverage."""
    rows: list[tuple[int, str]] = _read_filing_tsv(path, label="proposal batch map")
    if not rows:
        raise LearnFromBugsError("proposal batch map is empty")
    mapping: dict[str, int] = {}
    for line_number, row in rows:
        try:
            proposal_id, item_raw = row.split("\t")
        except ValueError as exc:
            raise LearnFromBugsError(
                f"proposal batch map line {line_number} must have two TSV fields"
            ) from exc
        if _PROPOSAL_ID_RE.fullmatch(proposal_id) is None:
            raise LearnFromBugsError(f"proposal batch map line {line_number} has invalid proposal id")
        if proposal_id in mapping:
            raise LearnFromBugsError(f"proposal batch map line {line_number} repeats proposal id {proposal_id}")
        if not item_raw.isdigit() or not 1 <= int(item_raw) <= item_count:
            raise LearnFromBugsError(f"proposal batch map line {line_number} has out-of-range batch item")
        mapping[proposal_id] = int(item_raw)
    mapped_items: set[int] = set(mapping.values())
    expected_items: set[int] = set(range(1, item_count + 1))
    if mapped_items != expected_items:
        missing: str = ",".join(str(index) for index in sorted(expected_items - mapped_items))
        raise LearnFromBugsError(f"proposal batch map does not cover batch item(s): {missing}")
    return mapping


def _declared_filing_edges(path: Path, *, proposal_items: Mapping[str, int]) -> set[tuple[int, int]]:
    """Translate proposal-id blocker rows to 1-based batch-item edges."""
    rows: list[tuple[int, str]] = _read_filing_tsv(path, label="proposal dependency file")
    proposal_edges: set[tuple[str, str]] = set()
    item_edges: set[tuple[int, int]] = set()
    for line_number, row in rows:
        try:
            blocker_id, blocked_id = row.split("\t")
        except ValueError as exc:
            raise LearnFromBugsError(
                f"proposal dependency line {line_number} must have two TSV fields"
            ) from exc
        if blocker_id == blocked_id:
            raise LearnFromBugsError(f"proposal dependency line {line_number} is a self-dependency")
        for proposal_id in (blocker_id, blocked_id):
            if _PROPOSAL_ID_RE.fullmatch(proposal_id) is None:
                raise LearnFromBugsError(f"proposal dependency line {line_number} has invalid proposal id")
            if proposal_id not in proposal_items:
                raise LearnFromBugsError(
                    f"proposal dependency line {line_number} names unmapped proposal {proposal_id}"
                )
        proposal_edge: tuple[str, str] = (blocker_id, blocked_id)
        if proposal_edge in proposal_edges:
            raise LearnFromBugsError(f"proposal dependency line {line_number} repeats an earlier edge")
        proposal_edges.add(proposal_edge)
        blocker_item: int = proposal_items[blocker_id]
        blocked_item: int = proposal_items[blocked_id]
        if blocker_item == blocked_item:
            continue
        item_edge: tuple[int, int] = (blocker_item, blocked_item)
        if (blocked_item, blocker_item) in item_edges:
            raise LearnFromBugsError("proposal dependencies map to reciprocal batch-item edges")
        item_edges.add(item_edge)
    return item_edges


def _filing_path_exists(
    edges: set[tuple[int, int]], *, start: int, target: int
) -> bool:
    """Return whether directed ``edges`` already connect ``start`` to ``target``."""
    pending: list[int] = [start]
    visited: set[int] = set()
    while pending:
        node: int = pending.pop()
        if node == target:
            return True
        if node in visited:
            continue
        visited.add(node)
        pending.extend(right for left, right in edges if left == node)
    return False


def _merge_filing_edges(
    *, declared: set[tuple[int, int]], shared_file: set[tuple[int, int]]
) -> set[tuple[int, int]]:
    """Merge edges without letting shared-file order override semantic order."""
    combined: set[tuple[int, int]] = set()
    for edge in sorted(declared):
        if _filing_path_exists(combined, start=edge[1], target=edge[0]):
            raise LearnFromBugsError("proposal dependencies contain a cycle")
        combined.add(edge)
    for edge in sorted(shared_file):
        if edge in combined:
            continue
        if not _filing_path_exists(combined, start=edge[1], target=edge[0]):
            combined.add(edge)
    return combined


def filing_dependencies(
    *, input_file: Path, proposal_map_file: Path, proposal_deps_file: Path
) -> tuple[tuple[int, int], ...]:
    """Build caller-supplied batch edges from declarations and shared files."""
    if input_file.is_symlink() or not input_file.is_file():
        raise LearnFromBugsError(f"batch input is not a regular file: {input_file}")
    batch_text: str = larch_io.read_text(input_file, errors="strict")
    items, _mode = parse_issue_input(batch_text)
    if not items:
        raise LearnFromBugsError("batch input has no issue items")
    if any(item.malformed for item in items):
        raise LearnFromBugsError("batch input contains a malformed issue item")
    proposal_items: dict[str, int] = _proposal_batch_map(proposal_map_file, item_count=len(items))
    declared_edges: set[tuple[int, int]] = _declared_filing_edges(
        proposal_deps_file, proposal_items=proposal_items
    )
    shared_file_edges: set[tuple[int, int]] = set(file_conflict_deps(input_file))
    combined: set[tuple[int, int]] = _merge_filing_edges(
        declared=declared_edges, shared_file=shared_file_edges
    )
    if len(combined) > config.ISSUE_INTRA_BATCH_DEPS_MAX_ROWS:
        raise LearnFromBugsError(
            f"filing dependency output exceeds {config.ISSUE_INTRA_BATCH_DEPS_MAX_ROWS} rows"
        )
    return tuple(sorted(combined))


def filing_deps_main(argv: list[str]) -> int:
    """Write deterministic caller-side dependency edges for filing mode."""
    parser = argparse.ArgumentParser(prog="learn-from-bugs filing-deps", allow_abbrev=False)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--proposal-map-file", required=True)
    parser.add_argument("--proposal-deps-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output_path = Path(args.output)
    try:
        edges: tuple[tuple[int, int], ...] = filing_dependencies(
            input_file=Path(args.input_file),
            proposal_map_file=Path(args.proposal_map_file),
            proposal_deps_file=Path(args.proposal_deps_file),
        )
        rendered: str = "".join(f"{blocker}\t{blocked}\n" for blocker, blocked in edges)
        larch_io.atomic_write(
            path=output_path,
            text=rendered,
            mode=0o600,
            prefix=f".{output_path.name}.",
            nofollow=False,
        )
    except (LearnFromBugsError, OSError, ValueError) as exc:
        print(f"learn-from-bugs filing-deps: {exc}", file=sys.stderr)
        return 1
    return 0


# --- State publication ------------------------------------------------------
# ``state-publish`` now delegates one local state write. The private Git
# publisher helpers below are dormant compatibility code owned by #7824.

STATE_PUBLISH_BRANCH_PREFIX: Final = "chore/learn-from-bugs-state-"
_STATE_MARKER_SUBJECT: Final = "chore(larch-logs): update learn-from-bugs state"
_STATE_PR_BODY: Final = (
    "## Summary\n\nPublish the latest `/learn-from-bugs` scan and proposal state.\n"
)
# gh pr create runs from the state branch; strip the /implement session
# handoff vars so its scope-disposition guard cannot bind to an unrelated run.
_STATE_PR_ENV_STRIP: Final = ("IMPLEMENT_TMPDIR", "SHIP_PR_STATE_FILE")

# STATE_PUBLISH_STATUS success values.
STATE_PUBLISH_MERGED: Final = "merged"
STATE_PUBLISH_HANDOFF_PENDING: Final = "handoff-pending"
STATE_PUBLISH_SAVED: Final = "saved"

# STATE_PUBLISH_STATUS failure reason tokens (G-Cfg-1: each token defined once).
STATE_PUBLISH_NOT_A_CHECKOUT: Final = "not-a-checkout"
STATE_PUBLISH_MISSING_ORIGIN: Final = "missing-origin"
STATE_PUBLISH_ORIGIN_MISMATCH: Final = "origin-mismatch"
STATE_PUBLISH_DEFAULT_BRANCH_UNRESOLVED: Final = "default-branch-unresolved"
STATE_PUBLISH_FETCH_FAILED: Final = "fetch-failed"
STATE_PUBLISH_INVALID_BRANCH: Final = "invalid-branch"
STATE_PUBLISH_EXISTING_LOCAL_BRANCH: Final = "existing-local-branch"
STATE_PUBLISH_EXISTING_REMOTE_BRANCH: Final = "existing-remote-branch"
STATE_PUBLISH_REMOTE_CHECK_FAILED: Final = "remote-check-failed"
STATE_PUBLISH_BRANCH_CREATE_FAILED: Final = "branch-create-failed"
STATE_PUBLISH_WRITE_STATE_FAILED: Final = "write-state-failed"
STATE_PUBLISH_COMMIT_FAILED: Final = "commit-failed"
STATE_PUBLISH_PR_CREATE_FAILED: Final = "pr-create-failed"

_PR_NUMBER_RE: Final = re.compile(r"[1-9][0-9]*")
_PR_STATUSES: Final = frozenset({"created", "existing"})


class StatePublishError(LearnFromBugsError):
    """A state-publication failure carrying a machine reason token."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.recovery_branch = ""


@dataclass(frozen=True)
class StatePublishRequest:
    root: Path
    repo: str
    run_dir: Path
    search: str
    state: str
    selected_count: int
    highest_closed_issue_number_scanned: int
    run_date: str
    scan_started_at: str
    proposals_file: str
    base_proposals_file: str


@dataclass(frozen=True)
class StatePublishResult:
    status: str
    pr_number: int
    pr_url: str
    state_path: str = ""


@dataclass(frozen=True)
class _PublishContext:
    request: StatePublishRequest
    root: Path
    branch: str
    default_branch: str


@dataclass
class _PublishProgress:
    committed: bool = False
    pr_created: bool = False


def _cli_argv(*args: str) -> list[str]:
    cli_path = Path(__file__).resolve().parents[2] / "cli.py"
    return [sys.executable, str(cli_path), *args]


def _git(runner: Runner, root: Path, args: Sequence[str]) -> CommandResult:
    return runner.run(["git", "-C", str(root), *args])


def _unique_kv(stdout: str, keys: tuple[str, ...]) -> dict[str, str] | None:
    """Return each key's value only when every key appears on exactly one line."""
    counts = dict.fromkeys(keys, 0)
    values: dict[str, str] = {}
    for line in stdout.splitlines():
        for key in keys:
            prefix = f"{key}="
            if line.startswith(prefix):
                counts[key] += 1
                values[key] = line[len(prefix) :]
    if any(count != 1 for count in counts.values()):
        return None
    return values


def _is_repo_relative(relpath: str) -> bool:
    if "\r" in relpath:
        return False
    guarded = f"/{relpath}/"
    return not any(marker in guarded for marker in ("//", "/./", "/../"))


def _preflight(runner: Runner, request: StatePublishRequest) -> None:
    root = request.root
    inside = _git(runner, root, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise StatePublishError(
            STATE_PUBLISH_NOT_A_CHECKOUT,
            "state publication requires the analysis root to be a repository checkout",
        )
    if _git(runner, root, ["remote", "get-url", "origin"]).returncode != 0:
        raise StatePublishError(
            STATE_PUBLISH_MISSING_ORIGIN, "state publication requires the origin remote"
        )
    verify = runner.run(
        _cli_argv(
            "learn-from-bugs", "verify-origin", "--root", str(root), "--repo", request.repo
        )
    )
    if verify.returncode != 0:
        raise StatePublishError(
            STATE_PUBLISH_ORIGIN_MISMATCH,
            f"state publication requires the analysis-root origin to identify {request.repo}",
        )
    status = _git(runner, root, ["status", "--porcelain"])
    if status.returncode != 0 or status.stdout.strip():
        raise StatePublishError(STATE_PUBLISH_NOT_A_CHECKOUT, "state publication requires a clean checkout")


def _resolve_default_branch(runner: Runner, request: StatePublishRequest) -> tuple[str, str]:
    root = request.root
    view = gh.command(
        runner,
        ["repo", "view", request.repo, "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"],
    )
    branches = [line for line in view.stdout.splitlines() if line.strip()]
    if view.returncode != 0 or len(branches) != 1:
        raise StatePublishError(
            STATE_PUBLISH_DEFAULT_BRANCH_UNRESOLVED, "could not resolve one repository default branch"
        )
    default_branch = branches[0]
    if _git(runner, root, ["check-ref-format", f"refs/heads/{default_branch}"]).returncode != 0:
        raise StatePublishError(
            STATE_PUBLISH_DEFAULT_BRANCH_UNRESOLVED,
            "the repository default branch is not a valid Git branch",
        )
    fetch_spec = f"+refs/heads/{default_branch}:refs/remotes/origin/{default_branch}"
    if git.fetch(runner, "origin", fetch_spec, cwd=str(root)).returncode != 0:
        raise StatePublishError(
            STATE_PUBLISH_FETCH_FAILED, "could not fetch the repository default branch"
        )
    default_ref = f"refs/remotes/origin/{default_branch}"
    if _git(runner, root, ["rev-parse", "--verify", f"{default_ref}^{{commit}}"]).returncode != 0:
        raise StatePublishError(
            STATE_PUBLISH_DEFAULT_BRANCH_UNRESOLVED, "the fetched default-branch ref is missing"
        )
    branch = _git(runner, root, ["branch", "--show-current"])
    head = _git(runner, root, ["rev-parse", "HEAD"])
    remote = _git(runner, root, ["rev-parse", default_ref])
    if (
        branch.returncode != 0
        or branch.stdout.strip() != default_branch
        or head.returncode != 0
        or remote.returncode != 0
        or head.stdout.strip() != remote.stdout.strip()
    ):
        raise StatePublishError(
            STATE_PUBLISH_FETCH_FAILED,
            "state publication requires the current checkout on the synced default branch",
        )
    return default_branch, default_ref


def _state_branch_name(request: StatePublishRequest) -> str:
    timestamp = re.sub(r"[^A-Za-z0-9]", "", request.run_date)
    run_token = re.sub(r"[^A-Za-z0-9._-]", "-", request.run_dir.name)
    if not timestamp or not run_token:
        raise StatePublishError(
            STATE_PUBLISH_INVALID_BRANCH, "state publication branch components must not be empty"
        )
    return f"{STATE_PUBLISH_BRANCH_PREFIX}{timestamp}-{run_token}"


def _reserve_branch(runner: Runner, root: Path, branch: str) -> None:
    if _git(runner, root, ["check-ref-format", "--branch", branch]).returncode != 0:
        raise StatePublishError(
            STATE_PUBLISH_INVALID_BRANCH, "the state publication branch is invalid"
        )
    if git.local_branch_exists(runner, branch, cwd=str(root)):
        raise StatePublishError(
            STATE_PUBLISH_EXISTING_LOCAL_BRANCH,
            "refusing to reuse an existing local state publication branch",
        )
    remote = git.remote_branch_state(runner, f"refs/heads/{branch}", cwd=str(root))
    if remote.state == "present":
        raise StatePublishError(
            STATE_PUBLISH_EXISTING_REMOTE_BRANCH,
            "refusing to reuse an existing remote state publication branch",
        )
    if remote.state != "absent":
        raise StatePublishError(
            STATE_PUBLISH_REMOTE_CHECK_FAILED, "could not check the remote state publication branch"
        )


def _write_state_in_checkout(runner: Runner, ctx: _PublishContext) -> str:
    request = ctx.request
    argv = _cli_argv(
        "learn-from-bugs", "write-state",
        "--root", str(ctx.root),
        "--repo", request.repo,
        "--search", request.search,
        "--state", request.state,
        "--selected-count", str(request.selected_count),
        "--highest-closed-issue-number-scanned", str(request.highest_closed_issue_number_scanned),
        "--run-date", request.run_date,
        "--scan-started-at", request.scan_started_at,
        "--proposals-file", request.proposals_file,
    )
    if request.base_proposals_file:
        argv.extend(["--base-proposals-file", request.base_proposals_file])
    result = runner.run(argv, cwd=str(ctx.root))
    if result.returncode != 0:
        raise StatePublishError(
            STATE_PUBLISH_WRITE_STATE_FAILED,
            "learn-from-bugs write-state failed during state publication",
        )
    parsed = _unique_kv(result.stdout, ("STATE_RELPATH",))
    if parsed is None or not parsed["STATE_RELPATH"]:
        raise StatePublishError(
            STATE_PUBLISH_WRITE_STATE_FAILED, "write-state did not return exactly one STATE_RELPATH"
        )
    marker_rel = parsed["STATE_RELPATH"]
    if not _is_repo_relative(marker_rel):
        raise StatePublishError(
            STATE_PUBLISH_WRITE_STATE_FAILED, "STATE_RELPATH must be repository-relative"
        )
    return marker_rel


def _commit_marker(
    runner: Runner, ctx: _PublishContext, marker_rel: str, progress: _PublishProgress
) -> None:
    root = str(ctx.root)
    if git.add(runner, marker_rel, cwd=root).returncode != 0:
        raise StatePublishError(STATE_PUBLISH_COMMIT_FAILED, "could not stage the state marker")
    commit = git.commit(
        runner, _STATE_MARKER_SUBJECT, only=True, paths=(marker_rel,), cwd=root
    )
    if commit.returncode != 0:
        raise StatePublishError(STATE_PUBLISH_COMMIT_FAILED, "could not commit the state marker")
    progress.committed = True
    changed = git.diff_tree_name_only(runner, "HEAD", cwd=root)
    committed_paths = [line for line in changed.stdout.splitlines() if line.strip()]
    if changed.returncode != 0 or committed_paths != [marker_rel]:
        raise StatePublishError(
            STATE_PUBLISH_COMMIT_FAILED, "the state commit changed more than the marker"
        )


def _parse_pr_identity(stdout: str) -> tuple[int, str]:
    fields = _unique_kv(stdout, ("PR_NUMBER", "PR_URL", "PR_STATUS"))
    if fields is None or not fields["PR_URL"]:
        raise StatePublishError(
            STATE_PUBLISH_PR_CREATE_FAILED, "PR creation returned incomplete identity"
        )
    if _PR_NUMBER_RE.fullmatch(fields["PR_NUMBER"]) is None:
        raise StatePublishError(
            STATE_PUBLISH_PR_CREATE_FAILED, "PR creation returned an invalid number"
        )
    if fields["PR_STATUS"] not in _PR_STATUSES:
        raise StatePublishError(
            STATE_PUBLISH_PR_CREATE_FAILED, "PR creation returned an invalid status"
        )
    return int(fields["PR_NUMBER"]), fields["PR_URL"]


def _create_state_pr(runner: Runner, ctx: _PublishContext) -> tuple[int, str]:
    body_path = ctx.request.run_dir / "state-publication-pr-body.md"
    larch_io.atomic_write(
        body_path, _STATE_PR_BODY, create_parent=True, prefix=f".{body_path.name}.", nofollow=True
    )
    env = {key: value for key, value in os.environ.items() if key not in _STATE_PR_ENV_STRIP}
    result = runner.run(
        _cli_argv(
            "pr", "create",
            "--repo", ctx.request.repo,
            "--branch", ctx.branch,
            "--base", ctx.default_branch,
            "--title", _STATE_MARKER_SUBJECT,
            "--body-file", str(body_path),
        ),
        cwd=str(ctx.root),
        env=env,
    )
    if result.returncode != 0:
        raise StatePublishError(STATE_PUBLISH_PR_CREATE_FAILED, "state PR creation failed")
    return _parse_pr_identity(result.stdout)


def _pr_state(runner: Runner, ctx: _PublishContext, number: int) -> CommandResult:
    return gh.command(
        runner,
        ["pr", "view", str(number), "--repo", ctx.request.repo, "--json", "state", "--jq", ".state"],
        cwd=str(ctx.root),
    )


def _resolve_pr_outcome(
    runner: Runner, ctx: _PublishContext, number: int, url: str
) -> StatePublishResult:
    opened = _pr_state(runner, ctx, number)
    if opened.returncode != 0:
        return StatePublishResult(STATE_PUBLISH_HANDOFF_PENDING, number, url)
    if opened.stdout.strip() != "OPEN":
        raise StatePublishError(
            STATE_PUBLISH_PR_CREATE_FAILED, "the identified state PR is not open"
        )
    merge = design_log_ship.run_design_log_ci_merge(
        runner,
        pr=number,
        repo=ctx.request.repo,
        cwd=str(ctx.root),
        merge_cwd=str(ctx.root),
    )
    merged_state = _pr_state(runner, ctx, number)
    merged_at = gh.command(
        runner,
        ["pr", "view", str(number), "--repo", ctx.request.repo, "--json", "mergedAt", "--jq", '.mergedAt // ""'],
        cwd=str(ctx.root),
    )
    durable = (
        merge.ok
        and merged_state.returncode == 0
        and merged_state.stdout.strip() == "MERGED"
        and merged_at.returncode == 0
        and merged_at.stdout.strip() != ""
    )
    status = STATE_PUBLISH_MERGED if durable else STATE_PUBLISH_HANDOFF_PENDING
    return StatePublishResult(status, number, url)


def _publish_in_checkout(
    runner: Runner, ctx: _PublishContext, progress: _PublishProgress
) -> StatePublishResult:
    if _git(runner, ctx.root, ["switch", "-c", ctx.branch]).returncode != 0:
        raise StatePublishError(
            STATE_PUBLISH_BRANCH_CREATE_FAILED, "could not create the state branch in the current checkout"
        )
    marker_rel = _write_state_in_checkout(runner, ctx)
    _commit_marker(runner, ctx, marker_rel, progress)
    push = _git(runner, ctx.root, ["push", "-u", "origin", ctx.branch])
    if push.returncode != 0:
        raise StatePublishError(STATE_PUBLISH_PR_CREATE_FAILED, "could not push the state branch")
    number, url = _create_state_pr(runner, ctx)
    progress.pr_created = True
    return _resolve_pr_outcome(runner, ctx, number, url)


def _restore_default_branch(runner: Runner, ctx: _PublishContext) -> None:
    if _git(runner, ctx.root, ["switch", ctx.default_branch]).returncode != 0:
        raise StatePublishError(STATE_PUBLISH_BRANCH_CREATE_FAILED, "could not restore the default branch")
    if _git(runner, ctx.root, ["pull", "--ff-only", "origin", ctx.default_branch]).returncode != 0:
        raise StatePublishError(STATE_PUBLISH_FETCH_FAILED, "could not sync the restored default branch")


def run_state_publish(runner: Runner, request: StatePublishRequest) -> StatePublishResult:
    """Persist the marker through the non-Git mutable-state contract."""
    argv = _cli_argv("learn-from-bugs", "write-state", "--root", str(request.root), "--repo", request.repo, "--search", request.search, "--state", request.state, "--selected-count", str(request.selected_count), "--highest-closed-issue-number-scanned", str(request.highest_closed_issue_number_scanned), "--run-date", request.run_date, "--scan-started-at", request.scan_started_at, "--proposals-file", request.proposals_file)
    if request.base_proposals_file:
        argv.extend(["--base-proposals-file", request.base_proposals_file])
    result = runner.run(argv, cwd=str(request.root))
    if result.returncode != 0:
        raise StatePublishError(STATE_PUBLISH_WRITE_STATE_FAILED, "learn-from-bugs write-state failed during state publication")
    parsed = _unique_kv(result.stdout, ("STATE_PATH",))
    if parsed is None or not Path(parsed["STATE_PATH"]).is_absolute():
        raise StatePublishError(STATE_PUBLISH_WRITE_STATE_FAILED, "write-state did not return one absolute STATE_PATH")
    return StatePublishResult(STATE_PUBLISH_SAVED, 0, "", parsed["STATE_PATH"])


_DORMANT_GIT_PUBLISHERS = (_preflight, _resolve_default_branch, _state_branch_name, _reserve_branch, _publish_in_checkout, _restore_default_branch)


def state_publish_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="learn-from-bugs state-publish", allow_abbrev=False)
    parser.add_argument("--root", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--search", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--selected-count", type=int, required=True)
    parser.add_argument("--highest-closed-issue-number-scanned", type=int, required=True)
    parser.add_argument("--run-date", required=True)
    parser.add_argument("--scan-started-at", required=True)
    parser.add_argument("--proposals-file", required=True)
    parser.add_argument("--base-proposals-file", default="")
    args = parser.parse_args(argv)
    request = StatePublishRequest(
        root=Path(args.root).expanduser(),
        repo=args.repo,
        run_dir=Path(args.run_dir).expanduser(),
        search=args.search,
        state=args.state,
        selected_count=args.selected_count,
        highest_closed_issue_number_scanned=args.highest_closed_issue_number_scanned,
        run_date=args.run_date,
        scan_started_at=args.scan_started_at,
        proposals_file=args.proposals_file,
        base_proposals_file=args.base_proposals_file,
    )
    try:
        result = run_state_publish(_runner(), request)
    except StatePublishError as exc:
        rows: dict[str, object] = {"STATE_PUBLISH_STATUS": exc.reason}
        if exc.recovery_branch:
            rows["STATE_PUBLISH_RECOVERY_BRANCH"] = exc.recovery_branch
        _print_kv(rows)
        print(str(exc), file=sys.stderr)
        return 2
    _print_kv(
        {
            "STATE_PUBLISH_STATUS": result.status,
            "STATE_PATH": result.state_path,
        }
    )
    return 0
