"""Reject raw Codex CLI dispatch call sites without shared auth wiring."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from larch.lint.lint_common import GIT, git_rooted, parse_root_args

ALLOWED_SHELL_FILES: set[str] = set()
ALLOWED_PYTHON_FILES = {"python/larch/agents/agents.py"}
REVIEW_CORE_SUBPROCESS_RE = re.compile(
    r'["\']review["\']\s*,\s*["\']core["\']|python/cli\.py review core|cli\.py review core'
)
TRAILING_PRAGMA_RE = re.compile(r"\s#[^\"'`]*lint-codex-exec-auth:\s*ok(\s|$)[^\"'`]*$")
CODEX_EXEC_RE = re.compile(r"(^|[^A-Za-z0-9_])[\"'\\]?codex[\"'\\]?\s+exec")
PY_CODEX_EXEC_RE = re.compile(r"(['\"]codex['\"]\s*,\s*['\"]exec['\"]|['\"]codex\s+exec\b)")
ENV_PREFIX_RE = re.compile(r"^([\s]*[A-Za-z_][A-Za-z0-9_]*=[^\s]*\s*)+")


def _git_files( *,root: Path, patterns: list[str]) -> list[str]:
    proc = subprocess.run(
        [GIT, "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", *patterns],
        check=False,
        stdout=subprocess.PIPE,
    )
    return [p.decode() for p in proc.stdout.split(b"\0") if p and not p.decode().startswith("larch-logs/")]


def _shell_files(root: Path) -> list[str]:
    if git_rooted(root):
        candidates = _git_files(root=root, patterns=["scripts/*.sh", "skills/*/scripts/*.sh"])
    else:
        candidates: list[str] = []
        for base in (root / "scripts", root / "skills"):
            if base.exists():
                candidates.extend([str(path.relative_to(root)) for path in base.glob("**/*.sh") if path.is_file()])
    return [p for p in candidates if not (Path(p).name.startswith("test-") and p.endswith(".sh"))]


def _python_files(root: Path) -> list[str]:
    if git_rooted(root):
        candidates = _git_files(root=root, patterns=["python/*.py"])
    else:
        candidates = [str(path.relative_to(root)) for path in (root / "python").glob("*.py") if path.is_file()]
    return [p for p in candidates if not Path(p).name.startswith("test_")]


def _markdown_files(root: Path) -> list[str]:
    if git_rooted(root):
        return _git_files(root=root, patterns=["skills/**/*.md", ".claude/skills/**/*.md", ".claude/rules/*.md"])
    rels: list[str] = []
    for base in (root / "skills", root / ".claude" / "skills", root / ".claude" / "rules"):
        if base.exists():
            rels.extend([str(path.relative_to(root)) for path in base.glob("**/*.md") if path.is_file()])
    return rels


def _has_codex_exec(line: str) -> bool:
    return CODEX_EXEC_RE.search(line) is not None


def _scan_command(line: str) -> bool:
    if TRAILING_PRAGMA_RE.search(line) or re.match(r"^\s*#", line):
        return False
    if _has_codex_exec(line):
        return True
    stripped = ENV_PREFIX_RE.sub("", line)
    return _has_codex_exec(stripped)


def _logical_lines(lines: list[str]) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    pending = ""
    pending_nr = 0
    for lineno, raw in enumerate(lines, 1):
        line = f"{pending}{raw}" if pending else raw
        nr = pending_nr or lineno
        pending = ""
        pending_nr = 0
        if re.search(r"\\\s*$", line):
            pending = re.sub(r"\\\s*$", " ", line)
            pending_nr = nr
            continue
        result.append((nr, line))
    if pending:
        result.append((pending_nr, pending))
    return result


def scan_shell_file( *,root: Path, rel: str) -> bool:
    if rel in ALLOWED_SHELL_FILES:
        return False
    path = root / rel
    if not path.is_file() or path.is_symlink():
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    violation = False
    for nr, line in _logical_lines(lines):
        if _scan_command(line):
            print(
                f"lint-codex-exec-auth: {rel}:{nr}: unwired Codex dispatch without auth wiring; use python3 python/cli.py agent launch-codex-exec or # lint-codex-exec-auth: ok <reason>",
                file=sys.stderr,
            )
            violation = True
    return violation


def scan_markdown_file( *,root: Path, rel: str) -> bool:
    path = root / rel
    if not path.is_file() or path.is_symlink():
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    violation = False
    fence_depth = 0
    pending = ""
    pending_nr = 0

    def flush() -> None:
        nonlocal pending, pending_nr, violation
        if pending and _scan_command(pending):
            print(
                f"lint-codex-exec-auth: {rel}:{pending_nr}: unwired Codex dispatch in bash fence; use python3 python/cli.py agent launch-codex-exec",
                file=sys.stderr,
            )
            violation = True
        pending = ""
        pending_nr = 0

    for lineno, raw in enumerate(lines, 1):
        lower = raw.lower()
        if re.match(r"^\s*```\s*(bash|sh|shell)(\s.*)?$", lower):
            fence_depth += 1
            continue
        if fence_depth > 0 and re.match(r"^\s*```\s*$", raw):
            flush()
            fence_depth -= 1
            continue
        if fence_depth == 0:
            continue
        line = f"{pending}{raw}" if pending else raw
        nr = pending_nr or lineno
        pending = ""
        pending_nr = 0
        if re.search(r"\\\s*$", line):
            pending = re.sub(r"\\\s*$", " ", line)
            pending_nr = nr
            continue
        if _scan_command(line):
            print(
                f"lint-codex-exec-auth: {rel}:{nr}: unwired Codex dispatch in bash fence; use python3 python/cli.py agent launch-codex-exec",
                file=sys.stderr,
            )
            violation = True
    flush()
    return violation


def scan_review_and_fix_review_core(root: Path) -> bool:
    rel = "python/review_and_fix.py"
    path = root / rel
    if not path.is_file() or path.is_symlink():
        return False
    violation = False
    for nr, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if TRAILING_PRAGMA_RE.search(line) or re.match(r"^\s*#", line):
            continue
        if REVIEW_CORE_SUBPROCESS_RE.search(line):
            print(
                f"lint-codex-exec-auth: {rel}:{nr}: Step 5 must not subprocess review core; use review_core_capture / review_pipeline.review_core",
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


def main(argv: list[str] | None = None) -> int:
    parsed = parse_root_args(
        argv if argv is not None else sys.argv[1:],
        prog="cli.py lint codex-exec-auth",
        description=__doc__,
    )
    if parsed is None:
        return 2
    root = Path(parsed.root)
    if not root.is_dir():
        print(f"lint-codex-exec-auth: --root is not a directory: {root}", file=sys.stderr)
        return 2
    root = root.resolve()
    violations = 0
    if scan_review_and_fix_review_core(root):
        violations += 1
    for rel in _shell_files(root):
        if scan_shell_file(root=root, rel=rel):
            violations += 1
    for rel in _python_files(root):
        if scan_python_file(root=root, rel=rel):
            violations += 1
    for rel in _markdown_files(root):
        if scan_markdown_file(root=root, rel=rel):
            violations += 1
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
