"""Custom AST lint: keyword-only argument enforcement in python/ non-test source.

Flags any def / async def in python/ non-test source with 2 or more non-self/cls
positional parameters that lacks a bare *.  Ships warning-only behind a baseline
file (keyword-only-baseline.json) listing every currently-failing def, mirroring
the lint_complexity_baseline.py ratchet pattern.  New violations fail (exit 1);
baselined ones only warn (exit 0).  Use --write to regenerate the baseline.

Waiver paths for externally dictated or callback-shaped signatures:
- Fixed-signature protocol dunders (``__eq__``, ``__enter__``, ``__exit__``, and similar;
  not ``__init__``, ``__new__``, or ``__call__``).
- Override methods on ``argparse.ArgumentParser`` subclasses (auto-detected).
- ``ast.NodeVisitor.visit_*`` callbacks (auto-detected).
- Trailing or standalone ``# lint-keyword-only: ok <reason>`` on the ``def`` line.
- Optional ``keyword-only-exemptions.json`` rows with ``file`` and
  ``qualified_symbol``.
"""

from __future__ import annotations

import argparse as argparse_module
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_KEYS = frozenset({"file", "qualified_symbol"})
EXEMPTION_KEYS = frozenset({"file", "qualified_symbol", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
SELF_LIKE = frozenset({"self", "cls"})
MIN_POSITIONAL_PARAMS = 2
STANDALONE_PRAGMA_RE = re.compile(r"^\s*#\s*lint-keyword-only: ok\s+(\S.*)$")
TRAILING_PRAGMA_RE = re.compile(r"\s#\s*lint-keyword-only: ok\s+(\S.*)$")
BARE_STAR_IN_ARGS_RE = re.compile(r"(?:[(,]\s*)\*(?!\w|\*)")
_DEF_HEAD_RE = re.compile(r"(?:async\s+)?def\s+\w+\s*\(")


class Record(TypedDict):
    file: str
    qualified_symbol: str


class BaselineError(ValueError):
    """Raised when the committed baseline cannot be trusted."""


@dataclass(frozen=True)
class ScanContext:
    normalized_file: str
    source_lines: tuple[str, ...]
    exemption_keys: frozenset[tuple[str, str]]


def is_exempt_path(name: str) -> bool:
    """Return True when the filename is pytest-facing and not production source."""
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


FIXED_SIGNATURE_PROTOCOL_DUNDERS = frozenset(
    {
        "__repr__",
        "__str__",
        "__bytes__",
        "__format__",
        "__lt__",
        "__le__",
        "__eq__",
        "__ne__",
        "__gt__",
        "__ge__",
        "__hash__",
        "__bool__",
        "__getattr__",
        "__getattribute__",
        "__setattr__",
        "__delattr__",
        "__dir__",
        "__get__",
        "__set__",
        "__delete__",
        "__len__",
        "__length_hint__",
        "__getitem__",
        "__setitem__",
        "__delitem__",
        "__contains__",
        "__missing__",
        "__iter__",
        "__next__",
        "__reversed__",
        "__enter__",
        "__exit__",
        "__aenter__",
        "__aexit__",
        "__aiter__",
        "__anext__",
        "__await__",
        "__abs__",
        "__neg__",
        "__pos__",
        "__invert__",
        "__index__",
        "__int__",
        "__float__",
        "__complex__",
        "__trunc__",
        "__floor__",
        "__ceil__",
        "__round__",
        "__add__",
        "__sub__",
        "__mul__",
        "__matmul__",
        "__truediv__",
        "__floordiv__",
        "__mod__",
        "__divmod__",
        "__pow__",
        "__lshift__",
        "__rshift__",
        "__and__",
        "__xor__",
        "__or__",
        "__radd__",
        "__rsub__",
        "__rmul__",
        "__rmatmul__",
        "__rtruediv__",
        "__rfloordiv__",
        "__rmod__",
        "__rdivmod__",
        "__rpow__",
        "__rlshift__",
        "__rrshift__",
        "__rand__",
        "__rxor__",
        "__ror__",
        "__iadd__",
        "__isub__",
        "__imul__",
        "__imatmul__",
        "__itruediv__",
        "__ifloordiv__",
        "__imod__",
        "__ipow__",
        "__ilshift__",
        "__irshift__",
        "__iand__",
        "__ixor__",
        "__ior__",
        "__copy__",
        "__deepcopy__",
        "__del__",
        "__post_init__",
        "__buffer__",
        "__match_args__",
    }
)


def _is_fixed_signature_protocol_dunder(func_name: str) -> bool:
    return func_name in FIXED_SIGNATURE_PROTOCOL_DUNDERS


def _def_args_paren_text(
    source: str, func: ast.FunctionDef | ast.AsyncFunctionDef
) -> str | None:
    """Return the parenthesized parameter list text for one function definition."""
    lines = source.splitlines()
    start = func.lineno - 1
    end = (func.end_lineno or func.lineno) - 1
    if start < 0 or end >= len(lines):
        return None
    chunk = "\n".join(lines[start : end + 1])
    match = _DEF_HEAD_RE.search(chunk)
    if match is None:
        return None
    open_paren = match.end() - 1
    depth = 0
    for index in range(open_paren, len(chunk)):
        char = chunk[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return chunk[open_paren : index + 1]
    return None


def _has_bare_star_separator(  # type: ignore[reportUnusedFunction]
    args: ast.arguments,
    source: str | None = None,
    func: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
) -> bool:
    """Return True when the signature uses a bare * (not a named *args)."""
    if args.vararg is not None:
        return False
    if source is not None:
        segment: str | None = ast.get_source_segment(source, args)
        if segment is None and func is not None:
            segment = _def_args_paren_text(source, func)
        if segment is not None and BARE_STAR_IN_ARGS_RE.search(segment):
            return True
    return bool(args.kwonlyargs)


def _has_violation(args: ast.arguments) -> bool:
    """Return True when 2+ non-self/cls params remain positional-or-keyword."""
    positional: list[ast.arg] = list(args.posonlyargs) + list(args.args)
    non_self_cls: list[ast.arg] = [a for a in positional if a.arg not in SELF_LIKE]
    return len(non_self_cls) >= MIN_POSITIONAL_PARAMS


def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _is_argument_parser_subclass(class_node: ast.ClassDef) -> bool:
    return any(_base_name(base) == "ArgumentParser" for base in class_node.bases)


def _is_node_visitor_subclass(class_node: ast.ClassDef) -> bool:
    return any(_base_name(base) == "NodeVisitor" for base in class_node.bases)


def _is_external_api_override(class_node: ast.ClassDef, method_name: str) -> bool:
    if not _is_argument_parser_subclass(class_node):
        return False
    return hasattr(argparse_module.ArgumentParser, method_name)


def _is_node_visitor_callback(class_node: ast.ClassDef, method_name: str) -> bool:
    return _is_node_visitor_subclass(class_node) and method_name.startswith("visit_")


def _line_has_pragma(line: str) -> bool:
    return bool(
        STANDALONE_PRAGMA_RE.match(line) or TRAILING_PRAGMA_RE.search(line)
    )


def _should_report_violation(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    prefix: tuple[str, ...],
    *,
    ctx: ScanContext,
    containing_class: ast.ClassDef | None,
) -> bool:
    if _is_fixed_signature_protocol_dunder(func.name):
        return False
    qualified: str = ".".join((*prefix, func.name))
    if (ctx.normalized_file, qualified) in ctx.exemption_keys:
        return False
    if 0 < func.lineno <= len(ctx.source_lines) and _line_has_pragma(
        ctx.source_lines[func.lineno - 1]
    ):
        return False
    if containing_class is not None:
        if _is_external_api_override(containing_class, func.name):
            return False
        if _is_node_visitor_callback(containing_class, func.name):
            return False
    return _has_violation(func.args)


def _collect_function_violations(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    prefix: tuple[str, ...],
    *,
    ctx: ScanContext,
    containing_class: ast.ClassDef | None,
) -> list[Record]:
    violations: list[Record] = []
    if _should_report_violation(
        func, prefix, ctx=ctx, containing_class=containing_class
    ):
        qualified: str = ".".join((*prefix, func.name))
        violations.append({"file": ctx.normalized_file, "qualified_symbol": qualified})
    violations.extend(
        _collect_violations(
            func, (*prefix, func.name), ctx=ctx, containing_class=None
        )
    )
    return violations


def _collect_violations(
    node: ast.AST,
    prefix: tuple[str, ...],
    *,
    ctx: ScanContext,
    containing_class: ast.ClassDef | None = None,
) -> list[Record]:
    violations: list[Record] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            violations.extend(
                _collect_violations(
                    child,
                    (*prefix, child.name),
                    ctx=ctx,
                    containing_class=child,
                )
            )
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            violations.extend(
                _collect_function_violations(
                    child, prefix, ctx=ctx, containing_class=containing_class
                )
            )
        else:
            violations.extend(
                _collect_violations(child, prefix, ctx=ctx, containing_class=containing_class)
            )
    return violations


def _validate_exemption_record(item: object, *, index: int, source: Path) -> tuple[str, str]:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: exemption {index} must be an object")
    record: dict[str, object] = cast("dict[str, object]", item)
    if set(record) - EXEMPTION_KEYS:
        raise BaselineError(
            f"{source}: exemption {index} must have keys {sorted(EXEMPTION_KEYS)}"
        )
    file_val: object = record.get("file")
    sym_val: object = record.get("qualified_symbol")
    if not isinstance(file_val, str) or not file_val:
        raise BaselineError(f"{source}: exemption {index} has invalid file")
    if not isinstance(sym_val, str) or not sym_val:
        raise BaselineError(f"{source}: exemption {index} has invalid qualified_symbol")
    reason: object = record.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise BaselineError(f"{source}: exemption {index} has invalid reason")
    return (file_val, sym_val)


def load_exemptions(path: Path) -> frozenset[tuple[str, str]]:
    """Load optional exemption rows; missing file yields an empty set."""
    if not path.is_file():
        return frozenset()
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"{path}: cannot load exemptions: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: exemptions must be a top-level JSON array")
    items: list[object] = cast("list[object]", data)
    return frozenset(
        _validate_exemption_record(item, index=index, source=path)
        for index, item in enumerate(items)
    )


def scan_file(
    path: Path,
    *,
    python_dir: Path,
    exemption_keys: frozenset[tuple[str, str]],
) -> list[Record]:
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
    ctx = ScanContext(
        normalized_file=normalized,
        source_lines=tuple(source.splitlines()),
        exemption_keys=exemption_keys,
    )
    return _collect_violations(tree, (), ctx=ctx)


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


def _collect_all(
    python_dir: Path, *, exemption_keys: frozenset[tuple[str, str]]
) -> list[Record]:
    records: list[Record] = []
    for path in iter_source_files(python_dir):
        records.extend(
            scan_file(path, python_dir=python_dir, exemption_keys=exemption_keys)
        )
    return records


def _run_write(
    python_dir: Path,
    *,
    baseline_path: Path,
    exemption_keys: frozenset[tuple[str, str]],
) -> int:
    records: list[Record] = _collect_all(python_dir, exemption_keys=exemption_keys)
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(
        f"lint-keyword-only: wrote {len(records)} records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check(
    python_dir: Path,
    *,
    baseline_path: Path,
    exemption_keys: frozenset[tuple[str, str]],
) -> int:
    try:
        baseline_records: list[Record] = load_baseline(baseline_path)
    except BaselineError as exc:
        print(f"lint-keyword-only: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_set: frozenset[tuple[str, str]] = frozenset(
        _record_key(r) for r in baseline_records
    )
    live_records: list[Record] = _collect_all(python_dir, exemption_keys=exemption_keys)
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


def _parse_args(argv: list[str]) -> argparse_module.Namespace | None:
    parser = argparse_module.ArgumentParser(
        prog="cli.py lint keyword-only", description=__doc__
    )
    _ = parser.add_argument(
        "--root", default=str(Path(__file__).resolve().parents[3])
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
    parsed: argparse_module.Namespace | None = _parse_args(
        argv=argv if argv is not None else sys.argv[1:]
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
    exemptions_path: Path = python_dir / "keyword-only-exemptions.json"
    try:
        exemption_keys: frozenset[tuple[str, str]] = load_exemptions(exemptions_path)
    except BaselineError as exc:
        print(f"lint-keyword-only: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if parsed.write:
        return _run_write(
            python_dir=python_dir, baseline_path=baseline_path, exemption_keys=exemption_keys
        )
    return _run_check(
        python_dir=python_dir, baseline_path=baseline_path, exemption_keys=exemption_keys
    )


if __name__ == "__main__":
    raise SystemExit(main())
