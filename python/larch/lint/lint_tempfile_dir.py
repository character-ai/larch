"""Ratchet tempfile creation toward explicit scratch directories.

Scans production modules under python/larch/**/*.py for tempfile factory calls
that omit dir=. Existing deliberate ambient-temp uses are grandfathered in
python/tempfile-dir-baseline.json with a required reason per row.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "tempfile-dir-baseline.json"
ALLOWED_CALLEES = frozenset({"mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryDirectory"})
BASELINE_KEYS = frozenset({"file", "qualified_symbol", "callee", "occurrence", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
MODULE_SYMBOL = "<module>"


class Record(TypedDict):
    file: str
    qualified_symbol: str
    callee: str
    occurrence: int
    reason: str


class BaselineError(ValueError):
    """Raised when the baseline cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    callee: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, int]:
        return (self.file, self.qualified_symbol, self.callee, self.occurrence)


def normalize_file_path(raw: str) -> str:
    """Return a normalized POSIX path relative to python/."""
    normalized = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.removeprefix("python/")


def _validate_normalized_file(value: object, *, source: Path, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: record {index} has invalid file")
    normalized = normalize_file_path(value)
    parts = normalized.split("/")
    if (
        normalized != value
        or normalized.startswith("/")
        or not normalized.startswith("larch/")
        or not normalized.endswith(".py")
        or "" in parts
        or "." in parts
        or ".." in parts
    ):
        raise BaselineError(f"{source}: record {index} has invalid file")
    return normalized


def is_exempt_path(path: Path) -> bool:
    """Return whether a source file is outside production lint scope."""
    name = path.name
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def iter_source_files(larch_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under larch/, sorted."""
    result: list[Path] = []
    for path in sorted(larch_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink() or is_exempt_path(path):
            continue
        relative = path.relative_to(larch_dir.parent)
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        result.append(path)
    return result


def _qualified(prefix: tuple[str, ...]) -> str:
    return ".".join(prefix) if prefix else MODULE_SYMBOL


def _child_position(node: ast.AST, *, index: int) -> tuple[int, int, int]:
    if isinstance(node, ast.withitem):
        context_expr = node.context_expr
        return (
            getattr(context_expr, "lineno", 10**9),
            getattr(context_expr, "col_offset", 10**9),
            index,
        )
    return (
        getattr(node, "lineno", 10**9),
        getattr(node, "col_offset", 10**9),
        index,
    )


def _ordered_child_nodes(node: ast.AST) -> list[ast.AST]:
    children = list(ast.iter_child_nodes(node))
    indexed = list(enumerate(children))
    indexed.sort(key=lambda item: _child_position(item[1], index=item[0]))
    return [node for _, node in indexed]


def _tempfile_callee(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in ALLOWED_CALLEES:
        return None
    if not isinstance(func.value, ast.Name) or func.value.id != "tempfile":
        return None
    return func.attr


def _has_dir_keyword(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and any(keyword.arg == "dir" for keyword in node.keywords)


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    normalized_file: str,
    findings: list[Finding],
) -> None:
    occurrence = 0
    symbol = _qualified(prefix)

    def walk(node: ast.AST) -> None:
        nonlocal occurrence
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                normalized_file=normalized_file,
                findings=findings,
            )
            return
        if isinstance(node, ast.ClassDef):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                normalized_file=normalized_file,
                findings=findings,
            )
            return
        callee = _tempfile_callee(node)
        if callee is not None:
            occurrence += 1
            if not _has_dir_keyword(node):
                lineno = getattr(node, "lineno", 0)
                findings.append(
                    Finding(
                        file=normalized_file,
                        qualified_symbol=symbol,
                        callee=callee,
                        occurrence=occurrence,
                        lineno=lineno if isinstance(lineno, int) else 0,
                    )
                )
        for child in _ordered_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(path: Path, *, larch_dir: Path) -> list[Finding]:
    """Return tempfile-without-dir findings for one source file."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    findings: list[Finding] = []
    _collect_scope(
        tree.body,
        prefix=(),
        normalized_file=path.relative_to(larch_dir.parent).as_posix(),
        findings=findings,
    )
    return findings


def _record_key(record: Record) -> tuple[str, str, str, int]:
    return (
        record["file"],
        record["qualified_symbol"],
        record["callee"],
        record["occurrence"],
    )


def _finding_sort_key(finding: Finding) -> tuple[str, str, str, int]:
    return finding.key()


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name = _validate_normalized_file(record["file"], source=source, index=index)
    qualified_symbol = record["qualified_symbol"]
    callee = record["callee"]
    occurrence = record["occurrence"]
    reason = record["reason"]
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(callee, str) or callee not in ALLOWED_CALLEES:
        raise BaselineError(f"{source}: record {index} has invalid callee")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "qualified_symbol": qualified_symbol,
        "callee": callee,
        "occurrence": occurrence,
        "reason": reason,
    }


def _first_duplicate(
    keys: Iterable[tuple[str, str, str, int]],
) -> tuple[str, str, str, int] | None:
    seen: set[tuple[str, str, str, int]] = set()
    for key in keys:
        if key in seen:
            return key
        seen.add(key)
    return None


def load_baseline(path: Path) -> list[Record]:
    """Load and validate the committed baseline."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a top-level JSON array")
    records = [_validate_record(item, index=index, source=path) for index, item in enumerate(cast("list[object]", data))]
    duplicate = _first_duplicate(_record_key(record) for record in records)
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate baseline identity {format_key(duplicate)}")
    return records


def _collect_all(larch_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_source_files(larch_dir):
        findings.extend(scan_file(path, larch_dir=larch_dir))
    return findings


def _check_duplicate_live(findings: list[Finding]) -> str | None:
    duplicate = _first_duplicate(finding.key() for finding in findings)
    if duplicate is None:
        return None
    return f"duplicate live identity {format_key(duplicate)}"


def format_key(key: tuple[str, str, str, int]) -> str:
    file_name, qualified_symbol, callee, occurrence = key
    return f"{file_name}:{qualified_symbol} {callee}#{occurrence}"


def serialize_baseline(records: list[Record]) -> str:
    """Return canonical sorted JSON for the baseline."""
    ordered = sorted(records, key=_record_key)
    return json.dumps(ordered, indent=2) + "\n"


def _records_for_write(
    findings: list[Finding],
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> list[Record]:
    preserved: dict[tuple[str, str, str, int], str] = {}
    if baseline_path.is_file():
        preserved = {_record_key(record): record["reason"] for record in load_baseline(baseline_path)}
    reason_default = initial_reason.strip() if initial_reason is not None else None
    records: list[Record] = []
    missing: list[str] = []
    for finding in sorted(findings, key=_finding_sort_key):
        reason = preserved.get(finding.key()) or reason_default
        if reason is None:
            missing.append(format_key(finding.key()))
            continue
        records.append(
            {
                "file": finding.file,
                "qualified_symbol": finding.qualified_symbol,
                "callee": finding.callee,
                "occurrence": finding.occurrence,
                "reason": reason,
            }
        )
    if missing:
        joined = "\n  ".join(missing)
        raise BaselineError("missing baseline reasons for live tempfile findings:\n  " + joined)
    return records


def _run_write(
    larch_dir: Path,
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> int:
    try:
        findings = _collect_all(larch_dir)
        duplicate = _check_duplicate_live(findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
        records = _records_for_write(
            findings,
            baseline_path=baseline_path,
            initial_reason=initial_reason,
        )
    except BaselineError as exc:
        print(f"lint-tempfile-dir: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(f"lint-tempfile-dir: wrote {len(records)} records to {baseline_path}", file=sys.stderr)
    return 0


def _run_check(larch_dir: Path, *, baseline_path: Path) -> int:
    try:
        baseline_records = load_baseline(baseline_path)
        findings = _collect_all(larch_dir)
        duplicate = _check_duplicate_live(findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
    except BaselineError as exc:
        print(f"lint-tempfile-dir: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys = frozenset(_record_key(record) for record in baseline_records)
    new_findings: list[Finding] = []
    warned: list[Finding] = []
    for finding in sorted(findings, key=_finding_sort_key):
        if finding.key() in baseline_keys:
            warned.append(finding)
        else:
            new_findings.append(finding)
    for finding in warned:
        print(
            "warning: "
            f"{finding.file}:{finding.qualified_symbol} calls tempfile.{finding.callee} "
            f"occurrence {finding.occurrence} line {finding.lineno} (baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.file}:{finding.qualified_symbol} calls tempfile.{finding.callee} "
            f"occurrence {finding.occurrence} line {finding.lineno}; pass an explicit dir=",
            file=sys.stderr,
        )
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint tempfile-dir", description=__doc__)
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
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = Path(str(parsed.root)).resolve()
    larch_dir = root / "python" / "larch"
    if not larch_dir.is_dir():
        print(f"lint-tempfile-dir: larch directory not found: {larch_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_path = root / "python" / BASELINE_FILENAME
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-tempfile-dir: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(larch_dir, baseline_path=baseline_path, initial_reason=initial_reason)
    return _run_check(larch_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
