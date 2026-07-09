"""Reject duplicate convention regexes that should use shared owners.

Scans production modules under ``python/larch/**/*.py`` for copied
architectural-guideline heading regexes and module-level ``[BUG] in:title``
selector constants. The owners remain the single source of truth:
``larch.core.architectural_guidelines`` for heading readers and
``larch.issue.title_match`` for bug-title predicates.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from larch.issue.title_match import BUG_PREFIX

TOOL_FAILURE_EXIT = 2
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__", "tests"})
ALLOWLIST_RELPATHS = frozenset({"larch/core/architectural_guidelines.py", "larch/issue/title_match.py"})
LINT_MODULE_RELPATH = "larch/lint/lint_shared_convention_regex.py"
PRAGMA_RE = re.compile(r"#\s*lint-shared-convention-regex:\s*ok\s+(\S.*)$")


@dataclass(frozen=True)
class Finding:
    file: str
    lineno: int
    context: str
    guidance: str


def is_exempt_path(path: Path) -> bool:
    """Return whether a Python path is outside production lint scope."""
    name: str = path.name
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def iter_source_files(larch_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under larch/, sorted."""
    result: list[Path] = []
    for path in sorted(larch_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink() or is_exempt_path(path):
            continue
        relative: Path = path.relative_to(larch_dir.parent)
        normalized: str = relative.as_posix()
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        if normalized in ALLOWLIST_RELPATHS or normalized == LINT_MODULE_RELPATH:
            continue
        result.append(path)
    return result


def _literal_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _call_name(node: ast.Call) -> tuple[str, str] | None:
    func: ast.expr = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return (func.value.id, func.attr)
    return None


def _is_re_compile_call(node: ast.Call) -> bool:
    return _call_name(node) == ("re", "compile")


def _looks_like_guideline_heading_regex(value: str) -> bool:
    has_heading_anchor: bool = value.startswith(("^#", r"\A#"))
    has_guideline_id: bool = "G-" in value and r"\d" in value
    has_markdown_separator: bool = ":" in value and r"\s" in value
    return has_heading_anchor and has_guideline_id and has_markdown_separator


def _looks_like_invariant_heading_regex(value: str) -> bool:
    has_heading_anchor: bool = value.startswith(("^#", r"\A#"))
    has_invariant_id: bool = ("I-" in value or "INV-" in value) and r"\d" in value
    has_markdown_separator: bool = ":" in value and r"\s" in value
    return has_heading_anchor and has_invariant_id and has_markdown_separator


def _heading_findings_for_value(*, value: str, normalized_file: str, lineno: int) -> list[Finding]:
    findings: list[Finding] = []
    if _looks_like_guideline_heading_regex(value):
        findings.append(
            Finding(
                file=normalized_file,
                lineno=lineno,
                context="guideline-heading-regex",
                guidance="use architectural_guidelines.GUIDELINE_HEADING_RE",
            )
        )
    if _looks_like_invariant_heading_regex(value):
        findings.append(
            Finding(
                file=normalized_file,
                lineno=lineno,
                context="invariant-heading-regex",
                guidance="use architectural_guidelines.INVARIANT_HEADING_RE",
            )
        )
    return findings


def _module_assignment_value(node: ast.stmt) -> str | None:
    if isinstance(node, ast.Assign):
        return _literal_text(node.value)
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        return _literal_text(node.value)
    return None


def _bug_selector_finding_for_assignment(*, node: ast.stmt, normalized_file: str) -> Finding | None:
    value: str | None = _module_assignment_value(node)
    if value is None:
        return None
    if BUG_PREFIX not in value or "in:title" not in value:
        return None
    lineno_value: object = getattr(node, "lineno", 0)
    lineno: int = lineno_value if isinstance(lineno_value, int) else 0
    return Finding(
        file=normalized_file,
        lineno=lineno,
        context="bug-title-selector",
        guidance="use title_match.bug_title_match or title_match.BUG_PREFIX",
    )


def _compile_call_findings(tree: ast.Module, *, normalized_file: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_re_compile_call(node) or not node.args:
            continue
        pattern: str | None = _literal_text(node.args[0])
        if pattern is None:
            continue
        lineno_value: object = getattr(node, "lineno", 0)
        lineno: int = lineno_value if isinstance(lineno_value, int) else 0
        findings.extend(
            _heading_findings_for_value(value=pattern, normalized_file=normalized_file, lineno=lineno)
        )
    return findings


def _module_assignment_findings(tree: ast.Module, *, normalized_file: str) -> list[Finding]:
    findings: list[Finding] = []
    for statement in tree.body:
        value: str | None = _module_assignment_value(statement)
        if value is not None:
            lineno_value: object = getattr(statement, "lineno", 0)
            lineno: int = lineno_value if isinstance(lineno_value, int) else 0
            findings.extend(
                _heading_findings_for_value(value=value, normalized_file=normalized_file, lineno=lineno)
            )
        bug_finding: Finding | None = _bug_selector_finding_for_assignment(
            node=statement, normalized_file=normalized_file
        )
        if bug_finding is not None:
            findings.append(bug_finding)
    return findings


def _comment_tokens_by_line(source: str) -> dict[int, tuple[str, ...]]:
    comments: dict[int, list[str]] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.setdefault(token.start[0], []).append(token.string)
    except tokenize.TokenError:
        return {}
    return {line: tuple(values) for line, values in comments.items()}


def _is_suppressed(finding: Finding, *, comments_by_line: Mapping[int, tuple[str, ...]]) -> bool:
    return any(PRAGMA_RE.search(comment) for comment in comments_by_line.get(finding.lineno, ()))


def scan_file(path: Path, *, larch_dir: Path) -> list[Finding]:
    """Return shared-convention duplicate findings for one source file."""
    normalized_file: str = path.relative_to(larch_dir.parent).as_posix()
    try:
        source: str = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"{normalized_file}: cannot read source: {exc}") from exc
    try:
        tree: ast.Module = ast.parse(source)
    except SyntaxError as exc:
        raise RuntimeError(f"{normalized_file}: cannot parse source: {exc}") from exc
    comments_by_line: dict[int, tuple[str, ...]] = _comment_tokens_by_line(source)
    findings: list[Finding] = []
    findings.extend(_module_assignment_findings(tree, normalized_file=normalized_file))
    findings.extend(_compile_call_findings(tree, normalized_file=normalized_file))
    return [finding for finding in findings if not _is_suppressed(finding, comments_by_line=comments_by_line)]


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint shared-convention-regex", description=__doc__
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
    larch_dir: Path = root / "python" / "larch"
    if not larch_dir.is_dir():
        print(f"lint-shared-convention-regex: larch directory not found: {larch_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    findings: list[Finding] = []
    try:
        for path in iter_source_files(larch_dir):
            findings.extend(scan_file(path, larch_dir=larch_dir))
    except RuntimeError as exc:
        print(f"lint-shared-convention-regex: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    for finding in sorted(findings, key=lambda item: (item.file, item.lineno, item.context)):
        print(
            f"{finding.file}: line {finding.lineno} matched {finding.context}; {finding.guidance}",
            file=sys.stderr,
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
