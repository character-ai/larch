"""Ratchet ad-hoc raw ``KEY=value`` readers and issue emitters toward shared owners.

The scan deliberately targets only reader-shaped split loops, shell
``awk -F=`` / ``cut -d=`` forms, and the two migrated issue emitter modules.
It does not flag ordinary option or tab-delimited parsing. Existing bootstrap
and compatibility debt is kept in the strict, reason-bearing baseline; inline
comments cannot suppress a gate.
"""

from __future__ import annotations

import ast
import hashlib
import re
import sys
from pathlib import Path
from typing import cast

from larch.core import proc
from larch.lint.engine import Finding, LintRule, RuleCli, SourceFile, run_rule_cli

RULE_ID = "kv-codec"
SUPPRESSION_TOKEN = "lint-kv-codec"
BASELINE_FILENAME = "kv-codec-baseline.json"
PYTHON_PREFIX = "python/larch/"
SHELL_PREFIXES = ("scripts/", "skills/")
READER_OWNER_PATHS = frozenset({"python/larch/io.py", "python/larch/core/env_file.py"})
EMITTER_OWNER_PATH = "python/larch/core/logging_util.py"
EMITTER_GUARDED_PATHS = frozenset({
    "python/larch/issue/issue_create.py",
    "python/larch/issue/execution_issues.py",
})
SPLIT_ARGUMENT_COUNT = 2


def _is_split_equals(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "split"
        and len(node.args) >= SPLIT_ARGUMENT_COUNT
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "="
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == 1
    )


def _is_option_loop(node: ast.AST) -> bool:
    return (
        isinstance(node, (ast.For, ast.AsyncFor))
        and isinstance(node.iter, ast.Name)
        and node.iter.id in {"args", "argv", "options", "tokens"}
    )


def _python_findings(source: SourceFile) -> list[Finding]:
    if not source.path.startswith(PYTHON_PREFIX):
        return []
    findings = _emitter_findings(source)
    if source.path in READER_OWNER_PATHS:
        return findings
    calls: dict[int, ast.Call] = {}
    for node in ast.walk(source.python_ast):
        if not isinstance(node, (ast.For, ast.AsyncFor, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            continue
        if _is_option_loop(node):
            continue
        for child in ast.walk(node):
            if _is_split_equals(child):
                call = cast("ast.Call", child)
                calls[call.lineno] = call
    findings.extend(
        _split_finding(source, call, occurrence=occurrence)
        for occurrence, call in enumerate(calls.values(), start=1)
    )
    return findings


def _emitter_findings(source: SourceFile) -> list[Finding]:
    if source.path == EMITTER_OWNER_PATH:
        return []
    findings: list[Finding] = []
    for node in ast.walk(source.python_ast):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "emit_kv":
            findings.append(_emitter_finding(source, node.lineno, "private emit_kv definition"))
        elif source.path in EMITTER_GUARDED_PATHS and isinstance(node, ast.Call) and _is_kv_print(node):
            findings.append(_emitter_finding(source, node.lineno, "ad-hoc KEY=value print wrapper"))
    return findings


def _is_kv_print(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Name) or node.func.id != "print" or not node.args:
        return False
    first = node.args[0]
    return (
        isinstance(first, ast.JoinedStr)
        and any(isinstance(value, ast.Constant) and value.value == "=" for value in first.values)
    )


def _emitter_finding(source: SourceFile, line: int, detail: str) -> Finding:
    return Finding(
        path=source.path,
        line=line,
        rule_id=RULE_ID,
        message=f"{detail}; use larch.core.logging_util.emit_kv",
        anchor=f"emitter={detail}:{line}",
    )


def _split_finding(source: SourceFile, call: ast.Call, *, occurrence: int) -> Finding:
    return Finding(
        path=source.path,
        line=call.lineno,
        rule_id=RULE_ID,
        message="ad-hoc KEY=value split loop; use larch.io codec",
        anchor="split=" + hashlib.sha256(
            f"{ast.dump(call, include_attributes=False)}:{occurrence}".encode()
        ).hexdigest(),
    )


_AWK_EQUALS_RE = re.compile(
    r"\bawk\b(?=[^\n]*(?:\$1|index\(\$0\)))[^\n]*-F\s*(?:=|['\"]=['\"]?)"
)
_CUT_EQUALS_RE = re.compile(
    r"\bcut\b(?=[^\n]*-f\s*\d)[^\n]*-d\s*(?:=|['\"]=['\"]?)",
    re.IGNORECASE,
)
_GREP_KEY_EQUALS_RE = re.compile(
    r"\bgrep\b(?!\s+-)[^\n]*[\"']\^[A-Za-z_${][^\"']*=[^\"']*[\"']",
)


def _shell_anchor(*, line: str, occurrence: int) -> str:
    normalized = " ".join(line.split())
    digest = hashlib.sha256(f"{normalized}:{occurrence}".encode()).hexdigest()
    return f"shell={digest}"


def _shell_findings(source: SourceFile) -> list[Finding]:
    if (
        not source.path.endswith(".sh")
        or not source.path.startswith(SHELL_PREFIXES)
        or Path(source.path).name.startswith("test-")
    ):
        return []
    findings: list[Finding] = []
    occurrence = 0
    for number, line in enumerate(source.lines, start=1):
        if (
            _AWK_EQUALS_RE.search(line)
            or _CUT_EQUALS_RE.search(line)
            or _GREP_KEY_EQUALS_RE.search(line)
        ):
            occurrence += 1
            findings.append(
                Finding(
                    path=source.path,
                    line=number,
                    rule_id=RULE_ID,
                    message="ad-hoc shell KEY=value reader; use scripts/larch.sh kv get",
                    anchor=_shell_anchor(line=line, occurrence=occurrence),
                )
            )
    return findings


def detect(source: SourceFile) -> list[Finding]:
    """Return narrow production parsing findings for the shared lint engine."""
    if source.is_python:
        return _python_findings(source)
    return _shell_findings(source)


RULE = LintRule(
    rule_id=RULE_ID,
    description="Ratchet raw KEY=value parsing and emission toward shared codecs",
    detect=detect,
    syntax_policy="fail",
    suppression_token=SUPPRESSION_TOKEN,
    allow_inline_suppression=False,
)


def main(argv: list[str] | None = None) -> int:
    """Run the kv-codec ratchet or regenerate its checked-in baseline."""
    return run_rule_cli(
        argv if argv is not None else sys.argv[1:],
        rule=RULE,
        cli=RuleCli(
            prog="cli.py lint kv-codec",
            description=__doc__,
            baseline_filename=BASELINE_FILENAME,
            error_label="lint-kv-codec",
            scoped_paths=("python/larch", "scripts", "skills"),
        ),
        runner=proc.ProcRunner(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
