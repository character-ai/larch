"""Ratchet direct subprocess calls toward the proc.Runner seam.

Scans production modules under python/**/*.py for direct calls to selected
subprocess APIs. Existing debt is grandfathered in
subprocess-via-runner-baseline.json with a required reason per row. New direct
calls fail unless covered by an explicit file exemption or an inline pragma.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "subprocess-via-runner-baseline.json"
EXEMPTIONS_FILENAME = "subprocess-via-runner-exemptions.json"
ALLOWED_CALLEES = frozenset({"run", "Popen", "check_output", "call"})
BASELINE_KEYS = frozenset({"file", "qualified_symbol", "callee", "occurrence", "reason"})
EXEMPTION_KEYS = frozenset({"file", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
# Runner module's current home, relative to python/ (posix-normalized). The flat
# python/ tree is migrating to a package layout (larch/core/ is the first subdir);
# update this single constant when proc.py moves again.
RUNNER_RELPATH = "larch/core/proc.py"
MODULE_SYMBOL = "<module>"
PRAGMA_RE = re.compile(r"#\s*lint-subprocess-via-runner:\s*ok\s+(\S.*)$")
STANDALONE_PRAGMA_RE = re.compile(r"^\s*#\s*lint-subprocess-via-runner:\s*ok\s+(\S.*)$")


class Record(TypedDict):
    file: str
    qualified_symbol: str
    callee: str
    occurrence: int
    reason: str


class Exemption(TypedDict):
    file: str
    reason: str


class BaselineError(ValueError):
    """Raised when a baseline or exemption file cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    file: str
    qualified_symbol: str
    callee: str
    occurrence: int
    lineno: int

    def key(self) -> tuple[str, str, str, int]:
        return (self.file, self.qualified_symbol, self.callee, self.occurrence)


def normalize_file_path(raw: str) -> str:
    """Return a normalized POSIX path relative to python/."""
    normalized = raw.replace("\\", "/")
    marker = "/python/"
    if marker in normalized:
        normalized = normalized.rsplit(marker, maxsplit=1)[1]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized == "python":
        return ""
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


def iter_source_files(python_dir: Path) -> list[Path]:
    """Return recursively discovered production Python files, sorted."""
    result: list[Path] = []
    for path in sorted(python_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink() or is_exempt_path(path):
            continue
        normalized = path.relative_to(python_dir).as_posix()
        if normalized == RUNNER_RELPATH:
            continue
        result.append(path)
    return result


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
    return [node for _, node in indexed]


def _subprocess_callee(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in ALLOWED_CALLEES:
        return None
    if not isinstance(func.value, ast.Name) or func.value.id != "subprocess":
        return None
    return func.attr


def _collect_scope(
    body: list[ast.stmt],
    *,
    prefix: tuple[str, ...],
    normalized_file: str,
    findings: list[Finding],
) -> None:
    occurrence = 0
    symbol = _qualified(prefix)

    def walk(node: ast.AST) -> None:
        nonlocal occurrence
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                normalized_file=normalized_file,
                findings=findings,
            )
            return
        if isinstance(node, ast.ClassDef):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                normalized_file=normalized_file,
                findings=findings,
            )
            return
        callee = _subprocess_callee(node)
        if callee is not None:
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
        for child in _ordered_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(path: Path, *, python_dir: Path) -> list[Finding]:
    """Return all direct subprocess findings for one source file."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    findings: list[Finding] = []
    _collect_scope(
        tree.body,
        prefix=(),
        normalized_file=path.relative_to(python_dir).as_posix(),
        findings=findings,
    )
    return findings


def _record_key(record: Record) -> tuple[str, str, str, int]:
    return (
        record["file"],
        record["qualified_symbol"],
        record["callee"],
        record["occurrence"],
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
    callee = record["callee"]
    occurrence = record["occurrence"]
    reason = record["reason"]
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(callee, str) or callee not in ALLOWED_CALLEES:
        raise BaselineError(f"{source}: record {index} has invalid callee")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "qualified_symbol": qualified_symbol,
        "callee": callee,
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


def _validate_exemption(item: object, *, index: int, source: Path) -> Exemption:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: exemption {index} must be an object")
    record = cast("dict[str, object]", item)
    if set(record) != set(EXEMPTION_KEYS):
        raise BaselineError(f"{source}: exemption {index} must have exactly {sorted(EXEMPTION_KEYS)}")
    file_name = _validate_normalized_file(record["file"], source=source, index=index, kind="exemption")
    reason = record["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: exemption {index} has invalid reason")
    return {"file": file_name, "reason": reason}


def load_exemptions(path: Path) -> list[Exemption]:
    """Load optional file-level exemptions. Missing file means no exemptions."""
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BaselineError(f"{path}: cannot read exemptions: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: exemptions must be a top-level JSON array")
    items = cast("list[object]", data)
    return [
        _validate_exemption(item, index=index, source=path)
        for index, item in enumerate(items)
    ]


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


def _collect_all(python_dir: Path) -> tuple[list[Finding], dict[str, tuple[str, ...]]]:
    findings: list[Finding] = []
    source_lines_by_file: dict[str, tuple[str, ...]] = {}
    for path in iter_source_files(python_dir):
        normalized = path.relative_to(python_dir).as_posix()
        source_lines_by_file[normalized] = _source_lines(path)
        findings.extend(scan_file(path, python_dir=python_dir))
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
    exemptions: list[Exemption],
    source_lines_by_file: dict[str, tuple[str, ...]],
) -> list[Finding]:
    exempt_files = frozenset(exemption["file"] for exemption in exemptions)
    return [
        finding
        for finding in findings
        if finding.file not in exempt_files
        and not _has_inline_pragma(finding, source_lines_by_file=source_lines_by_file)
    ]


def format_key(key: tuple[str, str, str, int]) -> str:
    file_name, qualified_symbol, callee, occurrence = key
    return f"{file_name}:{qualified_symbol} {callee}#{occurrence}"


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
    if baseline_path.is_file():
        preserved = {_record_key(record): record["reason"] for record in load_baseline(baseline_path)}
    reason_default = initial_reason.strip() if initial_reason is not None else None
    records: list[Record] = []
    missing: list[str] = []
    for finding in sorted(findings, key=_finding_sort_key):
        reason = preserved.get(finding.key())
        if reason is None and reason_default:
            reason = reason_default
        if reason is None:
            missing.append(format_key(finding.key()))
            continue
        records.append(
            {
                "file": finding.file,
                "qualified_symbol": finding.qualified_symbol,
                "callee": finding.callee,
                "occurrence": finding.occurrence,
                "reason": reason,
            }
        )
    if missing:
        joined = "\n  ".join(missing)
        raise BaselineError(
            "missing baseline reasons for live subprocess findings:\n  " + joined
        )
    return records


def _run_write(
    python_dir: Path,
    *,
    baseline_path: Path,
    exemptions: list[Exemption],
    initial_reason: str | None,
) -> int:
    try:
        all_findings, source_lines_by_file = _collect_all(python_dir)
        duplicate = _check_duplicate_live(all_findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
        findings = _filter_suppressed(
            all_findings,
            exemptions=exemptions,
            source_lines_by_file=source_lines_by_file,
        )
        records = _records_for_write(
            findings,
            baseline_path=baseline_path,
            initial_reason=initial_reason,
        )
    except BaselineError as exc:
        print(f"lint-subprocess-via-runner: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(
        f"lint-subprocess-via-runner: wrote {len(records)} records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check(
    python_dir: Path,
    *,
    baseline_path: Path,
    exemptions: list[Exemption],
) -> int:
    try:
        baseline_records = load_baseline(baseline_path)
        all_findings, source_lines_by_file = _collect_all(python_dir)
        duplicate = _check_duplicate_live(all_findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
    except BaselineError as exc:
        print(f"lint-subprocess-via-runner: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys = frozenset(_record_key(record) for record in baseline_records)
    live_findings = _filter_suppressed(
        all_findings,
        exemptions=exemptions,
        source_lines_by_file=source_lines_by_file,
    )
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
            f"{finding.file}:{finding.qualified_symbol} calls subprocess.{finding.callee} "
            f"occurrence {finding.occurrence} (baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.file}:{finding.qualified_symbol} calls subprocess.{finding.callee} "
            f"occurrence {finding.occurrence}; route through proc.Runner or document an exemption",
            file=sys.stderr,
        )
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint subprocess-via-runner", description=__doc__
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
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


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = Path(str(parsed.root)).resolve()
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(
            f"lint-subprocess-via-runner: python directory not found: {python_dir}",
            file=sys.stderr,
        )
        return TOOL_FAILURE_EXIT
    baseline_path = python_dir / BASELINE_FILENAME
    exemptions_path = python_dir / EXEMPTIONS_FILENAME
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-subprocess-via-runner: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        exemptions = load_exemptions(exemptions_path)
    except BaselineError as exc:
        print(f"lint-subprocess-via-runner: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(
            python_dir,
            baseline_path=baseline_path,
            exemptions=exemptions,
            initial_reason=initial_reason,
        )
    return _run_check(python_dir, baseline_path=baseline_path, exemptions=exemptions)


if __name__ == "__main__":
    raise SystemExit(main())
