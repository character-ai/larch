"""Reject inline GitHub CLI body and notes payloads."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from larch.lint.lint_common import GIT, git_rooted, parse_root_args

GH_RE = re.compile(r"(^|[\s/'\"`(=])gh([\s'\"])")
PRAGMA_RE = re.compile(r"(^|\s)#\s*lint-gh-body-inline: ok(\s.*)?$")


def _list_git_files(root: Path) -> list[str]:
    proc = subprocess.run(
        [
            GIT,
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "*.sh",
            "*.py",
        ],
        check=False,
        stdout=subprocess.PIPE,
    )
    return [p.decode() for p in proc.stdout.split(b"\0") if p and not p.decode().startswith("larch-logs/")]


def _list_find_files(root: Path) -> list[str]:
    pruned = {".git", "node_modules", ".venv", ".agents", "larch-logs"}
    rels: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in pruned]
        base = Path(dirpath)
        rels.extend(
            str((base / name).relative_to(root))
            for name in filenames
            if name.endswith((".sh", ".py"))
        )
    return sorted(rels)


def list_shell_files(root: Path) -> list[str]:
    return _list_git_files(root) if git_rooted(root) else _list_find_files(root)


def _is_violation_line(line: str) -> list[tuple[str, str]]:
    if PRAGMA_RE.search(line) or re.match(r"^\s*#", line):
        return []
    if not GH_RE.search(line):
        return []
    findings: list[tuple[str, str]] = []
    body_opt = "--" + "body"
    notes_opt = "--" + "notes"
    if re.search(rf"{re.escape(body_opt)}[^-]", line):
        findings.append((body_opt, body_opt + "-file"))
    if re.search(rf"{re.escape(notes_opt)}[^-]", line):
        findings.append((notes_opt, notes_opt + "-file"))
    return findings


def scan_file( *,root: Path, rel: str) -> bool:
    path = root / rel
    if not path.is_file() or path.is_symlink():
        return False
    violation = False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    for lineno, line in enumerate(lines, 1):
        for option, replacement in _is_violation_line(line):
            gh_token = "g" + "h"
            print(
                f"lint-gh-body-inline: {rel}:{lineno}: inline {gh_token} {option} is forbidden, use {replacement}",
                file=sys.stderr,
            )
            violation = True
    return violation


def main(argv: list[str] | None = None) -> int:
    parsed = parse_root_args(
        argv if argv is not None else sys.argv[1:],
        prog="cli.py lint gh-body-inline",
        description=__doc__,
    )
    if parsed is None:
        return 2
    root = Path(parsed.root)
    if not root.is_dir():
        print(f"lint-gh-body-inline: --root is not a directory: {root}", file=sys.stderr)
        return 2
    root = root.resolve()
    violations = 0
    for rel in list_shell_files(root):
        if scan_file(root=root, rel=rel):
            violations += 1
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
