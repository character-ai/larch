"""Ratchet wire-artifact readers toward paired production writers.

Scans a curated manifest of wire artifact names and fails when production
``python/larch`` code reads an artifact that has no production writer evidence in
Python or shell sources. Existing one-sided artifacts are grandfathered in a
reason-bearing baseline.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from functools import cache
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict, cast

TOOL_FAILURE_EXIT = 2
MANIFEST_FILENAME = "wire-artifact-manifest.json"
BASELINE_FILENAME = "wire-artifact-pairing-baseline.json"
MANIFEST_KEYS = frozenset({"artifact", "kind"})
BASELINE_KEYS = frozenset({"artifact", "side", "reason"})
SIDES = frozenset({"external-writer", "external-reader", "intentionally-one-sided"})
PY_EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
PY_EXCLUDED_PREFIXES = (
    ("tests",),
    ("test_fixtures",),
)
SHELL_WRITE_RE = re.compile(
    r"(^|[;&|\s])(touch|tee|mv)\s|(^|[^<>])>>?[^>]|(^|[;&|\s])printf\s.*>>?"
)
PY_WRITE_NAMES = frozenset({"write_text", "touch", "atomic_write", "_touch"})
PY_OPEN_WRITE_MODES = frozenset({"w", "a", "x", "wb", "ab", "xb", "wt", "at", "xt"})
OPEN_MODE_ARG_INDEX = 1
OPEN_MIN_ARGS_WITH_MODE = 2
BATCH_INFO_RE = re.compile(r'"(?P<slug>[A-Za-z0-9_.-]+)"\s*:\s*BatchInfo\(\s*"(?P<ext>\.[A-Za-z0-9_.-]+)"')
Kind = Literal["basename", "relative_path"]


class ManifestRow(TypedDict):
    artifact: str
    kind: Kind


class BaselineRow(TypedDict):
    artifact: str
    side: str
    reason: str


@dataclass(frozen=True)
class Finding:
    kind: Kind
    artifact: str
    readers: int
    writers: int

    def key(self) -> tuple[str, str]:
        return (self.kind, self.artifact)


class BaselineError(ValueError):
    """Raised when a manifest or baseline file cannot be trusted."""


def _json_load(path: Path, *, label: str) -> list[object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BaselineError(f"{path}: cannot read {label}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: {label} must be a top-level JSON array")
    return cast("list[object]", data)


def _valid_relative_path(value: str) -> bool:
    parts = value.split("/")
    return bool(value) and not value.startswith("/") and "" not in parts and "." not in parts and ".." not in parts


def _validate_manifest_row(item: object, *, index: int, source: Path) -> ManifestRow:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: manifest row {index} must be an object")
    record = cast("dict[str, object]", item)
    if set(record) != set(MANIFEST_KEYS):
        raise BaselineError(f"{source}: manifest row {index} must have exactly {sorted(MANIFEST_KEYS)}")
    artifact = record["artifact"]
    kind = record["kind"]
    if not isinstance(artifact, str) or not artifact:
        raise BaselineError(f"{source}: manifest row {index} has invalid artifact")
    if kind not in ("basename", "relative_path"):
        raise BaselineError(f"{source}: manifest row {index} has invalid kind")
    if kind == "basename" and ("/" in artifact or artifact in {".", ".."}):
        raise BaselineError(f"{source}: manifest row {index} has invalid basename artifact")
    if kind == "relative_path" and not _valid_relative_path(artifact):
        raise BaselineError(f"{source}: manifest row {index} has invalid relative_path artifact")
    return {"artifact": artifact, "kind": kind}


def load_manifest(path: Path) -> list[ManifestRow]:
    """Load and validate the artifact manifest."""
    rows = [_validate_manifest_row(item, index=index, source=path) for index, item in enumerate(_json_load(path, label="manifest"))]
    duplicate = _first_duplicate((row["kind"], row["artifact"]) for row in rows)
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate manifest identity {duplicate[0]}:{duplicate[1]}")
    return rows


def _validate_baseline_row(item: object, *, index: int, source: Path) -> BaselineRow:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: baseline row {index} must be an object")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: baseline row {index} must have exactly {sorted(BASELINE_KEYS)}")
    artifact = record["artifact"]
    side = record["side"]
    reason = record["reason"]
    if not isinstance(artifact, str) or not artifact:
        raise BaselineError(f"{source}: baseline row {index} has invalid artifact")
    if not isinstance(side, str) or side not in SIDES:
        raise BaselineError(f"{source}: baseline row {index} has invalid side")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: baseline row {index} has invalid reason")
    return {"artifact": artifact, "side": side, "reason": reason}


def load_baseline(path: Path) -> list[BaselineRow]:
    """Load and validate the committed baseline. Missing baseline means none."""
    if not path.is_file():
        return []
    rows = [_validate_baseline_row(item, index=index, source=path) for index, item in enumerate(_json_load(path, label="baseline"))]
    duplicate = _first_duplicate((row["artifact"],) for row in rows)
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate baseline identity {duplicate[0]}")
    return rows


def _first_duplicate(keys: Iterable[tuple[str, ...]]) -> tuple[str, ...] | None:
    seen: set[tuple[str, ...]] = set()
    for key in keys:
        if key in seen:
            return key
        seen.add(key)
    return None


def _is_excluded_python_path(relative: Path) -> bool:
    if PY_EXCLUDED_DIRS.intersection(relative.parts):
        return True
    return any(relative.parts[: len(prefix)] == prefix for prefix in PY_EXCLUDED_PREFIXES)


def _iter_python_files(root: Path, *, under_larch: bool) -> list[Path]:
    base = root / "python" / "larch" if under_larch else root / "python"
    if not base.is_dir():
        return []
    result: list[Path] = []
    for path in sorted(base.rglob("*.py")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root / "python")
        if _is_excluded_python_path(relative):
            continue
        result.append(path)
    return result


def _iter_shell_writer_files(root: Path) -> list[Path]:
    result: list[Path] = []
    scripts_dir = root / "scripts"
    if scripts_dir.is_dir():
        result.extend(
            path
            for path in sorted(scripts_dir.rglob("*"))
            if path.is_file() and not path.is_symlink() and not path.name.startswith("test-")
        )
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for script_dir in sorted(skills_dir.glob("*/scripts")):
            result.extend(
                path
                for path in sorted(script_dir.rglob("*"))
                if path.is_file() and not path.is_symlink() and not path.name.startswith("test-")
            )
    return result


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _artifact_token(row: ManifestRow) -> str:
    return row["artifact"]


@cache
def _basename_artifact_pattern(artifact: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_.-]){re.escape(artifact)}(?![A-Za-z0-9_.-])")


@cache
def _relative_path_artifact_pattern(artifact: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in artifact.split("/") if part]
    if not parts:
        return re.compile(r"^$")
    return re.compile(r".*?".join(parts), re.DOTALL)


def _mentions_artifact(text: str, row: ManifestRow) -> bool:
    artifact = _artifact_token(row)
    if row["kind"] == "basename":
        return _basename_artifact_pattern(artifact).search(text) is not None
    parts = [part for part in artifact.split("/") if part]
    return (
        artifact in text
        or f"/{artifact}" in text
        or all(part in text for part in parts)
        or _relative_path_artifact_pattern(artifact).search(text) is not None
    )


def _python_call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _literal_open_write_mode(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value) in PY_OPEN_WRITE_MODES
    if len(node.args) >= OPEN_MIN_ARGS_WITH_MODE:
        mode_arg = node.args[OPEN_MODE_ARG_INDEX]
        if isinstance(mode_arg, ast.Constant):
            return str(mode_arg.value) in PY_OPEN_WRITE_MODES
    return False


def _python_call_writes(name: str) -> bool:
    return (
        name in PY_WRITE_NAMES
        or name.startswith(("_write_", "_atomic_"))
        or name.endswith("_atomic")
        or "atomic_write" in name
    )


def _python_scope_lines(*, source: str, lines: list[str], parent_map: dict[int, ast.AST], node: ast.AST) -> str:
    scope: ast.AST | None = node
    while scope is not None and not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
        scope = parent_map.get(id(scope))

    if scope is None:
        return source
    start = getattr(scope, "lineno", 1) - 1 if not isinstance(scope, ast.Module) else 0
    end = getattr(scope, "end_lineno", len(source.splitlines()))
    return "\n".join(lines[max(start, 0) : min(len(lines), end)])


def _python_has_write_call(source: str, *, row: ManifestRow) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    parent_map: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[id(child)] = parent
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _python_call_name(node)
        if name is None or (name != "open" and not _python_call_writes(name)):
            continue
        if name == "open" and not _literal_open_write_mode(node):
            continue
        scope_text = _python_scope_lines(source=source, lines=lines, parent_map=parent_map, node=node)
        if _mentions_artifact(scope_text, row):
            return True
    return False


def _shell_line_writes_artifact(line: str, row: ManifestRow) -> bool:
    artifact = _artifact_token(row)

    def matches_artifact(text: str) -> bool:
        if row["kind"] == "basename":
            return _basename_artifact_pattern(artifact).search(text) is not None
        return artifact in text or f"/{artifact}" in text

    if re.search(r"(^|[;&|\s])touch\b", line) and matches_artifact(line):
        return True
    if re.search(r"(^|[;&|\s])tee\b", line) and matches_artifact(line):
        return True
    if re.search(r"(^|[;&|\s])mv\b", line):
        mv_tail = line.split("mv", 1)[1]
        mv_targets = [token for token in mv_tail.split() if token and not token.startswith("-")]
        if mv_targets and matches_artifact(mv_targets[-1]):
            return True
    redirect_index = max(line.rfind(">>"), line.rfind(">"))
    if redirect_index >= 0:
        tail = line[redirect_index + (2 if line[redirect_index : redirect_index + 2] == ">>" else 1) :]
        if matches_artifact(tail):
            return True
    return False


def _batch_artifacts(root: Path) -> set[str]:
    artifacts: set[str] = set()
    for path in _iter_python_files(root, under_larch=False):
        text = _read_text(path)
        if "BatchInfo" not in text:
            continue
        for match in BATCH_INFO_RE.finditer(text):
            artifacts.add(f"{match.group('slug')}{match.group('ext')}")
    return artifacts


def _count_readers(root: Path, row: ManifestRow) -> int:
    return sum(1 for path in _iter_python_files(root, under_larch=True) if _mentions_artifact(_read_text(path), row))


def _count_writers(root: Path, row: ManifestRow, *, batch_artifacts: set[str]) -> int:
    writers = 0
    artifact = row["artifact"]
    if row["kind"] == "basename" and artifact in batch_artifacts:
        writers += 1
    for path in _iter_python_files(root, under_larch=False):
        if _python_has_write_call(_read_text(path), row=row):
            writers += 1
    for path in _iter_shell_writer_files(root):
        text = _read_text(path)
        for line in text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if _shell_line_writes_artifact(line, row):
                writers += 1
                break
    return writers


def collect_findings(root: Path, manifest_rows: list[ManifestRow]) -> list[Finding]:
    """Return manifest artifacts with reader evidence but no writer evidence."""
    batch_artifacts = _batch_artifacts(root)
    findings: list[Finding] = []
    for row in manifest_rows:
        readers = _count_readers(root, row)
        writers = _count_writers(root, row, batch_artifacts=batch_artifacts)
        if readers > 0 and writers == 0:
            findings.append(Finding(row["kind"], row["artifact"], readers, writers))
    return sorted(findings, key=lambda finding: finding.key())


def serialize_baseline(rows: list[BaselineRow]) -> str:
    ordered = sorted(rows, key=lambda row: row["artifact"])
    return json.dumps(ordered, indent=2) + "\n"


def _records_for_write(
    findings: list[Finding],
    *,
    baseline_rows: list[BaselineRow],
    initial_reason: str | None,
) -> list[BaselineRow]:
    preserved = {row["artifact"]: row for row in baseline_rows}
    default_reason = initial_reason.strip() if initial_reason is not None else None
    records: list[BaselineRow] = []
    missing: list[str] = []
    for finding in findings:
        old = preserved.get(finding.artifact)
        if old is not None:
            records.append(old)
        elif default_reason:
            records.append({"artifact": finding.artifact, "side": "intentionally-one-sided", "reason": default_reason})
        else:
            missing.append(f"{finding.kind}:{finding.artifact}")
    if missing:
        raise BaselineError("missing baseline reasons for live wire artifacts:\n  " + "\n  ".join(missing))
    return records


def _run_write(root: Path, *, manifest_path: Path, baseline_path: Path, initial_reason: str | None) -> int:
    try:
        manifest_rows = load_manifest(manifest_path)
        baseline_rows = load_baseline(baseline_path)
        findings = collect_findings(root, manifest_rows)
        records = _records_for_write(findings, baseline_rows=baseline_rows, initial_reason=initial_reason)
    except BaselineError as exc:
        print(f"lint-wire-artifact-pairing: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(f"lint-wire-artifact-pairing: wrote {len(records)} records to {baseline_path}", file=sys.stderr)
    return 0


def _run_check(root: Path, *, manifest_path: Path, baseline_path: Path) -> int:
    try:
        manifest_rows = load_manifest(manifest_path)
        baseline_rows = load_baseline(baseline_path)
        baseline_artifacts = frozenset(row["artifact"] for row in baseline_rows)
        findings = collect_findings(root, manifest_rows)
    except BaselineError as exc:
        print(f"lint-wire-artifact-pairing: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    new_findings = [finding for finding in findings if finding.artifact not in baseline_artifacts]
    warned = [finding for finding in findings if finding.artifact in baseline_artifacts]
    for finding in warned:
        print(
            f"warning: {finding.kind}:{finding.artifact} has reader evidence but no production writer (baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.kind}:{finding.artifact} has reader evidence but no production writer; add a writer or baseline a one-sided artifact",
            file=sys.stderr,
        )
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py lint wire-artifact-pairing", description=__doc__)
    _ = parser.add_argument("positional_root", nargs="?", help="Optional repository root.")
    _ = parser.add_argument("--root", help="Repository root (overrides positional root).")
    _ = parser.add_argument("--write", action="store_true", help=f"Regenerate {BASELINE_FILENAME} from live findings.")
    _ = parser.add_argument("--initial-reason", help="Reason used for new live findings during --write.")
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
    root_text = cast("str | None", parsed.root) or cast("str | None", parsed.positional_root)
    root = Path(root_text).resolve() if root_text else Path(__file__).resolve().parents[3]
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(f"lint-wire-artifact-pairing: python directory not found: {python_dir}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    manifest_path = python_dir / MANIFEST_FILENAME
    baseline_path = python_dir / BASELINE_FILENAME
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-wire-artifact-pairing: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(root, manifest_path=manifest_path, baseline_path=baseline_path, initial_reason=initial_reason)
    return _run_check(root, manifest_path=manifest_path, baseline_path=baseline_path)


if __name__ == "__main__":
    raise SystemExit(main())
