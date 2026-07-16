"""Shared helpers for python/lint_*.py file-scanning linters."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from larch.lint.engine import RuleCli, run_root_cli

GIT = shutil.which("git") or "git"


class LintError(Exception):
    """Raised for internal errors (file unreadable, non-UTF-8 bytes). Exit 2."""


def git_rooted(root: Path) -> bool:
    """True when ``root`` is inside a git work tree."""
    return subprocess.run(
        [GIT, "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def git_ls_files_z( *,root: Path, pattern: str, error_prefix: str) -> list[Path]:
    """Return tracked + untracked, non-ignored files matching ``pattern``.

    Runs ``git ls-files --cached --others --exclude-standard -z -- <pattern>``
    under ``root`` and returns ``root``-joined paths in git's order. Raises
    :class:`LintError` (message prefixed with ``error_prefix``) when git exits
    non-zero. Callers apply their own ``is_file``/symlink/scope filtering.
    """
    try:
        result = subprocess.run(
            [GIT, "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", pattern],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise LintError(f"{error_prefix}: {detail}") from exc
    return [root / rel.decode("utf-8") for rel in result.stdout.split(b"\0") if rel]


def run_file_lint(
    argv: list[str] | None,
    *,
    prog: str,
    description: str | None,
    iter_files: Callable[[Path], list[Path]],
    lint_file: Callable[..., list[str]],
) -> int:
    """Shared driver for ``--root`` file-scanning linters.

    Resolves ``--root``, enumerates files via ``iter_files``, runs ``lint_file``
    per file, then prints internal errors followed by violations to stderr.
    Returns the standard exit code: 0 clean, 1 violations, 2 internal/usage
    errors (errors win over violations). ``iter_files`` and ``lint_file`` raise
    :class:`LintError` to report internal failures.
    """
    def action(root: Path) -> int:
        if not root.is_dir():
            print(f"{prog}: --root is not a directory: {root}", file=sys.stderr)
            return 2

        violations: list[str] = []
        errors: list[str] = []
        try:
            files = iter_files(root)
        except LintError as exc:
            errors.append(str(exc))
            files = []

        for path in files:
            try:
                violations.extend(lint_file(path=path, root=root))
            except LintError as exc:
                errors.append(str(exc))

        for error in errors:
            print(error, file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        if errors:
            return 2
        return 1 if violations else 0

    return run_root_cli(
        argv if argv is not None else sys.argv[1:],
        cli=RuleCli(prog=prog, description=description),
        action=action,
    )
