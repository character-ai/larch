"""Shared scan-only lint pipeline (models, discovery, detect, render).

Unregistered library surface: no CLI. Callers supply a ``LintRule`` and an
injected ``Runner``; ``run_rule`` supports scan-only, baseline-check, and
guarded baseline-write modes, prints findings to stdout and diagnostics to
stderr, then returns 0 / 1 / 2.
"""

from __future__ import annotations

import ast
import argparse
import io
import json
import os
import re
import stat
import sys
import tokenize
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, TypeAlias, TypeVar, cast

from larch import io as larch_io
from larch.core.proc import CommandResult, Runner

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2
SYNTAX_FAIL_MESSAGE = "unable to parse Python"
GIT_DIAGNOSTIC_MAX_CHARS = 200
PYTHON_TREE_PREFIX = "python/"
PYTHON_TEST_EXEMPT_FILENAMES = frozenset(
    {"conftest.py", "test_support.py", "review_test_support.py"}
)
PYTHON_EXCLUDED_DIRS = frozenset(
    {".git", "node_modules", ".venv", ".agents", "__pycache__"}
)
SyntaxPolicy = Literal["fail", "skip", "raise"]
OccurrencePatternField = str
OccurrenceFields = tuple[str, ...]
SourceFilter = Callable[[str], bool]
DuplicateKey = TypeVar("DuplicateKey", bound=Hashable)
T = TypeVar("T")
_MARKDOWN_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})([^`~]*)$")


@dataclass(frozen=True)
class MarkdownLine:
    """One Markdown line and the language of its enclosing fence, if any."""

    number: int
    text: str
    language: str | None


def fenced_markdown_lines(lines: Sequence[str]) -> Iterable[MarkdownLine]:
    """Yield lines annotated with their active fenced-code-block language."""
    marker: str | None = None
    width = 0
    language: str | None = None
    for number, line in enumerate(lines, start=1):
        match = _MARKDOWN_FENCE_RE.match(line)
        if marker is None:
            if match is not None:
                token, info = match.groups()
                marker = token[0]
                width = len(token)
                language = info.strip().split(maxsplit=1)[0].lower() if info.strip() else ""
                yield MarkdownLine(number, line, None)
                continue
            yield MarkdownLine(number, line, None)
            continue
        if match is not None and match.group(1)[0] == marker and len(match.group(1)) >= width:
            yield MarkdownLine(number, line, language)
            marker = None
            width = 0
            language = None
            continue
        yield MarkdownLine(number, line, language)


class ScanError(Exception):
    """Expected scan failure with a deterministic stderr diagnostic."""


class StrictStaleError(ScanError):
    """A strict stale failure that retains its stable warning diagnostics."""

    def __init__(self, warnings: Sequence[str]) -> None:
        super().__init__("strict_stale rejected stale baseline rows")
        self.warnings = warnings


class BaselineError(ValueError):
    """A baseline, exemption, or configuration file cannot be trusted."""


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
    pattern_name: str | None = None
    occurrence: int | None = None
    occurrence_values: tuple[tuple[str, str], ...] = ()


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


PrepareCorpus: TypeAlias = Callable[[Sequence[SourceFile]], None]


@dataclass(frozen=True)
class LintRule:
    """Detect-function rule configuration for ``run_rule``."""

    rule_id: str
    description: str
    detect: Callable[[SourceFile], object]
    syntax_policy: SyntaxPolicy
    suppression_token: str
    allow_inline_suppression: bool = True
    pathspecs: tuple[str, ...] | None = None
    source_filter: SourceFilter | None = None
    occurrence_baseline: bool = False
    stale_baseline_on_clean_scan: bool = False
    occurrence_pattern_field: OccurrencePatternField = "pattern_name"
    occurrence_fields: OccurrenceFields | None = None
    require_baseline: bool = False
    warn_matching_baseline: bool = False
    exclude_tracked_symlinks: bool = False
    occurrence_symbol_optional: bool = False
    stale_as_finding: bool = False
    prepare_corpus: PrepareCorpus | None = None


def normalize_python_file_path(raw: str) -> str:
    """Return a normalized POSIX path relative to the ``python/`` tree."""
    normalized = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.removeprefix(PYTHON_TREE_PREFIX)


def is_exempt_python_source(path: Path) -> bool:
    """Return whether a Python test or shared test helper is out of scope."""
    name = path.name
    return (
        (name.startswith("test_") and name.endswith(".py"))
        or name in PYTHON_TEST_EXEMPT_FILENAMES
    )


def is_production_python_path(rel_path: str, *, prefix: str = PYTHON_TREE_PREFIX) -> bool:
    """Check a repo-relative production Python path before loading its source."""
    if not rel_path.startswith(prefix) or not rel_path.endswith(".py"):
        return False
    relative = Path(rel_path[len(prefix) :])
    return not (
        is_exempt_python_source(relative)
        or bool(PYTHON_EXCLUDED_DIRS.intersection(relative.parts))
    )


def qualified_symbol(prefix: tuple[str, ...], *, module_symbol: str = "<module>") -> str:
    """Render a nested AST scope as its stable baseline symbol."""
    return ".".join(prefix) if prefix else module_symbol


def ordered_ast_child_nodes(node: ast.AST) -> list[ast.AST]:
    """Return AST children in source order, including ``with`` expressions."""
    def position(child: ast.AST, index: int) -> tuple[int, int, int]:
        if isinstance(child, ast.withitem):
            context_expr = child.context_expr
            return (
                getattr(context_expr, "lineno", 10**9),
                getattr(context_expr, "col_offset", 10**9),
                index,
            )
        return (
            getattr(child, "lineno", 10**9),
            getattr(child, "col_offset", 10**9),
            index,
        )

    indexed = list(enumerate(ast.iter_child_nodes(node)))
    indexed.sort(key=lambda item: position(item[1], item[0]))
    return [child for _, child in indexed]


def read_python_source(path: Path) -> tuple[str, ast.Module] | None:
    """Read and parse a Python file, returning ``(source, tree)`` or ``None``.

    Returns ``None`` when the file cannot be read or parsed, so callers can treat
    both as "no findings" without duplicating the read/parse boilerplate.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    return source, tree


def scan_python_file(
    path: Path,
    *,
    python_dir: Path,
    collect: Callable[[ast.Module, str, list[T]], None],
) -> list[T]:
    """Read and parse one Python file, then append findings via ``collect``.

    The callback receives the parsed module, the path relative to ``python_dir``
    (POSIX), and a fresh findings list to mutate; this collapses the shared
    read/parse/collect scaffolding used by per-module ``scan_file`` entrypoints.
    """
    parsed = read_python_source(path)
    if parsed is None:
        return []
    _source, tree = parsed
    findings: list[T] = []
    collect(tree, path.relative_to(python_dir).as_posix(), findings)
    return findings


def has_inline_pragma(
    lineno: int,
    lines: Sequence[str],
    *,
    pragma_re: re.Pattern[str],
    standalone_pragma_re: re.Pattern[str],
) -> bool:
    """Return whether a same-line or preceding standalone pragma suppresses ``lineno``."""
    index = lineno - 1
    if 0 <= index < len(lines) and pragma_re.search(lines[index]):
        return True
    previous = index - 1
    return 0 <= previous < len(lines) and standalone_pragma_re.match(lines[previous]) is not None


def walk_scopes(
    body: Sequence[ast.stmt],
    *,
    prefix: tuple[str, ...],
    module_symbol: str,
    enter_scope: Callable[[str], Callable[[ast.AST], None]],
) -> None:
    """Walk AST scopes, invoking a per-scope handler for each non-scope node.

    ``enter_scope(symbol)`` returns a fresh node handler that owns one scope's
    occurrence counter; ``FunctionDef`` / ``AsyncFunctionDef`` / ``ClassDef``
    bodies recurse into a nested scope with an extended prefix (and thus a fresh
    handler), so occurrence numbering resets per scope just like a per-scope
    ``_collect_scope`` recursion. This is the shared scope-walk skeleton used by
    per-module occurrence collectors.
    """
    handle = enter_scope(qualified_symbol(prefix, module_symbol=module_symbol))

    def walk(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            walk_scopes(
                node.body,
                prefix=(*prefix, node.name),
                module_symbol=module_symbol,
                enter_scope=enter_scope,
            )
            return
        if isinstance(node, ast.ClassDef):
            walk_scopes(
                node.body,
                prefix=(*prefix, node.name),
                module_symbol=module_symbol,
                enter_scope=enter_scope,
            )
            return
        handle(node)
        for child in ordered_ast_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def load_json_array(path: Path, *, label: str) -> list[object]:
    """Load a top-level JSON array from ``path``, or ``[]`` when the file is absent.

    Raises :class:`BaselineError` when the file cannot be read, is not valid
    JSON, or is not a top-level array.
    """
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"{path}: cannot load {label}: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: {label} must be a top-level JSON array")
    return cast("list[object]", data)


def first_duplicate(keys: Iterable[DuplicateKey]) -> DuplicateKey | None:
    """Return the first repeated stable identity, or ``None`` when unique."""
    seen: set[DuplicateKey] = set()
    for key in keys:
        if key in seen:
            return key
        seen.add(key)
    return None


@dataclass(frozen=True)
class RuleCli:
    """Stable command-line contract for an engine-backed lint rule."""

    prog: str
    description: str | None
    baseline_filename: str | None = None
    error_label: str | None = None
    default_root: Path = Path(__file__).resolve().parents[3]
    scoped_paths: tuple[str, ...] | None = None
    strict_stale: bool = True
    resolve_root: bool = True


RootCliAction: TypeAlias = Callable[[Path], int]


def parse_lint_argv(
    argv: Sequence[str],
    *,
    cli: RuleCli,
) -> argparse.Namespace | None:
    """Parse the standard lint argv and validate --initial-reason.

    Shared by :func:`run_rule_cli` and by rules whose ``main`` needs bespoke
    multi-rule or factory-driven composition. Returns the parsed namespace with
    ``initial_reason`` normalized to a non-empty stripped string (or ``None``),
    or ``None`` after printing a diagnostic when argv is invalid or
    ``--initial-reason`` is empty.
    """
    parser = argparse.ArgumentParser(prog=cli.prog, description=cli.description)
    _ = parser.add_argument(
        "--root",
        default=str(cli.default_root),
        help="Repository root (default: checkout containing this module).",
    )
    if cli.baseline_filename is not None:
        _ = parser.add_argument(
            "--write",
            action="store_true",
            help=f"Regenerate {cli.baseline_filename} from the live scan.",
        )
        _ = parser.add_argument(
            "--initial-reason",
            help="Reason for live findings that have no preserved baseline reason.",
        )
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None

    initial_reason = getattr(parsed, "initial_reason", None)
    if initial_reason is None or cli.baseline_filename is None:
        return parsed
    text = str(initial_reason).strip()
    if not text:
        print(
            f"{cli.error_label or cli.prog}: --initial-reason must be non-empty",
            file=sys.stderr,
        )
        return None
    parsed.initial_reason = text
    return parsed


def run_rule_cli(
    argv: Sequence[str],
    *,
    rule: LintRule,
    cli: RuleCli,
    runner: Runner,
) -> int:
    """Parse the standard lint argv and run an engine rule.

    The shared contract keeps every rule's root, baseline, strict-stale, and
    reason validation identical. Rules whose ``main`` closes over repo state
    (config constants, module resolvers), runs multiple rules, or needs bespoke
    positional arguments call :func:`parse_lint_argv` and drive :func:`run_rule`
    directly.
    """
    parsed = parse_lint_argv(argv, cli=cli)
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    if cli.baseline_filename is None:
        return run_rule(rule, root, runner, paths=cli.scoped_paths)

    write_baseline = bool(parsed.write)
    initial_reason = cast("str | None", parsed.initial_reason)
    return run_rule(
        rule,
        root,
        runner,
        paths=None if write_baseline else cli.scoped_paths,
        baseline_path=root / "python" / cli.baseline_filename,
        write_baseline=write_baseline,
        initial_reason=initial_reason,
        strict_stale=cli.strict_stale and not write_baseline,
    )


def run_root_cli(
    argv: Sequence[str],
    *,
    cli: RuleCli,
    action: RootCliAction,
) -> int:
    """Parse a root-only lint command and invoke its typed action.

    This is the narrow engine CLI seam for legacy scan commands whose result
    model does not yet fit :func:`run_rule_cli`. It intentionally exposes only
    ``--root``: baseline flags remain exclusive to engine ``LintRule`` scans.
    """
    if cli.baseline_filename is not None:
        msg = "run_root_cli requires a RuleCli without a baseline filename"
        raise ValueError(msg)
    parsed = parse_lint_argv(argv, cli=cli)
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root))
    return action(root.resolve() if cli.resolve_root else root)


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


def _occurrence_field_names(rule: LintRule) -> OccurrenceFields:
    """Return the ordered legacy JSON fields that identify one occurrence."""
    if rule.occurrence_fields is None:
        return (rule.occurrence_pattern_field,)
    return rule.occurrence_fields


def _validate_rule(rule: LintRule) -> None:  # noqa: C901, PLR0912 - rule field validation is intentional
    if not _is_single_line(rule.rule_id):
        raise ScanError("lint rule rule_id must be a non-empty single-line string")
    if not _is_exact_bool(rule.allow_inline_suppression):
        raise ScanError("lint rule allow_inline_suppression must be a bool")
    if not _is_exact_bool(rule.occurrence_baseline):
        raise ScanError("lint rule occurrence_baseline must be a bool")
    if not _is_exact_bool(rule.require_baseline):
        raise ScanError("lint rule require_baseline must be a bool")
    if not _is_exact_bool(rule.stale_baseline_on_clean_scan):
        raise ScanError("lint rule stale_baseline_on_clean_scan must be a bool")
    if not _is_exact_bool(rule.warn_matching_baseline):
        raise ScanError("lint rule warn_matching_baseline must be a bool")
    if not _is_exact_bool(rule.exclude_tracked_symlinks):
        raise ScanError("lint rule exclude_tracked_symlinks must be a bool")
    if not _is_exact_bool(rule.occurrence_symbol_optional):
        raise ScanError("lint rule occurrence_symbol_optional must be a bool")
    if not _is_exact_bool(rule.stale_as_finding):
        raise ScanError("lint rule stale_as_finding must be a bool")
    if rule.occurrence_symbol_optional and not rule.occurrence_baseline:
        raise ScanError("occurrence_symbol_optional requires rule.occurrence_baseline")
    if not _is_single_line(rule.occurrence_pattern_field):
        raise ScanError(
            "lint rule occurrence_pattern_field must be a non-empty single-line string"
        )
    occurrence_fields = _occurrence_field_names(rule)
    if not rule.occurrence_baseline and rule.occurrence_fields is not None:
        raise ScanError("occurrence_fields requires rule.occurrence_baseline")
    if len(set(occurrence_fields)) != len(occurrence_fields) or any(
        not _is_single_line(field) for field in occurrence_fields
    ):
        raise ScanError(
            "lint rule occurrence_fields must contain unique non-empty single-line strings"
        )
    if (
        not rule.occurrence_baseline
        and rule.occurrence_pattern_field != "pattern_name"
    ):
        raise ScanError(
            "occurrence_pattern_field requires rule.occurrence_baseline"
        )
    if not _is_single_line(rule.suppression_token):
        raise ScanError(
            "lint rule suppression_token must be a non-empty single-line string"
        )
    if rule.syntax_policy not in ("fail", "skip", "raise"):
        raise ScanError(
            f"lint rule syntax_policy is unsupported: {rule.syntax_policy!r}"
        )
    if rule.pathspecs is not None:
        if not rule.pathspecs:
            raise ScanError("lint rule pathspecs must be a non-empty tuple when set")
        for item in rule.pathspecs:
            if not _is_single_line(item):
                raise ScanError(
                    "lint rule pathspecs entries must be non-empty single-line strings"
                )
    if rule.source_filter is not None and not callable(rule.source_filter):
        raise ScanError("lint rule source_filter must be callable when set")


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
    source_filter: SourceFilter | None = None,
    exclude_tracked_symlinks: bool = False,
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
        lexical_rel = _normalize_repo_relative_path(
            entry,
            root=root,
            label="discovered path",
            check_filesystem=False,
        )
        if source_filter is not None and not source_filter(lexical_rel):
            continue
        # Opt-in skip after lexical filtering and before filesystem normalize.
        if exclude_tracked_symlinks and (root / entry).is_symlink():
            continue
        rel = _normalize_repo_relative_path(entry, root=root, label="discovered path")
        if rel in seen:
            continue
        seen.add(rel)
        ordered.append(rel)
    return ordered


def _normalize_repo_relative_path(
    raw: str,
    *,
    root: Path,
    label: str,
    check_filesystem: bool = True,
) -> str:
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
    lexical = Path(candidate).as_posix()
    if not check_filesystem:
        return lexical
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


def _validate_finding(  # noqa: C901, PLR0912, PLR0915 - finding field validation is intentional
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
    pattern_name = finding.pattern_name
    occurrence = finding.occurrence
    occurrence_values = finding.occurrence_values
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
    if pattern_name is not None and not _is_single_line(pattern_name):
        raise ScanError(
            "finding pattern_name must be a non-empty single-line string when present"
        )
    if occurrence is not None and occurrence < 1:
        raise ScanError("finding occurrence must be a positive int when present")
    occurrence_fields = _occurrence_field_names(rule)
    has_occurrence = pattern_name is not None or occurrence is not None or occurrence_values
    if occurrence_values:
        if not rule.occurrence_baseline:
            raise ScanError("finding occurrence_values require rule.occurrence_baseline")
        if tuple(key for key, _ in occurrence_values) != occurrence_fields or any(
            not _is_single_line(key) or not _is_single_line(value)
            for key, value in occurrence_values
        ):
            raise ScanError(
                "finding occurrence_values must match the rule occurrence_fields"
            )
    if has_occurrence and occurrence is None:
        raise ScanError("finding occurrence requires a positive occurrence value")
    if has_occurrence and not occurrence_values and occurrence_fields and (
        pattern_name is None or len(occurrence_fields) != 1
    ):
        raise ScanError(
            "finding occurrence baseline requires values for every occurrence field"
        )
    if rule.occurrence_baseline:
        if not has_occurrence:
            raise ScanError(
                "occurrence-baseline findings require occurrence values and occurrence"
            )
        if qualified_symbol is None and not rule.occurrence_symbol_optional:
            raise ScanError(
                "occurrence-baseline findings require qualified_symbol"
            )
        if finding.metric is not None:
            raise ScanError(
                "occurrence-baseline findings must not set metric"
            )
    elif has_occurrence:
        raise ScanError(
            "finding pattern_name/occurrence require rule.occurrence_baseline"
        )
    metric = _validate_metric(finding.metric)
    return Finding(
        path=path,
        line=line,
        rule_id=rule_id,
        message=message,
        qualified_symbol=qualified_symbol,
        metric=metric,
        anchor=anchor,
        pattern_name=pattern_name,
        occurrence=occurrence,
        occurrence_values=occurrence_values,
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
            if rule.syntax_policy == "raise":
                raise ScanError(
                    f"{source.path}:{_syntax_finding_line(source, syntax_error)}: "
                    f"cannot parse source: {syntax_error.msg}"
                )
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


BaselineKind = Literal["generic", "symbol_metric", "occurrence"]


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


@dataclass(frozen=True)
class OccurrenceBaselineRow:
    """Occurrence-keyed baseline row with Python-tree path mapping."""

    path: str
    qualified_symbol: str | None
    pattern_name: str
    occurrence: int
    reason: str
    values: tuple[tuple[str, str], ...] = ()

    @property
    def occurrence_values(self) -> tuple[tuple[str, str], ...]:
        """Return explicit fields, retaining the original single-field constructor."""
        if self.values:
            return self.values
        if self.pattern_name:
            return (("pattern_name", self.pattern_name),)
        return ()

    @property
    def identity(self) -> tuple[object, ...]:
        return (self.path, self.qualified_symbol, *self.occurrence_values, self.occurrence)


BaselineRow: TypeAlias = (
    GenericBaselineRow | SymbolMetricBaselineRow | OccurrenceBaselineRow
)


# Complexity rows retain a richer historical contract than the generic metric
# baseline.  They deliberately live beside the other engine-owned baseline
# schemas so trusted I/O and structural read-back stay centralized.
ComplexityCode = Literal["C901", "PLR0911", "PLR0912", "PLR0913", "PLR0915"]
COMPLEXITY_CODES = frozenset({"C901", "PLR0911", "PLR0912", "PLR0913", "PLR0915"})
_COMPLEXITY_LEGACY_FIELDS = frozenset(
    {"file", "code", "qualified_symbol", "metric"}
)
_COMPLEXITY_REQUIRED_FIELDS = _COMPLEXITY_LEGACY_FIELDS | {"added_at", "history"}
_COMPLEXITY_OPTIONAL_FIELDS = frozenset({"source_issue", "reason", "operator_override"})
_COMPLEXITY_HISTORY_FIELDS = frozenset({"date", "metric"})
_COMPLEXITY_OVERRIDE_FIELDS = frozenset({"reason", "issue"})


@dataclass(frozen=True)
class ComplexityHistoryEntry:
    """One dated complexity metric event."""

    date: str
    metric: int


@dataclass(frozen=True)
class ComplexityOperatorOverride:
    """One active operator-approved repeat-bump exception."""

    reason: str
    issue: int


@dataclass(frozen=True)
class ComplexityLiveRow:
    """A current Ruff observation before baseline metadata is merged."""

    file: str
    code: ComplexityCode
    qualified_symbol: str
    metric: int

    @property
    def identity(self) -> tuple[str, str, str]:
        """Return the metric-independent complexity identity."""
        return (self.file, self.code, self.qualified_symbol)


@dataclass(frozen=True)
class ComplexityBaselineRow:
    """Immutable typed representation of one complexity baseline record."""

    file: str
    code: ComplexityCode
    qualified_symbol: str
    metric: int
    added_at: str
    history: tuple[ComplexityHistoryEntry, ...]
    source_issue: int | None = None
    reason: str | None = None
    operator_override: ComplexityOperatorOverride | None = None

    @property
    def identity(self) -> tuple[str, str, str]:
        """Return the metric-independent complexity identity."""
        return (self.file, self.code, self.qualified_symbol)


@dataclass(frozen=True)
class ComplexityHistoryEvent:
    """One metric increase event attributed to its baseline row."""

    event_date: date
    record: ComplexityBaselineRow
    history_index: int
    metric: int


@dataclass(frozen=True)
class ComplexityBaselineArgs:
    """Validated compatible arguments for the complexity-baseline CLI."""

    root: Path
    write: bool
    reason: str | None
    migrate: bool


@dataclass(frozen=True)
class ComplexityDebtArgs:
    """Validated arguments for the complexity-debt report command."""

    root: Path
    report: bool


def parse_complexity_baseline_argv(
    argv: Sequence[str], *, default_root: Path
) -> ComplexityBaselineArgs | None:
    """Parse the established complexity-baseline command surface."""
    parser = argparse.ArgumentParser(
        prog="cli.py lint complexity-baseline",
        description="Ratchet ruff complexity findings against a committed production baseline.",
    )
    _ = parser.add_argument("--root", default=str(default_root))
    _ = parser.add_argument("--write", action="store_true")
    _ = parser.add_argument("--reason")
    _ = parser.add_argument("--migrate", action="store_true")
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None
    reason = cast("str | None", parsed.reason)
    if parsed.migrate and parsed.write:
        print("--migrate and --write are incompatible", file=sys.stderr)
        return None
    if reason is not None and (not parsed.write or parsed.migrate or not _nonempty_single_line(reason)):
        print("--reason is only valid with --write and must be non-empty", file=sys.stderr)
        return None
    return ComplexityBaselineArgs(
        root=Path(cast("str", parsed.root)).resolve(),
        write=bool(parsed.write),
        reason=reason.strip() if reason is not None else None,
        migrate=bool(parsed.migrate),
    )


def parse_complexity_debt_argv(
    argv: Sequence[str], *, default_root: Path
) -> ComplexityDebtArgs | None:
    """Parse the established complexity-debt reporting command surface."""
    parser = argparse.ArgumentParser(
        prog="cli.py lint complexity-debt",
        description="Render the operator-facing complexity-baseline debt report.",
    )
    _ = parser.add_argument("--report", action="store_true")
    _ = parser.add_argument("--root", default=str(default_root))
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None
    if not parsed.report:
        return None
    return ComplexityDebtArgs(
        root=Path(cast("str", parsed.root)).resolve(), report=True
    )


def _complexity_date(value: object, *, source: str, index: int, field: str, today: date) -> str:
    if not isinstance(value, str):
        raise ScanError(f"{source}: record {index} has invalid {field}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ScanError(f"{source}: record {index} has invalid {field}") from exc
    if parsed.isoformat() != value or parsed > today:
        raise ScanError(f"{source}: record {index} has invalid {field}")
    return value


def _complexity_metric(value: object, *, source: str, index: int, field: str = "metric") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ScanError(f"{source}: record {index} has invalid {field}")
    return value


def _complexity_history(value: object, *, source: str, index: int, today: date) -> tuple[ComplexityHistoryEntry, ...]:
    if not isinstance(value, list):
        raise ScanError(f"{source}: record {index} has invalid history")
    entries: list[ComplexityHistoryEntry] = []
    previous: date | None = None
    for raw_item in cast("list[object]", value):
        if not isinstance(raw_item, dict):
            raise ScanError(f"{source}: record {index} has malformed history entry")
        entry = cast("dict[str, object]", raw_item)
        if frozenset(entry) != _COMPLEXITY_HISTORY_FIELDS:
            raise ScanError(f"{source}: record {index} has malformed history entry")
        event_date = _complexity_date(entry["date"], source=source, index=index, field="history date", today=today)
        parsed_date = date.fromisoformat(event_date)
        if previous is not None and parsed_date < previous:
            raise ScanError(f"{source}: record {index} has date-decreasing history")
        entries.append(ComplexityHistoryEntry(event_date, _complexity_metric(entry["metric"], source=source, index=index, field="history metric")))
        previous = parsed_date
    return tuple(entries)


def _complexity_override(value: object, *, source: str, index: int) -> ComplexityOperatorOverride:
    if not isinstance(value, dict):
        raise ScanError(f"{source}: record {index} has invalid operator_override")
    override = cast("dict[str, object]", value)
    if frozenset(override) != _COMPLEXITY_OVERRIDE_FIELDS:
        raise ScanError(f"{source}: record {index} has invalid operator_override")
    if not _nonempty_single_line(override["reason"]):
        raise ScanError(f"{source}: record {index} has invalid operator_override reason")
    issue = override["issue"]
    if not isinstance(issue, int) or isinstance(issue, bool) or issue <= 0:
        raise ScanError(f"{source}: record {index} has invalid operator_override issue")
    return ComplexityOperatorOverride(cast("str", override["reason"]), issue)


def _parse_complexity_row(  # noqa: C901 - exact legacy schema validation is intentionally centralized.
    raw: object, *, source: str, index: int, strict: bool, today: date
) -> ComplexityBaselineRow:
    if not isinstance(raw, dict):
        raise ScanError(f"{source}: record {index} must be an object")
    record = cast("Mapping[str, object]", raw)
    keys = frozenset(record)
    unknown = keys - _COMPLEXITY_REQUIRED_FIELDS - _COMPLEXITY_OPTIONAL_FIELDS
    if unknown:
        raise ScanError(f"{source}: record {index} has unknown fields {sorted(unknown)}")
    required = _COMPLEXITY_REQUIRED_FIELDS if strict else _COMPLEXITY_LEGACY_FIELDS
    missing = required - keys
    if missing:
        raise ScanError(f"{source}: record {index} missing required fields {sorted(missing)}")
    file_name, code, symbol = record["file"], record["code"], record["qualified_symbol"]
    if not _nonempty_single_line(file_name) or normalize_python_file_path(cast("str", file_name)) != file_name:
        raise ScanError(f"{source}: record {index} has invalid file")
    if not isinstance(code, str) or code not in COMPLEXITY_CODES:
        raise ScanError(f"{source}: record {index} has invalid code")
    if not _nonempty_single_line(symbol):
        raise ScanError(f"{source}: record {index} has invalid qualified_symbol")
    added_at = record.get("added_at", "legacy")
    if added_at != "legacy":
        added_at = _complexity_date(added_at, source=source, index=index, field="added_at", today=today)
    if not isinstance(added_at, str):
        raise ScanError(f"{source}: record {index} has invalid added_at")
    history = _complexity_history(record.get("history", []), source=source, index=index, today=today)
    source_issue = record.get("source_issue")
    if source_issue is not None and (not isinstance(source_issue, int) or isinstance(source_issue, bool) or source_issue <= 0):
        raise ScanError(f"{source}: record {index} has invalid source_issue")
    reason = record.get("reason")
    if reason is not None and not _nonempty_single_line(reason):
        raise ScanError(f"{source}: record {index} has invalid reason")
    override = _complexity_override(record["operator_override"], source=source, index=index) if "operator_override" in record else None
    return ComplexityBaselineRow(
        cast("str", file_name), cast("ComplexityCode", code), cast("str", symbol),
        _complexity_metric(record["metric"], source=source, index=index),
        added_at, history, source_issue, cast("str | None", reason), override,
    )


def parse_complexity_baseline(
    text: str, *, source: str, strict: bool = True, today: date | None = None
) -> list[ComplexityBaselineRow]:
    """Parse exact complexity records and reject malformed or duplicate identities."""
    try:
        decoded = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        raise ScanError(f"{source}: cannot load baseline: {exc}") from exc
    if not isinstance(decoded, list):
        raise ScanError(f"{source}: baseline must be a top-level JSON array")
    checked_today = today or datetime.now(UTC).date()
    rows = [
        _parse_complexity_row(
            row, source=source, index=index, strict=strict, today=checked_today
        )
        for index, row in enumerate(cast("list[object]", decoded))
    ]
    duplicates = complexity_duplicate_identities(rows)
    if duplicates:
        raise ScanError("duplicate baseline complexity identities:\n" + "\n".join(duplicates))
    return rows


def complexity_duplicate_identities(rows: Sequence[ComplexityBaselineRow | ComplexityLiveRow]) -> list[str]:
    """Return repeated complexity identities as stable diagnostic lines."""
    seen: set[tuple[str, str, str]] = set()
    duplicates: list[str] = []
    for row in rows:
        if row.identity in seen:
            file_name, code, symbol = row.identity
            duplicates.append(f"{file_name}:{symbol} {code}")
        else:
            seen.add(row.identity)
    return duplicates


def load_complexity_baseline(
    path: str | Path,
    *,
    root: Path,
    strict: bool = True,
    today: date | None = None,
    allow_missing: bool = False,
) -> list[ComplexityBaselineRow]:
    """Trusted-read and parse the complexity baseline through the engine."""
    destination = _validate_baseline_path(path, root=root, write_mode=False)
    if not _baseline_exists(destination, root=root):
        if allow_missing:
            return []
        raise ScanError(f"{destination}: cannot load baseline: file does not exist")
    try:
        text = larch_io.read_trusted_text(destination, root=root, reject_cr=True)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScanError(f"{destination}: cannot load baseline: {exc}") from exc
    return parse_complexity_baseline(text, source=str(destination), strict=strict, today=today)


def complexity_row_record(row: ComplexityBaselineRow) -> dict[str, object]:
    """Render one typed row in the legacy field order without null optionals."""
    result: dict[str, object] = {
        "file": row.file, "code": row.code, "qualified_symbol": row.qualified_symbol,
        "metric": row.metric, "added_at": row.added_at,
        "history": [{"date": item.date, "metric": item.metric} for item in row.history],
    }
    if row.source_issue is not None:
        result["source_issue"] = row.source_issue
    if row.reason is not None:
        result["reason"] = row.reason
    if row.operator_override is not None:
        result["operator_override"] = {"reason": row.operator_override.reason, "issue": row.operator_override.issue}
    return result


def serialize_complexity_baseline(rows: Sequence[ComplexityBaselineRow]) -> str:
    """Serialize canonical complexity records preserving legacy field order."""
    records = [complexity_row_record(row) for row in sorted(rows, key=lambda row: row.identity)]
    return json.dumps(records, indent=2) + "\n"


def write_complexity_baseline(
    path: str | Path, *, root: Path, rows: Sequence[ComplexityBaselineRow], today: date | None = None
) -> list[ComplexityBaselineRow]:
    """Atomically publish and byte/structure-read-back typed complexity rows."""
    destination = _validate_baseline_path(path, root=root, write_mode=True)
    intended = serialize_complexity_baseline(rows)
    checked_today = today or datetime.now(UTC).date()
    return _write_baseline_with_readback(
        destination,
        root=root,
        intended=intended,
        parse=lambda text: parse_complexity_baseline(
            text, source=f"baseline {destination}", today=checked_today
        ),
    )


def migrate_complexity_baseline(
    path: str | Path, *, root: Path, today: date | None = None
) -> int:
    """Add only missing migration metadata while proving metric projection parity."""
    destination = _validate_baseline_path(path, root=root, write_mode=False)
    try:
        text = larch_io.read_trusted_text(destination, root=root, reject_cr=True)
        decoded = cast("object", json.loads(text))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ScanError(f"{destination}: cannot load baseline: {exc}") from exc
    if not isinstance(decoded, list):
        raise ScanError(f"{destination}: baseline must be a top-level JSON array")
    rows = parse_complexity_baseline(text, source=str(destination), strict=False, today=today)
    migrated_count = sum(
        isinstance(raw, dict) and ("added_at" not in raw or "history" not in raw)
        for raw in cast("list[object]", decoded)
    )
    before = {row.identity: row.metric for row in rows}
    migrated = [
        ComplexityBaselineRow(
            row.file, row.code, row.qualified_symbol, row.metric, row.added_at,
            row.history, row.source_issue, row.reason, row.operator_override,
        )
        for row in rows
    ]
    after = {row.identity: row.metric for row in migrated}
    if before != after:
        raise ScanError(f"{path}: migration would change the identity-to-metric projection")
    _ = write_complexity_baseline(destination, root=root, rows=migrated, today=today)
    return migrated_count


def merge_complexity_baseline(
    *, live_rows: Sequence[ComplexityLiveRow], stored_rows: Sequence[ComplexityBaselineRow], reason: str | None, today: date
) -> list[ComplexityBaselineRow]:
    """Merge live metrics with historical metadata, requiring reasons for growth."""
    live_duplicates = complexity_duplicate_identities(live_rows)
    if live_duplicates:
        raise ScanError("duplicate live complexity identities:\n" + "\n".join(live_duplicates))
    stored_duplicates = complexity_duplicate_identities(stored_rows)
    if stored_duplicates:
        raise ScanError("duplicate baseline complexity identities:\n" + "\n".join(stored_duplicates))
    stored_by_identity = {row.identity: row for row in stored_rows}
    merged: list[ComplexityBaselineRow] = []
    for live in live_rows:
        stored = stored_by_identity.get(live.identity)
        if stored is None:
            if reason is None:
                raise ScanError("--reason is required for a new baseline row")
            merged.append(ComplexityBaselineRow(live.file, live.code, live.qualified_symbol, live.metric, today.isoformat(), (ComplexityHistoryEntry(today.isoformat(), live.metric),), reason=reason))
            continue
        history = stored.history
        next_reason = stored.reason
        if live.metric > stored.metric:
            if reason is None:
                raise ScanError("--reason is required for a metric increase")
            history = (*history, ComplexityHistoryEntry(today.isoformat(), live.metric))
            next_reason = reason
        merged.append(ComplexityBaselineRow(live.file, live.code, live.qualified_symbol, live.metric, stored.added_at, history, stored.source_issue, next_reason, stored.operator_override))
    return sorted(merged, key=lambda row: row.identity)


def complexity_regressions(
    *, live_rows: Sequence[ComplexityLiveRow], baseline_rows: Sequence[ComplexityBaselineRow]
) -> list[str]:
    """Return new identities and metric growth against typed baseline rows."""
    baseline = {row.identity: row.metric for row in baseline_rows}
    failures: list[str] = []
    for row in live_rows:
        previous = baseline.get(row.identity)
        label = f"{row.file}:{row.qualified_symbol} {row.code}"
        if previous is None:
            failures.append(f"{label} (new)")
        elif row.metric > previous:
            failures.append(f"{label} metric {row.metric} > baseline {previous}")
    return failures


def complexity_history_events(
    rows: Sequence[ComplexityBaselineRow], *, legacy_start: int = 0
) -> dict[tuple[str, str], list[ComplexityHistoryEvent]]:
    """Group deterministic metric-growth events for repeat-bump consumers."""
    grouped: dict[tuple[str, str], list[ComplexityHistoryEvent]] = {}
    for row in rows:
        start = legacy_start if row.added_at == "legacy" else 1
        for history_index, item in enumerate(row.history[start:], start=start):
            event = ComplexityHistoryEvent(date.fromisoformat(item.date), row, history_index, item.metric)
            grouped.setdefault((row.file, row.qualified_symbol), []).append(event)
    for events in grouped.values():
        events.sort(key=lambda event: (event.event_date, *event.record.identity, event.history_index))
    return grouped


# Skill-closure rows are aggregate records, not source-level findings.  Keep
# their exact schema and ratchet policy here with the other engine-owned
# baseline contracts, while closure discovery remains in its dedicated module.
SKILL_CLOSURE_RATCHETED_TARGETS = ("design", "implement", "review", "panel-tier")
SKILL_CLOSURE_FILE_RATCHET_TARGETS = frozenset({"panel-tier"})
SKILL_CLOSURE_METRIC_FIELDS = (
    "skill_md_lines",
    "skill_md_estimated_tokens",
    "skill_md_content_estimated_tokens",
    "closure_lines",
    "closure_estimated_tokens",
    "closure_content_estimated_tokens",
)
SKILL_CLOSURE_CONDITIONAL_METRIC_FIELDS = (
    "conditional_lines",
    "conditional_estimated_tokens",
    "conditional_content_estimated_tokens",
)
_SKILL_CLOSURE_CONDITIONAL_TO_EAGER_METRIC = {
    "conditional_lines": "closure_lines",
    "conditional_estimated_tokens": "closure_estimated_tokens",
    "conditional_content_estimated_tokens": "closure_content_estimated_tokens",
}
_SKILL_CLOSURE_FIELDS = frozenset(
    {
        "skill",
        *SKILL_CLOSURE_METRIC_FIELDS,
        "files",
        *SKILL_CLOSURE_CONDITIONAL_METRIC_FIELDS,
        "conditional_files",
    }
)
SKILL_CLOSURE_BASELINE_KEYS = _SKILL_CLOSURE_FIELDS


@dataclass(frozen=True)
class SkillClosureBaselineRow:
    """One immutable aggregate skill-closure baseline record."""

    skill: str
    skill_md_lines: int
    skill_md_estimated_tokens: int
    skill_md_content_estimated_tokens: int
    closure_lines: int
    closure_estimated_tokens: int
    closure_content_estimated_tokens: int
    files: tuple[str, ...]
    conditional_lines: int
    conditional_estimated_tokens: int
    conditional_content_estimated_tokens: int
    conditional_files: tuple[str, ...]


@dataclass(frozen=True)
class SkillClosureGrowthArgs:
    """Validated arguments for the skill-closure growth lint command."""

    root: Path
    write: bool
    skill: str | None


@dataclass(frozen=True)
class SkillClosureReportArgs:
    """Validated arguments for the skill-closure report command."""

    root: Path


def parse_skill_closure_report_argv(
    argv: Sequence[str], *, default_root: Path
) -> SkillClosureReportArgs | None:
    """Parse the established scan-only skill-closure report command surface."""
    parser = argparse.ArgumentParser(
        prog="cli.py skill-closure report",
        description="Report and ratchet always-loaded prompt-source closure size.",
    )
    _ = parser.add_argument("--root", default=str(default_root))
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None
    return SkillClosureReportArgs(root=Path(cast("str", parsed.root)).resolve())


def parse_skill_closure_growth_argv(
    argv: Sequence[str], *, default_root: Path
) -> SkillClosureGrowthArgs | None:
    """Parse the established skill-closure growth command surface."""
    parser = argparse.ArgumentParser(
        prog="cli.py lint skill-closure-growth",
        description="Report and ratchet always-loaded prompt-source closure size.",
    )
    _ = parser.add_argument("--root", default=str(default_root))
    _ = parser.add_argument(
        "--write", action="store_true", help="regenerate the committed baseline"
    )
    _ = parser.add_argument(
        "--skill", choices=SKILL_CLOSURE_RATCHETED_TARGETS, help="check one ratcheted target"
    )
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None
    write = bool(parsed.write)
    skill = cast("str | None", parsed.skill)
    if write and skill is not None:
        print("--skill is check-only; --write regenerates all ratcheted targets", file=sys.stderr)
        return None
    return SkillClosureGrowthArgs(
        root=Path(cast("str", parsed.root)).resolve(), write=write, skill=skill
    )


def _skill_closure_metric(
    value: object, *, source: str, index: int, field: str
) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ScanError(f"{source}: record {index} has invalid {field}")
    return value


def _skill_closure_files(
    value: object, *, source: str, index: int, field: str, allow_empty: bool
) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ScanError(f"{source}: record {index} has invalid {field}")
    paths: list[str] = []
    for raw in cast("list[object]", value):
        if (
            not isinstance(raw, str)
            or not _nonempty_single_line(raw)
            or raw.startswith("/")
            or "\\" in raw
        ):
            raise ScanError(f"{source}: record {index} has invalid {field}")
        path = Path(raw)
        if path.as_posix() != raw or any(
            part in {"", ".", ".."} for part in path.parts
        ):
            raise ScanError(f"{source}: record {index} has invalid {field}")
        paths.append(raw)
    if len(paths) != len(set(paths)):
        raise ScanError(f"{source}: record {index} has duplicate {field}")
    return tuple(paths)


def _skill_closure_row(
    raw: object, *, source: str, index: int
) -> SkillClosureBaselineRow:
    if not isinstance(raw, dict):
        raise ScanError(f"{source}: record {index} must be an object")
    record = cast("Mapping[str, object]", raw)
    if frozenset(record) != _SKILL_CLOSURE_FIELDS:
        raise ScanError(
            f"{source}: record {index} must have exactly {sorted(_SKILL_CLOSURE_FIELDS)}"
        )
    skill = record["skill"]
    if not isinstance(skill, str) or skill not in SKILL_CLOSURE_RATCHETED_TARGETS:
        raise ScanError(f"{source}: record {index} has invalid skill")
    return SkillClosureBaselineRow(
        skill=skill,
        skill_md_lines=_skill_closure_metric(
            record["skill_md_lines"], source=source, index=index, field="skill_md_lines"
        ),
        skill_md_estimated_tokens=_skill_closure_metric(
            record["skill_md_estimated_tokens"],
            source=source,
            index=index,
            field="skill_md_estimated_tokens",
        ),
        skill_md_content_estimated_tokens=_skill_closure_metric(
            record["skill_md_content_estimated_tokens"],
            source=source,
            index=index,
            field="skill_md_content_estimated_tokens",
        ),
        closure_lines=_skill_closure_metric(
            record["closure_lines"], source=source, index=index, field="closure_lines"
        ),
        closure_estimated_tokens=_skill_closure_metric(
            record["closure_estimated_tokens"],
            source=source,
            index=index,
            field="closure_estimated_tokens",
        ),
        closure_content_estimated_tokens=_skill_closure_metric(
            record["closure_content_estimated_tokens"],
            source=source,
            index=index,
            field="closure_content_estimated_tokens",
        ),
        files=_skill_closure_files(
            record["files"], source=source, index=index, field="files", allow_empty=False
        ),
        conditional_lines=_skill_closure_metric(
            record["conditional_lines"],
            source=source,
            index=index,
            field="conditional_lines",
        ),
        conditional_estimated_tokens=_skill_closure_metric(
            record["conditional_estimated_tokens"],
            source=source,
            index=index,
            field="conditional_estimated_tokens",
        ),
        conditional_content_estimated_tokens=_skill_closure_metric(
            record["conditional_content_estimated_tokens"],
            source=source,
            index=index,
            field="conditional_content_estimated_tokens",
        ),
        conditional_files=_skill_closure_files(
            record["conditional_files"],
            source=source,
            index=index,
            field="conditional_files",
            allow_empty=True,
        ),
    )


def _validate_skill_closure_rows(
    rows: Sequence[SkillClosureBaselineRow], *, source: str
) -> list[SkillClosureBaselineRow]:
    skills = [row.skill for row in rows]
    if len(skills) != len(set(skills)) or frozenset(skills) != frozenset(
        SKILL_CLOSURE_RATCHETED_TARGETS
    ):
        raise ScanError(f"{source}: baseline must contain one row per ratcheted target")
    return sorted(rows, key=lambda row: row.skill)


def parse_skill_closure_baseline(text: str, *, source: str) -> list[SkillClosureBaselineRow]:
    """Parse exact aggregate closure records and reject incomplete target sets."""
    try:
        decoded = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        raise ScanError(f"{source}: cannot load baseline: {exc}") from exc
    if not isinstance(decoded, list):
        raise ScanError(f"{source}: baseline must be a top-level JSON array")
    rows = [
        _skill_closure_row(raw, source=source, index=index)
        for index, raw in enumerate(cast("list[object]", decoded), start=1)
    ]
    return _validate_skill_closure_rows(rows, source=source)


def load_skill_closure_baseline(
    path: str | Path, *, root: Path
) -> list[SkillClosureBaselineRow]:
    """Trusted-read and parse a complete aggregate closure baseline."""
    destination = _validate_baseline_path(path, root=root, write_mode=False)
    if not _baseline_exists(destination, root=root):
        raise ScanError(f"baseline not found: {destination}")
    try:
        text = larch_io.read_trusted_text(destination, root=root, reject_cr=True)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScanError(f"cannot read baseline {destination}: {exc}") from exc
    return parse_skill_closure_baseline(text, source=str(destination))


def skill_closure_row_record(row: SkillClosureBaselineRow) -> dict[str, object]:
    """Render one aggregate record using the committed canonical fields."""
    return {
        "skill": row.skill,
        "skill_md_lines": row.skill_md_lines,
        "skill_md_estimated_tokens": row.skill_md_estimated_tokens,
        "skill_md_content_estimated_tokens": row.skill_md_content_estimated_tokens,
        "closure_lines": row.closure_lines,
        "closure_estimated_tokens": row.closure_estimated_tokens,
        "closure_content_estimated_tokens": row.closure_content_estimated_tokens,
        "files": list(row.files),
        "conditional_lines": row.conditional_lines,
        "conditional_estimated_tokens": row.conditional_estimated_tokens,
        "conditional_content_estimated_tokens": row.conditional_content_estimated_tokens,
        "conditional_files": list(row.conditional_files),
    }


def serialize_skill_closure_baseline(rows: Sequence[SkillClosureBaselineRow]) -> str:
    """Serialize complete aggregate closure rows byte-stably."""
    ordered = _validate_skill_closure_rows(rows, source="skill-closure baseline")
    records = [skill_closure_row_record(row) for row in ordered]
    return json.dumps(records, indent=2, sort_keys=True) + "\n"


def write_skill_closure_baseline(
    path: str | Path, *, root: Path, rows: Sequence[SkillClosureBaselineRow]
) -> list[SkillClosureBaselineRow]:
    """Atomically write a complete baseline and prove byte/record read-back."""
    destination = _validate_baseline_path(
        path, root=root, write_mode=True, create_missing_parents=True
    )
    intended = serialize_skill_closure_baseline(rows)
    return _write_baseline_with_readback(
        destination,
        root=root,
        intended=intended,
        parse=lambda text: parse_skill_closure_baseline(text, source=str(destination)),
    )


def _skill_closure_conditional_growth_allowed(
    live: SkillClosureBaselineRow, baseline: SkillClosureBaselineRow, metric: str
) -> bool:
    moved_to_conditional = (
        set(baseline.files) - set(baseline.conditional_files)
    ) & set(live.conditional_files)
    if not moved_to_conditional:
        return False
    eager_metric = _SKILL_CLOSURE_CONDITIONAL_TO_EAGER_METRIC[metric]
    live_total = getattr(live, eager_metric) + getattr(live, metric)
    baseline_total = getattr(baseline, eager_metric) + getattr(baseline, metric)
    return live_total <= baseline_total


def skill_closure_growth_violations(
    live_rows: Sequence[SkillClosureBaselineRow],
    baseline_rows: Sequence[SkillClosureBaselineRow],
) -> list[str]:
    """Compare selected live aggregate rows against a complete typed baseline."""
    _ = _validate_skill_closure_rows(baseline_rows, source="skill-closure baseline")
    selected = list(live_rows)
    if not selected or len({row.skill for row in selected}) != len(selected):
        raise ScanError("live skill-closure rows must select unique ratcheted targets")
    if any(row.skill not in SKILL_CLOSURE_RATCHETED_TARGETS for row in selected):
        raise ScanError("live skill-closure rows contain an invalid ratcheted target")
    baseline_by_skill = {row.skill: row for row in baseline_rows}
    violations: list[str] = []
    for live in selected:
        baseline = baseline_by_skill[live.skill]
        violations.extend(
            f"{live.skill}: {metric} {getattr(live, metric)} > baseline {getattr(baseline, metric)}"
            for metric in SKILL_CLOSURE_METRIC_FIELDS
            if getattr(live, metric) > getattr(baseline, metric)
        )
        if live.skill == "review":
            violations.extend(
                f"{live.skill}: {metric} {getattr(live, metric)} > baseline {getattr(baseline, metric)}"
                for metric in SKILL_CLOSURE_CONDITIONAL_METRIC_FIELDS
                if getattr(live, metric) > getattr(baseline, metric)
                and not _skill_closure_conditional_growth_allowed(live, baseline, metric)
            )
        baseline_files = set(baseline.files) | set(baseline.conditional_files)
        live_files = set(live.files) | set(live.conditional_files)
        violations.extend(
            f"{live.skill}: baseline-tracked file dropped {path}"
            for path in sorted(baseline_files - live_files)
        )
        if live.skill in SKILL_CLOSURE_FILE_RATCHET_TARGETS:
            violations.extend(
                f"{live.skill}: files added {path}"
                for path in live.files
                if path not in set(baseline.files)
            )
    return violations


# These intentionally-small schemas cover lints whose identities do not fit the
# location/metric/occurrence baseline families above.  Keeping them here gives
# those lints the same trusted read, strict JSON, duplicate, and atomic-write
# contract without weakening their committed payloads into free-form records.
IdentityBaselineKind = Literal[
    "keyword_only", "wire_artifact_pairing", "renderer_golden_tests", "guideline_no_exception"
]


@dataclass(frozen=True)
class KeywordOnlyBaselineRow:
    """Reason-less identity for one keyword-only exception."""

    file: str
    qualified_symbol: str

    @property
    def identity(self) -> tuple[str, str]:
        return (self.file, self.qualified_symbol)


@dataclass(frozen=True)
class WireArtifactPairingBaselineRow:
    """Reason-bearing identity for an intentionally one-sided artifact."""

    artifact: str
    side: Literal["external-writer", "external-reader", "intentionally-one-sided"]
    reason: str

    @property
    def identity(self) -> tuple[str, str]:
        return (self.artifact, self.side)


@dataclass(frozen=True)
class RendererGoldenTestsBaselineRow:
    """Reason-bearing identity for one renderer test-coverage exception."""

    file: str
    function_name: str
    reason: str

    @property
    def identity(self) -> tuple[str, str]:
        return (self.file, self.function_name)


@dataclass(frozen=True)
class GuidelineNoExceptionBaselineRow:
    """Reason-bearing identity for one guideline exception."""

    guideline_id: str
    reason: str

    @property
    def identity(self) -> tuple[str]:
        return (self.guideline_id,)


IdentityBaselineRow: TypeAlias = (
    KeywordOnlyBaselineRow
    | WireArtifactPairingBaselineRow
    | RendererGoldenTestsBaselineRow
    | GuidelineNoExceptionBaselineRow
)


@dataclass(frozen=True)
class IdentityLintCli:
    """Shared CLI shape for an identity-baseline lint with a custom scanner."""

    prog: str
    description: str
    baseline_filename: str
    writable: bool = False
    positional_root: bool = False


@dataclass(frozen=True)
class IdentityLintArgs:
    """Validated operator arguments for an identity-baseline lint."""

    root: Path
    write_baseline: bool
    initial_reason: str | None


def parse_identity_lint_argv(
    argv: Sequence[str], *, cli: IdentityLintCli, default_root: Path
) -> IdentityLintArgs | None:
    """Parse a custom-scanner lint's compatible root/write command surface."""
    parser = argparse.ArgumentParser(prog=cli.prog, description=cli.description)
    if cli.positional_root:
        _ = parser.add_argument("positional_root", nargs="?", help="Optional repository root.")
        _ = parser.add_argument("--root", help="Repository root (overrides positional root).")
    else:
        _ = parser.add_argument("--root", default=str(default_root))
    if cli.writable:
        _ = parser.add_argument("--write", action="store_true", help=f"Regenerate {cli.baseline_filename} from live findings.")
        _ = parser.add_argument("--initial-reason", help="Reason used for new live findings during --write.")
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None
    root_text = (
        cast("str | None", parsed.root) or cast("str | None", getattr(parsed, "positional_root", None))
    )
    initial_reason = cast("str | None", getattr(parsed, "initial_reason", None))
    if initial_reason is not None and not _nonempty_single_line(initial_reason):
        print("--initial-reason must be non-empty", file=sys.stderr)
        return None
    return IdentityLintArgs(
        root=Path(root_text).resolve() if root_text else default_root.resolve(),
        write_baseline=bool(getattr(parsed, "write", False)),
        initial_reason=initial_reason,
    )


def _baseline_kind(row: BaselineRow) -> BaselineKind:
    if isinstance(row, GenericBaselineRow):
        return "generic"
    if isinstance(row, SymbolMetricBaselineRow):
        return "symbol_metric"
    return "occurrence"


def _baseline_sort_key(row: BaselineRow) -> tuple[object, ...]:
    if isinstance(row, GenericBaselineRow):
        return ("generic", row.path, row.rule_id, row.message, row.anchor or "", row.line)
    if isinstance(row, SymbolMetricBaselineRow):
        return ("symbol_metric", row.path, row.rule_id, row.qualified_symbol)
    return (
        "occurrence",
        row.path,
        row.qualified_symbol,
        row.occurrence_values,
        row.occurrence,
    )


def _baseline_identity(row: BaselineRow) -> tuple[object, ...]:
    return row.identity


def _baseline_row_display(row: BaselineRow) -> str:
    if isinstance(row, GenericBaselineRow):
        return f"{row.path}:{row.line}: {row.rule_id} {row.message}"
    if isinstance(row, SymbolMetricBaselineRow):
        return f"{row.path}:{row.qualified_symbol}: {row.rule_id} metric {row.metric}"
    file_name = _occurrence_json_file(row.path)
    values = " ".join(f"{key}={value}" for key, value in row.occurrence_values)
    symbol = row.qualified_symbol
    if symbol is not None:
        return f"{file_name}:{symbol} {values}#{row.occurrence}"
    return f"{file_name} {values}#{row.occurrence}"


def _occurrence_repo_path(file_name: str, *, source: str, index: int) -> str:
    if not _is_single_line(file_name):
        raise ScanError(f"{source}: baseline row {index} has invalid file")
    normalized = file_name.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith(PYTHON_TREE_PREFIX):
        raise ScanError(f"{source}: baseline row {index} has invalid file")
    parts = Path(normalized).parts
    malformed = (
        normalized != file_name
        or normalized.startswith("/")
        or not normalized.endswith(".py")
    )
    malformed = malformed or "" in normalized.split("/")
    if malformed or "." in parts or ".." in parts:
        raise ScanError(f"{source}: baseline row {index} has invalid file")
    return f"{PYTHON_TREE_PREFIX}{normalized}"


def _occurrence_json_file(path: str) -> str:
    if not path.startswith(PYTHON_TREE_PREFIX):
        raise ScanError(
            f"occurrence baseline path must start with {PYTHON_TREE_PREFIX!r}: {path}"
        )
    relative = path[len(PYTHON_TREE_PREFIX) :]
    if not relative or relative.startswith("/") or ".." in relative.split("/"):
        raise ScanError(f"occurrence baseline path is invalid: {path}")
    return relative


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


def _occurrence_baseline_row(
    record: Mapping[str, object],
    *,
    index: int,
    source: str,
    occurrence_fields: OccurrenceFields,
    symbol_optional: bool = False,
) -> OccurrenceBaselineRow:
    file_name = record["file"]
    occurrence = record["occurrence"]
    reason = record["reason"]
    if not isinstance(file_name, str):
        raise ScanError(f"{source}: baseline row {index} has invalid file")
    path = _occurrence_repo_path(file_name, source=source, index=index)
    if symbol_optional:
        qualified_symbol = record.get("qualified_symbol")
    else:
        qualified_symbol = record["qualified_symbol"]
    if qualified_symbol is not None and not _is_single_line(qualified_symbol):
        raise ScanError(f"{source}: baseline row {index} has invalid qualified_symbol")
    values: list[tuple[str, str]] = []
    for field_name in occurrence_fields:
        value = record[field_name]
        if not _is_single_line(value):
            raise ScanError(f"{source}: baseline row {index} has invalid {field_name}")
        values.append((field_name, cast("str", value)))
    if (
        not isinstance(occurrence, int)
        or isinstance(occurrence, bool)
        or occurrence < 1
    ):
        raise ScanError(f"{source}: baseline row {index} has invalid occurrence")
    if not _nonempty_single_line(reason):
        raise ScanError(f"{source}: baseline row {index} has invalid reason")
    return OccurrenceBaselineRow(
        path,
        cast("str | None", qualified_symbol),
        values[0][1] if values else "",
        occurrence,
        cast("str", reason),
        tuple(values),
    )


def _parse_baseline_row(
    raw: object,
    *,
    index: int,
    source: str,
    occurrence_fields: OccurrenceFields,
    symbol_optional: bool = False,
) -> BaselineRow:
    if not isinstance(raw, dict):
        raise ScanError(f"{source}: baseline row {index} must be an object")
    record = cast("dict[str, object]", raw)
    generic_keys = frozenset({"path", "line", "rule_id", "message", "reason"})
    anchored_generic_keys = generic_keys | {"anchor"}
    symbol_keys = frozenset({"path", "rule_id", "qualified_symbol", "metric", "reason"})
    occurrence_keys = frozenset(
        {"file", "qualified_symbol", *occurrence_fields, "occurrence", "reason"}
    )
    keys = frozenset(record)
    if keys in {generic_keys, anchored_generic_keys}:
        return _generic_baseline_row(record, index=index, source=source)
    if keys == symbol_keys:
        return _symbol_metric_baseline_row(record, index=index, source=source)
    if keys == occurrence_keys or (
        symbol_optional
        and keys == frozenset({"file", *occurrence_fields, "occurrence", "reason"})
    ):
        return _occurrence_baseline_row(
            record,
            index=index,
            source=source,
            occurrence_fields=occurrence_fields,
            symbol_optional=symbol_optional,
        )
    if occurrence_fields == ("pattern_name",) and keys == frozenset(
        {"file", "qualified_symbol", "normalized_condition", "occurrence", "reason"}
    ):
        parsed = _occurrence_baseline_row(
            record,
            index=index,
            source=source,
            occurrence_fields=("normalized_condition",),
        )
        return OccurrenceBaselineRow(
            parsed.path,
            parsed.qualified_symbol,
            parsed.pattern_name,
            parsed.occurrence,
            parsed.reason,
        )
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


def _parse_baseline_text(
    text: str,
    *,
    source: str,
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    symbol_optional: bool = False,
) -> list[BaselineRow]:
    try:
        decoded = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        raise ScanError(f"{source}: invalid JSON baseline: {exc.msg}") from exc
    if not isinstance(decoded, list):
        raise ScanError(f"{source}: baseline must be a top-level JSON array")
    raw_rows = cast("list[object]", decoded)
    rows = [
        _parse_baseline_row(
            raw,
            index=index,
            source=source,
            occurrence_fields=occurrence_fields,
            symbol_optional=symbol_optional,
        )
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


def _create_baseline_parent(path: Path) -> None:
    """Create one absent baseline parent and immediately revalidate its type."""
    try:
        _ = path.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise ScanError(f"failed to inspect baseline path {path}: {exc}") from exc
    else:
        raise ScanError(f"baseline parent changed while validating: {path}")
    try:
        path.mkdir()
    except OSError as exc:
        raise ScanError(f"failed to create baseline parent {path}: {exc}") from exc
    _ = _validate_baseline_component(path, is_parent=True)


def _validate_baseline_path(
    raw: str | Path,
    *,
    root: Path,
    write_mode: bool,
    create_missing_parents: bool = False,
) -> Path:
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
        is_parent = index < len(components) - 1
        try:
            exists = _validate_baseline_component(current, is_parent=is_parent)
        except ScanError:
            if not (write_mode and create_missing_parents and is_parent):
                raise
            _create_baseline_parent(current)
            exists = True
        if not exists:
            break
    if write_mode and not absolute.parent.is_dir():
        raise ScanError(f"baseline parent does not exist: {absolute.parent}")
    return absolute


def _load_baseline(
    path: Path,
    *,
    root: Path,
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    symbol_optional: bool = False,
) -> list[BaselineRow]:
    try:
        text = larch_io.read_trusted_text(path, root=root, reject_cr=True)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScanError(f"failed to read baseline {path}: {exc}") from exc
    return _parse_baseline_text(
        text,
        source=f"baseline {path}",
        occurrence_fields=occurrence_fields,
        symbol_optional=symbol_optional,
    )


def _baseline_exists(path: Path, *, root: Path) -> bool:
    try:
        return larch_io.trusted_file_present(path, root=root)
    except OSError as exc:
        raise ScanError(f"failed to inspect baseline {path}: {exc}") from exc


def _write_baseline_with_readback(
    destination: Path,
    *,
    root: Path,
    intended: str,
    parse: Callable[[str], T],
) -> T:
    """Atomically publish canonical bytes and verify their typed read-back."""
    expected = parse(intended)
    try:
        larch_io.trusted_atomic_write(destination, intended, root=root)
        read_back = larch_io.read_trusted_text(destination, root=root, reject_cr=True)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScanError(f"failed to write baseline {destination}: {exc}") from exc
    if read_back != intended:
        raise ScanError(f"baseline read-back bytes differ after write: {destination}")
    parsed = parse(read_back)
    if parsed != expected:
        raise ScanError(f"baseline read-back records differ after write: {destination}")
    return parsed


def _identity_baseline_kind(row: IdentityBaselineRow) -> IdentityBaselineKind:
    if isinstance(row, KeywordOnlyBaselineRow):
        return "keyword_only"
    if isinstance(row, WireArtifactPairingBaselineRow):
        return "wire_artifact_pairing"
    if isinstance(row, RendererGoldenTestsBaselineRow):
        return "renderer_golden_tests"
    return "guideline_no_exception"


def identity_baseline_identity(row: IdentityBaselineRow) -> tuple[object, ...]:
    """Return a schema's stable, reason-free baseline identity."""
    return row.identity


def identity_baseline_sort_key(row: IdentityBaselineRow) -> tuple[object, ...]:
    """Return deterministic schema-local ordering for a typed identity row."""
    return (_identity_baseline_kind(row), *row.identity)


def _validate_identity_row_kinds(
    rows: Sequence[IdentityBaselineRow], *, kind: IdentityBaselineKind, source: str
) -> None:
    """Reject a mixed or caller-mismatched schema before comparison or publication."""
    if any(_identity_baseline_kind(row) != kind for row in rows):
        raise ScanError(f"{source}: identity baseline rows use the wrong schema")


def _require_identity_keys(
    record: Mapping[str, object], *, expected: frozenset[str], index: int, source: str
) -> None:
    keys = frozenset(record)
    if keys != expected:
        raise ScanError(f"{source}: baseline row {index} has unsupported keys")


def _keyword_only_identity_row(record: Mapping[str, object], *, index: int, source: str) -> KeywordOnlyBaselineRow:
    _require_identity_keys(record, expected=frozenset({"file", "qualified_symbol"}), index=index, source=source)
    file_name, symbol = record["file"], record["qualified_symbol"]
    if not _is_single_line(file_name) or not _is_single_line(symbol):
        raise ScanError(f"{source}: baseline row {index} has invalid keyword-only identity")
    return KeywordOnlyBaselineRow(cast("str", file_name), cast("str", symbol))


def _wire_artifact_identity_row(record: Mapping[str, object], *, index: int, source: str) -> WireArtifactPairingBaselineRow:
    _require_identity_keys(record, expected=frozenset({"artifact", "side", "reason"}), index=index, source=source)
    artifact, side, reason = record["artifact"], record["side"], record["reason"]
    allowed_sides = {"external-writer", "external-reader", "intentionally-one-sided"}
    if not _nonempty_single_line(artifact) or side not in allowed_sides or not _nonempty_single_line(reason):
        raise ScanError(f"{source}: baseline row {index} has invalid wire-artifact row")
    return WireArtifactPairingBaselineRow(cast("str", artifact), cast("Literal['external-writer', 'external-reader', 'intentionally-one-sided']", side), cast("str", reason))


def _renderer_identity_row(record: Mapping[str, object], *, index: int, source: str) -> RendererGoldenTestsBaselineRow:
    _require_identity_keys(record, expected=frozenset({"file", "function_name", "reason"}), index=index, source=source)
    file_name, function_name, reason = record["file"], record["function_name"], record["reason"]
    normalized = normalize_python_file_path(file_name) if isinstance(file_name, str) else ""
    invalid_path = not _is_single_line(file_name) or normalized != file_name or not normalized.startswith("larch/report/") or not normalized.endswith(".py") or bool({"", ".", ".."}.intersection(normalized.split("/")))
    if invalid_path or not _nonempty_single_line(function_name) or not _nonempty_single_line(reason):
        raise ScanError(f"{source}: baseline row {index} has invalid renderer row")
    return RendererGoldenTestsBaselineRow(cast("str", file_name), cast("str", function_name), cast("str", reason))


def _guideline_identity_row(record: Mapping[str, object], *, index: int, source: str) -> GuidelineNoExceptionBaselineRow:
    _require_identity_keys(record, expected=frozenset({"guideline_id", "reason"}), index=index, source=source)
    guideline_id, reason = record["guideline_id"], record["reason"]
    if (
        not _nonempty_single_line(guideline_id)
        or re.fullmatch(r"G-[A-Za-z][A-Za-z0-9-]*-\d+", cast("str", guideline_id)) is None
        or not _nonempty_single_line(reason)
    ):
        raise ScanError(f"{source}: baseline row {index} has invalid guideline row")
    return GuidelineNoExceptionBaselineRow(cast("str", guideline_id), cast("str", reason))


def _identity_baseline_row(record: Mapping[str, object], *, kind: IdentityBaselineKind, index: int, source: str) -> IdentityBaselineRow:
    if kind == "keyword_only":
        return _keyword_only_identity_row(record, index=index, source=source)
    if kind == "wire_artifact_pairing":
        return _wire_artifact_identity_row(record, index=index, source=source)
    if kind == "renderer_golden_tests":
        return _renderer_identity_row(record, index=index, source=source)
    return _guideline_identity_row(record, index=index, source=source)


def parse_identity_baseline(
    text: str, *, kind: IdentityBaselineKind, source: str
) -> list[IdentityBaselineRow]:
    """Parse one exact identity schema, rejecting unknown, missing, and duplicate rows."""
    try:
        decoded = cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        raise ScanError(f"{source}: invalid JSON baseline: {exc.msg}") from exc
    if not isinstance(decoded, list):
        raise ScanError(f"{source}: baseline must be a top-level JSON array")
    raw_rows = cast("list[object]", decoded)
    rows = [
        _identity_baseline_row(cast("Mapping[str, object]", raw), kind=kind, index=index, source=source)
        if isinstance(raw, dict)
        else _identity_baseline_row({}, kind=kind, index=index, source=source)
        for index, raw in enumerate(raw_rows)
    ]
    identities: set[tuple[object, ...]] = set()
    for row in rows:
        identity = identity_baseline_identity(row)
        if identity in identities:
            raise ScanError(f"{source}: duplicate baseline identity")
        identities.add(identity)
    return sorted(rows, key=identity_baseline_sort_key)


def load_identity_baseline(
    path: str | Path,
    *,
    root: Path,
    kind: IdentityBaselineKind,
    allow_missing: bool = False,
) -> list[IdentityBaselineRow]:
    """Read an exact identity baseline through the engine's trusted-file policy."""
    destination = _validate_baseline_path(path, root=root, write_mode=False)
    if not _baseline_exists(destination, root=root):
        if allow_missing:
            return []
        raise ScanError(f"failed to read baseline {destination}: file does not exist")
    try:
        text = larch_io.read_trusted_text(destination, root=root, reject_cr=True)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ScanError(f"cannot read baseline {destination}: {exc}") from exc
    return parse_identity_baseline(text, kind=kind, source=f"baseline {destination}")


def serialize_identity_baseline(rows: Sequence[IdentityBaselineRow]) -> str:
    """Serialize typed identity rows in their legacy field order."""
    records: list[dict[str, object]] = []
    for row in sorted(rows, key=identity_baseline_sort_key):
        if isinstance(row, KeywordOnlyBaselineRow):
            records.append({"file": row.file, "qualified_symbol": row.qualified_symbol})
        elif isinstance(row, WireArtifactPairingBaselineRow):
            records.append({"artifact": row.artifact, "side": row.side, "reason": row.reason})
        elif isinstance(row, RendererGoldenTestsBaselineRow):
            records.append({"file": row.file, "function_name": row.function_name, "reason": row.reason})
        else:
            records.append({"guideline_id": row.guideline_id, "reason": row.reason})
    return json.dumps(records, indent=2) + "\n"


def compare_identity_baseline(
    live_rows: Sequence[IdentityBaselineRow], baseline_rows: Sequence[IdentityBaselineRow]
) -> tuple[list[IdentityBaselineRow], list[IdentityBaselineRow], list[IdentityBaselineRow]]:
    """Return new, stale, and matching rows by each schema's stable identity."""
    if live_rows and baseline_rows and _identity_baseline_kind(live_rows[0]) != _identity_baseline_kind(baseline_rows[0]):
        raise ScanError("live findings and baseline rows use different shapes")
    baseline_by_id = {identity_baseline_identity(row): row for row in baseline_rows}
    live_ids = {identity_baseline_identity(row) for row in live_rows}
    new = [row for row in live_rows if identity_baseline_identity(row) not in baseline_by_id]
    stale = [row for row in baseline_rows if identity_baseline_identity(row) not in live_ids]
    matched = [row for row in live_rows if identity_baseline_identity(row) in baseline_by_id]
    return (
        sorted(new, key=identity_baseline_sort_key),
        sorted(stale, key=identity_baseline_sort_key),
        sorted(matched, key=identity_baseline_sort_key),
    )


def write_identity_baseline(  # noqa: PLR0913 - public baseline-write contract is explicit.
    path: str | Path,
    *,
    root: Path,
    kind: IdentityBaselineKind,
    live_rows: Sequence[IdentityBaselineRow],
    baseline_rows: Sequence[IdentityBaselineRow],
    initial_reason: str | None = None,
) -> list[IdentityBaselineRow]:
    """Preserve reasons, atomically write, and byte/structure-read-back an identity baseline."""
    destination = _validate_baseline_path(path, root=root, write_mode=True)
    _validate_identity_row_kinds(live_rows, kind=kind, source="live findings")
    _validate_identity_row_kinds(baseline_rows, kind=kind, source="baseline")
    previous = {identity_baseline_identity(row): row for row in baseline_rows}
    written: list[IdentityBaselineRow] = []
    missing_reason_ids: list[tuple[object, ...]] = []
    for row in live_rows:
        prior = previous.get(identity_baseline_identity(row))
        if isinstance(row, KeywordOnlyBaselineRow):
            written.append(row)
            continue
        reason = getattr(prior, "reason", None) if prior is not None else initial_reason
        if not _nonempty_single_line(reason):
            missing_reason_ids.append(identity_baseline_identity(row))
            continue
        if isinstance(row, WireArtifactPairingBaselineRow):
            written.append(WireArtifactPairingBaselineRow(row.artifact, row.side, cast("str", reason)))
        elif isinstance(row, RendererGoldenTestsBaselineRow):
            written.append(RendererGoldenTestsBaselineRow(row.file, row.function_name, cast("str", reason)))
        else:
            written.append(GuidelineNoExceptionBaselineRow(row.guideline_id, cast("str", reason)))
    if missing_reason_ids:
        labels = "\n  ".join(":".join(str(value) for value in identity) for identity in missing_reason_ids)
        raise ScanError(
            "missing baseline reasons for live findings; supply initial_reason:\n  " + labels
        )
    intended = serialize_identity_baseline(written)
    parsed = _write_baseline_with_readback(
        destination,
        root=root,
        intended=intended,
        parse=lambda text: parse_identity_baseline(
            text, kind=kind, source=f"baseline {destination}"
        ),
    )
    ordered = sorted(written, key=identity_baseline_sort_key)
    if parsed != ordered:
        raise ScanError(f"baseline read-back records differ after write: {destination}")
    return ordered


def _finding_occurrence_values(
    finding: Finding, *, occurrence_fields: OccurrenceFields
) -> tuple[tuple[str, str], ...]:
    if finding.occurrence_values:
        return finding.occurrence_values
    if len(occurrence_fields) == 1 and finding.pattern_name is not None:
        return ((occurrence_fields[0], finding.pattern_name),)
    return ()


def _project_finding(
    finding: Finding,
    *,
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    symbol_optional: bool = False,
) -> BaselineRow:
    if finding.occurrence is not None and (
        finding.qualified_symbol is not None or symbol_optional
    ):
        if finding.metric is not None:
            raise ScanError(
                "occurrence baseline findings must not set metric"
            )
        occurrence_values = _finding_occurrence_values(
            finding, occurrence_fields=occurrence_fields
        )
        pattern_name = finding.pattern_name
        if pattern_name is None and occurrence_values:
            pattern_name = occurrence_values[0][1]
        return OccurrenceBaselineRow(
            finding.path,
            finding.qualified_symbol,
            pattern_name or "",
            finding.occurrence,
            "",
            occurrence_values,
        )
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


def _project_findings(
    findings: Sequence[Finding],
    *,
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    symbol_optional: bool = False,
) -> list[BaselineRow]:
    rows = [
        _project_finding(
            finding, occurrence_fields=occurrence_fields, symbol_optional=symbol_optional
        )
        for finding in findings
    ]
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
    live_rows: Sequence[BaselineRow],
    baseline_rows: Sequence[BaselineRow],
) -> tuple[list[BaselineRow], list[BaselineRow]]:
    _ensure_compatible_shapes(live_rows, baseline_rows)
    indexed = {_baseline_identity(row): row for row in baseline_rows}
    active: list[BaselineRow] = []
    seen: set[tuple[object, ...]] = set()
    for row in live_rows:
        identity = _baseline_identity(row)
        prior = indexed.get(identity)
        seen.add(identity)
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


def _occurrence_record(
    row: OccurrenceBaselineRow, *, occurrence_fields: OccurrenceFields
) -> dict[str, object]:
    file_name = _occurrence_json_file(row.path)
    values = dict(row.occurrence_values)
    if row.values == () and len(occurrence_fields) == 1:
        values = {occurrence_fields[0]: row.pattern_name}
    if occurrence_fields == ("normalized_condition",):
        # Legacy unreachable-branch field order (occurrence before condition).
        return {
            "file": file_name,
            "qualified_symbol": row.qualified_symbol,
            "occurrence": row.occurrence,
            "normalized_condition": values["normalized_condition"],
            "reason": row.reason,
        }
    record: dict[str, object] = {"file": file_name}
    if row.qualified_symbol is not None:
        record["qualified_symbol"] = row.qualified_symbol
    record.update(values)
    record["occurrence"] = row.occurrence
    record["reason"] = row.reason
    return record


def _serialized_baseline(
    rows: Sequence[BaselineRow],
    *,
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    occurrence_pattern_field: OccurrencePatternField | None = None,
) -> str:
    if occurrence_pattern_field is not None:
        occurrence_fields = (occurrence_pattern_field,)
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
        elif isinstance(row, SymbolMetricBaselineRow):
            records.append(
                {
                    "path": row.path,
                    "rule_id": row.rule_id,
                    "qualified_symbol": row.qualified_symbol,
                    "metric": row.metric,
                    "reason": row.reason,
                }
            )
        else:
            # Preserve legacy field order and omit sort_keys for byte-stable rewrites.
            records.append(
                _occurrence_record(row, occurrence_fields=occurrence_fields)
            )
    if rows and isinstance(rows[0], OccurrenceBaselineRow):
        return json.dumps(records, indent=2) + "\n"
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
        elif isinstance(row, SymbolMetricBaselineRow):
            written.append(
                SymbolMetricBaselineRow(
                    row.path,
                    row.rule_id,
                    row.qualified_symbol,
                    row.metric,
                    reason,
                )
            )
        else:
            written.append(
                OccurrenceBaselineRow(
                    row.path,
                    row.qualified_symbol,
                    row.pattern_name,
                    row.occurrence,
                    reason,
                    row.values,
                )
            )
    return written


def _publish_baseline(
    path: Path,
    *,
    root: Path,
    rows: Sequence[BaselineRow],
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    symbol_optional: bool = False,
) -> None:
    intended = _serialized_baseline(
        rows, occurrence_fields=occurrence_fields
    )
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
        parsed = _parse_baseline_text(
            read_back,
            source=f"baseline {path}",
            occurrence_fields=occurrence_fields,
            symbol_optional=symbol_optional,
        )
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
    discovery_pathspecs: Sequence[str] | None = rule.pathspecs
    if discovery_pathspecs is None and paths is not None:
        # Validate selectors before discovery so bad pathspecs fail closed and
        # git only enumerates in-scope cached paths.
        discovery_pathspecs = [
            _validate_requested_path(item, root=root)[0] for item in paths
        ]
    tracked = _discover_tracked_paths(
        root,
        runner,
        pathspecs=discovery_pathspecs,
        source_filter=rule.source_filter,
        exclude_tracked_symlinks=rule.exclude_tracked_symlinks,
    )
    selected = _filter_tracked_paths(tracked, root=root, paths=paths)
    if rule.source_filter is not None:
        selected = [rel for rel in selected if rule.source_filter(rel)]
    pragma_re = re.compile(rf"#\s*{re.escape(rule.suppression_token)}:\s*ok\s+(\S.*)$")
    empty_pragma_re = re.compile(rf"#\s*{re.escape(rule.suppression_token)}:\s*ok\s*$")
    sources = [_load_source(root, rel_path) for rel_path in selected]
    if rule.prepare_corpus is not None:
        rule.prepare_corpus(sources)
    collected: list[Finding] = []
    for source in sources:
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
    findings: Sequence[Finding],
    active_rows: Sequence[BaselineRow],
    *,
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    symbol_optional: bool = False,
) -> list[Finding]:
    active = {_baseline_identity(row) for row in active_rows}
    rendered = [
        finding
        for finding in findings
        if _baseline_identity(
            _project_finding(
                finding,
                occurrence_fields=occurrence_fields,
                symbol_optional=symbol_optional,
            )
        )
        in active
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


def _matching_baseline_findings(
    findings: Sequence[Finding],
    *,
    baseline_rows: Sequence[BaselineRow],
    active_rows: Sequence[BaselineRow],
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    symbol_optional: bool = False,
) -> list[Finding]:
    """Return live findings whose identities are grandfathered (matched, not new)."""
    baseline_ids = {_baseline_identity(row) for row in baseline_rows}
    active_ids = {_baseline_identity(row) for row in active_rows}
    matched: list[Finding] = []
    for finding in findings:
        identity = _baseline_identity(
            _project_finding(
                finding,
                occurrence_fields=occurrence_fields,
                symbol_optional=symbol_optional,
            )
        )
        if identity in baseline_ids and identity not in active_ids:
            matched.append(finding)
    matched.sort(
        key=lambda item: (
            item.path,
            item.line,
            item.rule_id,
            item.message,
            item.qualified_symbol or "",
            item.metric if item.metric is not None else -1,
        )
    )
    return matched


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
    occurrence_fields: OccurrenceFields = ("pattern_name",),
    warn_matching_baseline: bool = False,
    symbol_optional: bool = False,
    stale_as_finding: bool = False,
) -> tuple[int, list[Finding], list[str]]:
    live_rows = _project_findings(
        collected, occurrence_fields=occurrence_fields, symbol_optional=symbol_optional
    )
    if write_baseline:
        written = _rows_for_write(
            live_rows, baseline_rows, initial_reason=initial_reason
        )
        _publish_baseline(
            destination,
            root=root,
            rows=written,
            occurrence_fields=occurrence_fields,
            symbol_optional=symbol_optional,
        )
        return EXIT_CLEAN, [], []
    scoped_baseline = _selected_baseline_rows(baseline_rows, root=root, paths=paths)
    active_rows, stale_rows = _baseline_comparison(live_rows, scoped_baseline)
    warnings = [
        f"warning: stale baseline row: {_baseline_row_display(row)}"
        for row in stale_rows
    ]
    if warn_matching_baseline:
        warnings.extend(
            f"warning: matching baseline finding: {render_finding(finding)}"
            for finding in _matching_baseline_findings(
                collected,
                baseline_rows=scoped_baseline,
                active_rows=active_rows,
                occurrence_fields=occurrence_fields,
                symbol_optional=symbol_optional,
            )
        )
    if strict_stale and stale_rows:
        raise StrictStaleError(warnings)
    has_failures = bool(active_rows) or (stale_as_finding and bool(stale_rows))
    return (
        EXIT_FINDINGS if has_failures else EXIT_CLEAN,
        _findings_for_active_rows(
            collected,
            active_rows,
            occurrence_fields=occurrence_fields,
            symbol_optional=symbol_optional,
        ),
        warnings,
    )


def run_rule(  # noqa: C901, PLR0912, PLR0913 - public API preserves direct keyword options.
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
    Occurrence baselines may be absent when the live scan is clean unless the
    rule requires a baseline.
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
        baseline_absent = False
        if baseline_path is not None:
            destination = _validate_baseline_path(
                baseline_path, root=repo_root, write_mode=write_baseline
            )
            if _baseline_exists(destination, root=repo_root):
                baseline_rows = _load_baseline(
                    destination,
                    root=repo_root,
                    occurrence_fields=_occurrence_field_names(rule),
                    symbol_optional=rule.occurrence_symbol_optional,
                )
                if rule.occurrence_baseline:
                    if baseline_rows and _baseline_kind(baseline_rows[0]) != "occurrence":
                        raise ScanError(
                            f"baseline {destination}: occurrence rule requires "
                            "occurrence-shaped rows"
                        )
                elif baseline_rows and _baseline_kind(baseline_rows[0]) == "occurrence":
                    raise ScanError(
                        f"baseline {destination}: occurrence rows require "
                        "rule.occurrence_baseline"
                    )
            elif not write_baseline:
                if rule.occurrence_baseline and not rule.require_baseline:
                    baseline_absent = True
                else:
                    raise ScanError(
                        f"failed to read baseline {destination}: file does not exist"
                    )
        collected = _scan_findings(rule, root=repo_root, runner=runner, paths=paths)
        if baseline_path is None:
            findings = _dedupe_and_sort(collected)
            result = EXIT_FINDINGS if findings else EXIT_CLEAN
            warnings: list[str] = []
        elif baseline_absent:
            assert destination is not None
            if collected:
                raise ScanError(f"required baseline missing: {destination}")
            findings = []
            result = EXIT_CLEAN
            warnings = []
        elif (
            rule.stale_baseline_on_clean_scan
            and not write_baseline
            and not collected
            and not baseline_rows
        ):
            assert destination is not None
            raise ScanError(
                f"stale baseline present with zero live findings: {destination}"
            )
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
                occurrence_fields=_occurrence_field_names(rule),
                warn_matching_baseline=rule.warn_matching_baseline,
                symbol_optional=rule.occurrence_symbol_optional,
                stale_as_finding=rule.stale_as_finding,
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
