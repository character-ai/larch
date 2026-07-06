from __future__ import annotations

import ast
import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

_TIMING_TASK_KIND_RE = re.compile(r"--timing-task-kind\s+([A-Za-z0-9][A-Za-z0-9_-]*)")

# Minimum path-part counts for scope classification
_SKILL_ROOT_MIN = 2
_SKILL_REF_MIN = 3
_SKILL_SCRIPT_MIN = 4
_PYTHON_PKG_MIN = 2


def in_scope(rel: str) -> bool:
    path = Path(rel)
    parts = path.parts
    if "larch-logs" in parts or "test_fixtures" in parts:
        return False
    if path.name.startswith("test-") or path.name.startswith("test_"):
        return False
    if len(parts) >= _SKILL_ROOT_MIN and parts[0] == "skills" and path.name == "SKILL.md":
        return True
    if len(parts) >= _SKILL_REF_MIN and parts[0] == "skills" and parts[2] == "references" and path.suffix == ".md":
        return True
    if len(parts) >= _SKILL_SCRIPT_MIN and parts[0] == "skills" and parts[2] == "scripts" and path.suffix == ".sh":
        return True
    return len(parts) >= _PYTHON_PKG_MIN and parts[0] == "python" and parts[1] == "larch" and path.suffix == ".py"


def _remember(found: dict[str, set[str]], rel: str, value: str) -> None:
    if value.startswith("-") or any(ch in value for ch in "$<>{}"):
        return
    found.setdefault(value, set()).add(rel)


def _static_string_literals(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
        return [node.value]
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        literals: list[str] = []
        for value in node.values:
            literals.extend(_static_string_literals(value))
        return literals
    if isinstance(node, ast.IfExp):
        return [*_static_string_literals(node.body), *_static_string_literals(node.orelse)]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"get", "getenv"}
        and len(node.args) >= 2  # noqa: PLR2004
    ):
        fallback = node.args[1]
        if isinstance(fallback, ast.Constant) and isinstance(fallback.value, str) and fallback.value:
            return [fallback.value]
    return []


def _check_sequence_node(rel: str, node: ast.List | ast.Tuple, found: dict[str, set[str]]) -> None:
    values = [
        elt.value if isinstance(elt, ast.Constant) and isinstance(elt.value, str) else None
        for elt in node.elts
    ]
    for index, value in enumerate(values[:-1]):
        if value == "--timing-task-kind" and values[index + 1] is not None:
            _remember(found, rel, values[index + 1] or "")


def _check_call_node(rel: str, node: ast.Call, found: dict[str, set[str]]) -> None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_argument":
        return
    if not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value != "--timing-task-kind":
        return
    for keyword in node.keywords:
        if keyword.arg == "default":
            for value in _static_string_literals(keyword.value):
                _remember(found, rel, value)


def _scan_python_source(rel: str, text: str, found: dict[str, set[str]]) -> None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            _check_sequence_node(rel, node, found)
        elif isinstance(node, ast.Call):
            _check_call_node(rel, node, found)


def scan_files(root: Path, rel_paths: Sequence[str]) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for rel in rel_paths:
        if not in_scope(rel):
            continue
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix in {".md", ".sh"}:
            for match in _TIMING_TASK_KIND_RE.finditer(text):
                _remember(found, rel, match.group(1))
            continue
        if path.suffix == ".py":
            _scan_python_source(rel, text, found)
    return found


def missing_allowlist_entries(root: Path, rel_paths: Sequence[str], allowed: set[str]) -> dict[str, list[str]]:
    found = scan_files(root, rel_paths)
    return {kind: sorted(paths) for kind, paths in found.items() if kind not in allowed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m larch.lint.timing_task_kind_allowlist")
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    root = Path(args.root).resolve()
    allowed = set(
        subprocess.check_output(  # lint-subprocess-via-runner: ok lint utility invokes larch CLI to fetch the canonical allow-list
            [sys.executable, str(root / "python/cli.py"), "timing", "task-kinds"], text=True
        ).splitlines()
    )
    tracked = subprocess.check_output(  # lint-subprocess-via-runner: ok lint utility calls git to enumerate tracked files; no proc.Runner needed
        ["git", "-C", str(root), "ls-files"], text=True  # noqa: S607
    ).splitlines()
    missing = missing_allowlist_entries(root, tracked, allowed)
    if missing:
        for kind, paths in sorted(missing.items()):
            print(f"missing TIMING_TASK_KINDS_ALLOWED entry for {kind}: {', '.join(paths)}", file=sys.stderr)
        return 1
    return 0
