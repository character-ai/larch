"""Flag truthiness tests of status-like values with same-scope semantic members.

Mechanically backs G-Py-15 (#6153, #7216): never decide terminality from
truthiness when the same function proves the value has explicit members.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Iterator

from larch.core import proc
from larch.lint.engine import (
    Finding as EngineFinding,
    LintRule,
    RuleCli,
    SourceFile,
    is_production_python_path,
    ordered_ast_child_nodes,
    qualified_symbol,
    run_rule_cli,
)

RULE_ID = "lint-status-routing-truthiness"
SUPPRESSION = RULE_ID
BASELINE_FILENAME = "status-routing-truthiness-baseline.json"
PATHSPECS = ("python/larch/*.py", "python/larch/**/*.py")
_SELF_MODULE = "python/larch/lint/lint_status_routing_truthiness.py"
_STATUS_SUFFIXES = ("status", "verdict", "result", "outcome")
_SKIP_NESTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
_CMP_OPS = (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)
_MEMBER_OPS = (ast.In, ast.NotIn)


def normalize_expr(node: ast.AST) -> str:
    """Return a stable AST dump for evidence matching and baseline identity."""
    try:
        return ast.dump(node, annotate_fields=False)
    except TypeError:
        return ast.dump(node)


def is_production_source_path(rel_path: str) -> bool:
    """Retain production ``python/larch/`` modules, excluding this rule module."""
    if rel_path == _SELF_MODULE:
        return False
    return is_production_python_path(rel_path)


def _status_suffix(name: str) -> bool:
    lower = name.lower()
    return any(lower.endswith(suffix) for suffix in _STATUS_SUFFIXES)


def _candidate_expr(node: ast.AST) -> ast.expr | None:
    """Return a status-like Name/Attribute chain, or None when unstable."""
    if isinstance(node, ast.Name):
        return node if _status_suffix(node.id) else None
    if not isinstance(node, ast.Attribute):
        return None
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    return node if _status_suffix(node.attr) else None


def _name_rooted_attr(node: ast.AST) -> bool:
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        cur = cur.value
    return isinstance(cur, ast.Name)


def _is_semantic_member(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(node.value)
    return isinstance(node, ast.Attribute) and _name_rooted_attr(node)


def _uppercase_name(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id.isupper()


def _membership_container_ok(node: ast.AST) -> bool:
    if _uppercase_name(node):
        return True
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        return bool(node.elts) and all(_is_semantic_member(elt) for elt in node.elts)
    return False


def _walk_same_scope(node: ast.AST) -> Iterator[ast.AST]:
    for child in ordered_ast_child_nodes(node):
        if isinstance(child, _SKIP_NESTED):
            continue
        yield child
        yield from _walk_same_scope(child)


def _collect_evidence(fn: ast.AST) -> set[str]:
    evidenced: set[str] = set()
    for node in _walk_same_scope(fn):
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        comparators = node.comparators
        ops = node.ops
        if len(ops) != 1 or len(comparators) != 1:
            continue
        right = comparators[0]
        op = ops[0]
        if isinstance(op, _CMP_OPS):
            for side, other in ((left, right), (right, left)):
                cand = _candidate_expr(side)
                if cand is not None and _is_semantic_member(other):
                    evidenced.add(normalize_expr(cand))
        elif isinstance(op, _MEMBER_OPS):
            cand = _candidate_expr(left)
            if cand is not None and _membership_container_ok(right):
                evidenced.add(normalize_expr(cand))
    return evidenced


def _iter_bare_boolean_nodes(expr: ast.expr) -> Iterator[ast.expr]:
    if isinstance(expr, ast.BoolOp):
        for value in expr.values:
            yield from _iter_bare_boolean_nodes(value)
        return
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        yield from _iter_bare_boolean_nodes(expr.operand)
        return
    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "bool"
        and len(expr.args) == 1
        and not expr.keywords
    ):
        yield from _iter_bare_boolean_nodes(expr.args[0])
        return
    yield expr


def _boolean_tests(fn: ast.AST) -> Iterator[ast.expr]:
    for node in _walk_same_scope(fn):
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            yield node.test


def _collect_bare_hits(
    fn: ast.AST, *, evidenced: set[str]
) -> list[tuple[ast.expr, str]]:
    reported: set[int] = set()
    hits: list[tuple[ast.expr, str]] = []

    def _consider(node: ast.expr) -> None:
        cand = _candidate_expr(node)
        if cand is None:
            return
        key = normalize_expr(cand)
        if key not in evidenced or id(node) in reported:
            return
        reported.add(id(node))
        hits.append((cand, key))

    for test in _boolean_tests(fn):
        for node in _iter_bare_boolean_nodes(test):
            _consider(node)
    for node in _walk_same_scope(fn):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "bool"
            and len(node.args) == 1
            and not node.keywords
        ):
            for bare in _iter_bare_boolean_nodes(node.args[0]):
                _consider(bare)
    hits.sort(key=lambda item: (item[0].lineno, item[0].col_offset, item[1]))
    return hits


def _nested_functions(fn: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    nested: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for stmt in getattr(fn, "body", []):
        nested.extend(_nested_functions_in_stmt(stmt))
    return nested


def _nested_functions_in_stmt(
    stmt: ast.AST,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    found: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        found.append(stmt)
        return found
    if isinstance(stmt, ast.ClassDef):
        return found
    for child in ordered_ast_child_nodes(stmt):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append(child)
        elif isinstance(child, ast.ClassDef):
            continue
        else:
            found.extend(_nested_functions_in_stmt(child))
    return found


def _analyze_function(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    prefix: tuple[str, ...],
    path: str,
) -> list[EngineFinding]:
    evidenced = _collect_evidence(fn)
    hits = _collect_bare_hits(fn, evidenced=evidenced)
    symbol = qualified_symbol(prefix)
    counts: dict[str, int] = {}
    findings: list[EngineFinding] = []
    for node, key in hits:
        counts[key] = counts.get(key, 0) + 1
        occurrence = counts[key]
        findings.append(
            EngineFinding(
                path=path,
                line=node.lineno,
                rule_id=RULE_ID,
                message=(
                    f"{symbol}: truthiness of status-like {key}; "
                    "use explicit terminal or routing membership"
                ),
                qualified_symbol=symbol,
                pattern_name=key,
                occurrence=occurrence,
            )
        )
    for nested in _nested_functions(fn):
        findings.extend(
            _analyze_function(nested, prefix=(*prefix, nested.name), path=path)
        )
    return findings


def _iter_top_functions(
    tree: ast.Module,
) -> Iterable[tuple[tuple[str, ...], ast.FunctionDef | ast.AsyncFunctionDef]]:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield (node.name,), node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield (node.name, item.name), item


def scan_module(tree: ast.Module, *, path: str) -> list[EngineFinding]:
    """Scan one module AST and return engine findings."""
    findings: list[EngineFinding] = []
    for prefix, fn in _iter_top_functions(tree):
        findings.extend(_analyze_function(fn, prefix=prefix, path=path))
    return findings


def detect(source: SourceFile) -> list[EngineFinding]:
    """Adapt module hits into engine findings with occurrence identity."""
    if not source.is_python:
        return []
    tree = source.python_ast
    if not isinstance(tree, ast.Module):
        return []
    return scan_module(tree, path=source.path)


RULE = LintRule(
    rule_id=RULE_ID,
    description=(
        "Flag truthiness tests of status-like values that have same-scope "
        "semantic members (G-Py-15)"
    ),
    detect=detect,
    syntax_policy="raise",
    suppression_token=SUPPRESSION,
    allow_inline_suppression=True,
    pathspecs=PATHSPECS,
    source_filter=is_production_source_path,
    occurrence_baseline=True,
    require_baseline=True,
    stale_baseline_on_clean_scan=False,
    occurrence_pattern_field="normalized_condition",
    warn_matching_baseline=True,
    exclude_tracked_symlinks=True,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint status-routing-truthiness``."""
    return run_rule_cli(
        argv if argv is not None else sys.argv[1:],
        rule=RULE,
        cli=RuleCli(
            prog="cli.py lint status-routing-truthiness",
            description=__doc__,
            baseline_filename=BASELINE_FILENAME,
            error_label="lint-status-routing-truthiness",
        ),
        runner=proc.ProcRunner(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
