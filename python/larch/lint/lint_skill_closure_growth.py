"""Report and ratchet always-loaded prompt-source closure size."""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from larch.lint import engine

TOOL_FAILURE_EXIT = 2
BASELINE_RELPATH = Path("python/skill-closure-baseline.json")
GATED_SKILLS = engine.SKILL_CLOSURE_RATCHETED_TARGETS[:3]
PANEL_TIER_TARGET = "panel-tier"
RATCHETED_TARGETS = engine.SKILL_CLOSURE_RATCHETED_TARGETS
FILE_RATCHET_TARGETS = engine.SKILL_CLOSURE_FILE_RATCHET_TARGETS
METRIC_FIELDS = engine.SKILL_CLOSURE_METRIC_FIELDS
CONDITIONAL_METRIC_FIELDS = engine.SKILL_CLOSURE_CONDITIONAL_METRIC_FIELDS
BASELINE_KEYS = engine.SKILL_CLOSURE_BASELINE_KEYS
PLUGIN_ROOT_PREFIX = "${CLAUDE_PLUGIN_ROOT}/"
CONDITIONAL_SECTIONS_BY_SKILL: dict[str, frozenset[str]] = {
    "design": frozenset(
        {
            "Plan command validator failure (shared)",
            "Split-path (decomposition panel)",
        }
    ),
    "implement": frozenset({"Checks Failure Entry Macro", "Durable Bail to Step 18 Macro"}),
}

MANDATORY_DIRECTIVE_RE = re.compile(r"MANDATORY:\s+READ\s+ENTIRE\s+FILE", re.IGNORECASE)
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
REGISTRY_PATH_RE = re.compile(
    r"`(?P<ticked>[^`\n]+?skills/[A-Za-z0-9_-]+/scripts/step-name-registry\.tsv)`|"
    r"(?P<bare>(?:\$\{CLAUDE_PLUGIN_ROOT\}/|\./|/)?[A-Za-z0-9_./{}$+-]*skills/[A-Za-z0-9_-]+/scripts/step-name-registry\.tsv)"
)
SESSION_START_REGISTRY_RE = re.compile(r"\bRead\b.*?step-name-registry\.tsv", re.IGNORECASE)
SESSION_SETUP_OUTPUT_RE = re.compile(r"\buse\b.*?session-setup-output\.md.*?\bfor\b", re.IGNORECASE)
EXTERNAL_REVIEWERS_PROCEDURE_RE = re.compile(r"\bprocedure\s+in\b.*?external-reviewers\.md", re.IGNORECASE)
IMPLEMENT_FINAL_SUMMARY_RE = re.compile(r"\bfollow\b.*?final-summary-emit\.md", re.IGNORECASE)
CONDITIONAL_REFERENCE_RE = re.compile(
    r"\b(?:see|load|read|follow)\b"
    r"(?P<body>(?:(?![.,]\s).)*?\.md(?:(?![.,]\s).)*?\bonly\s+(?:for|when|after|before|on|upon)\b)",
    re.IGNORECASE,
)


class ScanError(ValueError):
    """Raised when closure scanning cannot produce a trusted result."""


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


    def to_engine_row(self) -> engine.SkillClosureBaselineRow:
        """Project scan results onto the engine-owned aggregate schema."""
        return engine.SkillClosureBaselineRow(
            self.skill,
            self.skill_md_lines,
            self.skill_md_estimated_tokens,
            self.skill_md_content_estimated_tokens,
            self.closure_lines,
            self.closure_estimated_tokens,
            self.closure_content_estimated_tokens,
            self.files,
            self.conditional_lines,
            self.conditional_estimated_tokens,
            self.conditional_content_estimated_tokens,
            self.conditional_files,
        )


BaselineRow: TypeAlias = engine.SkillClosureBaselineRow


@dataclass(frozen=True)
class DirectiveMatch:
    index: int
    clause: str
    supported: bool
    force_conditional: bool = False


@dataclass(frozen=True)
class DirectiveContext:
    line: str
    line_number: int
    match: DirectiveMatch
    conditional_section: bool


@dataclass(frozen=True)
class ScanState:
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
    return raw.strip().strip("`").rstrip(".,);]")


def _is_runtime_markdown_operand(raw: str) -> bool:
    cleaned = _clean_raw_path(raw)
    return RUNTIME_MARKDOWN_OPERAND_RE.match(cleaned) is not None


def _resolve_repo_path(root: Path, source_path: Path, raw_path: str) -> str:
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
        raise ScanError(f"referenced prompt source not found: {rel}")
    return rel


def _extract_repo_paths(root: Path, source_path: Path, clause: str, *, strict: bool) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    matches = sorted(
        [*MARKDOWN_PATH_RE.finditer(clause), *REGISTRY_PATH_RE.finditer(clause)],
        key=lambda item: item.start(),
    )
    for match in matches:
        raw_path = match.group("ticked") or match.group("bare")
        if raw_path is None:
            continue
        if _is_runtime_markdown_operand(raw_path):
            continue
        try:
            rel = _resolve_repo_path(root, source_path, raw_path)
        except ScanError:
            if strict:
                raise
            continue
        if rel not in seen:
            seen.add(rel)
            paths.append(rel)
    return paths


def _has_supported_prompt_operand(clause: str) -> bool:
    return MARKDOWN_PATH_RE.search(clause) is not None or REGISTRY_PATH_RE.search(clause) is not None


def _read_completely_crosses_mandatory(line: str, read_match: re.Match[str]) -> bool:
    for mandatory in MANDATORY_DIRECTIVE_RE.finditer(line):
        if read_match.start() < mandatory.start() < read_match.end():
            return True
    return False


def _mandatory_clause(remainder: str) -> str:
    read_match = READ_COMPLETELY_RE.search(remainder)
    if read_match is not None:
        return remainder[read_match.start() : read_match.end()]
    path_match = _first_supported_path_match(remainder)
    if path_match is None:
        return remainder
    sentence_end_match = re.search(r"\.(?:\s|$)", remainder[path_match.end() :])
    if sentence_end_match is None:
        return remainder
    sentence_end = path_match.end() + sentence_end_match.start()
    return remainder[: sentence_end + 1]


def _first_supported_path_match(text: str) -> re.Match[str] | None:
    return min(
        [*MARKDOWN_PATH_RE.finditer(text), *REGISTRY_PATH_RE.finditer(text)],
        key=lambda item: item.start(),
        default=None,
    )


def _sentence_clause(line: str, match: re.Match[str]) -> str:
    previous_sentence = line.rfind(". ", 0, match.start())
    sentence_start = 0 if previous_sentence == -1 else previous_sentence + 2
    sentence_end_match = re.search(r"\.(?:\s|$)", line[match.end() :])
    if sentence_end_match is None:
        return line[sentence_start:]
    sentence_end = match.end() + sentence_end_match.start()
    return line[sentence_start : sentence_end + 1]


def _conditional_reference_matches(line: str) -> list[DirectiveMatch]:
    return [
        DirectiveMatch(
            index=match.start(),
            clause=match.group(0),
            supported=True,
            force_conditional=True,
        )
        for match in CONDITIONAL_REFERENCE_RE.finditer(line)
    ]


def _narrow_directive_matches(line: str, skill: str) -> list[DirectiveMatch]:
    patterns: list[re.Pattern[str]]
    if skill in {"design", "review"}:
        patterns = [
            SESSION_START_REGISTRY_RE,
            SESSION_SETUP_OUTPUT_RE,
            EXTERNAL_REVIEWERS_PROCEDURE_RE,
        ]
    elif skill == "implement":
        patterns = [SESSION_START_REGISTRY_RE, IMPLEMENT_FINAL_SUMMARY_RE]
    else:
        patterns = []
    return [
        DirectiveMatch(index=match.start(), clause=_sentence_clause(line, match), supported=True)
        for pattern in patterns
        for match in pattern.finditer(line)
    ]


def _directive_matches(line: str, skill: str) -> list[DirectiveMatch]:
    matches = [
        DirectiveMatch(
            index=match.start(),
            clause=_mandatory_clause(line[match.end() :]),
            supported=True,
        )
        for match in MANDATORY_DIRECTIVE_RE.finditer(line)
    ]
    matches.extend(_narrow_directive_matches(line, skill))
    matches.extend(_conditional_reference_matches(line))
    for match in READ_COMPLETELY_RE.finditer(line):
        if any(existing.index <= match.start() for existing in matches):
            continue
        if _read_completely_crosses_mandatory(line, match):
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


def _prefix_is_conditional(prefix: str) -> bool:
    if CONDITIONAL_TEXT_RE.search(prefix) is None:
        return False
    current_sentence = prefix.rsplit(". ", 1)[-1]
    body = _body_after_bullet(current_sentence.strip())
    if CONDITIONAL_PREFIX_RE.match(body.lstrip("* ")):
        return True
    if "fail" in current_sentence.lower() and CONDITIONAL_TEXT_RE.search(
        prefix.removesuffix(current_sentence)
    ) is not None:
        return True
    if ":" not in current_sentence:
        return False
    return CONDITIONAL_TEXT_RE.search(current_sentence) is not None


def _line_is_conditional(line: str, directive_index: int) -> bool:
    if "force_requested=false" in line and "preflight-plan-audit.md" in line:
        return False
    stripped = line.strip()
    first_cell = _first_table_cell(stripped)
    if first_cell is not None and _table_cell_is_route_predicate(first_cell):
        return True

    body = _body_after_bullet(stripped)
    if CONDITIONAL_PREFIX_RE.match(body):
        return True
    prefix = line[:directive_index]
    if BRANCH_BULLET_RE.match(body) or (body.startswith(("`", "**`")) and ":" in prefix):
        return True

    if _prefix_is_conditional(prefix):
        return True

    suffix = line[directive_index:]
    return CONDITIONAL_SUFFIX_RE.search(suffix) is not None


def _update_conditional_section_state(skill: str, line: str, state: ScanState) -> ScanState:
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
    if next_state.conditional_section_depth is None and title in CONDITIONAL_SECTIONS_BY_SKILL.get(skill, frozenset()):
        return ScanState(conditional_section_depth=heading_depth)
    return next_state


def _update_scan_state(skill: str, line: str, state: ScanState) -> ScanState:
    return _update_conditional_section_state(skill, line, state)


def _session_start_registry_path(root: Path, skill: str) -> str | None:
    registry_rel = f"skills/{skill}/scripts/step-name-registry.tsv"
    if (root / registry_rel).is_file():
        return registry_rel
    return None


def _paths_for_directive_match(
    root: Path,
    skill_path: Path,
    context: DirectiveContext,
) -> tuple[bool, list[str]]:
    is_conditional = (
        context.conditional_section
        or context.match.force_conditional
        or _line_is_conditional(context.line, context.match.index)
    )
    paths = _extract_repo_paths(root, skill_path, context.match.clause, strict=not is_conditional)
    if not paths and SESSION_START_REGISTRY_RE.search(context.match.clause):
        registry_rel = _session_start_registry_path(root, skill_path.parent.name)
        if registry_rel is not None:
            paths = [registry_rel]
    if is_conditional:
        return True, paths
    if paths:
        return False, paths
    if _has_supported_prompt_operand(context.match.clause):
        raise ScanError(
            f"{_repo_relative(root, skill_path)}:{context.line_number}: "
            "supported read directive has no resolvable prompt source"
        )
    if NON_MD_PATH_RE.search(context.match.clause):
        return False, paths
    raise ScanError(
        f"{_repo_relative(root, skill_path)}:{context.line_number}: "
        "supported read directive has no resolvable prompt source"
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
        for match in _directive_matches(line, skill):
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


def scan_panel_tier(root: Path) -> SkillClosureResult:
    agents_dir = root / "agents"
    agent_paths = sorted(agents_dir.glob("*.md"))
    if not agent_paths:
        raise ScanError("panel-tier source scan found no agents/*.md files")
    fixed_files = (
        root / "skills/shared/reviewer-templates.md",
        root / "skills/shared/voting-protocol.md",
    )
    for path in fixed_files:
        if not path.is_file():
            raise ScanError(f"panel-tier source missing: {_repo_relative(root, path)}")
    files: list[str] = []
    seen: set[str] = set()
    for path in (*agent_paths, *fixed_files):
        rel = _repo_relative(root, path)
        if rel not in seen:
            seen.add(rel)
            files.append(rel)
    metrics = {rel: _read_file_metrics(root / rel) for rel in files}
    return SkillClosureResult(
        skill=PANEL_TIER_TARGET,
        skill_md_lines=0,
        skill_md_estimated_tokens=0,
        skill_md_content_estimated_tokens=0,
        closure_lines=sum(item.lines for item in metrics.values()),
        closure_estimated_tokens=sum(item.estimated_tokens for item in metrics.values()),
        closure_content_estimated_tokens=sum(item.content_estimated_tokens for item in metrics.values()),
        files=tuple(files),
        conditional_lines=0,
        conditional_estimated_tokens=0,
        conditional_content_estimated_tokens=0,
        conditional_files=(),
    )


def scan_target(root: Path, target: str) -> SkillClosureResult:
    if target == PANEL_TIER_TARGET:
        return scan_panel_tier(root)
    return scan_skill(root, target)


def scan_all(root: Path) -> list[SkillClosureResult]:
    return [scan_target(root, target) for target in RATCHETED_TARGETS]


def write_baseline(path: Path, results: Iterable[SkillClosureResult]) -> None:
    root = path.parent.parent if path.parent.name == "python" else path.parent
    _ = engine.write_skill_closure_baseline(
        path,
        root=root,
        rows=[result.to_engine_row() for result in results],
    )


def _coerce_root(root_text: str | Path, *, prog: str) -> Path | None:
    root = Path(root_text).resolve()
    if not root.is_dir():
        print(f"{prog}: --root is not a directory: {root}", file=sys.stderr)
        return None
    return root


def _print_report(results: list[SkillClosureResult]) -> None:
    print("Eager closure (ratcheted)")
    print("target      skill_lines  skill_tokens  skill_content_tokens  closure_lines  closure_tokens  closure_content_tokens")
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
    print("Conditional closure (review ratcheted; design and implement reported only)")
    print("target      conditional_lines  conditional_tokens  conditional_content_tokens")
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
    parsed = engine.parse_skill_closure_report_argv(
        argv if argv is not None else sys.argv[1:], default_root=Path.cwd()
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
    parsed = engine.parse_skill_closure_growth_argv(
        argv if argv is not None else sys.argv[1:], default_root=Path.cwd()
    )
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = _coerce_root(parsed.root, prog="lint skill-closure-growth")
    if root is None:
        return TOOL_FAILURE_EXIT
    try:
        if parsed.write:
            results = scan_all(root)
            write_baseline(root / BASELINE_RELPATH, results)
            return 0
        results = [scan_target(root, parsed.skill)] if parsed.skill else scan_all(root)
        baseline = engine.load_skill_closure_baseline(BASELINE_RELPATH, root=root)
    except (engine.ScanError, ScanError) as exc:
        print(f"lint skill-closure-growth: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT

    violations = engine.skill_closure_growth_violations(
        [result.to_engine_row() for result in results], baseline
    )
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
