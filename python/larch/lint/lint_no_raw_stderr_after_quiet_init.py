# ruff: noqa: PLR2004,SIM103
"""Lint shell scripts for raw stderr writes after larch_quiet_init.

S041/no-raw-stderr-after-quiet-init flags post-init echo/printf/cat writes to
FD 2. After quiet init, user-visible diagnostics must use larch_err or
larch_errf so they reach the caller's original stderr instead of the quiet log.
Exit codes: 0 clean, 1 violations, 2 internal errors. Canonical contract:
python/lint_no_raw_stderr_after_quiet_init.md.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

QUIET_INIT_RE = re.compile(r"^\s*larch_quiet_init(?:\s|;|$)")
RAW_STDERR_RE = re.compile(r">\s*&2")
DIAGNOSTIC_CMD_RE = re.compile(r"(?:^|[;&|({])\s*(echo|printf|cat)(?:\s|$)")
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

EXCLUDED_DIRS = {".git", "node_modules", ".venv", ".agents"}


def is_scoped_shell_path( *,path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    if rel.suffix != ".sh":
        return False
    parts = rel.parts
    if not parts:
        return False
    if parts[0] in {"scripts", "hooks"}:
        return True
    return len(parts) >= 4 and parts[0] == "skills" and parts[2] == "scripts"


def iter_shell_files(root: Path) -> list[Path]:
    """Return scoped shell files under root in deterministic order."""
    if lint_common.git_rooted(root):
        files = lint_common.git_ls_files_z(
            root=root, pattern="*.sh", error_prefix="lint-no-raw-stderr-after-quiet-init: cannot enumerate shell files"
        )
        return sorted(
            path
            for path in files
            if path.is_file() and not path.is_symlink() and is_scoped_shell_path(path=path, root=root)
        )

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if path.is_symlink() or not is_scoped_shell_path(path=path, root=root):
                continue
            files.append(path)
    return sorted(files)


def unquoted_shell_code(line: str) -> str:
    """Return line text with quoted strings and trailing comments blanked."""
    out: list[str] = []
    i = 0
    quote = ""
    while i < len(line):
        ch = line[i]
        if quote:
            out.append(" ")
            if ch == "\\" and quote == '"' and i + 1 < len(line):
                out.append(" ")
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            out.append(" ")
            i += 1
            continue
        if ch == "#":
            out.extend(" " for _ in line[i:])
            break
        out.append(ch)
        i += 1
    return "".join(out)


def heredoc_delimiter(line: str) -> str | None:
    match = HEREDOC_RE.search(line)
    if not match:
        return None
    return match.group(2)


def is_quiet_init_line(code: str) -> bool:
    stripped = code.strip()
    if not QUIET_INIT_RE.match(code):
        return False
    if stripped.startswith("function ") or "()" in stripped:
        return False
    return True


def lint_file( *,path: Path, root: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise LintError(
            f"lint-no-raw-stderr-after-quiet-init: {path}: cannot read file: {e}"
        ) from e

    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path

    violations: list[str] = []
    after_quiet_init = False
    pending_heredoc: str | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        if pending_heredoc is not None:
            if line.strip() == pending_heredoc:
                pending_heredoc = None
            continue

        code = unquoted_shell_code(line)
        if not after_quiet_init:
            if is_quiet_init_line(code):
                after_quiet_init = True
            delimiter = heredoc_delimiter(line)
            if delimiter:
                pending_heredoc = delimiter
            continue

        if (
            RAW_STDERR_RE.search(code)
            and DIAGNOSTIC_CMD_RE.search(code)
            and "larch_err" not in code
        ):
            violations.append(
                f"lint-no-raw-stderr-after-quiet-init: {rel}:{line_number}: "
                "S041/no-raw-stderr-after-quiet-init: raw echo/printf/cat "
                "stderr after larch_quiet_init; use larch_err/larch_errf"
            )

        delimiter = heredoc_delimiter(line)
        if delimiter:
            pending_heredoc = delimiter

    return violations


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-no-raw-stderr-after-quiet-init",
        description=(__doc__ or "").splitlines()[0],
        iter_files=iter_shell_files,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    sys.exit(main())
