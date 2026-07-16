"""Ratchet lint and type suppressions toward same-line reasons.

Thin engine-backed rule: detection tokenizes production modules under
``python/**/*.py`` for suppression-family comments that do not use a
reason-bearing form. Existing unexplained suppressions are grandfathered in
``python/suppression-reason-baseline.json`` with a required reason per row.
The occurrence identity omits ``qualified_symbol`` (suppression scans are not
scoped to an AST symbol), so the rule opts into symbol-optional occurrence
rows and treats stale rows as findings (exit 1) rather than engine errors.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import cast

from larch.core import proc
from larch.lint.engine import (
    EXIT_ERROR,
    Finding as EngineFinding,
    LintRule,
    SourceFile,
    run_rule,
)

RULE_ID = "suppression-reason"
SUPPRESSION_TOKEN = "lint-suppression-reason"
BASELINE_FILENAME = "suppression-reason-baseline.json"
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "env",
        "node_modules",
        "tests",
        "venv",
        "vendor",
        "vendored",
    }
)

KIND_NOQA = "noqa"
KIND_RUFF_NOQA = "ruff-noqa"
KIND_PYLINT_DISABLE = "pylint-disable"
KIND_PYLINT_DISABLE_NEXT = "pylint-disable-next"
KIND_PYLINT_SKIP_FILE = "pylint-skip-file"
KIND_TYPE_IGNORE = "type-ignore"
KIND_PYRIGHT_IGNORE = "pyright-ignore"
KIND_PYRIGHT_REPORT = "pyright-report"

SUPPRESSION_PREFIX = r"(?:^|;\s*)"
NOQA_FAMILY_RE = re.compile(SUPPRESSION_PREFIX + r"(?P<label>ruff:\s*noqa|noqa)\b", re.IGNORECASE)
NOQA_STRICT_RE = re.compile(
    SUPPRESSION_PREFIX
    + r"(?P<label>ruff:\s*noqa|noqa)\s*:\s*(?P<codes>[^#;\s][^#;]*?)\s+-\s*(?P<reason>\S.*)$",
    re.IGNORECASE,
)
SUPPRESSION_START_RE = re.compile(
    r"(?:(?:ruff:\s*)?noqa\b(?:\s*:\s*[^#;]+(?:\s+-\s*\S.*)?)?|"
    r"pylint:\s*(?:disable-next|disable|skip-file)\b(?:\s*=\s*[A-Za-z0-9_,\-\s]+)?(?:\s*#\s*\S.*)?|"
    r"type:\s*ignore\[[^\]\s][^\]]*\](?:\s*#\s*\S.*)?|"
    r"pyright:\s*ignore\[[^\]\s][^\]]*\](?:\s*#\s*\S.*)?|"
    r"pyright:\s*report[A-Za-z0-9_]+\s*=\s*false(?:\s*,\s*report[A-Za-z0-9_]+\s*=\s*false)*(?:\s*#\s*\S.*)?)$",
    re.IGNORECASE,
)
PYLINT_FAMILY_RE = re.compile(
    SUPPRESSION_PREFIX + r"pylint:\s*(?P<action>disable-next|disable|skip-file)\b",
    re.IGNORECASE,
)
PYLINT_STRICT_RE = re.compile(
    SUPPRESSION_PREFIX
    + r"pylint:\s*(?P<action>disable-next|disable|skip-file)\b(?P<tail>[^;#]*?)"
    + r"(?:\s*#\s*(?P<reason>.*))?$",
    re.IGNORECASE,
)
TYPE_IGNORE_FAMILY_RE = re.compile(SUPPRESSION_PREFIX + r"type:\s*ignore\b", re.IGNORECASE)
TYPE_IGNORE_STRICT_RE = re.compile(
    SUPPRESSION_PREFIX + r"type:\s*ignore\[(?P<codes>[^\]\s][^\]]*)\]\s*(?:#\s*(?P<reason>.*))?$",
    re.IGNORECASE,
)
PYRIGHT_IGNORE_FAMILY_RE = re.compile(SUPPRESSION_PREFIX + r"pyright:\s*ignore\b", re.IGNORECASE)
PYRIGHT_IGNORE_STRICT_RE = re.compile(
    SUPPRESSION_PREFIX + r"pyright:\s*ignore\[(?P<rules>[^\]\s][^\]]*)\]\s*(?:#\s*(?P<reason>.*))?$",
    re.IGNORECASE,
)
PYRIGHT_REPORT_FAMILY_RE = re.compile(
    SUPPRESSION_PREFIX + r"pyright:\s*report[A-Za-z0-9_]+\s*=\s*false\b",
    re.IGNORECASE,
)
PYRIGHT_REPORT_STRICT_RE = re.compile(
    SUPPRESSION_PREFIX
    + r"pyright:\s*report[A-Za-z0-9_]+\s*=\s*false(?:\s*,\s*report[A-Za-z0-9_]+\s*=\s*false)*\s*(?:#\s*(?P<reason>.*))?$",
    re.IGNORECASE,
)
REASON_SUPPRESSION_PREFIX_RE = re.compile(
    r"^(?:(?:ruff:\s*)?noqa\b(?:\s*:\s*[^#;]*?(?:\s+-\s*.*)?)?|"
    r"pylint:\s*(?:disable-next|disable|skip-file)\b(?:\s*=\s*[A-Za-z0-9_,\-\s]+)?|"
    r"type:\s*ignore(?:\[[^\]]+\])?|"
    r"pyright:\s*(?:ignore(?:\[[^\]]+\])?|report[A-Za-z0-9_]+\s*=\s*false))",
    re.IGNORECASE,
)


class BaselineError(ValueError):
    """Raised when the source tree cannot be trusted."""


@dataclass(frozen=True)
class FindingDraft:
    suppression_kind: str
    text: str
    lineno: int


@dataclass(frozen=True)
class Finding:
    file: str
    suppression_kind: str
    text: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, int]:
        return (self.file, self.suppression_kind, self.text, self.occurrence)


@dataclass(frozen=True)
class SegmentMatch:
    suppression_kind: str
    strict: bool
    matched_text: str
    reason: str | None = None


def _is_exempt_name(name: str) -> bool:
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def _is_excluded_relative_path(relative: Path) -> bool:
    return bool(EXCLUDED_DIRS.intersection(relative.parts)) or _is_exempt_name(relative.name)


def iter_source_files(python_dir: Path) -> list[Path]:
    """Return production Python files under python/, sorted."""
    result: list[Path] = []
    for path in sorted(python_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink():
            continue
        relative: Path = path.relative_to(python_dir)
        if _is_excluded_relative_path(relative):
            continue
        result.append(path)
    return result


def _read_source(path: Path, *, python_dir: Path) -> str:
    normalized: str = path.relative_to(python_dir).as_posix()
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BaselineError(f"{normalized}: cannot read source: {exc}") from exc


def _normalize_text(text: str) -> str:
    stripped: str = text.strip().lstrip(";").strip()
    return re.sub(r"\s+", " ", stripped)


def _comment_segments(comment: str) -> list[str]:
    body: str = comment.lstrip("#").lstrip()
    segments: list[str] = []
    start = 0
    index = 0
    while index < len(body):
        char = body[index]
        if char == ";":
            segment = body[start:index].strip()
            if segment:
                segments.append(segment)
            start = index + 1
            index += 1
            continue
        if char == "#":
            reason_tail: str = body[index + 1 :].lstrip()
            if SUPPRESSION_START_RE.match(reason_tail) is not None:
                segment = body[start:index].strip()
                if segment:
                    segments.append(segment)
                start = index + 1
                index += 1
                continue
        index += 1
    segment = body[start:].strip()
    if segment:
        segments.append(segment)
    return segments


def _pyright_report_segments(segment: str) -> list[str]:
    return [segment]


def _has_reason_text(text: str | None) -> bool:
    if text is None:
        return False
    stripped: str = text.strip()
    if not stripped:
        return False
    suppression_prefix: re.Match[str] | None = REASON_SUPPRESSION_PREFIX_RE.match(stripped)
    if suppression_prefix is None:
        return True
    remainder: str = stripped[suppression_prefix.end() :].strip(" ;,.-")
    return bool(remainder)


def _kind_for_noqa(label: str) -> str:
    return KIND_RUFF_NOQA if label.lower().startswith("ruff") else KIND_NOQA


def _pylint_kind(action: str) -> str:
    lowered: str = action.lower()
    if lowered == "disable-next":
        return KIND_PYLINT_DISABLE_NEXT
    if lowered == "skip-file":
        return KIND_PYLINT_SKIP_FILE
    return KIND_PYLINT_DISABLE


def _match_noqa(segment: str) -> SegmentMatch | None:
    family_match: re.Match[str] | None = NOQA_FAMILY_RE.search(segment)
    if family_match is None:
        return None
    strict_match: re.Match[str] | None = NOQA_STRICT_RE.search(segment)
    suppression_kind: str = _kind_for_noqa(family_match.group("label"))
    if strict_match is None:
        return SegmentMatch(
            suppression_kind=suppression_kind,
            strict=False,
            matched_text=_normalize_text(segment[family_match.start() :]),
        )
    reason: str = strict_match.group("reason")
    return SegmentMatch(
        suppression_kind=_kind_for_noqa(strict_match.group("label")),
        strict=_has_reason_text(reason),
        matched_text=_normalize_text(segment[strict_match.start() :]),
        reason=reason,
    )


def _pylint_tail_has_checks(action: str, tail: str) -> bool:
    if action.lower() == "skip-file":
        return tail.strip() == ""
    tail_match: re.Match[str] | None = re.fullmatch(r"\s*=\s*[^\s,][A-Za-z0-9_,\-\s]*", tail)
    return tail_match is not None


def _match_pylint(segment: str) -> SegmentMatch | None:
    family_match: re.Match[str] | None = PYLINT_FAMILY_RE.search(segment)
    if family_match is None:
        return None
    strict_match: re.Match[str] | None = PYLINT_STRICT_RE.search(segment)
    action: str = family_match.group("action")
    suppression_kind: str = _pylint_kind(action)
    if strict_match is None or not _pylint_tail_has_checks(strict_match.group("action"), strict_match.group("tail")):
        return SegmentMatch(
            suppression_kind=suppression_kind,
            strict=False,
            matched_text=_normalize_text(segment[family_match.start() :]),
        )
    return SegmentMatch(
        suppression_kind=suppression_kind,
        strict=_has_reason_text(cast("str | None", strict_match.groupdict().get("reason"))),
        matched_text=_normalize_text(segment[strict_match.start() :]),
        reason=cast("str | None", strict_match.groupdict().get("reason")),
    )


def _match_following_reason_suppression(
    segment: str,
    *,
    family_re: Pattern[str],
    strict_re: Pattern[str],
    suppression_kind: str,
) -> SegmentMatch | None:
    family_match: re.Match[str] | None = family_re.search(segment)
    if family_match is None:
        return None
    strict_match: re.Match[str] | None = strict_re.search(segment)
    if strict_match is None:
        return SegmentMatch(
            suppression_kind=suppression_kind,
            strict=False,
            matched_text=_normalize_text(segment[family_match.start() :]),
        )
    reason: str | None = cast("str | None", strict_match.groupdict().get("reason"))
    return SegmentMatch(
        suppression_kind=suppression_kind,
        strict=_has_reason_text(reason),
        matched_text=_normalize_text(segment[strict_match.start() :]),
        reason=reason,
    )


def _match_segment(segment: str) -> SegmentMatch | None:
    for match in (
        _match_noqa(segment),
        _match_pylint(segment),
        _match_following_reason_suppression(
            segment,
            family_re=TYPE_IGNORE_FAMILY_RE,
            strict_re=TYPE_IGNORE_STRICT_RE,
            suppression_kind=KIND_TYPE_IGNORE,
        ),
        _match_following_reason_suppression(
            segment,
            family_re=PYRIGHT_IGNORE_FAMILY_RE,
            strict_re=PYRIGHT_IGNORE_STRICT_RE,
            suppression_kind=KIND_PYRIGHT_IGNORE,
        ),
        _match_following_reason_suppression(
            segment,
            family_re=PYRIGHT_REPORT_FAMILY_RE,
            strict_re=PYRIGHT_REPORT_STRICT_RE,
            suppression_kind=KIND_PYRIGHT_REPORT,
        ),
    ):
        if match is not None:
            return match
    return None


def _scan_comment(comment: str, *, lineno: int) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    for segment in _comment_segments(comment):
        for candidate in _pyright_report_segments(segment):
            match: SegmentMatch | None = _match_segment(candidate)
            if match is None or match.strict:
                continue
            findings.append(
                FindingDraft(
                    suppression_kind=match.suppression_kind,
                    text=match.matched_text,
                    lineno=lineno,
                )
            )
    return findings


def _drafts_for_source(source: str, *, normalized_file: str) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type == tokenize.COMMENT:
                findings.extend(_scan_comment(token.string, lineno=token.start[0]))
    except tokenize.TokenError as exc:
        raise BaselineError(f"{normalized_file}: cannot tokenize source: {exc}") from exc
    return findings


def _with_occurrences(drafts: list[FindingDraft], *, normalized_file: str) -> list[Finding]:
    counts: dict[tuple[str, str], int] = {}
    findings: list[Finding] = []
    for draft in drafts:
        key = (draft.suppression_kind, draft.text)
        occurrence: int = counts.get(key, 0) + 1
        counts[key] = occurrence
        findings.append(
            Finding(
                file=normalized_file,
                suppression_kind=draft.suppression_kind,
                text=draft.text,
                occurrence=occurrence,
                lineno=draft.lineno,
            )
        )
    return findings


def findings_from_source(source: str, *, normalized_file: str) -> list[Finding]:
    """Tokenize one source buffer and return suppression findings with occurrences."""
    drafts: list[FindingDraft] = _drafts_for_source(source, normalized_file=normalized_file)
    return _with_occurrences(drafts, normalized_file=normalized_file)


def scan_file(path: Path, *, python_dir: Path) -> list[Finding]:
    """Return suppression comments missing accepted same-line reasons."""
    normalized_file: str = path.relative_to(python_dir).as_posix()
    source: str = _read_source(path, python_dir=python_dir)
    return findings_from_source(source, normalized_file=normalized_file)


def is_production_source_path(rel_path: str) -> bool:
    """Pre-load filter for repo-relative suppression scan paths."""
    if not rel_path.startswith("python/") or not rel_path.endswith(".py"):
        return False
    relative: Path = Path(rel_path[len("python/") :])
    return not _is_excluded_relative_path(relative)


def to_engine_finding(finding: Finding) -> EngineFinding:
    """Adapt one suppression finding to the shared engine finding shape."""
    return EngineFinding(
        path=f"python/{finding.file}",
        line=finding.lineno,
        rule_id=RULE_ID,
        message=(
            f"{finding.suppression_kind} suppression lacks an accepted "
            f"same-line reason: {finding.text}"
        ),
        qualified_symbol=None,
        occurrence=finding.occurrence,
        occurrence_values=(
            ("suppression_kind", finding.suppression_kind),
            ("text", finding.text),
        ),
    )


def detect(source: SourceFile) -> list[EngineFinding]:
    """Engine detector entry: tokenize one source and emit symbol-free findings."""
    if not source.is_python or not is_production_source_path(source.path):
        return []
    normalized_file = source.path.removeprefix("python/")
    findings = findings_from_source(source.text, normalized_file=normalized_file)
    return [to_engine_finding(finding) for finding in findings]


RULE = LintRule(
    rule_id=RULE_ID,
    description=(
        "Ratchet lint and type suppressions toward same-line reasons"
    ),
    detect=detect,
    syntax_policy="raise",
    suppression_token=SUPPRESSION_TOKEN,
    allow_inline_suppression=False,
    pathspecs=("python",),
    source_filter=is_production_source_path,
    occurrence_baseline=True,
    occurrence_fields=("suppression_kind", "text"),
    occurrence_symbol_optional=True,
    require_baseline=True,
    stale_as_finding=True,
    warn_matching_baseline=True,
)


def _parse_args(argv: list[str]) -> tuple[str, bool, str | None] | None:
    parser = argparse.ArgumentParser(prog="cli.py lint suppression-reason", description=__doc__)
    _ = parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root (default: checkout containing this module).",
    )
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=f"Regenerate {BASELINE_FILENAME} from the live suppression scan.",
    )
    _ = parser.add_argument(
        "--initial-reason",
        help="Reason used for live findings without preserved baseline reasons.",
    )
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None
    return str(parsed.root), bool(parsed.write), parsed.initial_reason


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint suppression-reason``."""
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return EXIT_ERROR
    root_str, write_baseline, initial_reason = parsed
    root = Path(root_str).resolve()
    if initial_reason is not None and not initial_reason.strip():
        print("lint-suppression-reason: --initial-reason must be non-empty", file=sys.stderr)
        return EXIT_ERROR
    baseline_path = root / "python" / BASELINE_FILENAME
    # Legacy policy: --initial-reason only seeds new rows when the baseline is
    # absent. Once a baseline exists, every new row needs its own preserved
    # reason and the engine fail-closes without a seed.
    if write_baseline and baseline_path.is_file():
        seed_reason: str | None = None
    else:
        seed_reason = None if initial_reason is None else initial_reason.strip()
    return run_rule(
        RULE,
        root,
        proc.ProcRunner(),
        baseline_path=baseline_path,
        write_baseline=write_baseline,
        initial_reason=seed_reason,
        strict_stale=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
