"""AST scanner for self-disarmable gate detection.

Provides corpus-based preparation and per-source detection over
``SourceFile`` values from the lint engine. Also re-exports ``scan_file``,
``resolve_optional_metadata``, ``Finding``, ``MetadataResolution``, and
``ScanError`` for legacy callers.
"""
# ruff: noqa: C901, PLR0911, PLR0912, PLR0913, PLR2004, SIM102 - AST gate scan complexity is inherent

from __future__ import annotations

import ast
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.lint.engine import Finding as EngineFinding
from larch.lint.engine import ScanError  # re-export; do not define a local ScanError
from larch.lint.engine import SourceFile
from larch.lint.engine import comment_tokens_by_line, suppression_reason

SUPPRESSION = "lint-self-disarmable-gate"
PRAGMA_RE = re.compile(rf"#\s*{re.escape(SUPPRESSION)}:\s*ok\s+(\S.*)$")
EMPTY_PRAGMA_RE = re.compile(rf"#\s*{re.escape(SUPPRESSION)}:\s*ok\s*$")
OWNER_REASON_RE = re.compile(r"\b(?:gate\s+owner|owner)\s*[:=]\s*\S+", re.IGNORECASE)
REQUIRED_META_FIELDS = frozenset({"diff_added", "mechanical_churn"})
OPTIONAL_METADATA_NAME = "OptionalMetadata"
_DESIGN_PREFIX = "python/larch/design/"
_DESIGN_REL = Path("larch") / "design"
_PLAN_QUALITY_REL = _DESIGN_REL / "plan_quality.py"


@dataclass(frozen=True)
class Finding:
    """Compatibility finding for legacy callers of ``scan_file``."""

    file: str
    qualified_symbol: str
    lineno: int
    message: str


@dataclass
class MetadataResolution:
    fields: frozenset[str]
    defining_file: str


@dataclass
class PreparedCorpus:
    """In-memory context built from corpus preparation."""

    resolution: MetadataResolution


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
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == OPTIONAL_METADATA_NAME:
                    return node.module
        if isinstance(node, ast.Assign):
            if (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == OPTIONAL_METADATA_NAME
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == OPTIONAL_METADATA_NAME
            ):
                return None
    return None


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
    if isinstance(test, ast.Compare) and _contains_meta_field(test, meta_fields=meta_fields):
        return any(isinstance(op, (ast.NotIn, ast.In, ast.Is, ast.IsNot)) for op in test.ops)
    return False


def _is_suppression_condition(test: ast.AST, *, meta_fields: frozenset[str]) -> bool:
    if _contains_meta_field(test, meta_fields=meta_fields) is None:
        return False
    if _is_validation_condition(test, meta_fields=meta_fields):
        return False
    if _is_negated(test):
        return True
    if _is_meta_field_access(test, meta_fields=meta_fields) is not None:
        return True
    if isinstance(test, ast.Compare):
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


def _emit(
    *,
    findings: list[Finding],
    normalized_file: str,
    symbol: str,
    lineno: int,
    message: str,
    comments_by_line: Mapping[int, tuple[str, ...]],
) -> None:
    reason = suppression_reason(
        lineno,
        comments_by_line=comments_by_line,
        pragma_re=PRAGMA_RE,
        empty_pragma_re=EMPTY_PRAGMA_RE,
    )
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
        if isinstance(stmt.value, ast.BoolOp) and isinstance(stmt.value.op, ast.And):
            meta_field = _contains_meta_field(stmt.value, meta_fields=meta_fields)
            if meta_field is not None and (target in hard_names or _looks_like_hard_trigger_name(target)):
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


def _scan_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    normalized_file: str,
    meta_fields: frozenset[str],
    comments_by_line: Mapping[int, tuple[str, ...]],
    findings: list[Finding],
) -> None:
    symbol = node.name
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


def _scan_module(
    tree: ast.Module,
    *,
    normalized_file: str,
    source_text: str,
    meta_fields: frozenset[str],
) -> list[Finding]:
    """Scan one module AST; return compat ``Finding`` list."""
    comments_by_line = comment_tokens_by_line(source_text)
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


# ---------------------------------------------------------------------------
# Corpus-based preparation
# ---------------------------------------------------------------------------

def _probe_syntax(source: SourceFile) -> ast.Module:
    """Probe syntax and return the AST; raise ``ScanError`` on malformed Python."""
    err = source.python_syntax_error()
    if err is not None:
        raise ScanError(f"{source.path}: cannot parse source: {err}")
    return cast("ast.Module", source.python_ast)


def _resolve_from_corpus_source(
    source: SourceFile, *, label: str
) -> MetadataResolution | None:
    """Return ``MetadataResolution`` if ``OptionalMetadata`` is defined in source."""
    tree = _probe_syntax(source)
    local = _find_class(tree, OPTIONAL_METADATA_NAME)
    if local is None:
        return None
    fields = _dataclass_fields(local)
    if not REQUIRED_META_FIELDS.issubset(fields):
        missing = ", ".join(sorted(REQUIRED_META_FIELDS - fields))
        raise ScanError(
            f"OptionalMetadata in {label} missing required fields: {missing}"
        )
    return MetadataResolution(fields=fields, defining_file=source.path)


def resolve_optional_metadata_corpus(
    corpus: Mapping[str, SourceFile],
) -> MetadataResolution:
    """Resolve OptionalMetadata via the plan-quality import chain from corpus."""
    plan_quality_path = _DESIGN_PREFIX + "plan_quality.py"
    plan_quality = corpus.get(plan_quality_path)
    candidates: list[str] = [
        _DESIGN_PREFIX + "_plan_quality_commands.py",
        plan_quality_path,
    ]
    if plan_quality is not None:
        tree = _probe_syntax(plan_quality)
        local = _find_class(tree, OPTIONAL_METADATA_NAME)
        if local is not None:
            fields = _dataclass_fields(local)
            if not REQUIRED_META_FIELDS.issubset(fields):
                missing = ", ".join(sorted(REQUIRED_META_FIELDS - fields))
                raise ScanError(
                    f"OptionalMetadata in {plan_quality_path} missing required fields: {missing}"
                )
            return MetadataResolution(fields=fields, defining_file=plan_quality_path)
        imported_module = _import_optional_metadata_module(tree)
        if imported_module is not None:
            module_tail = imported_module.rsplit(".", maxsplit=1)[-1]
            candidate = _DESIGN_PREFIX + f"{module_tail}.py"
            if candidate not in candidates:
                candidates.insert(0, candidate)
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == OPTIONAL_METADATA_NAME and node.module:
                        module_tail = node.module.rsplit(".", maxsplit=1)[-1]
                        candidate = _DESIGN_PREFIX + f"{module_tail}.py"
                        if candidate not in candidates:
                            candidates.insert(0, candidate)
    for path in candidates:
        source = corpus.get(path)
        if source is None:
            continue
        resolution = _resolve_from_corpus_source(source, label=path)
        if resolution is not None:
            return resolution
    raise ScanError(
        "cannot resolve OptionalMetadata definition covering "
        f"{', '.join(sorted(REQUIRED_META_FIELDS))}"
    )


def prepare_corpus(sources: Sequence[SourceFile]) -> PreparedCorpus:
    """Build in-memory preparation context from the complete corpus.

    Probes syntax before accessing ASTs; raises ``ScanError`` on malformed
    Python in any design source that carries ``OptionalMetadata``.
    """
    corpus = {s.path: s for s in sources if s.path.startswith(_DESIGN_PREFIX)}
    resolution = resolve_optional_metadata_corpus(corpus)
    return PreparedCorpus(resolution=resolution)


def detect(source: SourceFile, *, prepared: PreparedCorpus) -> list[EngineFinding]:
    """Detect self-disarmable gate violations in one source.

    The engine's ``syntax_policy='raise'`` guarantees that syntax was probed
    before this function is called on the normal ``run_rule`` path.
    """
    tree = cast("ast.Module", source.python_ast)
    local_findings = _scan_module(
        tree,
        normalized_file=source.path,
        source_text=source.text,
        meta_fields=prepared.resolution.fields,
    )
    return [
        EngineFinding(
            path=f.file,
            line=f.lineno,
            rule_id=SUPPRESSION,
            message=f.message,
            qualified_symbol=f.qualified_symbol,
        )
        for f in local_findings
    ]


# ---------------------------------------------------------------------------
# Compatibility exports (legacy Path-based interface)
# ---------------------------------------------------------------------------

def _read_parse(path: Path, *, label: str) -> tuple[str, ast.Module]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ScanError(f"{label}: cannot read source: {exc}") from exc
    try:
        return source, ast.parse(source)
    except SyntaxError as exc:
        raise ScanError(f"{label}: cannot parse source: {exc}") from exc


def resolve_optional_metadata(design_dir: Path) -> MetadataResolution:
    """Resolve OptionalMetadata fields via the plan-quality import chain."""
    candidates = [
        design_dir / "_plan_quality_commands.py",
        design_dir / "plan_quality.py",
    ]
    plan_quality = design_dir / "plan_quality.py"
    if plan_quality.is_file():
        _, tree = _read_parse(plan_quality, label=str(_PLAN_QUALITY_REL))
        local = _find_class(tree, OPTIONAL_METADATA_NAME)
        if local is not None:
            fields = _dataclass_fields(local)
            if not REQUIRED_META_FIELDS.issubset(fields):
                missing = ", ".join(sorted(REQUIRED_META_FIELDS - fields))
                raise ScanError(
                    f"OptionalMetadata in {_PLAN_QUALITY_REL} missing required fields: {missing}"
                )
            return MetadataResolution(fields=fields, defining_file=str(_PLAN_QUALITY_REL))
        imported_module = _import_optional_metadata_module(tree)
        if imported_module is not None:
            module_tail = imported_module.rsplit(".", maxsplit=1)[-1]
            candidate = design_dir / f"{module_tail}.py"
            if candidate.is_file():
                candidates.insert(0, candidate)
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
        _, tree = _read_parse(path, label=path.name)
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


def scan_file(
    path: Path,
    *,
    larch_dir: Path,
    meta_fields: frozenset[str],
) -> list[Finding]:
    """Return self-disarm findings for one design module (legacy interface)."""
    normalized_file = path.relative_to(larch_dir.parent).as_posix()
    source_text, tree = _read_parse(path, label=normalized_file)
    return _scan_module(
        tree,
        normalized_file=normalized_file,
        source_text=source_text,
        meta_fields=meta_fields,
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
