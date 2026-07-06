# argparse add_argument() and file write_text()/write() results are intentionally discarded.
# pyright: reportUnusedCallResult=false
"""Mine closed issues for recurring root causes and propose preventions.

Backs the ``/learn-from-bugs`` skill. GitHub access goes through the
``larch.core.proc.Runner`` seam so the digest and coverage-index logic stay
unit-testable offline. The module never reads a full issue backlog into a model:
it compresses each body to a compact root-cause digest first (an average
``[BUG]`` body is dominated by an appended ``/design`` plan, which this drops),
so the synthesis step reads a small fraction of the raw tokens.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from larch.core.proc import ProcRunner, Runner
from larch.issue.analyze_bugs import resolve_repo

DEFAULT_SEARCH: Final = "[BUG] in:title"
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

# Coverage-index scanners: match a repo's existing enforcement surface so the
# report can flag proposals that already have coverage.
_GUIDELINE_ID_RE: Final = re.compile(r"^#{2,4}\s+(G-[A-Za-z0-9]+-\d+):\s*(.+?)\s*$", re.MULTILINE)
_INVARIANT_ID_RE: Final = re.compile(r"^#{2,4}\s+((?:INV|I)-[A-Za-z0-9]*-?\d+):\s*(.+?)\s*$", re.MULTILINE)


class LearnFromBugsError(RuntimeError):
    """Raised when issue mining cannot proceed."""


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
    rules: tuple[tuple[str, str], ...]
    python_lints: tuple[str, ...]
    script_lints: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "guidelines": [list(item) for item in self.guidelines],
            "invariants": [list(item) for item in self.invariants],
            "rules": [list(item) for item in self.rules],
            "python_lints": list(self.python_lints),
            "script_lints": list(self.script_lints),
        }


@dataclass(frozen=True)
class PrepareRequest:
    search: str
    state: str
    limit: int
    repo_explicit: str
    out_dir: Path
    root: Path


def _runner() -> Runner:
    return ProcRunner()


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


def _scan_rules(rules_dir: Path) -> tuple[tuple[str, str], ...]:
    if not rules_dir.is_dir():
        return ()
    rows: list[tuple[str, str]] = []
    for path in sorted(rules_dir.glob("*.md")):
        heading = ""
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("# "):
                heading = line[2:].strip()
                break
        rows.append((path.name, heading))
    return tuple(rows)


def _scan_lint_names(directory: Path, glob: str, prefix: str) -> tuple[str, ...]:
    if not directory.is_dir():
        return ()
    return tuple(sorted(path.stem for path in directory.glob(glob) if path.stem.startswith(prefix)))


def coverage_index(root: Path) -> CoverageIndex:
    """Scan the repo root for existing guidelines, invariants, rules, and lints."""
    return CoverageIndex(
        guidelines=_scan_marked_ids(root / "ARCHITECTURAL_GUIDELINES.md", _GUIDELINE_ID_RE),
        invariants=_scan_marked_ids(root / "ARCHITECTURAL_INVARIANTS.md", _INVARIANT_ID_RE),
        rules=_scan_rules(root / ".claude" / "rules"),
        python_lints=_scan_lint_names(root / "python" / "larch" / "lint", "lint_*.py", "lint_"),
        script_lints=_scan_lint_names(root / "scripts", "lint-*", "lint-"),
    )


# --- Orchestration cores + cli mains ----------------------------------------


def run_prepare(runner: Runner, request: PrepareRequest) -> dict[str, object]:
    """Fetch, digest, and coverage-index; write artifacts; return KV stats."""
    repo = resolve_repo(runner, request.repo_explicit)
    issues = list_issues(runner, search=request.search, state=request.state, limit=request.limit, repo=repo)
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
        "ISSUES_SELECTED": len(digests),
        "STRUCTURED": structured,
        "FREEFORM_OR_TITLE_ONLY": len(digests) - structured,
        "DIGEST_CHARS": digest_chars,
        "DIGEST_TOKENS_EST": digest_chars // 4,
        "GUIDELINES_INDEXED": len(coverage.guidelines),
        "INVARIANTS_INDEXED": len(coverage.invariants),
        "RULES_INDEXED": len(coverage.rules),
        "PYTHON_LINTS_INDEXED": len(coverage.python_lints),
        "SCRIPT_LINTS_INDEXED": len(coverage.script_lints),
    }


def _print_kv(pairs: Mapping[str, object]) -> None:
    for key, value in pairs.items():
        print(f"{key}={value}")


def prepare_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="learn-from-bugs prepare")
    parser.add_argument("--search", default=DEFAULT_SEARCH)
    parser.add_argument("--state", default=DEFAULT_STATE)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--repo", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    request = PrepareRequest(
        search=args.search,
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
