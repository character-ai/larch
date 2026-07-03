"""Reject prompt-side awk field references in SKILL.md shell fences."""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

from larch.lint.lint_common import LintError, run_file_lint

FENCE_OPEN_RE = re.compile(r"^[ \t]{0,3}```[ \t]*(bash|sh|shell)(?:[ \t].*)?$")
FENCE_ANY_RE = re.compile(r"^[ \t]{0,3}```")
FIELD_REF_RE = re.compile(r"\$[0-9]+")
SUPPRESSION = "# lint-skill-awk-field-ref: ok"
BOOTSTRAP_REL = "skills/implement/SKILL.md"
SEPARATORS = {"|", "||", "&&", ";", "&"}


def _rel( *,path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def iter_skill_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("skills/*/SKILL.md", ".claude/skills/*/SKILL.md"):
        files.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(files)


def _is_bootstrap_exception( *,command: str, path: Path, root: Path) -> bool:
    return (
        _rel(path=path, root=root) == BOOTSTRAP_REL
        and 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="}' in command
        and "index($0,p)==1" in command
        and "session-env.sh" in command
    )


def _is_awk_token(token: str) -> bool:
    clean = token.rstrip("();")
    return re.search(r"(^|[/($=])awk$", clean) is not None


def _awk_programs(command: str) -> list[str]:  # noqa: C901
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    programs: list[str] = []
    pos = 0
    while pos < len(tokens):
        token = tokens[pos]
        if not _is_awk_token(token):
            pos += 1
            continue
        pos += 1
        source_from_file = False
        while pos < len(tokens):
            token = tokens[pos]
            if token in SEPARATORS:
                break
            if token in {"-F", "-v"}:
                pos += 2
                continue
            if token.startswith(("-F", "-v")) and token != "-":
                pos += 1
                continue
            if token == "-f":
                source_from_file = True
                pos += 2
                continue
            if token.startswith("-f") and token != "-":
                source_from_file = True
                pos += 1
                continue
            if token.startswith("-"):
                pos += 1
                continue
            if source_from_file:
                pos += 1
                continue
            programs.append(token)
            pos += 1
            break
    return programs


def _command_has_awk_field_ref(command: str) -> bool:
    return any(FIELD_REF_RE.search(program) is not None for program in _awk_programs(command))


def _command_is_complete(command: str) -> bool:
    try:
        shlex.split(command, posix=True)
    except ValueError:
        return False
    return True


def _suppression_reason(text: str) -> str | None:
    marker = text.find(SUPPRESSION)
    if marker == -1:
        return None
    return text[marker + len(SUPPRESSION) :].strip()


def report_command( *,path: Path, root: Path, line_no: int, command: str, previous_line: str) -> list[str]:
    for text in (previous_line, command):
        reason = _suppression_reason(text)
        if reason is None:
            continue
        if reason:
            return []
        rel = _rel(path=path, root=root)
        return [
            f"{rel}:{line_no}: lint-skill-awk-field-ref suppression requires a justification"
        ]
    if _is_bootstrap_exception(command=command, path=path, root=root):
        return []
    if not _command_has_awk_field_ref(command):
        return []
    rel = _rel(path=path, root=root)
    return [
        f"{rel}:{line_no}: bare awk $<digit> field reference in SKILL.md fence; "
        "move parsing behind python/cli.py or add a justified suppression"
    ]


def lint_file( *,path: Path, root: Path) -> list[str]:  # noqa: C901
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise LintError(f"lint-skill-awk-field-refs: cannot read {_rel(path=path, root=root)}: {exc}") from exc

    violations: list[str] = []
    in_fence = False
    previous = ""
    logical = ""
    logical_start = 0
    logical_previous = ""

    def _segment(line: str) -> str:
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            return stripped[:-1].rstrip()
        return stripped

    for lineno, line in enumerate(lines, 1):
        if FENCE_OPEN_RE.match(line):
            in_fence = True
            previous = line
            continue
        if FENCE_ANY_RE.match(line):
            if in_fence and logical:
                violations.extend(
                    report_command(
                        path=path,
                        root=root,
                        line_no=logical_start,
                        command=logical,
                        previous_line=logical_previous,
                    )
                )
                logical = ""
            in_fence = False
            previous = line
            continue
        if not in_fence:
            previous = line
            continue
        segment = _segment(line)
        if not logical:
            logical = segment
            logical_start = lineno
            logical_previous = previous
        else:
            logical = f"{logical} {segment}" if segment else logical
        if line.rstrip().endswith("\\"):
            previous = line
            continue
        if not _command_is_complete(logical):
            previous = line
            continue
        violations.extend(
            report_command(
                path=path,
                root=root,
                line_no=logical_start,
                command=logical,
                previous_line=logical_previous,
            )
        )
        logical = ""
        logical_start = 0
        logical_previous = ""
        previous = line
    return violations


def main(argv: list[str] | None = None) -> int:
    return run_file_lint(
        argv,
        prog="cli.py lint skill-awk-field-refs",
        description=__doc__,
        iter_files=iter_skill_files,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
