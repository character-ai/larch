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
from typing import TypedDict, cast

COMPLEXITY_CODES = ("C901", "PLR0911", "PLR0912", "PLR0913", "PLR0915")
TOOL_FAILURE_EXIT = 2
BASELINE_KEYS = frozenset({"file", "code", "qualified_symbol", "metric"})
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


class Record(TypedDict):
    file: str
    code: str
    qualified_symbol: str
    metric: int


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


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(
            f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}"
        )
    record = cast("Mapping[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(
            f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}"
        )
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
    return {
        "file": file_name,
        "code": code,
        "qualified_symbol": qualified_symbol,
        "metric": metric,
    }


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
        _validate_record(item, index=index, source=baseline_path)
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
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Regenerate complexity-baseline.json from live ruff output "
            "instead of checking against it."
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


def serialize_baseline(records: list[Record]) -> str:
    """Return canonical baseline JSON: key-sorted, 2-space, trailing newline."""
    ordered = sorted(records, key=_record_key)
    return json.dumps(ordered, indent=2) + "\n"


def write_baseline( *,path: Path, records: list[Record]) -> None:
    """Write the canonical baseline JSON for ``records`` to ``path``."""
    _ = path.write_text(serialize_baseline(records), encoding="utf-8")


def _run_write( *,python_dir: Path, baseline_path: Path) -> int:
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
    if parsed.write:
        return _run_write(python_dir=python_dir, baseline_path=baseline_path)
    return _run_check(python_dir=python_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
