r"""Require explicit destination refspecs in raw ``["git", "push", ...]`` argv lists.

Git resolves a refspec-less push through ambient ``push.default`` and upstream
tracking. Test fixtures may suppress an intentional exception with a same-line,
reason-bearing pragma.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from larch.lint.engine import RuleCli, comment_tokens_by_line, iter_python_source_files, run_root_cli

TOOL_FAILURE_EXIT = 2
PUSH_COMMAND_ELEMENTS = 2
EXPLICIT_PUSH_OPERANDS = 2
PRAGMA_RE = re.compile(r"#\s*lint-git-push-refspec:\s*ok\s+(\S.*)$")


@dataclass(frozen=True)
class Finding:
    file: str
    lineno: int


def _is_fixture_pragma(
    finding: Finding, *, comments_by_line: Mapping[int, tuple[str, ...]]
) -> bool:
    return finding.file.startswith("python/tests/") and any(
        PRAGMA_RE.search(comment) for comment in comments_by_line.get(finding.lineno, ())
    )


def _static_prefix(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if not isinstance(node, ast.JoinedStr):
        return None
    prefix = ""
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            prefix += value.value
        else:
            break
    return prefix


def _is_raw_git_push_argv(node: ast.AST) -> bool:
    if not isinstance(node, ast.List) or len(node.elts) < PUSH_COMMAND_ELEMENTS:
        return False
    return _static_prefix(node.elts[0]) == "git" and _static_prefix(node.elts[1]) == "push"


def _has_explicit_refspec(node: ast.List) -> bool:
    operands = 0
    for element in node.elts[PUSH_COMMAND_ELEMENTS:]:
        static_prefix = _static_prefix(element)
        if static_prefix is not None and static_prefix.startswith("-"):
            continue
        operands += 1
    return operands >= EXPLICIT_PUSH_OPERANDS


def scan_file(path: Path, *, root: Path) -> list[Finding]:
    """Return raw Git push argv lists without an explicit refspec operand."""
    relative = path.relative_to(root).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"{relative}: cannot read source: {exc}") from exc
    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError as exc:
        raise RuntimeError(f"{relative}: cannot parse source: {exc}") from exc
    comments_by_line = comment_tokens_by_line(source)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.List) or not _is_raw_git_push_argv(node) or _has_explicit_refspec(node):
            continue
        lineno = getattr(node, "lineno", 0)
        finding = Finding(file=relative, lineno=lineno if isinstance(lineno, int) else 0)
        if not _is_fixture_pragma(finding, comments_by_line=comments_by_line):
            findings.append(finding)
    return findings


CLI = RuleCli(prog="cli.py lint git-push-refspec", description=__doc__)


def _run(root: Path) -> int:
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(f"lint-git-push-refspec: python directory not found: {python_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        findings = [
            finding
            for path in iter_python_source_files(
                python_dir,
                is_exempt=lambda _path: False,
                excluded_dirs=frozenset(),
            )
            for finding in scan_file(path, root=root)
        ]
    except RuntimeError as exc:
        print(f"lint-git-push-refspec: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    for finding in sorted(findings, key=lambda item: (item.file, item.lineno)):
        print(
            f"{finding.file}: line {finding.lineno} contains git push without an explicit refspec",
            file=sys.stderr,
        )
    return 1 if findings else 0


def main(argv: list[str] | None = None) -> int:
    return run_root_cli(argv if argv is not None else sys.argv[1:], cli=CLI, action=_run)


if __name__ == "__main__":
    raise SystemExit(main())
