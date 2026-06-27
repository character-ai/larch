"""Reject adjacent prompt-side bash fences in orchestrator-facing skill markdown."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import lint_common
from lint_common import GIT, LintError

SCOPE_PATTERNS = [
    "skills/*/SKILL.md",
    "skills/*/references/*.md",
    ".claude/skills/*/SKILL.md",
]
FENCE_OPEN_RE = re.compile(r"^( {0,3})(`{3,})(.*)$")
HTML_COMMENT_START_RE = re.compile(r"^\s*<!--")
HTML_COMMENT_END_RE = re.compile(r"-->\s*$")
STANDALONE_PRAGMA_RE = re.compile(r"^\s*# lint-consecutive-bash: ok\s+(\S.*)$")
TRAILING_PRAGMA_RE = re.compile(r"\s# lint-consecutive-bash: ok\s+(\S.*)$")
BREADCRUMB_MAX_CHARS = 160
BREADCRUMB_MAX_LINE_CHARS = 100
BREADCRUMB_MAX_LINES = 2
RECOVERY_SENTINELS = (
    ".completed/step-3-terminal",
    ".completed/step-5c-terminal",
    ".completed/step-final-summary",
)
VIOLATION_HELP = (
    "combine into one cli.py-backed call or add trailing "
    "# lint-consecutive-bash: ok <reason> on single-line launcher fences "
    "(or body comment in multi-line fences) for an intentional boundary"
)


@dataclass(frozen=True)
class BodyLine:
    line_number: int
    text: str


@dataclass(frozen=True)
class Fence:
    start_line: int
    end_line: int
    info: str
    body: str
    body_lines: tuple[BodyLine, ...]
    preceding_context: tuple[str, ...]


def _git_files( *,root: Path, patterns: list[str]) -> list[Path]:
    try:
        proc = subprocess.run(
            [GIT, "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", *patterns],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise LintError(f"lint-consecutive-bash: cannot enumerate markdown files: {detail}") from exc
    except OSError as exc:
        raise LintError(f"lint-consecutive-bash: cannot enumerate markdown files: {exc}") from exc
    rels = {rel.decode("utf-8") for rel in proc.stdout.split(b"\0") if rel}
    return [root / rel for rel in sorted(rels)]


def iter_markdown_files(root: Path) -> list[Path]:
    if lint_common.git_rooted(root):
        candidates = _git_files(root=root, patterns=SCOPE_PATTERNS)
    else:
        found: set[Path] = set()
        for pattern in SCOPE_PATTERNS:
            found.update(root.glob(pattern))
        candidates = sorted(found, key=lambda path: path.relative_to(root).as_posix())
    return [path for path in candidates if path.is_file() and not path.is_symlink()]


def _closing_fence_re( *,indent: str, marker_len: int) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(indent)}`{{{marker_len},}}\s*$")


def _parse_fences(lines: list[str]) -> list[Fence]:
    fences: list[Fence] = []
    index = 0
    while index < len(lines):
        opener = FENCE_OPEN_RE.match(lines[index])
        if not opener:
            index += 1
            continue
        indent, marker, info = opener.groups()
        close_re = _closing_fence_re(indent=indent, marker_len=len(marker))
        body_lines: list[BodyLine] = []
        close_index = index
        cursor = index + 1
        while cursor < len(lines):
            if close_re.match(lines[cursor]):
                close_index = cursor
                break
            body_lines.append(BodyLine(cursor + 1, lines[cursor]))
            cursor += 1
        else:
            # Unclosed opener at EOF: do NOT treat it as a fence extending to the
            # end of the file. Swallowing the remainder hid every later fence
            # (e.g. indented fences whose closers never match this opener) and
            # suppressed real consecutive-bash detection. Skip the malformed
            # opener and keep scanning from the next line.
            index += 1
            continue
        preceding = tuple(lines[max(0, index - 3) : index])
        body = "\n".join(line.text for line in body_lines)
        fences.append(Fence(index + 1, close_index + 1, info.strip(), body, tuple(body_lines), preceding))
        index = cursor + 1
    return fences


def _is_bash_candidate(fence: Fence) -> bool:
    return fence.info.lower().lstrip().startswith("bash")


def _strip_html_comments(lines: list[str]) -> list[str]:
    remaining: list[str] = []
    in_comment = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if in_comment:
            if HTML_COMMENT_END_RE.search(stripped):
                in_comment = False
            continue
        if HTML_COMMENT_START_RE.match(stripped):
            if not HTML_COMMENT_END_RE.search(stripped):
                in_comment = True
            continue
        remaining.append(stripped)
    return remaining


def _is_breadcrumb_line(line: str) -> bool:
    if len(line) > BREADCRUMB_MAX_LINE_CHARS:
        return False
    if re.match(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>|\|)", line):
        return False
    return not re.match(r"^-{3,}$", line)


def _gap_is_adjacent(lines: list[str]) -> bool:
    remaining = _strip_html_comments(lines)
    if not remaining:
        return True
    if len(remaining) > BREADCRUMB_MAX_LINES:
        return False
    if sum(len(line) for line in remaining) > BREADCRUMB_MAX_CHARS:
        return False
    return all(_is_breadcrumb_line(line) for line in remaining)


def _has_valid_suppression(fence: Fence) -> bool:
    nonblank = [line.text for line in fence.body_lines if line.text.strip()]
    for line in nonblank:
        standalone = STANDALONE_PRAGMA_RE.match(line)
        if standalone:
            return len(nonblank) > 1
        trailing = TRAILING_PRAGMA_RE.search(line)
        if trailing and line[: trailing.start()].strip() and not line[: trailing.start()].lstrip().startswith("#"):
            return True
    return False


def _is_wrong_correct_pair( *,first: Fence, second: Fence, gap_lines: list[str]) -> bool:
    text = "\n".join(
        [
            *first.preceding_context,
            first.info,
            first.body,
            *gap_lines,
            *second.preceding_context,
            second.info,
            second.body,
        ]
    )
    return bool(re.search(r"\bWRONG\b", text, re.IGNORECASE) and re.search(r"\bCORRECT\b", text, re.IGNORECASE))


def _combined_pair_text( *,first: Fence, second: Fence, gap_lines: list[str]) -> str:
    return "\n".join([first.body, *gap_lines, second.body])


def _is_recovery_probe_pair(text: str) -> bool:
    if not any(sentinel in text for sentinel in RECOVERY_SENTINELS):
        return False
    return "test -f" in text or "[ -f" in text


def _is_design_pause_resume_pair(text: str) -> bool:
    if "/design" not in text and " design " not in text and "design driver" not in text:
        return False
    markers = ("pause", "resume", "design-step", "DESIGN_ACTION", "skills/design/scripts")
    return any(marker in text for marker in markers)


def _is_immediate_background_pair(text: str) -> bool:
    return "<task-notification>" in text or "run_in_background" in text


def _is_carved_out_pair( *,first: Fence, second: Fence, gap_lines: list[str]) -> bool:
    if _is_wrong_correct_pair(first=first, second=second, gap_lines=gap_lines):
        return True
    text = _combined_pair_text(first=first, second=second, gap_lines=gap_lines)
    return _is_recovery_probe_pair(text) or _is_design_pause_resume_pair(text) or _is_immediate_background_pair(text)


def _rel( *,path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def lint_file( *,path: Path, root: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LintError(f"lint-consecutive-bash: {_rel(path=path, root=root)}: cannot read file: {exc}") from exc
    lines = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    fences = [fence for fence in _parse_fences(lines) if _is_bash_candidate(fence)]
    violations: list[str] = []
    for first, second in pairwise(fences):
        gap_lines = lines[first.end_line : second.start_line - 1]
        if not _gap_is_adjacent(gap_lines):
            continue
        if _has_valid_suppression(first) or _has_valid_suppression(second):
            continue
        if _is_carved_out_pair(first=first, second=second, gap_lines=gap_lines):
            continue
        violations.append(
            f"lint-consecutive-bash: {_rel(path=path, root=root)}:{first.start_line}: consecutive bash tool-call "
            f"fences at lines {first.start_line} and {second.start_line}; {VIOLATION_HELP}"
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-consecutive-bash",
        description=(__doc__ or "").splitlines()[0],
        iter_files=iter_markdown_files,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    sys.exit(main())
