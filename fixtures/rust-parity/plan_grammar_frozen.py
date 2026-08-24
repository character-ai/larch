"""Frozen Python plan grammar retained only for pre-cutover parity fixtures.

The live owner is ``larch_core::design::plan_grammar``. This snapshot preserves
historical Python behavior for Rust parity harnesses; production Python must not
import it.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

HeadingKind = Literal["NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE"]
TrailerKey = Literal[
    "review_status",
    "rounds_completed",
    "difficulty",
    "diff_added",
    "diff_deleted",
    "mechanical_churn",
    "oversize_override",
    "diff_lines",
]

HEADING_KINDS: Final[tuple[HeadingKind, ...]] = ("NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE")
FIRM_HEADING_KINDS: Final[frozenset[HeadingKind]] = frozenset({"NEW", "UPDATED", "REWRITTEN"})
TRAILER_KEYS: Final[tuple[TrailerKey, ...]] = (
    "review_status",
    "rounds_completed",
    "difficulty",
    "diff_added",
    "diff_deleted",
    "mechanical_churn",
    "oversize_override",
    "diff_lines",
)
OPTIONAL_SIZE_TRAILER_KEYS: Final[tuple[TrailerKey, ...]] = (
    "diff_added",
    "diff_deleted",
    "mechanical_churn",
    "oversize_override",
)
CANONICAL_TRAILER_ORDER: Final[tuple[TrailerKey, ...]] = TRAILER_KEYS


def implementation_plan_body(lines: Sequence[str]) -> str:
    """Extract a nonempty Implementation Plan body from a full plan document."""
    in_section = False
    saw_section = False
    body_lines: list[str] = []
    test_plan_index = 0
    for line in lines:
        if line == "## Implementation Plan":
            if not saw_section:
                in_section = True
            saw_section = True
            continue
        if in_section:
            body_lines.append(line)
            if line == "## Test plan":
                test_plan_index = len(body_lines)
    if not saw_section:
        raise ValueError("missing ## Implementation Plan")
    limit = test_plan_index - 1 if test_plan_index > 0 else len(body_lines)
    if not any(line.strip() for line in body_lines[:limit]):
        raise ValueError("Implementation Plan body is empty")
    return "\n".join(body_lines[:limit]).rstrip() + "\n"

HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<level>##|###)[ \t]+(?P<kind>NEW|UPDATED|REWRITTEN|MAY_UPDATE)(?:[ \t]*:[ \t]*(?P<colon>.+?)|[ \t]+\[(?P<bracket>[^]\r\n]+)\][ \t]*:?)[ \t]*$"
)
TRAILER_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<key>review_status|rounds_completed|difficulty|diff_added|diff_deleted|mechanical_churn|oversize_override|diff_lines): (?P<value>[^\r\n]+)$"
)
_GENERIC_LEVEL_TWO_RE: Final[re.Pattern[str]] = re.compile(r"^##(?:[ \t]+|$)(?!#)")
_FENCE_MARKER_RE: Final[re.Pattern[str]] = re.compile(r"^(`{3,}|~{3,})(.*)$")
_SIZE_INTEGER_RE: Final[re.Pattern[str]] = re.compile(r"(?:0[0-7]*|[1-9][0-9]*)")
_DIGITS_RE: Final[re.Pattern[str]] = re.compile(r"[0-9]+")


def balanced_fence_line_indices(lines: list[str]) -> set[int]:
    """Return 0-based indices of lines strictly inside balanced code fences.

    An unmatched opener does not fence later lines, so headings after a truncated
    fence remain visible. A closer must use the same marker character, be at least
    as long as the opener, and carry only a whitespace suffix.
    """
    fenced_lines: set[int] = set()
    stack: list[tuple[int, str, int]] = []
    for index, line in enumerate(lines):
        match = _FENCE_MARKER_RE.match(line.strip())
        if match is None:
            continue
        marker = match.group(1)
        marker_char = marker[0]
        marker_len = len(marker)
        suffix = match.group(2)
        if not stack:
            stack.append((index, marker_char, marker_len))
            continue
        top_index, top_char, top_len = stack[-1]
        if marker_char == top_char and marker_len >= top_len and suffix.strip() == "":
            _ = stack.pop()
            fenced_lines.update(range(top_index + 1, index))
    return fenced_lines


def is_fence_marker(line: str) -> bool:
    """Return whether a line is a Markdown fence marker."""
    return _FENCE_MARKER_RE.match(line.strip()) is not None


@dataclass(frozen=True)
class HeadingMatch:
    kind: HeadingKind
    path: str
    level: int
    line_number: int = 0

    @property
    def firm(self) -> bool:
        return self.kind in FIRM_HEADING_KINDS


@dataclass(frozen=True)
class HeadingEvent:
    line_number: int
    text: str
    heading: HeadingMatch | None
    generic_level_two: bool


@dataclass(frozen=True)
class TrailerMatch:
    key: TrailerKey
    value: str
    parsed_value: str | int | bool


@dataclass(frozen=True)
class PlanTrailers:
    lines: tuple[str, ...]
    matches: tuple[TrailerMatch, ...]
    start_line: int
    duplicates: tuple[TrailerKey, ...]

    def get(self, key: TrailerKey) -> TrailerMatch | None:
        return next((match for match in reversed(self.matches) if match.key == key), None)

    @property
    def diff_lines(self) -> int | None:
        match = self.get("diff_lines")
        return match.parsed_value if match is not None and isinstance(match.parsed_value, int) else None


def match_heading(line: str, *, line_number: int = 0) -> HeadingMatch | None:
    """Match one accepted whole-line plan heading."""
    match = HEADING_RE.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    path = (match.group("colon") or match.group("bracket") or "").strip()
    if not path:
        return None
    return HeadingMatch(
        kind=match.group("kind"),  # type: ignore[arg-type]  # regex restricts the literal set
        path=path,
        level=len(match.group("level")),
        line_number=line_number,
    )


def iter_heading_events(text: str) -> Iterator[HeadingEvent]:
    """Yield non-fenced heading events, with recognized headings taking precedence."""
    lines = text.splitlines()
    fenced_lines = balanced_fence_line_indices(lines)
    for line_number, line in enumerate(lines, start=1):
        index = line_number - 1
        if index in fenced_lines or is_fence_marker(line):
            continue
        heading = match_heading(line, line_number=line_number)
        yield HeadingEvent(
            line_number=line_number,
            text=line,
            heading=heading,
            generic_level_two=heading is None and _GENERIC_LEVEL_TWO_RE.match(line) is not None,
        )


def iter_plan_headings(text: str, *, kinds: frozenset[HeadingKind] | None = None) -> Iterator[HeadingMatch]:
    for event in iter_heading_events(text):
        if event.heading is not None and (kinds is None or event.heading.kind in kinds):
            yield event.heading


def iter_firm_headings(text: str) -> Iterator[HeadingMatch]:
    return iter_plan_headings(text, kinds=FIRM_HEADING_KINDS)


def _parse_trailer_value(key: TrailerKey, value: str) -> str | int | bool | None:
    parsed: str | int | bool | None = value
    if key in {"rounds_completed", "diff_lines"}:
        parsed = int(value, 10) if _DIGITS_RE.fullmatch(value) is not None else None
    elif key in {"diff_added", "diff_deleted"}:
        parsed = None if _SIZE_INTEGER_RE.fullmatch(value) is None else (
            int(value, 8) if len(value) > 1 and value.startswith("0") else int(value, 10)
        )
    elif key == "difficulty" and value not in {"TRIVIAL", "MODERATE", "HARD"}:
        parsed = None
    elif key == "mechanical_churn":
        parsed = {"true": True, "false": False}.get(value)
    elif (key == "oversize_override" and value != "operator") or (key == "review_status" and not value.strip()):
        parsed = None
    return parsed


def match_trailer_line(line: str) -> TrailerMatch | None:
    """Return a typed whole-line trailer match, or ``None`` for malformed input."""
    match = TRAILER_LINE_RE.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    key: TrailerKey = match.group("key")  # type: ignore[assignment]  # regex restricts the literal set
    value = match.group("value")
    parsed = _parse_trailer_value(key, value)
    return None if parsed is None else TrailerMatch(key=key, value=value, parsed_value=parsed)


def iter_trailer_lines(text: str, *, keys: Iterable[TrailerKey] | None = None) -> Iterator[TrailerMatch]:
    """Scan the whole document for valid trailer lines.

    This is the compatibility API for consumers whose historical behavior is a
    whole-document scan. Terminal consumers should use :func:`parse_final_trailers`.
    """
    allowed = frozenset(keys) if keys is not None else None
    for line in text.splitlines():
        match = match_trailer_line(line)
        if match is not None and (allowed is None or match.key in allowed):
            yield match


def parse_final_trailers(text: str, *, require_diff_lines: bool = False) -> PlanTrailers:
    """Parse the final contiguous valid trailer block.

    Blank lines and registry-excluded lines such as ``confidence:`` end the
    block. Duplicate keys are retained and reported for consumer policy.
    """
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        _ = lines.pop()
    matches: list[TrailerMatch] = []
    raw_lines: list[str] = []
    for line in reversed(lines):
        match = match_trailer_line(line)
        if match is None:
            break
        matches.append(match)
        raw_lines.append(line)
    matches.reverse()
    raw_lines.reverse()
    seen: set[TrailerKey] = set()
    duplicates: list[TrailerKey] = []
    for match in matches:
        if match.key in seen and match.key not in duplicates:
            duplicates.append(match.key)
        seen.add(match.key)
    result = PlanTrailers(
        lines=tuple(raw_lines),
        matches=tuple(matches),
        start_line=len(lines) - len(matches) + 1 if matches else len(lines) + 1,
        duplicates=tuple(duplicates),
    )
    if require_diff_lines and (not matches or matches[-1].key != "diff_lines"):
        return PlanTrailers(lines=(), matches=(), start_line=len(lines) + 1, duplicates=())
    return result


def terminal_diff_lines(text: str) -> int | None:
    trailers = parse_final_trailers(text, require_diff_lines=True)
    return trailers.diff_lines


def compose_trailer_lines(values: Mapping[TrailerKey, str | int | bool | None]) -> tuple[str, ...]:
    """Compose validated trailers in canonical order."""
    rendered: list[str] = []
    for key in CANONICAL_TRAILER_ORDER:
        value = values.get(key)
        if value is None:
            continue
        token = str(value).lower() if isinstance(value, bool) else str(value)
        match = match_trailer_line(f"{key}: {token}")
        if match is None:
            raise ValueError(f"invalid {key} trailer value")
        rendered.append(f"{key}: {match.value}")
    return tuple(rendered)


def grammar_prompt() -> str:
    """Return compact drafting guidance from the shared registries."""
    kinds = ", ".join(f"`### {kind}:`" for kind in HEADING_KINDS)
    optional = ", ".join(f"`{key}: <value>`" for key in OPTIONAL_SIZE_TRAILER_KEYS)
    return (
        f"Use per-file headings {kinds}. Include non-empty "
        "`## Closed decisions and ownership`, `## Acceptance`, and "
        "`## Breaking changes and migration` sections. Include "
        "`## Ordered implementation` with at least one numbered step. End with "
        f"`difficulty: <TRIVIAL|MODERATE|HARD>`, optional {optional}, and "
        "terminal `diff_lines: <N>`."
    )


# --- Executable plan contract (M1 shape + M2 repository scope) ---

M1_DEFECT_TOKENS: Final[tuple[str, ...]] = (
    "missing-plan-block",
    "multiple-plan-blocks",
    "missing-firm-scope",
    "missing-ordered-implementation",
    "missing-acceptance",
    "missing-closed-decisions",
    "missing-breaking-migration",
    "missing-diff-lines",
)
M2_DEFECT_TOKENS: Final[tuple[str, ...]] = (
    "empty-plan-glob",
    "missing-updated-plan-path",
    "existing-new-plan-path",
    "unsafe-plan-path",
)
PLAN_DEFECT_ORDER: Final[tuple[str, ...]] = (*M1_DEFECT_TOKENS, *M2_DEFECT_TOKENS)
FORCE_PLAN_CONTRACT_ERROR: Final[str] = (
    "ERROR: --force can skip semantic plan review, but it cannot run without "
    "a valid issue-body larch:plan block"
)

_SECTION_HEADING_RE: Final[re.Pattern[str]] = re.compile(r"^(#{2,3})[ \t]+(.+?)[ \t]*$")
_NUMBERED_STEP_RE: Final[re.Pattern[str]] = re.compile(r"^[ \t]*\d+\.[ \t]+\S")
_CLOSED_DECISIONS_RE: Final[re.Pattern[str]] = re.compile(
    r"^closed[ \t]+decisions(?:[ \t]+and[ \t]+ownership)?$",
    re.IGNORECASE,
)
_ORDERED_IMPLEMENTATION_RE: Final[re.Pattern[str]] = re.compile(
    r"^ordered[ \t]+implementation$",
    re.IGNORECASE,
)
_ACCEPTANCE_RE: Final[re.Pattern[str]] = re.compile(r"^acceptance$", re.IGNORECASE)
_BREAKING_MIGRATION_RE: Final[re.Pattern[str]] = re.compile(
    r"^breaking[ \t]+changes[ \t]+and[ \t]+migration$",
    re.IGNORECASE,
)
_GLOB_META_RE: Final[re.Pattern[str]] = re.compile(r"[*?[]")


@dataclass(frozen=True)
class PlanValidationResult:
    """Frozen executable-plan validation outcome with ordered defect tokens."""

    defects: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.defects


def _ordered_defects(found: Iterable[str]) -> tuple[str, ...]:
    present = frozenset(found)
    return tuple(token for token in PLAN_DEFECT_ORDER if token in present)


def _section_title(line: str) -> tuple[int, str] | None:
    match = _SECTION_HEADING_RE.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    return len(match.group(1)), match.group(2).strip()


def _iter_section_bodies(text: str) -> Iterator[tuple[str, tuple[str, ...]]]:
    """Yield (title, body_lines) for non-fenced ##/### headings."""
    lines = text.splitlines()
    fenced = balanced_fence_line_indices(lines)
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        if index in fenced or is_fence_marker(line):
            continue
        parsed = _section_title(line)
        if parsed is None:
            continue
        level, title = parsed
        headings.append((index, level, title))
    for position, (index, level, title) in enumerate(headings):
        end = len(lines)
        for later_index, later_level, _later_title in headings[position + 1 :]:
            if later_level <= level:
                end = later_index
                break
        body = tuple(lines[index + 1 : end])
        yield title, body


def _body_nonempty(body: Sequence[str]) -> bool:
    return any(line.strip() for line in body)


def _heading_path_token(raw: str) -> str:
    stripped = raw.strip()
    backtick_matches = list(re.finditer(r"`([^`]+)`", stripped))
    if backtick_matches:
        return backtick_matches[0].group(1).strip()
    parts = stripped.split()
    if not parts:
        return ""
    return re.sub(r"\(.*$", "", parts[0]).strip()


def _section_has_numbered_step(body: Sequence[str]) -> bool:
    return any(_NUMBERED_STEP_RE.match(line) for line in body)


def _m1_section_flags(plan_text: str) -> tuple[bool, bool, bool, bool]:
    closed_ok = False
    ordered_ok = False
    acceptance_ok = False
    breaking_ok = False
    for title, body in _iter_section_bodies(plan_text):
        if _CLOSED_DECISIONS_RE.fullmatch(title) is not None and _body_nonempty(body):
            closed_ok = True
        if _ORDERED_IMPLEMENTATION_RE.fullmatch(title) is not None and _section_has_numbered_step(body):
            ordered_ok = True
        if _ACCEPTANCE_RE.fullmatch(title) is not None and _body_nonempty(body):
            acceptance_ok = True
        if _BREAKING_MIGRATION_RE.fullmatch(title) is not None and _body_nonempty(body):
            breaking_ok = True
    return closed_ok, ordered_ok, acceptance_ok, breaking_ok


def _m1_facet_defects(plan_text: str) -> set[str]:
    defects: set[str] = set()
    if not list(iter_firm_headings(plan_text)):
        defects.add("missing-firm-scope")

    closed_ok, ordered_ok, acceptance_ok, breaking_ok = _m1_section_flags(plan_text)
    if not closed_ok:
        defects.add("missing-closed-decisions")
    if not ordered_ok:
        defects.add("missing-ordered-implementation")
    if not acceptance_ok:
        defects.add("missing-acceptance")
    if not breaking_ok:
        defects.add("missing-breaking-migration")

    trailers = parse_final_trailers(plan_text, require_diff_lines=True)
    if trailers.diff_lines is None:
        defects.add("missing-diff-lines")
    return defects


def validate_plan_facets(*, plan_text: str) -> PlanValidationResult:
    """Validate executable-plan M1 shape facets without repository path checks."""
    return PlanValidationResult(defects=_ordered_defects(_m1_facet_defects(plan_text)))


def _is_glob_path(path: str) -> bool:
    return _GLOB_META_RE.search(path) is not None


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


def _load_tracked_paths(repo_root: Path) -> frozenset[str]:
    from larch.core import proc  # noqa: PLC0415 - avoid module-level git/proc coupling in the grammar owner
    from larch.errors import ShipError  # noqa: PLC0415 - avoid module-level git/proc coupling in the grammar owner

    try:
        result = proc.run(["git", "ls-files"], cwd=str(repo_root))
        if result.returncode != 0:
            return frozenset()
        return frozenset(line for line in result.stdout.splitlines() if line)
    except (OSError, ShipError):
        return frozenset()


def _repo_resolved(repo_root: Path) -> Path:
    return repo_root.resolve()


def _path_inside_repo(*, repo_root: Path, path: Path) -> bool:
    root = _repo_resolved(repo_root)
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return resolved == root or root in resolved.parents


def _existing_parents_safe(*, repo_root: Path, rel_path: str) -> bool:
    """Reject symlink parents that escape the repository without following them as scope."""
    if not repo_root.is_dir():
        return False
    current = repo_root
    for part in Path(rel_path).parts[:-1]:
        current = current / part
        # Symlink parents are never acceptable for NEW confinement.
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            return False
        if not current.exists():
            return True
        if not _path_inside_repo(repo_root=repo_root, path=current):
            return False
    return True


def _glob_matches_tracked(*, pattern: str, tracked: frozenset[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for path in tracked)


def _m2_path_defects(
    *, plan_text: str, repo_root: Path, tracked_paths: frozenset[str] | None = None
) -> set[str]:
    defects: set[str] = set()
    tracked = tracked_paths if tracked_paths is not None else _load_tracked_paths(repo_root)
    for heading in iter_plan_headings(plan_text):
        path = _heading_path_token(heading.path)
        if not path or _path_has_unsafe_shape(path):
            defects.add("unsafe-plan-path")
            continue
        leaf = repo_root / path
        if leaf.is_symlink() and not _path_inside_repo(repo_root=repo_root, path=leaf):
            defects.add("unsafe-plan-path")
            continue
        if not _existing_parents_safe(repo_root=repo_root, rel_path=path):
            defects.add("unsafe-plan-path")
            continue

        if heading.kind == "NEW":
            if path in tracked or leaf.exists():
                defects.add("existing-new-plan-path")
            continue

        if _is_glob_path(path):
            if not _glob_matches_tracked(pattern=path, tracked=tracked):
                defects.add("empty-plan-glob")
            continue
        if path not in tracked:
            defects.add("missing-updated-plan-path")
    return defects


def validate_plan_contract(
    *, plan_text: str, repo_root: Path, tracked_paths: frozenset[str] | None = None
) -> PlanValidationResult:
    """Validate executable-plan facets and repository-scope paths (no marker check)."""
    found: set[str] = set()
    found.update(validate_plan_facets(plan_text=plan_text).defects)
    found.update(
        _m2_path_defects(
            plan_text=plan_text, repo_root=repo_root, tracked_paths=tracked_paths
        )
    )
    return PlanValidationResult(defects=_ordered_defects(found))
