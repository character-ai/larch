"""Reject em dashes in larch-authored output literals."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from larch.lint import lint_common

EM_DASH = "\u2014"
SUPPRESSION = "lint-em-dash-output: ok"
NAME_SINKS = frozenset({"print", "_emit", "_diag", "_err", "_core_diagnostic"})
LOGGING_UTIL_SINKS = frozenset({"emit", "emit_kv", "diagnostic"})
PRINT_TEMPLATE_RE = re.compile(r"\b(?:P|p)rint:?\s+`([^`\n]*)`")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _repo_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _iter_python_files(root: Path) -> list[Path]:
    source = root / "python" / "larch"
    if not source.is_dir():
        return []
    return sorted(path for path in source.rglob("*.py") if path.is_file() and not path.is_symlink())


def _iter_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for base in (root / "skills", root / "agents"):
        if not base.is_dir():
            continue
        files.extend(path for path in base.rglob("*.md") if path.is_file() and not path.is_symlink())
    return sorted(files)


def _iter_files(root: Path) -> list[Path]:
    return [*_iter_python_files(root), *_iter_markdown_files(root)]


def _suppression_reason(line: str) -> str | None:
    marker = line.find(SUPPRESSION)
    if marker == -1:
        return None
    return line[marker + len(SUPPRESSION) :].strip()


def _suppression_violations(lines: list[str], rel: str) -> list[str]:
    violations: list[str] = []
    for lineno, line in enumerate(lines, start=1):
        reason = _suppression_reason(line)
        if reason == "":
            violations.append(f"{rel}:{lineno}: suppression requires a non-empty reason")
    return violations


def _line_suppresses(lines: list[str], lineno: int) -> bool:
    if not 1 <= lineno <= len(lines):
        return False
    reason = _suppression_reason(lines[lineno - 1])
    return reason is not None and reason != ""


def _callee_is_sink(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id in NAME_SINKS
    if not isinstance(node, ast.Attribute):
        return False
    if node.attr == "write" and isinstance(node.value, ast.Attribute):
        return (
            node.value.attr in {"stdout", "stderr"}
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "sys"
        )
    if node.attr in LOGGING_UTIL_SINKS and isinstance(node.value, ast.Name):
        return node.value.id == "logging_util"
    return node.attr == "emit" and _is_breadcrumb_writer_receiver(node.value)


def _is_breadcrumb_writer_receiver(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute):
            return func.attr == "BreadcrumbWriter" and isinstance(func.value, ast.Name) and func.value.id == "logging_util"
        if isinstance(func, ast.Name):
            return func.id == "BreadcrumbWriter"
    if isinstance(node, ast.Name):
        return node.id in {"breadcrumb_writer", "writer"}
    return False


def _string_literal_parts(node: ast.AST) -> list[tuple[int, str]]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [(node.lineno, node.value)]
    if isinstance(node, ast.JoinedStr):
        return [
            (value.lineno, value.value)
            for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        ]
    return []


def _call_literal_parts(node: ast.Call) -> list[tuple[int, str]]:
    parts: list[tuple[int, str]] = []
    for arg in node.args:
        parts.extend(_string_literal_parts(arg))
    for keyword in node.keywords:
        parts.extend(_string_literal_parts(keyword.value))
    return parts


def _lint_python(path: Path, root: Path, text: str, lines: list[str]) -> list[str]:
    rel = _repo_rel(path, root)
    try:
        tree = ast.parse(text, filename=rel)
    except SyntaxError as exc:
        raise lint_common.LintError(f"{rel}: unable to parse Python: {exc}") from exc
    violations = _suppression_violations(lines, rel)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _callee_is_sink(node.func):
            continue
        for lineno, value in _call_literal_parts(node):
            if EM_DASH in value and not _line_suppresses(lines, lineno):
                violations.append(f"{rel}:{lineno}: em dash in Python output literal")
    return violations


def _is_fence_toggle(line: str) -> bool:
    return FENCE_RE.match(line) is not None


def _lint_markdown(path: Path, root: Path, lines: list[str]) -> list[str]:
    rel = _repo_rel(path, root)
    violations = _suppression_violations(lines, rel)
    in_fence = False
    for lineno, line in enumerate(lines, start=1):
        if _is_fence_toggle(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        suppressed = _line_suppresses(lines, lineno)
        for match in PRINT_TEMPLATE_RE.finditer(line):
            if EM_DASH in match.group(1) and not suppressed:
                violations.append(f"{rel}:{lineno}: em dash in markdown print literal")
        stripped = line.lstrip()
        if stripped.startswith("⏩") and EM_DASH in stripped and not suppressed:
            violations.append(f"{rel}:{lineno}: em dash in markdown status line")
    return violations


def lint_file(*, path: Path, root: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise lint_common.LintError(f"{_repo_rel(path, root)}: non-UTF-8 input") from exc
    except OSError as exc:
        raise lint_common.LintError(f"{_repo_rel(path, root)}: unable to read: {exc}") from exc
    lines = text.splitlines()
    if path.suffix == ".py":
        return _lint_python(path, root, text, lines)
    return _lint_markdown(path, root, lines)


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="cli.py lint em-dash-output",
        description=__doc__,
        iter_files=_iter_files,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
