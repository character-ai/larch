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
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

from larch import io as larch_io
from larch.core import config
from larch.core.architectural_guidelines import GUIDELINE_HEADING_RE, INVARIANT_HEADING_RE
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
    re.compile(r"^###\s+(?:NEW|UPDATED|REWRITTEN|MAY_UPDATE):", re.IGNORECASE | re.MULTILINE),
)
_HEADING_RE: Final = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)
_DONE_PREFIX_RE: Final = re.compile(r"^\[DONE\]\s*")


class LearnFromBugsError(RuntimeError):
    """Raised when issue mining cannot proceed."""


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
    schema_version: int = 1

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "run_date": self.run_date,
            "repo": self.repo,
            "search": self.search,
            "state": self.state,
            "selected_count": self.selected_count,
            "highest_closed_issue_number_scanned": self.highest_closed_issue_number_scanned,
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


def _state_from_json(payload: object) -> LearnFromBugsState | None:
    if not isinstance(payload, dict):
        return None
    typed = cast("dict[str, object]", payload)
    schema_version = typed.get("schema_version")
    if schema_version is None or str(schema_version) != "1":
        return None
    run_date = str(typed.get("run_date") or "")
    repo = str(typed.get("repo") or "")
    if not run_date or not repo:
        return None
    scan_started_at_raw = typed.get("scan_started_at")
    scan_started_at = str(scan_started_at_raw or "") or None
    return LearnFromBugsState(
        run_date=run_date,
        scan_started_at=scan_started_at,
        highest_closed_issue_number_scanned=_int_field(typed, "highest_closed_issue_number_scanned", 0),
        repo=repo,
        search=str(typed.get("search") or ""),
        state=str(typed.get("state") or ""),
        selected_count=_int_field(typed, "selected_count", 0),
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
    cuts = [match.start() for pattern in _BOUNDARY_PATTERNS for match in [pattern.search(body)] if match]
    return body[: min(cuts)] if cuts else body


def _split_sections(prefix: str) -> dict[str, str]:
    heads = list(_HEADING_RE.finditer(prefix))
    out: dict[str, str] = {}
    for index, head in enumerate(heads):
        name = head.group(1).replace("`", "").strip().lower()
        start = head.end()
        end = heads[index + 1].start() if index + 1 < len(heads) else len(prefix)
        out[name] = prefix[start:end].strip()
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
    number = int(number_raw) if isinstance(number_raw, (int, str)) and str(number_raw).isdigit() else 0
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


def list_issues(runner: Runner, *, search: str, state: str, limit: int, repo: str) -> list[dict[str, object]]:
    result = runner.run(_issue_list_argv(search=search, state=state, limit=limit, repo=repo))
    if result.returncode != 0:
        raise LearnFromBugsError(f"gh issue list failed: {(result.stderr or result.stdout).strip()}")
    try:
        parsed = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise LearnFromBugsError(f"gh issue list returned invalid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise LearnFromBugsError("gh issue list did not return a JSON array")
    return [cast("dict[str, object]", row) for row in cast("list[object]", parsed) if isinstance(row, dict)]


# --- Coverage index (offline, pure) -----------------------------------------


def _scan_marked_ids(path: Path, pattern: re.Pattern[str]) -> tuple[tuple[str, str], ...]:
    if not path.is_file():
        return ()
    text = path.read_text(encoding="utf-8", errors="replace")
    return tuple((match.group(1), match.group(2)) for match in pattern.finditer(text))


def _scan_lint_names(directory: Path, glob: str, prefix: str) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    return tuple(sorted(path.stem for path in directory.glob(glob) if path.stem.startswith(prefix)))


def coverage_index(root: Path) -> CoverageIndex:
    """Scan the repo root for existing guidelines, invariants, and lints."""
    return CoverageIndex(
        guidelines=_scan_marked_ids(root / "ARCHITECTURAL_GUIDELINES.md", GUIDELINE_HEADING_RE),
        invariants=_scan_marked_ids(root / "ARCHITECTURAL_INVARIANTS.md", INVARIANT_HEADING_RE),
        python_lints=_scan_lint_names(root / "python" / "larch" / "lint", "lint_*.py", "lint_"),
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
    issues = [issue for issue in raw_issues if bug_title_match(str(issue.get("title") or ""))]
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
    coverage_path.write_text(json.dumps(coverage.to_json(), indent=2) + "\n", encoding="utf-8")
    digest_chars = sum(len(json.dumps(digest.to_json()["sections"])) for digest in digests)
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
    search_explicit: bool = any(token == "--search" or token.startswith("--search=") for token in argv)
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


def read_state_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="learn-from-bugs read-state", allow_abbrev=False)
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
    }
    if state.scan_started_at:
        rows["SCAN_STARTED_AT"] = state.scan_started_at
    _print_kv(rows)
    return 0


def write_state_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="learn-from-bugs write-state", allow_abbrev=False)
    parser.add_argument("--root", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--search", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--selected-count", type=int, required=True)
    parser.add_argument("--highest-closed-issue-number-scanned", type=int, required=True)
    parser.add_argument("--run-date", required=True)
    parser.add_argument("--scan-started-at", required=True)
    args = parser.parse_args(argv)
    path = state_path(Path(args.root))
    state = LearnFromBugsState(
        run_date=args.run_date,
        scan_started_at=args.scan_started_at,
        highest_closed_issue_number_scanned=args.highest_closed_issue_number_scanned,
        repo=args.repo,
        search=args.search,
        state=args.state,
        selected_count=args.selected_count,
    )
    write_state(path, state)
    _print_kv(
        {
            "STATE_RELPATH": config.LEARN_FROM_BUGS_STATE_RELPATH,
            "STATE_PATH": str(path),
            "RUN_DATE": state.run_date,
            "SCAN_STARTED_AT": state.scan_started_at or "",
            "HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED": state.highest_closed_issue_number_scanned,
        }
    )
    return 0
