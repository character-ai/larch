"""Flag Markdown heading regexes applied to splitlines without fence state.

Scans production modules under ``python/**/*.py`` for ``re.compile`` patterns
that match Markdown headings (``^#{1,6}``) and are applied via ``.match`` /
``.search`` to lines derived from ``.splitlines()``. A module is compliant when
it defines or imports a fence-line-index helper and the heading-match path
consults the resulting fenced-line set. Mechanically backs G-Md-3 / #6676.

Existing debt is grandfathered in ``python/markdown-heading-fence-state-baseline.json``.
"""
# ruff: noqa: C901, PLR0912, SIM102 - AST walker complexity is inherent to the scan

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import tokenize
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "markdown-heading-fence-state-baseline.json"
SUPPRESSION = "lint-markdown-heading-fence-state"
PRAGMA_RE = re.compile(rf"#\s*{re.escape(SUPPRESSION)}:\s*ok\s+(\S.*)$")
EMPTY_PRAGMA_RE = re.compile(rf"#\s*{re.escape(SUPPRESSION)}:\s*ok\s*$")
BASELINE_KEYS = frozenset({"file", "qualified_symbol", "pattern_name", "occurrence", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
MODULE_SYMBOL = "<module>"
# Heading patterns: start-anchored one-to-six hashes, optionally followed by
# whitespace or a character class that includes whitespace.
HEADING_PATTERN_RE = re.compile(
    r"(?:\^|\\A)\s*#\{1,6\}|"
    r"(?:\^|\\A)\s*#{1,6}(?:\\s|\[\\s|\[ \t)|"
    r"(?:\^|\\A)\s*#{1,6}[ \t]"
)
FENCE_HELPER_NAME_RE = re.compile(r"fence", re.IGNORECASE)
KNOWN_FENCE_HELPERS = frozenset({"_balanced_fence_line_indices"})


class Record(TypedDict):
    file: str
    qualified_symbol: str
    pattern_name: str
    occurrence: int
    reason: str


class BaselineError(ValueError):
    """Raised when the baseline cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    occurrence: int
    lineno: int
    pattern_name: str

    def key(self) -> tuple[str, str, str, int]:
        return (self.file, self.qualified_symbol, self.pattern_name, self.occurrence)


class ScanError(RuntimeError):
    """Raised when a source file cannot be read or parsed."""


def is_exempt_path(path: Path) -> bool:
    """Return whether a source file is outside production lint scope."""
    name = path.name
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def iter_source_files(python_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under python/, sorted."""
    result: list[Path] = []
    for path in sorted(python_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink() or is_exempt_path(path):
            continue
        relative = path.relative_to(python_dir)
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        result.append(path)
    return result


def _qualified(prefix: tuple[str, ...]) -> str:
    return ".".join(prefix) if prefix else MODULE_SYMBOL


def _comment_tokens_by_line(source: str) -> dict[int, tuple[str, ...]]:
    comments: dict[int, list[str]] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.setdefault(token.start[0], []).append(token.string)
    except tokenize.TokenError:
        return {}
    return {line: tuple(values) for line, values in comments.items()}


def _suppression_reason(
    lineno: int, *, comments_by_line: Mapping[int, tuple[str, ...]]
) -> str | None:
    for comment in comments_by_line.get(lineno, ()):
        match = PRAGMA_RE.search(comment)
        if match is not None:
            return match.group(1).strip()
        if EMPTY_PRAGMA_RE.search(comment) is not None:
            return ""
    return None


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return "".join(parts)
    return None


def _is_heading_pattern(pattern: str) -> bool:
    return HEADING_PATTERN_RE.search(pattern) is not None


def _re_compile_call(node: ast.AST) -> ast.Call | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "compile":
        if isinstance(func.value, ast.Name) and func.value.id == "re":
            return node
    if isinstance(func, ast.Name) and func.id == "compile":
        return node
    return None


def _pattern_arg(call: ast.Call) -> str | None:
    if not call.args:
        return None
    return _literal_string(call.args[0])


def _is_splitlines_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "splitlines"
    )


def _name_of(node: ast.AST) -> str | None:
    return node.id if isinstance(node, ast.Name) else None


def _verified_fence_helper(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a local helper visibly constructs fence-line indices."""
    if node.name not in KNOWN_FENCE_HELPERS and FENCE_HELPER_NAME_RE.search(node.name) is None:
        return False
    has_set = any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Name)
        and child.func.id in {"set", "range"}
        for child in ast.walk(node)
    )
    return any(isinstance(child, ast.Return) for child in ast.walk(node)) and (
        node.name in KNOWN_FENCE_HELPERS or has_set
    )


def _collect_fence_helpers(tree: ast.AST) -> set[str]:
    helpers: set[str] = set()
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _verified_fence_helper(node):
                helpers.add(node.name)
        elif isinstance(node, (ast.ImportFrom,)):
            for alias in node.names:
                name = alias.asname or alias.name
                if alias.name in KNOWN_FENCE_HELPERS:
                    helpers.add(name)
    return helpers


@dataclass
class _ScopeState:
    heading_regexes: dict[str, int]  # name -> declaration lineno
    split_vars: set[str]
    fence_sets: set[str]
    fence_helpers: set[str]
    fence_guard_names: set[str]
    findings: list[Finding]
    occurrence: int
    symbol: str
    normalized_file: str
    comments_by_line: Mapping[int, tuple[str, ...]]


def _record_heading_regex(state: _ScopeState, *, name: str, lineno: int) -> None:
    reason = _suppression_reason(lineno, comments_by_line=state.comments_by_line)
    if reason is not None:
        if reason == "":
            state.findings.append(
                Finding(
                    file=state.normalized_file,
                    qualified_symbol=state.symbol,
                    occurrence=0,
                    lineno=lineno,
                    pattern_name=f"{name} (empty suppression)",
                )
            )
        return
    state.heading_regexes[name] = lineno


def _track_assignment(state: _ScopeState, node: ast.Assign, *, loop_targets: set[str]) -> None:
    if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return
    name = node.targets[0].id
    compile_call = _re_compile_call(node.value)
    if compile_call is not None:
        pattern = _pattern_arg(compile_call)
        if pattern is not None and _is_heading_pattern(pattern):
            lineno = getattr(compile_call, "lineno", getattr(node, "lineno", 0))
            _record_heading_regex(state, name=name, lineno=lineno if isinstance(lineno, int) else 0)
            return
    if _is_splitlines_call(node.value):
        state.split_vars.add(name)
        return
    if isinstance(node.value, ast.Call):
        func = node.value.func
        callee = _name_of(func) if not isinstance(func, ast.Attribute) else None
        if callee in state.fence_helpers:
            state.fence_sets.add(name)
            return
    if loop_targets and _uses_fence_guard(
        node.value,
        fence_sets=state.fence_sets,
        fence_helpers=state.fence_helpers,
        line_names=loop_targets,
    ):
        state.fence_guard_names.add(name)


def _is_fence_source(node: ast.AST, *, fence_sets: set[str], fence_helpers: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in fence_sets
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in fence_helpers
    )


def _uses_fence_guard(
    test: ast.AST,
    *,
    fence_sets: set[str],
    fence_helpers: set[str],
    line_names: set[str],
) -> bool:
    """Return True when ``test`` checks a line/index against a fence source."""
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return _uses_fence_guard(
            test.operand,
            fence_sets=fence_sets,
            fence_helpers=fence_helpers,
            line_names=line_names,
        )
    if isinstance(test, ast.Compare):
        left = test.left
        for operator, comparator in zip(test.ops, test.comparators, strict=True):
            if (
                isinstance(operator, (ast.In, ast.NotIn))
                and (_name_of(left) in line_names or _name_of(comparator) in line_names)
                and (
                    _is_fence_source(left, fence_sets=fence_sets, fence_helpers=fence_helpers)
                    or _is_fence_source(comparator, fence_sets=fence_sets, fence_helpers=fence_helpers)
                )
            ):
                return True
            left = comparator
    if isinstance(test, ast.BoolOp):
        return any(
            _uses_fence_guard(
                value,
                fence_sets=fence_sets,
                fence_helpers=fence_helpers,
                line_names=line_names,
            )
            for value in test.values
        )
    return False


def _skips_fenced_lines(
    test: ast.AST, *, fence_sets: set[str], fence_helpers: set[str], line_names: set[str]
) -> bool:
    """Return True for a positive fence-membership test used to skip a loop turn."""
    if not isinstance(test, ast.Compare):
        return False
    left = test.left
    for operator, comparator in zip(test.ops, test.comparators, strict=True):
        if (
            isinstance(operator, ast.In)
            and _name_of(left) in line_names
            and _is_fence_source(comparator, fence_sets=fence_sets, fence_helpers=fence_helpers)
        ):
            return True
        left = comparator
    return False


def _uses_fence_guard_name(test: ast.AST, *, guard_names: set[str]) -> bool:
    if isinstance(test, ast.Name):
        return test.id in guard_names
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return _uses_fence_guard_name(test.operand, guard_names=guard_names)
    if isinstance(test, ast.BoolOp):
        return any(_uses_fence_guard_name(value, guard_names=guard_names) for value in test.values)
    return False


def _match_target_is_split_line(arg: ast.AST, *, split_vars: set[str], loop_targets: set[str]) -> bool:
    name = _name_of(arg)
    if name is not None:
        return name in loop_targets or name in split_vars
    return (
        isinstance(arg, ast.Subscript)
        and isinstance(arg.value, ast.Name)
        and arg.value.id in split_vars
        and isinstance(arg.slice, ast.Name)
        and arg.slice.id in loop_targets
    )


def _iterates_split_lines(node: ast.AST, *, split_vars: set[str]) -> bool:
    if _is_splitlines_call(node):
        return True
    if isinstance(node, ast.Name):
        return node.id in split_vars
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "enumerate"
        and bool(node.args)
        and _iterates_split_lines(node.args[0], split_vars=split_vars)
    )


def _walk_statements(
    body: list[ast.stmt],
    *,
    state: _ScopeState,
    loop_targets: set[str],
    fence_guard_active: bool,
) -> None:
    active_guard = fence_guard_active
    for statement in body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            child = _ScopeState(
                heading_regexes=dict(state.heading_regexes),
                split_vars=set(state.split_vars),
            fence_sets=set(),
            fence_helpers=set(state.fence_helpers),
                fence_guard_names=set(state.fence_guard_names),
                findings=state.findings,
                occurrence=0,
                symbol=_qualified((*state.symbol.split("."), statement.name))
                if state.symbol != MODULE_SYMBOL
                else statement.name,
                normalized_file=state.normalized_file,
                comments_by_line=state.comments_by_line,
            )
            if state.symbol == MODULE_SYMBOL:
                child.symbol = statement.name
            else:
                child.symbol = f"{state.symbol}.{statement.name}"
            if FENCE_HELPER_NAME_RE.search(statement.name):
                child.fence_helpers = set(state.fence_helpers) | {statement.name}
            _walk_statements(
                statement.body,
                state=child,
                loop_targets=set(),
                fence_guard_active=False,
            )
            continue
        if isinstance(statement, ast.ClassDef):
            child = _ScopeState(
                heading_regexes=dict(state.heading_regexes),
                split_vars=set(state.split_vars),
                fence_sets=set(),
                fence_helpers=set(state.fence_helpers),
                fence_guard_names=set(state.fence_guard_names),
                findings=state.findings,
                occurrence=0,
                symbol=f"{state.symbol}.{statement.name}"
                if state.symbol != MODULE_SYMBOL
                else statement.name,
                normalized_file=state.normalized_file,
                comments_by_line=state.comments_by_line,
            )
            _walk_statements(
                statement.body,
                state=child,
                loop_targets=set(),
                fence_guard_active=False,
            )
            continue
        if isinstance(statement, ast.Assign):
            _track_assignment(state, statement, loop_targets=loop_targets)
        if isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                if alias.name in KNOWN_FENCE_HELPERS:
                    state.fence_helpers.add(alias.asname or alias.name)
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            if statement.value is not None:
                fake = ast.Assign(targets=[statement.target], value=statement.value)
                _track_assignment(state, fake, loop_targets=loop_targets)
        if isinstance(statement, ast.For):
            new_targets = set(loop_targets)
            if isinstance(statement.target, ast.Name):
                new_targets.add(statement.target.id)
            elif isinstance(statement.target, ast.Tuple):
                for elt in statement.target.elts:
                    if isinstance(elt, ast.Name):
                        new_targets.add(elt.id)
            iter_is_split = _iterates_split_lines(statement.iter, split_vars=state.split_vars)
            child_targets = new_targets if iter_is_split else loop_targets
            previous_guard_names = set(state.fence_guard_names)
            _walk_statements(
                statement.body,
                state=state,
                loop_targets=child_targets,
                fence_guard_active=fence_guard_active,
            )
            state.fence_guard_names = previous_guard_names
            _walk_statements(
                statement.orelse,
                state=state,
                loop_targets=loop_targets,
                fence_guard_active=fence_guard_active,
            )
            continue
        if isinstance(statement, ast.If):
            guard = active_guard or _uses_fence_guard(
                statement.test,
                fence_sets=state.fence_sets,
                fence_helpers=state.fence_helpers,
                line_names=loop_targets,
            )
            guard = guard or _uses_fence_guard_name(
                statement.test, guard_names=state.fence_guard_names
            )
            # ``if not in_fence and ...`` keeps the body guarded.
            _walk_statements(
                statement.body,
                state=state,
                loop_targets=loop_targets,
                fence_guard_active=guard,
            )
            _walk_statements(
                statement.orelse,
                state=state,
                loop_targets=loop_targets,
                fence_guard_active=active_guard,
            )
            # Also scan the test expression for heading matches.
            _scan_expr(
                statement.test,
                state=state,
                loop_targets=loop_targets,
                fence_guard_active=guard,
            )
            if loop_targets and _skips_fenced_lines(
                statement.test,
                fence_sets=state.fence_sets,
                fence_helpers=state.fence_helpers,
                line_names=loop_targets,
            ) and any(isinstance(item, (ast.Break, ast.Continue)) for item in statement.body):
                active_guard = True
            continue
        _scan_stmt_exprs(
            statement,
            state=state,
            loop_targets=loop_targets,
            fence_guard_active=active_guard,
        )


def _scan_stmt_exprs(
    statement: ast.stmt,
    *,
    state: _ScopeState,
    loop_targets: set[str],
    fence_guard_active: bool,
) -> None:
    for child in ast.walk(statement):
        if child is statement:
            continue
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.For, ast.If)):
            # Nested control flow is handled by _walk_statements recursion.
            continue
        _scan_expr(
            child,
            state=state,
            loop_targets=loop_targets,
            fence_guard_active=fence_guard_active,
        )


def _scan_expr(
    node: ast.AST,
    *,
    state: _ScopeState,
    loop_targets: set[str],
    fence_guard_active: bool,
) -> None:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"match", "search"}:
            regex_name = _name_of(func.value)
            if (
                regex_name is not None
                and regex_name in state.heading_regexes
                and node.args
                and _match_target_is_split_line(
                    node.args[0], split_vars=state.split_vars, loop_targets=loop_targets
                )
            ):
                if not (
                    fence_guard_active and (state.fence_sets or state.fence_helpers)
                ):
                    state.occurrence += 1
                    lineno = getattr(node, "lineno", 0)
                    state.findings.append(
                        Finding(
                            file=state.normalized_file,
                            qualified_symbol=state.symbol,
                            occurrence=state.occurrence,
                            lineno=lineno if isinstance(lineno, int) else 0,
                            pattern_name=regex_name,
                        )
                    )
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        _scan_expr(
            child,
            state=state,
            loop_targets=loop_targets,
            fence_guard_active=fence_guard_active,
        )


def scan_file(path: Path, *, python_dir: Path) -> list[Finding]:
    """Return heading-regex-without-fence findings for one source file."""
    normalized_file = path.relative_to(python_dir).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ScanError(f"{normalized_file}: cannot read source: {exc}") from exc
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ScanError(f"{normalized_file}: cannot parse source: {exc}") from exc
    comments_by_line = _comment_tokens_by_line(source)
    fence_helpers = _collect_fence_helpers(tree)
    state = _ScopeState(
        heading_regexes={},
        split_vars=set(),
        fence_sets=set(),
        fence_helpers=fence_helpers,
        fence_guard_names=set(),
        findings=[],
        occurrence=0,
        symbol=MODULE_SYMBOL,
        normalized_file=normalized_file,
        comments_by_line=comments_by_line,
    )
    # First pass: module-level heading regex declarations.
    for node in tree.body:
        if isinstance(node, ast.Assign):
            _track_assignment(state, node, loop_targets=set())
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            fake = ast.Assign(targets=[node.target], value=node.value)
            _track_assignment(state, fake, loop_targets=set())
    _walk_statements(tree.body, state=state, loop_targets=set(), fence_guard_active=False)
    # Drop empty-suppression pseudo-findings that used occurrence 0; re-emit as tool failures.
    real: list[Finding] = []
    for finding in state.findings:
        if finding.occurrence == 0 and finding.pattern_name.endswith("(empty suppression)"):
            raise ScanError(
                f"{finding.file}:{finding.lineno}: empty {SUPPRESSION} suppression reason"
            )
        real.append(finding)
    return real


def _collect_all(python_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_source_files(python_dir):
        findings.extend(scan_file(path, python_dir=python_dir))
    return findings


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
        or not normalized.endswith(".py")
        or "" in parts
        or "." in parts
        or ".." in parts
    ):
        raise BaselineError(f"{source}: record {index} has invalid file")
    return normalized


def _record_key(record: Record) -> tuple[str, str, str, int]:
    return (
        record["file"],
        record["qualified_symbol"],
        record["pattern_name"],
        record["occurrence"],
    )


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name = _validate_normalized_file(record["file"], source=source, index=index)
    qualified_symbol = record["qualified_symbol"]
    pattern_name = record["pattern_name"]
    occurrence = record["occurrence"]
    reason = record["reason"]
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(pattern_name, str) or not pattern_name:
        raise BaselineError(f"{source}: record {index} has invalid pattern_name")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "qualified_symbol": qualified_symbol,
        "pattern_name": pattern_name,
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


def format_key(key: tuple[str, str, str, int]) -> str:
    file_name, qualified_symbol, pattern_name, occurrence = key
    return f"{file_name}:{qualified_symbol} {pattern_name}#{occurrence}"


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
    for finding in sorted(findings, key=lambda item: item.key()):
        reason = preserved.get(finding.key()) or reason_default
        if reason is None:
            missing.append(format_key(finding.key()))
            continue
        records.append(
            {
                "file": finding.file,
                "qualified_symbol": finding.qualified_symbol,
                "pattern_name": finding.pattern_name,
                "occurrence": finding.occurrence,
                "reason": reason,
            }
        )
    if missing:
        joined = "\n  ".join(missing)
        raise BaselineError(
            "missing baseline reasons for live markdown-heading-fence-state findings:\n  " + joined
        )
    return records


def _run_write(
    python_dir: Path,
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> int:
    try:
        findings = _collect_all(python_dir)
        duplicate = _first_duplicate(finding.key() for finding in findings)
        if duplicate is not None:
            raise BaselineError(f"duplicate live identity {format_key(duplicate)}")
        records = _records_for_write(
            findings,
            baseline_path=baseline_path,
            initial_reason=initial_reason,
        )
    except (BaselineError, ScanError) as exc:
        print(f"lint-markdown-heading-fence-state: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(
        f"lint-markdown-heading-fence-state: wrote {len(records)} records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check(python_dir: Path, *, baseline_path: Path) -> int:
    try:
        findings = _collect_all(python_dir)
        duplicate = _first_duplicate(finding.key() for finding in findings)
        if duplicate is not None:
            raise BaselineError(f"duplicate live identity {format_key(duplicate)}")
        if not findings:
            if baseline_path.is_file():
                raise BaselineError(f"stale baseline present with zero live findings: {baseline_path}")
            return 0
        if not baseline_path.is_file():
            raise BaselineError(f"required baseline missing: {baseline_path}")
        baseline_records = load_baseline(baseline_path)
    except (BaselineError, ScanError) as exc:
        print(f"lint-markdown-heading-fence-state: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys = frozenset(_record_key(record) for record in baseline_records)
    live_keys = frozenset(finding.key() for finding in findings)
    new_findings = [finding for finding in findings if finding.key() not in baseline_keys]
    stale = sorted(baseline_keys - live_keys)
    for finding in sorted(findings, key=lambda item: item.key()):
        if finding.key() in baseline_keys:
            print(
                "warning: "
                f"{finding.file}:{finding.qualified_symbol} applies heading regex "
                f"{finding.pattern_name} occurrence {finding.occurrence} "
                f"line {finding.lineno} (baselined)",
                file=sys.stderr,
            )
    for finding in sorted(new_findings, key=lambda item: item.key()):
        print(
            f"{finding.file}:{finding.qualified_symbol} applies heading regex "
            f"{finding.pattern_name} to splitlines without fence-state gating "
            f"(occurrence {finding.occurrence} line {finding.lineno})",
            file=sys.stderr,
        )
    for key in stale:
        print(
            f"lint-markdown-heading-fence-state: stale baseline row {format_key(key)}",
            file=sys.stderr,
        )
    if stale:
        return TOOL_FAILURE_EXIT
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint markdown-heading-fence-state", description=__doc__
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
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = Path(str(parsed.root)).resolve()
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(
            f"lint-markdown-heading-fence-state: python directory not found: {python_dir}",
            file=sys.stderr,
        )
        return TOOL_FAILURE_EXIT
    baseline_path = root / "python" / BASELINE_FILENAME
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print(
            "lint-markdown-heading-fence-state: --initial-reason must be non-empty",
            file=sys.stderr,
        )
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(python_dir, baseline_path=baseline_path, initial_reason=initial_reason)
    return _run_check(python_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
