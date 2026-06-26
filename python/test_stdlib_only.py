"""Ensure runtime python/ modules import only stdlib or siblings."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parent
PACKAGE_NAME = "larch"


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(PYTHON_DIR).with_suffix("").parts)


def _discover_runtime_modules() -> list[str]:
    paths = [
        p
        for p in PYTHON_DIR.glob("*.py")
        if p.name != "__init__.py" and not p.name.startswith("test_") and p.name != "conftest.py"
    ]
    package_dir = PYTHON_DIR / PACKAGE_NAME
    if package_dir.is_dir():
        paths.extend(
            p
            for p in package_dir.rglob("*.py")
            if p.name != "__init__.py" and not p.name.startswith("test_")
        )
    return sorted(_module_name(p) for p in paths)


RUNTIME_MODULES = _discover_runtime_modules()

# Valid sibling import roots: every top-level module stem (top-level modules are
# importable by bare name) plus the larch package root, since modules inside the
# package import each other via `from larch... import ...` (root `larch`).
SIBLING_ROOTS = frozenset(
    {mod.split(".")[0] for mod in RUNTIME_MODULES} | {PACKAGE_NAME},
)

NON_STDLIB_ALLOWLIST: dict[str, frozenset[str]] = {
    "duplicate_code": frozenset({"astroid", "pylint"}),
}


def _resolve_import(module_name: str, *, package: str | None) -> str:
    if package and not module_name.startswith("."):
        return module_name
    if package and module_name.startswith("."):
        level = len(module_name) - len(module_name.lstrip("."))
        parts = package.split(".")
        base = parts[: -level] if level <= len(parts) else []
        rel = module_name[level:].split(".")
        return ".".join([*base, *rel]).strip(".")
    return module_name


def _collect_imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []

    class Visitor(ast.NodeVisitor):
        def _record_dynamic_import(self, node: ast.Call) -> None:
            if not node.args or not isinstance(node.args[0], ast.Constant):
                return
            if not isinstance(node.args[0].value, str):
                return
            name = node.args[0].value
            if not name:
                return
            found.append((node.lineno, name.split(".")[0]))

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                found.append((node.lineno, alias.name.split(".")[0]))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            pkg = path.stem
            if node.module is None:
                for alias in node.names:
                    found.append((node.lineno, alias.name.split(".")[0]))
                return
            resolved = _resolve_import("." * node.level + node.module, package=pkg)
            found.append((node.lineno, resolved.split(".")[0]))

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                self._record_dynamic_import(node)
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "import_module"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
            ):
                self._record_dynamic_import(node)
            self.generic_visit(node)

    Visitor().visit(tree)
    return found


def test_runtime_modules_are_stdlib_only() -> None:
    stdlib = set(sys.stdlib_module_names)
    violations: list[str] = []
    for mod in RUNTIME_MODULES:
        path = PYTHON_DIR / (mod.replace(".", "/") + ".py")
        for lineno, root in _collect_imports(path):
            if root in stdlib or root in SIBLING_ROOTS:
                continue
            if root in NON_STDLIB_ALLOWLIST.get(mod, frozenset()):
                continue
            violations.append(f"{mod}:{lineno}: {root}")
    assert not violations, "non-stdlib imports:\n" + "\n".join(violations)


def test_runtime_modules_import_cleanly() -> None:
    for mod in RUNTIME_MODULES:
        _ = importlib.import_module(mod)
