"""Guard shared ownership of the plan-block marker grammar."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final


RUNTIME_ROOT: Final = Path(__file__).resolve().parents[2] / "larch"
GRAMMAR_OWNER: Final = Path("issue/issue_wire.py")
PLAN_MARKERS: Final = (
    "larch:plan:start",
    "larch:plan:end",
    "<!-- larch:plan:start -->",
    "<!-- larch:plan:end -->",
)
EXCLUDED_PARTS: Final = frozenset({"tests", "fixtures", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"})
REQUIRED_HELPER_CALLS: Final = (
    (Path("design/decompose.py"), "compose_named_block"),
    (Path("design/design_router.py"), "parse_named_block"),
    (Path("issue/learn_from_bugs.py"), "named_block_marker_re"),
)


def _runtime_sources(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*.py"):
        relative: Path = path.relative_to(root)
        if relative == GRAMMAR_OWNER or any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        paths.append(path)
    return sorted(paths)


def _string_literals(path: Path) -> set[str]:
    tree: ast.AST = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _issue_wire_calls(path: Path) -> set[str]:
    tree: ast.AST = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "issue_wire"
    }


def _ownership_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for path in _runtime_sources(root):
        relative: str = path.relative_to(root).as_posix()
        for marker in PLAN_MARKERS:
            if marker in _string_literals(path):
                violations.append(f"{relative}: hardcodes {marker!r}")

    for relative_path, helper in REQUIRED_HELPER_CALLS:
        path: Path = root / relative_path
        relative = relative_path.as_posix()
        if not path.is_file() or helper not in _issue_wire_calls(path):
            violations.append(f"{relative}: missing call issue_wire.{helper}")
    return violations


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")


def _write_required_consumers(root: Path) -> None:
    for relative_path, helper in REQUIRED_HELPER_CALLS:
        _write(root / relative_path, f"issue_wire.{helper}()\n")


def test_runtime_plan_markers_use_the_shared_grammar_owner() -> None:
    violations: list[str] = _ownership_violations(RUNTIME_ROOT)
    assert not violations, "plan marker ownership violations:\n" + "\n".join(violations)


def test_ownership_guard_reports_hardcoded_markers_and_ignores_fixtures(tmp_path: Path) -> None:
    _write_required_consumers(tmp_path)
    _write(tmp_path / "issue/bypass.py", 'MARKER = "<!-- larch:plan:start -->"\n')
    _write(tmp_path / "fixtures/marker_example.py", 'MARKER = "larch:plan:end"\n')
    _write(tmp_path / "tests/marker_example.py", 'MARKER = "larch:plan:end"\n')
    _write(tmp_path / "__pycache__/marker_example.py", 'MARKER = "larch:plan:end"\n')

    violations: list[str] = _ownership_violations(tmp_path)

    assert violations == ["issue/bypass.py: hardcodes '<!-- larch:plan:start -->'"]


def test_ownership_guard_reports_missing_shared_helper_call(tmp_path: Path) -> None:
    _write_required_consumers(tmp_path)
    _write(tmp_path / "design/design_router.py", "issue_wire.compose_named_block()\n")

    violations: list[str] = _ownership_violations(tmp_path)

    assert violations == ["design/design_router.py: missing call issue_wire.parse_named_block"]
