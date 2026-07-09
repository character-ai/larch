"""Reject direct architectural-guidelines note invalidation outside its owner.

The ship-guidelines owner module owns the pin-or-invalidate sequence. Other
production modules must call ``_pin_or_invalidate_guidelines_note`` rather than
bypassing the re-pin attempt with ``_invalidate_guidelines_note``.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

TOOL_FAILURE_EXIT = 2
TARGET_CALLEE = "_invalidate_guidelines_note"
WRAPPER_CALLEE = "_pin_or_invalidate_guidelines_note"
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__", "tests"})
OWNER_RELPATH = "larch/implement/ship_guidelines.py"
LINT_MODULE_RELPATH = "larch/lint/lint_guidelines_note_wrapper_bypass.py"
PRAGMA_RE = re.compile(r"#\s*lint-guidelines-note-wrapper-bypass:\s*ok\s+(\S.*)$")


@dataclass(frozen=True)
class Finding:
    file: str
    lineno: int


def is_exempt_path(path: Path) -> bool:
    """Return whether a Python path is outside production lint scope."""
    name: str = path.name
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def iter_source_files(larch_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under larch/, sorted."""
    result: list[Path] = []
    for path in sorted(larch_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink() or is_exempt_path(path):
            continue
        relative: Path = path.relative_to(larch_dir.parent)
        normalized: str = relative.as_posix()
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        if normalized in {OWNER_RELPATH, LINT_MODULE_RELPATH}:
            continue
        result.append(path)
    return result


def _comment_tokens_by_line(source: str) -> dict[int, tuple[str, ...]]:
    comments: dict[int, list[str]] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.setdefault(token.start[0], []).append(token.string)
    except tokenize.TokenError:
        return {}
    return {line: tuple(values) for line, values in comments.items()}


def _is_suppressed(finding: Finding, *, comments_by_line: Mapping[int, tuple[str, ...]]) -> bool:
    return any(PRAGMA_RE.search(comment) for comment in comments_by_line.get(finding.lineno, ()))


def _is_target_call(node: ast.Call) -> bool:
    func: ast.expr = node.func
    if isinstance(func, ast.Name):
        return func.id == TARGET_CALLEE
    if isinstance(func, ast.Attribute):
        return func.attr == TARGET_CALLEE
    return False


def scan_file(path: Path, *, larch_dir: Path) -> list[Finding]:
    """Return direct guidelines-note invalidation calls for one source file."""
    normalized_file: str = path.relative_to(larch_dir.parent).as_posix()
    try:
        source: str = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"{normalized_file}: cannot read source: {exc}") from exc
    try:
        tree: ast.Module = ast.parse(source)
    except SyntaxError as exc:
        raise RuntimeError(f"{normalized_file}: cannot parse source: {exc}") from exc
    comments_by_line: dict[int, tuple[str, ...]] = _comment_tokens_by_line(source)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_target_call(node):
            continue
        lineno_value: object = getattr(node, "lineno", 0)
        lineno: int = lineno_value if isinstance(lineno_value, int) else 0
        finding = Finding(file=normalized_file, lineno=lineno)
        if not _is_suppressed(finding, comments_by_line=comments_by_line):
            findings.append(finding)
    return findings


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint guidelines-note-wrapper-bypass", description=__doc__
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    parsed: argparse.Namespace | None = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root: Path = Path(str(parsed.root)).resolve()
    larch_dir: Path = root / "python" / "larch"
    if not larch_dir.is_dir():
        print(
            f"lint-guidelines-note-wrapper-bypass: larch directory not found: {larch_dir}",
            file=sys.stderr,
        )
        return TOOL_FAILURE_EXIT
    findings: list[Finding] = []
    try:
        for path in iter_source_files(larch_dir):
            findings.extend(scan_file(path, larch_dir=larch_dir))
    except RuntimeError as exc:
        print(f"lint-guidelines-note-wrapper-bypass: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    for finding in sorted(findings, key=lambda item: (item.file, item.lineno)):
        print(
            f"{finding.file}: line {finding.lineno} calls {TARGET_CALLEE}; "
            f"use {WRAPPER_CALLEE} instead",
            file=sys.stderr,
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
