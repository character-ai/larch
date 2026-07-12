"""Reject raw committed run-log corpus walkers outside ``run_log_corpus``.

Scans tracked Python under ``python/`` plus the in-scope skill scanner scripts
and fails when a new committed-corpus ``glob`` / ``rglob`` / ``walk`` /
``scandir``, copied classification triple-glob, or dual-manifest candidate loop
appears outside the shared owner. Validated per-run recursive inspection must
go through ``run_log_corpus`` helpers.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

TOOL_FAILURE_EXIT = 2
OWNER_RELPATH = "larch/report/run_log_corpus.py"
SKILL_SCANNERS = (
    "skills/fluff-analysis/scripts/fluff-analysis.py",
    "skills/voter-calibration/scripts/voter-calibration.py",
)
# Temporary exemptions while #7008 deletes these walker modules.
EXEMPT_RELPATHS = frozenset(
    {
        "larch/report/retro_fix_cursor.py",  # #7008 deletion target
        "larch/report/retro_v3_sweep.py",  # #7008 deletion target
        "larch/report/cleanup_implement_logs.py",  # #7008 deletion target
    }
)
EXCLUDED_DIR_PARTS = frozenset(
    {".git", "node_modules", ".venv", ".agents", "__pycache__", "larch-logs", "tests", "test"}
)
MANIFEST_NAMES = frozenset({"manifest.json", "run-manifest.json"})
CLASSIFICATION_GLOBS = (
    "design/*/plan-review/round-*/findings-classification.tsv",
    "implement/*/round-*/findings-classification.tsv",
    "review/*/review-findings-classification-round-*.tsv",
)
CORPUS_PATH_MARKERS = (
    "larch-logs",
    "log_root",
    "log_base",
    "logs_root",
    "impl_root",
    "design_root",
    "implement_root",
    "skill_dir",
    "skill_root",
)
SESSION_PATH_MARKERS = (
    "tmpdir",
    "implement_tmpdir",
    "design_tmpdir",
    "canonical_tmp",
    "session_tmpdir",
    "session_env",
)


@dataclass(frozen=True)
class Finding:
    file: str
    lineno: int
    rule: str
    message: str


def _repo_root_from_module() -> Path:
    return Path(__file__).resolve().parents[3]


def _tracked_python_relpaths(root: Path) -> list[str]:
    proc = subprocess.run(  # lint-subprocess-via-runner: ok lint utility calls git directly to enumerate tracked files; no proc.Runner needed
        ["git", "-C", str(root), "ls-files", "-z", "--", "python", *SKILL_SCANNERS],  # noqa: S607 - lint tool calls git to enumerate tracked files; partial path is intentional
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {proc.stderr.decode(errors='replace')}")
    paths: list[str] = []
    for chunk in proc.stdout.split(b"\0"):
        if not chunk:
            continue
        text = chunk.decode()
        if not text.endswith(".py"):
            continue
        paths.append(text)
    return sorted(paths)


def _normalize_scan_relpath(raw: str) -> str:
    normalized = raw.replace("\\", "/")
    if normalized.startswith("python/"):
        return normalized[len("python/") :]
    return normalized


def _is_excluded_relpath(relpath: str) -> bool:
    parts = Path(relpath).parts
    if any(part in EXCLUDED_DIR_PARTS for part in parts):
        return True
    name = Path(relpath).name
    return name.startswith("test_") or name.endswith("_test.py")


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _joined_str_contains(node: ast.AST, needle: str) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return needle in node.value
    if isinstance(node, ast.JoinedStr):
        return any(_joined_str_contains(value, needle) for value in node.values)
    if isinstance(node, ast.FormattedValue):
        return False
    return False


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _attr_root_name(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


def _looks_like_corpus_receiver(node: ast.AST) -> bool:
    text = ast.dump(node)
    if any(marker in text for marker in SESSION_PATH_MARKERS):
        return False
    return any(marker in text for marker in CORPUS_PATH_MARKERS)


def _is_classification_glob_arg(arg: ast.AST | None) -> bool:
    value = _const_str(arg)
    if value is None:
        return False
    return any(pattern in value for pattern in CLASSIFICATION_GLOBS) or (
        "findings-classification" in value and ("design/" in value or "implement/" in value or "review/" in value)
    )


def _iter_loop_targets(node: ast.AST) -> Iterable[str]:
    if isinstance(node, ast.Name):
        yield node.id
        return
    if isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            yield from _iter_loop_targets(elt)


class _Walker(ast.NodeVisitor):
    def __init__(self, *, relpath: str) -> None:
        self.relpath = relpath
        self.findings: list[Finding] = []
        self._manifest_loop_names: set[str] = set()
        self._corpus_aliases: set[str] = set()
        self._safe_run_aliases: set[str] = set()

    def _expr_is_safe_run(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._safe_run_aliases
        if isinstance(node, ast.Call) and _call_name(node) in {"str", "Path"} and node.args:
            return self._expr_is_safe_run(node.args[0])
        return False

    def _expr_is_corpus(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._corpus_aliases or _looks_like_corpus_receiver(node)
        if self._expr_is_safe_run(node):
            return False
        if _looks_like_corpus_receiver(node):
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self._expr_is_corpus(node.left)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            return self._expr_is_corpus(node.func.value)
        return False

    @staticmethod
    def _target_names(node: ast.AST) -> set[str]:
        return set(_iter_loop_targets(node))

    def _add(self, node: ast.AST, rule: str, message: str) -> None:
        self.findings.append(
            Finding(
                file=self.relpath,
                lineno=getattr(node, "lineno", 1),
                rule=rule,
                message=message,
            )
        )

    def visit_For(self, node: ast.For) -> None:
        iter_node = node.iter
        names: set[str] = set()
        if isinstance(iter_node, (ast.Tuple, ast.List)):
            for elt in iter_node.elts:
                value = _const_str(elt)
                if value in MANIFEST_NAMES:
                    names.update(_iter_loop_targets(node.target))
        elif isinstance(iter_node, ast.Call) and _call_name(iter_node) in {"tuple", "list"} and iter_node.args:
            first = iter_node.args[0]
            if isinstance(first, (ast.Tuple, ast.List)):
                for elt in first.elts:
                    value = _const_str(elt)
                    if value in MANIFEST_NAMES:
                        names.update(_iter_loop_targets(node.target))
        if names and self._loop_uses_both_manifests(node):
            self._add(
                node,
                "dual-manifest-loop",
                "use run_log_corpus metadata helpers instead of dual-manifest candidate loops",
            )
        if isinstance(iter_node, ast.Call) and _call_name(iter_node) == "safe_child_run_dirs":
            self._safe_run_aliases.update(self._target_names(node.target))
        self.generic_visit(node)

    def _track_assignment(self, node: ast.Assign | ast.AnnAssign) -> None:
        self.generic_visit(node)
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        names = set[str]().union(*(self._target_names(target) for target in targets))
        value = node.value
        if value is None:
            return
        if self._expr_is_safe_run(value):
            self._safe_run_aliases.update(names)
            self._corpus_aliases.difference_update(names)
        elif self._expr_is_corpus(value):
            self._corpus_aliases.update(names)
            self._safe_run_aliases.difference_update(names)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._track_assignment(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._track_assignment(node)

    def _loop_uses_both_manifests(self, node: ast.For) -> bool:
        seen: set[str] = set()
        for child in ast.walk(node):
            value = _const_str(child)
            if value in MANIFEST_NAMES:
                seen.add(value)
        return seen >= MANIFEST_NAMES

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        if name in {"glob", "rglob", "iglob"}:
            self._check_glob_call(node, name)
        elif name == "walk":
            root = _attr_root_name(node.func)
            if (root == "os" or (isinstance(node.func, ast.Attribute) and self._expr_is_corpus(node.func.value))) and self._walk_looks_like_corpus(node):
                self._add(
                    node,
                    "raw-walk",
                    "use run_log_corpus.safe_child_run_dirs / validated-run helpers instead of os.walk on corpus roots",
                )
        elif name == "scandir" and self._walk_looks_like_corpus(node):
            self._add(
                node,
                "raw-scandir",
                "use run_log_corpus.safe_child_run_dirs instead of os.scandir on corpus roots",
            )
        self.generic_visit(node)

    def _check_glob_call(self, node: ast.Call, name: str) -> None:
        pattern_arg = node.args[0] if node.args else None
        if _is_classification_glob_arg(pattern_arg):
            self._add(
                node,
                "classification-glob",
                "use run_log_corpus.discover_classifications / classification_tsv_paths",
            )
            return
        receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
        stdlib_glob = isinstance(receiver, ast.Name) and receiver.id == "glob"
        corpusish = False
        if receiver is not None and not stdlib_glob:
            corpusish = self._expr_is_corpus(receiver)
        if stdlib_glob and pattern_arg is not None:
            corpusish = self._expr_is_corpus(pattern_arg)
        pattern_text = _const_str(pattern_arg) or ""
        if name == "rglob" and corpusish:
            self._add(
                node,
                "raw-rglob",
                "use run_log_corpus validated-run helpers instead of Path.rglob on corpus roots",
            )
            return
        if corpusish and (
            pattern_text in {"*", "**"}
            or pattern_text.startswith("*/")
            or "larch-logs" in pattern_text
            or _joined_str_contains(pattern_arg or ast.Constant(value=""), "larch-logs")
            or any(
                _joined_str_contains(pattern_arg or ast.Constant(value=""), marker)
                for marker in ("implement/", "design/", "review/")
            )
            or (
                stdlib_glob
                and pattern_arg is not None
                and any(marker in ast.dump(pattern_arg) for marker in CORPUS_PATH_MARKERS)
                and not any(marker in ast.dump(pattern_arg) for marker in SESSION_PATH_MARKERS)
            )
        ):
            self._add(
                node,
                "raw-glob",
                "use run_log_corpus.safe_child_run_dirs instead of raw corpus Path.glob",
            )

    def _walk_looks_like_corpus(self, node: ast.Call) -> bool:
        if not node.args:
            return False
        return self._expr_is_corpus(node.args[0])


def scan_source(*, relpath: str, source: str) -> list[Finding]:
    try:
        tree = ast.parse(source, filename=relpath)
    except SyntaxError as exc:
        raise RuntimeError(f"invalid Python source: {relpath}: {exc}") from exc
    walker = _Walker(relpath=relpath)
    walker.visit(tree)
    return walker.findings


def collect_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for tracked in _tracked_python_relpaths(root):
        rel = _normalize_scan_relpath(tracked)
        if rel == OWNER_RELPATH or rel in EXEMPT_RELPATHS:
            continue
        if _is_excluded_relpath(rel) and not tracked.startswith("skills/"):
            continue
        path = root / tracked
        if path.is_symlink():
            raise RuntimeError(f"tracked Python source is a symlink: {tracked}")
        if not path.is_file():
            raise RuntimeError(f"tracked Python source is not a regular file: {tracked}")
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"unreadable Python source: {tracked}: {exc}") from exc
        findings.extend(scan_source(relpath=tracked, source=source))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py lint run-log-walkers", description=__doc__)
    _ = parser.add_argument("--root", default=str(_repo_root_from_module()))
    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as exc:
        return int(exc.code or 0)
    root = Path(args.root)
    if not root.is_dir():
        print(f"lint-run-log-walkers: --root is not a directory: {root}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        findings = collect_findings(root.resolve())
    except RuntimeError as exc:
        print(f"lint-run-log-walkers: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if not findings:
        return 0
    print("lint-run-log-walkers: raw committed run-log walkers must use run_log_corpus:", file=sys.stderr)
    for finding in findings:
        print(f"  {finding.file}:{finding.lineno}: [{finding.rule}] {finding.message}", file=sys.stderr)
    print(
        "Remediation: call larch.report.run_log_corpus helpers "
        "(safe_child_run_dirs, metadata helpers, classification discovery, "
        "validated-run walkers).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
