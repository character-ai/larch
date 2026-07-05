"""Reject em dashes in larch-authored output literals."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from larch.lint import lint_common

EM_DASH = "\u2014"
SUPPRESSION = "lint-em-dash-output: ok"
NAME_SINKS = frozenset(
    {
        "print",
        "_emit",
        "_diag",
        "_err",
        "_core_diagnostic",
        "emit",
        "emit_kv",
        "diagnostic",
        "_plain_diagnostic",
        "_emit_kv",
    }
)
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


def _assignment_targets(node: ast.AST) -> list[ast.Name]:
    if isinstance(node, ast.Assign):
        candidates = node.targets
    elif isinstance(node, ast.AnnAssign):
        candidates = [node.target]
    else:
        return []
    return [target for target in candidates if isinstance(target, ast.Name)]


def _is_logging_util_sink_reference(node: ast.AST, logging_util_names: set[str]) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in logging_util_names
        and node.attr in LOGGING_UTIL_SINKS
    )


def _is_breadcrumb_writer_constructor(
    node: ast.AST,
    logging_util_names: set[str],
    constructor_names: set[str],
) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr == "BreadcrumbWriter" and isinstance(func.value, ast.Name) and func.value.id in logging_util_names
    if isinstance(func, ast.Name):
        return func.id in constructor_names
    return False


def _collect_sink_metadata(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    logging_util_names = {"logging_util"}
    sink_names = set(NAME_SINKS)
    breadcrumb_writer_names = {"BreadcrumbWriter", "breadcrumb_writer", "writer"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "larch.core.logging_util":
                    logging_util_names.add(alias.asname or alias.name.rsplit(".", maxsplit=1)[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.module == "larch.core":
                for alias in node.names:
                    if alias.name == "logging_util":
                        logging_util_names.add(alias.asname or alias.name)
            elif node.module == "larch.core.logging_util":
                for alias in node.names:
                    target = alias.asname or alias.name
                    if alias.name in LOGGING_UTIL_SINKS:
                        sink_names.add(target)
                    elif alias.name == "BreadcrumbWriter":
                        breadcrumb_writer_names.add(target)
    assignments = [node for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.AnnAssign))]
    changed = True
    while changed:
        changed = False
        for node in assignments:
            value = node.value
            if value is None:
                continue
            targets = _assignment_targets(node)
            if not targets:
                continue
            if isinstance(value, ast.Name) and value.id in breadcrumb_writer_names:
                for target in targets:
                    if target.id not in breadcrumb_writer_names:
                        breadcrumb_writer_names.add(target.id)
                        changed = True
                continue
            if _is_breadcrumb_writer_constructor(value, logging_util_names, breadcrumb_writer_names):
                for target in targets:
                    if target.id not in breadcrumb_writer_names:
                        breadcrumb_writer_names.add(target.id)
                        changed = True
                continue
            if _is_logging_util_sink_reference(value, logging_util_names) or (
                isinstance(value, ast.Name) and value.id in sink_names
            ):
                for target in targets:
                    if target.id not in sink_names:
                        sink_names.add(target.id)
                        changed = True
    return sink_names, breadcrumb_writer_names, logging_util_names


def _callee_is_sink(
    node: ast.AST,
    *,
    sink_names: set[str],
    breadcrumb_writer_names: set[str],
    logging_util_names: set[str],
) -> bool:
    if isinstance(node, ast.Name):
        return node.id in sink_names
    if not isinstance(node, ast.Attribute):
        return False
    if node.attr == "write" and isinstance(node.value, ast.Attribute):
        return (
            node.value.attr in {"stdout", "stderr"}
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "sys"
        )
    if node.attr == "emit" and _is_breadcrumb_writer_receiver(
        node.value,
        breadcrumb_writer_names,
        logging_util_names,
    ):
        return True
    if node.attr in LOGGING_UTIL_SINKS and isinstance(node.value, ast.Name):
        return node.value.id in logging_util_names
    return False


def _is_breadcrumb_writer_receiver(
    node: ast.AST,
    breadcrumb_writer_names: set[str],
    logging_util_names: set[str],
) -> bool:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute):
            return func.attr == "BreadcrumbWriter" and isinstance(func.value, ast.Name) and func.value.id in logging_util_names
        if isinstance(func, ast.Name):
            return func.id in breadcrumb_writer_names
    if isinstance(node, ast.Name):
        return node.id in breadcrumb_writer_names
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
    sink_names, breadcrumb_writer_names, logging_util_names = _collect_sink_metadata(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _callee_is_sink(
            node.func,
            sink_names=sink_names,
            breadcrumb_writer_names=breadcrumb_writer_names,
            logging_util_names=logging_util_names,
        ):
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
        if line.lstrip().startswith(">"):
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
