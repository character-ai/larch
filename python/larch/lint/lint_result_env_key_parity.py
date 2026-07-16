"""Ratchet result-env writers toward key-set parity across sibling writers.

Scans ``python/larch`` for result-env writer calls, groups them by the literal
target basename, and fails when one writer of a basename omits a key that a
sibling writer of the same basename emits. Sibling writers of one result env
that drift apart (a missing ``ROUNDS_COMPLETED`` on a zero-findings path, a
``detail`` field populated in one writer but not its twin) recurred as a class
that per-incident fixes never closed. Existing divergences are grandfathered in
a reason-bearing, shrink-only baseline.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "result-env-key-parity-baseline.json"
BASELINE_KEYS = frozenset({"basename", "path", "key", "reason"})
PRAGMA = "# lint-result-env-key-parity: ok"
WRITER_EXACT_NAMES = frozenset({"phase_driver_write_result_env", "write_result_env"})
WRITER_SUFFIX = "_write_result_env"
EXCLUDED_DIR_PARTS = frozenset({"__pycache__"})
KV_TUPLE_LEN = 2
MIN_SIBLING_WRITERS = 2

# Single declared place for per-key exceptions (G-Cfg-3): a basename maps to the
# keys a writer may omit without violating parity. Seeded empty; a per-key
# exception is added here, never scattered at call sites.
OPTIONAL_KEYS: Final[dict[str, frozenset[str]]] = {}


@dataclass(frozen=True)
class WriterCall:
    """A collected result-env writer call with a literal basename and key set."""

    path: str
    line: int
    basename: str
    keys: frozenset[str]
    suppressed: bool


@dataclass(frozen=True)
class Violation:
    basename: str
    path: str
    line: int
    key: str

    def identity(self) -> tuple[str, str, str]:
        return (self.basename, self.path, self.key)


class BaselineRow(TypedDict):
    basename: str
    path: str
    key: str
    reason: str


class BaselineError(ValueError):
    """Raised when a baseline file cannot be trusted."""


def _json_load(path: Path, *, label: str) -> list[object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BaselineError(f"{path}: cannot read {label}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: {label} must be a top-level JSON array")
    return cast("list[object]", data)


def _first_duplicate(keys: Iterable[tuple[str, ...]]) -> tuple[str, ...] | None:
    seen: set[tuple[str, ...]] = set()
    for key in keys:
        if key in seen:
            return key
        seen.add(key)
    return None


def _validate_baseline_row(item: object, *, index: int, source: Path) -> BaselineRow:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: baseline row {index} must be an object")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: baseline row {index} must have exactly {sorted(BASELINE_KEYS)}")
    values = {name: record[name] for name in BASELINE_KEYS}
    for name, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise BaselineError(f"{source}: baseline row {index} has invalid {name}")
    return {
        "basename": cast("str", values["basename"]),
        "path": cast("str", values["path"]),
        "key": cast("str", values["key"]),
        "reason": cast("str", values["reason"]),
    }


def load_baseline(path: Path) -> list[BaselineRow]:
    """Load and validate the committed baseline. Missing baseline means none."""
    if not path.is_file():
        return []
    rows = [_validate_baseline_row(item, index=index, source=path) for index, item in enumerate(_json_load(path, label="baseline"))]
    duplicate = _first_duplicate((row["basename"], row["path"], row["key"]) for row in rows)
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate baseline identity {':'.join(duplicate)}")
    return rows


def _iter_python_files(root: Path) -> list[Path]:
    base = root / "python" / "larch"
    if not base.is_dir():
        return []
    self_name = Path(__file__).name
    result: list[Path] = []
    for path in sorted(base.rglob("*.py")):
        if not path.is_file() or path.is_symlink():
            continue
        if EXCLUDED_DIR_PARTS.intersection(path.parts) or path.name == self_name:
            continue
        result.append(path)
    return result


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _callee_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _is_writer_name(name: str) -> bool:
    return name in WRITER_EXACT_NAMES or name.endswith(WRITER_SUFFIX)


def _call_arg_values(node: ast.Call) -> list[ast.expr]:
    return [*node.args, *(keyword.value for keyword in node.keywords)]


def _fstring_basename(node: ast.JoinedStr) -> str | None:
    """Return the final path component only when it is fully literal.

    The final component is everything after the last ``/``; an interpolation at
    or after that boundary makes it non-literal, so the call site is skipped.
    """
    tail: list[str] = []
    for value in reversed(node.values):
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            return None
        text: str = value.value
        slash = text.rfind("/")
        if slash != -1:
            tail.append(text[slash + 1 :])
            break
        tail.append(text)
    component = "".join(reversed(tail))
    return component if component.endswith(".env") else None


def _basename_from_expr(expr: ast.expr) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        base = expr.value.rsplit("/", 1)[-1]
        return base if base.endswith(".env") else None
    if isinstance(expr, ast.JoinedStr):
        return _fstring_basename(expr)
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
        return _basename_from_expr(expr.right)
    return None


def _literal_basename(node: ast.Call) -> str | None:
    for arg in _call_arg_values(node):
        basename = _basename_from_expr(arg)
        if basename is not None:
            return basename
    return None


def _keys_from_expr(expr: ast.expr) -> frozenset[str] | None:
    if not isinstance(expr, (ast.List, ast.Tuple)):
        return None
    keys: list[str] = []
    for elt in expr.elts:
        if not isinstance(elt, ast.Tuple) or len(elt.elts) != KV_TUPLE_LEN:
            return None
        first = elt.elts[0]
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            return None
        keys.append(first.value)
    return frozenset(keys)


def _literal_keys(node: ast.Call) -> frozenset[str] | None:
    for arg in _call_arg_values(node):
        keys = _keys_from_expr(arg)
        if keys is not None:
            return keys
    return None


def _has_pragma(line: str) -> bool:
    index = line.find(PRAGMA)
    return index != -1 and bool(line[index + len(PRAGMA) :].strip())


def _collect_file(*, rel: str, source: str) -> list[WriterCall]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines = source.splitlines()
    calls: list[WriterCall] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _callee_name(node)
        if name is None or not _is_writer_name(name):
            continue
        basename = _literal_basename(node)
        if basename is None:
            continue
        keys = _literal_keys(node)
        if keys is None:
            continue
        line_index = node.lineno - 1
        source_line = lines[line_index] if 0 <= line_index < len(lines) else ""
        calls.append(WriterCall(path=rel, line=node.lineno, basename=basename, keys=keys, suppressed=_has_pragma(source_line)))
    return calls


def collect_violations(root: Path) -> list[Violation]:
    """Return unsuppressed key-parity violations across sibling result-env writers."""
    writers: list[WriterCall] = []
    for path in _iter_python_files(root):
        writers.extend(_collect_file(rel=path.relative_to(root).as_posix(), source=_read_text(path)))
    by_basename: dict[str, list[WriterCall]] = {}
    for writer in writers:
        by_basename.setdefault(writer.basename, []).append(writer)
    violations: list[Violation] = []
    for basename, group in by_basename.items():
        if len(group) < MIN_SIBLING_WRITERS:
            continue
        union = frozenset[str]().union(*(writer.keys for writer in group))
        required = union - OPTIONAL_KEYS.get(basename, frozenset())
        for writer in group:
            if writer.suppressed:
                continue
            violations.extend(
                Violation(basename=basename, path=writer.path, line=writer.line, key=key)
                for key in sorted(required - writer.keys)
            )
    return sorted(violations, key=lambda violation: (violation.basename, violation.path, violation.line, violation.key))


def _message(violation: Violation) -> str:
    return (
        f"{violation.path}:{violation.line}: result-env-key-parity: "
        f"{violation.basename} writer missing key {violation.key} present in sibling writers"
    )


def serialize_baseline(rows: list[BaselineRow]) -> str:
    ordered = sorted(rows, key=lambda row: (row["basename"], row["path"], row["key"]))
    return json.dumps(ordered, indent=2) + "\n"


def _records_for_write(violations: list[Violation], *, baseline_rows: list[BaselineRow], initial_reason: str | None) -> list[BaselineRow]:
    preserved = {(row["basename"], row["path"], row["key"]): row for row in baseline_rows}
    default_reason = initial_reason.strip() if initial_reason is not None else None
    records: list[BaselineRow] = []
    missing: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for violation in violations:
        identity = violation.identity()
        if identity in seen:
            continue
        seen.add(identity)
        old = preserved.get(identity)
        if old is not None:
            records.append(old)
        elif default_reason:
            records.append({"basename": violation.basename, "path": violation.path, "key": violation.key, "reason": default_reason})
        else:
            missing.append(":".join(identity))
    if missing:
        raise BaselineError("missing baseline reasons for live result-env key-parity violations:\n  " + "\n  ".join(missing))
    return records


def _run_write(root: Path, *, baseline_path: Path, initial_reason: str | None) -> int:
    try:
        baseline_rows = load_baseline(baseline_path)
        violations = collect_violations(root)
        records = _records_for_write(violations, baseline_rows=baseline_rows, initial_reason=initial_reason)
    except BaselineError as exc:
        print(f"lint-result-env-key-parity: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(f"lint-result-env-key-parity: wrote {len(records)} records to {baseline_path}", file=sys.stderr)
    return 0


def _run_check(root: Path, *, baseline_path: Path) -> int:
    try:
        baseline_rows = load_baseline(baseline_path)
        violations = collect_violations(root)
    except BaselineError as exc:
        print(f"lint-result-env-key-parity: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baselined = {(row["basename"], row["path"], row["key"]) for row in baseline_rows}
    new = [violation for violation in violations if violation.identity() not in baselined]
    warned = [violation for violation in violations if violation.identity() in baselined]
    for violation in warned:
        print(f"warning: {_message(violation)} (baselined)", file=sys.stderr)
    for violation in new:
        print(_message(violation), file=sys.stderr)
    return 1 if new else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint result-env-key-parity", description=__doc__)
    _ = parser.add_argument("positional_root", nargs="?", help="Optional repository root.")
    _ = parser.add_argument("--root", help="Repository root (overrides positional root).")
    _ = parser.add_argument("--write", action="store_true", help=f"Regenerate {BASELINE_FILENAME} from live violations.")
    _ = parser.add_argument("--initial-reason", help="Reason used for new live violations during --write.")
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
    root_text = cast("str | None", parsed.root) or cast("str | None", parsed.positional_root)
    root = Path(root_text).resolve() if root_text else Path(__file__).resolve().parents[3]
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(f"lint-result-env-key-parity: python directory not found: {python_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_path = python_dir / BASELINE_FILENAME
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-result-env-key-parity: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(root, baseline_path=baseline_path, initial_reason=initial_reason)
    return _run_check(root, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
