"""Lint SKILL.md frontmatter description values over the length cap."""

from __future__ import annotations

import re
from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

MAX_DESCRIPTION_CHARS = 200
GLOB_PATTERNS = ("skills/*/SKILL.md", ".claude/skills/*/SKILL.md")
MIN_QUOTED_LENGTH = 2
DESCRIPTION_REGEX = re.compile(r"^description\s*:\s*(.*)$")


def extract_frontmatter(text: str) -> str | None:
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return None
    remainder = normalized[len("---\n") :]
    end_marker = "\n---\n"
    marker_index = remainder.find(end_marker)
    if marker_index >= 0:
        return remainder[:marker_index]
    if remainder.endswith("\n---"):
        return remainder[: -len("\n---")]
    return None


def _strip_inline_comment(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    if value[0] not in {"'", '"'}:
        for index, char in enumerate(value):
            if char == "#" and (index == 0 or value[index - 1].isspace()):
                return value[:index].rstrip()
        return value
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double and index > 0 and value[index - 1].isspace():
            return value[:index].rstrip()
    return value


def _strip_surrounding_quotes(value: str) -> str:
    if len(value) >= MIN_QUOTED_LENGTH and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def extract_description_value(frontmatter: str) -> str | None:
    for line in frontmatter.split("\n"):
        match = DESCRIPTION_REGEX.match(line)
        if match:
            value = _strip_inline_comment(match.group(1).strip())
            return _strip_surrounding_quotes(value)
    return None


def find_skill_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in GLOB_PATTERNS:
        files.extend(sorted(root.glob(pattern)))
    return files


def _rel(*, path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def lint_file(*, path: Path, root: Path) -> list[str]:
    rel = _rel(path=path, root=root)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LintError(f"lint-skill-description-length: {rel}: cannot read file: {exc}") from exc
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        return []
    description = extract_description_value(frontmatter)
    if description is None or len(description) <= MAX_DESCRIPTION_CHARS:
        return []
    return [
        f"lint-skill-description-length: {rel}: description is {len(description)} chars "
        f"(max {MAX_DESCRIPTION_CHARS}); shorten the frontmatter description value"
    ]


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-skill-description-length",
        description=(__doc__ or "").splitlines()[0],
        iter_files=find_skill_files,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
