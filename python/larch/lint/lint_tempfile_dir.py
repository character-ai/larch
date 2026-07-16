"""Ratchet tempfile creation toward explicit scratch directories.

Scans production modules under python/larch/**/*.py for tempfile factory calls
that omit dir=. Existing deliberate ambient-temp uses are grandfathered in
python/tempfile-dir-baseline.json with a required reason per row.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.core import proc
from larch.lint.engine import (
    Finding as EngineFinding,
    LintRule,
    RuleCli,
    SourceFile,
    iter_python_source_files,
    is_production_python_path,
    ordered_ast_child_nodes,
    qualified_symbol,
    run_rule_cli,
)

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "tempfile-dir-baseline.json"
SUPPRESSION_TOKEN = "lint-tempfile-dir"
ALLOWED_CALLEES = frozenset({"mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryDirectory"})
BASELINE_KEYS = frozenset({"file", "qualified_symbol", "callee", "occurrence", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
MODULE_SYMBOL = "<module>"


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    callee: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, int]:
        return (self.file, self.qualified_symbol, self.callee, self.occurrence)


def iter_source_files(larch_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under larch/, sorted."""
    return iter_python_source_files(
        larch_dir.parent,
        scope=Path("larch"),
        excluded_dirs=EXCLUDED_DIRS,
    )


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
    symbol = qualified_symbol(prefix, module_symbol=MODULE_SYMBOL)

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
        for child in ordered_ast_child_nodes(node):
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

def detect(source: SourceFile) -> list[EngineFinding]:
    """Adapt tempfile findings to the shared baseline engine."""
    if not source.path.startswith("python/larch/"):
        return []
    tree = cast("ast.Module", source.python_ast)
    legacy: list[Finding] = []
    _collect_scope(
        tree.body,
        prefix=(),
        normalized_file=source.path.removeprefix("python/"),
        findings=legacy,
    )
    return [
        EngineFinding(
            path=source.path,
            line=finding.lineno,
            rule_id="tempfile-dir",
            message=f"calls tempfile.{finding.callee} without dir=",
            qualified_symbol=finding.qualified_symbol,
            pattern_name=finding.callee,
            occurrence=finding.occurrence,
        )
        for finding in legacy
    ]


RULE = LintRule(
    rule_id="tempfile-dir",
    description="Ratchet tempfile creation toward explicit scratch directories",
    detect=detect,
    syntax_policy="skip",
    suppression_token=SUPPRESSION_TOKEN,
    pathspecs=("python/larch",),
    source_filter=is_production_python_path,
    occurrence_baseline=True,
    occurrence_pattern_field="callee",
    require_baseline=True,
)


def main(argv: list[str] | None = None) -> int:
    """Run the tempfile-directory ratchet or regenerate its baseline."""
    return run_rule_cli(
        argv if argv is not None else sys.argv[1:],
        rule=RULE,
        cli=RuleCli(
            prog="cli.py lint tempfile-dir",
            description=__doc__,
            baseline_filename=BASELINE_FILENAME,
            error_label="lint-tempfile-dir",
            scoped_paths=("python/larch",),
            strict_stale=False,
        ),
        runner=proc.ProcRunner(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
