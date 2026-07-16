"""Ratchet result-env writers toward key-set parity across sibling writers.

Scans ``python/larch`` for result-env writer calls, groups them by the literal
target basename, and fails when one writer of a basename omits a key that a
sibling writer of the same basename emits. Sibling writers of one result env
that drift apart (a missing ``ROUNDS_COMPLETED`` on a zero-findings path, a
``detail`` field populated in one writer but not its twin) recurred as a class
that per-incident fixes never closed. Existing divergences are grandfathered in
a reason-bearing, shrink-only baseline.

Engine rule wrapper: corpus preparation groups sibling writers cross-file, then
per-source detection emits engine findings. ``main`` delegates to
``larch.lint.engine.run_rule`` so baseline check, write, and reason validation
stay identical to sibling engine rules.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from larch.core import proc
from larch.lint.engine import (
    EXIT_ERROR,
    Finding,
    LintRule,
    ScanError,
    SourceFile,
    run_rule,
)

RULE_ID = "result-env-key-parity"
SUPPRESSION_TOKEN = "lint-result-env-key-parity"
BASELINE_FILENAME = "result-env-key-parity-baseline.json"
PATHSPECS = ("python/larch",)
SCOPE_PREFIX = "python/larch/"
SELF_REL = "python/larch/lint/lint_result_env_key_parity.py"
WRITER_EXACT_NAMES = frozenset({"phase_driver_write_result_env", "write_result_env"})
WRITER_SUFFIX = "_write_result_env"
EXCLUDED_DIR_PARTS = frozenset({"__pycache__"})
KV_TUPLE_LEN = 2
MIN_SIBLING_WRITERS = 2

# Single declared place for per-key exceptions (G-Cfg-3): a basename maps to the
# keys a writer may omit without violating parity. Seeded empty; a per-key
# exception is added here, never scattered at call sites.
OPTIONAL_KEYS: Final[dict[str, frozenset[str]]] = {}


@dataclass(frozen=True)
class WriterCall:
    """A collected result-env writer call with a literal basename and key set."""

    path: str
    line: int
    basename: str
    keys: frozenset[str]


@dataclass(frozen=True)
class PreparedCorpus:
    """Cross-file grouping: required keys per basename and writers per source."""

    required: dict[str, frozenset[str]]
    writers_by_path: dict[str, tuple[WriterCall, ...]]


def _in_scope(path: str) -> bool:
    if not path.startswith(SCOPE_PREFIX) or not path.endswith(".py"):
        return False
    if path == SELF_REL:
        return False
    return not EXCLUDED_DIR_PARTS.intersection(path.split("/"))


def _callee_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _is_writer_name(name: str) -> bool:
    return name in WRITER_EXACT_NAMES or name.endswith(WRITER_SUFFIX)


def _call_arg_values(node: ast.Call) -> list[ast.expr]:
    return [*node.args, *(keyword.value for keyword in node.keywords)]


def _fstring_basename(node: ast.JoinedStr) -> str | None:
    """Return the final path component only when it is fully literal.

    The final component is everything after the last ``/``; an interpolation at
    or after that boundary makes it non-literal, so the call site is skipped.
    """
    tail: list[str] = []
    for value in reversed(node.values):
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            return None
        text: str = value.value
        slash = text.rfind("/")
        if slash != -1:
            tail.append(text[slash + 1 :])
            break
        tail.append(text)
    component = "".join(reversed(tail))
    return component if component.endswith(".env") else None


def _basename_from_expr(expr: ast.expr) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        base = expr.value.rsplit("/", 1)[-1]
        return base if base.endswith(".env") else None
    if isinstance(expr, ast.JoinedStr):
        return _fstring_basename(expr)
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
        return _basename_from_expr(expr.right)
    return None


def _literal_basename(node: ast.Call) -> str | None:
    for arg in _call_arg_values(node):
        basename = _basename_from_expr(arg)
        if basename is not None:
            return basename
    return None


def _keys_from_expr(expr: ast.expr) -> frozenset[str] | None:
    if not isinstance(expr, (ast.List, ast.Tuple)):
        return None
    keys: list[str] = []
    for elt in expr.elts:
        if not isinstance(elt, ast.Tuple) or len(elt.elts) != KV_TUPLE_LEN:
            return None
        first = elt.elts[0]
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            return None
        keys.append(first.value)
    return frozenset(keys)


def _literal_keys(node: ast.Call) -> frozenset[str] | None:
    for arg in _call_arg_values(node):
        keys = _keys_from_expr(arg)
        if keys is not None:
            return keys
    return None


def _collect_source(source: SourceFile) -> list[WriterCall]:
    """Return literal result-env writer calls in one source, or none on error."""
    if not source.is_python or source.python_syntax_error() is not None:
        return []
    tree = source.python_ast
    calls: list[WriterCall] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _callee_name(node)
        if name is None or not _is_writer_name(name):
            continue
        basename = _literal_basename(node)
        if basename is None:
            continue
        keys = _literal_keys(node)
        if keys is None:
            continue
        calls.append(WriterCall(path=source.path, line=node.lineno, basename=basename, keys=keys))
    return calls


def prepare_corpus(sources: Sequence[SourceFile]) -> PreparedCorpus:
    """Group sibling writers across the corpus and compute per-basename required keys."""
    writers_by_path: dict[str, tuple[WriterCall, ...]] = {}
    by_basename: dict[str, list[WriterCall]] = {}
    for source in sources:
        calls = _collect_source(source)
        if not calls:
            continue
        writers_by_path[source.path] = tuple(calls)
        for call in calls:
            by_basename.setdefault(call.basename, []).append(call)
    required: dict[str, frozenset[str]] = {}
    for basename, group in by_basename.items():
        if len(group) < MIN_SIBLING_WRITERS:
            continue
        union = frozenset[str]().union(*(writer.keys for writer in group))
        required[basename] = union - OPTIONAL_KEYS.get(basename, frozenset())
    return PreparedCorpus(required=required, writers_by_path=writers_by_path)


def detect(source: SourceFile, *, prepared: PreparedCorpus) -> list[Finding]:
    """Emit a finding for each key a source writer omits versus its siblings."""
    findings: list[Finding] = []
    for writer in prepared.writers_by_path.get(source.path, ()):
        required = prepared.required.get(writer.basename)
        if required is None:
            continue
        findings.extend(
            Finding(
                path=source.path,
                line=writer.line,
                rule_id=RULE_ID,
                message=f"{writer.basename} writer missing key {key} present in sibling writers",
                anchor=f"{writer.basename}:{key}",
            )
            for key in sorted(required - writer.keys)
        )
    return findings


def build_rule() -> LintRule:
    """Build a fresh engine rule with a corpus-preparation closure."""
    state: list[PreparedCorpus | None] = [None]

    def _prepare(sources: Sequence[SourceFile]) -> None:
        state[0] = prepare_corpus(sources)

    def _detect(source: SourceFile) -> list[Finding]:
        prepared = state[0]
        if prepared is None:
            raise ScanError("prepare_corpus was not called before detect")
        return detect(source, prepared=prepared)

    return LintRule(
        rule_id=RULE_ID,
        description=(
            "Ratchet result-env writers toward key-set parity across sibling "
            "writers of the same target basename."
        ),
        detect=_detect,
        syntax_policy="skip",
        suppression_token=SUPPRESSION_TOKEN,
        allow_inline_suppression=True,
        pathspecs=PATHSPECS,
        source_filter=_in_scope,
        require_baseline=True,
        prepare_corpus=_prepare,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint result-env-key-parity",
        description=__doc__,
    )
    _ = parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root (default: checkout containing this module).",
    )
    _ = parser.add_argument(
        "--write",
        action="store_true",
        help=f"Regenerate {BASELINE_FILENAME} from the live scan.",
    )
    _ = parser.add_argument(
        "--initial-reason",
        help="Reason for live findings that have no preserved baseline reason.",
    )
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint result-env-key-parity``."""
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    baseline_path = root / "python" / BASELINE_FILENAME
    initial_reason = parsed.initial_reason
    if initial_reason is not None and not str(initial_reason).strip():
        print(
            "lint-result-env-key-parity: --initial-reason must be non-empty",
            file=sys.stderr,
        )
        return EXIT_ERROR
    write_baseline = bool(parsed.write)
    return run_rule(
        build_rule(),
        root,
        proc.ProcRunner(),
        baseline_path=baseline_path,
        write_baseline=write_baseline,
        initial_reason=None if initial_reason is None else str(initial_reason),
    )


if __name__ == "__main__":
    raise SystemExit(main())
