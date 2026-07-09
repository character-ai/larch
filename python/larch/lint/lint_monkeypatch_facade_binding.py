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
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "monkeypatch-facade-binding-baseline.json"
BASELINE_KEYS = frozenset(
    {
        "file",
        "qualified_symbol",
        "facade_module",
        "attribute",
        "defining_module",
        "occurrence",
        "reason",
    }
)
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
MODULE_SYMBOL = "<module>"
SUPPRESSION_RE = re.compile(r"#\s*lint-monkeypatch-binding:\s*ok\s+\S")
OBJECT_SETATTR_MIN_ARGS = 2


class Record(TypedDict):
    file: str
    qualified_symbol: str
    facade_module: str
    attribute: str
    defining_module: str
    occurrence: int
    reason: str


class BaselineError(ValueError):
    """Raised when the baseline cannot be trusted."""


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
        try:
            source = ref.path.read_text(encoding="utf-8")
        except OSError:
            self._tree_cache[ref.path] = None
            return None
        try:
            tree = ast.parse(source)
        except SyntaxError:
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


def normalize_file_path(raw: str) -> str:
    """Return a normalized POSIX path relative to python/."""
    normalized = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.removeprefix("python/")


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


def _validate_normalized_file(value: object, *, source: Path, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: record {index} has invalid file")
    normalized = normalize_file_path(value)
    if normalized != value or not _is_valid_test_file(normalized):
        raise BaselineError(f"{source}: record {index} has invalid file")
    return normalized


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
    symbol = _qualified(prefix)

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
        for child in _ordered_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(path: Path, *, python_dir: Path, resolver: ModuleResolver) -> list[Finding]:
    """Return monkeypatch facade-binding findings for one test file."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
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


def _record_key(record: Record) -> tuple[str, str, str, str, str, int]:
    return (
        record["file"],
        record["qualified_symbol"],
        record["facade_module"],
        record["attribute"],
        record["defining_module"],
        record["occurrence"],
    )


def _finding_sort_key(finding: Finding) -> tuple[str, str, str, str, str, int]:
    return finding.key()


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name = _validate_normalized_file(record["file"], source=source, index=index)
    qualified_symbol = record["qualified_symbol"]
    facade_module = record["facade_module"]
    attribute = record["attribute"]
    defining_module = record["defining_module"]
    occurrence = record["occurrence"]
    reason = record["reason"]
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(facade_module, str) or not _valid_module_name(facade_module):
        raise BaselineError(f"{source}: record {index} has invalid facade_module")
    if not isinstance(attribute, str) or not attribute.isidentifier():
        raise BaselineError(f"{source}: record {index} has invalid attribute")
    if not isinstance(defining_module, str) or not _valid_module_name(defining_module):
        raise BaselineError(f"{source}: record {index} has invalid defining_module")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "qualified_symbol": qualified_symbol,
        "facade_module": facade_module,
        "attribute": attribute,
        "defining_module": defining_module,
        "occurrence": occurrence,
        "reason": reason,
    }


def _first_duplicate(
    keys: Iterable[tuple[str, str, str, str, str, int]],
) -> tuple[str, str, str, str, str, int] | None:
    seen: set[tuple[str, str, str, str, str, int]] = set()
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


def _collect_all(python_dir: Path) -> list[Finding]:
    resolver = ModuleResolver(python_dir)
    findings: list[Finding] = []
    for path in iter_source_files(python_dir):
        findings.extend(scan_file(path, python_dir=python_dir, resolver=resolver))
    return findings


def _active_findings(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if not finding.suppressed]


def _check_duplicate_live(findings: list[Finding]) -> str | None:
    duplicate = _first_duplicate(finding.key() for finding in _active_findings(findings))
    if duplicate is None:
        return None
    return f"duplicate live identity {format_key(duplicate)}"


def format_key(key: tuple[str, str, str, str, str, int]) -> str:
    file_name, qualified_symbol, facade_module, attribute, defining_module, occurrence = key
    return f"{file_name}:{qualified_symbol} {facade_module}.{attribute} from {defining_module}#{occurrence}"


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
    preserved: dict[tuple[str, str, str, str, str, int], str] = {}
    if baseline_path.is_file():
        preserved = {_record_key(record): record["reason"] for record in load_baseline(baseline_path)}
    reason_default = initial_reason.strip() if initial_reason is not None else None
    records: list[Record] = []
    missing: list[str] = []
    for finding in sorted(_active_findings(findings), key=_finding_sort_key):
        reason = preserved.get(finding.key()) or reason_default
        if reason is None:
            missing.append(format_key(finding.key()))
            continue
        records.append(
            {
                "file": finding.file,
                "qualified_symbol": finding.qualified_symbol,
                "facade_module": finding.facade_module,
                "attribute": finding.attribute,
                "defining_module": finding.defining_module,
                "occurrence": finding.occurrence,
                "reason": reason,
            }
        )
    if missing:
        joined = "\n  ".join(missing)
        raise BaselineError("missing baseline reasons for live monkeypatch facade-binding findings:\n  " + joined)
    return records


def _run_write(
    python_dir: Path,
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> int:
    try:
        findings = _collect_all(python_dir)
        duplicate = _check_duplicate_live(findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
        records = _records_for_write(
            findings,
            baseline_path=baseline_path,
            initial_reason=initial_reason,
        )
    except BaselineError as exc:
        print(f"lint-monkeypatch-facade-binding: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(f"lint-monkeypatch-facade-binding: wrote {len(records)} records to {baseline_path}", file=sys.stderr)
    return 0


def _run_check(python_dir: Path, *, baseline_path: Path) -> int:
    try:
        baseline_records = load_baseline(baseline_path)
        findings = _collect_all(python_dir)
        duplicate = _check_duplicate_live(findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
    except BaselineError as exc:
        print(f"lint-monkeypatch-facade-binding: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys = frozenset(_record_key(record) for record in baseline_records)
    new_findings: list[Finding] = []
    warned: list[Finding] = []
    for finding in sorted(_active_findings(findings), key=_finding_sort_key):
        if finding.key() in baseline_keys:
            warned.append(finding)
        else:
            new_findings.append(finding)
    for finding in warned:
        print(
            "warning: "
            f"{finding.file}:{finding.lineno}:{finding.qualified_symbol} patches "
            f"{finding.facade_module}.{finding.attribute}, imported from {finding.defining_module} "
            f"occurrence {finding.occurrence} (baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.file}:{finding.lineno}:{finding.qualified_symbol} patches "
            f"{finding.facade_module}.{finding.attribute}, imported from {finding.defining_module} "
            f"occurrence {finding.occurrence}; patch the defining module, or patch the "
            "consuming module's own binding",
            file=sys.stderr,
        )
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint monkeypatch-facade-binding", description=__doc__)
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
        print(f"lint-monkeypatch-facade-binding: python directory not found: {python_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_path = python_dir / BASELINE_FILENAME
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-monkeypatch-facade-binding: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(python_dir, baseline_path=baseline_path, initial_reason=initial_reason)
    return _run_check(python_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
