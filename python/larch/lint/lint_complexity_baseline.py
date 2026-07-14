"""Ratchet ruff complexity findings against a committed production baseline.

The baseline identity deliberately comes from source, not from ruff's display
message. ``qualified_symbol`` is AST-derived for every rule: PLR messages carry
only metrics, and C901's message-local name is still ambiguous across nesting.
``file`` paths are normalized so audit runs from ``cwd=python/`` do not split
keys across ``./ship.py`` and ``ship.py``. Baseline rows omit line numbers so
innocent edits above a function do not require rebaselining.

The default mode checks live findings against the baseline and fails on
regressions. ``--write`` instead regenerates ``complexity-baseline.json`` from
live ruff output: it is the mechanical entrypoint that emits the per-file
grandfather rows, so the baseline is never hand-maintained. Generation reuses
the same fail-closed collection as the check -- a ruff tool failure, an
unparseable finding, or a duplicate live identity aborts before any write -- and
the emitted rows are sorted canonically so an unchanged tree regenerates
byte-identically.

Committed baselines carry a nine-field schema: the four identity fields plus
``added_at`` and ``history`` (required), and optional ``source_issue``,
``reason``, and ``operator_override``. ``--migrate`` grandfathers legacy or
partially migrated records in place by adding only the missing ``added_at``
and ``history`` fields. Until a metadata-preserving writer lands, ``--write``
refuses to overwrite any baseline that already carries extended metadata, so
the unchanged four-field writer never clobbers migration history.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, cast

COMPLEXITY_CODES = ("C901", "PLR0911", "PLR0912", "PLR0913", "PLR0915")
TOOL_FAILURE_EXIT = 2
IDENTITY_KEYS = frozenset({"file", "code", "qualified_symbol", "metric"})
STRICT_REQUIRED_KEYS = IDENTITY_KEYS | {"added_at", "history"}
OPTIONAL_KEYS = frozenset({"source_issue", "reason", "operator_override"})
ALL_KEYS = STRICT_REQUIRED_KEYS | OPTIONAL_KEYS
EXTENDED_ONLY_KEYS = ALL_KEYS - IDENTITY_KEYS
HISTORY_ENTRY_KEYS = frozenset({"date", "metric"})
OPERATOR_OVERRIDE_KEYS = frozenset({"reason", "issue"})
FIELD_ORDER = (
    "file",
    "code",
    "qualified_symbol",
    "metric",
    "added_at",
    "history",
    "source_issue",
    "reason",
    "operator_override",
)
EXEMPT_FILENAMES = frozenset(
    {"conftest.py", "test_support.py", "review_test_support.py"}
)
METRIC_RE = re.compile(r"\((\d+)\s*>\s*\d+\)")
RUFF_ARGS = (
    "ruff",
    "check",
    ".",
    "--no-cache",
    "--select",
    ",".join(COMPLEXITY_CODES),
    "--output-format",
    "json",
    "--config",
    "ruff-complexity-audit.toml",
)


class HistoryEntry(TypedDict):
    date: str
    metric: int


class OperatorOverride(TypedDict):
    reason: str
    issue: int


class Record(TypedDict):
    file: str
    code: str
    qualified_symbol: str
    metric: int
    added_at: NotRequired[str]
    history: NotRequired[list[HistoryEntry]]
    source_issue: NotRequired[int]
    reason: NotRequired[str]
    operator_override: NotRequired[OperatorOverride]


BaselineIndex = dict[tuple[str, str, str], int]
SymbolSpan = tuple[int, int, str]


class BaselineError(ValueError):
    """Raised when the committed baseline cannot be trusted."""


@dataclass(frozen=True)
class RuffResult:
    returncode: int
    stdout: str
    stderr: str


def normalize_file_path(raw: str) -> str:
    """Return a normalized repo-relative path under the python directory."""
    normalized = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized == "python":
        return ""
    return normalized.removeprefix("python/")


def is_exempt_path(path: str) -> bool:
    """Return whether a normalized path is pytest-facing and not production."""
    name = Path(path).name
    return (
        name.startswith("test_") and name.endswith(".py")
    ) or name in EXEMPT_FILENAMES


def parse_metric( *,code: str, message: str) -> int | None:
    """Extract the observed complexity count from a ruff message."""
    _ = code
    match = METRIC_RE.search(message)
    if match is None:
        return None
    return int(match.group(1))


def _collect_symbol_spans(source: str) -> list[SymbolSpan] | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    spans: list[SymbolSpan] = []

    def visit( *,node: ast.AST, prefix: tuple[str, ...]) -> None:
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


def _resolve_from_spans( *,spans: list[SymbolSpan], row: int) -> str | None:
    matches = [
        (start, end, symbol) for start, end, symbol in spans if start <= row <= end
    ]
    if not matches:
        return None
    return min(matches, key=lambda item: (item[1] - item[0], -item[0]))[2]


def resolve_qualified_symbol( *,source: str, row: int) -> str | None:
    """Resolve the innermost function or method enclosing a one-based row."""
    spans = _collect_symbol_spans(source)
    if spans is None:
        return None
    return _resolve_from_spans(spans=spans, row=row)


def parse_violation_record(
    ruff_json_item: object, *, file_source: str
) -> Record | None:
    """Normalize one ruff JSON finding into a stable baseline record."""
    if not isinstance(ruff_json_item, dict):
        return None
    item = cast("Mapping[str, object]", ruff_json_item)
    filename = item.get("filename")
    code = item.get("code")
    message = item.get("message")
    location = item.get("location")
    if (
        not isinstance(filename, str)
        or not isinstance(code, str)
        or not isinstance(message, str)
    ):
        return None
    if code not in COMPLEXITY_CODES or not isinstance(location, dict):
        return None
    location_record = cast("Mapping[str, object]", location)
    row = location_record.get("row")
    if not isinstance(row, int):
        return None
    metric = parse_metric(code=code, message=message)
    qualified_symbol = resolve_qualified_symbol(source=file_source, row=row)
    if metric is None or qualified_symbol is None:
        return None
    return {
        "file": normalize_file_path(filename),
        "code": code,
        "qualified_symbol": qualified_symbol,
        "metric": metric,
    }


def _validate_identity(
    record: Mapping[str, object], *, index: int, source: Path
) -> tuple[str, str, str, int]:
    file_name = record["file"]
    code = record["code"]
    qualified_symbol = record["qualified_symbol"]
    metric = record["metric"]
    if (
        not isinstance(file_name, str)
        or not file_name
        or normalize_file_path(file_name) != file_name
    ):
        raise BaselineError(f"{source}: record {index} has invalid file")
    if not isinstance(code, str) or code not in COMPLEXITY_CODES:
        raise BaselineError(f"{source}: record {index} has invalid code")
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(metric, int) or isinstance(metric, bool) or metric < 0:
        raise BaselineError(f"{source}: record {index} has invalid metric")
    return file_name, code, qualified_symbol, metric


def _validate_history(
    history: object, *, index: int, source: Path
) -> list[HistoryEntry]:
    if not isinstance(history, list):
        raise BaselineError(f"{source}: record {index} has invalid history")
    entries: list[HistoryEntry] = []
    for entry in cast("list[object]", history):
        if not isinstance(entry, dict):
            raise BaselineError(f"{source}: record {index} has malformed history entry")
        entry_map = cast("Mapping[str, object]", entry)
        if set(entry_map) != set(HISTORY_ENTRY_KEYS):
            raise BaselineError(f"{source}: record {index} has malformed history entry")
        date = entry_map["date"]
        entry_metric = entry_map["metric"]
        if not isinstance(date, str) or not date:
            raise BaselineError(f"{source}: record {index} has invalid history date")
        if (
            not isinstance(entry_metric, int)
            or isinstance(entry_metric, bool)
            or entry_metric < 0
        ):
            raise BaselineError(f"{source}: record {index} has invalid history metric")
        entries.append({"date": date, "metric": entry_metric})
    return entries


def _validate_operator_override(
    value: object, *, index: int, source: Path
) -> OperatorOverride:
    if not isinstance(value, dict):
        raise BaselineError(f"{source}: record {index} has invalid operator_override")
    value_map = cast("Mapping[str, object]", value)
    if set(value_map) != set(OPERATOR_OVERRIDE_KEYS):
        raise BaselineError(f"{source}: record {index} has invalid operator_override")
    reason = value_map["reason"]
    issue = value_map["issue"]
    if not isinstance(reason, str) or not reason:
        raise BaselineError(
            f"{source}: record {index} has invalid operator_override reason"
        )
    if not isinstance(issue, int) or isinstance(issue, bool) or issue <= 0:
        raise BaselineError(
            f"{source}: record {index} has invalid operator_override issue"
        )
    return {"reason": reason, "issue": issue}


def _check_record_keys(
    keys: set[str], *, index: int, source: Path, strict: bool
) -> None:
    unknown = keys - ALL_KEYS
    if unknown:
        raise BaselineError(f"{source}: record {index} has unknown fields {sorted(unknown)}")
    missing_identity = IDENTITY_KEYS - keys
    if missing_identity:
        raise BaselineError(
            f"{source}: record {index} missing identity fields {sorted(missing_identity)}"
        )
    if not strict:
        return
    missing_required = STRICT_REQUIRED_KEYS - keys
    if missing_required:
        raise BaselineError(
            f"{source}: record {index} missing required fields {sorted(missing_required)}"
        )


def _validate_added_at(value: object, *, index: int, source: Path) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: record {index} has invalid added_at")
    return value


def _validate_source_issue(value: object, *, index: int, source: Path) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise BaselineError(f"{source}: record {index} has invalid source_issue")
    return value


def _validate_reason(value: object, *, index: int, source: Path) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return value


def _validate_record(
    item: object, *, index: int, source: Path, strict: bool
) -> Record:
    """Validate one raw baseline record.

    ``strict`` requires the committed ``added_at``/``history`` fields (used
    by ``load_baseline``); non-strict validates whatever fields are present
    without requiring them (used by ``migrate_baseline`` on legacy or
    partially migrated input). Both reject unknown fields and missing
    identity fields.
    """
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must be an object")
    record = cast("Mapping[str, object]", item)
    keys = set(record)
    _check_record_keys(keys, index=index, source=source, strict=strict)
    file_name, code, qualified_symbol, metric = _validate_identity(
        record, index=index, source=source
    )
    result: Record = {
        "file": file_name,
        "code": code,
        "qualified_symbol": qualified_symbol,
        "metric": metric,
    }
    if "added_at" in keys:
        result["added_at"] = _validate_added_at(
            record["added_at"], index=index, source=source
        )
    if "history" in keys:
        result["history"] = _validate_history(record["history"], index=index, source=source)
    if "source_issue" in keys:
        result["source_issue"] = _validate_source_issue(
            record["source_issue"], index=index, source=source
        )
    if "reason" in keys:
        result["reason"] = _validate_reason(record["reason"], index=index, source=source)
    if "operator_override" in keys:
        result["operator_override"] = _validate_operator_override(
            record["operator_override"], index=index, source=source
        )
    return result


def load_baseline(path: Path | str) -> list[Record]:
    """Load and validate the top-level baseline JSON array."""
    baseline_path = Path(path)
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"{baseline_path}: cannot load baseline: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{baseline_path}: baseline must be a top-level JSON array")
    items = cast("list[object]", data)
    return [
        _validate_record(item, index=index, source=baseline_path, strict=True)
        for index, item in enumerate(items)
    ]


def _record_key(record: Record) -> tuple[str, str, str]:
    return (str(record["file"]), str(record["code"]), str(record["qualified_symbol"]))


def index_baseline(records: list[Record]) -> BaselineIndex:
    """Map baseline identity to the allowed observed metric."""
    return {_record_key(record): int(record["metric"]) for record in records}


def find_duplicate_keys(records: list[Record]) -> list[str]:
    """Return duplicate baseline identities as human-readable lines."""
    seen: set[tuple[str, str, str]] = set()
    duplicates: list[str] = []
    for record in records:
        key = _record_key(record)
        if key in seen:
            file_name, code, qualified_symbol = key
            duplicates.append(f"{file_name}:{qualified_symbol} {code}")
        else:
            seen.add(key)
    return duplicates


def find_regressions( *,
    live_records: list[Record], baseline_index: BaselineIndex
) -> list[str]:
    """Return new identities and metric growth compared with the baseline."""
    regressions: list[str] = []
    for record in live_records:
        key = _record_key(record)
        live_metric = int(record["metric"])
        baseline_metric = baseline_index.get(key)
        file_name, code, qualified_symbol = key
        if baseline_metric is None:
            regressions.append(f"{file_name}:{qualified_symbol} {code} (new)")
        elif live_metric > baseline_metric:
            regressions.append(
                f"{file_name}:{qualified_symbol} {code} metric {live_metric} > baseline {baseline_metric}"
            )
    return regressions


def _run_ruff(python_dir: Path) -> RuffResult:
    try:
        proc = subprocess.run(
            list(RUFF_ARGS),
            cwd=python_dir,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return RuffResult(returncode=2, stdout="", stderr=str(exc))
    return RuffResult(
        returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr
    )


def _load_ruff_items(result: RuffResult) -> list[object]:
    if result.returncode >= TOOL_FAILURE_EXIT:
        raise BaselineError(f"ruff exited {result.returncode}: {result.stderr.strip()}")
    if not result.stdout.strip():
        raise BaselineError("ruff produced empty JSON output")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BaselineError(f"ruff produced invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError("ruff JSON output must be a list")
    return cast("list[object]", data)


def _read_source( *,
    python_dir: Path, normalized_file: str, cache: dict[str, str]
) -> str | None:
    cached = cache.get(normalized_file)
    if cached is not None:
        return cached
    path = python_dir / normalized_file
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    cache[normalized_file] = source
    return source


def _parse_live_record( *,
    item: Mapping[str, object],
    normalized_file: str,
    source: str,
    span_cache: dict[str, list[SymbolSpan]],
) -> Record | None:
    code = item.get("code")
    message = item.get("message")
    location = item.get("location")
    if (
        not isinstance(code, str)
        or not isinstance(message, str)
        or code not in COMPLEXITY_CODES
    ):
        return None
    if not isinstance(location, dict):
        return None
    location_record = cast("Mapping[str, object]", location)
    row = location_record.get("row")
    if not isinstance(row, int):
        return None
    spans = span_cache.get(normalized_file)
    if spans is None:
        collected = _collect_symbol_spans(source)
        if collected is None:
            return None
        spans = collected
        span_cache[normalized_file] = spans
    qualified_symbol = _resolve_from_spans(spans=spans, row=row)
    metric = parse_metric(code=code, message=message)
    if qualified_symbol is None or metric is None:
        return None
    return {
        "file": normalized_file,
        "code": code,
        "qualified_symbol": qualified_symbol,
        "metric": metric,
    }


def _parse_live_records( *,
    items: list[object], python_dir: Path
) -> tuple[list[Record], list[str]]:
    records: list[Record] = []
    failures: list[str] = []
    source_cache: dict[str, str] = {}
    span_cache: dict[str, list[SymbolSpan]] = {}
    for item in items:
        if not isinstance(item, dict):
            failures.append("<unknown>: malformed ruff JSON item")
            continue
        item_mapping = cast("Mapping[str, object]", item)
        filename = item_mapping.get("filename")
        if not isinstance(filename, str):
            failures.append("<unknown>: malformed ruff JSON item")
            continue
        normalized_file = normalize_file_path(filename)
        if is_exempt_path(normalized_file):
            continue
        source = _read_source(python_dir=python_dir, normalized_file=normalized_file, cache=source_cache)
        if source is None:
            failures.append(f"{normalized_file}: cannot read source")
            continue
        record = _parse_live_record(item=item_mapping, normalized_file=normalized_file, source=source, span_cache=span_cache)
        if record is None:
            failures.append(f"{normalized_file}: cannot parse violation")
            continue
        records.append(record)
    return records, failures


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint complexity-baseline", description=__doc__
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Regenerate complexity-baseline.json from live ruff output "
            "instead of checking against it."
        ),
    )
    _ = parser.add_argument(
        "--migrate",
        action="store_true",
        help=(
            "Grandfather legacy or partially migrated baseline records in "
            "place instead of checking or writing."
        ),
    )
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _collect_live_records(python_dir: Path) -> list[Record]:
    """Run ruff and return validated live records, fail-closed on any defect."""
    ruff_items = _load_ruff_items(_run_ruff(python_dir))
    live_records, parse_failures = _parse_live_records(items=ruff_items, python_dir=python_dir)
    if parse_failures:
        raise BaselineError("\n".join(parse_failures))
    live_duplicates = find_duplicate_keys(live_records)
    if live_duplicates:
        raise BaselineError(
            "duplicate live complexity identities:\n" + "\n".join(live_duplicates)
        )
    return live_records


def _canonical_record(record: Record) -> dict[str, object]:
    mapping = cast("Mapping[str, object]", record)
    return {key: mapping[key] for key in FIELD_ORDER if key in mapping}


def serialize_baseline(records: list[Record]) -> str:
    """Return canonical baseline JSON: key-sorted, 2-space, trailing newline."""
    ordered = sorted(records, key=_record_key)
    canonical = [_canonical_record(record) for record in ordered]
    return json.dumps(canonical, indent=2) + "\n"


def write_baseline( *,path: Path, records: list[Record]) -> None:
    """Write the canonical baseline JSON for ``records`` to ``path``."""
    _ = path.write_text(serialize_baseline(records), encoding="utf-8")


def migrate_baseline(path: Path) -> int:
    """Grandfather legacy or partially migrated records in ``path`` in place.

    Adds only the missing ``added_at: "legacy"`` and ``history: []`` fields;
    every other identity and optional field is preserved verbatim. Fails
    closed on unknown fields, missing identity fields, or a changed
    ``(file, code, qualified_symbol) -> metric`` projection. Returns the
    count of records that gained migration metadata.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"{path}: cannot load baseline: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a top-level JSON array")
    items = cast("list[object]", data)
    validated = [
        _validate_record(item, index=index, source=path, strict=False)
        for index, item in enumerate(items)
    ]
    before_projection = {_record_key(record): record["metric"] for record in validated}

    migrated_count = 0
    migrated: list[Record] = []
    for record in validated:
        added_at = record.get("added_at")
        history = record.get("history")
        if added_at is None or history is None:
            migrated_count += 1
        new_record: Record = {
            "file": record["file"],
            "code": record["code"],
            "qualified_symbol": record["qualified_symbol"],
            "metric": record["metric"],
            "added_at": added_at if added_at is not None else "legacy",
            "history": history if history is not None else [],
        }
        if "source_issue" in record:
            new_record["source_issue"] = record["source_issue"]
        if "reason" in record:
            new_record["reason"] = record["reason"]
        if "operator_override" in record:
            new_record["operator_override"] = record["operator_override"]
        migrated.append(new_record)

    after_projection = {_record_key(record): record["metric"] for record in migrated}
    if before_projection != after_projection:
        raise BaselineError(
            f"{path}: migration would change the identity-to-metric projection"
        )
    write_baseline(path=path, records=migrated)
    return migrated_count


def _first_extended_metadata_reason(
    items: list[object], *, baseline_path: Path
) -> str | None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return f"{baseline_path}: record {index} is not an object"
        item_map = cast("Mapping[str, object]", item)
        extended = set(item_map) & EXTENDED_ONLY_KEYS
        if extended:
            return (
                f"{baseline_path}: record {index} carries migrated metadata "
                f"{sorted(extended)}"
            )
    return None


def _write_guard_blocks(baseline_path: Path) -> tuple[bool, str | None]:
    """Return ``(blocked, reason)`` for the fail-closed ``--write`` pre-check.

    A nonexistent baseline is a genuine bootstrap and is never blocked. Any
    existing baseline that already carries extended metadata (fully or
    partially migrated) blocks the unchanged four-field writer, since it
    cannot preserve that metadata.
    """
    if not baseline_path.exists():
        return False, None
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return True, f"cannot read {baseline_path}: {exc}"
    except json.JSONDecodeError as exc:
        return True, f"{baseline_path}: cannot parse existing baseline: {exc}"
    if not isinstance(data, list):
        return True, f"{baseline_path}: existing baseline must be a top-level JSON array"
    reason = _first_extended_metadata_reason(
        cast("list[object]", data), baseline_path=baseline_path
    )
    if reason is not None:
        return True, reason
    return False, None


def _run_write( *,python_dir: Path, baseline_path: Path) -> int:
    blocked, reason = _write_guard_blocks(baseline_path)
    if blocked:
        print(
            f"lint-complexity-baseline: {reason}; baseline regeneration is "
            "disabled until Piece 2's metadata-preserving writer lands",
            file=sys.stderr,
        )
        return 2
    try:
        live_records = _collect_live_records(python_dir)
    except BaselineError as exc:
        print(f"lint-complexity-baseline: {exc}", file=sys.stderr)
        return 2
    write_baseline(path=baseline_path, records=live_records)
    print(
        f"lint-complexity-baseline: wrote {len(live_records)} "
        f"records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_migrate( *,baseline_path: Path) -> int:
    try:
        migrated_count = migrate_baseline(baseline_path)
    except BaselineError as exc:
        print(f"lint-complexity-baseline: {exc}", file=sys.stderr)
        return 2
    print(
        f"lint-complexity-baseline: migrated {migrated_count} "
        f"records in {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check( *,python_dir: Path, baseline_path: Path) -> int:
    try:
        live_records = _collect_live_records(python_dir)
        baseline_records = load_baseline(baseline_path)
        baseline_duplicates = find_duplicate_keys(baseline_records)
        if baseline_duplicates:
            raise BaselineError(
                "duplicate baseline complexity identities:\n"
                + "\n".join(baseline_duplicates)
            )
    except BaselineError as exc:
        print(f"lint-complexity-baseline: {exc}", file=sys.stderr)
        return 2

    regressions = find_regressions(live_records=live_records, baseline_index=index_baseline(baseline_records))
    for regression in regressions:
        print(regression, file=sys.stderr)
    return 1 if regressions else 0


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv=argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return 2
    root = Path(parsed.root).resolve()
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(
            f"lint-complexity-baseline: python directory not found: {python_dir}",
            file=sys.stderr,
        )
        return 2

    baseline_path = python_dir / "complexity-baseline.json"
    if parsed.migrate:
        return _run_migrate(baseline_path=baseline_path)
    if parsed.write:
        return _run_write(python_dir=python_dir, baseline_path=baseline_path)
    return _run_check(python_dir=python_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
