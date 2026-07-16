"""Adoption ratchet: flag lint modules that still own private CLI/baseline plumbing.

Tracks ``python/larch/lint/lint_*.py``. Flags:

1. Operational ``argparse.ArgumentParser`` construction outside the shared engine,
   unless module-level ``main`` directly delegates to an imported
   ``larch.lint.engine.run_rule`` binding.
2. Direct sibling ``*-baseline.json`` I/O (and same-module helper indirection)
   outside the shared engine baseline path.

Grandfathering is baseline-only: ``allow_inline_suppression=False``. Stable
identity is ``(path, rule_id, fixed message, class anchor)``.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from larch.core import proc
from larch.lint.engine import (
    EXIT_ERROR,
    Finding,
    LintRule,
    SourceFile,
    run_rule,
)

RULE_ID = "engine-adoption"
SUPPRESSION_TOKEN = "lint-engine-adoption"
BASELINE_FILENAME = "lint-engine-adoption-baseline.json"
PATHSPECS = ("python/larch/lint/lint_*.py",)
SCOPE_PREFIX = "python/larch/lint/"
ANCHOR_ARGPARSE = "argparse-construction"
ANCHOR_BASELINE = "baseline-io"
MSG_ARGPARSE = "legacy ArgumentParser construction outside shared lint engine"
MSG_BASELINE = "direct *-baseline.json I/O outside shared lint engine"
BASELINE_SUFFIX = "-baseline.json"
ENGINE_MODULE = "larch.lint.engine"
RUN_RULE_NAME = "run_rule"
IO_METHODS = frozenset({"read_text", "write_text", "open"})
JSON_FUNCS = frozenset({"load", "dump", "loads", "dumps"})


def _in_scope(path: str) -> bool:
    if not path.startswith(SCOPE_PREFIX) or not path.endswith(".py"):
        return False
    name = path.rsplit("/", 1)[-1]
    return name.startswith("lint_") and "/" not in path[len(SCOPE_PREFIX) :]


def _is_baseline_filename(value: object) -> bool:
    return isinstance(value, str) and value.endswith(BASELINE_SUFFIX) and bool(value)


@dataclass(frozen=True)
class _ImportBindings:
    """Resolved names that refer to ArgumentParser or engine.run_rule."""

    argparse_ctors: frozenset[str]
    run_rule_names: frozenset[str]
    json_modules: frozenset[str]
    path_ctors: frozenset[str]
    open_names: frozenset[str]


@dataclass
class _BindingAccum:
    """Mutable import-binding accumulator used while walking imports."""

    argparse_ctors: set[str]
    run_rule_names: set[str]
    json_modules: set[str]
    path_ctors: set[str]
    open_names: set[str]


def _note_plain_import(alias: ast.alias, accum: _BindingAccum) -> None:
    asname = alias.asname or alias.name
    if alias.name == "argparse" or alias.name.startswith("argparse."):
        accum.argparse_ctors.add(f"{asname}.ArgumentParser")
    if alias.name == "json" or alias.name.startswith("json."):
        accum.json_modules.add(asname)
    if alias.name == "pathlib" or alias.name.startswith("pathlib."):
        accum.path_ctors.add(f"{asname}.Path")


def _note_from_import(module: str, alias: ast.alias, accum: _BindingAccum) -> None:
    local = alias.asname or alias.name
    if module == "argparse" and alias.name == "ArgumentParser":
        accum.argparse_ctors.add(local)
    if module == ENGINE_MODULE and alias.name == RUN_RULE_NAME:
        accum.run_rule_names.add(local)
    if module == "json" and alias.name in JSON_FUNCS:
        accum.json_modules.add(f"__func__.{local}")
    if module == "json" and alias.name == "json":
        accum.json_modules.add(local)
    if module in {"pathlib", "pathlib._local"} and alias.name == "Path":
        accum.path_ctors.add(local)
    if module == "builtins" and alias.name == "open":
        accum.open_names.add(local)


def _collect_import_bindings(tree: ast.AST) -> _ImportBindings:
    accum = _BindingAccum(set(), set(), set(), set(), {"open"})
    body = tree.body if isinstance(tree, ast.Module) else []
    for node in body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                _note_plain_import(alias, accum)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                _note_from_import(module, alias, accum)
    return _ImportBindings(
        argparse_ctors=frozenset(accum.argparse_ctors),
        run_rule_names=frozenset(accum.run_rule_names),
        json_modules=frozenset(accum.json_modules),
        path_ctors=frozenset(accum.path_ctors),
        open_names=frozenset(accum.open_names),
    )


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    return None


def _is_argparse_ctor_call(node: ast.Call, *, bindings: _ImportBindings) -> bool:
    name = _call_name(node.func)
    return name is not None and name in bindings.argparse_ctors


def _main_delegates_to_run_rule(tree: ast.Module, *, bindings: _ImportBindings) -> bool:
    if not bindings.run_rule_names:
        return False
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != "main":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            callee = _call_name(child.func)
            if callee is not None and callee in bindings.run_rule_names:
                return True
        return False
    return False


def _first_argparse_call_line(
    tree: ast.Module, *, bindings: _ImportBindings
) -> int | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_argparse_ctor_call(node, bindings=bindings):
            return int(getattr(node, "lineno", 1) or 1)
    return None


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_str_bindings(tree: ast.Module) -> dict[str, str]:
    """Map simple module-level ``NAME = "..."`` bindings to their string values."""
    bindings: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = _const_str(node.value)
        if value is not None:
            bindings[target.id] = value
    return bindings


def _resolve_name(
    node: ast.Name,
    *,
    str_bindings: dict[str, str],
    baseline_names: frozenset[str],
) -> str | None:
    if node.id in str_bindings:
        return str_bindings[node.id]
    if node.id in baseline_names:
        return f"<baseline:{node.id}>"
    return None


def _resolve_div(
    node: ast.BinOp,
    *,
    str_bindings: dict[str, str],
    path_ctors: frozenset[str],
    baseline_names: frozenset[str],
) -> str | None:
    left = _resolve_path_expr(
        node.left,
        str_bindings=str_bindings,
        path_ctors=path_ctors,
        baseline_names=baseline_names,
    )
    right = _resolve_path_expr(
        node.right,
        str_bindings=str_bindings,
        path_ctors=path_ctors,
        baseline_names=baseline_names,
    )
    for side in (right, left):
        if side is not None and (
            _is_baseline_filename(side) or side.startswith("<baseline:")
        ):
            return side
    if right is not None and left is not None:
        return f"{left}/{right}"
    return right or left


def _resolve_path_expr(
    node: ast.AST,
    *,
    str_bindings: dict[str, str],
    path_ctors: frozenset[str],
    baseline_names: frozenset[str],
) -> str | None:
    """Best-effort resolve a path expression to a string containing a filename."""
    literal = _const_str(node)
    if literal is not None:
        return literal
    if isinstance(node, ast.Name):
        return _resolve_name(
            node, str_bindings=str_bindings, baseline_names=baseline_names
        )
    if isinstance(node, ast.Call):
        callee = _call_name(node.func)
        if callee in path_ctors and node.args:
            return _resolve_path_expr(
                node.args[0],
                str_bindings=str_bindings,
                path_ctors=path_ctors,
                baseline_names=baseline_names,
            )
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _resolve_div(
            node,
            str_bindings=str_bindings,
            path_ctors=path_ctors,
            baseline_names=baseline_names,
        )
    return None


def _resolved_is_baseline(resolved: str | None) -> bool:
    if resolved is None:
        return False
    if resolved.startswith("<baseline:"):
        return True
    return _is_baseline_filename(resolved) or resolved.endswith(BASELINE_SUFFIX)


def _expr_is_baseline_path(
    node: ast.AST,
    *,
    str_bindings: dict[str, str],
    path_ctors: frozenset[str],
    baseline_names: frozenset[str],
) -> bool:
    if isinstance(node, ast.Name) and node.id in baseline_names:
        return True
    resolved = _resolve_path_expr(
        node,
        str_bindings=str_bindings,
        path_ctors=path_ctors,
        baseline_names=baseline_names,
    )
    return _resolved_is_baseline(resolved)


def _assign_target_value(node: ast.AST) -> tuple[ast.Name, ast.AST] | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if isinstance(target, ast.Name):
            return target, node.value
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        target = node.target
        if isinstance(target, ast.Name):
            return target, node.value
    return None


def _collect_baseline_names(
    tree: ast.Module,
    *,
    str_bindings: dict[str, str],
    path_ctors: frozenset[str],
) -> frozenset[str]:
    """Names assigned from expressions that resolve to a ``*-baseline.json`` path."""
    names: set[str] = {
        name for name, value in str_bindings.items() if _is_baseline_filename(value)
    }
    changed = True
    while changed:
        changed = False
        snapshot = frozenset(names)
        for node in ast.walk(tree):
            pair = _assign_target_value(node)
            if pair is None:
                continue
            target, value = pair
            if target.id in names:
                continue
            if _expr_is_baseline_path(
                value,
                str_bindings=str_bindings,
                path_ctors=path_ctors,
                baseline_names=snapshot,
            ):
                names.add(target.id)
                changed = True
    return frozenset(names)


def _is_json_call(node: ast.Call, *, bindings: _ImportBindings) -> bool:
    name = _call_name(node.func)
    if name is None:
        return False
    if name.startswith("__func__.") and name in bindings.json_modules:
        return True
    if "." in name:
        module, _, attr = name.partition(".")
        return module in bindings.json_modules and attr in JSON_FUNCS
    return f"__func__.{name}" in bindings.json_modules


class _PathKwargs(TypedDict):
    """Keyword bundle forwarded to :func:`_expr_is_baseline_path`."""

    str_bindings: dict[str, str]
    path_ctors: frozenset[str]
    baseline_names: frozenset[str]


def _is_direct_baseline_io_call(
    node: ast.Call,
    *,
    str_bindings: dict[str, str],
    bindings: _ImportBindings,
    baseline_names: frozenset[str],
) -> bool:
    path_kwargs: _PathKwargs = {
        "str_bindings": str_bindings,
        "path_ctors": bindings.path_ctors,
        "baseline_names": baseline_names,
    }
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in IO_METHODS
        and _expr_is_baseline_path(node.func.value, **path_kwargs)
    ):
        return True
    callee = _call_name(node.func)
    if (
        callee in bindings.open_names
        and node.args
        and _expr_is_baseline_path(node.args[0], **path_kwargs)
    ):
        return True
    if not _is_json_call(node, bindings=bindings):
        return False
    for arg in node.args:
        if isinstance(arg, ast.Call) and _is_direct_baseline_io_call(
            arg,
            str_bindings=str_bindings,
            bindings=bindings,
            baseline_names=baseline_names,
        ):
            return True
        if _expr_is_baseline_path(arg, **path_kwargs):
            return True
    return False


def _param_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = func.args
    names = [arg.arg for arg in args.posonlyargs]
    names.extend(arg.arg for arg in args.args)
    if args.vararg is not None:
        names.append(args.vararg.arg)
    names.extend(arg.arg for arg in args.kwonlyargs)
    if args.kwarg is not None:
        names.append(args.kwarg.arg)
    return names


def _call_uses_param_as_io_target(
    node: ast.Call, *, param: str, bindings: _ImportBindings
) -> bool:
    if isinstance(node.func, ast.Attribute) and node.func.attr in IO_METHODS:
        receiver = node.func.value
        if isinstance(receiver, ast.Name) and receiver.id == param:
            return True
    callee = _call_name(node.func)
    if callee in bindings.open_names and node.args:
        first = node.args[0]
        if isinstance(first, ast.Name) and first.id == param:
            return True
    if not _is_json_call(node, bindings=bindings):
        return False
    for arg in node.args:
        if isinstance(arg, ast.Name) and arg.id == param:
            return True
        if (
            isinstance(arg, ast.Call)
            and isinstance(arg.func, ast.Attribute)
            and arg.func.attr in IO_METHODS
            and isinstance(arg.func.value, ast.Name)
            and arg.func.value.id == param
        ):
            return True
    return False


def _name_flows_to_baseline_sink(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    param: str,
    bindings: _ImportBindings,
) -> bool:
    """Return True when ``param`` is used as a baseline I/O target inside ``func``."""
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and _call_uses_param_as_io_target(
            node, param=param, bindings=bindings
        ):
            return True
    return False


def _baseline_helper_params(
    tree: ast.Module,
    *,
    bindings: _ImportBindings,
) -> dict[str, frozenset[int]]:
    """Map local helper name -> parameter indexes that flow into baseline I/O."""
    helpers: dict[str, frozenset[int]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        params = _param_names(node)
        sinking = {
            index
            for index, param in enumerate(params)
            if _name_flows_to_baseline_sink(node, param=param, bindings=bindings)
        }
        if sinking:
            helpers[node.name] = frozenset(sinking)
    return helpers


@dataclass(frozen=True)
class _PathContext:
    """Shared path-resolution inputs for baseline I/O analysis."""

    str_bindings: dict[str, str]
    path_ctors: frozenset[str]
    baseline_names: frozenset[str]
    bindings: _ImportBindings


def _helper_call_passes_baseline(
    node: ast.Call,
    *,
    tree: ast.Module,
    helpers: dict[str, frozenset[int]],
    ctx: _PathContext,
) -> bool:
    callee = _call_name(node.func)
    if callee is None or callee not in helpers:
        return False
    sinking = helpers[callee]
    path_kwargs: _PathKwargs = {
        "str_bindings": ctx.str_bindings,
        "path_ctors": ctx.path_ctors,
        "baseline_names": ctx.baseline_names,
    }
    for index, arg in enumerate(node.args):
        if index in sinking and _expr_is_baseline_path(arg, **path_kwargs):
            return True
    func_defs = [
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == callee
    ]
    if not func_defs:
        return False
    params = _param_names(func_defs[0])
    for keyword in node.keywords:
        if keyword.arg is None or keyword.arg not in params:
            continue
        param_index = params.index(keyword.arg)
        if param_index in sinking and _expr_is_baseline_path(
            keyword.value, **path_kwargs
        ):
            return True
    return False


def _first_baseline_io_line(
    tree: ast.Module,
    *,
    ctx: _PathContext,
) -> int | None:
    helpers = _baseline_helper_params(tree, bindings=ctx.bindings)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_direct_baseline_io_call(
            node,
            str_bindings=ctx.str_bindings,
            bindings=ctx.bindings,
            baseline_names=ctx.baseline_names,
        ) or _helper_call_passes_baseline(
            node,
            tree=tree,
            helpers=helpers,
            ctx=ctx,
        ):
            return int(getattr(node, "lineno", 1) or 1)
    return None


def detect(source: SourceFile) -> list[Finding]:
    """Detect legacy ArgumentParser construction and sibling baseline I/O."""
    if not source.is_python or not _in_scope(source.path):
        return []
    tree = source.python_ast
    if not isinstance(tree, ast.Module):
        return []
    bindings = _collect_import_bindings(tree)
    str_bindings = _collect_str_bindings(tree)
    baseline_names = _collect_baseline_names(
        tree, str_bindings=str_bindings, path_ctors=bindings.path_ctors
    )
    ctx = _PathContext(
        str_bindings=str_bindings,
        path_ctors=bindings.path_ctors,
        baseline_names=baseline_names,
        bindings=bindings,
    )
    findings: list[Finding] = []

    adopted = _main_delegates_to_run_rule(tree, bindings=bindings)
    if not adopted:
        argparse_line = _first_argparse_call_line(tree, bindings=bindings)
        if argparse_line is not None:
            findings.append(
                Finding(
                    path=source.path,
                    line=argparse_line,
                    rule_id=RULE_ID,
                    message=MSG_ARGPARSE,
                    anchor=ANCHOR_ARGPARSE,
                )
            )

    baseline_line = _first_baseline_io_line(tree, ctx=ctx)
    if baseline_line is not None:
        findings.append(
            Finding(
                path=source.path,
                line=baseline_line,
                rule_id=RULE_ID,
                message=MSG_BASELINE,
                anchor=ANCHOR_BASELINE,
            )
        )
    return findings


RULE = LintRule(
    rule_id=RULE_ID,
    description=(
        "Ratchet python/larch/lint/lint_*.py modules onto the shared lint engine "
        "by flagging private ArgumentParser construction and sibling baseline I/O"
    ),
    detect=detect,
    syntax_policy="fail",
    suppression_token=SUPPRESSION_TOKEN,
    allow_inline_suppression=False,
    pathspecs=PATHSPECS,
    source_filter=_in_scope,
    require_baseline=True,
)


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint engine-adoption",
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
    _ = parser.add_argument(
        "--strict-stale",
        action="store_true",
        help="Fail when the baseline contains rows with no matching live finding.",
    )
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint engine-adoption``."""
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    baseline_path = root / "python" / BASELINE_FILENAME
    initial_reason = parsed.initial_reason
    if initial_reason is not None and not str(initial_reason).strip():
        print(
            "lint-engine-adoption: --initial-reason must be non-empty",
            file=sys.stderr,
        )
        return EXIT_ERROR
    write_baseline = bool(parsed.write)
    strict_stale = bool(parsed.strict_stale) and not write_baseline
    return run_rule(
        RULE,
        root,
        proc.ProcRunner(),
        baseline_path=baseline_path,
        write_baseline=write_baseline,
        initial_reason=None if initial_reason is None else str(initial_reason),
        strict_stale=strict_stale,
    )


if __name__ == "__main__":
    raise SystemExit(main())
