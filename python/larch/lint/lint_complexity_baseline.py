"""Ratchet Ruff complexity findings through the shared lint engine.

Ruff invocation and AST-qualified-symbol resolution remain local because they
describe this lint's source domain.  The engine owns the complexity baseline
schema, trusted I/O, comparisons, migration, and atomic publication.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias, cast

from larch.lint.engine import (
    COMPLEXITY_CODES,
    ComplexityBaselineRow,
    ComplexityHistoryEvent,
    ComplexityLiveRow,
    ScanError,
    complexity_duplicate_identities,
    complexity_history_events,
    complexity_regressions,
    complexity_row_record,
    load_complexity_baseline,
    merge_complexity_baseline,
    migrate_complexity_baseline,
    parse_complexity_baseline,
    parse_complexity_baseline_argv,
    serialize_complexity_baseline,
    write_complexity_baseline,
)

if TYPE_CHECKING:
    from larch.lint.engine import ComplexityCode

TOOL_FAILURE_EXIT = 2
REPEAT_BUMP_DAYS = 14
METRIC_RE = re.compile(r"\((\d+)\s*>\s*\d+\)")
RUFF_ARGS = (
    "ruff", "check", ".", "--no-cache", "--select", ",".join(sorted(COMPLEXITY_CODES)),
    "--output-format", "json", "--config", "ruff-complexity-audit.toml",
)
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
SymbolSpan: TypeAlias = tuple[int, int, str]
Record: TypeAlias = dict[str, object]
BaselineError = ScanError
HistoryEvent = ComplexityHistoryEvent


@dataclass(frozen=True)
class RuffResult:
    """Captured Ruff process result, retained as the external-tool seam."""

    returncode: int
    stdout: str
    stderr: str


def normalize_file_path(raw: str) -> str:
    """Return a normalized repo-relative path under the Python directory."""
    normalized = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.removeprefix("python/")


def is_exempt_path(path: str) -> bool:
    """Return whether a normalized path is pytest-facing and out of scope."""
    name = Path(path).name
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def parse_metric(*, code: str, message: str) -> int | None:
    """Extract the observed complexity count from a Ruff message."""
    _ = code
    match = METRIC_RE.search(message)
    return int(match.group(1)) if match is not None else None


def _collect_symbol_spans(source: str) -> list[SymbolSpan] | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    spans: list[SymbolSpan] = []

    def visit(*, node: ast.AST, prefix: tuple[str, ...]) -> None:
        if isinstance(node, ast.ClassDef):
            for child in ast.iter_child_nodes(node):
                visit(node=child, prefix=(*prefix, node.name))
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_lineno = getattr(node, "end_lineno", None)
            if isinstance(end_lineno, int):
                parts = (*prefix, node.name)
                spans.append((node.lineno, end_lineno, ".".join(parts)))
                for child in ast.iter_child_nodes(node):
                    visit(node=child, prefix=parts)
            return
        for child in ast.iter_child_nodes(node):
            visit(node=child, prefix=prefix)

    visit(node=tree, prefix=())
    return spans


def _resolve_from_spans(*, spans: Sequence[SymbolSpan], row: int) -> str | None:
    matches = [(start, end, symbol) for start, end, symbol in spans if start <= row <= end]
    if not matches:
        return None
    return min(matches, key=lambda item: (item[1] - item[0], -item[0]))[2]


def resolve_qualified_symbol(*, source: str, row: int) -> str | None:
    """Resolve the innermost function or method enclosing a one-based row."""
    spans = _collect_symbol_spans(source)
    return None if spans is None else _resolve_from_spans(spans=spans, row=row)


def parse_violation_record(
    ruff_json_item: object, *, file_source: str
) -> Record | None:
    """Compatibility projection of one Ruff violation for focused callers."""
    if not isinstance(ruff_json_item, dict):
        return None
    item = cast("Mapping[str, object]", ruff_json_item)
    filename, code, message, location = (
        item.get("filename"), item.get("code"), item.get("message"), item.get("location")
    )
    if not isinstance(filename, str) or not isinstance(code, str) or not isinstance(message, str):
        return None
    if code not in COMPLEXITY_CODES or not isinstance(location, dict):
        return None
    row = cast("Mapping[str, object]", location).get("row")
    metric = parse_metric(code=code, message=message)
    symbol = resolve_qualified_symbol(source=file_source, row=row) if isinstance(row, int) else None
    if metric is None or symbol is None:
        return None
    return {"file": normalize_file_path(filename), "code": code, "qualified_symbol": symbol, "metric": metric}


def utc_today() -> date:
    """Return the current UTC calendar date through a testable seam."""
    return datetime.now(UTC).date()


def _root_for_baseline(path: Path) -> Path:
    """Infer a safe root for legacy library callers that pass only a path."""
    return path.parent.parent if path.parent.name == "python" else path.parent


def _typed_rows(records: Sequence[Record], *, source: Path, strict: bool = True) -> list[ComplexityBaselineRow]:
    return parse_complexity_baseline(json.dumps(list(records)), source=str(source), strict=strict, today=utc_today())


def load_baseline(path: Path | str) -> list[Record]:
    """Compatibility adapter over the engine-owned typed baseline parser."""
    baseline_path = Path(path)
    rows = load_complexity_baseline(baseline_path, root=_root_for_baseline(baseline_path), today=utc_today())
    return [complexity_row_record(row) for row in rows]


def serialize_baseline(records: Sequence[Record]) -> str:
    """Compatibility serializer retaining the committed field order."""
    rows = _typed_rows(records, source=Path("<records>"))
    return serialize_complexity_baseline(rows)


def write_baseline(*, path: Path, records: Sequence[Record]) -> None:
    """Compatibility write adapter; engine performs all actual baseline I/O."""
    rows = _typed_rows(records, source=path)
    _ = write_complexity_baseline(path, root=_root_for_baseline(path), rows=rows, today=utc_today())


def migrate_baseline(path: Path) -> int:
    """Compatibility migration adapter backed by the engine."""
    return migrate_complexity_baseline(path, root=_root_for_baseline(path), today=utc_today())


def _record_identity(record: Mapping[str, object]) -> tuple[str, str, str]:
    return (str(record["file"]), str(record["code"]), str(record["qualified_symbol"]))


def _legacy_live_row(record: Mapping[str, object]) -> ComplexityLiveRow:
    file_name, code, symbol = _record_identity(record)
    return ComplexityLiveRow(
        file_name,
        cast("ComplexityCode", code),
        symbol,
        cast("int", record["metric"]),
    )


def find_duplicate_keys(records: Sequence[Record]) -> list[str]:
    """Return duplicate complexity identities for legacy callers."""
    live = [_legacy_live_row(record) for record in records]
    return complexity_duplicate_identities(live)


def index_baseline(records: Sequence[Record]) -> dict[tuple[str, str, str], int]:
    """Map the metric-independent record identity to its allowed metric."""
    return {
        _record_identity(record): cast("int", record["metric"])
        for record in records
    }


def find_regressions(*, live_records: Sequence[Record], baseline_index: Mapping[tuple[str, str, str], int]) -> list[str]:
    """Compatibility comparison helper retaining existing diagnostics."""
    regressions: list[str] = []
    for record in live_records:
        file_name, code, symbol = _record_identity(record)
        metric = cast("int", record["metric"])
        baseline = baseline_index.get((file_name, code, symbol))
        if baseline is None:
            regressions.append(f"{file_name}:{symbol} {code} (new)")
        elif metric > baseline:
            regressions.append(f"{file_name}:{symbol} {code} metric {metric} > baseline {baseline}")
    return regressions


def merge_baseline(*, live_records: Sequence[Record], stored_records: Sequence[Record], reason: str | None, today: date, source: Path) -> list[Record]:
    """Compatibility adapter for callers still passing mapping-shaped records."""
    del source
    live = [_legacy_live_row(record) for record in live_records]
    stored = _typed_rows(stored_records, source=Path("<stored>"))
    return [complexity_row_record(row) for row in merge_complexity_baseline(live_rows=live, stored_rows=stored, reason=reason, today=today)]


def _run_ruff(python_dir: Path) -> RuffResult:
    try:
        proc = subprocess.run(list(RUFF_ARGS), cwd=python_dir, check=False, capture_output=True, text=True)
    except OSError as exc:
        return RuffResult(returncode=2, stdout="", stderr=str(exc))
    return RuffResult(proc.returncode, proc.stdout, proc.stderr)


def _load_ruff_items(result: RuffResult) -> list[object]:
    if result.returncode >= TOOL_FAILURE_EXIT:
        raise ScanError(f"ruff exited {result.returncode}: {result.stderr.strip()}")
    if not result.stdout.strip():
        raise ScanError("ruff produced empty JSON output")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ScanError(f"ruff produced invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ScanError("ruff JSON output must be a list")
    return cast("list[object]", data)


def _parse_live_records(*, items: Sequence[object], python_dir: Path) -> tuple[list[ComplexityLiveRow], list[str]]:
    rows: list[ComplexityLiveRow] = []
    failures: list[str] = []
    source_cache: dict[str, str] = {}
    span_cache: dict[str, list[SymbolSpan]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("filename"), str):
            failures.append("<unknown>: malformed ruff JSON item")
            continue
        mapping = cast("Mapping[str, object]", item)
        filename = normalize_file_path(cast("str", mapping["filename"]))
        if is_exempt_path(filename):
            continue
        source = source_cache.get(filename)
        if source is None:
            try:
                source = (python_dir / filename).read_text(encoding="utf-8")
            except OSError:
                failures.append(f"{filename}: cannot read source")
                continue
            source_cache[filename] = source
        code, message, location = mapping.get("code"), mapping.get("message"), mapping.get("location")
        row = cast("Mapping[str, object]", location).get("row") if isinstance(location, dict) else None
        if not isinstance(code, str) or code not in COMPLEXITY_CODES or not isinstance(message, str) or not isinstance(row, int):
            failures.append(f"{filename}: cannot parse violation")
            continue
        spans = span_cache.get(filename)
        if spans is None:
            spans = _collect_symbol_spans(source)
            if spans is None:
                failures.append(f"{filename}: cannot parse violation")
                continue
            span_cache[filename] = spans
        metric = parse_metric(code=code, message=message)
        symbol = _resolve_from_spans(spans=spans, row=row)
        if metric is None or symbol is None:
            failures.append(f"{filename}: cannot parse violation")
            continue
        rows.append(ComplexityLiveRow(filename, cast("ComplexityCode", code), symbol, metric))
    return rows, failures


def _collect_live_records(python_dir: Path) -> list[ComplexityLiveRow]:
    """Run Ruff and return validated current observations."""
    rows, failures = _parse_live_records(items=_load_ruff_items(_run_ruff(python_dir)), python_dir=python_dir)
    if failures:
        raise ScanError("\n".join(failures))
    duplicates = complexity_duplicate_identities(rows)
    if duplicates:
        raise ScanError("duplicate live complexity identities:\n" + "\n".join(duplicates))
    return rows


def history_events(records: Sequence[Record]) -> dict[tuple[str, str], list[HistoryEvent]]:
    """Compatibility adapter retaining the historical event-report API."""
    return complexity_history_events(_typed_rows(records, source=Path("<records>")))


def _format_event(event: HistoryEvent) -> str:
    return f"{event.event_date.isoformat()} [{event.record.code}] metric {event.metric}"


def repeat_bump_failures(records: Sequence[Record]) -> list[str]:
    """Return every unoverridden second bump inside the inclusive 14-day window."""
    failures: list[str] = []
    for (file_name, symbol), events in sorted(history_events(records).items()):
        for previous, current in pairwise(events):
            if (current.event_date - previous.event_date).days > REPEAT_BUMP_DAYS or current.record.operator_override is not None:
                continue
            failures.append(f"repeat complexity bumps for {file_name}:{symbol}: {_format_event(previous)}; {_format_event(current)}. Simplify the function, split it, or add an operator override.")
    return failures


def active_overrides(records: Sequence[Record]) -> list[str]:
    """Render all active manual override records in canonical identity order."""
    return [
        f"active operator override: {row.file}:{row.qualified_symbol} [{row.code}] issue #{row.operator_override.issue}: {row.operator_override.reason}"
        for row in _typed_rows(records, source=Path("<records>"))
        if row.operator_override is not None
    ]


def _run_write(*, root: Path, python_dir: Path, baseline_path: Path, reason: str | None) -> int:
    try:
        live = _collect_live_records(python_dir)
        stored = load_complexity_baseline(
            baseline_path, root=root, today=utc_today(), allow_missing=True
        )
        merged = merge_complexity_baseline(live_rows=live, stored_rows=stored, reason=reason, today=utc_today())
        _ = write_complexity_baseline(baseline_path, root=root, rows=merged, today=utc_today())
    except ScanError as exc:
        print(f"lint-complexity-baseline: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    print(f"lint-complexity-baseline: wrote {len(merged)} records to {baseline_path}", file=sys.stderr)
    return 0


def _run_check(*, root: Path, python_dir: Path, baseline_path: Path) -> int:
    try:
        live = _collect_live_records(python_dir)
        baseline = load_complexity_baseline(baseline_path, root=root, today=utc_today())
    except ScanError as exc:
        print(f"lint-complexity-baseline: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    regressions = complexity_regressions(live_rows=live, baseline_rows=baseline)
    records = [complexity_row_record(row) for row in baseline]
    failures = repeat_bump_failures(records)
    for line in [*regressions, *failures, *active_overrides(records)]:
        print(line, file=sys.stderr)
    return 1 if regressions or failures else 0


def main(argv: list[str] | None = None) -> int:
    """Run the compatible complexity baseline check, write, or migration mode."""
    parsed = parse_complexity_baseline_argv(argv if argv is not None else sys.argv[1:], default_root=Path(__file__).resolve().parents[3])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    python_dir = parsed.root / "python"
    if not python_dir.is_dir():
        print(f"lint-complexity-baseline: python directory not found: {python_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_path = python_dir / "complexity-baseline.json"
    if parsed.migrate:
        try:
            count = migrate_complexity_baseline(baseline_path, root=parsed.root, today=utc_today())
        except ScanError as exc:
            print(f"lint-complexity-baseline: {exc}", file=sys.stderr)
            return TOOL_FAILURE_EXIT
        print(f"lint-complexity-baseline: migrated {count} records in {baseline_path}", file=sys.stderr)
        return 0
    if parsed.write:
        return _run_write(root=parsed.root, python_dir=python_dir, baseline_path=baseline_path, reason=parsed.reason)
    return _run_check(root=parsed.root, python_dir=python_dir, baseline_path=baseline_path)
