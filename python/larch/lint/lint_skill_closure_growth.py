"""Report and ratchet always-loaded skill markdown closure size."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_RELPATH = Path("python/skill-closure-baseline.json")
GATED_SKILLS = ("design", "implement")
METRIC_FIELDS = (
    "skill_md_lines",
    "skill_md_estimated_tokens",
    "skill_md_content_estimated_tokens",
    "closure_lines",
    "closure_estimated_tokens",
    "closure_content_estimated_tokens",
)
BASELINE_KEYS = frozenset({"skill", *METRIC_FIELDS, "files"})
PLUGIN_ROOT_PREFIX = "${CLAUDE_PLUGIN_ROOT}/"
SUPPRESSED_IMPLEMENT_SECTIONS = frozenset({"Checks Failure Entry Macro", "Durable Bail to Step 18 Macro"})
CONDITIONAL_DESIGN_SECTIONS = frozenset(
    {
        "Plan command validator failure (shared)",
        "Split-path (decomposition panel)",
    }
)

MANDATORY_DIRECTIVE_RE = re.compile(r"MANDATORY\s+(?:[—-]\s+)?READ\s+ENTIRE\s+FILE", re.IGNORECASE)
READ_COMPLETELY_RE = re.compile(r"\bread\b(?P<body>.*?\.md.*?)\bcompletely\b", re.IGNORECASE)
MARKDOWN_PATH_RE = re.compile(
    r"`(?P<ticked>[^`\n]+?\.md)`|(?P<bare>(?:\$\{CLAUDE_PLUGIN_ROOT\}/|\./|/)?[A-Za-z0-9_./{}$+-]+\.md)"
)
NON_MD_PATH_RE = re.compile(
    r"`[^`\n]+\.[A-Za-z0-9]+`|(?:\$\{CLAUDE_PLUGIN_ROOT\}/|\./|/)?[A-Za-z0-9_./{}$+-]+\.[A-Za-z0-9]+"
)
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
STEP_COMMENT_RE = re.compile(r"^<!--\s*step:", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+\.\s+)(?P<body>.*)$")
CONDITIONAL_PREFIX_RE = re.compile(
    r"^(?:if|when|whenever|only\s+if|only\s+when|for\s+`|for\s+\*\*`|on\s+`)",
    re.IGNORECASE,
)
CONDITIONAL_TEXT_RE = re.compile(
    r"\b(?:if|when|whenever|only\s+if|only\s+when|conditional|branch(?:es|ing)?|route(?:s|ing)?|predicate|retained)\b",
    re.IGNORECASE,
)
CONDITIONAL_SUFFIX_RE = re.compile(r"\((?:if|when|only\s+if|only\s+when)\b", re.IGNORECASE)
BRANCH_BULLET_RE = re.compile(r"^(?:\*\*)?`[^`]+`(?:\*\*)?\s*(?:\([^)]*\))?\s*:")
RUNTIME_MARKDOWN_OPERAND_RE = re.compile(
    r"^\$(?:[A-Z_][A-Z0-9_]*|\{(?!CLAUDE_PLUGIN_ROOT\})[A-Z_][A-Z0-9_]*\})/"
)


class BaselineRowDict(TypedDict):
    skill: str
    skill_md_lines: int
    skill_md_estimated_tokens: int
    skill_md_content_estimated_tokens: int
    closure_lines: int
    closure_estimated_tokens: int
    closure_content_estimated_tokens: int
    files: list[str]


class ScanError(ValueError):
    """Raised when closure scanning cannot produce a trusted result."""


class BaselineError(ValueError):
    """Raised when the committed closure baseline cannot be trusted."""


@dataclass(frozen=True)
class FileMetrics:
    lines: int
    estimated_tokens: int
    content_estimated_tokens: int


@dataclass(frozen=True)
class SkillClosureResult:
    skill: str
    skill_md_lines: int
    skill_md_estimated_tokens: int
    skill_md_content_estimated_tokens: int
    closure_lines: int
    closure_estimated_tokens: int
    closure_content_estimated_tokens: int
    files: tuple[str, ...]
    conditional_lines: int
    conditional_estimated_tokens: int
    conditional_content_estimated_tokens: int
    conditional_files: tuple[str, ...]

    def to_baseline_row(self) -> BaselineRowDict:
        return {
            "skill": self.skill,
            "skill_md_lines": self.skill_md_lines,
            "skill_md_estimated_tokens": self.skill_md_estimated_tokens,
            "skill_md_content_estimated_tokens": self.skill_md_content_estimated_tokens,
            "closure_lines": self.closure_lines,
            "closure_estimated_tokens": self.closure_estimated_tokens,
            "closure_content_estimated_tokens": self.closure_content_estimated_tokens,
            "files": list(self.files),
        }


@dataclass(frozen=True)
class BaselineRow:
    skill: str
    skill_md_lines: int
    skill_md_estimated_tokens: int
    skill_md_content_estimated_tokens: int
    closure_lines: int
    closure_estimated_tokens: int
    closure_content_estimated_tokens: int
    files: tuple[str, ...]


@dataclass(frozen=True)
class DirectiveMatch:
    index: int
    clause: str
    supported: bool


@dataclass(frozen=True)
class DirectiveContext:
    line: str
    line_number: int
    match: DirectiveMatch
    conditional_section: bool


@dataclass(frozen=True)
class ScanState:
    suppressed_section: str | None = None
    conditional_section_depth: int | None = None


def _estimated_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def _content_text(text: str) -> str:
    return "".join(f"{line}\n" for line in text.splitlines() if line.strip())


def _read_file_metrics(path: Path) -> FileMetrics:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ScanError(f"cannot read {path}: {exc}") from exc
    return FileMetrics(
        lines=len(text.splitlines()),
        estimated_tokens=_estimated_tokens(text),
        content_estimated_tokens=_estimated_tokens(_content_text(text)),
    )


def _repo_relative(root: Path, path: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ScanError(f"referenced path escapes repository: {path}") from exc
    if ".." in rel.parts:
        raise ScanError(f"referenced path escapes repository: {path}")
    return rel.as_posix()


def _clean_raw_path(raw: str) -> str:
    return raw.strip().strip("`.,);]")


def _is_runtime_markdown_operand(raw: str) -> bool:
    cleaned = _clean_raw_path(raw)
    return RUNTIME_MARKDOWN_OPERAND_RE.match(cleaned) is not None


def _resolve_markdown_path(root: Path, source_path: Path, raw_path: str) -> str:
    cleaned = _clean_raw_path(raw_path)
    if cleaned.startswith(PLUGIN_ROOT_PREFIX):
        candidate = root / cleaned.removeprefix(PLUGIN_ROOT_PREFIX)
    else:
        raw_candidate = Path(cleaned)
        if raw_candidate.is_absolute():
            candidate = raw_candidate
        else:
            repo_candidate = root / cleaned
            source_candidate = source_path.parent / cleaned
            candidate = repo_candidate if repo_candidate.exists() else source_candidate
    rel = _repo_relative(root, candidate)
    if not candidate.is_file():
        raise ScanError(f"referenced markdown file not found: {rel}")
    return rel


def _extract_markdown_paths(root: Path, source_path: Path, clause: str, *, strict: bool) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for match in MARKDOWN_PATH_RE.finditer(clause):
        raw_path = match.group("ticked") or match.group("bare")
        if raw_path is None:
            continue
        if _is_runtime_markdown_operand(raw_path):
            continue
        try:
            rel = _resolve_markdown_path(root, source_path, raw_path)
        except ScanError:
            if strict:
                raise
            continue
        if rel not in seen:
            seen.add(rel)
            paths.append(rel)
    return paths


def _has_markdown_operand(clause: str) -> bool:
    return MARKDOWN_PATH_RE.search(clause) is not None


def _mandatory_clause(remainder: str) -> str:
    read_match = READ_COMPLETELY_RE.search(remainder)
    if read_match is not None:
        return remainder[read_match.start() : read_match.end()]
    path_match = MARKDOWN_PATH_RE.search(remainder)
    if path_match is None:
        return remainder
    sentence_end_match = re.search(r"\.(?:\s|$)", remainder[path_match.end() :])
    if sentence_end_match is None:
        return remainder
    sentence_end = path_match.end() + sentence_end_match.start()
    return remainder[: sentence_end + 1]


def _directive_matches(line: str) -> list[DirectiveMatch]:
    matches = [
        DirectiveMatch(
            index=match.start(),
            clause=_mandatory_clause(line[match.end() :]),
            supported=True,
        )
        for match in MANDATORY_DIRECTIVE_RE.finditer(line)
    ]
    for match in READ_COMPLETELY_RE.finditer(line):
        if any(existing.index <= match.start() for existing in matches):
            continue
        matches.append(DirectiveMatch(index=match.start(), clause=match.group(0), supported=True))
    return sorted(matches, key=lambda item: item.index)


def _first_table_cell(stripped_line: str) -> str | None:
    if not stripped_line.startswith("|"):
        return None
    cells = stripped_line.strip("|").split("|")
    if not cells:
        return None
    return cells[0].strip().strip("* ")


def _table_cell_is_route_predicate(cell: str) -> bool:
    normalized = cell.strip().strip("`").lower()
    return (
        "=" in normalized
        or normalized.startswith(("if ", "when ", "on "))
        or any(word in normalized for word in ("route", "branch", "predicate", "status", "next_action"))
    )


def _body_after_bullet(stripped_line: str) -> str:
    bullet_match = BULLET_RE.match(stripped_line)
    if bullet_match is None:
        return stripped_line
    return bullet_match.group("body").lstrip()


def _line_is_conditional(line: str, directive_index: int) -> bool:
    stripped = line.strip()
    first_cell = _first_table_cell(stripped)
    if first_cell is not None and _table_cell_is_route_predicate(first_cell):
        return True

    body = _body_after_bullet(stripped)
    if CONDITIONAL_PREFIX_RE.match(body):
        return True
    if body.startswith(("`", "**`")) or BRANCH_BULLET_RE.match(body):
        return True

    prefix = line[:directive_index]
    if CONDITIONAL_TEXT_RE.search(prefix) is not None:
        return True

    suffix = line[directive_index:]
    return CONDITIONAL_SUFFIX_RE.search(suffix) is not None


def _update_design_scan_state(line: str, state: ScanState) -> ScanState:
    if STEP_COMMENT_RE.match(line):
        return ScanState()
    heading_match = HEADING_RE.match(line)
    if heading_match is None:
        return state
    heading_depth = len(heading_match.group("marks"))
    title = heading_match.group("title").strip("# ").strip()
    next_state = state
    if state.conditional_section_depth is not None and heading_depth <= state.conditional_section_depth:
        next_state = ScanState()
    if next_state.conditional_section_depth is None and title in CONDITIONAL_DESIGN_SECTIONS:
        return ScanState(conditional_section_depth=heading_depth)
    return next_state


def _update_implement_scan_state(line: str, state: ScanState) -> ScanState:
    heading_match = HEADING_RE.match(line)
    if heading_match is None:
        return state
    title = heading_match.group("title").strip("# ").strip()
    if title in SUPPRESSED_IMPLEMENT_SECTIONS:
        return ScanState(suppressed_section=title)
    if state.suppressed_section is not None:
        return ScanState()
    return state


def _update_scan_state(skill: str, line: str, state: ScanState) -> ScanState:
    if skill == "design":
        return _update_design_scan_state(line, state)
    if skill == "implement":
        return _update_implement_scan_state(line, state)
    return state


def _paths_for_directive_match(
    root: Path,
    skill_path: Path,
    context: DirectiveContext,
) -> tuple[bool, list[str]]:
    is_conditional = context.conditional_section or _line_is_conditional(context.line, context.match.index)
    paths = _extract_markdown_paths(root, skill_path, context.match.clause, strict=not is_conditional)
    if is_conditional:
        return True, paths
    if paths:
        return False, paths
    if _has_markdown_operand(context.match.clause):
        raise ScanError(
            f"{_repo_relative(root, skill_path)}:{context.line_number}: "
            "supported read directive has no resolvable markdown path"
        )
    if NON_MD_PATH_RE.search(context.match.clause):
        return False, paths
    raise ScanError(
        f"{_repo_relative(root, skill_path)}:{context.line_number}: "
        "supported read directive has no resolvable markdown path"
    )


def _append_unique_paths(references: list[str], seen: set[str], paths: Iterable[str]) -> None:
    for rel in paths:
        if rel not in seen:
            seen.add(rel)
            references.append(rel)


def parse_direct_markdown_references(root: Path, skill: str, skill_path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        lines = skill_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ScanError(f"cannot read {skill_path}: {exc}") from exc

    eager_references: list[str] = []
    eager_seen: set[str] = set()
    conditional_references: list[str] = []
    conditional_seen: set[str] = set()
    state = ScanState()
    for line_number, line in enumerate(lines, start=1):
        state = _update_scan_state(skill, line, state)
        if state.suppressed_section is not None:
            continue
        for match in _directive_matches(line):
            context = DirectiveContext(
                line,
                line_number,
                match,
                conditional_section=state.conditional_section_depth is not None,
            )
            is_conditional, paths = _paths_for_directive_match(root, skill_path, context)
            if is_conditional:
                _append_unique_paths(conditional_references, conditional_seen, paths)
            else:
                _append_unique_paths(eager_references, eager_seen, paths)
    conditional_only = tuple(rel for rel in conditional_references if rel not in eager_seen)
    return tuple(eager_references), conditional_only


def scan_skill(root: Path, skill: str) -> SkillClosureResult:
    skill_path = root / "skills" / skill / "SKILL.md"
    if not skill_path.is_file():
        raise ScanError(f"skill root not found: skills/{skill}/SKILL.md")
    skill_rel = _repo_relative(root, skill_path)
    eager_references, conditional_references = parse_direct_markdown_references(root, skill, skill_path)
    files = (skill_rel, *eager_references)
    metrics = {rel: _read_file_metrics(root / rel) for rel in files}
    conditional_metrics = {rel: _read_file_metrics(root / rel) for rel in conditional_references}
    skill_metrics = metrics[skill_rel]
    closure_lines = sum(item.lines for item in metrics.values())
    closure_tokens = sum(item.estimated_tokens for item in metrics.values())
    closure_content_tokens = sum(item.content_estimated_tokens for item in metrics.values())
    conditional_lines = sum(item.lines for item in conditional_metrics.values())
    conditional_tokens = sum(item.estimated_tokens for item in conditional_metrics.values())
    conditional_content_tokens = sum(item.content_estimated_tokens for item in conditional_metrics.values())
    return SkillClosureResult(
        skill=skill,
        skill_md_lines=skill_metrics.lines,
        skill_md_estimated_tokens=skill_metrics.estimated_tokens,
        skill_md_content_estimated_tokens=skill_metrics.content_estimated_tokens,
        closure_lines=closure_lines,
        closure_estimated_tokens=closure_tokens,
        closure_content_estimated_tokens=closure_content_tokens,
        files=files,
        conditional_lines=conditional_lines,
        conditional_estimated_tokens=conditional_tokens,
        conditional_content_estimated_tokens=conditional_content_tokens,
        conditional_files=conditional_references,
    )


def scan_all(root: Path) -> list[SkillClosureResult]:
    return [scan_skill(root, skill) for skill in GATED_SKILLS]


def _validate_int(value: object, *, source: Path, index: int, key: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise BaselineError(f"{source}: record {index} has invalid {key}")
    return value


def _validate_files(value: object, *, source: Path, index: int) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise BaselineError(f"{source}: record {index} has invalid files")
    entries = cast("list[object]", value)
    result: list[str] = []
    for item in entries:
        if not isinstance(item, str) or not item or item.startswith("/"):
            raise BaselineError(f"{source}: record {index} has invalid files")
        path = Path(item)
        if any(part in {"", ".", ".."} for part in path.parts):
            raise BaselineError(f"{source}: record {index} has invalid files")
        result.append(path.as_posix())
    if len(set(result)) != len(result):
        raise BaselineError(f"{source}: record {index} has duplicate files")
    return tuple(result)


def _validate_baseline_row(item: object, *, source: Path, index: int) -> BaselineRow:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must be an object")
    row = cast("dict[str, object]", item)
    if set(row.keys()) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    skill = row["skill"]
    if not isinstance(skill, str) or skill not in GATED_SKILLS:
        raise BaselineError(f"{source}: record {index} has invalid skill")
    return BaselineRow(
        skill=skill,
        skill_md_lines=_validate_int(row["skill_md_lines"], source=source, index=index, key="skill_md_lines"),
        skill_md_estimated_tokens=_validate_int(
            row["skill_md_estimated_tokens"],
            source=source,
            index=index,
            key="skill_md_estimated_tokens",
        ),
        skill_md_content_estimated_tokens=_validate_int(
            row["skill_md_content_estimated_tokens"],
            source=source,
            index=index,
            key="skill_md_content_estimated_tokens",
        ),
        closure_lines=_validate_int(row["closure_lines"], source=source, index=index, key="closure_lines"),
        closure_estimated_tokens=_validate_int(
            row["closure_estimated_tokens"],
            source=source,
            index=index,
            key="closure_estimated_tokens",
        ),
        closure_content_estimated_tokens=_validate_int(
            row["closure_content_estimated_tokens"],
            source=source,
            index=index,
            key="closure_content_estimated_tokens",
        ),
        files=_validate_files(row["files"], source=source, index=index),
    )


def load_baseline(path: Path) -> list[BaselineRow]:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BaselineError(f"baseline not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise BaselineError(f"cannot read baseline {path}: {exc}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"cannot read baseline {path}: {exc}") from exc
    if not isinstance(raw, list):
        raise BaselineError(f"{path}: baseline must be a top-level array")
    entries = cast("list[object]", raw)
    rows = [_validate_baseline_row(item, source=path, index=index) for index, item in enumerate(entries, start=1)]
    skills = [row.skill for row in rows]
    if sorted(skills) != sorted(GATED_SKILLS) or len(set(skills)) != len(skills):
        raise BaselineError(f"{path}: baseline must contain one row per gated skill")
    return rows


def _canonical_json(results: Iterable[SkillClosureResult]) -> str:
    rows = [result.to_baseline_row() for result in sorted(results, key=lambda item: item.skill)]
    return json.dumps(rows, indent=2, sort_keys=True) + "\n"


def write_baseline(path: Path, results: Iterable[SkillClosureResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(_canonical_json(results), encoding="utf-8")


def _growth_violations(live: list[SkillClosureResult], baseline: list[BaselineRow]) -> list[str]:
    baseline_by_skill = {row.skill: row for row in baseline}
    violations: list[str] = []
    for result in live:
        row = baseline_by_skill[result.skill]
        for metric in METRIC_FIELDS:
            live_value = getattr(result, metric)
            baseline_value = getattr(row, metric)
            if live_value > baseline_value:
                violations.append(f"{result.skill}: {metric} {live_value} > baseline {baseline_value}")
    return violations


def _parse_args(argv: list[str], *, prog: str, allow_write: bool) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    if allow_write:
        _ = parser.add_argument("--write", action="store_true", help="regenerate the committed baseline")
        _ = parser.add_argument("--skill", choices=GATED_SKILLS, help="check one gated skill")
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _coerce_root(root_text: str, *, prog: str) -> Path | None:
    root = Path(root_text).resolve()
    if not root.is_dir():
        print(f"{prog}: --root is not a directory: {root}", file=sys.stderr)
        return None
    return root


def _print_report(results: list[SkillClosureResult]) -> None:
    print("Eager closure (ratcheted)")
    print("skill      skill_lines  skill_tokens  skill_content_tokens  closure_lines  closure_tokens  closure_content_tokens")
    for result in results:
        print(
            f"{result.skill:<10}"
            f"{result.skill_md_lines:>11}"
            f"{result.skill_md_estimated_tokens:>14}"
            f"{result.skill_md_content_estimated_tokens:>22}"
            f"{result.closure_lines:>15}"
            f"{result.closure_estimated_tokens:>16}"
            f"{result.closure_content_estimated_tokens:>24}"
        )
        for rel in result.files:
            print(f"  - {rel}")
    print()
    print("Conditional closure (reported only)")
    print("skill      conditional_lines  conditional_tokens  conditional_content_tokens")
    for result in results:
        print(
            f"{result.skill:<10}"
            f"{result.conditional_lines:>19}"
            f"{result.conditional_estimated_tokens:>20}"
            f"{result.conditional_content_estimated_tokens:>28}"
        )
        for rel in result.conditional_files:
            print(f"  - {rel}")


def report_main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(
        argv if argv is not None else sys.argv[1:],
        prog="cli.py skill-closure report",
        allow_write=False,
    )
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = _coerce_root(parsed.root, prog="skill-closure report")
    if root is None:
        return TOOL_FAILURE_EXIT
    try:
        results = scan_all(root)
    except ScanError as exc:
        print(f"skill-closure report: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _print_report(results)
    return 0


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(
        argv if argv is not None else sys.argv[1:],
        prog="cli.py lint skill-closure-growth",
        allow_write=True,
    )
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = _coerce_root(parsed.root, prog="lint skill-closure-growth")
    if root is None:
        return TOOL_FAILURE_EXIT
    try:
        if parsed.write and parsed.skill:
            raise BaselineError("--skill is check-only; --write regenerates all gated skills")
        if parsed.write:
            results = scan_all(root)
            write_baseline(root / BASELINE_RELPATH, results)
            return 0
        results = [scan_skill(root, parsed.skill)] if parsed.skill else scan_all(root)
        baseline = load_baseline(root / BASELINE_RELPATH)
    except (BaselineError, ScanError) as exc:
        print(f"lint skill-closure-growth: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT

    violations = _growth_violations(results, baseline)
    if not violations:
        return 0
    for violation in violations:
        print(f"lint skill-closure-growth: {violation}", file=sys.stderr)
    print(
        "Regenerate python/skill-closure-baseline.json with "
        "`python3 python/cli.py lint skill-closure-growth --write` when growth is intentional.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
