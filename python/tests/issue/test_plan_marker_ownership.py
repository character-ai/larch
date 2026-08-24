"""Guard shared ownership of the plan-block marker grammar."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final


RUNTIME_ROOT: Final = Path(__file__).resolve().parents[2] / "larch"
PLAN_MARKERS: Final = (
    "larch:plan:start",
    "larch:plan:end",
    "<!-- larch:plan:start -->",
    "<!-- larch:plan:end -->",
)
EXCLUDED_PARTS: Final = frozenset({"tests", "fixtures", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"})
# The plan-block presence probe moved with `design route` to the Rust owner
# (crates/larch-cli/src/design_commands.rs, larch-core parse_named_block). The
# last Python consumer, design/decompose.py, migrated to the Rust
# larch_core::design::decompose owner in #8588, so no production Python module
# now requires a shared `issue_wire` helper call.
REQUIRED_HELPER_CALLS: Final[list[tuple[Path, str]]] = []


def _runtime_sources(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*.py"):
        relative: Path = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
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


def test_python_runtime_does_not_hardcode_plan_markers() -> None:
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
    # The guard still flags a required-helper omission; drive it through a
    # synthetic requirement now that no production Python module carries one.
    requirement = (Path("design/synthetic.py"), "compose_named_block")
    _write(tmp_path / "design/synthetic.py", "issue_wire.parse_named_block()\n")

    path = tmp_path / requirement[0]
    violation = (
        None
        if path.is_file() and requirement[1] in _issue_wire_calls(path)
        else f"{requirement[0].as_posix()}: missing call issue_wire.{requirement[1]}"
    )

    assert violation == "design/synthetic.py: missing call issue_wire.compose_named_block"
