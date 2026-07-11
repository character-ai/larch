"""Flag branch bodies proved impossible by earlier same-value returns.

This lint is intentionally narrower than pyright or pylint unreachable-code
analysis. It walks each function body in execution order, retains only path
conditions necessary to reach the next sequential statement, and flags a later
``if`` / ``elif`` branch body only when:

1. every path that can reach the condition contradicts that condition, and
2. the unreachable branch returns the same normalized value as the earlier
   return that established the contradiction.

A later ``if`` statement remains reachable for evaluation even when one of its
branch bodies is impossible; the finding names the impossible condition/body,
not the whole statement. Uncertain control flow discards tracked facts
(fail-safe: do not flag).

Existing debt is grandfathered in ``python/unreachable-branch-baseline.json``.
"""
# ruff: noqa: C901, PLR0912, PLR0913, SIM103 - path-sensitive AST walk complexity is inherent

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
BASELINE_FILENAME = "unreachable-branch-baseline.json"
SUPPRESSION = "lint-unreachable-branch"
PRAGMA_RE = re.compile(rf"#\s*{re.escape(SUPPRESSION)}:\s*ok\s+(\S.*)$")
EMPTY_PRAGMA_RE = re.compile(rf"#\s*{re.escape(SUPPRESSION)}:\s*ok\s*$")
BASELINE_KEYS = frozenset(
    {"file", "qualified_symbol", "occurrence", "normalized_condition", "reason"}
)
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
MODULE_SYMBOL = "<module>"


class Record(TypedDict):
    file: str
    qualified_symbol: str
    occurrence: int
    normalized_condition: str
    reason: str


class BaselineError(ValueError):
    """Raised when the baseline cannot be trusted."""


class ScanError(RuntimeError):
    """Raised when a source file cannot be read or parsed."""


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    occurrence: int
    lineno: int
    normalized_condition: str

    def key(self) -> tuple[str, str, int, str]:
        return (self.file, self.qualified_symbol, self.occurrence, self.normalized_condition)


def normalize_file_path(raw: str) -> str:
    """Return a normalized POSIX path relative to python/."""
    normalized = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.removeprefix("python/")


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


def normalize_expr(node: ast.AST | None) -> str:
    """Return a stable, whitespace-collapsed dump of an expression."""
    if node is None:
        return "<none>"
    try:
        return ast.dump(node, annotate_fields=False)
    except TypeError:
        return ast.dump(node)


def _negate_condition(cond: str) -> str:
    return f"NOT({cond})"


def _conditions_contradict(path_facts: frozenset[str], condition: str) -> bool:
    """Return True when path facts prove ``condition`` cannot hold."""
    if condition in path_facts:
        return False
    negated = _negate_condition(condition)
    if negated in path_facts:
        return True
    # Also: if path has ``cond`` and we check ``NOT(cond)``.
    if condition.startswith("NOT(") and condition.endswith(")"):
        inner = condition[4:-1]
        if inner in path_facts:
            return True
    return False


def _names_referenced(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _assignment_targets(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.Assign):
        for target in node.targets:
            names.update(_names_referenced(target))
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) and isinstance(node.target, ast.Name):
        names.add(node.target.id)
    return names


def _body_returns_value(body: list[ast.stmt]) -> str | None:
    """Return the value from a terminal direct return after preparation statements."""
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Return):
            return normalize_expr(stmt.value)
    return None


def _body_always_returns(body: list[ast.stmt]) -> bool:
    for stmt in body:
        if isinstance(stmt, ast.Return):
            return True
        if isinstance(stmt, ast.Raise):
            return True
        if isinstance(stmt, ast.If):
            if _body_always_returns(stmt.body) and _body_always_returns(stmt.orelse):
                return True
            return False
        if isinstance(stmt, (ast.For, ast.While, ast.Try, ast.With, ast.AsyncWith)):
            return False
    return False


@dataclass
class _PathState:
    facts: frozenset[str]
    return_proofs: frozenset[tuple[str, str]] = frozenset()
    uncertain: bool = False

    def clear(self) -> _PathState:
        return _PathState(facts=frozenset(), return_proofs=frozenset(), uncertain=True)

    def with_fact(self, fact: str) -> _PathState:
        if self.uncertain:
            return self
        return _PathState(
            facts=self.facts | {fact},
            return_proofs=self.return_proofs,
            uncertain=False,
        )

    def with_return_proof(self, *, cond: str, returned: str) -> _PathState:
        if self.uncertain:
            return self
        return _PathState(
            facts=self.facts | {_negate_condition(cond)},
            return_proofs=self.return_proofs | {(cond, returned)},
            uncertain=False,
        )

    def drop_names(self, names: set[str]) -> _PathState:
        if not names or self.uncertain:
            return self

        def mentions(fact: str) -> bool:
            return any(f"'{name}'" in fact or f'"{name}"' in fact for name in names)

        kept_facts = frozenset(fact for fact in self.facts if not mentions(fact))
        kept_proofs = frozenset(
            (cond, returned)
            for cond, returned in self.return_proofs
            if not mentions(cond) and not mentions(returned)
        )
        return _PathState(facts=kept_facts, return_proofs=kept_proofs, uncertain=False)


def _scan_block(
    body: list[ast.stmt],
    *,
    state: _PathState,
    symbol: str,
    normalized_file: str,
    comments_by_line: Mapping[int, tuple[str, ...]],
    findings: list[Finding],
    occurrence_counter: list[int],
) -> _PathState:
    current = state
    for index, stmt in enumerate(body):
        if current.uncertain:
            # Still walk nested defs, but do not flag.
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _scan_function(
                    stmt,
                    prefix=tuple(symbol.split(".")) if symbol != MODULE_SYMBOL else (),
                    normalized_file=normalized_file,
                    comments_by_line=comments_by_line,
                    findings=findings,
                )
            continue

        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _scan_function(
                stmt,
                prefix=tuple(symbol.split(".")) if symbol != MODULE_SYMBOL else (),
                normalized_file=normalized_file,
                comments_by_line=comments_by_line,
                findings=findings,
            )
            continue

        if isinstance(stmt, ast.ClassDef):
            for item in stmt.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nested_prefix = (
                        (*symbol.split("."), stmt.name)
                        if symbol != MODULE_SYMBOL
                        else (stmt.name,)
                    )
                    _scan_function(
                        item,
                        prefix=nested_prefix,
                        normalized_file=normalized_file,
                        comments_by_line=comments_by_line,
                        findings=findings,
                    )
            current = current.clear()
            continue

        if isinstance(stmt, ast.Return):
            # Unconditional return: remaining statements in this block are
            # unreachable. Scan them for duplicate return branches before
            # reporting that this path cannot fall through.
            _scan_unreachable_tail(
                body[index + 1 :],
                returned=normalize_expr(stmt.value),
                symbol=symbol,
                normalized_file=normalized_file,
                comments_by_line=comments_by_line,
                findings=findings,
                occurrence_counter=occurrence_counter,
            )
            return current.clear()

        if isinstance(stmt, (ast.Raise, ast.Break, ast.Continue)):
            return current.clear()

        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            names = _assignment_targets(stmt)
            current = current.drop_names(names)
            continue

        if isinstance(stmt, (ast.For, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.AsyncFor)):
            # Uncertain control flow: discard facts, still scan nested functions.
            _scan_nested_defs(
                stmt,
                symbol=symbol,
                normalized_file=normalized_file,
                comments_by_line=comments_by_line,
                findings=findings,
            )
            current = current.clear()
            continue

        if isinstance(stmt, ast.If):
            current = _scan_if(
                stmt,
                state=current,
                symbol=symbol,
                normalized_file=normalized_file,
                comments_by_line=comments_by_line,
                findings=findings,
                occurrence_counter=occurrence_counter,
            )
            continue

        # Other statements (Expr, Pass, ...): check NamedExpr assignments.
        for child in ast.walk(stmt):
            if isinstance(child, ast.NamedExpr):
                current = current.drop_names(_assignment_targets(child))
    return current


def _scan_nested_defs(
    node: ast.AST,
    *,
    symbol: str,
    normalized_file: str,
    comments_by_line: Mapping[int, tuple[str, ...]],
    findings: list[Finding],
) -> None:
    parent_prefix = tuple(symbol.split(".")) if symbol != MODULE_SYMBOL else ()

    def visit(current: ast.AST) -> None:
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _scan_function(
                    child,
                    prefix=parent_prefix,
                    normalized_file=normalized_file,
                    comments_by_line=comments_by_line,
                    findings=findings,
                )
                continue
            visit(child)

    visit(node)


def _scan_unreachable_tail(
    body: list[ast.stmt],
    *,
    returned: str,
    symbol: str,
    normalized_file: str,
    comments_by_line: Mapping[int, tuple[str, ...]],
    findings: list[Finding],
    occurrence_counter: list[int],
) -> None:
    """Record unreachable conditional branches that repeat a terminal return."""
    for stmt in body:
        if isinstance(stmt, ast.If):
            cursor = stmt
            while True:
                candidate = _body_returns_value(cursor.body)
                if candidate == returned:
                    lineno = getattr(cursor, "lineno", 0)
                    reason = _suppression_reason(
                        lineno if isinstance(lineno, int) else 0,
                        comments_by_line=comments_by_line,
                    )
                    if reason == "":
                        raise ScanError(
                            f"{normalized_file}:{lineno}: empty {SUPPRESSION} suppression reason"
                        )
                    if reason is None:
                        occurrence_counter[0] += 1
                        findings.append(
                            Finding(
                                file=normalized_file,
                                qualified_symbol=symbol,
                                occurrence=occurrence_counter[0],
                                lineno=lineno if isinstance(lineno, int) else 0,
                                normalized_condition=normalize_expr(cursor.test),
                            )
                        )
                if len(cursor.orelse) != 1 or not isinstance(cursor.orelse[0], ast.If):
                    break
                cursor = cursor.orelse[0]


def _scan_if(
    stmt: ast.If,
    *,
    state: _PathState,
    symbol: str,
    normalized_file: str,
    comments_by_line: Mapping[int, tuple[str, ...]],
    findings: list[Finding],
    occurrence_counter: list[int],
) -> _PathState:
    """Scan an if/elif chain; return fallthrough path state."""
    current = state
    # Collect chain arms: (test_node|None for else, body).
    arms: list[tuple[ast.AST | None, list[ast.stmt], int]] = []
    cursor: ast.stmt = stmt
    while True:
        lineno = getattr(cursor, "lineno", 0)
        arms.append((cursor.test, cursor.body, lineno if isinstance(lineno, int) else 0))
        if len(cursor.orelse) == 1 and isinstance(cursor.orelse[0], ast.If):
            cursor = cursor.orelse[0]
            continue
        if cursor.orelse:
            arms.append((None, cursor.orelse, 0))
        break

    # Prior returns that establish contradictions for later arms.
    # Each entry: (condition_normalized, return_value_normalized).
    fallthrough = current
    established: list[tuple[str, str]] = list(fallthrough.return_proofs)

    for test, body, lineno in arms:
        if test is None:
            # else branch
            _ = _scan_block(
                body,
                state=fallthrough,
                symbol=symbol,
                normalized_file=normalized_file,
                comments_by_line=comments_by_line,
                findings=findings,
                occurrence_counter=occurrence_counter,
            )
            # else that always returns: no fallthrough.
            if _body_always_returns(body):
                return fallthrough.clear()
            fallthrough = fallthrough.clear()
            continue

        cond = normalize_expr(test)
        # Flag when path facts contradict this condition AND body returns same value.
        if not fallthrough.uncertain and _conditions_contradict(fallthrough.facts, cond):
            returned = _body_returns_value(body)
            matching_prior = next(
                (
                    prior_ret
                    for prior_cond, prior_ret in established
                    if prior_cond == cond and prior_ret == returned and returned is not None
                ),
                None,
            )
            if returned is not None and matching_prior is not None:
                reason = _suppression_reason(lineno, comments_by_line=comments_by_line)
                if reason == "":
                    raise ScanError(
                        f"{normalized_file}:{lineno}: empty {SUPPRESSION} suppression reason"
                    )
                if reason is None:
                    occurrence_counter[0] += 1
                    findings.append(
                        Finding(
                            file=normalized_file,
                            qualified_symbol=symbol,
                            occurrence=occurrence_counter[0],
                            lineno=lineno,
                            normalized_condition=cond,
                        )
                    )

        # Scan body under condition fact.
        body_state = fallthrough.with_fact(cond) if not fallthrough.uncertain else fallthrough
        _ = _scan_block(
            body,
            state=body_state,
            symbol=symbol,
            normalized_file=normalized_file,
            comments_by_line=comments_by_line,
            findings=findings,
            occurrence_counter=occurrence_counter,
        )

        returned = _body_returns_value(body)
        if returned is not None and _body_always_returns(body):
            established.append((cond, returned))
            fallthrough = fallthrough.with_return_proof(cond=cond, returned=returned)
        elif _body_always_returns(body):
            fallthrough = fallthrough.with_fact(_negate_condition(cond))
        else:
            # Body may fall through: facts after the if are uncertain for this arm.
            fallthrough = fallthrough.clear()
            break

    return fallthrough


def _scan_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    prefix: tuple[str, ...],
    normalized_file: str,
    comments_by_line: Mapping[int, tuple[str, ...]],
    findings: list[Finding],
) -> None:
    symbol = _qualified((*prefix, node.name))
    occurrence_counter = [0]
    # Per-function occurrence should count findings in this function only for
    # baseline identity; use a local counter then rewrite occurrence as
    # order-within-function.
    local_findings: list[Finding] = []
    _ = _scan_block(
        node.body,
        state=_PathState(facts=frozenset()),
        symbol=symbol,
        normalized_file=normalized_file,
        comments_by_line=comments_by_line,
        findings=local_findings,
        occurrence_counter=occurrence_counter,
    )
    for index, finding in enumerate(local_findings, start=1):
        findings.append(
            Finding(
                file=finding.file,
                qualified_symbol=finding.qualified_symbol,
                occurrence=index,
                lineno=finding.lineno,
                normalized_condition=finding.normalized_condition,
            )
        )


def scan_file(path: Path, *, larch_dir: Path) -> list[Finding]:
    """Return unreachable-branch findings for one source file."""
    normalized_file = path.relative_to(larch_dir.parent).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ScanError(f"{normalized_file}: cannot read source: {exc}") from exc
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ScanError(f"{normalized_file}: cannot parse source: {exc}") from exc
    comments_by_line = _comment_tokens_by_line(source)
    findings: list[Finding] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _scan_function(
                node,
                prefix=(),
                normalized_file=normalized_file,
                comments_by_line=comments_by_line,
                findings=findings,
            )
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _scan_function(
                        item,
                        prefix=(node.name,),
                        normalized_file=normalized_file,
                        comments_by_line=comments_by_line,
                        findings=findings,
                    )
    return findings


def _collect_all(larch_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_source_files(larch_dir):
        findings.extend(scan_file(path, larch_dir=larch_dir))
    return findings


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


def _record_key(record: Record) -> tuple[str, str, int, str]:
    return (
        record["file"],
        record["qualified_symbol"],
        record["occurrence"],
        record["normalized_condition"],
    )


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name = _validate_normalized_file(record["file"], source=source, index=index)
    qualified_symbol = record["qualified_symbol"]
    occurrence = record["occurrence"]
    normalized_condition = record["normalized_condition"]
    reason = record["reason"]
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(normalized_condition, str) or not normalized_condition:
        raise BaselineError(f"{source}: record {index} has invalid normalized_condition")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "qualified_symbol": qualified_symbol,
        "occurrence": occurrence,
        "normalized_condition": normalized_condition,
        "reason": reason,
    }


def _first_duplicate(
    keys: Iterable[tuple[str, str, int, str]],
) -> tuple[str, str, int, str] | None:
    seen: set[tuple[str, str, int, str]] = set()
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


def format_key(key: tuple[str, str, int, str]) -> str:
    file_name, qualified_symbol, occurrence, normalized_condition = key
    return f"{file_name}:{qualified_symbol}#{occurrence} cond={normalized_condition}"


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
    preserved: dict[tuple[str, str, int, str], str] = {}
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
                "occurrence": finding.occurrence,
                "normalized_condition": finding.normalized_condition,
                "reason": reason,
            }
        )
    if missing:
        joined = "\n  ".join(missing)
        raise BaselineError("missing baseline reasons for live unreachable-branch findings:\n  " + joined)
    return records


def _run_write(
    larch_dir: Path,
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> int:
    try:
        findings = _collect_all(larch_dir)
        duplicate = _first_duplicate(finding.key() for finding in findings)
        if duplicate is not None:
            raise BaselineError(f"duplicate live identity {format_key(duplicate)}")
        records = _records_for_write(
            findings,
            baseline_path=baseline_path,
            initial_reason=initial_reason,
        )
    except (BaselineError, ScanError) as exc:
        print(f"lint-unreachable-branch: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(f"lint-unreachable-branch: wrote {len(records)} records to {baseline_path}", file=sys.stderr)
    return 0


def _run_check(larch_dir: Path, *, baseline_path: Path) -> int:
    try:
        if not baseline_path.is_file():
            raise BaselineError(f"required baseline missing: {baseline_path}")
        baseline_records = load_baseline(baseline_path)
        findings = _collect_all(larch_dir)
        duplicate = _first_duplicate(finding.key() for finding in findings)
        if duplicate is not None:
            raise BaselineError(f"duplicate live identity {format_key(duplicate)}")
    except (BaselineError, ScanError) as exc:
        print(f"lint-unreachable-branch: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys = frozenset(_record_key(record) for record in baseline_records)
    live_keys = frozenset(finding.key() for finding in findings)
    new_findings = [finding for finding in findings if finding.key() not in baseline_keys]
    stale = sorted(baseline_keys - live_keys)
    for finding in sorted(findings, key=lambda item: item.key()):
        if finding.key() in baseline_keys:
            print(
                "warning: "
                f"{finding.file}:{finding.qualified_symbol} unreachable branch "
                f"occurrence {finding.occurrence} line {finding.lineno} (baselined)",
                file=sys.stderr,
            )
    for finding in sorted(new_findings, key=lambda item: item.key()):
        print(
            f"{finding.file}:{finding.qualified_symbol} unreachable branch "
            f"occurrence {finding.occurrence} line {finding.lineno} "
            f"cond={finding.normalized_condition}",
            file=sys.stderr,
        )
    for key in stale:
        print(f"lint-unreachable-branch: stale baseline row {format_key(key)}", file=sys.stderr)
    if stale:
        return TOOL_FAILURE_EXIT
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint unreachable-branch", description=__doc__)
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
        print(f"lint-unreachable-branch: larch directory not found: {larch_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_path = root / "python" / BASELINE_FILENAME
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-unreachable-branch: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(larch_dir, baseline_path=baseline_path, initial_reason=initial_reason)
    return _run_check(larch_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
