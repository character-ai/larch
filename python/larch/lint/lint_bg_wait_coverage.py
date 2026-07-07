"""Reject unallowlisted skill prose that still requests run_in_background."""

from __future__ import annotations

import re
from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

SCOPE_PATTERNS = ["skills/**/*.md"]
BACKGROUND_RE = re.compile(r"run_in_background\s*:?\s*true")
ALLOWLIST_PATH = Path(__file__).with_name("bg_wait_allowlist.txt")


def _git_files(*, root: Path, patterns: list[str]) -> list[Path]:
    paths: set[Path] = set()
    for pattern in patterns:
        if lint_common.git_rooted(root):
            paths.update(
                lint_common.git_ls_files_z(
                    root=root,
                    pattern=pattern,
                    error_prefix="lint-bg-wait-coverage: cannot enumerate markdown files",
                )
            )
        else:
            paths.update(root.glob(pattern))
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _load_allowlist(root: Path) -> dict[str, str]:
    path = root / "python/larch/lint/bg_wait_allowlist.txt"
    if not path.is_file():
        path = ALLOWLIST_PATH
    rows: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LintError(f"lint-bg-wait-coverage: cannot read allowlist {path}: {exc}") from exc
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in line:
            raise LintError(f"lint-bg-wait-coverage: malformed allowlist row {path}:{line_number}")
        rel, reason = line.split("\t", 1)
        if not rel or not reason.strip():
            raise LintError(f"lint-bg-wait-coverage: allowlist row needs path and reason {path}:{line_number}")
        rows[rel] = reason.strip()
    return rows


def iter_files(root: Path) -> list[Path]:
    return [
        path
        for path in _git_files(root=root, patterns=SCOPE_PATTERNS)
        if path.is_file() and not path.is_symlink()
    ]


def _is_historical_fixture(rel: str) -> bool:
    return rel.startswith(("python/test_fixtures/", "larch-logs/")) or "/larch-logs/" in rel


def lint_file(*, path: Path, root: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LintError(f"lint-bg-wait-coverage: cannot decode {path}: {exc}") from exc
    except OSError as exc:
        raise LintError(f"lint-bg-wait-coverage: cannot read {path}: {exc}") from exc
    rel = path.relative_to(root).as_posix()
    if _is_historical_fixture(rel):
        return []
    allowlist = _load_allowlist(root)
    if rel in allowlist:
        return []
    violations: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not BACKGROUND_RE.search(line):
            continue
        if "do NOT set" in line or "do not set" in line:
            continue
        violations.append(
            f"{rel}:{line_number}: run_in_background is forbidden outside python/larch/lint/bg_wait_allowlist.txt"
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-bg-wait-coverage",
        description="Reject unallowlisted run_in_background prose in skills markdown.",
        iter_files=iter_files,
        lint_file=lint_file,
    )
