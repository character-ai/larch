# ruff: noqa: D301
"""Lint markdown for drift-prone literal item counts.

Flags lines matching ``^\\s*\\d+\\s+(assertions|rules|bullets|rows|reviewers|
agents|specialists|cases|fields|sections)\\b`` unless the same line carries
``<!-- lint-literal-counts: allow <reason> -->``. Lines inside length-aware
fenced code blocks are exempt. Exit codes: 0 clean, 1 violations, 2 internal
errors. Canonical contract: python/lint_literal_counts.md.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

VIOLATION_REGEX = re.compile(
    r"^\s*\d+\s+(assertions|rules|bullets|rows|reviewers|agents|specialists|cases|fields|sections)\b",
    re.ASCII,
)
ALLOW_PRAGMA_REGEX = re.compile(
    r"<!--\s*lint-literal-counts:\s*allow\s+(\S.*?)\s*-->"
)
CODE_FENCE_REGEX = re.compile(r"^(\s*)(`{3,})")

EXCLUDED_DIRS = {".git", "node_modules", ".venv", ".agents"}


def iter_markdown_files(root: Path) -> list[Path]:
    """Return markdown files under root in deterministic order.

    Git worktrees use `git ls-files` so ignored/untracked trees are skipped.
    Non-git fixture roots use os.walk with explicit directory exclusions and
    symlink files skipped so targets outside the tree are never followed.
    """
    if lint_common.git_rooted(root):
        files = [
            path
            for path in lint_common.git_ls_files_z(
                root=root, pattern="*.md", error_prefix="lint-literal-counts: cannot enumerate markdown files"
            )
            if not path.relative_to(root).as_posix().startswith("larch-logs/")
        ]
        return sorted(path for path in files if path.is_file() and not path.is_symlink())

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for filename in sorted(filenames):
            if not filename.endswith(".md"):
                continue
            path = Path(dirpath) / filename
            if path.is_symlink():
                continue
            try:
                rel = path.relative_to(root)
            except ValueError:
                rel = path
            if rel.parts and rel.parts[0] == "larch-logs":
                continue
            files.append(path)
    return sorted(files)


def lint_file( *,path: Path, root: Path) -> list[str]:
    """Return violation messages for one markdown file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise LintError(f"lint-literal-counts: {path}: cannot read file: {e}") from e

    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path

    violations: list[str] = []
    in_fence = False
    fence_indent = ""
    fence_len = 0

    for line_number, line in enumerate(text.split("\n"), start=1):
        fence_match = CODE_FENCE_REGEX.match(line)
        if fence_match:
            indent, marker = fence_match.groups()
            marker_len = len(marker)
            if not in_fence:
                in_fence = True
                fence_indent = indent
                fence_len = marker_len
                continue
            if indent == fence_indent and marker_len >= fence_len:
                in_fence = False
                fence_indent = ""
                fence_len = 0
                continue

        if in_fence:
            continue
        if not VIOLATION_REGEX.search(line):
            continue
        if ALLOW_PRAGMA_REGEX.search(line):
            continue
        violations.append(
            f"lint-literal-counts: {rel}:{line_number}: literal item count drifts "
            "when the underlying count changes - prefer structural prose "
            '(e.g., "the panel", "the reviewer set") or add '
            "`<!-- lint-literal-counts: allow <reason> -->` on the same line "
            "if the count is fixed/historical"
        )

    return violations


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-literal-counts",
        description=(__doc__ or "").splitlines()[0],
        iter_files=iter_markdown_files,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    sys.exit(main())
