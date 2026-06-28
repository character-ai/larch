"""Ratchet cross-package import direction toward the larch layering contract.

Scans production modules under python/larch/**/*.py for imports that violate
the package-tier ordering: leaf utils (tier 0) -> larch.core (tier 1) ->
domain packages (tier 2) -> larch.cli (tier 3). A module in tier N must not
import from a package in tier M where M > N. Existing violations are
grandfathered in layering-baseline.json with a required reason per row.
New violations fail unless covered by an inline pragma.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "layering-baseline.json"
BASELINE_KEYS = frozenset({"file", "qualified_symbol", "imported_package", "occurrence", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
MODULE_SYMBOL = "<module>"
PRAGMA_RE = re.compile(r"#\s*lint-layering:\s*ok\s+(\S.*)$")
STANDALONE_PRAGMA_RE = re.compile(r"^\s*#\s*lint-layering:\s*ok\s+(\S.*)$")

# Tier 0: leaf utils (no outbound larch imports needed)
# Tier 1: larch.core
# Tier 2: domain packages
# Tier 3: larch.cli (top of the import DAG; nothing depends on it)
PACKAGE_TIER: dict[str, int] = {
    "larch": 0,
    "larch.errors": 0,
    "larch.io": 0,
    "larch.outcomes": 0,
    "larch.core": 1,
    "larch.agents": 2,
    "larch.calibration": 2,
    "larch.design": 2,
    "larch.git": 2,
    "larch.implement": 2,
    "larch.issue": 2,
    "larch.lint": 2,
    "larch.release": 2,
    "larch.rendering": 2,
    "larch.report": 2,
    "larch.research": 2,
    "larch.review": 2,
    "larch.state": 2,
    "larch.cli": 3,
}


class Record(TypedDict):
    file: str
    qualified_symbol: str
    imported_package: str
    occurrence: int
    reason: str


class BaselineError(ValueError):
    """Raised when a baseline file cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    imported_package: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, int]:
        return (self.file, self.qualified_symbol, self.imported_package, self.occurrence)


def normalize_file_path(raw: str) -> str:
    """Return a normalized POSIX path relative to python/."""
    normalized = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.removeprefix("python/")


def _validate_normalized_file(value: object, *, source: Path, index: int, kind: str) -> str:
    if not isinstance(value, str) or not value:
        raise BaselineError(f"{source}: {kind} {index} has invalid file")
    normalized = normalize_file_path(value)
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


def is_exempt_path(path: Path) -> bool:
    """Return whether a source file is outside production lint scope."""
    name = path.name
    return (name.startswith("test_") and name.endswith(".py")) or name in EXEMPT_FILENAMES


def iter_source_files(larch_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files under larch/, sorted."""
    result: list[Path] = []
    for path in sorted(larch_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink() or is_exempt_path(path):
            continue
        relative = path.relative_to(larch_dir.parent)
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        result.append(path)
    return result


def _importer_package(normalized_file: str) -> str | None:
    """Return the top-level larch package for a file's path, or None if not larch."""
    parts = normalized_file.split("/")
    if not parts or parts[0] != "larch":
        return None
    if not parts[1:]:
        return "larch"
    if not parts[2:]:
        basename = parts[1]
        if not basename.endswith(".py"):
            return None
        if basename == "__init__.py":
            return "larch"
        module_name = basename[:-3]
        return f"larch.{module_name}"
    subpkg = parts[1]
    return f"larch.{subpkg}"


def _top_level_package(module: str) -> str:
    """Extract the top-level larch sub-package, e.g. 'larch.core.config' -> 'larch.core'."""
    parts = module.split(".", 2)
    if parts[1:]:
        return f"{parts[0]}.{parts[1]}"
    return parts[0]


def _resolve_relative_package(importer_pkg: str, level: int, module: str | None) -> str | None:
    """Resolve a relative ImportFrom to an absolute dotted module name."""
    if level <= 0:
        return None
    parts = importer_pkg.split(".")
    ascend = level - 1
    if ascend > len(parts):
        return None
    base_parts = parts[: len(parts) - ascend] if ascend else parts
    if module:
        base_parts.extend(module.split("."))
    return ".".join(base_parts)


def _package_tier(pkg: str) -> int:
    """Return the tier for a package name; unknown larch.* sub-packages default to domain (2)."""
    if pkg in PACKAGE_TIER:
        return PACKAGE_TIER[pkg]
    if pkg.startswith("larch."):
        return 2
    return -1


def _importee_packages_from(node: ast.ImportFrom, *, importer_pkg: str) -> list[str]:
    """Return the list of top-level larch packages for an ImportFrom node."""
    if node.level and node.level > 0:
        resolved = _resolve_relative_package(importer_pkg, node.level, node.module)
        if resolved is None:
            return []
        if resolved == "larch" or resolved.startswith("larch."):
            return [_top_level_package(resolved)]
        return []
    module = node.module or ""
    if module == "larch":
        return [f"larch.{alias.name}" for alias in node.names]
    if module.startswith("larch."):
        return [_top_level_package(module)]
    return []


def _importee_packages(node: ast.stmt, *, importer_pkg: str) -> list[str]:
    """Return the list of top-level larch packages referenced by an import statement."""
    if isinstance(node, ast.Import):
        return [
            _top_level_package(alias.name)
            for alias in node.names
            if alias.name == "larch" or alias.name.startswith("larch.")
        ]
    if isinstance(node, ast.ImportFrom):
        return _importee_packages_from(node, importer_pkg=importer_pkg)
    return []


def _qualified(prefix: tuple[str, ...]) -> str:
    return ".".join(prefix) if prefix else MODULE_SYMBOL


def _ordered_child_nodes(node: ast.AST) -> list[ast.AST]:
    children = list(ast.iter_child_nodes(node))
    indexed = list(enumerate(children))
    indexed.sort(
        key=lambda item: (
            getattr(item[1], "lineno", 10**9),
            getattr(item[1], "col_offset", 10**9),
            item[0],
        )
    )
    return [n for _, n in indexed]


@dataclass
class _ScopeCtx:
    normalized_file: str
    importer_pkg: str
    importer_tier: int
    findings: list[Finding]


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    ctx: _ScopeCtx,
) -> None:
    symbol = _qualified(prefix)
    occurrence_by_importee: dict[str, int] = {}

    def walk(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scope(node.body, prefix=(*prefix, node.name), ctx=ctx)
            return
        if isinstance(node, ast.ClassDef):
            _collect_scope(node.body, prefix=(*prefix, node.name), ctx=ctx)
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            importee_pkgs = _importee_packages(node, importer_pkg=ctx.importer_pkg)
            for importee_pkg in importee_pkgs:
                importee_tier = _package_tier(importee_pkg)
                if importee_tier > ctx.importer_tier and ctx.importer_pkg != importee_pkg:
                    occurrence_by_importee[importee_pkg] = (
                        occurrence_by_importee.get(importee_pkg, 0) + 1
                    )
                    lineno = getattr(node, "lineno", 0)
                    ctx.findings.append(
                        Finding(
                            file=ctx.normalized_file,
                            qualified_symbol=symbol,
                            imported_package=importee_pkg,
                            occurrence=occurrence_by_importee[importee_pkg],
                            lineno=lineno if isinstance(lineno, int) else 0,
                        )
                    )
            return
        for child in _ordered_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(path: Path, *, python_dir: Path, importer_pkg: str, importer_tier: int) -> list[Finding]:
    """Return all layering violations for one source file."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    ctx = _ScopeCtx(
        normalized_file=path.relative_to(python_dir).as_posix(),
        importer_pkg=importer_pkg,
        importer_tier=importer_tier,
        findings=[],
    )
    _collect_scope(tree.body, prefix=(), ctx=ctx)
    return ctx.findings


def _record_key(record: Record) -> tuple[str, str, str, int]:
    return (
        record["file"],
        record["qualified_symbol"],
        record["imported_package"],
        record["occurrence"],
    )


def _relocation_key(item: Finding | Record) -> tuple[str, str, str, int]:
    if isinstance(item, Finding):
        return (
            Path(item.file).name,
            item.qualified_symbol,
            item.imported_package,
            item.occurrence,
        )
    return (
        Path(item["file"]).name,
        item["qualified_symbol"],
        item["imported_package"],
        item["occurrence"],
    )


def _finding_sort_key(finding: Finding) -> tuple[str, str, str, int]:
    return finding.key()


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name = _validate_normalized_file(record["file"], source=source, index=index, kind="record")
    qualified_symbol = record["qualified_symbol"]
    imported_package = record["imported_package"]
    occurrence = record["occurrence"]
    reason = record["reason"]
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(imported_package, str) or not imported_package.startswith("larch"):
        raise BaselineError(f"{source}: record {index} has invalid imported_package")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "qualified_symbol": qualified_symbol,
        "imported_package": imported_package,
        "occurrence": occurrence,
        "reason": reason,
    }


def load_baseline(path: Path) -> list[Record]:
    """Load and validate the committed baseline."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a top-level JSON array")
    items = cast("list[object]", data)
    records = [
        _validate_record(item, index=index, source=path)
        for index, item in enumerate(items)
    ]
    duplicate = _first_duplicate(_record_key(record) for record in records)
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate baseline identity {format_key(duplicate)}")
    return records


def _has_inline_pragma(
    finding: Finding, *, source_lines_by_file: dict[str, tuple[str, ...]]
) -> bool:
    lines = source_lines_by_file.get(finding.file, ())
    index = finding.lineno - 1
    if 0 <= index < len(lines) and PRAGMA_RE.search(lines[index]):
        return True
    previous = index - 1
    return 0 <= previous < len(lines) and STANDALONE_PRAGMA_RE.match(lines[previous]) is not None


def _source_lines(path: Path) -> tuple[str, ...]:
    try:
        return tuple(path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return ()


def _collect_all(
    python_dir: Path,
) -> tuple[list[Finding], dict[str, tuple[str, ...]]]:
    larch_dir = python_dir / "larch"
    findings: list[Finding] = []
    source_lines_by_file: dict[str, tuple[str, ...]] = {}
    for path in iter_source_files(larch_dir):
        normalized = path.relative_to(python_dir).as_posix()
        importer_pkg = _importer_package(normalized)
        if importer_pkg is None:
            continue
        importer_tier = _package_tier(importer_pkg)
        if importer_tier < 0:
            continue
        source_lines_by_file[normalized] = _source_lines(path)
        findings.extend(
            scan_file(path, python_dir=python_dir, importer_pkg=importer_pkg, importer_tier=importer_tier)
        )
    return findings, source_lines_by_file


def _first_duplicate(
    keys: Iterable[tuple[str, str, str, int]],
) -> tuple[str, str, str, int] | None:
    seen: set[tuple[str, str, str, int]] = set()
    for key in keys:
        if key in seen:
            return key
        seen.add(key)
    return None


def _check_duplicate_live(findings: list[Finding]) -> str | None:
    duplicate = _first_duplicate(finding.key() for finding in findings)
    if duplicate is None:
        return None
    return f"duplicate live identity {format_key(duplicate)}"


def _filter_suppressed(
    findings: list[Finding],
    *,
    source_lines_by_file: dict[str, tuple[str, ...]],
) -> list[Finding]:
    return [
        finding
        for finding in findings
        if not _has_inline_pragma(finding, source_lines_by_file=source_lines_by_file)
    ]


def format_key(key: tuple[str, str, str, int]) -> str:
    file_name, qualified_symbol, imported_package, occurrence = key
    return f"{file_name}:{qualified_symbol} {imported_package}#{occurrence}"


def serialize_baseline(records: list[Record]) -> str:
    """Return canonical sorted JSON for the baseline."""
    ordered = sorted(records, key=_record_key)
    return json.dumps(ordered, indent=2) + "\n"


def _records_for_write(
    findings: list[Finding],
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> list[Record]:
    preserved: dict[tuple[str, str, str, int], str] = {}
    baseline_relocation_counts: Counter[tuple[str, str, str, int]] = Counter()
    relocation_reasons: dict[tuple[str, str, str, int], str] = {}
    has_baseline = baseline_path.is_file()
    if has_baseline:
        baseline_records = load_baseline(baseline_path)
        preserved = {_record_key(record): record["reason"] for record in baseline_records}
        baseline_relocation_counts = Counter(_relocation_key(record) for record in baseline_records)
        relocation_reasons = {
            _relocation_key(record): record["reason"]
            for record in baseline_records
            if baseline_relocation_counts[_relocation_key(record)] == 1
        }
    live_relocation_counts = Counter(_relocation_key(finding) for finding in findings)
    reason_default = initial_reason.strip() if initial_reason is not None else None
    records: list[Record] = []
    missing: list[str] = []
    for finding in sorted(findings, key=_finding_sort_key):
        reason = preserved.get(finding.key())
        relocation_key = _relocation_key(finding)
        baseline_relocation_count = baseline_relocation_counts[relocation_key]
        live_relocation_count = live_relocation_counts[relocation_key]
        if (
            reason is None
            and baseline_relocation_count == 1
            and live_relocation_count == 1
        ):
            reason = relocation_reasons[relocation_key]
        elif reason is None and has_baseline and (
            baseline_relocation_count > 1 or live_relocation_count > 1
        ):
            raise BaselineError(
                "ambiguous relocation key for live layering finding "
                f"{format_key(finding.key())}"
            )
        if reason is None and reason_default:
            reason = reason_default
        if reason is None:
            missing.append(format_key(finding.key()))
            continue
        records.append(
            {
                "file": finding.file,
                "qualified_symbol": finding.qualified_symbol,
                "imported_package": finding.imported_package,
                "occurrence": finding.occurrence,
                "reason": reason,
            }
        )
    if missing:
        joined = "\n  ".join(missing)
        raise BaselineError(
            "missing baseline reasons for live layering findings:\n  " + joined
        )
    return records


def _run_write(
    python_dir: Path,
    *,
    baseline_path: Path,
    initial_reason: str | None,
) -> int:
    try:
        all_findings, source_lines_by_file = _collect_all(python_dir)
        duplicate = _check_duplicate_live(all_findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
        findings = _filter_suppressed(all_findings, source_lines_by_file=source_lines_by_file)
        records = _records_for_write(findings, baseline_path=baseline_path, initial_reason=initial_reason)
    except BaselineError as exc:
        print(f"lint-layering: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(f"lint-layering: wrote {len(records)} records to {baseline_path}", file=sys.stderr)
    return 0


def _run_check(
    python_dir: Path,
    *,
    baseline_path: Path,
) -> int:
    try:
        baseline_records = load_baseline(baseline_path)
        all_findings, source_lines_by_file = _collect_all(python_dir)
        duplicate = _check_duplicate_live(all_findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
    except BaselineError as exc:
        print(f"lint-layering: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys = frozenset(_record_key(record) for record in baseline_records)
    live_findings = _filter_suppressed(all_findings, source_lines_by_file=source_lines_by_file)
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
            f"{finding.file}:{finding.qualified_symbol} imports from {finding.imported_package} "
            f"occurrence {finding.occurrence} (baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.file}:{finding.qualified_symbol} imports from {finding.imported_package} "
            f"occurrence {finding.occurrence}; "
            "this violates the larch package layering contract — add a baseline entry with a reason or refactor",
            file=sys.stderr,
        )
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint layering", description=__doc__
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


def _resolve_python_dir(root: Path) -> Path | None:
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(f"lint-layering: python directory not found: {python_dir}", file=sys.stderr)
        return None
    larch_dir = python_dir / "larch"
    if not larch_dir.is_dir():
        print(f"lint-layering: larch directory not found: {larch_dir}", file=sys.stderr)
        return None
    return python_dir


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    python_dir = _resolve_python_dir(Path(str(parsed.root)).resolve())
    if python_dir is None:
        return TOOL_FAILURE_EXIT
    baseline_path = python_dir / BASELINE_FILENAME
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-layering: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(python_dir, baseline_path=baseline_path, initial_reason=initial_reason)
    if not baseline_path.is_file():
        print(
            f"lint-layering: baseline not found: {baseline_path}; "
            "run with --write --initial-reason '...' to generate",
            file=sys.stderr,
        )
        return TOOL_FAILURE_EXIT
    return _run_check(python_dir, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
