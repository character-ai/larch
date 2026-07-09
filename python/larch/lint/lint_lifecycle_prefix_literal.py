"""Ratchet lifecycle and bug title-prefix literals toward shared constants.

Scans production modules under python/larch/**/*.py for lifecycle or bug title
prefix string literals in comparison or match positions. Existing deliberate
uses are grandfathered in python/lifecycle-prefix-literal-baseline.json with a
required reason per row.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from larch.core import config
from larch.issue import title_match

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "lifecycle-prefix-literal-baseline.json"
BASELINE_KEYS = frozenset(
    {"file", "qualified_symbol", "token", "constant", "context", "occurrence", "reason"}
)
CONTEXT_KINDS = frozenset(
    {
        "startswith",
        "endswith",
        "removeprefix",
        "lstrip",
        "compare_eq",
        "compare_ne",
        "membership_in",
        "membership_not_in",
        "regex_pattern",
    }
)
PREFIX_METHODS = frozenset({"startswith", "endswith", "removeprefix", "lstrip"})
REGEX_FUNCTIONS = frozenset({"compile", "search", "match", "fullmatch"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__", "tests"})
ALLOWLIST_RELPATHS = frozenset({"larch/core/config.py", "larch/issue/title_match.py"})
MODULE_SYMBOL = "<module>"
PRAGMA_RE = re.compile(r"#\s*lint-lifecycle-prefix:\s*ok\s+(\S.*)$")
STANDALONE_PRAGMA_RE = re.compile(r"^\s*#\s*lint-lifecycle-prefix:\s*ok\s+(\S.*)$")


class Record(TypedDict):
    file: str
    qualified_symbol: str
    token: str
    constant: str
    context: str
    occurrence: int
    reason: str


class BaselineError(ValueError):
    """Raised when the baseline or token source cannot be trusted."""


@dataclass(frozen=True)
class TokenInfo:
    token: str
    constant: str


@dataclass(frozen=True)
class LiteralMatch:
    token: str
    constant: str


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    token: str
    constant: str
    context: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, str, str, int]:
        return (
            self.file,
            self.qualified_symbol,
            self.token,
            self.constant,
            self.context,
            self.occurrence,
        )


OccurrenceKey = tuple[str, str, str, str, str]


def normalize_file_path(raw: str) -> str:
    """Return a normalized POSIX path relative to python/."""
    normalized: str = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized == "python":
        return ""
    return normalized.removeprefix("python/")


def _has_bad_path_parts(parts: list[str]) -> bool:
    return "" in parts or "." in parts or ".." in parts


def _validate_normalized_file(value: object, *, source: Path, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: record {index} has invalid file")
    normalized: str = normalize_file_path(value)
    parts: list[str] = normalized.split("/")
    if (
        normalized != value
        or normalized.startswith("/")
        or not normalized.startswith("larch/")
        or not normalized.endswith(".py")
        or _has_bad_path_parts(parts)
    ):
        raise BaselineError(f"{source}: record {index} has invalid file")
    return normalized


def is_exempt_path(path: Path) -> bool:
    """Return whether a source file is outside production lint scope."""
    name: str = path.name
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def iter_source_files(larch_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under larch/, sorted."""
    result: list[Path] = []
    for path in sorted(larch_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink() or is_exempt_path(path):
            continue
        relative: Path = path.relative_to(larch_dir.parent)
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        normalized: str = relative.as_posix()
        if normalized in ALLOWLIST_RELPATHS:
            continue
        result.append(path)
    return result


def _normalized_token(value: str) -> str:
    return value.rstrip().casefold()


def build_token_map() -> dict[str, TokenInfo]:
    tokens: dict[str, TokenInfo] = {}

    def add(value: str, *, constant: str) -> None:
        normalized: str = _normalized_token(value)
        if not normalized:
            raise BaselineError(f"empty lifecycle token for {constant}")
        token: str = value.rstrip()
        existing: TokenInfo | None = tokens.get(normalized)
        if existing is not None and existing.constant != constant:
            raise BaselineError(
                f"duplicate lifecycle token {token!r} for {existing.constant} and {constant}"
            )
        tokens[normalized] = TokenInfo(token=token, constant=constant)

    for state, prefix in sorted(config.TRACKING_ISSUE_PREFIX_BY_STATE.items()):
        state_literal: str = json.dumps(state)
        add(prefix, constant=f"config.TRACKING_ISSUE_PREFIX_BY_STATE[{state_literal}]")
    add(title_match.BUG_PREFIX, constant="title_match.BUG_PREFIX")
    return tokens


def _qualified(prefix: tuple[str, ...]) -> str:
    return ".".join(prefix) if prefix else MODULE_SYMBOL


def _child_position(node: ast.AST, *, index: int) -> tuple[int, int, int]:
    return (
        getattr(node, "lineno", 10**9),
        getattr(node, "col_offset", 10**9),
        index,
    )


def _ordered_child_nodes(node: ast.AST) -> list[ast.AST]:
    children: list[ast.AST] = list(ast.iter_child_nodes(node))
    indexed: list[tuple[int, ast.AST]] = list(enumerate(children))
    indexed.sort(key=lambda item: _child_position(item[1], index=item[0]))
    return [child for _, child in indexed]


def _literal_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_values(node: ast.AST) -> list[str]:
    value: str | None = _literal_text(node)
    if value is not None:
        return [value]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values: list[str] = []
        for element in node.elts:
            element_value: str | None = _literal_text(element)
            if element_value is not None:
                values.append(element_value)
        return values
    return []


def _regex_surface(value: str) -> str:
    return value.replace(r"\[", "[").replace(r"\]", "]")


def _literal_matches(value: str, *, token_infos: Mapping[str, TokenInfo]) -> list[LiteralMatch]:
    normalized: str = _normalized_token(value)
    info: TokenInfo | None = token_infos.get(normalized)
    if info is None:
        return []
    token: str = value.rstrip()
    return [LiteralMatch(token=token, constant=info.constant)]


def _regex_literal_matches(value: str, *, token_infos: Mapping[str, TokenInfo]) -> list[LiteralMatch]:
    raw: str = value.casefold()
    surface: str = _regex_surface(value).casefold()
    matches: list[LiteralMatch] = []
    for token, info in sorted(token_infos.items()):
        if token in raw or token in surface:
            matches.append(LiteralMatch(token=info.token, constant=info.constant))
    return matches


def _call_contexts(node: ast.Call, *, token_infos: Mapping[str, TokenInfo]) -> list[tuple[str, LiteralMatch]]:
    func: ast.expr = node.func
    if isinstance(func, ast.Attribute) and func.attr in PREFIX_METHODS and node.args:
        matches: list[tuple[str, LiteralMatch]] = []
        for value in _literal_values(node.args[0]):
            matches.extend(
                (func.attr, match)
                for match in _literal_matches(value, token_infos=token_infos)
            )
        return matches
    if (
        isinstance(func, ast.Attribute)
        and func.attr in REGEX_FUNCTIONS
        and isinstance(func.value, ast.Name)
        and func.value.id == "re"
        and node.args
    ):
        pattern: str | None = _literal_text(node.args[0])
        if pattern is None:
            return []
        return [
            ("regex_pattern", match)
            for match in _regex_literal_matches(pattern, token_infos=token_infos)
        ]
    return []


def _comparison_context(op: ast.cmpop) -> str | None:
    if isinstance(op, ast.Eq):
        return "compare_eq"
    if isinstance(op, ast.NotEq):
        return "compare_ne"
    if isinstance(op, ast.In):
        return "membership_in"
    if isinstance(op, ast.NotIn):
        return "membership_not_in"
    return None


def _comparison_contexts(
    node: ast.Compare, *, token_infos: Mapping[str, TokenInfo]
) -> list[tuple[str, LiteralMatch]]:
    matches: list[tuple[str, LiteralMatch]] = []
    left: ast.expr = node.left
    for op, comparator in zip(node.ops, node.comparators, strict=True):
        context: str | None = _comparison_context(op)
        if context is not None:
            for operand in (left, comparator):
                for value in _literal_values(operand):
                    matches.extend(
                        (context, match)
                        for match in _literal_matches(value, token_infos=token_infos)
                    )
        left = comparator
    return matches


@dataclass(frozen=True)
class ScopeRecorder:
    findings: list[Finding]
    occurrence_counts: Counter[OccurrenceKey]
    normalized_file: str
    symbol: str

    def record(self, *, context: str, match: LiteralMatch, lineno: int) -> None:
        occurrence_key: OccurrenceKey = (
            self.normalized_file,
            self.symbol,
            match.token,
            match.constant,
            context,
        )
        self.occurrence_counts[occurrence_key] += 1
        occurrence: int = self.occurrence_counts[occurrence_key]
        self.findings.append(
            Finding(
                file=self.normalized_file,
                qualified_symbol=self.symbol,
                token=match.token,
                constant=match.constant,
                context=context,
                occurrence=occurrence,
                lineno=lineno,
            )
        )


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    normalized_file: str,
    token_infos: Mapping[str, TokenInfo],
    findings: list[Finding],
) -> None:
    occurrence_counts: Counter[OccurrenceKey] = Counter()
    symbol: str = _qualified(prefix)
    recorder = ScopeRecorder(
        findings=findings,
        occurrence_counts=occurrence_counts,
        normalized_file=normalized_file,
        symbol=symbol,
    )

    def walk(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                normalized_file=normalized_file,
                token_infos=token_infos,
                findings=findings,
            )
            return
        if isinstance(node, ast.ClassDef):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                normalized_file=normalized_file,
                token_infos=token_infos,
                findings=findings,
            )
            return
        contexts: list[tuple[str, LiteralMatch]] = []
        if isinstance(node, ast.Call):
            contexts.extend(_call_contexts(node, token_infos=token_infos))
        if isinstance(node, ast.Compare):
            contexts.extend(_comparison_contexts(node, token_infos=token_infos))
        lineno_value: object = getattr(node, "lineno", 0)
        lineno: int = lineno_value if isinstance(lineno_value, int) else 0
        for context, match in contexts:
            recorder.record(context=context, match=match, lineno=lineno)
        for child in _ordered_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(
    path: Path, *, larch_dir: Path, token_infos: Mapping[str, TokenInfo]
) -> list[Finding]:
    """Return lifecycle-prefix literal findings for one source file."""
    try:
        source: str = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree: ast.Module = ast.parse(source)
    except SyntaxError:
        return []
    findings: list[Finding] = []
    _collect_scope(
        tree.body,
        prefix=(),
        normalized_file=path.relative_to(larch_dir.parent).as_posix(),
        token_infos=token_infos,
        findings=findings,
    )
    return findings


def _record_key(record: Record) -> tuple[str, str, str, str, str, int]:
    return (
        record["file"],
        record["qualified_symbol"],
        record["token"],
        record["constant"],
        record["context"],
        record["occurrence"],
    )


def _finding_sort_key(finding: Finding) -> tuple[str, str, str, str, str, int]:
    return finding.key()


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name: str = _validate_normalized_file(record["file"], source=source, index=index)
    qualified_symbol: object = record["qualified_symbol"]
    token: object = record["token"]
    constant: object = record["constant"]
    context: object = record["context"]
    occurrence: object = record["occurrence"]
    reason: object = record["reason"]
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(token, str) or not token:
        raise BaselineError(f"{source}: record {index} has invalid token")
    if not isinstance(constant, str) or not constant:
        raise BaselineError(f"{source}: record {index} has invalid constant")
    if not isinstance(context, str) or context not in CONTEXT_KINDS:
        raise BaselineError(f"{source}: record {index} has invalid context")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "qualified_symbol": qualified_symbol,
        "token": token,
        "constant": constant,
        "context": context,
        "occurrence": occurrence,
        "reason": reason,
    }


def _first_duplicate(
    keys: Iterable[tuple[str, str, str, str, str, int]],
) -> tuple[str, str, str, str, str, int] | None:
    seen: set[tuple[str, str, str, str, str, int]] = set()
    for key in keys:
        if key in seen:
            return key
        seen.add(key)
    return None


def load_baseline(path: Path) -> list[Record]:
    """Load and validate the committed baseline."""
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a top-level JSON array")
    records: list[Record] = [
        _validate_record(item, index=index, source=path)
        for index, item in enumerate(cast("list[object]", data))
    ]
    duplicate: tuple[str, str, str, str, str, int] | None = _first_duplicate(
        _record_key(record) for record in records
    )
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate baseline identity {format_key(duplicate)}")
    return records


def _source_lines(path: Path) -> tuple[str, ...]:
    try:
        return tuple(path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return ()


def _has_inline_pragma(
    finding: Finding, *, source_lines_by_file: Mapping[str, tuple[str, ...]]
) -> bool:
    lines: tuple[str, ...] = source_lines_by_file.get(finding.file, ())
    index: int = finding.lineno - 1
    if 0 <= index < len(lines) and PRAGMA_RE.search(lines[index]):
        return True
    previous: int = index - 1
    return 0 <= previous < len(lines) and STANDALONE_PRAGMA_RE.match(lines[previous]) is not None


def _collect_all(
    larch_dir: Path, *, token_infos: Mapping[str, TokenInfo]
) -> tuple[list[Finding], dict[str, tuple[str, ...]]]:
    findings: list[Finding] = []
    source_lines_by_file: dict[str, tuple[str, ...]] = {}
    for path in iter_source_files(larch_dir):
        normalized: str = path.relative_to(larch_dir.parent).as_posix()
        source_lines_by_file[normalized] = _source_lines(path)
        findings.extend(scan_file(path, larch_dir=larch_dir, token_infos=token_infos))
    return findings, source_lines_by_file


def _check_duplicate_live(findings: list[Finding]) -> str | None:
    duplicate: tuple[str, str, str, str, str, int] | None = _first_duplicate(
        finding.key() for finding in findings
    )
    if duplicate is None:
        return None
    return f"duplicate live identity {format_key(duplicate)}"


def _filter_suppressed(
    findings: list[Finding], *, source_lines_by_file: Mapping[str, tuple[str, ...]]
) -> list[Finding]:
    return [
        finding
        for finding in findings
        if not _has_inline_pragma(finding, source_lines_by_file=source_lines_by_file)
    ]


def format_key(key: tuple[str, str, str, str, str, int]) -> str:
    file_name, qualified_symbol, token, constant, context, occurrence = key
    return f"{file_name}:{qualified_symbol} {token}/{constant} {context}#{occurrence}"


def serialize_baseline(records: list[Record]) -> str:
    """Return canonical sorted JSON for the baseline."""
    ordered: list[Record] = sorted(records, key=_record_key)
    return json.dumps(ordered, indent=2) + "\n"


def _records_for_write(
    findings: list[Finding],
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> list[Record]:
    preserved: dict[tuple[str, str, str, str, str, int], str] = {}
    if baseline_path.is_file():
        preserved = {_record_key(record): record["reason"] for record in load_baseline(baseline_path)}
    reason_default: str | None = initial_reason.strip() if initial_reason is not None else None
    records: list[Record] = []
    missing: list[str] = []
    for finding in sorted(findings, key=_finding_sort_key):
        reason: str | None = preserved.get(finding.key()) or reason_default
        if reason is None:
            missing.append(format_key(finding.key()))
            continue
        records.append(
            {
                "file": finding.file,
                "qualified_symbol": finding.qualified_symbol,
                "token": finding.token,
                "constant": finding.constant,
                "context": finding.context,
                "occurrence": finding.occurrence,
                "reason": reason,
            }
        )
    if missing:
        joined: str = "\n  ".join(missing)
        raise BaselineError("missing baseline reasons for live lifecycle prefix findings:\n  " + joined)
    return records


def _run_write(
    larch_dir: Path,
    *,
    baseline_path: Path,
    token_infos: Mapping[str, TokenInfo],
    initial_reason: str | None,
) -> int:
    try:
        all_findings, source_lines_by_file = _collect_all(larch_dir, token_infos=token_infos)
        duplicate: str | None = _check_duplicate_live(all_findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
        findings: list[Finding] = _filter_suppressed(
            all_findings,
            source_lines_by_file=source_lines_by_file,
        )
        records: list[Record] = _records_for_write(
            findings,
            baseline_path=baseline_path,
            initial_reason=initial_reason,
        )
    except BaselineError as exc:
        print(f"lint-lifecycle-prefix-literal: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(
        f"lint-lifecycle-prefix-literal: wrote {len(records)} records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check(
    larch_dir: Path,
    *,
    baseline_path: Path,
    token_infos: Mapping[str, TokenInfo],
) -> int:
    try:
        baseline_records: list[Record] = load_baseline(baseline_path)
        all_findings, source_lines_by_file = _collect_all(larch_dir, token_infos=token_infos)
        duplicate: str | None = _check_duplicate_live(all_findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
    except BaselineError as exc:
        print(f"lint-lifecycle-prefix-literal: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys: frozenset[tuple[str, str, str, str, str, int]] = frozenset(
        _record_key(record) for record in baseline_records
    )
    live_findings: list[Finding] = _filter_suppressed(
        all_findings,
        source_lines_by_file=source_lines_by_file,
    )
    new_findings: list[Finding] = []
    warned: list[Finding] = []
    for finding in sorted(live_findings, key=_finding_sort_key):
        if finding.key() in baseline_keys:
            warned.append(finding)
        else:
            new_findings.append(finding)
    for finding in warned:
        print(
            "warning: "
            f"{finding.file}:{finding.qualified_symbol} line {finding.lineno} "
            f"matched {finding.token} in {finding.context}; use {finding.constant} instead "
            "(baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.file}:{finding.qualified_symbol} line {finding.lineno} "
            f"matched {finding.token} in {finding.context}; use {finding.constant} instead",
            file=sys.stderr,
        )
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint lifecycle-prefix-literal", description=__doc__
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=f"Regenerate {BASELINE_FILENAME} from live AST scan.",
    )
    _ = parser.add_argument(
        "--initial-reason",
        help="Reason used for live findings without preserved baseline reasons.",
    )
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
        print(f"lint-lifecycle-prefix-literal: larch directory not found: {larch_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_path: Path = root / "python" / BASELINE_FILENAME
    initial_reason: str | None = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-lifecycle-prefix-literal: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        token_infos: dict[str, TokenInfo] = build_token_map()
    except BaselineError as exc:
        print(f"lint-lifecycle-prefix-literal: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(
            larch_dir,
            baseline_path=baseline_path,
            token_infos=token_infos,
            initial_reason=initial_reason,
        )
    return _run_check(larch_dir, baseline_path=baseline_path, token_infos=token_infos)


if __name__ == "__main__":
    raise SystemExit(main())
