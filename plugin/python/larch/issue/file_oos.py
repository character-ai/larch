"""Post-ship OOS detection and idempotency support.

Responsibilities:
1. Detect accepted, non-security OOS blocks across upstream inputs.
2. Enforce idempotency via the oos-issues-created.md sentinel.
3. Classify carve-outs (forked, repo_unavailable, security).

The actual GitHub issue creation and semantic dedup remain with the /issue
pipeline (LLM) invoked by the orchestrator.  This module prepares the
to-file set and exposes the sentinel-based idempotency check so the
orchestrator can avoid re-filing across same-session retries.
"""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import json
import os
import re
from itertools import pairwise
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from larch import io as larch_io
from larch.core import config
from larch.report import run_log_corpus
from larch.review import voting
from larch.review.review_types import count_non_security_blocks, parse_blocks
from larch.issue.issue_create import ParsedItem, parse_issue_input
from larch.core.redact import redact


# ---------------------------------------------------------------------------
# Constants (moved from config to keep OOS-specific tunables here)
# ---------------------------------------------------------------------------
INLINE_TRIAGE_MARKER: str = config.INLINE_TRIAGE_MARKER
OOS_FILED_URL_FIELD: str = config.OOS_FILED_URL_FIELD


# ---------------------------------------------------------------------------
# Regexes (ported from oos.py)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# GitHub URL helper
# ---------------------------------------------------------------------------
def _github_issue_url_pattern() -> re.Pattern[str]:
    gh_host = os.environ.get("GH_HOST", "github.com")
    if gh_host and gh_host != "github.com":
        esc = re.escape(gh_host)
        host = f"(?:{esc}|github\\.com)"
    else:
        host = r"github\.com"
    return re.compile(
        rf"https://{host}/[^/\s]+/[^/\s]+/issues/\d+",
    )


# ---------------------------------------------------------------------------
# Block-counting (ported from oos.py; includes #3550 legacy-header support)
# ---------------------------------------------------------------------------
def _count_non_security_markdown(text: str) -> int:
    """Count accepted non-security OOS blocks with shared policy."""
    return count_non_security_blocks(text)


def count_non_security(accepted_paths: tuple[str, ...]) -> int:
    """Count non-security accepted OOS blocks across markdown files."""
    total = 0
    for path in accepted_paths:
        file_path = Path(path)
        if not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8")
        total += _count_non_security_markdown(text)
    return total


# ---------------------------------------------------------------------------
# Idempotency: sentinel-based URL recovery
# ---------------------------------------------------------------------------
def read_filed_urls_from_sentinel(sentinel_path: str | None) -> list[str]:
    """Return GitHub issue URLs already recorded in the sentinel file."""
    if not sentinel_path or not Path(sentinel_path).is_file():
        return []
    url_re = _github_issue_url_pattern()
    text = Path(sentinel_path).read_text(encoding="utf-8")
    return url_re.findall(text)


# ---------------------------------------------------------------------------
# Accepted-OOS path resolution (bash checkpoint order)
# ---------------------------------------------------------------------------
def resolve_design_oos_path(tmpdir: Path) -> Path:
    """Resolve accepted design OOS path in bash checkpoint order."""
    design_tmpdir = os.environ.get("DESIGN_TMPDIR", "")
    if design_tmpdir:
        design_path = Path(design_tmpdir) / "oos-accepted-design.md"
        if design_path.is_file():
            return design_path
    exported = tmpdir / "design-export" / "oos-accepted-design.md"
    if exported.is_file():
        return exported
    return tmpdir / "oos-accepted-design.md"


def accepted_oos_paths(tmpdir: Path) -> tuple[str, ...]:
    """Return the canonical accepted-OOS file paths for the given tmpdir."""
    design_path = resolve_design_oos_path(tmpdir)
    return tuple(
        str(p)
        for p in (
            tmpdir / "oos-accepted-review.md",
            tmpdir / "oos-accepted-main-agent.md",
            design_path,
        )
    )


# ---------------------------------------------------------------------------
# Detection result
# ---------------------------------------------------------------------------
class OosStatus(NamedTuple):
    non_security_count: int
    already_filed: bool
    carve_out: bool
    security_present: bool


def detect(
    tmpdir: Path,
    *,
    forked: bool = False,
    repo_unavailable: bool = False,
) -> OosStatus:
    """Return OOS detection status for the current run."""
    if forked or repo_unavailable:
        return OosStatus(
            non_security_count=0,
            already_filed=False,
            carve_out=True,
            security_present=False,
        )

    sentinel = tmpdir / "oos-issues-created.md"
    already_filed = bool(read_filed_urls_from_sentinel(str(sentinel)))

    security_oos = tmpdir / "security-oos-observations.md"
    security_present = security_oos.is_file() and security_oos.stat().st_size > 0

    paths = accepted_oos_paths(tmpdir)
    non_sec = count_non_security(paths)

    return OosStatus(
        non_security_count=non_sec,
        already_filed=already_filed,
        carve_out=False,
        security_present=security_present,
    )



# ---------------------------------------------------------------------------
# C4c OOS helper ports
# ---------------------------------------------------------------------------

_INTERNAL_URL_RE = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|"
    r"172\.(?:1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|"
    r"\[?(?:fc[0-9a-f]{2}:|fd[0-9a-f]{2}:|fe80:)|"
    r"[^\s/]+\.(?:internal|local|corp|lan|intranet|test|example|invalid))[^\s]*"
    r"|\b(?:localhost|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|"
    r"172\.(?:1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|"
    r"[^\s/]+\.(?:internal|local|corp|lan|intranet))\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?1[ .-]?)?\(?[0-9]{3}\)?[ .-]?[0-9]{3}[ .-]?[0-9]{4}")
_SSN_RE = re.compile(r"[0-9]{3}-[0-9]{2}-[0-9]{4}")
_ACCOUNT_RE = re.compile(r"\b(?:account|user|customer|employee|tenant|org)[_-]?[A-Za-z0-9]{8,}\b", re.IGNORECASE)


_FILE_REF_RE = re.compile(
    r"(?P<path>(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_.-]+)?)"
    r"(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?"
)


def _sanitize_public_text(text: str) -> str:
    text = redact(text)
    text = _INTERNAL_URL_RE.sub("<INTERNAL-URL>", text)
    text = _EMAIL_RE.sub("<REDACTED-PII>", text)
    text = _SSN_RE.sub("<REDACTED-PII>", text)
    text = _PHONE_RE.sub("<REDACTED-PII>", text)
    return _ACCOUNT_RE.sub("<REDACTED-PII>", text)


def normalize_title(text: object) -> str:
    cleaned = _sanitize_public_text(str(text or ""))
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _read_kv_file(path: Path) -> dict[str, str]:
    return larch_io.read_kvs(path, default={}, cr_strip="strip")


def resolve_implement_run_id(tmpdir: Path, *, state: dict[str, str] | None = None) -> str:
    if state is None:
        state = _read_kv_file(path=tmpdir / "ship-pr-state.sh") | _read_kv_file(path=tmpdir / "finalize-state.sh")
    run_id = state.get("RUN_ID", "")
    if run_id:
        return run_id
    log_root = tmpdir / "larch-logs" / "implement"
    if log_root.is_dir():
        matches = [
            run_dir / "oos-issues.ndjson"
            for run_dir in run_log_corpus.safe_child_run_dirs(log_root)
            if (run_dir / "oos-issues.ndjson").is_file()
        ]
        if len(matches) == 1:
            return matches[0].parent.name
    return ""


def resolve_implement_run_id_for_disposition(tmpdir: Path, *, state: dict[str, str] | None = None) -> str:
    if state is None:
        state = _read_kv_file(path=tmpdir / "ship-pr-state.sh") | _read_kv_file(path=tmpdir / "finalize-state.sh")
    run_id = state.get("RUN_ID", "")
    if run_id:
        return run_id
    session_id = tmpdir / "session-id"
    if session_id.is_file():
        return session_id.read_text(encoding="utf-8").strip()
    return resolve_implement_run_id(tmpdir, state=state)


@dataclass(frozen=True)
class OosItem:
    number: int
    title: str
    body: str


def parse_oos_blocks(text: str) -> list[OosItem]:
    return [
        OosItem(int(block.item_id.removeprefix("OOS_")), block.title, block.block.rstrip())
        for block in parse_blocks(text, boundary="item-heading")
        if block.kind == "OOS"
    ]


@dataclass(frozen=True)
class FileConflictRecord:
    path: str
    start: int
    end: int
    whole: bool


@dataclass(frozen=True)
class FileConflictEdge:
    left: int
    right: int
    basename: str


class FileConflictGlobalCapExceeded(ValueError):
    """Raised when planned file-conflict TSV rows exceed the global cap."""


class FileConflictInvalidCap(ValueError):
    """Raised when OOS_FILE_CONFLICT_* env values are invalid."""


_FILE_CONFLICT_DEFAULT_CLUSTER_CAP = 200
_FILE_CONFLICT_MIN_COMPONENT_NODES = 2
_FILE_CONFLICT_RANGE_RE = re.compile(r"^(.+):([0-9]+)(-([0-9]+))?$")
_FILE_CONFLICT_SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
_FILE_CONFLICT_ANY_RE = re.compile(
    f"(?:{voting.FILE_LINE_REGEXES['any-re']})|(?:{voting.FILE_LINE_REGEXES['extensionless-re']})",
)


def _file_conflict_cap(*, name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    if not raw.isdigit() or int(raw) <= 0:
        raise FileConflictInvalidCap(f"ERROR: {name} must be a positive integer (got: '{raw}')")
    return int(raw)


def _file_conflict_caps() -> tuple[int, int]:
    return (
        _file_conflict_cap(name="OOS_FILE_CONFLICT_CLUSTER_CAP", default=_FILE_CONFLICT_DEFAULT_CLUSTER_CAP),
        _file_conflict_cap(
            name="OOS_FILE_CONFLICT_GLOBAL_CAP",
            default=config.ISSUE_INTRA_BATCH_DEPS_MAX_ROWS,
        ),
    )


def _clean_file_conflict_match(raw: str) -> str:
    cleaned = re.sub(r"^[^A-Za-z.]+", "", raw)
    cleaned = re.sub(r"[^A-Za-z0-9_./:-]+$", "", cleaned)
    return cleaned.removeprefix("./")


def _raw_file_conflict_match_is_unsafe(*, line: str, match: re.Match[str]) -> bool:
    """Reject traversal syntax the file-line regex can drop via sub-matches."""
    if line[: match.start()].endswith(".."):
        return True
    return ".." in match.group(0)


_TRAVERSAL_DOTDOT_PLACEHOLDER = "\x1e"


def _normalize_file_conflict_body(body: str) -> str:
    protected = body.replace("..", _TRAVERSAL_DOTDOT_PLACEHOLDER)
    normalized = re.sub(r"(^|[^A-Za-z0-9])\./", r"\1", protected)
    normalized = re.sub(r"[,;]", "\n", normalized)
    return normalized.replace(_TRAVERSAL_DOTDOT_PLACEHOLDER, "..")


def _file_conflict_path_is_safe(path: str) -> bool:
    if not path:
        return False
    if path.startswith(("/", "-")):
        return False
    if ".." in path or ":" in path:
        return False
    return bool(_FILE_CONFLICT_SAFE_PATH_RE.fullmatch(path))


def _file_conflict_record(candidate: str) -> FileConflictRecord | None:
    path = candidate
    start = 0
    end = 0
    whole = True
    if match := _FILE_CONFLICT_RANGE_RE.match(candidate):
        path = match.group(1)
        parsed_start = int(match.group(2))
        parsed_end = int(match.group(4) or match.group(2))
        if 0 < parsed_start <= parsed_end:
            start = parsed_start
            end = parsed_end
            whole = False
    path = path.removeprefix("./")
    if not _file_conflict_path_is_safe(path):
        return None
    return FileConflictRecord(path, start, end, whole)


def _item_file_records(item: ParsedItem) -> list[FileConflictRecord]:
    records: set[FileConflictRecord] = set()
    normalized = _normalize_file_conflict_body(item.body)
    for line in normalized.splitlines():
        for match in _FILE_CONFLICT_ANY_RE.finditer(line):
            if _raw_file_conflict_match_is_unsafe(line=line, match=match):
                continue
            candidate = _clean_file_conflict_match(match.group(0))
            if not candidate:
                continue
            record = _file_conflict_record(candidate)
            if record is not None:
                records.add(record)
    return sorted(records, key=lambda r: (r.path, r.start, r.end, int(r.whole)))


def _ranges_conflict(*, left: FileConflictRecord, right: FileConflictRecord) -> bool:
    if left.path != right.path:
        return False
    if left.whole or right.whole:
        return True
    return not (left.start > right.end or right.start > left.end)


def _path_conflicts(*, left_records: list[FileConflictRecord], right_records: list[FileConflictRecord], path: str) -> bool:
    left_for_path = [record for record in left_records if record.path == path]
    right_for_path = [record for record in right_records if record.path == path]
    if any(record.whole for record in left_for_path) or any(record.whole for record in right_for_path):
        return True
    return any(_ranges_conflict(left=left, right=right) for left in left_for_path for right in right_for_path)


def _find_parent(*, parent: list[int], node: int) -> int:
    root = node
    while parent[root] != root:
        root = parent[root]
    while parent[node] != node:
        next_node = parent[node]
        parent[node] = root
        node = next_node
    return root


def _union_nodes(*, parent: list[int], left: int, right: int) -> None:
    left_root = _find_parent(parent=parent, node=left)
    right_root = _find_parent(parent=parent, node=right)
    if left_root == right_root:
        return
    keep = min(left_root, right_root)
    drop = max(left_root, right_root)
    for node in range(1, len(parent)):
        if _find_parent(parent=parent, node=node) == drop:
            parent[node] = keep


def _candidate_file_conflict_edges(items: list[ParsedItem]) -> tuple[list[FileConflictEdge], list[int]]:
    records: dict[int, list[FileConflictRecord]] = {}
    for index, item in enumerate(items, start=1):
        records[index] = [] if item.malformed else _item_file_records(item)
    parent = list(range(len(items) + 1))
    candidates: list[FileConflictEdge] = []
    for left in range(1, len(items) + 1):
        for right in range(left + 1, len(items) + 1):
            shared_paths = sorted({record.path for record in records[left]} & {record.path for record in records[right]})
            for path in shared_paths:
                if _path_conflicts(left_records=records[left], right_records=records[right], path=path):
                    candidates.append(FileConflictEdge(left, right, PurePosixPath(path).name))
                    _union_nodes(parent=parent, left=left, right=right)
                    break
    roots = [_find_parent(parent=parent, node=index) for index in range(len(parent))]
    return candidates, roots


def _planned_file_conflict_deps(
    items: list[ParsedItem],
    *,
    cluster_cap: int,
    global_cap: int,
) -> list[tuple[int, int]]:
    candidates, roots = _candidate_file_conflict_edges(items)
    nodes_by_root: dict[int, list[int]] = {}
    for index in range(1, len(items) + 1):
        nodes_by_root.setdefault(roots[index], []).append(index)

    planned: list[tuple[int, int]] = []
    for root in sorted(nodes_by_root):
        nodes = sorted(nodes_by_root[root])
        if len(nodes) < _FILE_CONFLICT_MIN_COMPONENT_NODES:
            continue
        node_set = set(nodes)
        cluster_edges = [edge for edge in candidates if edge.left in node_set and edge.right in node_set]
        if len(cluster_edges) > cluster_cap:
            basename_hint = cluster_edges[0].basename if cluster_edges else "unknown"
            print(
                f"**⚠ /implement: oos-file-conflict-deps cluster on {basename_hint} would emit "
                f"{len(cluster_edges)} dependency rows (cap {cluster_cap}, N={len(nodes)}); emitting chain "
                "instead of all-pairs (lower robustness under SCC pruning).**",
                file=sys.stderr,
            )
            planned.extend(pairwise(nodes))
        else:
            planned.extend((edge.left, edge.right) for edge in cluster_edges)
    planned = sorted(set(planned))
    if len(planned) > global_cap:
        raise FileConflictGlobalCapExceeded(
            f"ERROR: oos-file-conflict-deps would emit {len(planned)} rows, exceeding the "
            f"{global_cap}-row --intra-batch-deps-file cap; split the OOS batch",
        )
    return planned


def file_conflict_deps(input_file: Path, *, cluster_cap: int | None = None, global_cap: int | None = None) -> list[tuple[int, int]]:
    if not input_file.is_file():
        raise FileNotFoundError(f"input file not found: {input_file}")
    if cluster_cap is None or global_cap is None:
        env_cluster_cap, env_global_cap = _file_conflict_caps()
        cluster_cap = env_cluster_cap if cluster_cap is None else cluster_cap
        global_cap = env_global_cap if global_cap is None else global_cap
    text = larch_io.read_text(input_file, errors="strict")
    items, _mode = parse_issue_input(text)
    return _planned_file_conflict_deps(items, cluster_cap=cluster_cap, global_cap=global_cap)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="file_oos.py",
        description="Detect accepted non-security OOS blocks for post-ship filing.",
    )
    _ = p.add_argument("--tmpdir", required=True, help="IMPLEMENT_TMPDIR path")
    _ = p.add_argument("--forked", action="store_true", default=False)
    _ = p.add_argument("--repo-unavailable", action="store_true", default=False)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    raw_tmpdir = str(args.tmpdir)
    tmpdir = Path(raw_tmpdir)
    status = detect(tmpdir, forked=args.forked, repo_unavailable=args.repo_unavailable)
    result = {
        "non_security_count": status.non_security_count,
        "already_filed": status.already_filed,
        "carve_out": status.carve_out,
        "security_present": status.security_present,
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
