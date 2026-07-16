"""Require shell regression harnesses to clear inherited larch session state."""

from __future__ import annotations

import re
from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

SESSION_ENV_PREAMBLE = "unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR"
_SESSION_VARIABLE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:IMPLEMENT_TMPDIR|DESIGN_TMPDIR|REVIEW_TMPDIR|RESEARCH_TMPDIR|SESSION_TMPDIR)(?![A-Za-z0-9_])"
)
_SUPPRESSION_RE = re.compile(r"#\s*lint-harness-session-env:\s*ok\s+\S(?:.*\S)?\s*$")
_PATTERNS = ("scripts/test-*.sh", "skills/*/scripts/test-*.sh")


def _rel(*, path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _is_harness(path: Path, *, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
        is_file = path.is_file()
    except OSError as exc:
        raise LintError(f"lint-harness-session-env: cannot stat {_rel(path=path, root=root)}: {exc}") from exc
    if not is_file or path.is_symlink():
        return False
    parts = relative.parts
    return (
        len(parts) == 2 and parts[0] == "scripts" and path.name.startswith("test-") and path.suffix == ".sh"
    ) or (
        len(parts) == 4
        and parts[0] == "skills"
        and parts[2] == "scripts"
        and path.name.startswith("test-")
        and path.suffix == ".sh"
    )


def find_harnesses(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if lint_common.git_rooted(root):
        files = [
            path
            for pattern in _PATTERNS
            for path in lint_common.git_ls_files_z(
                root=root,
                pattern=pattern,
                error_prefix="lint-harness-session-env: cannot enumerate git files",
            )
        ]
    else:
        files = [*root.glob(_PATTERNS[0]), *root.glob(_PATTERNS[1])]
    return sorted({path for path in files if _is_harness(path, root=root)})


def _first_command(lines: list[str]) -> int | None:
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return number
    return None


def _valid_suppression_on_first_session_use(lines: list[str]) -> bool:
    for line in lines:
        if line.lstrip().startswith("#") or _SESSION_VARIABLE_RE.search(line) is None:
            continue
        return _SUPPRESSION_RE.search(line) is not None
    return False


def lint_file(*, path: Path, root: Path) -> list[str]:
    rel = _rel(path=path, root=root)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise LintError(f"lint-harness-session-env: {rel}: non-UTF-8 input") from exc
    except OSError as exc:
        raise LintError(f"lint-harness-session-env: {rel}: unable to read: {exc}") from exc

    first_command = _first_command(lines)
    if first_command is not None and lines[first_command - 1] == SESSION_ENV_PREAMBLE:
        return []
    if _valid_suppression_on_first_session_use(lines):
        return []
    return [
        f"lint-harness-session-env: {rel}: missing required session-neutralization preamble before the first command"
    ]


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-harness-session-env",
        description=(__doc__ or "").splitlines()[0],
        iter_files=find_harnesses,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
