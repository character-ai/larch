"""Reject raw Codex CLI dispatch call sites without shared auth wiring."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from larch.lint.engine import RuleCli, run_root_cli
from larch.lint.lint_common import GIT, git_rooted

ALLOWED_PYTHON_FILES = {"python/larch/agents/agents.py"}
REVIEW_CORE_SUBPROCESS_RE = re.compile(
    r'["\']review["\']\s*,\s*["\']core["\']|python/cli\.py review core|cli\.py review core'
)
TRAILING_PRAGMA_RE = re.compile(r"\s#[^\"'`]*lint-codex-exec-auth:\s*ok(\s|$)[^\"'`]*$")
PY_CODEX_EXEC_RE = re.compile(r"(['\"]codex['\"]\s*,\s*['\"]exec['\"]|['\"]codex\s+exec\b)")


def _git_files( *,root: Path, patterns: list[str]) -> list[str]:
    proc = subprocess.run(
        [GIT, "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", *patterns],
        check=False,
        stdout=subprocess.PIPE,
    )
    return [p.decode() for p in proc.stdout.split(b"\0") if p and not p.decode().startswith("larch-logs/")]


def _python_files(root: Path) -> list[str]:
    if git_rooted(root):
        candidates = _git_files(root=root, patterns=["python/**/*.py"])
    else:
        candidates = [str(path.relative_to(root)) for path in (root / "python").glob("**/*.py") if path.is_file()]
    return [p for p in candidates if not Path(p).name.startswith("test_")]


def scan_review_and_fix_review_core(root: Path) -> bool:
    rels = [
        "python/larch/review/review_and_fix.py",
        "python/larch/review/round_runner.py",
    ]
    violation = False
    for rel in rels:
        path = root / rel
        if not path.is_file() or path.is_symlink():
            continue
        for nr, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if TRAILING_PRAGMA_RE.search(line) or re.match(r"^\s*#", line):
                continue
            if REVIEW_CORE_SUBPROCESS_RE.search(line):
                print(
                    f"lint-codex-exec-auth: {rel}:{nr}: Step 5 must not subprocess review core; use review_core_capture / review_core_body.review_core",
                    file=sys.stderr,
                )
                violation = True
    return violation


def scan_python_file( *,root: Path, rel: str) -> bool:
    if rel in ALLOWED_PYTHON_FILES:
        return False
    path = root / rel
    if not path.is_file() or path.is_symlink():
        return False
    violation = False
    for nr, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if TRAILING_PRAGMA_RE.search(line) or re.match(r"^\s*#", line):
            continue
        if PY_CODEX_EXEC_RE.search(line):
            print(
                f"lint-codex-exec-auth: {rel}:{nr}: unwired Python Codex dispatch without auth wiring; use python3 python/cli.py agent launch-codex-exec or # lint-codex-exec-auth: ok <reason>",
                file=sys.stderr,
            )
            violation = True
    return violation


CLI = RuleCli(
    prog="cli.py lint codex-exec-auth", description=__doc__, resolve_root=False
)


def _run(root: Path) -> int:
    if not root.is_dir():
        print(f"lint-codex-exec-auth: --root is not a directory: {root}", file=sys.stderr)
        return 2
    root = root.resolve()
    violations = 0
    if scan_review_and_fix_review_core(root):
        violations += 1
    for rel in _python_files(root):
        if scan_python_file(root=root, rel=rel):
            violations += 1
    return 1 if violations else 0


def main(argv: list[str] | None = None) -> int:
    return run_root_cli(argv if argv is not None else sys.argv[1:], cli=CLI, action=_run)


if __name__ == "__main__":
    raise SystemExit(main())
