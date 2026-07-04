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
    WriterSpec("python/larch/implement/dispatch_commit_route.py", "implement checks commit route"),
    WriterSpec("python/larch/implement/step_7a.py", "implement Step 7a"),
)

WRITER_EVIDENCE_TOKENS = (".bg-wait-active", "PID=", "START_EPOCH=", "STEP=")


def _has_writer_evidence(text: str) -> bool:
    return all(token in text for token in WRITER_EVIDENCE_TOKENS)


def _has_clone_path_emission(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("#", "//")):
            continue
        if "CLONE_PATH=" in line:
            return True
    return False


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
