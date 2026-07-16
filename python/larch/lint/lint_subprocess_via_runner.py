"""Ratchet direct subprocess calls toward the proc.Runner seam.

Thin engine-backed rule pair: detection scans production modules under
``python/**/*.py`` for direct calls to selected subprocess APIs and for direct
``runner.run(["gh", ...])`` calls outside the gh wrapper. Existing debt is
grandfathered in ``python/subprocess-via-runner-baseline.json`` and
``python/subprocess-via-runner-gh-baseline.json`` with a required reason per
row. New direct calls fail unless covered by an explicit file exemption or an
inline pragma.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from larch.core import proc
from larch.lint.engine import (
    EXIT_ERROR,
    Finding as EngineFinding,
    LintRule,
    RuleCli,
    SourceFile,
    has_inline_pragma,
    is_exempt_python_source,
    load_json_array,
    parse_lint_argv,
    run_rule,
    scan_python_file,
    walk_scopes,
)
from larch.lint.engine import BaselineError

RULE_ID = "subprocess-via-runner"
GH_RULE_ID = "subprocess-via-runner-gh"
SUPPRESSION_TOKEN = "lint-subprocess-via-runner"
BASELINE_FILENAME = "subprocess-via-runner-baseline.json"
EXEMPTIONS_FILENAME = "subprocess-via-runner-exemptions.json"
GH_BASELINE_FILENAME = "subprocess-via-runner-gh-baseline.json"
ALLOWED_CALLEES = frozenset({"run", "Popen", "check_output", "call"})
EXEMPTION_KEYS = frozenset({"file", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
RUNNER_RELPATH = "larch/core/proc.py"
GH_WRAPPER_RELPATH = "larch/git/gh.py"
MODULE_SYMBOL = "<module>"
PRAGMA_RE = re.compile(r"#\s*lint-subprocess-via-runner:\s*ok\s+(\S.*)$")
STANDALONE_PRAGMA_RE = re.compile(r"^\s*#\s*lint-subprocess-via-runner:\s*ok\s+(\S.*)$")
PYTHON_PREFIX = "python/"


class Exemption(TypedDict):
    file: str
    reason: str


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    callee: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, int]:
        return (self.file, self.qualified_symbol, self.callee, self.occurrence)


@dataclass(frozen=True)
class GhFinding:
    file: str
    qualified_symbol: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, int]:
        return (self.file, self.qualified_symbol, self.occurrence)


def iter_source_files(python_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files, sorted."""
    result: list[Path] = []
    for path in sorted(python_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink() or is_exempt_python_source(path):
            continue
        relative = path.relative_to(python_dir)
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        normalized = relative.as_posix()
        if normalized == RUNNER_RELPATH:
            continue
        result.append(path)
    return result


def is_production_source_path(rel_path: str) -> bool:
    """Pre-load filter for repo-relative subprocess scan paths."""
    if not rel_path.startswith(PYTHON_PREFIX) or not rel_path.endswith(".py"):
        return False
    under = Path(rel_path[len(PYTHON_PREFIX) :])
    if EXCLUDED_DIRS.intersection(under.parts) or is_exempt_python_source(under):
        return False
    return under.as_posix() != RUNNER_RELPATH


def _subprocess_callee(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in ALLOWED_CALLEES:
        return None
    if not isinstance(func.value, ast.Name) or func.value.id != "subprocess":
        return None
    return func.attr


def _runner_run_gh_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "run":
        return False
    if not node.args:
        return False
    argv = node.args[0]
    if not isinstance(argv, (ast.List, ast.Tuple)) or not argv.elts:
        return False
    first = argv.elts[0]
    return isinstance(first, ast.Constant) and first.value == "gh"


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    normalized_file: str,
    findings: list[Finding],
) -> None:
    def enter_scope(symbol: str) -> Callable[[ast.AST], None]:
        occurrence = 0

        def handle(node: ast.AST) -> None:
            nonlocal occurrence
            callee = _subprocess_callee(node)
            if callee is None:
                return
            occurrence += 1
            lineno = getattr(node, "lineno", 0)
            findings.append(
                Finding(
                    file=normalized_file,
                    qualified_symbol=symbol,
                    callee=callee,
                    occurrence=occurrence,
                    lineno=lineno if isinstance(lineno, int) else 0,
                )
            )

        return handle

    walk_scopes(body, prefix=prefix, module_symbol=MODULE_SYMBOL, enter_scope=enter_scope)


def _collect_gh_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    normalized_file: str,
    findings: list[GhFinding],
) -> None:
    def enter_scope(symbol: str) -> Callable[[ast.AST], None]:
        occurrence = 0

        def handle(node: ast.AST) -> None:
            nonlocal occurrence
            if not _runner_run_gh_call(node):
                return
            occurrence += 1
            lineno = getattr(node, "lineno", 0)
            findings.append(
                GhFinding(
                    file=normalized_file,
                    qualified_symbol=symbol,
                    occurrence=occurrence,
                    lineno=lineno if isinstance(lineno, int) else 0,
                )
            )

        return handle

    walk_scopes(body, prefix=prefix, module_symbol=MODULE_SYMBOL, enter_scope=enter_scope)


def scan_gh_file(path: Path, *, python_dir: Path) -> list[GhFinding]:
    """Return direct runner.run(["gh", ...]) findings for one source file."""
    return scan_python_file(
        path,
        python_dir=python_dir,
        collect=lambda tree, normalized_file, findings: _collect_gh_scope(
            tree.body,
            prefix=(),
            normalized_file=normalized_file,
            findings=findings,
        ),
    )


def scan_file(path: Path, *, python_dir: Path) -> list[Finding]:
    """Return all direct subprocess findings for one source file."""
    return scan_python_file(
        path,
        python_dir=python_dir,
        collect=lambda tree, normalized_file, findings: _collect_scope(
            tree.body,
            prefix=(),
            normalized_file=normalized_file,
            findings=findings,
        ),
    )


def findings_from_source(source: str, *, normalized_file: str) -> list[Finding]:
    """Return raw subprocess findings for one source buffer."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    findings: list[Finding] = []
    _collect_scope(tree.body, prefix=(), normalized_file=normalized_file, findings=findings)
    return findings


def gh_findings_from_source(source: str, *, normalized_file: str) -> list[GhFinding]:
    """Return raw gh wrapper-bypass findings for one source buffer."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    findings: list[GhFinding] = []
    _collect_gh_scope(tree.body, prefix=(), normalized_file=normalized_file, findings=findings)
    return findings


def _validate_exemption(item: object, *, index: int, source: Path) -> Exemption:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: exemption {index} must be an object")
    record = cast("dict[str, object]", item)
    if set(record) != set(EXEMPTION_KEYS):
        raise BaselineError(f"{source}: exemption {index} must have exactly {sorted(EXEMPTION_KEYS)}")
    value = record["file"]
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: exemption {index} has invalid file")
    parts = value.split("/")
    if (
        value.startswith("/")
        or "" in parts
        or "." in parts
        or ".." in parts
    ):
        raise BaselineError(f"{source}: exemption {index} has invalid file")
    reason = record["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: exemption {index} has invalid reason")
    return {"file": value, "reason": reason}


def load_exemptions(path: Path) -> list[Exemption]:
    """Load optional file-level exemptions. Missing file means no exemptions."""
    items = load_json_array(path, label="exemptions")
    return [
        _validate_exemption(item, index=index, source=path)
        for index, item in enumerate(items)
    ]


def _has_inline_pragma(lineno: int, *, lines: tuple[str, ...]) -> bool:
    return has_inline_pragma(
        lineno,
        lines,
        pragma_re=PRAGMA_RE,
        standalone_pragma_re=STANDALONE_PRAGMA_RE,
    )


def _to_engine_finding(finding: Finding) -> EngineFinding:
    return EngineFinding(
        path=f"{PYTHON_PREFIX}{finding.file}",
        line=finding.lineno,
        rule_id=RULE_ID,
        message=(
            f"{finding.qualified_symbol} calls subprocess.{finding.callee} "
            f"occurrence {finding.occurrence}; route through proc.Runner or document an exemption"
        ),
        qualified_symbol=finding.qualified_symbol,
        occurrence=finding.occurrence,
        occurrence_values=(("callee", finding.callee),),
    )


def _to_engine_gh_finding(finding: GhFinding) -> EngineFinding:
    return EngineFinding(
        path=f"{PYTHON_PREFIX}{finding.file}",
        line=finding.lineno,
        rule_id=GH_RULE_ID,
        message=(
            f"{finding.qualified_symbol} calls runner.run([gh, ...]) "
            f"occurrence {finding.occurrence}; use larch.git.gh"
        ),
        qualified_symbol=finding.qualified_symbol,
        occurrence=finding.occurrence,
    )


def build_rules(root: Path) -> tuple[LintRule, LintRule]:
    """Build the subprocess and gh engine rules closed over exemptions for ``root``."""
    exemptions = load_exemptions(root / "python" / EXEMPTIONS_FILENAME)
    exempt_files = frozenset(exemption["file"] for exemption in exemptions)

    def detect(source: SourceFile) -> list[EngineFinding]:
        if not source.is_python or not is_production_source_path(source.path):
            return []
        normalized_file = source.path.removeprefix(PYTHON_PREFIX)
        raw = findings_from_source(source.text, normalized_file=normalized_file)
        lines = source.lines
        return [
            _to_engine_finding(finding)
            for finding in raw
            if finding.file not in exempt_files
            and not _has_inline_pragma(finding.lineno, lines=lines)
        ]

    def detect_gh(source: SourceFile) -> list[EngineFinding]:
        if not source.is_python or not is_production_source_path(source.path):
            return []
        normalized_file = source.path.removeprefix(PYTHON_PREFIX)
        if normalized_file == GH_WRAPPER_RELPATH:
            return []
        raw = gh_findings_from_source(source.text, normalized_file=normalized_file)
        lines = source.lines
        return [
            _to_engine_gh_finding(finding)
            for finding in raw
            if not _has_inline_pragma(finding.lineno, lines=lines)
        ]

    rule = LintRule(
        rule_id=RULE_ID,
        description="Ratchet direct subprocess calls toward the proc.Runner seam",
        detect=detect,
        syntax_policy="skip",
        suppression_token=SUPPRESSION_TOKEN,
        allow_inline_suppression=False,
        pathspecs=("python",),
        source_filter=is_production_source_path,
        occurrence_baseline=True,
        occurrence_fields=("callee",),
        require_baseline=True,
        warn_matching_baseline=True,
    )
    gh_rule = LintRule(
        rule_id=GH_RULE_ID,
        description="Ratchet direct runner.run([gh, ...]) calls toward larch.git.gh",
        detect=detect_gh,
        syntax_policy="skip",
        suppression_token=SUPPRESSION_TOKEN,
        allow_inline_suppression=False,
        pathspecs=("python",),
        source_filter=is_production_source_path,
        occurrence_baseline=True,
        occurrence_fields=(),
        require_baseline=False,
        warn_matching_baseline=True,
    )
    return rule, gh_rule


CLI = RuleCli(
    prog="cli.py lint subprocess-via-runner",
    description=__doc__,
    baseline_filename=BASELINE_FILENAME,
    error_label="lint-subprocess-via-runner",
    scoped_paths=None,
    strict_stale=False,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry registered as ``python3 python/cli.py lint subprocess-via-runner``."""
    parsed = parse_lint_argv(argv if argv is not None else sys.argv[1:], cli=CLI)
    if parsed is None:
        return EXIT_ERROR
    root = Path(str(parsed.root)).resolve()
    try:
        rule, gh_rule = build_rules(root)
    except BaselineError as exc:
        print(f"{CLI.error_label}: {exc}", file=sys.stderr)
        return EXIT_ERROR
    baseline_path = root / "python" / BASELINE_FILENAME
    gh_baseline_path = root / "python" / GH_BASELINE_FILENAME
    write_baseline = bool(parsed.write)
    seed = cast("str | None", parsed.initial_reason)
    rc = run_rule(
        rule,
        root,
        proc.ProcRunner(),
        baseline_path=baseline_path,
        write_baseline=write_baseline,
        initial_reason=seed,
        strict_stale=False,
    )
    if write_baseline:
        gh_rc = run_rule(
            gh_rule,
            root,
            proc.ProcRunner(),
            baseline_path=gh_baseline_path,
            write_baseline=True,
            initial_reason=seed,
            strict_stale=False,
        )
    else:
        # The gh baseline is optional: treat an absent file as scan-only so a
        # stray direct gh call fails at exit 1 instead of erroring on a missing
        # required baseline.
        gh_destination = gh_baseline_path if gh_baseline_path.is_file() else None
        gh_rc = run_rule(
            gh_rule,
            root,
            proc.ProcRunner(),
            baseline_path=gh_destination,
            strict_stale=False,
        )
    return max(rc, gh_rc)


if __name__ == "__main__":
    raise SystemExit(main())
