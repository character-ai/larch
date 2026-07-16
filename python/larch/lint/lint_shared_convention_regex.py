"""Reject duplicate convention regexes that should use shared owners.

Scans production modules under ``python/larch/**/*.py`` for copied
architectural-guideline heading regexes, module-level ``[BUG] in:title``
selector constants, and lifecycle-prefix stripping loops. The owners remain
the single source of truth:
``larch.core.architectural_guidelines`` for heading readers and
``larch.issue.title_match`` for bug-title predicates.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from larch.issue.title_match import BUG_PREFIX
from larch.lint.engine import RuleCli, run_root_cli

TOOL_FAILURE_EXIT = 2
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__", "tests"})
ALLOWLIST_RELPATHS = frozenset({"larch/core/architectural_guidelines.py", "larch/issue/title_match.py", "larch/review/review_types.py"})
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


def _is_re_pattern_call(node: ast.Call) -> bool:
    call_name = _call_name(node)
    return call_name is not None and call_name[0] == "re" and call_name[1] in {"compile", "search", "match", "findall", "finditer", "split"}


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




def _looks_like_reviewer_item_heading_regex(value: str) -> bool:
    has_item_token = "FINDING_" in value or "OOS_" in value or "(?:FINDING|OOS)" in value or "(?:OOS|FINDING)" in value
    has_markdown_heading = "###" in value or "^#" in value or r"\A#" in value
    has_numeric_id = r"\d" in value or "[0-9]" in value
    # Block segmentation: lookahead/end-anchor form (.*? + lookahead or \Z)
    has_block_segmentation = ".*?" in value and ("(?=" in value or r"\Z" in value)
    # Block segmentation: inline-multiline .*$ form used as item boundary sentinel
    has_block_seg_multiline = "(?m" in value and ".*$" in value
    # Full canonical heading parse: extracts kind/number/title via (.*?) capture
    has_full_heading_parse = has_item_token and "(.*?)" in value and ("MULTILINE" not in value)
    # Canonical numeric-ID capture: extracts OOS_N or FINDING_N number via (\d+) group
    has_canonical_id_capture = (
        (r"OOS_(\d" in value or r"FINDING_(\d" in value) and has_markdown_heading
    )
    return has_item_token and has_markdown_heading and has_numeric_id and (
        has_block_segmentation or has_block_seg_multiline or has_full_heading_parse or has_canonical_id_capture
    )


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
    if _looks_like_reviewer_item_heading_regex(value):
        findings.append(
            Finding(
                file=normalized_file,
                lineno=lineno,
                context="reviewer-item-heading-regex",
                guidance="use review_types.parse_blocks or review_types.parse_canonical_heading",
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
        if not isinstance(node, ast.Call) or not _is_re_pattern_call(node) or not node.args:
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


def _slice_uses_loop_variable(node: ast.Subscript, *, loop_variable: str) -> bool:
    slice_node: ast.AST = node.slice
    for descendant in ast.walk(slice_node):
        if not isinstance(descendant, ast.Call) or not isinstance(descendant.func, ast.Name):
            continue
        if descendant.func.id != "len" or len(descendant.args) != 1:
            continue
        argument: ast.expr = descendant.args[0]
        if isinstance(argument, ast.Name) and argument.id == loop_variable:
            return True
    return False


def _starts_with_loop_variable(node: ast.AST, *, loop_variable: str) -> bool:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr != "startswith" or not node.args:
        return False
    argument: ast.expr = node.args[0]
    return isinstance(argument, ast.Name) and argument.id == loop_variable


def _lifecycle_prefix_strip_findings(tree: ast.Module, *, normalized_file: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        if not isinstance(node.iter, ast.Name) or "LIFECYCLE_PREFIXES" not in node.iter.id:
            continue
        loop_variable = node.target.id
        has_strip_logic = False
        for descendant in ast.walk(node):
            if _starts_with_loop_variable(descendant, loop_variable=loop_variable):
                has_strip_logic = True
            if isinstance(descendant, ast.Subscript) and _slice_uses_loop_variable(
                descendant, loop_variable=loop_variable
            ):
                has_strip_logic = True
        if has_strip_logic:
            lineno_value: object = getattr(node, "lineno", 0)
            lineno: int = lineno_value if isinstance(lineno_value, int) else 0
            findings.append(
                Finding(
                    file=normalized_file,
                    lineno=lineno,
                    context="lifecycle-prefix-strip-loop",
                    guidance="use title_match.strip_lifecycle_prefix or title_match.detect_lifecycle_prefix",
                )
            )
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
    findings.extend(_lifecycle_prefix_strip_findings(tree, normalized_file=normalized_file))
    return [finding for finding in findings if not _is_suppressed(finding, comments_by_line=comments_by_line)]


CLI = RuleCli(prog="cli.py lint shared-convention-regex", description=__doc__)


def _run(root: Path) -> int:
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


def main(argv: list[str] | None = None) -> int:
    return run_root_cli(argv if argv is not None else sys.argv[1:], cli=CLI, action=_run)


if __name__ == "__main__":
    raise SystemExit(main())
