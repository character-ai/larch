"""Ratchet cross-package import direction toward the larch layering contract.

Scans production modules under python/larch/**/*.py for imports that violate
the package-tier ordering: leaf utils (tier 0) -> larch.core (tier 1) ->
domain packages (tier 2) -> larch.cli (tier 3). A module in tier N must not
import from a package in tier M where M > N. Existing violations are
grandfathered in layering-baseline.json with a required reason per row.
New violations fail unless covered by an inline pragma.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.core import proc
from larch.lint.engine import (
    is_production_python_path,
    iter_python_source_files,
    ordered_ast_child_nodes,
    qualified_symbol,
    Finding as EngineFinding,
    LintRule,
    RuleCli,
    SourceFile,
    run_rule_cli,
)

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "layering-baseline.json"
BASELINE_KEYS = frozenset({"file", "qualified_symbol", "imported_package", "occurrence", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
MODULE_SYMBOL = "<module>"
SUPPRESSION_TOKEN = "lint-layering"

# Tier 0: leaf utils (no outbound larch imports needed)
# Tier 1: larch.core
# Tier 2: domain packages
# Tier 3: larch.cli (top of the import DAG; nothing depends on it)
PACKAGE_TIER: dict[str, int] = {
    "larch": 0,
    "larch.errors": 0,
    "larch.io": 0,
    "larch.outcomes": 0,
    "larch.core": 1,
    "larch.agents": 2,
    "larch.calibration": 2,
    "larch.design": 2,
    "larch.git": 2,
    "larch.implement": 2,
    "larch.issue": 2,
    "larch.lint": 2,
    "larch.release": 2,
    "larch.rendering": 2,
    "larch.report": 2,
    "larch.research": 2,
    "larch.review": 2,
    "larch.state": 2,
    "larch.cli": 3,
}


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    imported_package: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, int]:
        return (self.file, self.qualified_symbol, self.imported_package, self.occurrence)


def iter_source_files(larch_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under larch/, sorted."""
    return iter_python_source_files(
        larch_dir.parent,
        scope=Path("larch"),
        excluded_dirs=EXCLUDED_DIRS,
    )


def _importer_package(normalized_file: str) -> str | None:
    """Return the top-level larch package for a file's path, or None if not larch."""
    parts = normalized_file.split("/")
    if not parts or parts[0] != "larch":
        return None
    if not parts[1:]:
        return "larch"
    if not parts[2:]:
        basename = parts[1]
        if not basename.endswith(".py"):
            return None
        if basename == "__init__.py":
            return "larch"
        module_name = basename[:-3]
        return f"larch.{module_name}"
    subpkg = parts[1]
    return f"larch.{subpkg}"


def _top_level_package(module: str) -> str:
    """Extract the top-level larch sub-package, e.g. 'larch.core.config' -> 'larch.core'."""
    parts = module.split(".", 2)
    if parts[1:]:
        return f"{parts[0]}.{parts[1]}"
    return parts[0]


def _resolve_relative_package(importer_pkg: str, level: int, module: str | None) -> str | None:
    """Resolve a relative ImportFrom to an absolute dotted module name."""
    if level <= 0:
        return None
    parts = importer_pkg.split(".")
    ascend = level - 1
    if ascend > len(parts):
        return None
    base_parts = parts[: len(parts) - ascend] if ascend else parts
    if module:
        base_parts.extend(module.split("."))
    return ".".join(base_parts)


def _package_tier(pkg: str) -> int:
    """Return the tier for a package name; unknown larch.* sub-packages default to domain (2)."""
    if pkg in PACKAGE_TIER:
        return PACKAGE_TIER[pkg]
    if pkg.startswith("larch."):
        return 2
    return -1


def _importee_packages_from(node: ast.ImportFrom, *, importer_pkg: str) -> list[str]:
    """Return the list of top-level larch packages for an ImportFrom node."""
    if node.level and node.level > 0:
        resolved = _resolve_relative_package(importer_pkg, node.level, node.module)
        if resolved is None:
            return []
        if resolved == "larch" or resolved.startswith("larch."):
            return [_top_level_package(resolved)]
        return []
    module = node.module or ""
    if module == "larch":
        return [f"larch.{alias.name}" for alias in node.names]
    if module.startswith("larch."):
        return [_top_level_package(module)]
    return []


def _importee_packages(node: ast.stmt, *, importer_pkg: str) -> list[str]:
    """Return the list of top-level larch packages referenced by an import statement."""
    if isinstance(node, ast.Import):
        return [
            _top_level_package(alias.name)
            for alias in node.names
            if alias.name == "larch" or alias.name.startswith("larch.")
        ]
    if isinstance(node, ast.ImportFrom):
        return _importee_packages_from(node, importer_pkg=importer_pkg)
    return []


@dataclass
class _ScopeCtx:
    normalized_file: str
    importer_pkg: str
    importer_tier: int
    findings: list[Finding]


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    ctx: _ScopeCtx,
) -> None:
    symbol = qualified_symbol(prefix, module_symbol=MODULE_SYMBOL)
    occurrence_by_importee: dict[str, int] = {}

    def walk(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scope(node.body, prefix=(*prefix, node.name), ctx=ctx)
            return
        if isinstance(node, ast.ClassDef):
            _collect_scope(node.body, prefix=(*prefix, node.name), ctx=ctx)
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            importee_pkgs = _importee_packages(node, importer_pkg=ctx.importer_pkg)
            for importee_pkg in importee_pkgs:
                importee_tier = _package_tier(importee_pkg)
                if importee_tier > ctx.importer_tier and ctx.importer_pkg != importee_pkg:
                    occurrence_by_importee[importee_pkg] = (
                        occurrence_by_importee.get(importee_pkg, 0) + 1
                    )
                    lineno = getattr(node, "lineno", 0)
                    ctx.findings.append(
                        Finding(
                            file=ctx.normalized_file,
                            qualified_symbol=symbol,
                            imported_package=importee_pkg,
                            occurrence=occurrence_by_importee[importee_pkg],
                            lineno=lineno if isinstance(lineno, int) else 0,
                        )
                    )
            return
        for child in ordered_ast_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(path: Path, *, python_dir: Path, importer_pkg: str, importer_tier: int) -> list[Finding]:
    """Return all layering violations for one source file."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    ctx = _ScopeCtx(
        normalized_file=path.relative_to(python_dir).as_posix(),
        importer_pkg=importer_pkg,
        importer_tier=importer_tier,
        findings=[],
    )
    _collect_scope(tree.body, prefix=(), ctx=ctx)
    return ctx.findings

def detect(source: SourceFile) -> list[EngineFinding]:
    """Adapt layering findings to the shared baseline engine."""
    if not source.path.startswith("python/larch/"):
        return []
    normalized_file = source.path.removeprefix("python/")
    importer_pkg = _importer_package(normalized_file)
    if importer_pkg is None:
        return []
    importer_tier = _package_tier(importer_pkg)
    if importer_tier < 0:
        return []
    tree = cast("ast.Module", source.python_ast)
    ctx = _ScopeCtx(
        normalized_file=normalized_file,
        importer_pkg=importer_pkg,
        importer_tier=importer_tier,
        findings=[],
    )
    _collect_scope(tree.body, prefix=(), ctx=ctx)
    return [
        EngineFinding(
            path=source.path,
            line=finding.lineno,
            rule_id="layering",
            message=f"imports higher layer {finding.imported_package}",
            qualified_symbol=finding.qualified_symbol,
            pattern_name=finding.imported_package,
            occurrence=finding.occurrence,
        )
        for finding in ctx.findings
    ]


RULE = LintRule(
    rule_id="layering",
    description="Ratchet larch imports toward the package-tier contract",
    detect=detect,
    syntax_policy="skip",
    suppression_token=SUPPRESSION_TOKEN,
    pathspecs=("python/larch",),
    source_filter=is_production_python_path,
    occurrence_baseline=True,
    occurrence_pattern_field="imported_package",
    require_baseline=True,
)


def main(argv: list[str] | None = None) -> int:
    """Run the layering ratchet or regenerate its baseline."""
    return run_rule_cli(
        argv if argv is not None else sys.argv[1:],
        rule=RULE,
        cli=RuleCli(
            prog="cli.py lint layering",
            description=__doc__,
            baseline_filename=BASELINE_FILENAME,
            error_label="lint-layering",
            scoped_paths=("python/larch",),
            strict_stale=False,
        ),
        runner=proc.ProcRunner(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
