"""Require every bg-wait marker writer to emit a local CLONE_PATH stamp."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

PROG = "lint-bg-wait-writer-parity"


@dataclass(frozen=True)
class WriterSpec:
    path: str
    label: str


WRITERS: tuple[WriterSpec, ...] = (
    WriterSpec("skills/design/scripts/design-step3-review.sh", "design Step 3 review"),
    WriterSpec("skills/design/scripts/design-step3b-tail.sh", "design Step 4 tail"),
    WriterSpec("skills/implement/scripts/run-step-checks.sh", "implement Step 3 checks"),
    WriterSpec("skills/implement/scripts/step-5-review.sh", "implement Step 5 review"),
    WriterSpec("skills/implement/scripts/step-6-entry.sh", "implement Step 6 checks"),
    WriterSpec("skills/implement/scripts/step-8-ship.sh", "implement Step 8 ship"),
    WriterSpec("python/larch/design/design_core.py", "design Python bg-wait context"),
    WriterSpec("python/larch/implement/bg_wait.py", "implement Python bg-wait helper"),
)

WRITER_EVIDENCE_TOKENS = (".bg-wait-active", "PID=", "START_EPOCH=", "STEP=")


def _has_writer_evidence(text: str) -> bool:
    return all(token in text for token in WRITER_EVIDENCE_TOKENS)


WRITE_CONTEXT_TOKENS = ("write_text(", "printf", ">", ">>", ".replace(", "mv ")
CLONE_PATH_WINDOW_LINES = 15


def _is_comment_line(line: str) -> bool:
    return line.lstrip().startswith(("#", "//"))


def _non_comment_has_clone_path(line: str) -> bool:
    return not _is_comment_line(line) and "CLONE_PATH=" in line


def _is_cleanup_marker_line(line: str) -> bool:
    if ".bg-wait-active" not in line:
        return False
    stripped = line.lstrip()
    return stripped.startswith(("rm ", "rm -", "del ")) or ".unlink()" in line


def _has_write_context(lines: list[str], index: int) -> bool:
    line = lines[index]
    if any(token in line for token in WRITE_CONTEXT_TOKENS):
        return True
    start = max(0, index - CLONE_PATH_WINDOW_LINES)
    end = min(len(lines), index + CLONE_PATH_WINDOW_LINES + 1)
    return any(not _is_comment_line(candidate) and any(token in candidate for token in WRITE_CONTEXT_TOKENS) for candidate in lines[start:end])


def _has_nearby_clone_path(lines: list[str], index: int) -> bool:
    start = max(0, index - CLONE_PATH_WINDOW_LINES)
    end = min(len(lines), index + CLONE_PATH_WINDOW_LINES + 1)
    return any(_non_comment_has_clone_path(line) for line in lines[start:end])


def _has_clone_path_emission(text: str) -> bool:
    lines = text.splitlines()
    marker_write_indexes = [
        index
        for index, line in enumerate(lines)
        if not _is_comment_line(line)
        and ".bg-wait-active" in line
        and not _is_cleanup_marker_line(line)
        and _has_write_context(lines, index)
    ]
    if not marker_write_indexes:
        return any(_non_comment_has_clone_path(line) for line in lines)
    return all(_has_nearby_clone_path(lines, index) for index in marker_write_indexes)


def _read_writer(path: Path, *, rel: str) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise LintError(f"{PROG}: {rel}: cannot read expected writer file: {exc}") from exc


def lint_writers(root: Path, specs: Sequence[WriterSpec] = WRITERS) -> list[str]:
    violations: list[str] = []
    for spec in specs:
        path = root / spec.path
        if not path.is_file() or path.is_symlink():
            violations.append(
                f"{PROG}: {spec.path}: expected {spec.label} bg-wait writer file is missing; "
                "update the writer inventory if it moved"
            )
            continue
        text = _read_writer(path, rel=spec.path)
        if not _has_writer_evidence(text):
            violations.append(f"{PROG}: {spec.path}: no bg-wait marker writer evidence found")
            continue
        if not _has_clone_path_emission(text):
            violations.append(f"{PROG}: {spec.path}: bg-wait marker writer does not emit CLONE_PATH=")
    return violations


def main(argv: list[str] | None = None) -> int:
    args = lint_common.parse_root_args(
        argv if argv is not None else sys.argv[1:],
        prog=PROG,
        description="Require known bg-wait marker writers to emit CLONE_PATH.",
    )
    if args is None:
        return 2
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"{PROG}: --root is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        violations = lint_writers(root)
    except LintError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for violation in violations:
        print(violation, file=sys.stderr)
    return 1 if violations else 0
