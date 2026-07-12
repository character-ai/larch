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
import re
import shlex
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Final, Literal, cast

from larch import io as larch_io
from larch.core import config
from larch.core.architectural_guidelines import (
    GUIDELINE_HEADING_RE,
    INVARIANT_HEADING_RE,
)
from larch.core.proc import ProcRunner, Runner
from larch.issue.analyze_bugs import resolve_repo
from larch.issue.title_match import BUG_PREFIX, bug_title_match

DEFAULT_SEARCH: Final = f"{BUG_PREFIX} in:title"
DEFAULT_STATE: Final = "closed"
DEFAULT_LIMIT: Final = 50

# Per-section char caps for the compact digest.
SUMMARY_CAP: Final = 600
ROOT_CAUSE_CAP: Final = 1000
FIX_CAP: Final = 400
FREEFORM_CAP: Final = 1100
# A diagnostic prefix shorter than this means the body is only the appended plan;
# the bug's signal then lives in its title.
TITLE_ONLY_PREFIX_MAX: Final = 40

# Diagnostic sections to keep, each with its cap. Deduped by the heading's first
# word so "root cause" and "root cause analysis" do not both land.
WANT_SECTIONS: Final = (
    ("summary", SUMMARY_CAP),
    ("root cause analysis", ROOT_CAUSE_CAP),
    ("root cause", ROOT_CAUSE_CAP),
    ("suggested fix(es)", FIX_CAP),
    ("suggested fix", FIX_CAP),
)

# Earliest match marks where the appended /design plan begins; everything before
# it is the diagnostic report we mine.
_BOUNDARY_PATTERNS: Final = (
    re.compile(r"<!--\s*larch:plan:start", re.IGNORECASE),
    re.compile(r"^##\s+Plan\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^##\s+Approach\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^###\s+(?:NEW|UPDATED|REWRITTEN|MAY_UPDATE):", re.IGNORECASE | re.MULTILINE
    ),
)
_HEADING_RE: Final = re.compile(r"^#{2,4}\s+(.+?)\s*$")
_FENCE_MARKER_RE: Final = re.compile(r"^(`{3,}|~{3,})(.*)$")
_DONE_PREFIX_RE: Final = re.compile(r"^\[DONE\]\s*")
_PROPOSAL_ID_RE: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TEST_NAME_RE: Final = re.compile(r"^test_[A-Za-z0-9_]+$")
_FIX_TOKEN_RE: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

ProposalType = Literal["lint", "invariant", "guideline", "hook", "test", "fix"]
ProposalStatus = Literal["proposed", "adopted", "pending", "orphaned"]
PROPOSAL_TYPES: Final = frozenset(
    {"lint", "invariant", "guideline", "hook", "test", "fix"}
)
PROPOSAL_STATUSES: Final = frozenset({"proposed", "adopted", "pending", "orphaned"})
REGISTRY_KEY_LENGTH: Final = 2


class LearnFromBugsError(RuntimeError):
    """Raised when issue mining cannot proceed."""


@dataclass(frozen=True)
class Proposal:
    """One durable prevention proposal and its observed lifecycle."""

    id: str
    type: ProposalType
    target: str
    run_date: str
    status: ProposalStatus
    filed_issue: int | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.type,
            "target": self.target,
            "run_date": self.run_date,
            "status": self.status,
            "filed_issue": self.filed_issue,
        }


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
class BugDigest:
    number: int
    title: str
    closed_at: str
    url: str
    state: str
    structured: bool
    prefix_chars: int
    sections: Mapping[str, str]

    def to_json(self) -> dict[str, object]:
        return {
            "number": self.number,
            "title": self.title,
            "closed_at": self.closed_at,
            "url": self.url,
            "state": self.state,
            "structured": self.structured,
            "prefix_chars": self.prefix_chars,
            "sections": dict(self.sections),
        }


@dataclass(frozen=True)
class CoverageIndex:
    """The target repo's existing enforcement surface, for dedup in the report."""

    guidelines: tuple[tuple[str, str], ...]
    invariants: tuple[tuple[str, str], ...]
    python_lints: tuple[str, ...]
    script_lints: tuple[str, ...]

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


def _runner() -> Runner:
    return ProcRunner()


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_path(root: Path) -> Path:
    """Return the fixed marker path under ``root``."""
    root_path: Path = root.expanduser()
    if not root_path.is_absolute():
        root_path = Path.cwd() / root_path
    return root_path / config.LEARN_FROM_BUGS_STATE_RELPATH


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


def _validate_target(
    proposal_type: ProposalType, target: str, root: Path | None = None
) -> None:
    if _validate_fix_or_hook_target(proposal_type, target):
        return
    if proposal_type == "lint" and target.startswith("registration:"):
        name = target.removeprefix("registration:")
        if _FIX_TOKEN_RE.fullmatch(name) is None:
            raise LearnFromBugsError(f"invalid lint registration target: {target!r}")
    elif proposal_type == "lint" and target.startswith("module:"):
        _validate_path_target(target.removeprefix("module:"), (".py",), root)
    elif proposal_type in {"invariant", "guideline"}:
        path_target, _fragment = _validate_architectural_target(target)
        _validate_path_target(path_target, (".md",), root)
    elif proposal_type == "test":
        path_target, separator, test_name = target.partition("::")
        if separator and _TEST_NAME_RE.fullmatch(test_name) is None:
            raise LearnFromBugsError(f"invalid test function target: {target!r}")
        _validate_path_target(path_target, (".py",), root)
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


def _split_sections(prefix: str) -> dict[str, str]:
    """Split a diagnostic prefix into heading-named sections, ignoring fenced headings."""
    positioned = _lines_with_starts(prefix)
    lines = [line for _, line in positioned]
    fenced = _fenced_line_indices(lines)
    # (normalized_name, match_start, content_start)
    heads: list[tuple[str, int, int]] = []
    for index, (line_start, line) in enumerate(positioned):
        if index in fenced:
            continue
        match = _HEADING_RE.match(line)
        if match is None:
            continue
        name = match.group(1).replace("`", "").strip().lower()
        heads.append((name, line_start, line_start + match.end()))
    out: dict[str, str] = {}
    for index, (name, _match_start, content_start) in enumerate(heads):
        end = heads[index + 1][1] if index + 1 < len(heads) else len(prefix)
        out[name] = prefix[content_start:end].strip()
    return out


def _squeeze(text: str, cap: int) -> str:
    collapsed = re.sub(r"\n{2,}", "\n", text).strip()
    return collapsed[:cap] + ("…" if len(collapsed) > cap else "")


def _pick_sections(prefix: str) -> tuple[dict[str, str], bool]:
    """Return (kept sections, structured?), falling back to freeform or title-only."""
    found = _split_sections(prefix)
    picked: dict[str, str] = {}
    seen_roots: set[str] = set()
    for want, cap in WANT_SECTIONS:
        root = want.split()[0]
        if want in found and root not in seen_roots:
            picked[want] = _squeeze(found[want], cap)
            seen_roots.add(root)
    if picked:
        return picked, True
    if len(prefix.strip()) < TITLE_ONLY_PREFIX_MAX:
        return {"_title_only": ""}, False
    return {"_freeform": _squeeze(prefix, FREEFORM_CAP)}, False


def build_digest(issue: Mapping[str, object]) -> BugDigest:
    """Compress one raw issue row (from ``gh issue list --json``) to a digest."""
    body = str(issue.get("body") or "")
    prefix = diagnostic_prefix(body)
    sections, structured = _pick_sections(prefix)
    title = _DONE_PREFIX_RE.sub("", str(issue.get("title") or ""))
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
    )


# --- Issue listing (through the Runner seam) --------------------------------


def _issue_list_argv(*, search: str, state: str, limit: int, repo: str) -> list[str]:
    return [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--search",
        search,
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        "number,title,body,closedAt,url,state",
    ]


def list_issues(
    runner: Runner, *, search: str, state: str, limit: int, repo: str
) -> list[dict[str, object]]:
    result = runner.run(
        _issue_list_argv(search=search, state=state, limit=limit, repo=repo)
    )
    if result.returncode != 0:
        raise LearnFromBugsError(
            f"gh issue list failed: {(result.stderr or result.stdout).strip()}"
        )
    try:
        parsed = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise LearnFromBugsError(f"gh issue list returned invalid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise LearnFromBugsError("gh issue list did not return a JSON array")
    return [
        cast("dict[str, object]", row)
        for row in cast("list[object]", parsed)
        if isinstance(row, dict)
    ]


# --- Coverage index (offline, pure) -----------------------------------------


def _scan_marked_ids(
    path: Path, pattern: re.Pattern[str]
) -> tuple[tuple[str, str], ...]:
    if not path.is_file():
        return ()
    text = path.read_text(encoding="utf-8", errors="replace")
    return tuple((match.group(1), match.group(2)) for match in pattern.finditer(text))


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
    return CoverageIndex(
        guidelines=_scan_marked_ids(
            root / "ARCHITECTURAL_GUIDELINES.md", GUIDELINE_HEADING_RE
        ),
        invariants=_scan_marked_ids(
            root / "ARCHITECTURAL_INVARIANTS.md", INVARIANT_HEADING_RE
        ),
        python_lints=_scan_lint_names(
            root / "python" / "larch" / "lint", "lint_*.py", "lint_"
        ),
        script_lints=_scan_lint_names(root / "scripts", "lint-*", "lint-"),
    )


# --- Orchestration cores + cli mains ----------------------------------------


def run_prepare(runner: Runner, request: PrepareRequest) -> dict[str, object]:
    """Fetch, digest, and coverage-index; write artifacts; return KV stats."""
    repo = resolve_repo(runner, request.repo_explicit)
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
    highest_closed_issue_number_scanned = _highest_issue_number(raw_issues)
    digests = [build_digest(issue) for issue in issues]
    out_dir = request.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    digest_path = out_dir / "digest.jsonl"
    with digest_path.open("w", encoding="utf-8") as handle:
        for digest in digests:
            handle.write(json.dumps(digest.to_json()) + "\n")
    coverage = coverage_index(request.root)
    coverage_path = out_dir / "coverage-index.json"
    coverage_path.write_text(
        json.dumps(coverage.to_json(), indent=2) + "\n", encoding="utf-8"
    )
    digest_chars = sum(
        len(json.dumps(digest.to_json()["sections"])) for digest in digests
    )
    structured = sum(1 for digest in digests if digest.structured)
    return {
        "RUN_DIR": str(out_dir),
        "DIGEST_PATH": str(digest_path),
        "COVERAGE_INDEX_PATH": str(coverage_path),
        "REPO": repo,
        "SEARCH": request.search,
        "STATE": request.state,
        "SCAN_STARTED_AT": scan_started_at,
        "HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED": highest_closed_issue_number_scanned,
        "ISSUES_SELECTED": len(digests),
        "ISSUES_FILTERED_NON_BUG": filtered_non_bug,
        "STRUCTURED": structured,
        "FREEFORM_OR_TITLE_ONLY": len(digests) - structured,
        "DIGEST_CHARS": digest_chars,
        "DIGEST_TOKENS_EST": digest_chars // 4,
        "GUIDELINES_INDEXED": len(coverage.guidelines),
        "INVARIANTS_INDEXED": len(coverage.invariants),
        "PYTHON_LINTS_INDEXED": len(coverage.python_lints),
        "SCRIPT_LINTS_INDEXED": len(coverage.script_lints),
    }


def _print_kv(pairs: Mapping[str, object]) -> None:
    for key, value in pairs.items():
        print(f"{key}={value}")


def prepare_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="learn-from-bugs prepare", allow_abbrev=False)
    parser.add_argument("--search", default=DEFAULT_SEARCH)
    parser.add_argument("--state", default=DEFAULT_STATE)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--repo", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", default=".")
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
    )
    _print_kv(run_prepare(_runner(), request))
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


def _test_target_adopted(proposal: Proposal, root: Path) -> bool:
    raw_path, separator, test_name = proposal.target.partition("::")
    path = _safe_relative_path(root, raw_path, (".py",))
    if not path.is_file():
        return False
    if not separator:
        return True
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
    return checkers[proposal.type](proposal, root)


def _filed_issue_status(
    runner: Runner, proposal: Proposal, repo: str
) -> ProposalStatus:
    assert proposal.filed_issue is not None
    result = runner.run(  # lint-subprocess-via-runner: ok local gh issue view with JSON response
        [
            "gh",
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
    raise LearnFromBugsError("gh issue view returned an unknown closed issue reason")


def check_proposals(
    runner: Runner, proposals: tuple[Proposal, ...], root: Path, repo: str
) -> tuple[Proposal, ...]:
    """Refresh proposal lifecycle status against GitHub and repository evidence."""
    checked: list[Proposal] = []
    for proposal in proposals:
        _validate_target(proposal.type, proposal.target, root)
        if proposal.filed_issue is not None:
            status = _filed_issue_status(runner, proposal, repo)
        else:
            adopted = _repository_target_adopted(proposal, root)
            if adopted:
                status = "adopted"
            elif proposal.status in {"adopted", "orphaned"}:
                status = "orphaned"
            else:
                status = "pending"
        checked.append(Proposal(
            id=str(proposal.id),
            type=proposal.type,
            target=proposal.target,
            run_date=proposal.run_date,
            status=status,  # type: ignore[reportArgumentType]  # reason: local status narrowed from Literal["adopted","pending","orphaned"] to str
            filed_issue=proposal.filed_issue,
        ))
    return tuple(checked)


def render_adoption_summary(
    proposals: tuple[Proposal, ...], today: date | None = None
) -> str:
    """Render deterministic proposal adoption statistics."""
    counts = {
        status: sum(item.status == status for item in proposals)
        for status in ("adopted", "pending", "orphaned")
    }
    denominator = sum(counts.values())
    rate = 0.0 if denominator == 0 else counts["adopted"] / denominator * 100
    lines = [
        "## Proposal adoption",
        "",
        f"- Adopted: {counts['adopted']}",
        f"- Pending: {counts['pending']}",
        f"- Orphaned: {counts['orphaned']}",
        f"- Adoption rate: {rate:.1f}%",
    ]
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
    prior: tuple[Proposal, ...], residuals: tuple[Proposal, ...]
) -> tuple[Proposal, ...]:
    """Append new residuals while preserving stable pending identities."""
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
        out[index] = Proposal(
            id=historical.id,
            type=historical.type,
            target=historical.target,
            run_date=historical.run_date,
            status=historical.status,
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
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    state = _read_existing_state(state_path(root))
    if state is not None and state.repo != args.repo:
        raise LearnFromBugsError(
            "--repo does not match the durable learn-from-bugs state repository"
        )
    proposals = () if state is None else state.proposals
    checked = check_proposals(_runner(), proposals, root, args.repo)
    proposals_out = Path(args.proposals_out)
    adoption_out = Path(args.adoption_out)
    larch_io.atomic_write(
        proposals_out,
        "".join(json.dumps(item.to_json()) + "\n" for item in checked),
        prefix=f".{proposals_out.name}.",
        nofollow=True,
    )
    larch_io.atomic_write(
        adoption_out,
        render_adoption_summary(checked),
        prefix=f".{adoption_out.name}.",
        nofollow=True,
    )
    _print_kv(
        {
            "PROPOSALS_COUNT": len(checked),
            "PROPOSALS_ADOPTED": sum(item.status == "adopted" for item in checked),
            "PROPOSALS_PENDING": sum(item.status == "pending" for item in checked),
            "PROPOSALS_ORPHANED": sum(item.status == "orphaned" for item in checked),
            "CHECKED_PROPOSALS_PATH": str(proposals_out),
            "ADOPTION_SUMMARY_PATH": str(adoption_out),
        }
    )
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
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    path = state_path(root)
    existing = _read_existing_state(path)
    if args.proposals_file:
        proposals = load_proposals_jsonl(Path(args.proposals_file), root=root)
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
    write_state(path, state)
    _print_kv(
        {
            "STATE_RELPATH": config.LEARN_FROM_BUGS_STATE_RELPATH,
            "STATE_PATH": str(path),
            "RUN_DATE": state.run_date,
            "SCAN_STARTED_AT": state.scan_started_at or "",
            "HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED": state.highest_closed_issue_number_scanned,
            "SCHEMA_VERSION": state.schema_version,
            "PROPOSAL_COUNT": len(state.proposals),
        }
    )
    return 0
