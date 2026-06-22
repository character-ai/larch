"""Custom AST lint: keyword-only argument enforcement in python/ non-test source.

Flags any def / async def in python/ non-test source with 2 or more non-self/cls
positional parameters that lacks a bare *.  Ships warning-only behind a baseline
file (keyword-only-baseline.json) listing every currently-failing def, mirroring
the lint_complexity_baseline.py ratchet pattern.  New violations fail (exit 1);
baselined ones only warn (exit 0).  Use --write to regenerate the baseline.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_KEYS = frozenset({"file", "qualified_symbol"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
SELF_LIKE = frozenset({"self", "cls"})
MIN_POSITIONAL_PARAMS = 2


class Record(TypedDict):
    file: str
    qualified_symbol: str


class BaselineError(ValueError):
    """Raised when the committed baseline cannot be trusted."""


def is_exempt_path(name: str) -> bool:
    """Return True when the filename is pytest-facing and not production source."""
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def _is_dunder(func_name: str) -> bool:
    return func_name.startswith("__") and func_name.endswith("__")


def _has_violation(args: ast.arguments) -> bool:
    """Return True when the function needs a bare * but lacks one."""
    if args.vararg is not None or args.kwonlyargs:
        return False
    positional: list[ast.arg] = list(args.posonlyargs) + list(args.args)
    non_self_cls: list[ast.arg] = [a for a in positional if a.arg not in SELF_LIKE]
    return len(non_self_cls) >= MIN_POSITIONAL_PARAMS


def _collect_violations(
    node: ast.AST,
    prefix: tuple[str, ...],
    *,
    normalized_file: str,
) -> list[Record]:
    violations: list[Record] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            violations.extend(
                _collect_violations(
                    child, (*prefix, child.name), normalized_file=normalized_file
                )
            )
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualified: str = ".".join((*prefix, child.name))
            if not _is_dunder(child.name) and _has_violation(child.args):
                violations.append({"file": normalized_file, "qualified_symbol": qualified})
            violations.extend(
                _collect_violations(
                    child, (*prefix, child.name), normalized_file=normalized_file
                )
            )
        else:
            violations.extend(
                _collect_violations(child, prefix, normalized_file=normalized_file)
            )
    return violations


def scan_file(path: Path, *, python_dir: Path) -> list[Record]:
    """Return keyword-only violations for one source file."""
    try:
        source: str = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree: ast.Module = ast.parse(source)
    except SyntaxError:
        return []
    normalized: str = path.relative_to(python_dir).as_posix()
    return _collect_violations(tree, (), normalized_file=normalized)


def iter_source_files(python_dir: Path) -> list[Path]:
    """Return non-test Python files in python_dir, sorted."""
    return sorted(
        p
        for p in python_dir.glob("*.py")
        if p.is_file() and not p.is_symlink() and not is_exempt_path(p.name)
    )


def _record_key(r: Record) -> tuple[str, str]:
    return (r["file"], r["qualified_symbol"])


def load_baseline(path: Path) -> list[Record]:
    """Load and validate the baseline JSON array."""
    try:
        raw: str = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from exc
    try:
        data: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a top-level JSON array")
    items: list[object] = cast("list[object]", data)
    result: list[Record] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise BaselineError(
                f"{path}: record {i} must have exactly {sorted(BASELINE_KEYS)}"
            )
        record: dict[str, object] = cast("dict[str, object]", item)
        if set(record) != set(BASELINE_KEYS):
            raise BaselineError(
                f"{path}: record {i} must have exactly {sorted(BASELINE_KEYS)}"
            )
        file_val: object = record["file"]
        sym_val: object = record["qualified_symbol"]
        if not isinstance(file_val, str) or not file_val:
            raise BaselineError(f"{path}: record {i} has invalid file")
        if not isinstance(sym_val, str) or not sym_val:
            raise BaselineError(f"{path}: record {i} has invalid qualified_symbol")
        result.append({"file": file_val, "qualified_symbol": sym_val})
    return result


def serialize_baseline(records: list[Record]) -> str:
    """Return canonical baseline JSON: key-sorted, 2-space indent, trailing newline."""
    ordered: list[Record] = sorted(records, key=_record_key)
    return json.dumps(ordered, indent=2) + "\n"


def _collect_all(python_dir: Path) -> list[Record]:
    records: list[Record] = []
    for path in iter_source_files(python_dir):
        records.extend(scan_file(path, python_dir=python_dir))
    return records


def _run_write(python_dir: Path, *, baseline_path: Path) -> int:
    records: list[Record] = _collect_all(python_dir)
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(
        f"lint-keyword-only: wrote {len(records)} records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check(python_dir: Path, *, baseline_path: Path) -> int:
    try:
        baseline_records: list[Record] = load_baseline(baseline_path)
    except BaselineError as exc:
        print(f"lint-keyword-only: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_set: frozenset[tuple[str, str]] = frozenset(
        _record_key(r) for r in baseline_records
    )
    live_records: list[Record] = _collect_all(python_dir)
    new_violations: list[Record] = []
    warned: list[Record] = []
    for rec in live_records:
        key: tuple[str, str] = _record_key(rec)
        if key in baseline_set:
            warned.append(rec)
        else:
            new_violations.append(rec)
    for rec in warned:
        print(
            f"warning: {rec['file']}:{rec['qualified_symbol']} missing * (baselined)",
            file=sys.stderr,
        )
    for rec in new_violations:
        print(
            f"{rec['file']}:{rec['qualified_symbol']} missing *"
            f" (2+ positional non-self/cls params)",
            file=sys.stderr,
        )
    return 1 if new_violations else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint keyword-only", description=__doc__
    )
    _ = parser.add_argument(
        "--root", default=str(Path(__file__).resolve().parents[1])
    )
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate keyword-only-baseline.json from live AST scan.",
    )
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    parsed: argparse.Namespace | None = _parse_args(
        argv if argv is not None else sys.argv[1:]
    )
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root: Path = Path(parsed.root).resolve()
    python_dir: Path = root / "python"
    if not python_dir.is_dir():
        print(
            f"lint-keyword-only: python directory not found: {python_dir}",
            file=sys.stderr,
        )
        return TOOL_FAILURE_EXIT
    baseline_path: Path = python_dir / "keyword-only-baseline.json"
    if parsed.write:
        return _run_write(python_dir, baseline_path=baseline_path)
    return _run_check(python_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
