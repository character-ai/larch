r"""Reject raw ``[\"gh\", ...]`` argv lists outside the GitHub wrapper.

The wrapper package owns GitHub CLI invocation policy. Test fixtures may retain
intentional raw argv assertions only with a same-line, reason-bearing pragma.
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
EXEMPT_SUBTREE = Path("larch/git")
PRAGMA_RE = re.compile(r"#\s*lint-gh-argv-literal:\s*ok\s+(\S.*)$")


@dataclass(frozen=True)
class Finding:
    file: str
    lineno: int


def iter_source_files(python_dir: Path) -> list[Path]:
    """Return sorted regular, non-symlink Python files in the complete scope."""
    return iter_python_source_files(
        python_dir,
        is_exempt=lambda _path: False,
        excluded_dirs=frozenset(),
        excluded_relpaths=frozenset({EXEMPT_SUBTREE.as_posix()}),
    )


def _is_fixture_pragma(
    finding: Finding, *, comments_by_line: Mapping[int, tuple[str, ...]]
) -> bool:
    return finding.file.startswith("python/tests/") and any(
        PRAGMA_RE.search(comment) for comment in comments_by_line.get(finding.lineno, ())
    )


def _is_raw_gh_argv(node: ast.AST) -> bool:
    if not isinstance(node, ast.List) or not node.elts:
        return False
    first = node.elts[0]
    return isinstance(first, ast.Constant) and first.value == "gh"


def scan_file(path: Path, *, root: Path) -> list[Finding]:
    """Return unsuppressed raw GitHub argv list literals in one source file."""
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
        if not _is_raw_gh_argv(node):
            continue
        lineno = getattr(node, "lineno", 0)
        finding = Finding(file=relative, lineno=lineno if isinstance(lineno, int) else 0)
        if not _is_fixture_pragma(finding, comments_by_line=comments_by_line):
            findings.append(finding)
    return findings


CLI = RuleCli(prog="cli.py lint gh-argv-literal", description=__doc__)


def _run(root: Path) -> int:
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(f"lint-gh-argv-literal: python directory not found: {python_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        findings = [
            finding
            for path in iter_source_files(python_dir)
            for finding in scan_file(path, root=root)
        ]
    except RuntimeError as exc:
        print(f"lint-gh-argv-literal: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    for finding in sorted(findings, key=lambda item: (item.file, item.lineno)):
        print(
            f'{finding.file}: line {finding.lineno} contains raw ["gh", ...] argv; '
            "use larch.git.gh instead",
            file=sys.stderr,
        )
    return 1 if findings else 0


def main(argv: list[str] | None = None) -> int:
    return run_root_cli(argv if argv is not None else sys.argv[1:], cli=CLI, action=_run)


if __name__ == "__main__":
    raise SystemExit(main())
