"""Shared scan-only lint pipeline (models, discovery, detect, render).

Unregistered library surface: no CLI, baseline I/O, or write mode. Callers
supply a ``LintRule`` and an injected ``Runner``; ``run_rule`` prints findings
to stdout and diagnostics to stderr, then returns 0 / 1 / 2.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from larch.core.proc import CommandResult, Runner

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2
SYNTAX_FAIL_MESSAGE = "unable to parse Python"
GIT_DIAGNOSTIC_MAX_CHARS = 200
SyntaxPolicy = Literal["fail", "skip"]


class ScanError(Exception):
    """Expected scan failure with a deterministic stderr diagnostic."""


@dataclass
class _PythonAstState:
    """Mutable AST probe cache held by a frozen ``SourceFile``."""

    probed: bool = False
    tree: ast.AST | None = None
    error: SyntaxError | None = None


@dataclass(frozen=True)
class Finding:
    """One lint finding ready for suppression, dedupe, sort, and render."""

    path: str
    line: int
    rule_id: str
    message: str
    qualified_symbol: str | None = None
    metric: int | None = None


@dataclass(frozen=True)
class SourceFile:
    """Loaded source with immutable lines and a lazy Python AST cache."""

    path: str
    text: str
    lines: tuple[str, ...]
    _ast_state: _PythonAstState = field(
        default_factory=_PythonAstState,
        repr=False,
        compare=False,
        hash=False,
    )

    @property
    def is_python(self) -> bool:
        return self.path.endswith(".py")

    def _probe_python(self) -> None:
        state = self._ast_state
        if state.probed:
            return
        state.probed = True
        try:
            state.tree = ast.parse(self.text, filename=self.path)
        except SyntaxError as exc:
            state.error = exc

    def python_syntax_error(self) -> SyntaxError | None:
        """Probe once and return a cached ``SyntaxError`` for Python sources."""
        if not self.is_python:
            return None
        self._probe_python()
        return self._ast_state.error

    @property
    def python_ast(self) -> ast.AST:
        if not self.is_python:
            msg = f"no Python AST for non-Python source: {self.path}"
            raise TypeError(msg)
        self._probe_python()
        state = self._ast_state
        if state.error is not None:
            raise state.error
        if state.tree is None:
            msg = f"Python AST probe produced no tree for {self.path}"
            raise RuntimeError(msg)
        return state.tree


@dataclass(frozen=True)
class LintRule:
    """Detect-function rule configuration for ``run_rule``."""

    rule_id: str
    description: str
    detect: Callable[[SourceFile], object]
    syntax_policy: SyntaxPolicy
    suppression_token: str


def _is_single_line(value: str) -> bool:
    return bool(value) and "\n" not in value and "\r" not in value


def _validate_rule(rule: LintRule) -> None:
    if not _is_single_line(rule.rule_id):
        raise ScanError("lint rule rule_id must be a non-empty single-line string")
    if not _is_single_line(rule.suppression_token):
        raise ScanError(
            "lint rule suppression_token must be a non-empty single-line string"
        )
    if rule.syntax_policy not in ("fail", "skip"):
        raise ScanError(
            f"lint rule syntax_policy is unsupported: {rule.syntax_policy!r}"
        )


def _bounded_git_detail(result: CommandResult) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    if not detail:
        return f"git exited {result.returncode}"
    first_line = detail.splitlines()[0].strip()
    if len(first_line) > GIT_DIAGNOSTIC_MAX_CHARS:
        return first_line[:GIT_DIAGNOSTIC_MAX_CHARS]
    return first_line


def _validate_repo_root(root: Path, runner: Runner) -> Path:
    if not root.exists():
        raise ScanError(f"repository root does not exist: {root}")
    if not root.is_dir():
        raise ScanError(f"repository root is not a directory: {root}")
    resolved = root.resolve()
    result = runner.run(
        ("git", "rev-parse", "--show-toplevel"),
        cwd=str(resolved),
    )
    if result.returncode != 0:
        raise ScanError(
            f"git rev-parse --show-toplevel failed: {_bounded_git_detail(result)}"
        )
    raw = result.stdout.strip()
    if not raw or "\n" in raw or "\r" in raw:
        raise ScanError("git rev-parse --show-toplevel returned malformed output")
    reported = Path(raw).resolve()
    if reported != resolved:
        raise ScanError(
            f"repository root is not the git work-tree top-level: {resolved} != {reported}"
        )
    return resolved


def _discover_tracked_paths(root: Path, runner: Runner) -> list[str]:
    result = runner.run(("git", "ls-files", "--cached"), cwd=str(root))
    if result.returncode != 0:
        raise ScanError(f"git ls-files --cached failed: {_bounded_git_detail(result)}")
    seen: set[str] = set()
    ordered: list[str] = []
    for raw_line in result.stdout.splitlines():
        entry = raw_line.strip("\0")
        if entry == "":
            raise ScanError("git ls-files --cached returned a blank path record")
        rel = _normalize_repo_relative_path(entry, root=root, label="discovered path")
        if rel in seen:
            continue
        seen.add(rel)
        ordered.append(rel)
    return ordered


def _normalize_repo_relative_path(raw: str, *, root: Path, label: str) -> str:
    if not _is_single_line(raw.strip()):
        raise ScanError(f"{label} must be a non-empty single-line path")
    candidate = raw.strip().replace("\\", "/")
    while candidate.startswith("./"):
        candidate = candidate[2:]
    if candidate in {"", "."}:
        raise ScanError(f"{label} is empty after normalization")
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:/", candidate):
        raise ScanError(f"{label} must be repository-relative: {raw}")
    parts = Path(candidate).parts
    if ".." in parts:
        raise ScanError(f"{label} must not contain '..': {raw}")
    path_in_repo = root / candidate
    if path_in_repo.is_symlink():
        raise ScanError(f"{label} is a symlink: {raw}")
    absolute = path_in_repo.resolve()
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise ScanError(f"{label} escapes repository root: {raw}") from exc
    if not absolute.exists():
        raise ScanError(f"{label} does not exist: {raw}")
    if not absolute.is_file() or absolute.is_symlink():
        raise ScanError(f"{label} is not a regular file: {raw}")
    return relative.as_posix()


def _validate_requested_path(raw: str | Path, *, root: Path) -> tuple[str, bool]:
    """Return ``(repo_relative_posix, is_directory)`` for a requested path."""
    text = str(raw).strip()
    if not _is_single_line(text):
        raise ScanError(f"requested path must be a non-empty single-line path: {raw!r}")
    path = Path(text)
    absolute = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise ScanError(f"requested path escapes repository root: {raw}") from exc
    if absolute.is_symlink():
        raise ScanError(f"requested path is a symlink: {raw}")
    if not absolute.exists():
        raise ScanError(f"requested path does not exist: {raw}")
    if absolute.is_dir():
        return relative.as_posix(), True
    if absolute.is_file():
        if absolute.is_symlink():
            raise ScanError(f"requested path is a symlink: {raw}")
        return relative.as_posix(), False
    raise ScanError(f"requested path is not a file or directory: {raw}")


def _filter_tracked_paths(
    tracked: Sequence[str],
    *,
    root: Path,
    paths: Sequence[str | Path] | None,
) -> list[str]:
    if paths is None:
        return list(tracked)
    selectors: list[tuple[str, bool]] = [
        _validate_requested_path(item, root=root) for item in paths
    ]
    selected: list[str] = []
    seen: set[str] = set()
    for rel in tracked:
        for selector, is_dir in selectors:
            matched = rel == selector or (
                is_dir and (selector == "." or rel.startswith(f"{selector}/"))
            )
            if matched and rel not in seen:
                seen.add(rel)
                selected.append(rel)
                break
    return selected


def _load_source(root: Path, rel_path: str) -> SourceFile:
    absolute = root / rel_path
    try:
        raw = absolute.read_bytes()
    except OSError as exc:
        raise ScanError(f"failed to read {rel_path}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ScanError(f"failed to decode {rel_path} as UTF-8: {exc}") from exc
    return SourceFile(path=rel_path, text=text, lines=tuple(text.splitlines()))


def _syntax_finding_line(source: SourceFile, error: SyntaxError) -> int:
    lineno = error.lineno
    if (
        isinstance(lineno, int)
        and not isinstance(lineno, bool)
        and 1 <= lineno <= len(source.lines)
    ):
        return lineno
    return 1


def _comment_tokens_by_line(source: str) -> dict[int, tuple[str, ...]]:
    comments: dict[int, list[str]] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.setdefault(token.start[0], []).append(token.string)
    except tokenize.TokenError:
        return {}
    return {line: tuple(values) for line, values in comments.items()}


def _suppression_reason(
    lineno: int,
    *,
    comments_by_line: Mapping[int, tuple[str, ...]],
    pragma_re: re.Pattern[str],
    empty_pragma_re: re.Pattern[str],
) -> str | None:
    for comment in comments_by_line.get(lineno, ()):
        match = pragma_re.search(comment)
        if match is not None:
            return match.group(1).strip()
        if empty_pragma_re.search(comment) is not None:
            return ""
    return None


def _validate_metric(metric: object) -> int | None:
    if metric is None:
        return None
    if type(metric) is not int or metric < 0:
        raise ScanError("finding metric must be a non-negative int when present")
    return metric


def _validate_finding(
    finding: object, *, source: SourceFile, rule: LintRule
) -> Finding:
    if not isinstance(finding, Finding):
        raise ScanError("detector must return Finding instances")
    path = finding.path
    line = finding.line
    rule_id = finding.rule_id
    message = finding.message
    qualified_symbol = finding.qualified_symbol
    if path != source.path:
        raise ScanError(f"finding path {path!r} does not match source {source.path!r}")
    if rule_id != rule.rule_id:
        raise ScanError(
            f"finding rule_id {rule_id!r} does not match active rule {rule.rule_id!r}"
        )
    if type(line) is not int or line < 1 or line > len(source.lines):
        raise ScanError(
            f"finding line {line!r} is out of range for {source.path} "
            f"({len(source.lines)} lines)"
        )
    if not _is_single_line(message):
        raise ScanError("finding message must be a non-empty single-line string")
    if not _is_single_line(rule_id):
        raise ScanError("finding rule_id must be a non-empty single-line string")
    if not _is_single_line(path):
        raise ScanError("finding path must be a non-empty single-line string")
    if qualified_symbol is not None and not _is_single_line(qualified_symbol):
        raise ScanError(
            "finding qualified_symbol must be a non-empty single-line string when present"
        )
    metric = _validate_metric(finding.metric)
    return Finding(
        path=path,
        line=line,
        rule_id=rule_id,
        message=message,
        qualified_symbol=qualified_symbol,
        metric=metric,
    )


def _dedupe_and_sort(findings: Sequence[Finding]) -> list[Finding]:
    seen: set[tuple[str, int, str, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.path, finding.line, finding.rule_id, finding.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    unique.sort(key=lambda item: (item.path, item.line, item.rule_id, item.message))
    return unique


def render_finding(finding: Finding) -> str:
    """Render one finding as ``path:line: RULE_ID message``."""
    return f"{finding.path}:{finding.line}: {finding.rule_id} {finding.message}"


def _scan_source(
    source: SourceFile,
    *,
    rule: LintRule,
    pragma_re: re.Pattern[str],
    empty_pragma_re: re.Pattern[str],
) -> list[Finding]:
    if source.is_python:
        syntax_error = source.python_syntax_error()
        if syntax_error is not None:
            if rule.syntax_policy == "skip":
                return []
            return [
                Finding(
                    path=source.path,
                    line=_syntax_finding_line(source, syntax_error),
                    rule_id=rule.rule_id,
                    message=SYNTAX_FAIL_MESSAGE,
                )
            ]
    try:
        raw_findings: object = rule.detect(source)
    except ScanError:
        raise
    except Exception as exc:
        raise ScanError(f"detector raised for {source.path}: {exc}") from exc
    if not isinstance(raw_findings, list):
        raise ScanError("detector must return a list of Finding")

    comments_by_line = _comment_tokens_by_line(source.text)
    accepted: list[Finding] = []
    for item in cast("list[object]", raw_findings):
        finding = _validate_finding(item, source=source, rule=rule)
        reason = _suppression_reason(
            finding.line,
            comments_by_line=comments_by_line,
            pragma_re=pragma_re,
            empty_pragma_re=empty_pragma_re,
        )
        if reason is None:
            accepted.append(finding)
            continue
        if reason == "":
            raise ScanError(
                f"{source.path}:{finding.line}: suppression pragma "
                f"{rule.suppression_token!r} requires a non-empty reason"
            )
    return accepted


def run_rule(
    rule: LintRule,
    root: str | Path,
    runner: Runner,
    paths: Sequence[str | Path] | None = None,
) -> int:
    """Run one lint rule over tracked files under ``root``.

    Returns ``0`` for a clean scan, ``1`` when findings are printed to stdout,
    and ``2`` when a validation or execution error is printed to stderr.
    Does not create or modify repository files.
    """
    try:
        _validate_rule(rule)
        repo_root = _validate_repo_root(Path(root), runner)
        tracked = _discover_tracked_paths(repo_root, runner)
        selected = _filter_tracked_paths(tracked, root=repo_root, paths=paths)
        pragma_re = re.compile(
            rf"#\s*{re.escape(rule.suppression_token)}:\s*ok\s+(\S.*)$"
        )
        empty_pragma_re = re.compile(
            rf"#\s*{re.escape(rule.suppression_token)}:\s*ok\s*$"
        )
        collected: list[Finding] = []
        for rel_path in selected:
            source = _load_source(repo_root, rel_path)
            collected.extend(
                _scan_source(
                    source,
                    rule=rule,
                    pragma_re=pragma_re,
                    empty_pragma_re=empty_pragma_re,
                )
            )
        findings = _dedupe_and_sort(collected)
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR

    if not findings:
        return EXIT_CLEAN
    for finding in findings:
        print(render_finding(finding), file=sys.stdout)
    return EXIT_FINDINGS
