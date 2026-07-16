"""Ratchet report renderers toward explicit test references.

Scans top-level functions in ``python/larch/report/*.py`` whose names look like
renderers or row builders. A function is covered when a report test mentions the
function name as a whole identifier. Current deliberate gaps are grandfathered
in ``python/renderer-golden-tests-baseline.json`` with a required reason per
row.
"""

from __future__ import annotations

import ast
import re
from re import Pattern
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from larch.lint.engine import (
    IdentityLintCli,
    RendererGoldenTestsBaselineRow,
    ScanError,
    comment_tokens_by_line,
    compare_identity_baseline,
    first_duplicate as _first_duplicate,
    load_identity_baseline,
    parse_identity_lint_argv,
    write_identity_baseline,
)

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "renderer-golden-tests-baseline.json"
PRAGMA_RE = re.compile(r"#\s*lint-renderer-golden-tests:\s*ok\s+(\S.*)$")


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
    except (OSError, UnicodeDecodeError) as exc:
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


def format_key(key: tuple[str, str]) -> str:
    file_name, function_name = key
    return f"{file_name}:{function_name}"


def _collect_all(
    report_dir: Path, *, python_dir: Path
) -> tuple[list[Candidate], dict[str, dict[int, tuple[str, ...]]]]:
    candidates: list[Candidate] = []
    comments_by_file: dict[str, dict[int, tuple[str, ...]]] = {}
    for path in iter_report_files(report_dir):
        normalized_file: str = path.relative_to(python_dir).as_posix()
        source: str = _read_source(path, python_dir=python_dir)
        comments_by_file[normalized_file] = comment_tokens_by_line(source)
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


def _run_write(  # noqa: PLR0913 - scanner inputs mirror the established command contract.
    root: Path,
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
        baseline_rows = load_identity_baseline(
            baseline_path, root=root, kind="renderer_golden_tests", allow_missing=True
        )
        records = [
            RendererGoldenTestsBaselineRow(finding.file, finding.function_name, "")
            for finding in findings
        ]
        written = write_identity_baseline(
            baseline_path, root=root, kind="renderer_golden_tests", live_rows=records,
            baseline_rows=baseline_rows, initial_reason=initial_reason,
        )
    except (BaselineError, ScanError) as exc:
        print(f"lint-renderer-golden-tests: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    print(
        f"lint-renderer-golden-tests: wrote {len(written)} records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check(
    root: Path, report_dir: Path, *, report_test_dir: Path, python_dir: Path, baseline_path: Path
) -> int:
    try:
        baseline_records = load_identity_baseline(
            baseline_path, root=root, kind="renderer_golden_tests"
        )
        findings: list[Finding] = _live_findings(
            report_dir, report_test_dir=report_test_dir, python_dir=python_dir
        )
    except (BaselineError, ScanError) as exc:
        print(f"lint-renderer-golden-tests: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    live_rows = [RendererGoldenTestsBaselineRow(f.file, f.function_name, "") for f in findings]
    new_rows, stale_rows, warned_rows = compare_identity_baseline(live_rows, baseline_records)
    new_keys = {row.identity for row in new_rows if isinstance(row, RendererGoldenTestsBaselineRow)}
    warned_keys = {row.identity for row in warned_rows if isinstance(row, RendererGoldenTestsBaselineRow)}
    for finding in findings:
        if finding.key() not in warned_keys:
            continue
        print(
            "warning: "
            f"{finding.file}:{finding.function_name} line {finding.lineno} "
            "has no whole-identifier reference in python/tests/report/*.py (baselined)",
            file=sys.stderr,
        )
    for finding in findings:
        if finding.key() not in new_keys:
            continue
        print(
            f"{finding.file}:{finding.function_name} line {finding.lineno} "
            "has no whole-identifier reference in python/tests/report/*.py",
            file=sys.stderr,
        )
    for row in stale_rows:
        if isinstance(row, RendererGoldenTestsBaselineRow):
            print(f"stale baseline row: {format_key(row.identity)}", file=sys.stderr)
    return 1 if new_rows or stale_rows else 0


CLI = IdentityLintCli(
    prog="cli.py lint renderer-golden-tests", description=__doc__ or "",
    baseline_filename=BASELINE_FILENAME, writable=True,
)


def main(argv: list[str] | None = None) -> int:
    parsed = parse_identity_lint_argv(
        argv if argv is not None else sys.argv[1:], cli=CLI,
        default_root=Path(__file__).resolve().parents[3],
    )
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = parsed.root
    python_dir: Path = root / "python"
    report_dir: Path = python_dir / "larch" / "report"
    if not report_dir.is_dir():
        print(f"lint-renderer-golden-tests: report directory not found: {report_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    report_test_dir: Path = python_dir / "tests" / "report"
    baseline_path: Path = python_dir / BASELINE_FILENAME
    if parsed.write_baseline:
        return _run_write(
            root, report_dir,
            report_test_dir=report_test_dir,
            python_dir=python_dir,
            baseline_path=baseline_path,
            initial_reason=parsed.initial_reason,
        )
    return _run_check(
        root, report_dir, report_test_dir=report_test_dir, python_dir=python_dir, baseline_path=baseline_path
    )


if __name__ == "__main__":
    raise SystemExit(main())
