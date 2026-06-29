"""Require background skill fences to have bg-wait marker coverage."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

SCOPE_PATTERNS = [
    "skills/design/**/*.md",
    "skills/implement/**/*.md",
    "skills/review/**/*.md",
    "skills/review-and-fix/**/*.md",
]
FENCE_OPEN_RE = re.compile(r"^( {0,3})(`{3,})(.*)$")
BACKGROUND_RE = re.compile(r"run_in_background:\s*true")
PLACEHOLDER_RE = re.compile(r"<[^>\n]+>")
SEARCH_LINE_LIMIT = 12


@dataclass(frozen=True)
class Fence:
    start_line: int
    end_line: int
    info: str
    body: str


@dataclass(frozen=True)
class CommandMapping:
    label: str
    marker_step: str
    required: tuple[str, ...]


KNOWN_BACKGROUND_COMMANDS: tuple[CommandMapping, ...] = (
    CommandMapping(
        "design Step 3 review", "design-step3-review", ("design-step3-review.sh",)
    ),
    CommandMapping("design Step 5c publish", "design-step5c", ("design-step5c.sh",)),
    CommandMapping(
        "design final summary",
        "design-step-final-summary",
        ("design-step-final-summary.sh",),
    ),
    CommandMapping(
        "design Step 4 tail", "design-step4-tail", ("design-step3b-tail.sh",)
    ),
    CommandMapping(
        "implement Step 3 checks",
        "implement-step3-checks",
        ("python/cli.py", "implement", "checks-commit-route", "--checks-site", "step3"),
    ),
    CommandMapping(
        "implement Step 5 self-review",
        "implement-step5-self-review",
        (
            "python/cli.py",
            "implement",
            "checks-commit-route",
            "--checks-site",
            "step5-self-review",
        ),
    ),
    CommandMapping(
        "implement Step 5 review", "implement-step5-review", ("step-5-review.sh",)
    ),
    CommandMapping(
        "implement Step 5 resume",
        "implement-step5-resume",
        ("python/cli.py", "implement", "checks-step5-resume"),
    ),
    CommandMapping(
        "implement Step 6 checks", "implement-step6-checks", ("step-6-entry.sh",)
    ),
    CommandMapping(
        "implement Step 7a",
        "implement-step7a",
        ("python/cli.py", "implement", "step-7a"),
    ),
    CommandMapping(
        "implement Step 8 ship", "implement-step8-ship", ("step-8-ship.sh",)
    ),
)


def _closing_fence_re(*, indent: str, marker_len: int) -> re.Pattern[str]:
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
        body: list[str] = []
        cursor = index + 1
        while cursor < len(lines):
            if close_re.match(lines[cursor]):
                fences.append(
                    Fence(index + 1, cursor + 1, info.strip(), "\n".join(body))
                )
                index = cursor + 1
                break
            body.append(lines[cursor])
            cursor += 1
        else:
            index += 1
    return fences


def _is_bash_fence(fence: Fence) -> bool:
    info = fence.info.lower().strip()
    return info.startswith(("bash", "sh", "shell"))


def _normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command).strip()


def _mapping_for(command: str) -> CommandMapping | None:
    normalized = _normalize_command(command)
    for mapping in KNOWN_BACKGROUND_COMMANDS:
        if all(token in normalized for token in mapping.required):
            return mapping
    return None


def _is_illustrative_placeholder(command: str) -> bool:
    return bool(PLACEHOLDER_RE.search(command))


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


def iter_files(root: Path) -> list[Path]:
    return [
        path
        for path in _git_files(root=root, patterns=SCOPE_PATTERNS)
        if path.is_file() and not path.is_symlink()
    ]


def _nearest_launch_fence(*, directive_line: int, fences: list[Fence]) -> Fence | None:
    candidates = [
        fence
        for fence in fences
        if _is_bash_fence(fence)
        and fence.start_line > directive_line
        and fence.start_line - directive_line <= SEARCH_LINE_LIMIT
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda fence: fence.start_line)


def lint_file(*, path: Path, root: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LintError(f"lint-bg-wait-coverage: cannot decode {path}: {exc}") from exc
    except OSError as exc:
        raise LintError(f"lint-bg-wait-coverage: cannot read {path}: {exc}") from exc
    lines = text.splitlines()
    fences = _parse_fences(lines)
    rel = path.relative_to(root).as_posix()
    violations: list[str] = []
    for index, line in enumerate(lines, start=1):
        if not BACKGROUND_RE.search(line):
            continue
        if "do NOT set" in line or "do not set" in line:
            continue
        fence = _nearest_launch_fence(directive_line=index, fences=fences)
        if fence is None:
            continue
        if _is_illustrative_placeholder(fence.body):
            continue
        mapping = _mapping_for(fence.body)
        if mapping is None:
            command = _normalize_command(fence.body)
            violations.append(
                f"{rel}:{index}: run_in_background launch has no bg-wait marker mapping: {command}"
            )
    return violations


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-bg-wait-coverage",
        description="Require background skill launches to map to known bg-wait markers.",
        iter_files=iter_files,
        lint_file=lint_file,
    )
