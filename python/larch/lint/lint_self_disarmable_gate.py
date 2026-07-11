"""Flag hard gates that disarm themselves via author-controlled plan metadata.

Mechanically backs invariant I-Gate-1 (#6542, #6524): a size or publish trigger
must not be suppressed, replaced, or short-circuited solely by model-authored
optional metadata such as ``diff_added`` or ``mechanical_churn``. Metadata may
OR-combine into a trigger or soften presentation after the hard decision.

Scans ``python/larch/design/plan_quality.py`` and sibling design modules that
emit size or publish triggers. Resolves ``OptionalMetadata`` through the
plan-quality import/re-export chain rather than only local dataclass bodies.
"""
# ruff: noqa: C901, PLR0911, PLR0912, PLR0913, PLR2004, SIM102 - AST gate scan complexity is inherent

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

TOOL_FAILURE_EXIT = 2
SUPPRESSION = "lint-self-disarmable-gate"
PRAGMA_RE = re.compile(rf"#\s*{re.escape(SUPPRESSION)}:\s*ok\s+(\S.*)$")
EMPTY_PRAGMA_RE = re.compile(rf"#\s*{re.escape(SUPPRESSION)}:\s*ok\s*$")
OWNER_REASON_RE = re.compile(r"\b(?:gate\s+owner|owner)\s*[:=]\s*\S+", re.IGNORECASE)
REQUIRED_META_FIELDS = frozenset({"diff_added", "mechanical_churn"})
OPTIONAL_METADATA_NAME = "OptionalMetadata"
DESIGN_REL = Path("larch") / "design"
PLAN_QUALITY_REL = DESIGN_REL / "plan_quality.py"


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    lineno: int
    message: str


class ScanError(RuntimeError):
    """Raised for unreadable sources or unresolved metadata definitions."""


@dataclass
class MetadataResolution:
    fields: frozenset[str]
    defining_file: str


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
    lineno: int, *, comments_by_line: Mapping[int, tuple[str, ...]]
) -> str | None:
    for comment in comments_by_line.get(lineno, ()):
        match = PRAGMA_RE.search(comment)
        if match is not None:
            return match.group(1).strip()
        if EMPTY_PRAGMA_RE.search(comment) is not None:
            return ""
    return None


def _read_parse(path: Path, *, label: str) -> tuple[str, ast.Module]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ScanError(f"{label}: cannot read source: {exc}") from exc
    try:
        return source, ast.parse(source)
    except SyntaxError as exc:
        raise ScanError(f"{label}: cannot parse source: {exc}") from exc


def _dataclass_fields(node: ast.ClassDef) -> frozenset[str]:
    names: set[str] = set()
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.add(item.target.id)
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return frozenset(names)


def _find_class(tree: ast.Module, name: str) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _import_optional_metadata_module(tree: ast.Module) -> str | None:
    """Return a relative module hint for OptionalMetadata imports, if any."""
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == OPTIONAL_METADATA_NAME:
                    return node.module
        if isinstance(node, ast.Assign):
            # ``OptionalMetadata = something.OptionalMetadata`` re-exports.
            if (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == OPTIONAL_METADATA_NAME
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == OPTIONAL_METADATA_NAME
            ):
                return None
    return None


def resolve_optional_metadata(design_dir: Path) -> MetadataResolution:
    """Resolve OptionalMetadata fields via the plan-quality import chain."""
    candidates = [
        design_dir / "_plan_quality_commands.py",
        design_dir / "plan_quality.py",
    ]
    # Follow re-exports from plan_quality.py first.
    plan_quality = design_dir / "plan_quality.py"
    if plan_quality.is_file():
        _source, tree = _read_parse(plan_quality, label=str(PLAN_QUALITY_REL))
        local = _find_class(tree, OPTIONAL_METADATA_NAME)
        if local is not None:
            fields = _dataclass_fields(local)
            if not REQUIRED_META_FIELDS.issubset(fields):
                missing = ", ".join(sorted(REQUIRED_META_FIELDS - fields))
                raise ScanError(
                    f"OptionalMetadata in {PLAN_QUALITY_REL} missing required fields: {missing}"
                )
            return MetadataResolution(fields=fields, defining_file=str(PLAN_QUALITY_REL))
        imported_module = _import_optional_metadata_module(tree)
        if imported_module is not None:
            # ``from larch.design._plan_quality_commands import OptionalMetadata``
            # or ``from ._plan_quality_commands import OptionalMetadata``.
            module_tail = imported_module.rsplit(".", maxsplit=1)[-1]
            candidate = design_dir / f"{module_tail}.py"
            if candidate.is_file():
                candidates.insert(0, candidate)
        # Bare name import from relative package.
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == OPTIONAL_METADATA_NAME and node.module:
                        module_tail = node.module.rsplit(".", maxsplit=1)[-1]
                        candidate = design_dir / f"{module_tail}.py"
                        if candidate.is_file() and candidate not in candidates:
                            candidates.insert(0, candidate)
    for path in candidates:
        if not path.is_file():
            continue
        _source, tree = _read_parse(path, label=path.name)
        local = _find_class(tree, OPTIONAL_METADATA_NAME)
        if local is None:
            continue
        fields = _dataclass_fields(local)
        if not REQUIRED_META_FIELDS.issubset(fields):
            missing = ", ".join(sorted(REQUIRED_META_FIELDS - fields))
            raise ScanError(
                f"OptionalMetadata in {path.relative_to(design_dir.parent).as_posix()} "
                f"missing required fields: {missing}"
            )
        return MetadataResolution(
            fields=fields,
            defining_file=path.relative_to(design_dir.parent).as_posix(),
        )
    raise ScanError(
        "cannot resolve OptionalMetadata definition covering "
        f"{', '.join(sorted(REQUIRED_META_FIELDS))}"
    )


def iter_gate_modules(design_dir: Path) -> list[Path]:
    """Return design modules that may emit size or publish triggers."""
    result: list[Path] = []
    for path in sorted(design_dir.glob("*.py")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name.startswith("test_"):
            continue
        result.append(path)
    return result


def _attr_chain(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return tuple(reversed(parts))
    return None


def _is_meta_field_access(node: ast.AST, *, meta_fields: frozenset[str]) -> str | None:
    chain = _attr_chain(node)
    if chain is None or len(chain) < 2:
        return None
    field_name = chain[-1]
    if field_name in meta_fields:
        return field_name
    return None


def _contains_meta_field(node: ast.AST, *, meta_fields: frozenset[str]) -> str | None:
    for child in ast.walk(node):
        field_name = _is_meta_field_access(child, meta_fields=meta_fields)
        if field_name is not None:
            return field_name
    return None


def _is_false_constant(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _is_negated(node: ast.AST) -> bool:
    return isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)


def _is_validation_condition(test: ast.AST, *, meta_fields: frozenset[str]) -> bool:
    """Return True for metadata shape/presence checks that are not disarming."""
    if isinstance(test, ast.Compare) and _contains_meta_field(test, meta_fields=meta_fields):
        return any(isinstance(op, (ast.NotIn, ast.In, ast.Is, ast.IsNot)) for op in test.ops)
    return False


def _is_suppression_condition(test: ast.AST, *, meta_fields: frozenset[str]) -> bool:
    """Return True when the condition looks like a metadata-based disarm guard."""
    if _contains_meta_field(test, meta_fields=meta_fields) is None:
        return False
    if _is_validation_condition(test, meta_fields=meta_fields):
        return False
    if _is_negated(test):
        return True
    if _is_meta_field_access(test, meta_fields=meta_fields) is not None:
        return True
    if isinstance(test, ast.Compare):
        # ``meta.X == "true"`` / ``meta.X != "false"`` style suppressions.
        return any(isinstance(op, (ast.Eq, ast.NotEq)) for op in test.ops)
    if isinstance(test, ast.BoolOp) and isinstance(test.op, (ast.And, ast.Or)):
        return any(_is_suppression_condition(value, meta_fields=meta_fields) for value in test.values)
    return False


def _looks_like_hard_trigger_name(name: str) -> bool:
    lowered = name.lower()
    return any(
        token in lowered
        for token in (
            "size_diff",
            "size_trigger",
            "hard_trigger",
            "publish_trigger",
            "reasons",
            "size_diff_raw",
            "size_diff_lines",
            "size_diff_added",
        )
    )


def _contains_inline_hard_trigger(node: ast.AST) -> bool:
    """Return whether an expression performs a plan-size hard-gate calculation."""
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and _looks_like_hard_trigger_name(child.id):
            return True
        if isinstance(child, ast.Attribute) and _looks_like_hard_trigger_name(child.attr):
            return True
        if isinstance(child, ast.Compare):
            names = [name.id for name in ast.walk(child) if isinstance(name, ast.Name)]
            if any(token in name.lower() for name in names for token in ("diff", "line", "size", "plan")):
                return True
    return False


def _statement_returns(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Return):
        return True
    if isinstance(stmt, ast.If):
        return bool(stmt.orelse) and _body_returns(stmt.body) and _body_returns(stmt.orelse)
    return False


def _body_returns(body: list[ast.stmt]) -> bool:
    return any(_statement_returns(stmt) for stmt in body)


def _scan_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    normalized_file: str,
    meta_fields: frozenset[str],
    comments_by_line: Mapping[int, tuple[str, ...]],
    findings: list[Finding],
) -> None:
    symbol = node.name
    # Track hard triggers in source order; later assignments cannot justify an
    # earlier metadata-controlled return.
    hard_names: set[str] = set()
    for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
        if _looks_like_hard_trigger_name(argument.arg):
            hard_names.add(argument.arg)
    for stmt in node.body:
        _scan_statement(
            stmt,
            symbol=symbol,
            normalized_file=normalized_file,
            meta_fields=meta_fields,
            hard_names=hard_names,
            comments_by_line=comments_by_line,
            findings=findings,
        )
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            name = stmt.targets[0].id
            if _looks_like_hard_trigger_name(name) or _contains_inline_hard_trigger(stmt.value):
                hard_names.add(name)


def _emit(
    *,
    findings: list[Finding],
    normalized_file: str,
    symbol: str,
    lineno: int,
    message: str,
    comments_by_line: Mapping[int, tuple[str, ...]],
) -> None:
    reason = _suppression_reason(lineno, comments_by_line=comments_by_line)
    if reason is not None:
        if reason == "":
            raise ScanError(
                f"{normalized_file}:{lineno}: empty {SUPPRESSION} suppression reason"
            )
        if OWNER_REASON_RE.search(reason) is None:
            raise ScanError(
                f"{normalized_file}:{lineno}: {SUPPRESSION} suppression reason must name gate owner"
            )
        return
    findings.append(
        Finding(
            file=normalized_file,
            qualified_symbol=symbol,
            lineno=lineno,
            message=message,
        )
    )


def _scan_statement(
    stmt: ast.stmt,
    *,
    symbol: str,
    normalized_file: str,
    meta_fields: frozenset[str],
    hard_names: set[str],
    comments_by_line: Mapping[int, tuple[str, ...]],
    findings: list[Finding],
) -> None:
    if isinstance(stmt, ast.If):
        meta_field = _contains_meta_field(stmt.test, meta_fields=meta_fields)
        if meta_field is not None and _is_suppression_condition(stmt.test, meta_fields=meta_fields):
            body_clears_hard = False
            body_returns = False
            for body_stmt in stmt.body:
                if isinstance(body_stmt, ast.Return):
                    body_returns = True
                if isinstance(body_stmt, ast.Assign):
                    for target in body_stmt.targets:
                        if isinstance(target, ast.Name) and target.id in hard_names:
                            if _is_false_constant(body_stmt.value):
                                body_clears_hard = True
                if isinstance(body_stmt, ast.AugAssign) and isinstance(body_stmt.target, ast.Name):
                    if body_stmt.target.id in hard_names:
                        body_clears_hard = True
            presentation_only = all(
                isinstance(body_stmt, ast.Assign)
                and len(body_stmt.targets) == 1
                and isinstance(body_stmt.targets[0], ast.Name)
                and body_stmt.targets[0].id
                in {"soft", "softened", "presentation", "advisory"}
                for body_stmt in stmt.body
            )
            hard_context = bool(hard_names) or _contains_inline_hard_trigger(stmt.test)
            if not presentation_only and (body_clears_hard or (body_returns and hard_context)):
                lineno = getattr(stmt, "lineno", 0)
                _emit(
                    findings=findings,
                    normalized_file=normalized_file,
                    symbol=symbol,
                    lineno=lineno if isinstance(lineno, int) else 0,
                    message=(
                        f"author-controlled metadata field {meta_field!r} "
                        "disarms or short-circuits a hard gate"
                    ),
                    comments_by_line=comments_by_line,
                )
        for child in stmt.body + stmt.orelse:
            _scan_statement(
                child,
                symbol=symbol,
                normalized_file=normalized_file,
                meta_fields=meta_fields,
                hard_names=hard_names,
                comments_by_line=comments_by_line,
                findings=findings,
            )
        return

    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        target = stmt.targets[0].id
        # ``hard = False if meta.X else hard`` / ternary replacement.
        if isinstance(stmt.value, ast.IfExp):
            meta_field = _contains_meta_field(stmt.value.test, meta_fields=meta_fields)
            if meta_field is not None and (
                _is_false_constant(stmt.value.body) or _is_false_constant(stmt.value.orelse)
            ):
                if target in hard_names or _looks_like_hard_trigger_name(target):
                    lineno = getattr(stmt, "lineno", 0)
                    _emit(
                        findings=findings,
                        normalized_file=normalized_file,
                        symbol=symbol,
                        lineno=lineno if isinstance(lineno, int) else 0,
                        message=(
                            f"author-controlled metadata field {meta_field!r} "
                            "replaces a hard trigger via conditional expression"
                        ),
                        comments_by_line=comments_by_line,
                    )
        # ``hard = hard and not meta.X`` / precedence disarm.
        if isinstance(stmt.value, ast.BoolOp) and isinstance(stmt.value.op, ast.And):
            meta_field = _contains_meta_field(stmt.value, meta_fields=meta_fields)
            if meta_field is not None and (target in hard_names or _looks_like_hard_trigger_name(target)):
                # AND with negated metadata is a disarm; AND with positive
                # independent signals is fine. Detect ``not meta.field``.
                for value in stmt.value.values:
                    if _is_negated(value) and _contains_meta_field(value, meta_fields=meta_fields):
                        lineno = getattr(stmt, "lineno", 0)
                        _emit(
                            findings=findings,
                            normalized_file=normalized_file,
                            symbol=symbol,
                            lineno=lineno if isinstance(lineno, int) else 0,
                            message=(
                                f"author-controlled metadata field {meta_field!r} "
                                "AND-negates a hard trigger"
                            ),
                            comments_by_line=comments_by_line,
                        )
                        break
        return

    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        _scan_function(
            stmt,
            normalized_file=normalized_file,
            meta_fields=meta_fields,
            comments_by_line=comments_by_line,
            findings=findings,
        )


def scan_file(
    path: Path,
    *,
    larch_dir: Path,
    meta_fields: frozenset[str],
) -> list[Finding]:
    """Return self-disarm findings for one design module."""
    normalized_file = path.relative_to(larch_dir.parent).as_posix()
    source, tree = _read_parse(path, label=normalized_file)
    comments_by_line = _comment_tokens_by_line(source)
    findings: list[Finding] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _scan_function(
                node,
                normalized_file=normalized_file,
                meta_fields=meta_fields,
                comments_by_line=comments_by_line,
                findings=findings,
            )
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _scan_function(
                        item,
                        normalized_file=normalized_file,
                        meta_fields=meta_fields,
                        comments_by_line=comments_by_line,
                        findings=findings,
                    )
    return findings


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint self-disarmable-gate", description=__doc__)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = Path(str(parsed.root)).resolve()
    larch_dir = root / "python" / "larch"
    design_dir = larch_dir / "design"
    if not design_dir.is_dir():
        print(f"lint-self-disarmable-gate: design directory not found: {design_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        resolution = resolve_optional_metadata(design_dir)
        findings: list[Finding] = []
        for path in iter_gate_modules(design_dir):
            findings.extend(scan_file(path, larch_dir=larch_dir, meta_fields=resolution.fields))
    except ScanError as exc:
        print(f"lint-self-disarmable-gate: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    for finding in sorted(findings, key=lambda item: (item.file, item.lineno)):
        print(
            f"{finding.file}:{finding.qualified_symbol}: line {finding.lineno}: {finding.message}",
            file=sys.stderr,
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
