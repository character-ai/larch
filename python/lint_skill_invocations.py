"""Lint SKILL.md files that use the Skill tool for invocation wording."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERN_A_PHRASE = "Invoke the Skill tool"
PATTERN_B_PHRASE = "via the Skill tool"
INVOCATION_LINE_REGEX = re.compile(
    r"\b(?:re-)?[Ii]nvoke\b\s+(?:the\s+)?(?:\*\*[^*\n]{1,40}\*\*\s+)?`/[\w-]+`(?:\s+skill\b)?"
)
CODE_FENCE_REGEX = re.compile(r"^\s*```")
GLOB_PATTERNS = ("skills/*/SKILL.md", ".claude/skills/*/SKILL.md")
MIN_QUOTED_LENGTH = 2


class LintError(Exception):
    """Raised for internal read errors."""


def extract_frontmatter_and_body(text: str) -> tuple[str | None, str, int]:
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None, text, 1
    remainder = text[len("---\n") :]
    end_marker = "\n---\n"
    idx = remainder.find(end_marker)
    if idx < 0:
        if remainder.endswith("\n---"):
            return remainder[: -len("\n---")], "", 0
        return None, text, 1
    frontmatter = remainder[:idx]
    body = remainder[idx + len(end_marker) :]
    frontmatter_lines = frontmatter.count("\n") + 1
    body_start_line = 2 + frontmatter_lines + 1
    return frontmatter, body, body_start_line


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= MIN_QUOTED_LENGTH and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _strip_inline_comment(value: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif (
            char == "#"
            and not in_single
            and not in_double
            and (index == 0 or value[index - 1].isspace())
        ):
            return value[:index].rstrip()
    return value.strip()


def _split_tokens(value: str) -> list[str]:
    value = _strip_inline_comment(value.strip())
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    value = _strip_quotes(value)
    return [_strip_quotes(part).strip() for part in value.split(",") if _strip_quotes(part).strip()]


def allowed_tools_contains_skill(frontmatter_text: str) -> bool:
    try:
        lines = frontmatter_text.replace("\r\n", "\n").split("\n")
        if any(line.lstrip().startswith("-") for line in lines if line.strip()):
            # A top-level YAML sequence is not a mapping. Indented block-list
            # entries under allowed-tools are handled after the key is found.
            first = next(line for line in lines if line.strip())
            if first.lstrip().startswith("-"):
                return False
        for idx, line in enumerate(lines):
            match = re.match(r"^allowed-tools\s*:\s*(.*)$", line)
            if not match:
                continue
            value = match.group(1)
            if value.strip():
                return "Skill" in _split_tokens(value)
            tokens: list[str] = []
            for child in lines[idx + 1 :]:
                if not child.startswith((" ", "\t")):
                    break
                stripped = child.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                item = re.match(r"^-\s*(.+)$", stripped)
                if not item:
                    return False
                tokens.extend(_split_tokens(item.group(1)))
            return "Skill" in tokens
    except Exception:
        return False
    return False


def body_has_invocation_phrase(body: str) -> bool:
    return PATTERN_A_PHRASE in body or PATTERN_B_PHRASE in body


def body_per_invocation_violations(body: str, body_start_line: int) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    in_fence = False
    for body_line_idx, line in enumerate(body.split("\n")):
        if CODE_FENCE_REGEX.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if INVOCATION_LINE_REGEX.search(line) and PATTERN_B_PHRASE not in line:
            violations.append((body_start_line + body_line_idx, line))
    return violations


def find_skill_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in GLOB_PATTERNS:
        files.extend(sorted(root.glob(pattern)))
    return files


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def lint_file(path: Path, root: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LintError(f"lint-skill-invocations: {path}: cannot read file: {exc}") from exc
    frontmatter, body, body_start_line = extract_frontmatter_and_body(text)
    if frontmatter is None or not allowed_tools_contains_skill(frontmatter):
        return []
    rel = _rel(path, root)
    messages: list[str] = []
    if not body_has_invocation_phrase(body):
        messages.append(
            f"lint-skill-invocations: {rel}: declares 'Skill' in allowed-tools but contains no "
            f"'{PATTERN_A_PHRASE}' or '{PATTERN_B_PHRASE}' invocation step"
        )
    for absolute_line, _line_text in body_per_invocation_violations(body, body_start_line):
        messages.append(
            f"lint-skill-invocations: {rel}:{absolute_line}: 'Invoke `/<cmd>`' without "
            f"'{PATTERN_B_PHRASE}' on the same line — see skills/shared/subskill-invocation.md"
        )
    return messages


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint skill-invocations", description=__doc__)
    _ = parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return 2
    root = parsed.root.resolve()
    if not root.is_dir():
        print(f"lint-skill-invocations: --root is not a directory: {root}", file=sys.stderr)
        return 2
    violations: list[str] = []
    errors: list[str] = []
    for path in find_skill_files(root):
        try:
            violations.extend(lint_file(path, root))
        except LintError as exc:
            errors.append(str(exc))
    for error in errors:
        print(error, file=sys.stderr)
    for violation in violations:
        print(violation, file=sys.stderr)
    if errors:
        return 2
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
