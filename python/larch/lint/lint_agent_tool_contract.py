"""Lint agent prompts whose tool declarations contradict read instructions.

Scans shipped and dev-only agent definition files for YAML frontmatter that
restricts tools to an explicit list without ``Read`` while the prompt body asks
the agent to read files or bundles. It also rejects prompts that mandate
machine-parsed-only output (strict JSON or JSONL) while carrying no fail-closed
instruction for unreadable evidence.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from larch.lint import lint_common
from larch.lint.engine import RuleCli, run_root_cli

TOOL_FAILURE_EXIT = 2
GLOB_PATTERNS = ("agents/*.md", ".claude/agents/*.md")
FINDING_MESSAGE = (
    "agent declares tools without Read but its prompt instructs reading files; "
    "add Read, drop the instruction, or suppress with lint-agent-tool-contract: ok <reason>"
)
SUPPRESSION_RE = re.compile(r"<!--\s*lint-agent-tool-contract:\s*ok\s+(\S[^>]*?)\s*-->")
OUTPUT_MANDATE_MESSAGE = (
    "agent mandates machine-parsed-only output but its prompt has no fail-closed "
    "instruction for unreadable evidence; add a designated cannot-read outcome and "
    "never-invent language, or suppress with lint-agent-output-mandate: ok <reason>"
)
OUTPUT_MANDATE_SUPPRESSION_RE = re.compile(r"<!--\s*lint-agent-output-mandate:\s*ok\s+(\S[^>]*?)\s*-->")
# Detect mandates that the agent's entire output be machine-parsed content.
OUTPUT_MANDATE_RES = (
    re.compile(r"\bstrict\s+JSONL?\b", re.IGNORECASE),
    re.compile(
        r"\b(?:emit|output|return|respond\s+with|reply\s+with)\s+(?:strict\s+|valid\s+)?JSONL?\s+only\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bonly\s+(?:emit|output|return)\s+(?:strict\s+|valid\s+)?JSONL?\b", re.IGNORECASE),
    re.compile(r"\boutput\s+must\s+be\s+(?:strict\s+|valid\s+)?JSONL?\b", re.IGNORECASE),
)
# Detect fail-closed language that disarms the output-mandate finding.
FAIL_CLOSED_RES = (
    re.compile(r"\bnever\s+(?:invent|fabricate|guess)\b", re.IGNORECASE),
    re.compile(r"\bunreadable\b", re.IGNORECASE),
    re.compile(r"\b(?:cannot|can't|could\s+not|unable\s+to)\s+(?:read|open)\b", re.IGNORECASE),
    re.compile(r"\bRead\s+fails\b", re.IGNORECASE),
    re.compile(r"\bfail[\s-]+closed\b", re.IGNORECASE),
)
TOOLS_KEY_RE = re.compile(r"^tools\s*:\s*(.*)$")
BLOCK_LIST_ITEM_RE = re.compile(r"^\s+-\s*(.+)$")

# Detect direct instructions to read named file-like evidence.
READ_FILE_INTENT_RE = re.compile(
    r"\bread\s+(?:the|each|every|all|any|its|their|this|that)\b[^.\n]{0,60}\b"
    r"(?:file|files|bundle|bundles|path|paths|diff|diffs|body|bodies|artifact|artifacts|markdown|log|logs)\b",
    re.IGNORECASE,
)
# Detect open-file or open-bundle imperatives.
OPEN_FILE_INTENT_RE = re.compile(r"\bopen\s+(?:the|each|every)\s+(?:file|bundle)\b", re.IGNORECASE)
# Detect explicit tool-use instructions naming Read.
USE_READ_INTENT_RE = re.compile(r"\buse\s+(?:the\s+)?Read\b", re.IGNORECASE)
READ_INTENT_RES = (READ_FILE_INTENT_RE, OPEN_FILE_INTENT_RE, USE_READ_INTENT_RE)


@dataclass(frozen=True)
class Finding:
    file: str
    lineno: int
    message: str


@dataclass(frozen=True)
class Frontmatter:
    text: str
    body: str
    body_start_line: int


@dataclass(frozen=True)
class ToolsDeclaration:
    explicit_list: bool
    tools: tuple[str, ...]


def _rel(*, path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def iter_agent_files(root: Path) -> list[Path]:
    """Return non-recursive agent definition files in lint scope."""
    files: list[Path] = []
    for pattern in GLOB_PATTERNS:
        files.extend(path for path in sorted(root.glob(pattern)) if path.is_file() and not path.is_symlink())
    return files


def extract_frontmatter(text: str) -> Frontmatter | None:
    """Return leading frontmatter and body, or ``None`` when absent."""
    normalized: str = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return None
    remainder: str = normalized[len("---\n") :]
    end_marker: str = "\n---\n"
    marker_index: int = remainder.find(end_marker)
    if marker_index >= 0:
        frontmatter: str = remainder[:marker_index]
        body: str = remainder[marker_index + len(end_marker) :]
        frontmatter_lines: int = frontmatter.count("\n") + 1
        body_start_line: int = 2 + frontmatter_lines + 1
        return Frontmatter(text=frontmatter, body=body, body_start_line=body_start_line)
    trailing_marker: str = "\n---"
    if remainder.endswith(trailing_marker):
        frontmatter = remainder[: -len(trailing_marker)]
        frontmatter_lines = frontmatter.count("\n") + 1 if frontmatter else 0
        body_start_line = 2 + frontmatter_lines + 1
        return Frontmatter(text=frontmatter, body="", body_start_line=body_start_line)
    return None


def _strip_inline_comment(value: str) -> str:
    return lint_common.strip_inline_comment(value)


def _strip_quotes(value: str) -> str:
    return lint_common.strip_surrounding_quotes(value)


def _split_inline_list(inner: str) -> tuple[str, ...] | None:
    return lint_common.split_quoted_csv(inner)


def _parse_inline_tools(value: str) -> tuple[str, ...] | None:
    stripped: str = _strip_inline_comment(value)
    if not stripped.startswith("["):
        return None
    if not stripped.endswith("]"):
        raise ValueError("malformed inline tools list")
    parsed: tuple[str, ...] | None = _split_inline_list(stripped[1:-1])
    if parsed is None:
        raise ValueError("malformed inline tools list")
    return parsed


def _parse_block_tools(lines: list[str], *, tools_index: int) -> tuple[str, ...]:
    tools: list[str] = []
    for line in lines[tools_index + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            break
        match: re.Match[str] | None = BLOCK_LIST_ITEM_RE.match(line)
        if match is None:
            raise ValueError("malformed block tools list")
        value: str = _strip_inline_comment(match.group(1))
        if not value:
            raise ValueError("malformed block tools list")
        if value.startswith("["):
            parsed: tuple[str, ...] | None = _parse_inline_tools(value)
            if parsed is None:
                raise ValueError("malformed block tools list")
            tools.extend(parsed)
        else:
            tools.append(_strip_quotes(value))
    return tuple(tools)


def parse_tools_declaration(frontmatter: str) -> ToolsDeclaration | None:
    """Return the top-level tools declaration, if one exists."""
    lines: list[str] = frontmatter.split("\n")
    for index, line in enumerate(lines):
        match: re.Match[str] | None = TOOLS_KEY_RE.match(line)
        if match is None:
            continue
        value: str = _strip_inline_comment(match.group(1))
        if value:
            if value.startswith("["):
                return ToolsDeclaration(explicit_list=True, tools=_parse_inline_tools(value) or ())
            return ToolsDeclaration(explicit_list=False, tools=())
        return ToolsDeclaration(explicit_list=True, tools=_parse_block_tools(lines, tools_index=index))
    return None


def first_read_intent_line(body: str, *, body_start_line: int) -> int | None:
    """Return the first body line with read-intent language."""
    for offset, line in enumerate(body.split("\n")):
        if any(pattern.search(line) for pattern in READ_INTENT_RES):
            return body_start_line + offset
    return None


def first_output_mandate_line(body: str, *, body_start_line: int) -> int | None:
    """Return the first body line mandating machine-parsed-only output."""
    for offset, line in enumerate(body.split("\n")):
        if any(pattern.search(line) for pattern in OUTPUT_MANDATE_RES):
            return body_start_line + offset
    return None


def has_fail_closed_language(body: str) -> bool:
    """Return True when the body carries any fail-closed instruction."""
    return any(pattern.search(body) for pattern in FAIL_CLOSED_RES)


def scan_file(path: Path, *, root: Path) -> list[Finding]:
    """Return agent tool-contract findings for one Markdown file."""
    relpath: str = _rel(path=path, root=root)
    try:
        source: str = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"{relpath}: cannot read file: {exc}") from exc
    frontmatter: Frontmatter | None = extract_frontmatter(source)
    if frontmatter is None:
        return []
    try:
        declaration: ToolsDeclaration | None = parse_tools_declaration(frontmatter.text)
    except ValueError as exc:
        raise RuntimeError(f"{relpath}: {exc}") from exc
    findings: list[Finding] = []
    read_line: int | None = first_read_intent_line(frontmatter.body, body_start_line=frontmatter.body_start_line)
    tools_finding_applies: bool = (
        declaration is not None and declaration.explicit_list and "Read" not in declaration.tools
    )
    if tools_finding_applies and read_line is not None and SUPPRESSION_RE.search(source) is None:
        findings.append(Finding(file=relpath, lineno=read_line, message=FINDING_MESSAGE))
    mandate_line: int | None = first_output_mandate_line(frontmatter.body, body_start_line=frontmatter.body_start_line)
    if (
        read_line is not None
        and mandate_line is not None
        and not has_fail_closed_language(frontmatter.body)
        and OUTPUT_MANDATE_SUPPRESSION_RE.search(source) is None
    ):
        findings.append(Finding(file=relpath, lineno=mandate_line, message=OUTPUT_MANDATE_MESSAGE))
    return findings


CLI = RuleCli(prog="cli.py lint agent-tool-contract", description=__doc__)


def _run(root: Path) -> int:
    if not root.is_dir():
        print(f"lint-agent-tool-contract: root directory not found: {root}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    findings: list[Finding] = []
    try:
        for path in iter_agent_files(root):
            findings.extend(scan_file(path, root=root))
    except RuntimeError as exc:
        print(f"lint-agent-tool-contract: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    for finding in sorted(findings, key=lambda item: (item.file, item.lineno)):
        print(f"{finding.file}:{finding.lineno}: {finding.message}")
    return 1 if findings else 0


def main(argv: list[str] | None = None) -> int:
    return run_root_cli(argv if argv is not None else sys.argv[1:], cli=CLI, action=_run)


if __name__ == "__main__":
    raise SystemExit(main())
