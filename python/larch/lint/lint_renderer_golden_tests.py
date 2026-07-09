"""Ratchet report renderers toward explicit test references.

Scans top-level functions in ``python/larch/report/*.py`` whose names look like
renderers or row builders. A function is covered when a report test mentions the
function name as a whole identifier. Current deliberate gaps are grandfathered
in ``python/renderer-golden-tests-baseline.json`` with a required reason per
row.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
from re import Pattern
import sys
import tokenize
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "renderer-golden-tests-baseline.json"
BASELINE_KEYS = frozenset({"file", "function_name", "reason"})
PRAGMA_RE = re.compile(r"#\s*lint-renderer-golden-tests:\s*ok\s+(\S.*)$")


class Record(TypedDict):
    file: str
    function_name: str
    reason: str


class BaselineError(ValueError):
    """Raised when the baseline or source tree cannot be trusted."""


@dataclass(frozen=True)
class Candidate:
    file: str
    function_name: str
    lineno: int

    def key(self) -> tuple[str, str]:
        return (self.file, self.function_name)


Finding = Candidate


def normalize_file_path(raw: str) -> str:
    """Return a normalized POSIX path relative to python/."""
    normalized: str = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized == "python":
        return ""
    return normalized.removeprefix("python/")


def _has_bad_path_parts(parts: list[str]) -> bool:
    return "" in parts or "." in parts or ".." in parts


def _validate_normalized_file(value: object, *, source: Path, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: record {index} has invalid file")
    normalized: str = normalize_file_path(value)
    parts: list[str] = normalized.split("/")
    if (
        normalized != value
        or normalized.startswith("/")
        or not normalized.startswith("larch/report/")
        or not normalized.endswith(".py")
        or _has_bad_path_parts(parts)
    ):
        raise BaselineError(f"{source}: record {index} has invalid file")
    return normalized


def _candidate_name(name: str) -> bool:
    return name.startswith("_render_") or name.endswith("_rows")


def iter_report_files(report_dir: Path) -> list[Path]:
    """Return top-level report Python files in deterministic order."""
    return [path for path in sorted(report_dir.glob("*.py")) if path.is_file() and not path.is_symlink()]


def iter_report_test_files(tests_dir: Path) -> list[Path]:
    """Return top-level report test Python files in deterministic order."""
    if not tests_dir.is_dir():
        return []
    return [path for path in sorted(tests_dir.glob("*.py")) if path.is_file() and not path.is_symlink()]


def _read_source(path: Path, *, python_dir: Path) -> str:
    normalized: str = path.relative_to(python_dir).as_posix()
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BaselineError(f"{normalized}: cannot read source: {exc}") from exc


def _parse_source(source: str, *, normalized_file: str) -> ast.Module:
    try:
        return ast.parse(source)
    except SyntaxError as exc:
        raise BaselineError(f"{normalized_file}: cannot parse source: {exc}") from exc


def scan_file(path: Path, *, python_dir: Path) -> list[Candidate]:
    """Return top-level renderer-like functions from one report file."""
    normalized_file: str = path.relative_to(python_dir).as_posix()
    source: str = _read_source(path, python_dir=python_dir)
    tree: ast.Module = _parse_source(source, normalized_file=normalized_file)
    candidates: list[Candidate] = []
    for statement in tree.body:
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _candidate_name(statement.name):
            continue
        candidates.append(
            Candidate(file=normalized_file, function_name=statement.name, lineno=statement.lineno)
        )
    return candidates


def _comment_tokens_by_line(source: str) -> dict[int, tuple[str, ...]]:
    comments: dict[int, list[str]] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.setdefault(token.start[0], []).append(token.string)
    except tokenize.TokenError:
        return {}
    return {line: tuple(values) for line, values in comments.items()}


def _is_suppressed(candidate: Candidate, *, comments_by_line: Mapping[int, tuple[str, ...]]) -> bool:
    return any(PRAGMA_RE.search(comment) for comment in comments_by_line.get(candidate.lineno, ()))


def _identifier_pattern(name: str) -> Pattern[str]:
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")


def _covered_names(test_files: Iterable[Path], *, python_dir: Path, names: set[str]) -> set[str]:
    patterns: dict[str, Pattern[str]] = {name: _identifier_pattern(name) for name in sorted(names)}
    covered: set[str] = set()
    for path in test_files:
        text: str = _read_source(path, python_dir=python_dir)
        for name, pattern in patterns.items():
            if name not in covered and pattern.search(text) is not None:
                covered.add(name)
    return covered


def _record_key(record: Record) -> tuple[str, str]:
    return (record["file"], record["function_name"])


def _candidate_sort_key(candidate: Candidate) -> tuple[str, str]:
    return candidate.key()


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name: str = _validate_normalized_file(record["file"], source=source, index=index)
    function_name: object = record["function_name"]
    reason: object = record["reason"]
    if not isinstance(function_name, str) or not _candidate_name(function_name):
        raise BaselineError(f"{source}: record {index} has invalid function_name")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {"file": file_name, "function_name": function_name, "reason": reason}


def _first_duplicate(keys: Iterable[tuple[str, str]]) -> tuple[str, str] | None:
    seen: set[tuple[str, str]] = set()
    for key in keys:
        if key in seen:
            return key
        seen.add(key)
    return None


def load_baseline(path: Path) -> list[Record]:
    """Load and validate the committed baseline."""
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a top-level JSON array")
    records: list[Record] = [
        _validate_record(item, index=index, source=path)
        for index, item in enumerate(cast("list[object]", data))
    ]
    duplicate: tuple[str, str] | None = _first_duplicate(_record_key(record) for record in records)
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate baseline identity {format_key(duplicate)}")
    return records


def format_key(key: tuple[str, str]) -> str:
    file_name, function_name = key
    return f"{file_name}:{function_name}"


def serialize_baseline(records: list[Record]) -> str:
    """Return canonical sorted JSON for the baseline."""
    ordered: list[Record] = sorted(records, key=_record_key)
    return json.dumps(ordered, indent=2) + "\n"


def _collect_all(
    report_dir: Path, *, python_dir: Path
) -> tuple[list[Candidate], dict[str, dict[int, tuple[str, ...]]]]:
    candidates: list[Candidate] = []
    comments_by_file: dict[str, dict[int, tuple[str, ...]]] = {}
    for path in iter_report_files(report_dir):
        normalized_file: str = path.relative_to(python_dir).as_posix()
        source: str = _read_source(path, python_dir=python_dir)
        comments_by_file[normalized_file] = _comment_tokens_by_line(source)
        tree: ast.Module = _parse_source(source, normalized_file=normalized_file)
        for statement in tree.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if _candidate_name(statement.name):
                candidates.append(
                    Candidate(
                        file=normalized_file,
                        function_name=statement.name,
                        lineno=statement.lineno,
                    )
                )
    return candidates, comments_by_file


def _check_duplicate_live(candidates: list[Candidate]) -> str | None:
    duplicate: tuple[str, str] | None = _first_duplicate(candidate.key() for candidate in candidates)
    if duplicate is None:
        return None
    return f"duplicate live identity {format_key(duplicate)}"


def _filter_suppressed(
    candidates: list[Candidate], *, comments_by_file: Mapping[str, dict[int, tuple[str, ...]]]
) -> list[Candidate]:
    return [
        candidate
        for candidate in candidates
        if not _is_suppressed(
            candidate,
            comments_by_line=comments_by_file.get(candidate.file, {}),
        )
    ]


def _findings_for_candidates(
    candidates: list[Candidate], *, report_test_dir: Path, python_dir: Path
) -> list[Finding]:
    names: set[str] = {candidate.function_name for candidate in candidates}
    covered_names: set[str] = _covered_names(
        iter_report_test_files(report_test_dir), python_dir=python_dir, names=names
    )
    return [candidate for candidate in candidates if candidate.function_name not in covered_names]


def _live_findings(report_dir: Path, *, report_test_dir: Path, python_dir: Path) -> list[Finding]:
    candidates, comments_by_file = _collect_all(report_dir, python_dir=python_dir)
    duplicate: str | None = _check_duplicate_live(candidates)
    if duplicate is not None:
        raise BaselineError(duplicate)
    unsuppressed: list[Candidate] = _filter_suppressed(candidates, comments_by_file=comments_by_file)
    return _findings_for_candidates(unsuppressed, report_test_dir=report_test_dir, python_dir=python_dir)


def _records_for_write(
    findings: list[Finding], *, baseline_path: Path, initial_reason: str | None
) -> list[Record]:
    preserved: dict[tuple[str, str], str] = {}
    if baseline_path.is_file():
        preserved = {_record_key(record): record["reason"] for record in load_baseline(baseline_path)}
    reason_default: str | None = initial_reason.strip() if initial_reason is not None else None
    records: list[Record] = []
    missing: list[str] = []
    for finding in sorted(findings, key=_candidate_sort_key):
        reason: str | None = preserved.get(finding.key()) or reason_default
        if reason is None:
            missing.append(format_key(finding.key()))
            continue
        records.append(
            {"file": finding.file, "function_name": finding.function_name, "reason": reason}
        )
    if missing:
        joined: str = "\n  ".join(missing)
        raise BaselineError("missing baseline reasons for live renderer golden-test findings:\n  " + joined)
    return records


def _run_write(
    report_dir: Path,
    *,
    report_test_dir: Path,
    python_dir: Path,
    baseline_path: Path,
    initial_reason: str | None,
) -> int:
    try:
        findings: list[Finding] = _live_findings(
            report_dir, report_test_dir=report_test_dir, python_dir=python_dir
        )
        records: list[Record] = _records_for_write(
            findings, baseline_path=baseline_path, initial_reason=initial_reason
        )
    except BaselineError as exc:
        print(f"lint-renderer-golden-tests: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(
        f"lint-renderer-golden-tests: wrote {len(records)} records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check(
    report_dir: Path, *, report_test_dir: Path, python_dir: Path, baseline_path: Path
) -> int:
    try:
        baseline_records: list[Record] = load_baseline(baseline_path)
        findings: list[Finding] = _live_findings(
            report_dir, report_test_dir=report_test_dir, python_dir=python_dir
        )
    except BaselineError as exc:
        print(f"lint-renderer-golden-tests: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys: frozenset[tuple[str, str]] = frozenset(
        _record_key(record) for record in baseline_records
    )
    live_keys: frozenset[tuple[str, str]] = frozenset(finding.key() for finding in findings)
    new_findings: list[Finding] = []
    warned: list[Finding] = []
    for finding in sorted(findings, key=_candidate_sort_key):
        if finding.key() in baseline_keys:
            warned.append(finding)
        else:
            new_findings.append(finding)
    stale_keys: list[tuple[str, str]] = sorted(baseline_keys - live_keys)
    for finding in warned:
        print(
            "warning: "
            f"{finding.file}:{finding.function_name} line {finding.lineno} "
            "has no whole-identifier reference in python/tests/report/*.py (baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.file}:{finding.function_name} line {finding.lineno} "
            "has no whole-identifier reference in python/tests/report/*.py",
            file=sys.stderr,
        )
    for key in stale_keys:
        print(f"stale baseline row: {format_key(key)}", file=sys.stderr)
    return 1 if new_findings or stale_keys else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint renderer-golden-tests", description=__doc__
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=f"Regenerate {BASELINE_FILENAME} from live AST scan.",
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
    report_dir: Path = python_dir / "larch" / "report"
    if not report_dir.is_dir():
        print(f"lint-renderer-golden-tests: report directory not found: {report_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    report_test_dir: Path = python_dir / "tests" / "report"
    baseline_path: Path = python_dir / BASELINE_FILENAME
    initial_reason: str | None = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-renderer-golden-tests: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(
            report_dir,
            report_test_dir=report_test_dir,
            python_dir=python_dir,
            baseline_path=baseline_path,
            initial_reason=initial_reason,
        )
    return _run_check(
        report_dir, report_test_dir=report_test_dir, python_dir=python_dir, baseline_path=baseline_path
    )


if __name__ == "__main__":
    raise SystemExit(main())
