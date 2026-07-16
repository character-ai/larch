"""Ratchet repository-root resolution onto ``larch.core.repo_roots``.

Production code may define neither a private ``_plugin_root`` helper nor an
inline ``git rev-parse --show-toplevel`` argv. The strict, engine-backed
occurrence baseline preserves reason-bearing legacy debt and can only shrink.
"""

from __future__ import annotations

import ast
import sys

from larch.core import proc
from larch.lint.engine import Finding, LintRule, RuleCli, SourceFile, run_rule_cli

RULE_ID = "root-resolution"
BASELINE_FILENAME = "root-resolution-baseline.json"
_PLUGIN_ROOT_KIND = "private-plugin-root"
_GIT_TOPLEVEL_KIND = "inline-git-toplevel"
_EXEMPT_PATHS = frozenset({
    "python/larch/core/repo_roots.py",
    "python/larch/lint/lint_root_resolution.py",
})


def _kind_for(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_plugin_root":
        return _PLUGIN_ROOT_KIND
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values = {
        item.value
        for item in node.elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }
    return _GIT_TOPLEVEL_KIND if {"rev-parse", "--show-toplevel"}.issubset(values) else None


def detect(source: SourceFile) -> list[Finding]:
    """Emit stable, symbol-free occurrence findings for production sources."""
    if not source.is_python or source.path in _EXEMPT_PATHS:
        return []
    matches = sorted(
        (
            (node, kind)
            for node in ast.walk(source.python_ast)
            if (kind := _kind_for(node)) is not None
        ),
        key=lambda item: (getattr(item[0], "lineno", 1), getattr(item[0], "col_offset", 0)),
    )
    occurrences: dict[str, int] = {}
    findings: list[Finding] = []
    for node, kind in matches:
        occurrences[kind] = occurrences.get(kind, 0) + 1
        occurrence = occurrences[kind]
        findings.append(Finding(
            path=source.path,
            line=getattr(node, "lineno", 1),
            rule_id=RULE_ID,
            message=f"{kind} must use larch.core.repo_roots (occurrence {occurrence})",
            occurrence=occurrence,
            occurrence_values=(("kind", kind),),
        ))
    return findings


RULE = LintRule(
    rule_id=RULE_ID,
    description=__doc__ or RULE_ID,
    detect=detect,
    syntax_policy="raise",
    suppression_token=RULE_ID,
    allow_inline_suppression=False,
    pathspecs=("python/larch",),
    occurrence_baseline=True,
    occurrence_fields=("kind",),
    occurrence_symbol_optional=True,
    require_baseline=True,
)

CLI = RuleCli(
    prog="cli.py lint root-resolution",
    description=__doc__,
    baseline_filename=BASELINE_FILENAME,
    error_label="lint-root-resolution",
)


def main(argv: list[str] | None = None) -> int:
    """Run the strict root-resolution adoption ratchet."""
    return run_rule_cli(
        argv if argv is not None else sys.argv[1:],
        cli=CLI,
        rule=RULE,
        runner=proc.ProcRunner(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
