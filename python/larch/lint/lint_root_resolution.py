"""Ratchet root resolution onto ``larch.core.repo_roots`` owners.

The rule rejects private ``_plugin_root`` definitions and literal
``git rev-parse --show-toplevel`` argument vectors in production modules.
The small baseline records legacy probes that need their command-result shape
while callers are migrated; every row carries a reason and is reported stale
once its source no longer contains the recorded pattern.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import cast

from larch.core import proc
from larch.lint.engine import (
    EXIT_ERROR,
    BaselineError,
    Finding,
    LintRule,
    RuleCli,
    SourceFile,
    load_json_array,
    parse_lint_argv,
    run_rule,
)

RULE_ID = "root-resolution"
BASELINE_FILENAME = "root-resolution-baseline.json"
_PLUGIN_ROOT_KIND = "private-plugin-root"
_GIT_TOPLEVEL_KIND = "inline-git-toplevel"


def _kind_for(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_plugin_root":
        return _PLUGIN_ROOT_KIND
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values = {item.value for item in node.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)}
    return _GIT_TOPLEVEL_KIND if {"rev-parse", "--show-toplevel"}.issubset(values) else None


def _baseline(root: Path) -> dict[tuple[str, str], tuple[int, str]]:
    path = root / "python" / BASELINE_FILENAME
    rows = load_json_array(path, label="root-resolution baseline")
    result: dict[tuple[str, str], tuple[int, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("baseline row must be an object")
        values = cast("dict[str, object]", row)
        path_value = values.get("path")
        kind = values.get("kind")
        count = values.get("count")
        reason = values.get("reason")
        if not all(isinstance(value, str) and value.strip() for value in (path_value, kind, reason)) or not isinstance(count, int) or count <= 0:
            raise ValueError("baseline rows require non-empty path, kind, reason, and positive count")
        result[(cast("str", path_value), cast("str", kind))] = (count, cast("str", reason))
    return result


def build_rule(root: Path) -> LintRule:
    baseline = _baseline(root)

    def detect(source: SourceFile) -> list[Finding]:
        if source.path in {"python/larch/core/repo_roots.py", "python/larch/lint/lint_root_resolution.py"} or not source.is_python:
            return []
        findings: list[Finding] = []
        seen: dict[str, int] = {}
        for node in ast.walk(source.python_ast):
            kind = _kind_for(node)
            if kind is None:
                continue
            seen[kind] = seen.get(kind, 0) + 1
            baseline_count = baseline.get((source.path, kind), (0, ""))[0]
            if seen[kind] <= baseline_count:
                continue
            findings.append(Finding(
                path=source.path,
                line=getattr(node, "lineno", 1),
                rule_id=RULE_ID,
                message=f"{kind} must use larch.core.repo_roots (occurrence {seen[kind]})",
                pattern_name=kind,
                occurrence=seen[kind],
            ))
        return findings

    return LintRule(
        rule_id=RULE_ID,
        description=__doc__ or RULE_ID,
        detect=detect,
        syntax_policy="raise",
        suppression_token=RULE_ID,
        allow_inline_suppression=False,
        pathspecs=("python/larch",),
        occurrence_baseline=False,
    )


CLI = RuleCli(prog="cli.py lint root-resolution", description=__doc__, baseline_filename=None, error_label="lint-root-resolution")


def main(argv: list[str] | None = None) -> int:
    parsed = parse_lint_argv(argv if argv is not None else sys.argv[1:], cli=CLI)
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    try:
        rule = build_rule(root)
    except (BaselineError, TypeError, ValueError) as exc:
        print(f"lint-root-resolution: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return run_rule(rule, root, proc.ProcRunner())


if __name__ == "__main__":
    raise SystemExit(main())
