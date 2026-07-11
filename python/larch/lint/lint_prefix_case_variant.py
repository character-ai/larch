"""Reject case-variant lifecycle and bug title-prefix tokens on text surfaces.

Scans Markdown under ``skills/``, ``.claude/skills/``, and ``agents/``, plus the
residual Bash inventory, for bracketed tokens whose casefolded form matches a
canonical lifecycle or bug prefix but whose original bytes differ. Exact-case
canonical tokens remain allowed. There is no baseline; suppressions require a
non-empty trailing reason.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from larch.core.residual_bash import read_residual_paths
from larch.lint.lint_lifecycle_prefix_literal import TokenInfo, build_token_map
from larch.lint.lint_lifecycle_prefix_literal import BaselineError as TokenMapError

TOOL_FAILURE_EXIT = 2
MARKDOWN_ROOTS = ("skills", ".claude/skills", "agents")
BRACKET_TOKEN_RE = re.compile(r"\[[^\[\]]+\]")
MARKDOWN_PRAGMA_RE = re.compile(
    r"<!--\s*lint-prefix-case-variant:\s*ok\s+(\S.*?)\s*-->\s*$"
)
BASH_PRAGMA_RE = re.compile(r"#\s*lint-prefix-case-variant:\s*ok\s+(\S.*)$")


@dataclass(frozen=True)
class Finding:
    file: str
    lineno: int
    observed: str
    canonical: str


class LintError(RuntimeError):
    """Raised when discovery or file reads cannot be trusted."""


def _rel(*, path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def iter_markdown_files(root: Path) -> list[Path]:
    """Return sorted regular Markdown files under the configured prompt roots."""
    files: list[Path] = []
    seen: set[Path] = set()
    for rel_root in MARKDOWN_ROOTS:
        base: Path = root / rel_root
        if not base.exists():
            continue
        if base.is_symlink() or not base.is_dir():
            raise LintError(f"markdown root is not a regular directory: {rel_root}")
        for path in sorted(base.rglob("*.md")):
            if path.is_symlink() or not path.is_file():
                raise LintError(f"markdown scan target is not a regular file: {_rel(path=path, root=root)}")
            resolved: Path = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return sorted(files, key=lambda path: _rel(path=path, root=root))


def iter_residual_bash_files(root: Path) -> list[Path]:
    """Return residual Bash paths as regular files, fail-closed on bad targets."""
    try:
        rel_paths: list[str] = read_residual_paths(root, check_exists=True)
    except (RuntimeError, ValueError) as exc:
        raise LintError(str(exc)) from exc
    files: list[Path] = []
    seen: set[Path] = set()
    for rel in rel_paths:
        path: Path = root / rel
        if path.is_symlink() or not path.is_file():
            raise LintError(f"residual bash path is not a regular file: {rel}")
        resolved: Path = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(path)
    return files


def _line_suppressed(line: str, *, markdown: bool) -> bool:
    pattern: re.Pattern[str] = MARKDOWN_PRAGMA_RE if markdown else BASH_PRAGMA_RE
    match: re.Match[str] | None = pattern.search(line)
    if match is None:
        return False
    return bool(match.group(1).strip())


def _findings_for_line(
    line: str,
    *,
    file_name: str,
    lineno: int,
    token_infos: Mapping[str, TokenInfo],
    markdown: bool,
) -> list[Finding]:
    if _line_suppressed(line, markdown=markdown):
        return []
    findings: list[Finding] = []
    for match in BRACKET_TOKEN_RE.finditer(line):
        observed: str = match.group(0)
        info: TokenInfo | None = token_infos.get(observed.casefold())
        if info is None:
            continue
        if observed == info.token:
            continue
        findings.append(
            Finding(
                file=file_name,
                lineno=lineno,
                observed=observed,
                canonical=info.token,
            )
        )
    return findings


def scan_text_file(
    path: Path,
    *,
    root: Path,
    token_infos: Mapping[str, TokenInfo],
    markdown: bool,
) -> list[Finding]:
    """Return case-variant findings for one Markdown or Bash text file."""
    file_name: str = _rel(path=path, root=root)
    try:
        source: str = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LintError(f"{file_name}: cannot read source: {exc}") from exc
    findings: list[Finding] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        findings.extend(
            _findings_for_line(
                line,
                file_name=file_name,
                lineno=lineno,
                token_infos=token_infos,
                markdown=markdown,
            )
        )
    return findings


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint prefix-case-variant", description=__doc__
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    parsed: argparse.Namespace | None = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root: Path = Path(str(parsed.root)).resolve()
    if not root.is_dir():
        print(f"lint-prefix-case-variant: root is not a directory: {root}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        token_infos: dict[str, TokenInfo] = build_token_map()
    except TokenMapError as exc:
        print(f"lint-prefix-case-variant: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if not token_infos:
        print("lint-prefix-case-variant: canonical token map is empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    findings: list[Finding] = []
    try:
        for path in iter_markdown_files(root):
            findings.extend(
                scan_text_file(path, root=root, token_infos=token_infos, markdown=True)
            )
        for path in iter_residual_bash_files(root):
            findings.extend(
                scan_text_file(path, root=root, token_infos=token_infos, markdown=False)
            )
    except LintError as exc:
        print(f"lint-prefix-case-variant: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    for finding in sorted(findings, key=lambda item: (item.file, item.lineno, item.observed)):
        print(
            f"{finding.file}: line {finding.lineno} matched {finding.observed}; "
            f"use exact-case {finding.canonical}",
            file=sys.stderr,
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
