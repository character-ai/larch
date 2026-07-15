"""Ratchet lint and type suppressions toward same-line reasons.

Scans production modules under ``python/**/*.py`` for suppression-family
comments that do not use a reason-bearing form. Existing unexplained
suppressions are grandfathered in ``python/suppression-reason-baseline.json``
with a required reason per row.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import TypedDict, cast

from larch.lint.engine import first_duplicate as _first_duplicate
from larch.lint.engine import normalize_python_file_path

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "suppression-reason-baseline.json"
BASELINE_KEYS = frozenset({"file", "suppression_kind", "text", "occurrence", "reason"})
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
SUPPORTED_KINDS = frozenset(
    {
        KIND_NOQA,
        KIND_RUFF_NOQA,
        KIND_PYLINT_DISABLE,
        KIND_PYLINT_DISABLE_NEXT,
        KIND_PYLINT_SKIP_FILE,
        KIND_TYPE_IGNORE,
        KIND_PYRIGHT_IGNORE,
        KIND_PYRIGHT_REPORT,
    }
)

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


class Record(TypedDict):
    file: str
    suppression_kind: str
    text: str
    occurrence: int
    reason: str


class BaselineError(ValueError):
    """Raised when the source tree or baseline cannot be trusted."""


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


def _bad_path_parts(parts: list[str]) -> bool:
    return "" in parts or "." in parts or ".." in parts


def _is_exempt_name(name: str) -> bool:
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def _is_excluded_relative_path(relative: Path) -> bool:
    return bool(EXCLUDED_DIRS.intersection(relative.parts)) or _is_exempt_name(relative.name)


def _invalid_normalized_parts(normalized: str, parts: list[str]) -> bool:
    return (
        normalized.startswith("/")
        or not normalized.endswith(".py")
        or _bad_path_parts(parts)
        or bool(EXCLUDED_DIRS.intersection(parts))
        or _is_exempt_name(parts[-1])
    )


def _validate_normalized_file(value: object, *, source: Path, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: record {index} has invalid file")
    normalized: str = normalize_python_file_path(value)
    parts: list[str] = normalized.split("/")
    if normalized != value or _invalid_normalized_parts(normalized, parts):
        raise BaselineError(f"{source}: record {index} has invalid file")
    return normalized


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


def scan_file(path: Path, *, python_dir: Path) -> list[Finding]:
    """Return suppression comments missing accepted same-line reasons."""
    normalized_file: str = path.relative_to(python_dir).as_posix()
    source: str = _read_source(path, python_dir=python_dir)
    drafts: list[FindingDraft] = _drafts_for_source(source, normalized_file=normalized_file)
    return _with_occurrences(drafts, normalized_file=normalized_file)


def _record_key(record: Record) -> tuple[str, str, str, int]:
    return (record["file"], record["suppression_kind"], record["text"], record["occurrence"])


def _finding_sort_key(finding: Finding) -> tuple[str, str, str, int]:
    return finding.key()


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name: str = _validate_normalized_file(record["file"], source=source, index=index)
    suppression_kind: object = record["suppression_kind"]
    text: object = record["text"]
    occurrence: object = record["occurrence"]
    reason: object = record["reason"]
    if not isinstance(suppression_kind, str) or suppression_kind not in SUPPORTED_KINDS:
        raise BaselineError(f"{source}: record {index} has invalid suppression_kind")
    if not isinstance(text, str) or not text.strip():
        raise BaselineError(f"{source}: record {index} has invalid text")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "suppression_kind": suppression_kind,
        "text": text,
        "occurrence": occurrence,
        "reason": reason,
    }


def load_baseline(path: Path) -> list[Record]:
    """Load and validate the committed baseline."""
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a top-level JSON array")
    records: list[Record] = [
        _validate_record(item, index=index, source=path)
        for index, item in enumerate(cast("list[object]", data))
    ]
    duplicate: tuple[str, str, str, int] | None = _first_duplicate(_record_key(record) for record in records)
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate baseline identity {format_key(duplicate)}")
    return records


def _collect_all(python_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_source_files(python_dir):
        findings.extend(scan_file(path, python_dir=python_dir))
    return findings


def _check_duplicate_live(findings: list[Finding]) -> str | None:
    duplicate: tuple[str, str, str, int] | None = _first_duplicate(finding.key() for finding in findings)
    if duplicate is None:
        return None
    return f"duplicate live identity {format_key(duplicate)}"


def format_key(key: tuple[str, str, str, int]) -> str:
    file_name, suppression_kind, text, occurrence = key
    return f"{file_name}:{suppression_kind} {text}#{occurrence}"


def serialize_baseline(records: list[Record]) -> str:
    """Return canonical sorted JSON for the baseline."""
    ordered: list[Record] = sorted(records, key=_record_key)
    return json.dumps(ordered, indent=2) + "\n"


def _records_for_write(
    findings: list[Finding],
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> list[Record]:
    preserved: dict[tuple[str, str, str, int], str] = {}
    has_baseline = baseline_path.is_file()
    if has_baseline:
        preserved = {_record_key(record): record["reason"] for record in load_baseline(baseline_path)}
    reason_default: str | None = initial_reason.strip() if initial_reason is not None and not has_baseline else None
    records: list[Record] = []
    missing: list[str] = []
    for finding in sorted(findings, key=_finding_sort_key):
        reason: str | None = preserved.get(finding.key()) or reason_default
        if reason is None:
            missing.append(format_key(finding.key()))
            continue
        records.append(
            {
                "file": finding.file,
                "suppression_kind": finding.suppression_kind,
                "text": finding.text,
                "occurrence": finding.occurrence,
                "reason": reason,
            }
        )
    if missing:
        joined: str = "\n  ".join(missing)
        raise BaselineError("missing baseline reasons for live suppression findings:\n  " + joined)
    return records


def _run_write(
    python_dir: Path,
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> int:
    try:
        findings: list[Finding] = _collect_all(python_dir)
        duplicate: str | None = _check_duplicate_live(findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
        records: list[Record] = _records_for_write(
            findings,
            baseline_path=baseline_path,
            initial_reason=initial_reason,
        )
    except BaselineError as exc:
        print(f"lint-suppression-reason: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    except OSError as exc:
        print(f"lint-suppression-reason: {baseline_path}: cannot write baseline: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    print(f"lint-suppression-reason: wrote {len(records)} records to {baseline_path}", file=sys.stderr)
    return 0


def _run_check(python_dir: Path, *, baseline_path: Path) -> int:
    try:
        baseline_records: list[Record] = load_baseline(baseline_path)
        findings: list[Finding] = _collect_all(python_dir)
        duplicate: str | None = _check_duplicate_live(findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
    except BaselineError as exc:
        print(f"lint-suppression-reason: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys: frozenset[tuple[str, str, str, int]] = frozenset(
        _record_key(record) for record in baseline_records
    )
    live_keys: frozenset[tuple[str, str, str, int]] = frozenset(finding.key() for finding in findings)
    new_findings: list[Finding] = []
    warned: list[Finding] = []
    for finding in sorted(findings, key=_finding_sort_key):
        if finding.key() in baseline_keys:
            warned.append(finding)
        else:
            new_findings.append(finding)
    stale_keys: list[tuple[str, str, str, int]] = sorted(baseline_keys - live_keys)
    for finding in warned:
        print(
            "warning: "
            f"{finding.file}:{finding.lineno} {finding.suppression_kind} "
            f"suppression lacks an accepted reason (baselined): {finding.text}",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.file}:{finding.lineno} {finding.suppression_kind} "
            f"suppression lacks an accepted same-line reason: {finding.text}",
            file=sys.stderr,
        )
    for key in stale_keys:
        print(f"stale baseline row: {format_key(key)}", file=sys.stderr)
    return 1 if new_findings or stale_keys else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint suppression-reason", description=__doc__)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=f"Regenerate {BASELINE_FILENAME} from live suppression scan.",
    )
    _ = parser.add_argument(
        "--initial-reason",
        help="Reason used for live findings without preserved baseline reasons.",
    )
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    parsed: argparse.Namespace | None = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root: Path = Path(str(parsed.root)).resolve()
    python_dir: Path = root / "python"
    if not python_dir.is_dir():
        print(f"lint-suppression-reason: python directory not found: {python_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_path: Path = python_dir / BASELINE_FILENAME
    initial_reason: str | None = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-suppression-reason: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(python_dir, baseline_path=baseline_path, initial_reason=initial_reason)
    return _run_check(python_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
