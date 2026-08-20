"""Design decomposition helpers ported from shell."""
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from larch import io as larch_io
from larch.core import external_defaults
from larch.core import logging_util
from larch.core import proc
from larch.core.repo_roots import larch_entrypoint
from larch.core import retry
from larch.core import rust_runtime
from larch.design import plan_grammar
from larch.design.design_core import ROUTE_STATE_PATH
from larch.design.design_core import phase_driver_read_result_env
from larch.git import gh
from larch.issue import issue_wire
from larch.issue.title_match import leading_square_bracket_prefix, strip_lifecycle_prefix
from larch.state import session_env

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO_ROOT
DECOMPOSE_ARCHETYPES = ("decomposition-specialist", "dependency-analyst", "scope-minimalist", "risk-isolation")
RECOMMENDATION_RE = re.compile(r"^[ \t]*## Recommendation", re.MULTILINE)
PROMPT_PREFIX_LINE_MAX = 8
MIN_PARTITION_PIECES = 2
PARTITION_MAP_FIELD_COUNT = 3
PARTITION_DEP_FIELD_COUNT = 2
@dataclass(frozen=True)
class FiledPiece:
    piece: int
    issue: int
    repo: str


@dataclass(frozen=True)
class DependencyEdge:
    blocked: int
    blocker: int


@dataclass(frozen=True)
class DependencyMigration:
    original_issue: int
    repo: str
    pieces: tuple[FiledPiece, ...]
    incoming: tuple[DependencyEdge, ...]
    outgoing: tuple[DependencyEdge, ...]

class UsageError(ValueError):
    """CLI usage error."""


def _err(message: str) -> None:
    logging_util.BreadcrumbWriter().emit(message)


def _fail(message: str) -> None:
    raise UsageError(message)


def _emit_kv(*, key: str, value: object) -> None:
    text = ("true" if value else "false") if isinstance(value, bool) else str(value)
    logging_util.emit_kv(key=key, value=text)


def _validate_design_tmpdir(value: str) -> Path:
    ok, message = session_env.validate_design_tmpdir(value)
    if not ok:
        _fail(message)
    return Path(value).resolve()


def _positive_int(*, value: str, flag: str) -> int:
    if not value.isdigit() or int(value) <= 0:
        _fail(f"{flag} must be a positive integer")
    return int(value)


def _binary_bool(*, value: str, binary: str) -> bool:
    if value in {"true", "false"}:
        return value == "true"
    return shutil.which(binary) is not None


def _route_state_value(design_tmpdir: Path, key: str) -> str:
    """Read a ``KEY=value`` row from the Step 0 route-state env, or return "".

    The route-state file (written by the Rust-owned Step 0 route verb) carries
    the original issue title and number that ``/design`` bound at Step 0; the
    title is needed to build the split-piece title prefix. Reads go through the
    shared ``phase_driver_read_result_env`` helper that sibling consumers
    (``clarify``) already use, with a single-key containment,
    so parsing and value/newline handling stay centralized rather than being
    re-derived here. Missing/symlink/non-regular files degrade to "" so the
    caller's title passes through unchanged.
    """
    try:
        pairs = phase_driver_read_result_env(
            path=design_tmpdir / ROUTE_STATE_PATH,
            allow_keys=frozenset({key}),
        )
    except OSError:
        return ""
    for row_key, value in pairs:
        if row_key == key:
            return value
    return ""


def _prefixed_piece_title(
    *,
    original_title: str,
    issue_number: str,
    piece_number: int,
    piece_title: str,
) -> str:
    """Compose the filed-issue title for a partition piece.

    Preserves any leading square-bracket prefix carried by the original issue
    title, then appends the ``split-<original-issue-number>-<piece>`` token so
    every piece shares a common, traceable prefix. If the piece title already
    starts with the same bracket(s), they are not duplicated. When no issue
    number is bound, only the preserved bracket (if any) prefixes the title.
    """
    bracket = leading_square_bracket_prefix(strip_lifecycle_prefix(original_title))
    stripped_piece = piece_title
    if bracket:
        prefix_with_space = bracket + " "
        if stripped_piece.startswith(prefix_with_space):
            stripped_piece = stripped_piece[len(prefix_with_space):]
        elif stripped_piece.startswith(bracket):
            stripped_piece = stripped_piece[len(bracket):].lstrip()
    parts: list[str] = []
    if bracket:
        parts.append(bracket)
    if issue_number.isdigit():
        token = f"split-{issue_number}-{piece_number}:"
        if not stripped_piece.startswith(token + " ") and stripped_piece != token:
            parts.append(token)
    parts.append(stripped_piece)
    return " ".join(parts)


def _neutralize_markdown_h3_line_starts(text: str) -> str:
    return re.sub(r"(?m)^###", "\u200b###", text)


def _prepare_parse_dependency(*, dep: str, index_by_num: dict[int, int]) -> list[int] | None:
    match = re.search(r"blocked-by\b(.*)$", dep, re.IGNORECASE)
    if not match:
        return []
    remainder = match.group(1)
    segments = [seg.strip() for seg in re.split(r",|\s+and\b", remainder, flags=re.IGNORECASE)]
    segments = [seg for seg in segments if seg]
    if not segments:
        return None
    blockers: list[int] = []
    seen: set[int] = set()
    for segment in segments:
        sm = re.fullmatch(r"Piece\s+(\d+)", segment, re.IGNORECASE)
        if not sm:
            return None
        blocker = int(sm.group(1))
        if blocker in seen:
            return None
        seen.add(blocker)
        if blocker not in index_by_num:
            return None
        blockers.append(blocker)
    return blockers


def _piece_field(body: str, field: str) -> str:
    prefix = f"- {field}:"
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix.lower()):
            return stripped.split(":", 1)[1].strip()
    return ""


def _normalize_firm_heading(value: str) -> str:
    """Return the bare path from a partition's parent-plan heading token."""
    candidate = value.strip().strip("`").strip()
    heading = plan_grammar.match_heading(candidate)
    if heading is not None:
        candidate = heading.path
    return candidate.strip().strip("`").strip()


def _split_firm_headings(value: str) -> list[str]:
    items: list[str] = []
    for raw in re.split(r",|\n", value):
        item = _normalize_firm_heading(raw)
        if item:
            items.append(item)
    return items


def _scope_tokens(scope: str) -> list[str]:
    tokens: list[str] = []
    for match in re.finditer(r"`([^`]+)`", scope):
        token = match.group(1).strip().strip(",;")
        if token:
            tokens.append(token)
    cleaned = re.sub(r"`[^`]+`", " ", scope)
    for raw in re.split(r",|\s+", cleaned):
        token = raw.strip().strip(",;")
        if token and token not in {"and", "or"}:
            tokens.append(token)
    return list(dict.fromkeys(tokens))


def _path_matches_scope(*, path: str, scope_token: str) -> bool:
    token = scope_token.rstrip("/")
    return path == token or path.startswith(f"{token}/")


def _derive_firm_headings(*, parent_paths: list[str], scope: str) -> list[str]:
    tokens = _scope_tokens(scope)
    return [
        path
        for path in parent_paths
        if any(_path_matches_scope(path=path, scope_token=token) for token in tokens)
    ]


def _testing_strategy_lines(plan_text: str) -> list[str]:
    lines = plan_text.splitlines()
    start = -1
    level = 0
    for idx, line in enumerate(lines):
        match = re.match(r"^(#+)\s+Testing strategy\s*$", line, re.IGNORECASE)
        if match:
            start = idx + 1
            level = len(match.group(1))
            break
    if start < 0:
        return []
    out: list[str] = []
    for line in lines[start:]:
        heading = re.match(r"^(#+)\s+", line)
        if heading and len(heading.group(1)) <= level:
            break
        stripped = line.strip()
        if stripped:
            out.append(stripped)
    return out


def _derive_acceptance(*, plan_text: str, firm_headings: list[str], scope: str) -> str:
    strategy = _testing_strategy_lines(plan_text)
    matches = [
        line
        for line in strategy
        if any(path in line for path in firm_headings)
    ]
    if matches:
        return "\n".join(matches[:5])
    scope_summary = scope or ", ".join(firm_headings)
    if scope_summary:
        return f"Verify {scope_summary} per parent Testing strategy."
    return ""


def _parent_plan_scope_data(design_tmpdir: Path) -> tuple[str, list[str]]:
    parent_plan = design_tmpdir / "plan.txt"
    if not parent_plan.is_file() or parent_plan.is_symlink():
        return "", []
    parent_plan_text = parent_plan.read_text(encoding="utf-8", errors="replace")
    return parent_plan_text, issue_wire.extract_scope_paths(
        plan_text=parent_plan_text,
        use_fallback=False,
        include_optional=False,
    )


def _piece_metadata(
    *,
    body: str,
    parent_plan_text: str,
    parent_paths: list[str],
) -> tuple[str, list[str], str] | None:
    scope = _piece_field(body, "scope")
    firm = _split_firm_headings(_piece_field(body, "firm-headings"))
    if not firm:
        firm = _derive_firm_headings(parent_paths=parent_paths, scope=scope)
    acceptance = _piece_field(body, "acceptance")
    if not acceptance:
        acceptance = _derive_acceptance(plan_text=parent_plan_text, firm_headings=firm, scope=scope)
    if not firm or not acceptance:
        return None
    return scope, firm, acceptance


def _acyclic(*, node_count: int, edges: list[tuple[int, int]]) -> bool:
    adj: dict[int, list[int]] = defaultdict(list)
    indeg = [0] * node_count
    for a, b in edges:
        adj[a].append(b)
        indeg[b] += 1
    q: deque[int] = deque(i for i, degree in enumerate(indeg) if degree == 0)
    seen_count = 0
    while q:
        u = q.popleft()
        seen_count += 1
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return seen_count == node_count


def _collect_piece_data(
    *,
    pieces: list[tuple[int, str, str]],
    index_by_num: dict[int, int],
    parent_plan_text: str,
    parent_paths: list[str],
) -> tuple[str, list[str], list[str], list[list[str]], list[str], list[tuple[int, int]]]:
    panel_edges: list[tuple[int, int]] = []
    dep_lines: list[str] = []
    scopes: list[str] = []
    firm_heading_lines: list[list[str]] = []
    acceptance_lines: list[str] = []
    for i, (_pnum, _title, body) in enumerate(pieces):
        dep = _piece_field(body, "dependencies") or "none"
        dep_lines.append(dep)
        blockers = _prepare_parse_dependency(dep=dep, index_by_num=index_by_num)
        if blockers is None:
            return "bad-dependency-ref", [], [], [], [], []
        panel_edges.extend((index_by_num[blocker], i) for blocker in blockers)
        metadata = _piece_metadata(body=body, parent_plan_text=parent_plan_text, parent_paths=parent_paths)
        if metadata is None:
            return "missing-piece-metadata", [], [], [], [], []
        scope, firm, acceptance = metadata
        scopes.append(scope)
        firm_heading_lines.append(firm)
        acceptance_lines.append(acceptance)
    if parent_paths:
        parent_firm_headings = list(dict.fromkeys(parent_paths))
        child_firm_headings = list(dict.fromkeys(path for firm in firm_heading_lines for path in firm))
        if set(parent_firm_headings) != set(child_firm_headings):
            return "firm-heading-coverage-mismatch", [], [], [], [], []
    return "", dep_lines, scopes, firm_heading_lines, acceptance_lines, panel_edges


def prepare_partition_issues(
    *,
    design_tmpdir: Path,
    partition_file: Path,
    issue_number: str = "",
) -> tuple[str, str]:
    if not partition_file.is_file():
        raise UsageError("prepare: partition file not found")
    dec = design_tmpdir / "decompose"
    dec.mkdir(parents=True, exist_ok=True)
    out_input = dec / "partition-input.txt"
    out_deps = dec / "partition-deps.tsv"
    for path in (out_input, out_deps):
        path.unlink(missing_ok=True)

    text = partition_file.read_text(encoding="utf-8")
    if "## Pieces" not in text:
        return "invalid-partition-file", ""
    piece_rx = re.compile(r"(?m)^###\s+Piece\s+(\d+)\s*:\s*([^\n]+)$")
    pieces: list[tuple[int, str, str]] = []
    matches = list(piece_rx.finditer(text))
    for idx, match in enumerate(matches):
        pnum = int(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        pieces.append((pnum, title, text[start:end].strip()))
    piece_status = "no-pieces" if not pieces else "one-piece" if len(pieces) < MIN_PARTITION_PIECES else "bad-piece-number" if len({piece[0] for piece in pieces}) != len(pieces) else ""
    if piece_status:
        return piece_status, ""
    pieces.sort(key=lambda item: item[0])
    index_by_num: dict[int, int] = {pnum: i for i, (pnum, _title, _body) in enumerate(pieces)}

    parent_plan_text, parent_paths = _parent_plan_scope_data(design_tmpdir)
    err, dep_lines, scopes, firm_heading_lines, acceptance_lines, panel_edges = _collect_piece_data(
        pieces=pieces,
        index_by_num=index_by_num,
        parent_plan_text=parent_plan_text,
        parent_paths=parent_paths,
    )
    if err:
        return err, ""

    edges = list(dict.fromkeys(panel_edges))
    if not _acyclic(node_count=len(pieces), edges=edges):
        witness = "; ".join(f"Piece {pieces[a][0]}→Piece {pieces[b][0]}" for a, b in edges) or "(edges unavailable)"
        return "cycle-detected", witness

    feat_path = design_tmpdir / "feature-description.txt"
    feat = feat_path.read_text(encoding="utf-8") if feat_path.is_file() else ""
    feat = _neutralize_markdown_h3_line_starts(feat)
    feat = issue_wire.neutralize_named_block_markers(text=feat, marker="plan")
    orig = f"#{issue_number}" if issue_number.isdigit() else "(original issue — set ISSUE_NUMBER in session)"
    original_title = _route_state_value(design_tmpdir, "ISSUE_TITLE")
    lines: list[str] = []
    n = len(pieces)
    for i, (pnum, title, _body) in enumerate(pieces):
        scope = scopes[i]
        firm_text = ", ".join(firm_heading_lines[i])
        acceptance_text = acceptance_lines[i]
        prefixed_title = _prefixed_piece_title(
            original_title=original_title,
            issue_number=issue_number,
            piece_number=pnum,
            piece_title=title,
        )
        lines.append(f"### {prefixed_title}\n")
        body_text = (
            f"Partition piece {pnum} of {n} split from {orig}.\n\n"
            f"**Scope**: {scope or '(see parent partition file)'}\n\n"
            f"**Firm headings**: {firm_text}\n\n"
            f"**Acceptance**:\n\n{acceptance_text}\n\n"
            f"**Dependencies (from proposal)**: {dep_lines[i]}\n\n"
            "```\n"
            + issue_wire.neutralize_named_block_markers(
                text=issue_wire.compose_named_block(
                    marker="plan",
                    inner=(
                        "## Plan\n\n"
                        "(needs /design — operator runs `/design` on this filed piece "
                        "and reaches Gate C approval before `[DESIGNED]` or `/implement`.)\n"
                    ),
                ),
                marker="plan",
            )
            + "```\n\n"
            f"**Original feature context (excerpt)**:\n\n{feat[:4000]}\n"
        )
        lines.append(_neutralize_markdown_h3_line_starts(body_text))
    out_input.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with out_deps.open("w", encoding="utf-8") as handle:
        for a, b in edges:
            _ = handle.write(f"{a + 1}\t{b + 1}\n")
    return "ok", ""


def annotate_partition_issues(*, design_tmpdir: Path, issue_stdout_file: Path) -> None:
    if not issue_stdout_file.is_file():
        raise UsageError("annotate: stdout capture missing")
    sent = design_tmpdir / ".decompose-issues-filed"
    dec = design_tmpdir / "decompose"
    dec.mkdir(parents=True, exist_ok=True)
    filed = dec / "partition-filed.md"
    text = issue_stdout_file.read_text(encoding="utf-8")

    def kv(pattern: str) -> str:
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1) if m else ""

    created = kv(r"^ISSUES_CREATED=([0-9]+)\s*$") or "0"
    failed = kv(r"^ISSUES_FAILED=([0-9]+)\s*$") or "0"
    try:
        failed_n = int(failed)
    except ValueError:
        failed_n = 0
    urls: dict[int, str] = {}
    for m in re.finditer(r"^ISSUE_([0-9]+)_URL=(.+)\s*$", text, re.MULTILINE):
        urls[int(m.group(1))] = m.group(2).strip()

    input_file = dec / "partition-input.txt"
    expected_pieces = len(re.findall(r"(?m)^###\s+", input_file.read_text(encoding="utf-8"))) if input_file.is_file() and not input_file.is_symlink() else 0
    complete_mapping = (
        expected_pieces >= MIN_PARTITION_PIECES
        and set(urls) == set(range(1, expected_pieces + 1))
        and created.isdigit()
        and int(created) == expected_pieces
    )

    if sent.is_file():
        prev = sent.read_text(encoding="utf-8")
        if prev.strip() and filed.is_file() and failed_n == 0 and complete_mapping:
            ok = all(f"PARTITION_FILE_MAP\t{i}\t{url}" in prev for i, url in sorted(urls.items()))
            try:
                created_n = int(created)
            except ValueError:
                created_n = 0
            if ok and created_n == expected_pieces:
                return

    lines = ["# Partition filing record", "", f"- **ISSUES_CREATED**: {created}", f"- **ISSUES_FAILED**: {failed}", ""]
    for i in sorted(urls):
        lines.extend([f"## Piece {i}", f"- **Filed URL**: {urls[i]}", ""])
    filed.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failed_n == 0 and complete_mapping:
        with sent.open("w", encoding="utf-8") as handle:
            for i in sorted(urls):
                _ = handle.write(f"PARTITION_FILE_MAP\t{i}\t{urls[i]}\n")
    else:
        sent.unlink(missing_ok=True)


def _append_failure(design_tmpdir: Path, *, site: str, tool: str, exit_code: int, output_file: Path) -> None:
    subprocess.run(
        [
            str(larch_entrypoint(PLUGIN_ROOT)),
            "run-log",
            "append-failure",
            "--log",
            str(design_tmpdir / "execution-issues.md"),
            "--site",
            site,
            "--tool",
            tool,
            "--exit-code",
            str(exit_code),
            "--category",
            "External Reviewer Issues",
            "--output-file",
            str(output_file),
            "--redact",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _run_command(argv: Sequence[str], *, stdin: Path | None = None, stdout: Path | None = None) -> tuple[int, str]:
    with (stdin.open("rb") if stdin else Path(os.devnull).open("rb")) as inp:
        if stdout is None:
            result = subprocess.run(argv, input=inp.read() if stdin else None, check=False, capture_output=True)
            out = result.stdout.decode("utf-8", errors="replace") + result.stderr.decode("utf-8", errors="replace")
            return result.returncode, out
        with stdout.open("wb") as out_handle:
            result = subprocess.run(argv, stdin=inp if stdin else None, stdout=out_handle, stderr=subprocess.PIPE, check=False)
            return result.returncode, result.stderr.decode("utf-8", errors="replace")



def _parse_issue_url(url: str, *, expected_repo: str) -> int:
    match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/issues/([1-9][0-9]*)", url)
    if match is None or match.group(1) != expected_repo:
        raise UsageError("migrate-deps: filed issue URL does not match the expected repository")
    return int(match.group(2))


def filed_pieces(design_tmpdir: Path, *, repo: str) -> tuple[FiledPiece, ...]:
    sent = design_tmpdir / ".decompose-issues-filed"
    if not sent.is_file() or sent.is_symlink():
        raise UsageError("migrate-deps: missing complete annotation sentinel")
    pieces: list[FiledPiece] = []
    for line in sent.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) != PARTITION_MAP_FIELD_COUNT or parts[0] != "PARTITION_FILE_MAP" or not parts[1].isdigit():
            raise UsageError("migrate-deps: invalid annotation record")
        pieces.append(FiledPiece(piece=int(parts[1]), issue=_parse_issue_url(parts[2], expected_repo=repo), repo=repo))
    piece_numbers = {piece.piece for piece in pieces}
    issue_numbers = {piece.issue for piece in pieces}
    if (
        len(pieces) < MIN_PARTITION_PIECES
        or len(piece_numbers) != len(pieces)
        or len(issue_numbers) != len(pieces)
        or piece_numbers != set(range(1, len(pieces) + 1))
    ):
        raise UsageError("migrate-deps: incomplete or duplicate filed mapping")
    return tuple(sorted(pieces, key=lambda piece: piece.piece))


def _dependency_numbers(result: proc.CommandResult) -> tuple[int, ...]:
    if result.returncode != 0:
        raise RuntimeError("dependency-read-failed")
    rows = gh.loads_json_paginated_list(result.stdout)
    numbers: list[int] = []
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("dependency-read-invalid")
        number = cast("dict[str, object]", row).get("number")
        if isinstance(number, int) and number > 0:
            numbers.append(number)
        elif isinstance(number, str) and number.isdigit() and int(number) > 0:
            numbers.append(int(number))
        else:
            raise TypeError("dependency-read-invalid")
    return tuple(sorted(set(numbers)))


def _read_dependencies(*, issue: int, repo: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return (
        _dependency_numbers(gh.issue_blocked_by_read(proc, str(issue), repo=repo)),
        _dependency_numbers(gh.issue_blocking_read(proc, str(issue), repo=repo)),
    )


def _write_migration(path: Path, migration: DependencyMigration) -> None:
    payload = {
        "schema_version": "1",
        "original_issue": migration.original_issue,
        "repo": migration.repo,
        "pieces": [asdict(piece) for piece in migration.pieces],
        "incoming": [asdict(edge) for edge in migration.incoming],
        "outgoing": [asdict(edge) for edge in migration.outgoing],
    }
    larch_io.atomic_write(path=path, text=json.dumps(payload, sort_keys=True) + "\
")


def _load_migration(path: Path) -> DependencyMigration:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return DependencyMigration(
            original_issue=int(payload["original_issue"]),
            repo=str(payload["repo"]),
            pieces=tuple(FiledPiece(**row) for row in payload["pieces"]),
            incoming=tuple(DependencyEdge(**row) for row in payload["incoming"]),
            outgoing=tuple(DependencyEdge(**row) for row in payload["outgoing"]),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise UsageError("migrate-deps: invalid persisted migration manifest") from exc


def _run_dependency_mutation(*, remove: bool, blocked: int, blocker: int, repo: str) -> bool:
    return rust_runtime.block_issue_dependency(
        proc.ProcRunner(), remove=remove, issue=str(blocked), blocker=str(blocker), repo=repo
    )


def _intra_piece_edges(design_tmpdir: Path, pieces: tuple[FiledPiece, ...]) -> tuple[DependencyEdge, ...]:
    deps_path = design_tmpdir / "decompose" / "partition-deps.tsv"
    if not deps_path.is_file() or deps_path.is_symlink():
        raise UsageError("migrate-deps: missing partition-deps.tsv")
    issue_by_piece = {piece.piece: piece.issue for piece in pieces}
    edges: list[DependencyEdge] = []
    for line in deps_path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) != PARTITION_DEP_FIELD_COUNT or not all(part.isdigit() for part in parts):
            raise UsageError("migrate-deps: invalid partition dependency row")
        blocker_piece, blocked_piece = (int(part) for part in parts)
        if blocker_piece not in issue_by_piece or blocked_piece not in issue_by_piece or blocker_piece == blocked_piece:
            raise UsageError("migrate-deps: partition dependency references an unknown piece")
        edges.append(DependencyEdge(blocked=issue_by_piece[blocked_piece], blocker=issue_by_piece[blocker_piece]))
    return tuple(edges)


def _replacement_edges(migration: DependencyMigration) -> tuple[DependencyEdge, ...]:
    edges: list[DependencyEdge] = []
    for original in migration.incoming:
        edges.extend(DependencyEdge(blocked=piece.issue, blocker=original.blocker) for piece in migration.pieces)
    for original in migration.outgoing:
        edges.extend(DependencyEdge(blocked=original.blocked, blocker=piece.issue) for piece in migration.pieces)
    return tuple(edges)


def _edge_present(edge: DependencyEdge, *, repo: str) -> bool:
    blocked_by, _blocking = _read_dependencies(issue=edge.blocked, repo=repo)
    return edge.blocker in blocked_by


def _migration_postcondition(migration: DependencyMigration) -> bool:
    if any(not _edge_present(edge, repo=migration.repo) for edge in _replacement_edges(migration)):
        return False
    return all(not _edge_present(edge, repo=migration.repo) for edge in (*migration.incoming, *migration.outgoing))


def _intra_piece_postcondition(*, design_tmpdir: Path, pieces: tuple[FiledPiece, ...]) -> bool:
    return all(_edge_present(edge, repo=pieces[0].repo) for edge in _intra_piece_edges(design_tmpdir, pieces))


def _live_original_edges_match_migration(migration: DependencyMigration) -> bool:
    incoming_numbers, blocking_numbers = _read_dependencies(issue=migration.original_issue, repo=migration.repo)
    live_incoming = {DependencyEdge(blocked=migration.original_issue, blocker=number) for number in incoming_numbers}
    live_outgoing = {DependencyEdge(blocked=number, blocker=migration.original_issue) for number in blocking_numbers}
    expected_incoming = set(migration.incoming)
    expected_outgoing = set(migration.outgoing)
    if not live_incoming <= expected_incoming or not live_outgoing <= expected_outgoing:
        return False
    for edge in expected_incoming - live_incoming:
        if any(not _edge_present(DependencyEdge(blocked=piece.issue, blocker=edge.blocker), repo=migration.repo) for piece in migration.pieces):
            return False
    for edge in expected_outgoing - live_outgoing:
        if any(not _edge_present(DependencyEdge(blocked=edge.blocked, blocker=piece.issue), repo=migration.repo) for piece in migration.pieces):
            return False
    return True


def _record_migration_failure(design_tmpdir: Path, *, phase: str, detail: str) -> str:
    output_file = design_tmpdir / "decompose" / "migration-failure.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(f"phase={phase}\n{detail}\n", encoding="utf-8")
    _emit_kv(key="DECOMPOSE_DEPS_PHASE", value=phase)
    _append_failure(design_tmpdir, site="design decompose migrate-deps", tool=phase, exit_code=1, output_file=output_file)
    return "failed"


def _apply_migration(migration: DependencyMigration) -> bool:
    for edge in _replacement_edges(migration):
        if not _edge_present(edge, repo=migration.repo) and (not _run_dependency_mutation(remove=False, blocked=edge.blocked, blocker=edge.blocker, repo=migration.repo) or not _edge_present(edge, repo=migration.repo)):
            return False
    if not _live_original_edges_match_migration(migration):
        return False
    for edge in (*migration.incoming, *migration.outgoing):
        if _edge_present(edge, repo=migration.repo) and (not _run_dependency_mutation(remove=True, blocked=edge.blocked, blocker=edge.blocker, repo=migration.repo) or _edge_present(edge, repo=migration.repo)):
            return False
    return _live_original_edges_match_migration(migration) and _migration_postcondition(migration)


def migrate_dependencies(*, design_tmpdir: Path, original_issue: str, repo: str) -> str:
    if not original_issue.isdigit() or int(original_issue) < 1 or re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repo) is None:
        raise UsageError("migrate-deps: invalid issue or repository")
    source_env = design_tmpdir / "source-env.sh"
    run_id = ""
    if source_env.is_file() and not source_env.is_symlink():
        for raw in source_env.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.removeprefix("export ").strip()
            if line.startswith("LARCH_RUN_ID="):
                run_id = line.partition("=")[2].strip().strip("'\"")
    authorized, reason = session_env.check_live_mutation_auth(context_file=source_env, operator_mode=False, run_id=run_id, trusted_root=design_tmpdir)
    if not authorized:
        _record_migration_failure(design_tmpdir, phase="authorization", detail=reason)
        _emit_kv(key="DECOMPOSE_DEPS_AUTH_REASON", value=reason)
        return "authorization-denied"
    try:
        pieces = filed_pieces(design_tmpdir, repo=repo)
        manifest_path = design_tmpdir / "decompose" / "dependency-migration.json"
        if manifest_path.is_file():
            migration = _load_migration(manifest_path)
            if migration.original_issue != int(original_issue) or migration.repo != repo or migration.pieces != pieces:
                raise UsageError("migrate-deps: persisted migration does not match filed mapping")
            if not _live_original_edges_match_migration(migration):
                return _record_migration_failure(design_tmpdir, phase="live-dependency-drift", detail="original dependency graph changed")
        else:
            incoming_numbers, blocking_numbers = _read_dependencies(issue=int(original_issue), repo=repo)
            migration = DependencyMigration(
                original_issue=int(original_issue), repo=repo, pieces=pieces,
                incoming=tuple(DependencyEdge(blocked=int(original_issue), blocker=number) for number in incoming_numbers),
                outgoing=tuple(DependencyEdge(blocked=number, blocker=int(original_issue)) for number in blocking_numbers),
            )
            _write_migration(manifest_path, migration)
        sentinel = design_tmpdir / ".decompose-deps-migrated"
        ready = _intra_piece_postcondition(design_tmpdir=design_tmpdir, pieces=pieces)
        if ready and sentinel.is_file() and _live_original_edges_match_migration(migration) and _migration_postcondition(migration):
            return "ok"
        sentinel.unlink(missing_ok=True)
        failure: tuple[str, str] | None = None
        if not ready or not _apply_migration(migration):
            failure = ("migration", "dependency mutation or verification failed")
        elif not _live_original_edges_match_migration(migration):
            failure = ("live-dependency-drift", "original dependency graph changed")
        elif not _intra_piece_postcondition(design_tmpdir=design_tmpdir, pieces=pieces):
            failure = ("intra-piece-postcondition", "declared piece dependency missing")
        if failure is not None:
            return _record_migration_failure(design_tmpdir, phase=failure[0], detail=failure[1])
        sentinel.touch()
        return "ok"
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return _record_migration_failure(design_tmpdir, phase="dependency-read", detail=str(exc))

def close_original_issue(*, design_tmpdir: Path, original_issue: str, repo: str) -> str:
    if (design_tmpdir / ".decompose-original-closed").is_file():
        return "ok"
    dec = design_tmpdir / "decompose"
    migration_path = dec / "dependency-migration.json"
    if not (design_tmpdir / ".decompose-deps-migrated").is_file() or not migration_path.is_file():
        raise UsageError("close-original: dependency migration is not complete")
    migration = _load_migration(migration_path)
    if (
        migration.original_issue != int(original_issue)
        or migration.repo != repo
        or not _live_original_edges_match_migration(migration)
        or not _migration_postcondition(migration)
        or not _intra_piece_postcondition(design_tmpdir=design_tmpdir, pieces=migration.pieces)
    ):
        raise UsageError("close-original: dependency migration postcondition failed")
    filed = dec / "partition-filed.md"
    if not filed.is_file():
        raise UsageError("close-original: missing partition-filed.md (run annotate first)")
    body = dec / "close-comment-draft.md"
    comment_sent = dec / ".decompose-close-comment-posted"
    summary_lines = ["This issue is **obviated by a partition** into follow-up work.", "", "## New pieces", ""]
    summary_lines.extend(
        line
        for line in filed.read_text(encoding="utf-8", errors="replace").splitlines()
        if re.match(r"^## Piece ", line) or re.match(r"^-\s\*\*Filed URL\*\*", line)
    )
    summary_lines.extend(["", "## Blocked-by chain", "", "See intra-batch dependency edges filed via /larch:issue (partition-deps.tsv).", ""])
    body.write_text("\n".join(summary_lines), encoding="utf-8")

    redacted = dec / "close-comment.redacted.md"
    redact_env = os.environ.get("DECOMPOSE_REDACT_SH", "").strip()
    redact_cmd = redact_env.split() if redact_env else ["python3", str(PLUGIN_ROOT / "python" / "cli.py"), "redact", "secrets"]
    rc, _combined = _run_command(redact_cmd, stdin=body, stdout=redacted)
    if rc != 0:
        _append_failure(design_tmpdir, site="design decompose close-original", tool="redact secrets", exit_code=rc, output_file=body)
        return "failed"

    def run_gh(argv: list[str]) -> tuple[None, int, str]:
        result = gh.command(proc, argv)
        return None, result.returncode, result.stdout + result.stderr

    if not comment_sent.is_file():
        result = retry.with_transient_retry(
            lambda: run_gh(["issue", "comment", original_issue, "--repo", repo, "--body-file", str(redacted)]),
        )
        if result.last_returncode != 0:
            _append_failure(design_tmpdir, site="design decompose close-original", tool="gh issue comment", exit_code=result.last_returncode, output_file=redacted)
            return "failed"
        comment_sent.touch()

    close_result = gh.issue_close(proc, original_issue, repo=repo)
    if close_result.returncode != 0:
        _append_failure(design_tmpdir, site="design decompose close-original", tool="gh issue close", exit_code=close_result.returncode, output_file=redacted)
        return "failed"
    comment_sent.unlink(missing_ok=True)
    (design_tmpdir / ".decompose-original-closed").touch()
    return "ok"


def _read_text_or_empty(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _render_decompose_prompt(archetype: str, *, primary_input: Path, discussion_file: Path | None, out: Path) -> None:
    prompts = PLUGIN_ROOT / "skills" / "design" / "scripts" / "decompose-prompts"
    arch_file = prompts / f"{archetype}.txt"
    common_tail = prompts / "_common-tail.txt"
    if not arch_file.is_file():
        raise UsageError(f"missing archetype template: {arch_file}")
    if not common_tail.is_file():
        raise UsageError(f"missing common tail: {common_tail}")
    primary = _read_text_or_empty(primary_input).strip() or "(empty primary input file)"
    disc_body = "(none — discussion-round1 artifact not passed or absent.)"
    if discussion_file is not None:
        disc_body = _read_text_or_empty(discussion_file).strip() or "(discussion path not readable)"
    full = arch_file.read_text(encoding="utf-8").replace("{COMMON_TAIL}", common_tail.read_text(encoding="utf-8"))
    full = full.replace("{PLAN_OR_FEATURE_BLOCK}", f"## Primary input\n\n{primary}\n\n")
    full = full.replace("{DISCUSSION_BLOCK}", f"## Discussion round 1\n\n{disc_body}\n\n")
    out.write_text(full, encoding="utf-8")


def _parse_kv_lines(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _write_json_line(*, path: Path, row: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        _ = handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def dispatch_panel(  # noqa: C901,PLR0912,PLR0915,RUF100
    *,
    design_tmpdir: Path,
    codex_present: bool,
    cursor_present: bool,
    mode: str,
    plan_file: Path | None = None,
    feature_file: Path | None = None,
    discussion_file: Path | None = None,
    timeout: int = 1800,
) -> None:
    dec = design_tmpdir / "decompose"
    dec.mkdir(parents=True, exist_ok=True)
    if mode == "plan":
        if plan_file is None or not plan_file.is_file():
            raise UsageError("plan mode requires --plan-file")
        primary_input = plan_file
    elif mode == "feature-only":
        if feature_file is None or not feature_file.is_file():
            raise UsageError("feature-only mode requires --feature-file")
        primary_input = feature_file
    else:
        raise UsageError("--mode must be plan or feature-only")
    feature = feature_file or (design_tmpdir / "feature-description.txt")
    if not feature.is_file():
        raise UsageError(f"feature-description not found (set --feature-file): {feature}")
    if discussion_file is not None and not discussion_file.is_file():
        raise UsageError(f"discussion file not found: {discussion_file}")

    manifest = dec / "decompose-slots.ndjson"
    panel_rows = dec / "panel-outputs.ndjson"
    manifest.write_text("", encoding="utf-8")
    panel_rows.write_text("", encoding="utf-8")

    if not codex_present and not cursor_present:
        generic_output = dec / "decomp-claude-generic-output.txt"
        generic_prompt = dec / "decomp-claude-generic.prompt"
        tail_src = dec / ".generic-tail-src.prompt"
        _render_decompose_prompt("decomposition-specialist", primary_input=primary_input, discussion_file=discussion_file, out=tail_src)
        parts: list[str] = ["You are a combined decomposition panel applying all four standard archetype lenses in a single pass. Address each lens below, then follow the shared output contract.", ""]
        prompts = PLUGIN_ROOT / "skills" / "design" / "scripts" / "decompose-prompts"
        for arch in DECOMPOSE_ARCHETYPES:
            lines = (prompts / f"{arch}.txt").read_text(encoding="utf-8").splitlines()
            prefix: list[str] = []
            for line in lines:
                prefix.append(line)
                if line == "Your focus:":
                    break
                if len(prefix) >= PROMPT_PREFIX_LINE_MAX:
                    break
            parts.extend(prefix)
            parts.append("")
        tail_lines = tail_src.read_text(encoding="utf-8").splitlines()[1:]
        parts.extend(tail_lines)
        generic_prompt.write_text("\n".join(parts) + "\n", encoding="utf-8")
        tail_src.unlink(missing_ok=True)
        env_launch = os.environ.get("LARCH_TEST_LAUNCH_CLAUDE_REVIEW", "").strip()
        launch_cmd: list[str] = [env_launch] if env_launch else [str(larch_entrypoint(PLUGIN_ROOT)), "agent", "launch-claude-review"]
        with (generic_output.with_suffix(generic_output.suffix + ".launch-stderr")).open("wb") as stderr_handle:
            launch: subprocess.CompletedProcess[bytes] = subprocess.run(
                [*launch_cmd, "--output", str(generic_output), "--prompt-file", str(generic_prompt), "--mode", "description", "--model", "claude-sonnet-4-6", "--timeout", str(timeout), "--timing-task-kind", "claude-decomp-generic", "--feature-file", str(feature)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=stderr_handle,
            )
        if not (generic_output.with_suffix(generic_output.suffix + ".done")).is_file():
            generic_output.with_suffix(generic_output.suffix + ".done").write_text(str(launch.returncode) + "\n", encoding="utf-8")
        status = "missing"
        if generic_output.is_file() and RECOMMENDATION_RE.search(generic_output.read_text(encoding="utf-8", errors="replace")):
            status = "ok"
        elif generic_output.is_file():
            status = "unparsed"
        _write_json_line(path=panel_rows, row={"archetype": "generic", "vendor": "claude", "output": str(generic_output), "status": status})
        dispatch_ok = launch.returncode == 0 and status == "ok"
        for k, v in {
            "DISPATCH_OK": dispatch_ok,
            "FALLBACK_COUNT": 0,
            "COMBINED_FALLBACK_COUNT": 0,
            "STATIC_DISPATCH_OK": dispatch_ok,
            "DYNAMIC_DISPATCH_OK": True,
        }.items():
            _emit_kv(key=k, value=v)
        degraded = not dispatch_ok
        _emit_kv(key="PANEL_OUTPUTS_FILE", value=panel_rows)
        _emit_kv(key="DEGRADED_PANEL", value=degraded)
        _emit_kv(key="PANEL_STATUS", value="panel-failed" if degraded else "ok")
        return

    decompose_policy = external_defaults.role_default("design.decompose_panel").decompose_panel_policy
    allowed_tools = set(decompose_policy.parallel_tools if decompose_policy else ("cursor", "codex"))
    for arch in DECOMPOSE_ARCHETYPES:
        if cursor_present and "cursor" in allowed_tools:
            slot = next(row for row in external_defaults.slot_defaults("design.decompose_panel") if row.archetype == arch and row.tool == "cursor")
            prompt_file = dec / f"render-decomp-cursor-{arch}.prompt"
            output = dec / slot.output
            _render_decompose_prompt(arch, primary_input=primary_input, discussion_file=discussion_file, out=prompt_file)
            _write_json_line(path=manifest, row={"slot": slot.slot, "tool": slot.tool, "output": str(output), "prompt_file": str(prompt_file)})
        if codex_present and "codex" in allowed_tools:
            slot = next(row for row in external_defaults.slot_defaults("design.decompose_panel") if row.archetype == arch and row.tool == "codex")
            prompt_file = dec / f"render-decomp-codex-{arch}.prompt"
            output = dec / slot.output
            _render_decompose_prompt(arch, primary_input=primary_input, discussion_file=discussion_file, out=prompt_file)
            _write_json_line(path=manifest, row={"slot": slot.slot, "tool": slot.tool, "output": str(output), "prompt_file": str(prompt_file)})
    if "DECOMPOSE_PANEL_WATERFALL_SH" in os.environ:
        waterfall_argv: list[str] = [os.environ["DECOMPOSE_PANEL_WATERFALL_SH"]]
    else:
        waterfall_argv = [str(larch_entrypoint(PLUGIN_ROOT)), "agent", "dispatch-waterfall"]
    cmd: list[str] = [*waterfall_argv, "--slots-file", str(manifest), "--codex-present", str(codex_present).lower(), "--cursor-present", str(cursor_present).lower(), "--mode", "description"]
    if decompose_policy is None or decompose_policy.panel_no_fallback:
        cmd.append("--no-fallback")
    cmd.extend(["--require-result-pattern", "^[[:space:]]*## Recommendation", "--feature-file", str(feature), "--timeout", str(timeout)])
    if mode == "plan" and plan_file is not None:
        cmd.extend(["--plan-file", str(plan_file)])
    wf: subprocess.CompletedProcess[str] = subprocess.run(cmd, check=False, capture_output=True, text=True)
    dispatch_out = wf.stdout
    if wf.returncode != 0:
        cap = dec / "decompose-waterfall-failure.log"
        cap.write_text(dispatch_out, encoding="utf-8")
        _append_failure(design_tmpdir, site="design Step 2b.5 decompose panel", tool="agent dispatch-waterfall", exit_code=wf.returncode, output_file=cap)
    kvs: dict[str, str] = _parse_kv_lines(dispatch_out)
    dispatch_ok = kvs.get("DISPATCH_OK", "")
    fallback_count = kvs.get("FALLBACK_COUNT", "0")
    combined_fallback_count = kvs.get("COMBINED_FALLBACK_COUNT", fallback_count or "0")
    static_dispatch_ok = kvs.get("STATIC_DISPATCH_OK", "true")
    all_outputs_file = kvs.get("ALL_OUTPUT_FILES_PATH", "")
    all_slots_dropped = kvs.get("ALL_SLOTS_DROPPED", "")
    manifest_rows: list[dict[str, object]] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row: object = json.loads(line)
        except json.JSONDecodeError:
            _emit_kv(key="PANEL_OUTPUTS_FILE", value=panel_rows)
            _emit_kv(key="DEGRADED_PANEL", value=True)
            _emit_kv(key="PANEL_STATUS", value="panel-failed")
            raise UsageError("malformed decompose-slots.ndjson") from None
        if not isinstance(row, dict):
            _emit_kv(key="PANEL_OUTPUTS_FILE", value=panel_rows)
            _emit_kv(key="DEGRADED_PANEL", value=True)
            _emit_kv(key="PANEL_STATUS", value="panel-failed")
            raise UsageError("malformed decompose-slots.ndjson") from None
        manifest_rows.append(cast("dict[str, object]", row))
    slot_count = len(manifest_rows)
    try:
        combined_fallback_n = int(combined_fallback_count)
    except ValueError:
        combined_fallback_n = 0
    degraded = static_dispatch_ok == "false" or combined_fallback_n > (slot_count // 2) or all_slots_dropped == "true"
    resolved_paths: list[str] = []
    if all_outputs_file and Path(all_outputs_file).is_file():
        resolved_paths = [line for line in Path(all_outputs_file).read_text(encoding="utf-8").splitlines() if line]
    if slot_count > 0 and len(resolved_paths) < slot_count:
        degraded = True
    usable = 0
    warned_missing_paths = False

    def match_resolved(manifest_out: str) -> str:
        base = Path(manifest_out).name
        for rp in resolved_paths:
            if rp == manifest_out or Path(rp).name == base:
                return rp
        return ""

    for row in manifest_rows:
        manifest_out = str(row.get("output", ""))
        slot = str(row.get("slot", ""))
        arch = slot.removeprefix("decomp-cursor-").removeprefix("decomp-codex-")
        vendor = str(row.get("tool", ""))
        if resolved_paths:
            out_resolved = match_resolved(manifest_out)
            if not out_resolved:
                _write_json_line(path=panel_rows, row={"archetype": arch, "vendor": vendor, "output": manifest_out, "status": "missing"})
                continue
        else:
            if all_slots_dropped == "true":
                continue
            if not warned_missing_paths:
                _err("decompose-panel-dispatch.sh: ALL_OUTPUT_FILES_PATH empty or missing; skipping manifest rows (no resolved paths)")
                warned_missing_paths = True
            continue
        status = "missing"
        path = Path(out_resolved)
        if path.is_file() and RECOMMENDATION_RE.search(path.read_text(encoding="utf-8", errors="replace")):
            status = "ok"
            usable += 1
        elif path.is_file():
            status = "unparsed"
        _write_json_line(path=panel_rows, row={"archetype": arch, "vendor": vendor, "output": out_resolved, "status": status})
    panel_status = "ok"
    if usable == 0:
        panel_status = "panel-failed"
    elif degraded:
        panel_status = "degraded"
    if wf.returncode != 0:
        degraded = True
        if usable > 0 and panel_status == "ok":
            panel_status = "degraded"
    for line in dispatch_out.splitlines():
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key == "WARN":
            _emit_kv(key="WARN", value=val)
        else:
            _emit_kv(key=key, value=val)
    _emit_kv(key="PANEL_OUTPUTS_FILE", value=panel_rows)
    _emit_kv(key="DEGRADED_PANEL", value=degraded)
    _emit_kv(key="PANEL_STATUS", value=panel_status)


def aggregate_partition(*, design_tmpdir: Path, panel_outputs_file: Path, codex_present: bool, cursor_present: bool, output: Path, timeout: int = 1800) -> str:
    if not panel_outputs_file.is_file():
        raise UsageError("--panel-outputs-file must exist")
    dec = design_tmpdir / "decompose"
    dec.mkdir(parents=True, exist_ok=True)
    combined = dec / "combined-proposals.txt"
    with combined.open("w", encoding="utf-8") as handle:
        for line in panel_outputs_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row: object = json.loads(line)
            except json.JSONDecodeError:
                _emit_kv(key="AGGREGATOR_STATUS", value="failed")
                raise UsageError("malformed panel-outputs.ndjson") from None
            if not isinstance(row, dict):
                _emit_kv(key="AGGREGATOR_STATUS", value="failed")
                raise UsageError("malformed panel-outputs.ndjson") from None
            row_obj = cast("dict[str, object]", row)
            outp = Path(str(row_obj.get("output", "")))
            _ = handle.write(f"\n## Panel output ({row_obj.get('archetype', '')} / {row_obj.get('vendor', '')})\n\n")
            if outp.is_file():
                _ = handle.write(outp.read_text(encoding="utf-8", errors="replace"))
            else:
                _ = handle.write(f"(missing file: {outp})\n")
            _ = handle.write("\n")
    feature = design_tmpdir / "feature-description.txt"
    if not feature.is_file():
        raise UsageError(f"missing {feature} for aggregator context")
    merge_prompt = dec / "aggregator-partition-merge.prompt"
    merge_prompt.write_text(
        "You are the decomposition aggregator. Below are eight independent partition proposals from external reviewers (four archetypes x two vendors).\n\n"
        "Task: produce **one** canonical merged partition that best satisfies the independently-mergeable constraint (acyclic blocker graph) while minimizing unnecessary coupling.\n\n"
        + combined.read_text(encoding="utf-8")
        + "\nOutput **only** Markdown matching this schema (first heading must be detectable):\n\n"
        "## Recommendation\nsplit | no-split\n\n"
        "## Pieces (only when Recommendation is split)\n\n"
        "### Piece 1: <short title>\n"
        "- Scope: <files / behaviors covered>\n"
        "- Firm-headings: <bare parent-plan paths, comma-separated; no `###` or backticks>\n"
        "- Acceptance: <one or more implementable criteria for this piece>\n"
        "- Dependencies: none | blocked-by Piece N[, Piece M ...]\n"
        "- Diff_lines estimate: <integer>\n"
        "- Why independently mergeable: <prose>\n\n"
        "### Piece 2: ...\n",
        encoding="utf-8",
    )
    agg_out = dec / "aggregator-raw-output.txt"
    slots = dec / "aggregator-slots.ndjson"
    slot = external_defaults.slot_defaults("design.decompose_aggregator")[0]
    slots.write_text(json.dumps({"slot": slot.slot, "tool": slot.tool, "output": str(agg_out), "prompt_file": str(merge_prompt)}, separators=(",", ":")) + "\n", encoding="utf-8")
    if "DECOMPOSE_AGGREGATE_WATERFALL_SH" in os.environ:
        waterfall_argv: list[str] = [os.environ["DECOMPOSE_AGGREGATE_WATERFALL_SH"]]
    else:
        waterfall_argv = [str(larch_entrypoint(PLUGIN_ROOT)), "agent", "dispatch-waterfall"]
    cmd: list[str] = [*waterfall_argv, "--slots-file", str(slots), "--codex-present", str(codex_present).lower(), "--cursor-present", str(cursor_present).lower(), "--mode", "description", "--feature-file", str(feature), "--require-result-pattern", "^[[:space:]]*## Recommendation", "--timeout", str(timeout)]
    result: subprocess.CompletedProcess[str] = subprocess.run(cmd, check=False, capture_output=True, text=True)
    kvs: dict[str, str] = _parse_kv_lines(result.stdout)
    final_out = agg_out
    paths_file = kvs.get("ALL_OUTPUT_FILES_PATH", "")
    if paths_file and Path(paths_file).is_file():
        first = Path(paths_file).read_text(encoding="utf-8").splitlines()
        if first:
            final_out = Path(first[0])
    if result.returncode == 0 and kvs.get("DISPATCH_OK", "false") == "true" and final_out.is_file() and RECOMMENDATION_RE.search(final_out.read_text(encoding="utf-8", errors="replace")):
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(final_out, output)
        return "ok"
    return "failed"


def prepare_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-file-issues.sh")
    parser = argparse.ArgumentParser(prog="decompose prepare", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--partition-file", required=True)
    parser.add_argument("--issue-number", default="")
    try:
        args = parser.parse_args(argv)
        design_tmpdir = _validate_design_tmpdir(args.design_tmpdir)
        status, witness = prepare_partition_issues(design_tmpdir=design_tmpdir, partition_file=Path(args.partition_file), issue_number=args.issue_number)
        _emit_kv(key="DECOMPOSE_PARTITION_STATUS", value=status)
        if witness:
            _emit_kv(key="DECOMPOSE_PARTITION_CYCLE_WITNESS", value=witness)
        if status != "ok":
            (design_tmpdir / "decompose" / "partition-input.txt").unlink(missing_ok=True)
            (design_tmpdir / "decompose" / "partition-deps.tsv").unlink(missing_ok=True)
            return 2 if status != "cycle-detected" else 0
        return 0
    except (SystemExit, UsageError) as exc:
        _err(f"decompose prepare: {exc}")
        return 2


def annotate_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-file-issues.sh")
    parser = argparse.ArgumentParser(prog="decompose annotate", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--issue-stdout-file", required=True)
    parser.add_argument("--issue-number", default="")
    try:
        args = parser.parse_args(argv)
        annotate_partition_issues(design_tmpdir=_validate_design_tmpdir(args.design_tmpdir), issue_stdout_file=Path(args.issue_stdout_file))
        return 0
    except (SystemExit, UsageError) as exc:
        _err(f"decompose annotate: {exc}")
        return 2


def migrate_deps_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-file-issues.sh")
    parser = argparse.ArgumentParser(prog="decompose migrate-deps", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--original-issue", required=True)
    parser.add_argument("--repo", required=True)
    try:
        args = parser.parse_args(argv)
        design_tmpdir = _validate_design_tmpdir(args.design_tmpdir)
        status = migrate_dependencies(design_tmpdir=design_tmpdir, original_issue=args.original_issue, repo=args.repo)
        _emit_kv(key="DECOMPOSE_DEPS_STATUS", value=status)
        _emit_kv(key="DECOMPOSE_DEPS_SENTINEL", value=design_tmpdir / ".decompose-deps-migrated")
        return 0 if status == "ok" else 1
    except (SystemExit, UsageError) as exc:
        _err(f"decompose migrate-deps: {exc}")
        return 2
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        _err(f"decompose migrate-deps: {exc}")
        return 1


def close_original_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-file-issues.sh")
    parser = argparse.ArgumentParser(prog="decompose close-original", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--original-issue", required=True)
    parser.add_argument("--repo", required=True)
    try:
        args = parser.parse_args(argv)
        status = close_original_issue(design_tmpdir=_validate_design_tmpdir(args.design_tmpdir), original_issue=args.original_issue, repo=args.repo)
        _emit_kv(key="CLOSE_ORIGINAL_STATUS", value=status)
        return 0 if status == "ok" else 1
    except (SystemExit, UsageError) as exc:
        _err(f"decompose close-original: {exc}")
        return 2


def panel_dispatch_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-panel-dispatch.sh")
    parser = argparse.ArgumentParser(prog="decompose panel-dispatch", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--codex-present", default="")
    parser.add_argument("--cursor-present", default="")
    parser.add_argument("--codex-binary-found", default="")
    parser.add_argument("--cursor-binary-found", default="")
    parser.add_argument("--mode", required=True)
    parser.add_argument("--plan-file", default="")
    parser.add_argument("--feature-file", default="")
    parser.add_argument("--discussion-round1-file", default="")
    parser.add_argument("--timeout", default="1800")
    try:
        args = parser.parse_args(argv)
        dispatch_panel(
            design_tmpdir=_validate_design_tmpdir(args.design_tmpdir),
            codex_present=_binary_bool(value=args.codex_binary_found, binary="codex"),
            cursor_present=_binary_bool(value=args.cursor_binary_found, binary="cursor"),
            mode=args.mode,
            plan_file=Path(args.plan_file) if args.plan_file else None,
            feature_file=Path(args.feature_file) if args.feature_file else None,
            discussion_file=Path(args.discussion_round1_file) if args.discussion_round1_file else None,
            timeout=_positive_int(value=args.timeout, flag="--timeout"),
        )
        return 0
    except (SystemExit, UsageError) as exc:
        _err(f"decompose-panel-dispatch.sh: {exc}")
        return 2


def aggregate_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="decompose-aggregator.sh")
    parser = argparse.ArgumentParser(prog="decompose aggregate", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--panel-outputs-file", required=True)
    parser.add_argument("--codex-present", default="")
    parser.add_argument("--cursor-present", default="")
    parser.add_argument("--codex-binary-found", default="")
    parser.add_argument("--cursor-binary-found", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", default="1800")
    try:
        args = parser.parse_args(argv)
        status = aggregate_partition(
            design_tmpdir=_validate_design_tmpdir(args.design_tmpdir),
            panel_outputs_file=Path(args.panel_outputs_file),
            codex_present=_binary_bool(value=args.codex_binary_found, binary="codex"),
            cursor_present=_binary_bool(value=args.cursor_binary_found, binary="cursor"),
            output=Path(args.output),
            timeout=_positive_int(value=args.timeout, flag="--timeout"),
        )
        _emit_kv(key="AGGREGATOR_STATUS", value=status)
        if status == "ok":
            _emit_kv(key="AGGREGATOR_OUTPUT", value=args.output)
        return 0
    except (SystemExit, UsageError) as exc:
        _err(f"decompose-aggregator.sh: {exc}")
        return 2
