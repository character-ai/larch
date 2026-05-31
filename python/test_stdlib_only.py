"""Ensure runtime python/ modules import only stdlib or siblings."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parent
RUNTIME_MODULES = sorted(
    p.stem
    for p in PYTHON_DIR.glob("*.py")
    if p.name != "__init__.py" and not p.name.startswith("test_")
)


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
    sibling = set(RUNTIME_MODULES)
    violations: list[str] = []
    for mod in RUNTIME_MODULES:
        path = PYTHON_DIR / f"{mod}.py"
        for lineno, root in _collect_imports(path):
            if root in stdlib or root in sibling:
                continue
            violations.append(f"{mod}.py:{lineno}: {root}")
    assert not violations, "non-stdlib imports:\n" + "\n".join(violations)


def test_runtime_modules_import_cleanly() -> None:
    for mod in RUNTIME_MODULES:
        _ = importlib.import_module(mod)
