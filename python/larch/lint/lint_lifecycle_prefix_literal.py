"""Ratchet lifecycle and bug title-prefix literals toward shared constants.

Thin engine-backed rule: detection scans production modules under
``python/larch/**/*.py`` for lifecycle or bug title prefix string literals in
comparison, match, and composition positions. Composition covers f-string
Constant parts, ``+`` concatenation operands, and ``.format(...)`` receivers.
Existing deliberate uses are grandfathered in
``python/lifecycle-prefix-literal-baseline.json`` with a required reason per row.
"""

from __future__ import annotations

import ast
import io
import json
import re
import sys
import tokenize
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from larch.core import config
from larch.core import proc
from larch.issue import title_match
from larch.lint.engine import (
    Finding as EngineFinding,
    LintRule,
    RuleCli,
    SourceFile,
    is_exempt_python_source,
    iter_python_source_files,
    ordered_ast_child_nodes,
    qualified_symbol,
    run_rule_cli,
)

RULE_ID = "lifecycle-prefix-literal"
SUPPRESSION_TOKEN = "lint-lifecycle-prefix"
BASELINE_FILENAME = "lifecycle-prefix-literal-baseline.json"
PREFIX_METHODS = frozenset({"startswith", "endswith", "removeprefix", "lstrip"})
REGEX_FUNCTIONS = frozenset({"compile", "search", "match", "fullmatch"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__", "tests"})
ALLOWLIST_RELPATHS = frozenset({"larch/core/config.py", "larch/issue/title_match.py"})
MODULE_SYMBOL = "<module>"
PRAGMA_RE = re.compile(r"#\s*lint-lifecycle-prefix:\s*ok\s+(\S.*)$")
STANDALONE_PRAGMA_RE = re.compile(r"^\s*#\s*lint-lifecycle-prefix:\s*ok\s+(\S.*)$")
PYTHON_PREFIX = "python/"


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


def iter_source_files(larch_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under larch/, sorted."""
    return iter_python_source_files(
        larch_dir.parent,
        scope=Path("larch"),
        excluded_dirs=EXCLUDED_DIRS,
        excluded_relpaths=ALLOWLIST_RELPATHS,
    )


def is_production_source_path(rel_path: str) -> bool:
    """Pre-load filter for repo-relative lifecycle-prefix scan paths."""
    if not rel_path.startswith("python/larch/") or not rel_path.endswith(".py"):
        return False
    under = Path(rel_path[len(PYTHON_PREFIX) :])
    if EXCLUDED_DIRS.intersection(under.parts) or is_exempt_python_source(under):
        return False
    return under.as_posix() not in ALLOWLIST_RELPATHS


def _rstrip_spaces(value: str) -> str:
    return value.rstrip(" ")


def _normalized_token(value: str) -> str:
    return _rstrip_spaces(value).casefold()


def build_token_map() -> dict[str, TokenInfo]:
    tokens: dict[str, TokenInfo] = {}

    def add(value: str, *, constant: str) -> None:
        normalized: str = _normalized_token(value)
        if not normalized:
            raise BaselineError(f"empty lifecycle token for {constant}")
        token: str = _rstrip_spaces(value)
        existing: TokenInfo | None = tokens.get(normalized)
        if existing is not None and existing.constant != constant:
            raise BaselineError(
                f"duplicate lifecycle token {token!r} for {existing.constant} and {constant}"
            )
        tokens[normalized] = TokenInfo(token=token, constant=constant)

    for state, prefix in sorted(config.TRACKING_ISSUE_PREFIX_BY_STATE.items()):
        state_literal: str = json.dumps(state)
        add(prefix, constant=f"config.TRACKING_ISSUE_PREFIX_BY_STATE[{state_literal}]")
    for state, prefix in sorted(config.DEBATE_TITLE_PREFIX_BY_STATE.items()):
        debate_literal: str = json.dumps(state)
        add(prefix, constant=f"config.DEBATE_TITLE_PREFIX_BY_STATE[{debate_literal}]")
    add(title_match.BUG_PREFIX, constant="title_match.BUG_PREFIX")
    return tokens


_TOKEN_INFOS_CACHE: dict[str, TokenInfo] = {}


def _token_infos() -> dict[str, TokenInfo]:
    """Return the cached lifecycle token map, building it once on first use."""
    if not _TOKEN_INFOS_CACHE:
        _TOKEN_INFOS_CACHE.update(build_token_map())
    return _TOKEN_INFOS_CACHE


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
    token: str = _rstrip_spaces(value)
    return [LiteralMatch(token=token, constant=info.constant)]


def _composition_literal_matches(
    value: str, *, token_infos: Mapping[str, TokenInfo]
) -> list[LiteralMatch]:
    """Match composition literals by equality or space/colon token boundaries."""
    normalized: str = _normalized_token(value)
    matches: list[LiteralMatch] = []
    for token_key, info in sorted(token_infos.items()):
        if (
            normalized == token_key
            or normalized.startswith((f"{token_key} ", f"{token_key}:"))
        ):
            matches.append(LiteralMatch(token=info.token, constant=info.constant))
    return matches


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


def _fstring_compose_contexts(
    node: ast.JoinedStr, *, token_infos: Mapping[str, TokenInfo]
) -> list[tuple[str, LiteralMatch]]:
    matches: list[tuple[str, LiteralMatch]] = []
    for part in node.values:
        text: str | None = _literal_text(part)
        if text is None:
            continue
        matches.extend(
            ("fstring_compose", match)
            for match in _composition_literal_matches(text, token_infos=token_infos)
        )
    return matches


def _concat_compose_contexts(
    node: ast.BinOp, *, token_infos: Mapping[str, TokenInfo]
) -> list[tuple[str, LiteralMatch]]:
    if not isinstance(node.op, ast.Add):
        return []
    matches: list[tuple[str, LiteralMatch]] = []
    for operand in (node.left, node.right):
        text: str | None = _literal_text(operand)
        if text is None:
            continue
        matches.extend(
            ("concat_compose", match)
            for match in _composition_literal_matches(text, token_infos=token_infos)
        )
    return matches


def _format_compose_contexts(
    node: ast.Call, *, token_infos: Mapping[str, TokenInfo]
) -> list[tuple[str, LiteralMatch]]:
    func: ast.expr = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "format"):
        return []
    text: str | None = _literal_text(func.value)
    if text is None:
        return []
    return [
        ("format_compose", match)
        for match in _composition_literal_matches(text, token_infos=token_infos)
    ]


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


def _contexts_for_node(
    node: ast.AST, *, token_infos: Mapping[str, TokenInfo]
) -> list[tuple[str, LiteralMatch]]:
    contexts: list[tuple[str, LiteralMatch]] = []
    if isinstance(node, ast.Call):
        contexts.extend(_call_contexts(node, token_infos=token_infos))
        contexts.extend(_format_compose_contexts(node, token_infos=token_infos))
    if isinstance(node, ast.Compare):
        contexts.extend(_comparison_contexts(node, token_infos=token_infos))
    if isinstance(node, ast.JoinedStr):
        contexts.extend(_fstring_compose_contexts(node, token_infos=token_infos))
    if isinstance(node, ast.BinOp):
        contexts.extend(_concat_compose_contexts(node, token_infos=token_infos))
    return contexts


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    normalized_file: str,
    token_infos: Mapping[str, TokenInfo],
    findings: list[Finding],
) -> None:
    occurrence_counts: Counter[OccurrenceKey] = Counter()
    symbol: str = qualified_symbol(prefix, module_symbol=MODULE_SYMBOL)
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
        lineno_value: object = getattr(node, "lineno", 0)
        lineno: int = lineno_value if isinstance(lineno_value, int) else 0
        for context, match in _contexts_for_node(node, token_infos=token_infos):
            recorder.record(context=context, match=match, lineno=lineno)
        for child in ordered_ast_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(
    path: Path, *, larch_dir: Path, token_infos: Mapping[str, TokenInfo]
) -> list[Finding]:
    """Return lifecycle-prefix literal findings for one source file."""
    normalized_file: str = path.relative_to(larch_dir.parent).as_posix()
    try:
        source: str = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BaselineError(f"{normalized_file}: cannot read source: {exc}") from exc
    try:
        tree: ast.Module = ast.parse(source)
    except SyntaxError:
        return []
    findings: list[Finding] = []
    _collect_scope(
        tree.body,
        prefix=(),
        normalized_file=normalized_file,
        token_infos=token_infos,
        findings=findings,
    )
    return findings


def _comment_tokens_by_line(source: str) -> dict[int, tuple[tuple[int, str], ...]]:
    comments: dict[int, list[tuple[int, str]]] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.setdefault(token.start[0], []).append((token.start[1], token.string))
    except tokenize.TokenError:
        return {}
    return {line: tuple(tokens) for line, tokens in comments.items()}


def _has_inline_pragma(
    finding: Finding,
    *,
    lines: tuple[str, ...],
    comments_by_line: Mapping[int, tuple[tuple[int, str], ...]],
) -> bool:
    for _comment_column, comment in comments_by_line.get(finding.lineno, ()):
        if PRAGMA_RE.search(comment):
            return True
    previous_line_number: int = finding.lineno - 1
    if previous_line_number < 1 or previous_line_number > len(lines):
        return False
    previous_line: str = lines[previous_line_number - 1]
    for comment_column, comment in comments_by_line.get(previous_line_number, ()):
        if STANDALONE_PRAGMA_RE.match(comment) and previous_line[:comment_column].strip() == "":
            return True
    return False


def findings_from_source(source: str, *, normalized_file: str) -> list[Finding]:
    """Return lifecycle findings for one source buffer, dropping pragma-suppressed rows."""
    token_infos = _token_infos()
    try:
        tree: ast.Module = ast.parse(source)
    except SyntaxError:
        return []
    findings: list[Finding] = []
    _collect_scope(
        tree.body,
        prefix=(),
        normalized_file=normalized_file,
        token_infos=token_infos,
        findings=findings,
    )
    lines: tuple[str, ...] = tuple(source.splitlines())
    comments_by_line = _comment_tokens_by_line(source)
    return [
        finding
        for finding in findings
        if not _has_inline_pragma(finding, lines=lines, comments_by_line=comments_by_line)
    ]


def to_engine_finding(finding: Finding) -> EngineFinding:
    """Adapt one lifecycle finding to the shared engine finding shape."""
    return EngineFinding(
        path=f"{PYTHON_PREFIX}{finding.file}",
        line=finding.lineno,
        rule_id=RULE_ID,
        message=f"matched {finding.token} in {finding.context}; use {finding.constant} instead",
        qualified_symbol=finding.qualified_symbol,
        occurrence=finding.occurrence,
        occurrence_values=(
            ("token", finding.token),
            ("constant", finding.constant),
            ("context", finding.context),
        ),
    )


def detect(source: SourceFile) -> list[EngineFinding]:
    """Engine detector entry: scan one source for lifecycle-prefix literals."""
    if not source.is_python or not is_production_source_path(source.path):
        return []
    normalized_file = source.path.removeprefix(PYTHON_PREFIX)
    findings = findings_from_source(source.text, normalized_file=normalized_file)
    return [to_engine_finding(finding) for finding in findings]


RULE = LintRule(
    rule_id=RULE_ID,
    description=(
        "Ratchet lifecycle and bug title-prefix literals toward shared constants"
    ),
    detect=detect,
    syntax_policy="skip",
    suppression_token=SUPPRESSION_TOKEN,
    allow_inline_suppression=False,
    pathspecs=("python/larch",),
    source_filter=is_production_source_path,
    occurrence_baseline=True,
    occurrence_fields=("token", "constant", "context"),
    require_baseline=True,
    warn_matching_baseline=True,
)


CLI = RuleCli(
    prog="cli.py lint lifecycle-prefix-literal",
    description=__doc__,
    baseline_filename=BASELINE_FILENAME,
    error_label="lint-lifecycle-prefix-literal",
    scoped_paths=None,
    strict_stale=False,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint lifecycle-prefix-literal``."""
    return run_rule_cli(
        argv if argv is not None else sys.argv[1:],
        cli=CLI,
        runner=proc.ProcRunner(),
        rule=RULE,
    )


if __name__ == "__main__":
    raise SystemExit(main())
