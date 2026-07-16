"""Ratchet bare os.environ literals toward config.ENV_* constants.

Thin engine-backed rule: detection scans production modules under
``python/**/*.py`` for os.environ accesses whose string literal already has a
matching ENV_* constant in ``python/larch/core/config.py``. Existing debt is
grandfathered in ``python/env-via-config-constant-baseline.json`` with a
required reason per row. New bare literals fail unless covered by an explicit
exemption or an inline pragma.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, cast

from larch.core import proc
from larch.lint.engine import (
    EXIT_ERROR,
    Finding as EngineFinding,
    LintRule,
    RuleCli,
    SourceFile,
    has_inline_pragma,
    is_exempt_python_source,
    iter_python_source_files,
    load_json_array,
    normalize_python_file_path,
    parse_lint_argv,
    run_rule,
    scan_python_file,
    walk_scopes,
)
from larch.lint.engine import BaselineError

RULE_ID = "env-via-config-constant"
SUPPRESSION_TOKEN = "lint-env-via-config-constant"
BASELINE_FILENAME = "env-via-config-constant-baseline.json"
EXEMPTIONS_FILENAME = "env-via-config-constant-exemptions.json"
EXEMPTION_KEYS = frozenset({"file", "reason", "env_name", "constant"})
REQUIRED_EXEMPTION_KEYS = frozenset({"file", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
CONFIG_RELPATH = "larch/core/config.py"
MODULE_SYMBOL = "<module>"
PRAGMA_RE = re.compile(r"#\s*lint-env-via-config-constant:\s*ok\s+(\S.*)$")
STANDALONE_PRAGMA_RE = re.compile(r"^\s*#\s*lint-env-via-config-constant:\s*ok\s+(\S.*)$")
PYTHON_PREFIX = "python/"


class Exemption(TypedDict):
    file: str
    reason: str
    env_name: NotRequired[str]
    constant: NotRequired[str]


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    env_name: str
    constant: str
    access: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, str, str, int]:
        return (
            self.file,
            self.qualified_symbol,
            self.env_name,
            self.constant,
            self.access,
            self.occurrence,
        )


def _validate_normalized_file(value: object, *, source: Path, index: int, kind: str) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: {kind} {index} has invalid file")
    normalized = normalize_python_file_path(value)
    parts = normalized.split("/")
    if (
        normalized != value
        or normalized.startswith("/")
        or "" in parts
        or "." in parts
        or ".." in parts
    ):
        raise BaselineError(f"{source}: {kind} {index} has invalid file")
    return normalized


def iter_source_files(python_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files, sorted."""
    return iter_python_source_files(
        python_dir,
        excluded_dirs=EXCLUDED_DIRS,
        excluded_relpaths=frozenset({CONFIG_RELPATH}),
    )


def is_production_source_path(rel_path: str) -> bool:
    """Pre-load filter for repo-relative env-via-config scan paths."""
    if not rel_path.startswith(PYTHON_PREFIX) or not rel_path.endswith(".py"):
        return False
    under = Path(rel_path[len(PYTHON_PREFIX) :])
    if EXCLUDED_DIRS.intersection(under.parts) or is_exempt_python_source(under):
        return False
    return under.as_posix() != CONFIG_RELPATH


def _env_assignments(tree: ast.Module) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}

    def record(name: str, *, value_node: ast.AST | None) -> None:
        if not name.startswith("ENV_"):
            return
        if not isinstance(value_node, ast.Constant) or not isinstance(value_node.value, str):
            return
        values.setdefault(value_node.value, []).append(name)

    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            record(node.target.id, value_node=node.value)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    record(target.id, value_node=node.value)
    return values


def parse_config_constants(config_path: Path, *, allow_duplicate_values: bool) -> dict[str, str]:
    """Return env literal to ENV_* constant mapping from config.py."""
    try:
        source = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BaselineError(f"{config_path}: cannot read config: {exc}") from exc
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise BaselineError(f"{config_path}: invalid Python syntax: {exc}") from exc
    assignments = _env_assignments(tree)
    constants: dict[str, str] = {}
    duplicates: list[str] = []
    for value, names in sorted(assignments.items()):
        unique_names = sorted(set(names))
        if len(unique_names) > 1 and not allow_duplicate_values:
            duplicates.append(f"{value}: {', '.join(unique_names)}")
        constants[value] = unique_names[0]
    if duplicates:
        joined = "\n  ".join(duplicates)
        raise BaselineError(f"{config_path}: duplicate ENV_* values:\n  {joined}")
    return constants


def _is_os_environ(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _literal_slice(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _env_access(node: ast.AST) -> tuple[str, str] | None:
    if isinstance(node, ast.Call):
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and _is_os_environ(func.value)
            and node.args
        ):
            env_name = _literal_slice(node.args[0])
            if env_name is not None:
                return (env_name, "get")
    if isinstance(node, ast.Subscript) and _is_os_environ(node.value):
        env_name = _literal_slice(node.slice)
        if env_name is None:
            return None
        if isinstance(node.ctx, ast.Load):
            return (env_name, "subscript_load")
        if isinstance(node.ctx, ast.Store):
            return (env_name, "subscript_store")
    return None


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    normalized_file: str,
    env_constants: dict[str, str],
    findings: list[Finding],
) -> None:
    def enter_scope(symbol: str) -> Callable[[ast.AST], None]:
        occurrence = 0

        def handle(node: ast.AST) -> None:
            nonlocal occurrence
            access = _env_access(node)
            if access is None:
                return
            env_name, access_kind = access
            constant = env_constants.get(env_name)
            if constant is None or env_name.endswith("_SH"):
                return
            occurrence += 1
            lineno = getattr(node, "lineno", 0)
            findings.append(
                Finding(
                    file=normalized_file,
                    qualified_symbol=symbol,
                    env_name=env_name,
                    constant=constant,
                    access=access_kind,
                    occurrence=occurrence,
                    lineno=lineno if isinstance(lineno, int) else 0,
                )
            )

        return handle

    walk_scopes(body, prefix=prefix, module_symbol=MODULE_SYMBOL, enter_scope=enter_scope)


def scan_file(path: Path, *, python_dir: Path, env_constants: dict[str, str]) -> list[Finding]:
    """Return all bare env literal findings for one source file."""
    return scan_python_file(
        path,
        python_dir=python_dir,
        collect=lambda tree, normalized_file, findings: _collect_scope(
            tree.body,
            prefix=(),
            normalized_file=normalized_file,
            env_constants=env_constants,
            findings=findings,
        ),
    )


def findings_from_source(
    source: str, *, normalized_file: str, env_constants: dict[str, str]
) -> list[Finding]:
    """Return raw env findings for one source buffer."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    findings: list[Finding] = []
    _collect_scope(
        tree.body,
        prefix=(),
        normalized_file=normalized_file,
        env_constants=env_constants,
        findings=findings,
    )
    return findings


def _validate_optional_scope(record: dict[str, object], *, key: str, index: int, source: Path) -> str | None:
    if key not in record:
        return None
    value = record[key]
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: exemption {index} has invalid {key}")
    if key == "constant" and not value.startswith("ENV_"):
        raise BaselineError(f"{source}: exemption {index} has invalid constant")
    return value


def _validate_exemption(item: object, *, index: int, source: Path) -> Exemption:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: exemption {index} must be an object")
    record = cast("dict[str, object]", item)
    if set(record) - EXEMPTION_KEYS or not REQUIRED_EXEMPTION_KEYS.issubset(record):
        raise BaselineError(
            f"{source}: exemption {index} must have required keys {sorted(REQUIRED_EXEMPTION_KEYS)} "
            f"and optional keys {sorted(EXEMPTION_KEYS - REQUIRED_EXEMPTION_KEYS)}"
        )
    file_name = _validate_normalized_file(record["file"], source=source, index=index, kind="exemption")
    reason = record["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: exemption {index} has invalid reason")
    exemption: Exemption = {"file": file_name, "reason": reason}
    env_name = _validate_optional_scope(record, key="env_name", index=index, source=source)
    constant = _validate_optional_scope(record, key="constant", index=index, source=source)
    if env_name is not None:
        exemption["env_name"] = env_name
    if constant is not None:
        exemption["constant"] = constant
    return exemption


def load_exemptions(path: Path) -> list[Exemption]:
    """Load optional env exemptions. Missing file means no exemptions."""
    items = load_json_array(path, label="exemptions")
    return [
        _validate_exemption(item, index=index, source=path)
        for index, item in enumerate(items)
    ]


def _exemption_matches(*, finding: Finding, exemption: Exemption) -> bool:
    if exemption["file"] != finding.file:
        return False
    env_name = exemption.get("env_name")
    constant = exemption.get("constant")
    if env_name is None and constant is None:
        return True
    if env_name is not None and constant is not None:
        return finding.env_name == env_name and finding.constant == constant
    if env_name is not None:
        return finding.env_name == env_name
    return finding.constant == constant


def _has_inline_pragma(finding: Finding, *, lines: tuple[str, ...]) -> bool:
    return has_inline_pragma(
        finding.lineno,
        lines,
        pragma_re=PRAGMA_RE,
        standalone_pragma_re=STANDALONE_PRAGMA_RE,
    )


def to_engine_finding(finding: Finding) -> EngineFinding:
    """Adapt one env finding to the shared engine finding shape."""
    return EngineFinding(
        path=f"{PYTHON_PREFIX}{finding.file}",
        line=finding.lineno,
        rule_id=RULE_ID,
        message=(
            f"{finding.qualified_symbol} uses os.environ literal {finding.env_name!r} "
            f"for {finding.constant} access {finding.access} occurrence {finding.occurrence}"
        ),
        qualified_symbol=finding.qualified_symbol,
        occurrence=finding.occurrence,
        occurrence_values=(
            ("env_name", finding.env_name),
            ("constant", finding.constant),
            ("access", finding.access),
        ),
    )


def _allow_duplicate_policy(config_path: Path) -> bool:
    """Allow first-sorted-wins only for this checkout's live config.py."""
    try:
        live_config = Path(__file__).resolve().parent.joinpath(*CONFIG_RELPATH.split("/"))
        return config_path.resolve() == live_config.resolve()
    except OSError:
        return False


def build_rule(root: Path) -> LintRule:
    """Build an engine rule closed over config constants and exemptions for ``root``."""
    python_dir = root / "python"
    config_path = python_dir.joinpath(*CONFIG_RELPATH.split("/"))
    env_constants = parse_config_constants(
        config_path,
        allow_duplicate_values=_allow_duplicate_policy(config_path),
    )
    exemptions = load_exemptions(python_dir / EXEMPTIONS_FILENAME)

    def detect(source: SourceFile) -> list[EngineFinding]:
        if not source.is_python or not is_production_source_path(source.path):
            return []
        normalized_file = source.path.removeprefix(PYTHON_PREFIX)
        raw = findings_from_source(
            source.text, normalized_file=normalized_file, env_constants=env_constants
        )
        lines = source.lines
        return [
            to_engine_finding(finding)
            for finding in raw
            if not any(_exemption_matches(finding=finding, exemption=exemption) for exemption in exemptions)
            and not _has_inline_pragma(finding, lines=lines)
        ]

    return LintRule(
        rule_id=RULE_ID,
        description=(
            "Ratchet bare os.environ literals toward config.ENV_* constants"
        ),
        detect=detect,
        syntax_policy="skip",
        suppression_token=SUPPRESSION_TOKEN,
        allow_inline_suppression=False,
        pathspecs=("python",),
        source_filter=is_production_source_path,
        occurrence_baseline=True,
        occurrence_fields=("env_name", "constant", "access"),
        require_baseline=True,
        warn_matching_baseline=True,
    )


CLI = RuleCli(
    prog="cli.py lint env-via-config-constant",
    description=__doc__,
    baseline_filename=BASELINE_FILENAME,
    error_label="lint-env-via-config-constant",
    scoped_paths=None,
    strict_stale=False,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint env-via-config-constant``."""
    parsed = parse_lint_argv(argv if argv is not None else sys.argv[1:], cli=CLI)
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    try:
        rule = build_rule(root)
    except BaselineError as exc:
        print(f"{CLI.error_label}: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return run_rule(
        rule,
        root,
        proc.ProcRunner(),
        baseline_path=root / "python" / BASELINE_FILENAME,
        write_baseline=bool(parsed.write),
        initial_reason=cast("str | None", parsed.initial_reason),
        strict_stale=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
