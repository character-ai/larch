#!/usr/bin/env python3
"""Print tracked larch source line counts and run-log byte sizes."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

CATEGORY_WIDTH = 37
FILES_WIDTH = 5
LINES_WIDTH = 6
SIZE_LABEL_WIDTH = 29
BYTES_PER_MB = 1024 * 1024
LINE_COUNT_EXCLUDED_PREFIXES = ("larch-logs/", "node_modules/")


@dataclass(frozen=True)
class Category:
    """A rendered line-count category."""

    label: str
    files: int = 0
    lines: int = 0

    def add(self, line_count: int) -> "Category":
        return Category(self.label, self.files + 1, self.lines + line_count)


CATEGORIES = (
    "Bash scripts (runtime, non-test *.sh)",
    "Bash tests (test-*.sh)",
    "Python code (non-test *.py)",
    "Python tests (test_*.py)",
    "All Markdown (*.md)",
)


def git_ls_files(repo_root: Path) -> list[str]:
    """Return tracked repo-relative paths from ``git ls-files -z``."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.buffer.write(result.stderr)
        sys.exit(result.returncode)
    return [
        raw.decode("utf-8", "surrogateescape")
        for raw in result.stdout.split(b"\0")
        if raw
    ]


def count_newlines(repo_root: Path, rel_path: str) -> int:
    """Count newline bytes in a tracked file."""
    try:
        return (repo_root / rel_path).read_bytes().count(b"\n")
    except OSError:
        print(rel_path, file=sys.stderr)
        sys.exit(1)


def stat_size(repo_root: Path, rel_path: str) -> int:
    """Return the logical byte size reported by ``os.stat``."""
    try:
        return os.stat(repo_root / rel_path).st_size
    except OSError:
        print(rel_path, file=sys.stderr)
        sys.exit(1)


def line_count_category(rel_path: str) -> str | None:
    """Return the category label for ``rel_path``, or ``None``."""
    if rel_path.startswith(LINE_COUNT_EXCLUDED_PREFIXES):
        return None

    basename = Path(rel_path).name
    suffix = Path(rel_path).suffix

    if suffix == ".sh":
        if basename.startswith("test-"):
            return "Bash tests (test-*.sh)"
        return "Bash scripts (runtime, non-test *.sh)"
    if suffix == ".py":
        if basename.startswith("test_"):
            return "Python tests (test_*.py)"
        return "Python code (non-test *.py)"
    if suffix == ".md":
        return "All Markdown (*.md)"
    return None


def collect_line_counts(repo_root: Path, tracked_paths: list[str]) -> list[Category]:
    """Count files and newline bytes for the fixed report categories."""
    categories = {label: Category(label) for label in CATEGORIES}
    for rel_path in tracked_paths:
        label = line_count_category(rel_path)
        if label is None:
            continue
        categories[label] = categories[label].add(count_newlines(repo_root, rel_path))
    return [categories[label] for label in CATEGORIES]


def render_line_counts(categories: list[Category]) -> str:
    """Render the fixed-width box-drawing table."""
    top = f"┌{'─' * (CATEGORY_WIDTH + 2)}┬{'─' * (FILES_WIDTH + 2)}┬{'─' * (LINES_WIDTH + 2)}┐"
    middle = f"├{'─' * (CATEGORY_WIDTH + 2)}┼{'─' * (FILES_WIDTH + 2)}┼{'─' * (LINES_WIDTH + 2)}┤"
    bottom = f"└{'─' * (CATEGORY_WIDTH + 2)}┴{'─' * (FILES_WIDTH + 2)}┴{'─' * (LINES_WIDTH + 2)}┘"
    rows = [
        top,
        f"│ {'Category':^{CATEGORY_WIDTH}} │ {'Files':^{FILES_WIDTH}} │ {'Lines':^{LINES_WIDTH}} │",
        middle,
    ]
    for index, category in enumerate(categories):
        rows.append(
            f"│ {category.label:<{CATEGORY_WIDTH}} │ "
            f"{category.files:>{FILES_WIDTH},} │ "
            f"{category.lines:>{LINES_WIDTH},} │"
        )
        if index != len(categories) - 1:
            rows.append(middle)
    rows.append(bottom)
    return "\n".join(rows)


def pct(numerator: int, denominator: int) -> float:
    """Return a percentage with a zero-total guard."""
    if denominator == 0:
        return 0.0
    return numerator * 100 / denominator


def mb(byte_count: int) -> float:
    """Return mebibytes for the byte count, labeled as MB in output."""
    return byte_count / BYTES_PER_MB


def render_size_line(label: str, byte_count: int, suffix: str = "") -> str:
    """Render one size report line."""
    return f"{label:<{SIZE_LABEL_WIDTH}}{mb(byte_count):>8.2f} MB{suffix}"


def render_size_report(repo_root: Path, tracked_paths: list[str]) -> str:
    """Render tracked-content repository and larch-logs size totals."""
    repo_total = 0
    larch_logs_total = 0
    implement = 0
    design = 0

    for rel_path in tracked_paths:
        size = stat_size(repo_root, rel_path)
        repo_total += size
        if rel_path.startswith("larch-logs/"):
            larch_logs_total += size
            if rel_path.startswith("larch-logs/implement/"):
                implement += size
            elif rel_path.startswith("larch-logs/design/"):
                design += size

    rest = larch_logs_total - implement - design
    repo_minus_logs = repo_total - larch_logs_total

    return "\n".join(
        [
            render_size_line("Repo (tracked content):", repo_total),
            render_size_line(
                "larch-logs/ total:",
                larch_logs_total,
                f"   ({pct(larch_logs_total, repo_total):>4.1f}% of repo)",
            ),
            render_size_line(
                "  ├─ implement:",
                implement,
                f"   ({pct(implement, larch_logs_total):>4.1f}% of run-logs)",
            ),
            render_size_line(
                "  ├─ design:",
                design,
                f"   ({pct(design, larch_logs_total):>4.1f}% of run-logs)",
            ),
            render_size_line(
                "  └─ rest (shared, etc.):",
                rest,
                f"   ({pct(rest, larch_logs_total):>4.1f}% of run-logs)",
            ),
            render_size_line(
                "Repo minus larch-logs:",
                repo_minus_logs,
                f"   ({pct(repo_minus_logs, repo_total):>4.1f}% of repo)",
            ),
        ]
    )


def _git_toplevel() -> Path:
    """Return the repo root from git, exiting on failure."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.buffer.write(result.stderr)
        sys.exit(result.returncode)
    return Path(result.stdout.decode().strip())


def main() -> int:
    """CLI entrypoint."""
    repo_root = _git_toplevel()
    tracked_paths = git_ls_files(repo_root)
    print(render_line_counts(collect_line_counts(repo_root, tracked_paths)))
    print()
    print(render_size_report(repo_root, tracked_paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
