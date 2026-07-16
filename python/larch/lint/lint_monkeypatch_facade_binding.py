"""Ratchet monkeypatches away from facade-only imported bindings.

Scans test modules under python/test_*.py and python/tests/**/test_*.py
for monkeypatch.setattr calls that patch an attribute on a repo module where the
patched attribute is only re-exported by import in that module. Existing
intentional uses are grandfathered in
python/monkeypatch-facade-binding-baseline.json with a required reason per row.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from larch.core import proc
from larch.lint.engine import (
    EXIT_ERROR,
    Finding as EngineFinding,
    LintRule,
    SourceFile,
    ordered_ast_child_nodes,
    parse_argparse_args,
    qualified_symbol,
    try_read_python_ast,
    read_python_source_ast,
    run_rule,
)

TOOL_FAILURE_EXIT = 2
RULE_ID = "monkeypatch-facade-binding"
BASELINE_FILENAME = "monkeypatch-facade-binding-baseline.json"
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
MODULE_SYMBOL = "<module>"
SUPPRESSION_TOKEN = "lint-monkeypatch-binding"
SUPPRESSION_RE = re.compile(r"#\s*lint-monkeypatch-binding:\s*ok\s+\S")
OBJECT_SETATTR_MIN_ARGS = 2
OCCURRENCE_FIELDS = ("facade_module", "attribute", "defining_module")
PATHSPECS = ("python",)
PYTHON_PREFIX = "python/"


@dataclass(frozen=True)
class ModuleRef:
    name: str
    path: Path


@dataclass(frozen=True)
class Candidate:
    module: ModuleRef
    attribute: str


@dataclass(frozen=True)
class ScanState:
    normalized_file: str
    imports: dict[str, ModuleRef]
    resolver: ModuleResolver
    lines: list[str]
    findings: list[Finding]


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    facade_module: str
    attribute: str
    defining_module: str
    occurrence: int
    lineno: int
    suppressed: bool = False

    def key(self) -> tuple[str, str, str, str, str, int]:
        return (
            self.file,
            self.qualified_symbol,
            self.facade_module,
            self.attribute,
            self.defining_module,
            self.occurrence,
        )


class ModuleResolver:
    """Static resolver for repo modules under python/."""

    def __init__(self, python_dir: Path) -> None:
        self.python_dir = python_dir
        self._module_cache: dict[str, ModuleRef | None] = {}
        self._tree_cache: dict[Path, ast.Module | None] = {}

    def source_for_module(self, module_name: str) -> ModuleRef | None:
        if module_name in self._module_cache:
            return self._module_cache[module_name]
        ref = self._source_for_module_uncached(module_name)
        self._module_cache[module_name] = ref
        return ref

    def parse_module(self, ref: ModuleRef) -> ast.Module | None:
        cached = self._tree_cache.get(ref.path)
        if ref.path in self._tree_cache:
            return cached
        tree = try_read_python_ast(ref.path)
        if tree is None:
            self._tree_cache[ref.path] = None
            return None
        self._tree_cache[ref.path] = tree
        return tree

    def resolve_imported_module_attribute(self, ref: ModuleRef, attribute: str) -> ModuleRef | None:
        tree = self.parse_module(ref)
        if tree is None:
            return None
        if attribute in _module_level_definition_names(tree):
            return None
        imported = self._imported_module_attribute(tree, ref, attribute)
        if imported is not None:
            return imported
        return None

    def import_source_for_attribute(self, ref: ModuleRef, attribute: str) -> str | None:
        tree = self.parse_module(ref)
        if tree is None:
            return None
        if attribute in _module_level_definition_names(tree):
            return None
        defining_modules: list[str] = []
        for statement in tree.body:
            defining_module = _import_binding_source(statement, attribute, current=ref)
            if defining_module is not None:
                defining_modules.append(defining_module)
        return defining_modules[-1] if defining_modules else None

    def _source_for_module_uncached(self, module_name: str) -> ModuleRef | None:
        if not _valid_module_name(module_name):
            return None
        relative = Path(*module_name.split("."))
        file_path = self.python_dir / relative.with_suffix(".py")
        if _is_regular_under(file_path, self.python_dir):
            return ModuleRef(module_name, file_path)
        init_path = self.python_dir / relative / "__init__.py"
        if _is_regular_under(init_path, self.python_dir):
            return ModuleRef(module_name, init_path)
        return None

    def _imported_module_attribute(
        self,
        tree: ast.Module,
        current: ModuleRef,
        attribute: str,
    ) -> ModuleRef | None:
        resolved: ModuleRef | None = None
        for statement in tree.body:
            imported = self._module_ref_from_import(statement, current=current, attribute=attribute)
            if imported is not None:
                resolved = imported
        return resolved

    def _module_ref_from_import(
        self,
        statement: ast.stmt,
        *,
        current: ModuleRef,
        attribute: str,
    ) -> ModuleRef | None:
        if isinstance(statement, ast.Import):
            return self._module_ref_from_plain_import(statement, attribute=attribute)
        if isinstance(statement, ast.ImportFrom):
            return self._module_ref_from_from_import(statement, current=current, attribute=attribute)
        return None

    def _module_ref_from_plain_import(self, statement: ast.Import, *, attribute: str) -> ModuleRef | None:
        for alias in statement.names:
            bound_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
            if bound_name == attribute:
                return self.source_for_module(alias.name)
        return None

    def _module_ref_from_from_import(
        self,
        statement: ast.ImportFrom,
        *,
        current: ModuleRef,
        attribute: str,
    ) -> ModuleRef | None:
        base_module = _absolute_from_import(
            statement.module,
            statement.level,
            current_module=current.name,
            current_is_package=current.path.name == "__init__.py",
        )
        if base_module is None:
            return None
        for alias in statement.names:
            if alias.name == "*":
                continue
            bound_name = alias.asname or alias.name
            if bound_name != attribute:
                continue
            candidate_name = f"{base_module}.{alias.name}" if base_module else alias.name
            candidate = self.source_for_module(candidate_name)
            if candidate is not None:
                return candidate
        return None


def _is_regular_under(path: Path, root: Path) -> bool:
    try:
        _ = path.relative_to(root)
    except ValueError:
        return False
    return path.is_file() and not path.is_symlink()


def _valid_module_name(module_name: str) -> bool:
    return bool(module_name) and all(part.isidentifier() for part in module_name.split("."))


def _is_valid_test_file(value: str) -> bool:
    parts = value.split("/")
    if (
        value.startswith(("/", "larch/"))
        or not value.endswith(".py")
        or "" in parts
        or "." in parts
        or ".." in parts
    ):
        return False
    filename = parts[-1]
    if not filename.startswith("test_"):
        return False
    return len(parts) == 1 or parts[0] == "tests"


def iter_source_files(python_dir: Path) -> list[Path]:
    """Return recursively discovered test files in lint scope, sorted."""
    result = [path for path in sorted(python_dir.glob("test_*.py")) if _is_regular_under(path, python_dir)]
    tests_dir = python_dir / "tests"
    if not tests_dir.is_dir():
        return result
    for path in sorted(tests_dir.rglob("test_*.py")):
        if not _is_regular_under(path, python_dir):
            continue
        relative = path.relative_to(python_dir)
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        result.append(path)
    return result


def _module_name_for_path(path: Path, *, python_dir: Path) -> str:
    relative = path.relative_to(python_dir).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _absolute_from_import(
    module: str | None,
    level: int,
    *,
    current_module: str,
    current_is_package: bool,
) -> str | None:
    if level == 0:
        return module or ""
    package_parts = current_module.split(".") if current_is_package else current_module.split(".")[:-1]
    keep_count = len(package_parts) - level + 1
    if keep_count < 0:
        return None
    base_parts = package_parts[:keep_count]
    if module:
        base_parts.extend(module.split("."))
    return ".".join(base_parts)


def _module_level_definition_names(tree: ast.Module) -> frozenset[str]:
    names: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(statement.name)
        elif isinstance(statement, ast.Assign):
            for target in statement.targets:
                names.update(_target_names(target))
        elif isinstance(statement, ast.AnnAssign):
            names.update(_target_names(statement.target))
    return frozenset(names)


def _target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_target_names(element))
        return names
    return set()


def _import_binding_source(statement: ast.stmt, attribute: str, *, current: ModuleRef) -> str | None:
    if isinstance(statement, ast.Import):
        for alias in statement.names:
            bound_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
            if bound_name == attribute:
                return alias.name
    if not isinstance(statement, ast.ImportFrom):
        return None
    base_module = _absolute_from_import(
        statement.module,
        statement.level,
        current_module=current.name,
        current_is_package=current.path.name == "__init__.py",
    )
    if base_module is None:
        return None
    for alias in statement.names:
        if alias.name == "*":
            continue
        bound_name = alias.asname or alias.name
        if bound_name == attribute:
            return base_module or alias.name
    return None


def _build_import_map(
    tree: ast.Module,
    *,
    current: ModuleRef,
    resolver: ModuleResolver,
) -> dict[str, ModuleRef]:
    imports: dict[str, ModuleRef] = {}
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            imports.update(_plain_import_map(statement, resolver=resolver))
        elif isinstance(statement, ast.ImportFrom):
            imports.update(_from_import_map(statement, current=current, resolver=resolver))
    return imports


def _plain_import_map(statement: ast.Import, *, resolver: ModuleResolver) -> dict[str, ModuleRef]:
    imports: dict[str, ModuleRef] = {}
    for alias in statement.names:
        target_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
        module_name = alias.name if alias.asname else target_name
        module = resolver.source_for_module(module_name)
        if module is not None:
            imports[target_name] = module
    return imports


def _from_import_map(
    statement: ast.ImportFrom,
    *,
    current: ModuleRef,
    resolver: ModuleResolver,
) -> dict[str, ModuleRef]:
    imports: dict[str, ModuleRef] = {}
    base_module = _absolute_from_import(
        statement.module,
        statement.level,
        current_module=current.name,
        current_is_package=current.path.name == "__init__.py",
    )
    if base_module is None:
        return imports
    for alias in statement.names:
        if alias.name == "*":
            continue
        local_name = alias.asname or alias.name
        candidate_name = f"{base_module}.{alias.name}" if base_module else alias.name
        module = resolver.source_for_module(candidate_name)
        if module is not None:
            imports[local_name] = module
    return imports


def _attribute_parts(node: ast.AST) -> list[str] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    parts.reverse()
    return parts


def _resolve_expr_module(
    node: ast.AST,
    *,
    imports: dict[str, ModuleRef],
    resolver: ModuleResolver,
) -> ModuleRef | None:
    parts = _attribute_parts(node)
    if not parts:
        return None
    current = imports.get(parts[0])
    if current is None:
        return None
    for attribute in parts[1:]:
        current = resolver.resolve_imported_module_attribute(current, attribute)
        if current is None:
            return None
    return current


def _is_monkeypatch_setattr(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "setattr"
        and isinstance(func.value, ast.Name)
        and func.value.id == "monkeypatch"
    )


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _candidate_from_dotted_string(target: str, *, resolver: ModuleResolver) -> Candidate | None:
    if "." not in target:
        return None
    module_name, attribute = target.rsplit(".", maxsplit=1)
    if not attribute.isidentifier():
        return None
    module = resolver.source_for_module(module_name)
    if module is None:
        return None
    return Candidate(module, attribute)


def _candidate_from_call(
    node: ast.AST,
    *,
    imports: dict[str, ModuleRef],
    resolver: ModuleResolver,
) -> Candidate | None:
    if not _is_monkeypatch_setattr(node) or not isinstance(node, ast.Call) or not node.args:
        return None
    target_string = _literal_string(node.args[0])
    if target_string is not None:
        return _candidate_from_dotted_string(target_string, resolver=resolver)
    if len(node.args) < OBJECT_SETATTR_MIN_ARGS:
        return None
    attribute = _literal_string(node.args[1])
    if attribute is None or not attribute.isidentifier():
        return None
    module = _resolve_expr_module(node.args[0], imports=imports, resolver=resolver)
    if module is None:
        return None
    return Candidate(module, attribute)


def _has_suppression(lines: list[str], lineno: int) -> bool:
    if lineno < 1 or lineno > len(lines):
        return False
    return SUPPRESSION_RE.search(lines[lineno - 1]) is not None


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    state: ScanState,
) -> None:
    occurrence = 0
    symbol = qualified_symbol(prefix, module_symbol=MODULE_SYMBOL)

    def walk(node: ast.AST) -> None:
        nonlocal occurrence
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                state=state,
            )
            return
        if isinstance(node, ast.ClassDef):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                state=state,
            )
            return
        candidate = _candidate_from_call(node, imports=state.imports, resolver=state.resolver)
        if candidate is not None:
            occurrence += 1
            defining_module = state.resolver.import_source_for_attribute(candidate.module, candidate.attribute)
            if defining_module is not None:
                lineno = getattr(node, "lineno", 0)
                line_number = lineno if isinstance(lineno, int) else 0
                state.findings.append(
                    Finding(
                        file=state.normalized_file,
                        qualified_symbol=symbol,
                        facade_module=candidate.module.name,
                        attribute=candidate.attribute,
                        defining_module=defining_module,
                        occurrence=occurrence,
                        lineno=line_number,
                        suppressed=_has_suppression(state.lines, line_number),
                    )
                )
        for child in ordered_ast_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(path: Path, *, python_dir: Path, resolver: ModuleResolver) -> list[Finding]:
    """Return monkeypatch facade-binding findings for one test file."""
    parsed = read_python_source_ast(path)
    if parsed is None:
        return []
    source, tree = parsed
    normalized_file = path.relative_to(python_dir).as_posix()
    current = ModuleRef(_module_name_for_path(path, python_dir=python_dir), path)
    imports = _build_import_map(tree, current=current, resolver=resolver)
    findings: list[Finding] = []
    _collect_scope(
        tree.body,
        prefix=(),
        state=ScanState(
            normalized_file=normalized_file,
            imports=imports,
            resolver=resolver,
            lines=source.splitlines(),
            findings=findings,
        ),
    )
    return findings


def is_test_source_path(rel_path: str) -> bool:
    """Pre-load filter for repo-relative monkeypatch test paths."""
    if not rel_path.startswith(PYTHON_PREFIX) or not rel_path.endswith(".py"):
        return False
    under_python = rel_path[len(PYTHON_PREFIX) :]
    if EXCLUDED_DIRS.intersection(Path(under_python).parts):
        return False
    return _is_valid_test_file(under_python)


def _to_engine_finding(finding: Finding) -> EngineFinding:
    return EngineFinding(
        path=f"{PYTHON_PREFIX}{finding.file}",
        line=finding.lineno,
        rule_id=RULE_ID,
        message=(
            f"patches {finding.facade_module}.{finding.attribute}, imported from "
            f"{finding.defining_module} occurrence {finding.occurrence}; patch the "
            "defining module, or patch the consuming module's own binding"
        ),
        qualified_symbol=finding.qualified_symbol,
        pattern_name=finding.facade_module,
        occurrence=finding.occurrence,
        occurrence_values=(
            ("facade_module", finding.facade_module),
            ("attribute", finding.attribute),
            ("defining_module", finding.defining_module),
        ),
    )


def build_rule(root: Path) -> LintRule:
    """Build an engine rule closed over a ModuleResolver for ``root``."""
    python_dir = root / "python"
    resolver = ModuleResolver(python_dir)

    def detect(source: SourceFile) -> list[EngineFinding]:
        if not source.is_python or not is_test_source_path(source.path):
            return []
        rel = source.path[len(PYTHON_PREFIX) :]
        path = python_dir / rel
        legacy = scan_file(path, python_dir=python_dir, resolver=resolver)
        # Engine applies inline suppression; emit every live site.
        return [_to_engine_finding(finding) for finding in legacy]

    return LintRule(
        rule_id=RULE_ID,
        description=(
            "Ratchet monkeypatches away from facade-only imported bindings"
        ),
        detect=detect,
        syntax_policy="skip",
        suppression_token=SUPPRESSION_TOKEN,
        pathspecs=PATHSPECS,
        source_filter=is_test_source_path,
        occurrence_baseline=True,
        occurrence_fields=OCCURRENCE_FIELDS,
        require_baseline=True,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint monkeypatch-facade-binding",
        description=__doc__,
    )
    _ = parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root (default: checkout containing this module).",
    )
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=f"Regenerate {BASELINE_FILENAME} from live AST scan.",
    )
    _ = parser.add_argument(
        "--initial-reason",
        help="Reason used for live findings without preserved baseline reasons.",
    )
    return parse_argparse_args(parser, argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint monkeypatch-facade-binding``."""
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(
            f"lint-monkeypatch-facade-binding: python directory not found: {python_dir}",
            file=sys.stderr,
        )
        return EXIT_ERROR
    initial_reason = parsed.initial_reason
    if initial_reason is not None and not str(initial_reason).strip():
        print(
            "lint-monkeypatch-facade-binding: --initial-reason must be non-empty",
            file=sys.stderr,
        )
        return EXIT_ERROR
    return run_rule(
        build_rule(root),
        root,
        proc.ProcRunner(),
        baseline_path=python_dir / BASELINE_FILENAME,
        write_baseline=bool(parsed.write),
        initial_reason=None if initial_reason is None else str(initial_reason),
        strict_stale=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
