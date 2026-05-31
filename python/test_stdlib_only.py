"""Ensure runtime python/ modules import only stdlib or siblings."""

from __future__ import annotations

import ast
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
        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                found.append((node.lineno, alias.name.split(".")[0]))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.module is None:
                return
            pkg = path.stem
            resolved = _resolve_import(node.module, package=pkg)
            found.append((node.lineno, resolved.split(".")[0]))

    Visitor().visit(tree)
    return found


def test_runtime_modules_are_stdlib_only() -> None:
    stdlib = set(sys.stdlib_module_names)
    sibling = {p.stem for p in PYTHON_DIR.glob("*.py")}
    violations: list[str] = []
    for mod in RUNTIME_MODULES:
        path = PYTHON_DIR / f"{mod}.py"
        for lineno, root in _collect_imports(path):
            if root in stdlib or root in sibling:
                continue
            violations.append(f"{mod}.py:{lineno}: {root}")
    assert not violations, "non-stdlib imports:\n" + "\n".join(violations)
