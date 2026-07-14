"""Shared scan-only lint pipeline (models, discovery, detect, render).

Unregistered library surface: no CLI. Callers supply a ``LintRule`` and an
injected ``Runner``; ``run_rule`` supports scan-only, baseline-check, and
guarded baseline-write modes, prints findings to stdout and diagnostics to
stderr, then returns 0 / 1 / 2.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import stat
import sys
import tokenize
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias, cast

from larch import io as larch_io
from larch.core.proc import CommandResult, Runner

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2
SYNTAX_FAIL_MESSAGE = "unable to parse Python"
GIT_DIAGNOSTIC_MAX_CHARS = 200
SyntaxPolicy = Literal["fail", "skip"]


class ScanError(Exception):
    """Expected scan failure with a deterministic stderr diagnostic."""


class StrictStaleError(ScanError):
    """A strict stale failure that retains its stable warning diagnostics."""

    def __init__(self, warnings: Sequence[str]) -> None:
        super().__init__("strict_stale rejected stale baseline rows")
        self.warnings = warnings


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
    anchor: str | None = None


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
    allow_inline_suppression: bool = True


def _is_single_line(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and "\n" not in value
        and "\r" not in value
        and "\0" not in value
    )


def _is_exact_bool(value: object) -> bool:
    return isinstance(value, bool)


def _validate_rule(rule: LintRule) -> None:
    if not _is_single_line(rule.rule_id):
        raise ScanError("lint rule rule_id must be a non-empty single-line string")
    if not _is_exact_bool(rule.allow_inline_suppression):
        raise ScanError("lint rule allow_inline_suppression must be a bool")
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
    raw = result.stdout.removesuffix("\n")
    if not raw or "\0" in raw or "\n" in raw or "\r" in raw:
        raise ScanError("git rev-parse --show-toplevel returned malformed output")
    reported = Path(raw).resolve()
    if reported != resolved:
        raise ScanError(
            f"repository root is not the git work-tree top-level: {resolved} != {reported}"
        )
    return resolved


def _discover_tracked_paths(
    root: Path,
    runner: Runner,
    *,
    pathspecs: Sequence[str] | None = None,
) -> list[str]:
    # Scope ls-files when callers pass pathspecs so sparse checkouts that omit
    # unrelated trees (for example CI excluding larch-logs/) do not fail
    # existence checks on out-of-scope cached paths.
    argv: list[str] = ["git", "ls-files", "--cached", "-z"]
    if pathspecs is not None:
        argv.append("--")
        argv.extend(pathspecs)
    result = runner.run(tuple(argv), cwd=str(root))
    if result.returncode != 0:
        raise ScanError(f"git ls-files --cached failed: {_bounded_git_detail(result)}")
    seen: set[str] = set()
    ordered: list[str] = []
    if result.stdout and not result.stdout.endswith("\0"):
        raise ScanError("git ls-files --cached returned an unterminated path record")
    records = result.stdout.removesuffix("\0").split("\0") if result.stdout else []
    for entry in records:
        if entry == "":
            raise ScanError("git ls-files --cached returned a blank path record")
        rel = _normalize_repo_relative_path(entry, root=root, label="discovered path")
        if rel in seen:
            continue
        seen.add(rel)
        ordered.append(rel)
    return ordered


def _normalize_repo_relative_path(raw: str, *, root: Path, label: str) -> str:
    if not _is_single_line(raw):
        raise ScanError(f"{label} must be a non-empty single-line path")
    candidate = raw
    if candidate in {"", "."}:
        raise ScanError(f"{label} must not be empty or current-directory")
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:/", candidate):
        raise ScanError(f"{label} must be repository-relative: {raw}")
    parts = Path(candidate).parts
    if "." in parts or ".." in parts:
        raise ScanError(f"{label} must not contain '.' or '..': {raw}")
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
    text = str(raw)
    if not _is_single_line(text):
        raise ScanError(f"requested path must be a non-empty single-line path: {raw!r}")
    path = Path(text)
    if path.is_absolute() or re.match(r"^[A-Za-z]:/", text):
        raise ScanError(f"requested path must be repository-relative: {raw}")
    if ".." in path.parts:
        raise ScanError(f"requested path must not contain '..': {raw}")
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
    rel_path = _normalize_repo_relative_path(rel_path, root=root, label="source path")
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        directory_flags = flags | getattr(os, "O_DIRECTORY", 0)
        descriptor = os.open(root, directory_flags)
        try:
            for part in Path(rel_path).parts[:-1]:
                next_descriptor = os.open(part, directory_flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = next_descriptor
            file_descriptor = os.open(Path(rel_path).name, flags, dir_fd=descriptor)
        finally:
            os.close(descriptor)
        descriptor = file_descriptor
    except OSError as exc:
        raise ScanError(f"failed to read {rel_path}: {exc}") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ScanError(f"source path is not a regular file: {rel_path}")
        with os.fdopen(descriptor, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        with suppress(OSError):
            os.close(descriptor)
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
    except IndentationError as exc:
        raise ScanError("failed to tokenize source: indentation error") from exc
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
    if not isinstance(metric, int) or isinstance(metric, bool) or metric < 0:
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
    anchor = finding.anchor
    if path != source.path:
        raise ScanError(f"finding path {path!r} does not match source {source.path!r}")
    if rule_id != rule.rule_id:
        raise ScanError(
            f"finding rule_id {rule_id!r} does not match active rule {rule.rule_id!r}"
        )
    if isinstance(line, bool) or line < 1 or line > len(source.lines):
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
    if anchor is not None and not _is_single_line(anchor):
        raise ScanError("finding anchor must be a non-empty single-line string when present")
    metric = _validate_metric(finding.metric)
    return Finding(
        path=path,
        line=line,
        rule_id=rule_id,
        message=message,
        qualified_symbol=qualified_symbol,
        metric=metric,
        anchor=anchor,
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


def _validated_findings(
    raw_findings: Sequence[object],
    *,
    source: SourceFile,
    rule: LintRule,
) -> list[Finding]:
    return [
        _validate_finding(item, source=source, rule=rule) for item in raw_findings
    ]


def _apply_inline_suppressions(
    findings: Sequence[Finding],
    *,
    source: SourceFile,
    rule: LintRule,
    pragma_re: re.Pattern[str],
    empty_pragma_re: re.Pattern[str],
) -> list[Finding]:
    comments_by_line = _comment_tokens_by_line(source.text)
    accepted: list[Finding] = []
    for finding in findings:
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

    validated = _validated_findings(
        cast("list[object]", raw_findings), source=source, rule=rule
    )
    if not rule.allow_inline_suppression:
        return validated
    return _apply_inline_suppressions(
        validated,
        source=source,
        rule=rule,
        pragma_re=pragma_re,
        empty_pragma_re=empty_pragma_re,
    )


BaselineKind = Literal["generic", "symbol_metric"]


@dataclass(frozen=True)
class GenericBaselineRow:
    """A location-specific baseline row."""

    path: str
    line: int
    rule_id: str
    message: str
    reason: str
    anchor: str | None = None

    @property
    def identity(self) -> tuple[object, ...]:
        if self.anchor is not None:
            return (self.path, self.rule_id, self.message, self.anchor)
        return (self.path, self.line, self.rule_id, self.message)


@dataclass(frozen=True)
class SymbolMetricBaselineRow:
    """A symbol metric baseline row whose metric may decrease."""

    path: str
    rule_id: str
    qualified_symbol: str
    metric: int
    reason: str

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.path, self.rule_id, self.qualified_symbol)


BaselineRow: TypeAlias = GenericBaselineRow | SymbolMetricBaselineRow


def _baseline_kind(row: BaselineRow) -> BaselineKind:
    if isinstance(row, GenericBaselineRow):
        return "generic"
    return "symbol_metric"


def _baseline_sort_key(row: BaselineRow) -> tuple[object, ...]:
    if isinstance(row, GenericBaselineRow):
        return ("generic", row.path, row.rule_id, row.message, row.anchor or "", row.line)
    return ("symbol_metric", row.path, row.rule_id, row.qualified_symbol)


def _baseline_identity(row: BaselineRow) -> tuple[object, ...]:
    return row.identity


def _baseline_row_display(row: BaselineRow) -> str:
    if isinstance(row, GenericBaselineRow):
        return f"{row.path}:{row.line}: {row.rule_id} {row.message}"
    return f"{row.path}:{row.qualified_symbol}: {row.rule_id} metric {row.metric}"


def _nonempty_single_line(value: object) -> bool:
    return _is_single_line(value) and bool(cast("str", value).strip())


def _generic_baseline_row(
    record: Mapping[str, object], *, index: int, source: str
) -> GenericBaselineRow:
    path = record["path"]
    line = record["line"]
    rule_id = record["rule_id"]
    message = record["message"]
    reason = record["reason"]
    anchor = record.get("anchor")
    if not _is_single_line(path):
        raise ScanError(f"{source}: baseline row {index} has invalid path")
    if not isinstance(line, int) or isinstance(line, bool) or line < 1:
        raise ScanError(f"{source}: baseline row {index} has invalid line")
    if not _is_single_line(rule_id):
        raise ScanError(f"{source}: baseline row {index} has invalid rule_id")
    if not _is_single_line(message):
        raise ScanError(f"{source}: baseline row {index} has invalid message")
    if not _nonempty_single_line(reason):
        raise ScanError(f"{source}: baseline row {index} has invalid reason")
    if anchor is not None and not _is_single_line(anchor):
        raise ScanError(f"{source}: baseline row {index} has invalid anchor")
    return GenericBaselineRow(
        cast("str", path),
        line,
        cast("str", rule_id),
        cast("str", message),
        cast("str", reason),
        cast("str | None", anchor),
    )


def _symbol_metric_baseline_row(
    record: Mapping[str, object], *, index: int, source: str
) -> SymbolMetricBaselineRow:
    path = record["path"]
    rule_id = record["rule_id"]
    qualified_symbol = record["qualified_symbol"]
    metric = record["metric"]
    reason = record["reason"]
    if not _is_single_line(path):
        raise ScanError(f"{source}: baseline row {index} has invalid path")
    if not _is_single_line(rule_id):
        raise ScanError(f"{source}: baseline row {index} has invalid rule_id")
    if not _is_single_line(qualified_symbol):
        raise ScanError(f"{source}: baseline row {index} has invalid qualified_symbol")
    if not isinstance(metric, int) or isinstance(metric, bool) or metric < 0:
        raise ScanError(f"{source}: baseline row {index} has invalid metric")
    if not _nonempty_single_line(reason):
        raise ScanError(f"{source}: baseline row {index} has invalid reason")
    return SymbolMetricBaselineRow(
        cast("str", path),
        cast("str", rule_id),
        cast("str", qualified_symbol),
        metric,
        cast("str", reason),
    )


def _parse_baseline_row(raw: object, *, index: int, source: str) -> BaselineRow:
    if not isinstance(raw, dict):
        raise ScanError(f"{source}: baseline row {index} must be an object")
    record = cast("dict[str, object]", raw)
    generic_keys = frozenset({"path", "line", "rule_id", "message", "reason"})
    anchored_generic_keys = generic_keys | {"anchor"}
    symbol_keys = frozenset({"path", "rule_id", "qualified_symbol", "metric", "reason"})
    if frozenset(record) in {generic_keys, anchored_generic_keys}:
        return _generic_baseline_row(record, index=index, source=source)
    if frozenset(record) == symbol_keys:
        return _symbol_metric_baseline_row(record, index=index, source=source)
    raise ScanError(f"{source}: baseline row {index} has unsupported keys")


def _validate_baseline_rows(
    rows: Sequence[BaselineRow], *, source: str
) -> list[BaselineRow]:
    kinds: set[BaselineKind] = set()
    identities: set[tuple[object, ...]] = set()
    validated: list[BaselineRow] = []
    for row in rows:
        kinds.add(_baseline_kind(row))
        identity = _baseline_identity(row)
        if identity in identities:
            raise ScanError(f"{source}: duplicate baseline identity")
        identities.add(identity)
        validated.append(row)
    if len(kinds) > 1:
        raise ScanError(f"{source}: mixed baseline row shapes are not supported")
    return validated


def _parse_baseline_text(text: str, *, source: str) -> list[BaselineRow]:
    try:
        decoded = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        raise ScanError(f"{source}: invalid JSON baseline: {exc.msg}") from exc
    if not isinstance(decoded, list):
        raise ScanError(f"{source}: baseline must be a top-level JSON array")
    raw_rows = cast("list[object]", decoded)
    rows = [
        _parse_baseline_row(raw, index=index, source=source)
        for index, raw in enumerate(raw_rows)
    ]
    return _validate_baseline_rows(rows, source=source)


def _validate_baseline_component(path: Path, *, is_parent: bool) -> bool:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        if is_parent:
            raise ScanError(f"baseline parent does not exist: {path}") from None
        return False
    except OSError as exc:
        raise ScanError(f"failed to inspect baseline path {path}: {exc}") from exc
    if stat.S_ISLNK(mode):
        raise ScanError(f"baseline path is symlinked: {path}")
    if is_parent and not stat.S_ISDIR(mode):
        raise ScanError(f"baseline parent is not a directory: {path}")
    if not is_parent and not stat.S_ISREG(mode):
        raise ScanError(f"baseline path is not a regular file: {path}")
    return True


def _validate_baseline_path(raw: str | Path, *, root: Path, write_mode: bool) -> Path:
    text = str(raw)
    if not _is_single_line(text):
        raise ScanError("baseline path must be a non-empty single-line path")
    candidate = Path(text)
    if ".." in candidate.parts:
        raise ScanError(f"baseline path must not contain '..': {raw}")
    absolute = candidate if candidate.is_absolute() else root / candidate
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise ScanError(f"baseline path escapes repository root: {raw}") from exc
    if not relative.parts:
        raise ScanError("baseline path must name a file below the repository root")

    current = root
    components = relative.parts
    for index, component in enumerate(components):
        current = current / component
        exists = _validate_baseline_component(
            current,
            is_parent=index < len(components) - 1,
        )
        if not exists:
            break
    if write_mode and not absolute.parent.is_dir():
        raise ScanError(f"baseline parent does not exist: {absolute.parent}")
    return absolute


def _load_baseline(path: Path, *, root: Path) -> list[BaselineRow]:
    try:
        text = larch_io.read_trusted_text(path, root=root, reject_cr=True)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScanError(f"failed to read baseline {path}: {exc}") from exc
    return _parse_baseline_text(text, source=f"baseline {path}")


def _baseline_exists(path: Path, *, root: Path) -> bool:
    try:
        return larch_io.trusted_file_present(path, root=root)
    except OSError as exc:
        raise ScanError(f"failed to inspect baseline {path}: {exc}") from exc


def _project_finding(finding: Finding) -> BaselineRow:
    if finding.qualified_symbol is None and finding.metric is None:
        return GenericBaselineRow(
            finding.path, finding.line, finding.rule_id, finding.message, "", finding.anchor
        )
    if finding.qualified_symbol is not None and finding.metric is not None:
        return SymbolMetricBaselineRow(
            finding.path,
            finding.rule_id,
            finding.qualified_symbol,
            finding.metric,
            "",
        )
    raise ScanError(
        "baseline-active findings require qualified_symbol and metric together"
    )


def _project_findings(findings: Sequence[Finding]) -> list[BaselineRow]:
    rows = [_project_finding(finding) for finding in findings]
    kinds = {_baseline_kind(row) for row in rows}
    if len(kinds) > 1:
        raise ScanError("baseline-active findings have mixed row shapes")
    seen: set[tuple[object, ...]] = set()
    for row in rows:
        identity = _baseline_identity(row)
        if identity in seen:
            raise ScanError("duplicate live baseline identity")
        seen.add(identity)
    rows.sort(key=_baseline_sort_key)
    return rows


def _row_matches_selector(
    row: BaselineRow, selectors: Sequence[tuple[str, bool]]
) -> bool:
    for selector, is_directory in selectors:
        if row.path == selector or (
            is_directory and (selector == "." or row.path.startswith(f"{selector}/"))
        ):
            return True
    return False


def _selected_baseline_rows(
    rows: Sequence[BaselineRow],
    *,
    root: Path,
    paths: Sequence[str | Path] | None,
) -> list[BaselineRow]:
    if paths is None:
        return list(rows)
    selectors = [_validate_requested_path(item, root=root) for item in paths]
    return [row for row in rows if _row_matches_selector(row, selectors)]


def _ensure_compatible_shapes(
    live_rows: Sequence[BaselineRow], baseline_rows: Sequence[BaselineRow]
) -> None:
    if (
        live_rows
        and baseline_rows
        and _baseline_kind(live_rows[0]) != _baseline_kind(baseline_rows[0])
    ):
        raise ScanError("live findings and baseline rows use different shapes")


def _baseline_comparison(
    live_rows: Sequence[BaselineRow], baseline_rows: Sequence[BaselineRow]
) -> tuple[list[BaselineRow], list[BaselineRow]]:
    _ensure_compatible_shapes(live_rows, baseline_rows)
    indexed = {_baseline_identity(row): row for row in baseline_rows}
    active: list[BaselineRow] = []
    seen: set[tuple[object, ...]] = set()
    for row in live_rows:
        identity = _baseline_identity(row)
        seen.add(identity)
        prior = indexed.get(identity)
        if prior is None:
            active.append(row)
        elif isinstance(row, SymbolMetricBaselineRow):
            if not isinstance(prior, SymbolMetricBaselineRow):
                raise ScanError("live findings and baseline rows use different shapes")
            if row.metric > prior.metric:
                active.append(row)
    stale = [row for row in baseline_rows if _baseline_identity(row) not in seen]
    stale.sort(key=_baseline_sort_key)
    return active, stale


def _serialized_baseline(rows: Sequence[BaselineRow]) -> str:
    records: list[dict[str, object]] = []
    for row in sorted(rows, key=_baseline_sort_key):
        if isinstance(row, GenericBaselineRow):
            records.append(
                {
                    "path": row.path,
                    "line": row.line,
                    "rule_id": row.rule_id,
                    "message": row.message,
                    "reason": row.reason,
                    **({"anchor": row.anchor} if row.anchor is not None else {}),
                }
            )
        else:
            records.append(
                {
                    "path": row.path,
                    "rule_id": row.rule_id,
                    "qualified_symbol": row.qualified_symbol,
                    "metric": row.metric,
                    "reason": row.reason,
                }
            )
    return json.dumps(records, indent=2, sort_keys=True) + "\n"


def _rows_for_write(
    live_rows: Sequence[BaselineRow],
    baseline_rows: Sequence[BaselineRow],
    *,
    initial_reason: str | None,
) -> list[BaselineRow]:
    _ensure_compatible_shapes(live_rows, baseline_rows)
    previous = {_baseline_identity(row): row for row in baseline_rows}
    written: list[BaselineRow] = []
    for row in live_rows:
        prior = previous.get(_baseline_identity(row))
        reason = prior.reason if prior is not None else initial_reason
        if reason is None:
            raise ScanError(
                "live finding has no baseline reason; supply initial_reason"
            )
        if isinstance(row, GenericBaselineRow):
            written.append(
                GenericBaselineRow(
                    row.path,
                    row.line,
                    row.rule_id,
                    row.message,
                    reason,
                    row.anchor,
                )
            )
        else:
            written.append(
                SymbolMetricBaselineRow(
                    row.path,
                    row.rule_id,
                    row.qualified_symbol,
                    row.metric,
                    reason,
                )
            )
    return written


def _publish_baseline(path: Path, *, root: Path, rows: Sequence[BaselineRow]) -> None:
    intended = _serialized_baseline(rows)
    try:
        larch_io.trusted_atomic_write(path, intended, root=root)
    except OSError as exc:
        raise ScanError(f"failed to write baseline {path}: {exc}") from exc
    try:
        read_back = larch_io.read_trusted_text(path, root=root, reject_cr=True)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScanError(f"failed to read back baseline {path}: {exc}") from exc
    if read_back != intended:
        raise ScanError(f"baseline read-back bytes differ after write: {path}")
    try:
        parsed = _parse_baseline_text(read_back, source=f"baseline {path}")
    except ScanError as exc:
        raise ScanError(f"baseline read-back validation failed: {exc}") from exc
    if parsed != sorted(rows, key=_baseline_sort_key):
        raise ScanError(f"baseline read-back records differ after write: {path}")


def _scan_findings(
    rule: LintRule,
    *,
    root: Path,
    runner: Runner,
    paths: Sequence[str | Path] | None,
) -> list[Finding]:
    pathspecs: list[str] | None = None
    if paths is not None:
        # Validate selectors before discovery so bad pathspecs fail closed and
        # git only enumerates in-scope cached paths.
        pathspecs = [
            _validate_requested_path(item, root=root)[0] for item in paths
        ]
    tracked = _discover_tracked_paths(root, runner, pathspecs=pathspecs)
    selected = _filter_tracked_paths(tracked, root=root, paths=paths)
    pragma_re = re.compile(rf"#\s*{re.escape(rule.suppression_token)}:\s*ok\s+(\S.*)$")
    empty_pragma_re = re.compile(rf"#\s*{re.escape(rule.suppression_token)}:\s*ok\s*$")
    collected: list[Finding] = []
    for rel_path in selected:
        source = _load_source(root, rel_path)
        collected.extend(
            _scan_source(
                source,
                rule=rule,
                pragma_re=pragma_re,
                empty_pragma_re=empty_pragma_re,
            )
        )
    return collected


def _validate_baseline_options(
    *,
    baseline_path: str | Path | None,
    write_baseline: bool,
    initial_reason: str | None,
    strict_stale: bool,
    paths: Sequence[str | Path] | None,
) -> None:
    if write_baseline and baseline_path is None:
        raise ScanError("write_baseline requires baseline_path")
    if strict_stale and (write_baseline or baseline_path is None):
        raise ScanError("strict_stale requires baseline check mode and baseline_path")
    if initial_reason is not None and not write_baseline:
        raise ScanError("initial_reason is only valid with write_baseline")
    if initial_reason is not None and not _nonempty_single_line(initial_reason):
        raise ScanError("initial_reason must be a non-empty single-line string")
    if write_baseline and paths is not None:
        raise ScanError("write_baseline does not support filtered paths")


def _findings_for_active_rows(
    findings: Sequence[Finding], active_rows: Sequence[BaselineRow]
) -> list[Finding]:
    active = {_baseline_identity(row) for row in active_rows}
    rendered = [
        finding
        for finding in findings
        if _baseline_identity(_project_finding(finding)) in active
    ]
    rendered.sort(
        key=lambda item: (
            item.path,
            item.line,
            item.rule_id,
            item.message,
            item.qualified_symbol or "",
            item.metric if item.metric is not None else -1,
        )
    )
    return rendered


def _run_with_baseline(  # noqa: PLR0913 - keeps baseline data flow explicit.
    collected: Sequence[Finding],
    *,
    root: Path,
    destination: Path,
    baseline_rows: Sequence[BaselineRow],
    write_baseline: bool,
    initial_reason: str | None,
    strict_stale: bool,
    paths: Sequence[str | Path] | None,
) -> tuple[int, list[Finding], list[str]]:
    live_rows = _project_findings(collected)
    if write_baseline:
        written = _rows_for_write(
            live_rows, baseline_rows, initial_reason=initial_reason
        )
        _publish_baseline(destination, root=root, rows=written)
        return EXIT_CLEAN, [], []
    scoped_baseline = _selected_baseline_rows(baseline_rows, root=root, paths=paths)
    active_rows, stale_rows = _baseline_comparison(live_rows, scoped_baseline)
    warnings = [
        f"warning: stale baseline row: {_baseline_row_display(row)}"
        for row in stale_rows
    ]
    if strict_stale and stale_rows:
        raise StrictStaleError(warnings)
    return (
        EXIT_FINDINGS if active_rows else EXIT_CLEAN,
        _findings_for_active_rows(collected, active_rows),
        warnings,
    )


def run_rule(  # noqa: PLR0913 - public API preserves direct keyword options.
    rule: LintRule,
    root: str | Path,
    runner: Runner,
    paths: Sequence[str | Path] | None = None,
    *,
    baseline_path: str | Path | None = None,
    write_baseline: bool = False,
    initial_reason: str | None = None,
    strict_stale: bool = False,
) -> int:
    """Run one lint rule, optionally comparing or regenerating a baseline.

    With no baseline options this preserves the scan-only contract. Baseline
    checks return ``0`` for fully baselined findings, ``1`` for new or grown
    findings, and ``2`` for invalid state, strict stale rows, or I/O failures.
    """
    try:
        _validate_baseline_options(
            baseline_path=baseline_path,
            write_baseline=write_baseline,
            initial_reason=initial_reason,
            strict_stale=strict_stale,
            paths=paths,
        )
        _validate_rule(rule)
        repo_root = _validate_repo_root(Path(root), runner)
        destination: Path | None = None
        baseline_rows: list[BaselineRow] = []
        if baseline_path is not None:
            destination = _validate_baseline_path(
                baseline_path, root=repo_root, write_mode=write_baseline
            )
            if _baseline_exists(destination, root=repo_root):
                baseline_rows = _load_baseline(destination, root=repo_root)
            elif not write_baseline:
                raise ScanError(
                    f"failed to read baseline {destination}: file does not exist"
                )
        collected = _scan_findings(rule, root=repo_root, runner=runner, paths=paths)
        if baseline_path is None:
            findings = _dedupe_and_sort(collected)
            result = EXIT_FINDINGS if findings else EXIT_CLEAN
            warnings: list[str] = []
        else:
            assert destination is not None
            result, findings, warnings = _run_with_baseline(
                collected,
                root=repo_root,
                destination=destination,
                baseline_rows=baseline_rows,
                write_baseline=write_baseline,
                initial_reason=initial_reason,
                strict_stale=strict_stale,
                paths=paths,
            )
    except StrictStaleError as exc:
        for warning in exc.warnings:
            print(warning, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR

    for warning in warnings:
        print(warning, file=sys.stderr)
    for finding in findings:
        print(render_finding(finding), file=sys.stdout)
    return result
