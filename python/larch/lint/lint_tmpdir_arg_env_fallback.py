"""Flag direct ``args.tmpdir`` consumption without an IMPLEMENT_TMPDIR fallback.

Engine-backed AST ratchet over ``python/larch/**/*.py``. Flags:

1. ``validate_tmpdir(...)`` (bare or attribute) whose first argument is exactly
   ``args.tmpdir``.
2. ``Path(...)`` whose sole argument is exactly ``args.tmpdir``.

``BoolOp`` fallback forms such as
``args.tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")`` are outside
the direct-node rule. Grandfathered deliberate sites live in
``python/tmpdir-arg-env-fallback-baseline.json`` with required reasons.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

from larch.core import proc
from larch.lint.engine import (
    Finding as EngineFinding,
    LintRule,
    RuleCli,
    SourceFile,
    run_rule_cli,
)

SUPPRESSION = "lint-tmpdir-arg-env-fallback"
RULE_ID = SUPPRESSION
BASELINE_FILENAME = "tmpdir-arg-env-fallback-baseline.json"
PATHSPECS = ("python/larch/*.py", "python/larch/**/*.py")
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__", "tests"})
MODULE_SYMBOL = "<module>"
PYTHON_TREE_PREFIX = "python/"
PATTERN_VALIDATE = "validate_tmpdir"
PATTERN_PATH = "Path"


@dataclass(frozen=True)
class Hit:
    """One direct ``args.tmpdir`` call-site finding."""

    qualified_symbol: str
    pattern_name: str
    occurrence: int
    lineno: int


def is_exempt_path(path: Path) -> bool:
    """Return whether a source file is outside production lint scope."""
    name = path.name
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def is_production_source_path(rel_path: str) -> bool:
    """Pre-load filter for repo-relative paths under ``python/larch/**/*.py``."""
    if not rel_path.startswith(f"{PYTHON_TREE_PREFIX}larch/") or not rel_path.endswith(".py"):
        return False
    path = Path(rel_path)
    if is_exempt_path(path):
        return False
    under_python = rel_path[len(PYTHON_TREE_PREFIX) :]
    return not bool(EXCLUDED_DIRS.intersection(Path(under_python).parts))


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
    return [child for _, child in indexed]


def _is_args_tmpdir(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "tmpdir"
        and isinstance(node.value, ast.Name)
        and node.value.id == "args"
    )


def _callee_final_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _match_pattern(node: ast.Call) -> str | None:
    name = _callee_final_name(node.func)
    if name == PATTERN_VALIDATE and node.args and _is_args_tmpdir(node.args[0]):
        return PATTERN_VALIDATE
    if (
        name == PATTERN_PATH
        and len(node.args) == 1
        and not node.keywords
        and _is_args_tmpdir(node.args[0])
    ):
        return PATTERN_PATH
    return None


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    findings: list[Hit],
) -> None:
    counts: dict[str, int] = {}
    symbol = _qualified(prefix)

    def walk(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scope(node.body, prefix=(*prefix, node.name), findings=findings)
            return
        if isinstance(node, ast.ClassDef):
            _collect_scope(node.body, prefix=(*prefix, node.name), findings=findings)
            return
        if isinstance(node, ast.Call):
            pattern = _match_pattern(node)
            if pattern is not None:
                counts[pattern] = counts.get(pattern, 0) + 1
                lineno = getattr(node, "lineno", 0)
                findings.append(
                    Hit(
                        qualified_symbol=symbol,
                        pattern_name=pattern,
                        occurrence=counts[pattern],
                        lineno=lineno if isinstance(lineno, int) else 0,
                    )
                )
        for child in _ordered_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_module(tree: ast.Module) -> list[Hit]:
    """Return direct ``args.tmpdir`` findings for one parsed module."""
    findings: list[Hit] = []
    _collect_scope(tree.body, prefix=(), findings=findings)
    return findings


def detect(source: SourceFile) -> list[EngineFinding]:
    """Adapt detector hits into engine findings with occurrence identity."""
    if not source.is_python:
        return []
    tree = source.python_ast
    if not isinstance(tree, ast.Module):
        return []
    hits = scan_module(tree)
    return [
        EngineFinding(
            path=source.path,
            line=hit.lineno,
            rule_id=RULE_ID,
            message=(
                f"unsafe direct args.tmpdir via {hit.pattern_name} "
                f"occurrence {hit.occurrence}; use "
                f"args.tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, '') "
                f"or baseline with a reason"
            ),
            qualified_symbol=hit.qualified_symbol,
            pattern_name=hit.pattern_name,
            occurrence=hit.occurrence,
        )
        for hit in hits
    ]


RULE = LintRule(
    rule_id=RULE_ID,
    description=(
        "Flag direct args.tmpdir consumption without an IMPLEMENT_TMPDIR fallback"
    ),
    detect=detect,
    syntax_policy="raise",
    suppression_token=SUPPRESSION,
    allow_inline_suppression=False,
    pathspecs=PATHSPECS,
    source_filter=is_production_source_path,
    occurrence_baseline=True,
    require_baseline=True,
    stale_baseline_on_clean_scan=True,
)

CLI = RuleCli(
    prog="cli.py lint tmpdir-arg-env-fallback",
    description=__doc__,
    baseline_filename=BASELINE_FILENAME,
    error_label="lint-tmpdir-arg-env-fallback",
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint tmpdir-arg-env-fallback``."""
    return run_rule_cli(
        argv if argv is not None else sys.argv[1:],
        rule=RULE,
        cli=CLI,
        runner=proc.ProcRunner(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
