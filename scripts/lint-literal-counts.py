#!/usr/bin/env python3
"""Lint markdown for drift-prone literal item counts.

Flags lines matching ``^\\s*\\d+\\s+(assertions|rules|bullets|rows|reviewers|
agents|specialists|cases|fields|sections)\\b`` unless the same line carries
``<!-- lint-literal-counts: allow <reason> -->``. Lines inside length-aware
fenced code blocks are exempt. Exit codes: 0 clean, 1 violations, 2 internal
errors. Canonical contract: scripts/lint-literal-counts.md.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

VIOLATION_REGEX = re.compile(
    r"^\s*\d+\s+(assertions|rules|bullets|rows|reviewers|agents|specialists|cases|fields|sections)\b",
    re.ASCII,
)
ALLOW_PRAGMA_REGEX = re.compile(
    r"<!--\s*lint-literal-counts:\s*allow\s+(\S.*?)\s*-->"
)
CODE_FENCE_REGEX = re.compile(r"^(\s*)(`{3,})")

EXCLUDED_DIRS = {".git", "node_modules", ".venv", ".agents"}


class LintError(Exception):
    """Raised for internal errors (file unreadable, non-UTF-8 bytes). Exit 2."""


def is_git_worktree(root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def iter_markdown_files(root: Path) -> list[Path]:
    """Return markdown files under root in deterministic order.

    Git worktrees use `git ls-files` so ignored/untracked trees are skipped.
    Non-git fixture roots use os.walk with explicit directory exclusions and
    symlink files skipped so targets outside the tree are never followed.
    """
    if is_git_worktree(root):
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "-z",
                    "--",
                    "*.md",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            detail = e.stderr.decode("utf-8", errors="replace").strip()
            raise LintError(f"lint-literal-counts: cannot enumerate markdown files: {detail}") from e
        files = [
            root / rel.decode("utf-8")
            for rel in result.stdout.split(b"\0")
            if rel
        ]
        return sorted(path for path in files if not path.is_symlink())

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for filename in sorted(filenames):
            if not filename.endswith(".md"):
                continue
            path = Path(dirpath) / filename
            if path.is_symlink():
                continue
            files.append(path)
    return sorted(files)


def lint_file(path: Path, root: Path) -> list[str]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to scan (default: this script's parent directory).",
    )
    args = parser.parse_args()

    root: Path = args.root.resolve()
    if not root.is_dir():
        print(f"lint-literal-counts: --root is not a directory: {root}", file=sys.stderr)
        return 2

    violations: list[str] = []
    errors: list[str] = []
    try:
        files = iter_markdown_files(root)
    except LintError as e:
        errors.append(str(e))
        files = []

    for path in files:
        try:
            violations.extend(lint_file(path, root))
        except LintError as e:
            errors.append(str(e))

    for error in errors:
        print(error, file=sys.stderr)
    for violation in violations:
        print(violation, file=sys.stderr)
    if errors:
        return 2
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
