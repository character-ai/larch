"""Ratchet bare os.environ literals toward config.ENV_* constants.

Scans production modules under python/**/*.py for os.environ accesses whose string
literal already has a matching ENV_* constant in python/larch/core/config.py. Existing debt
is grandfathered in env-via-config-constant-baseline.json with a required reason
per row. New bare literals fail unless covered by an explicit exemption or an
inline pragma.
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
from typing import NotRequired, TypedDict, cast

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "env-via-config-constant-baseline.json"
EXEMPTIONS_FILENAME = "env-via-config-constant-exemptions.json"
BASELINE_KEYS = frozenset(
    {"file", "qualified_symbol", "env_name", "constant", "access", "occurrence", "reason"}
)
EXEMPTION_KEYS = frozenset({"file", "reason", "env_name", "constant"})
REQUIRED_EXEMPTION_KEYS = frozenset({"file", "reason"})
EXEMPT_FILENAMES = frozenset({"conftest.py", "test_support.py", "review_test_support.py"})
# Virtual-environment and vendored trees live under python/ but are not larch
# production modules; skip them so rglob never lints third-party packages.
EXCLUDED_DIRS = frozenset({".git", "node_modules", ".venv", ".agents", "__pycache__"})
# Config module's current home, relative to python/ (posix-normalized). The flat
# python/ tree is migrating to a package layout (larch/core/ is the first subdir);
# update this single constant when config.py moves again.
CONFIG_RELPATH = "larch/core/config.py"
ACCESS_KINDS = frozenset({"get", "subscript_load", "subscript_store"})
MODULE_SYMBOL = "<module>"
PRAGMA_RE = re.compile(r"#\s*lint-env-via-config-constant:\s*ok\s+(\S.*)$")
STANDALONE_PRAGMA_RE = re.compile(r"^\s*#\s*lint-env-via-config-constant:\s*ok\s+(\S.*)$")


class Record(TypedDict):
    file: str
    qualified_symbol: str
    env_name: str
    constant: str
    access: str
    occurrence: int
    reason: str


class Exemption(TypedDict):
    file: str
    reason: str
    env_name: NotRequired[str]
    constant: NotRequired[str]


class BaselineError(ValueError):
    """Raised when a baseline, exemption, or config file cannot be trusted."""


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
        relative = path.relative_to(python_dir)
        if EXCLUDED_DIRS.intersection(relative.parts):
            continue
        normalized = relative.as_posix()
        if normalized == CONFIG_RELPATH:
            continue
        result.append(path)
    return result


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
    occurrence = 0
    symbol = _qualified(prefix)

    def walk(node: ast.AST) -> None:
        nonlocal occurrence
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                normalized_file=normalized_file,
                env_constants=env_constants,
                findings=findings,
            )
            return
        if isinstance(node, ast.ClassDef):
            _collect_scope(
                node.body,
                prefix=(*prefix, node.name),
                normalized_file=normalized_file,
                env_constants=env_constants,
                findings=findings,
            )
            return
        access = _env_access(node)
        if access is not None:
            env_name, access_kind = access
            constant = env_constants.get(env_name)
            if constant is not None and not env_name.endswith("_SH"):
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
        for child in _ordered_child_nodes(node):
            walk(child)

    for statement in body:
        walk(statement)


def scan_file(path: Path, *, python_dir: Path, env_constants: dict[str, str]) -> list[Finding]:
    """Return all bare env literal findings for one source file."""
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
        env_constants=env_constants,
        findings=findings,
    )
    return findings


def _record_key(record: Record) -> tuple[str, str, str, str, str, int]:
    return (
        record["file"],
        record["qualified_symbol"],
        record["env_name"],
        record["constant"],
        record["access"],
        record["occurrence"],
    )


def _relocation_key(item: Finding | Record) -> tuple[str, str, str, str, str, int]:
    if isinstance(item, Finding):
        return (
            Path(item.file).name,
            item.qualified_symbol,
            item.env_name,
            item.constant,
            item.access,
            item.occurrence,
        )
    return (
        Path(item["file"]).name,
        item["qualified_symbol"],
        item["env_name"],
        item["constant"],
        item["access"],
        item["occurrence"],
    )


def _finding_sort_key(finding: Finding) -> tuple[str, str, str, str, str, int]:
    return finding.key()


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    file_name = _validate_normalized_file(record["file"], source=source, index=index, kind="record")
    qualified_symbol = record["qualified_symbol"]
    env_name = record["env_name"]
    constant = record["constant"]
    access = record["access"]
    occurrence = record["occurrence"]
    reason = record["reason"]
    if not isinstance(qualified_symbol, str) or not qualified_symbol:
        raise BaselineError(f"{source}: record {index} has invalid qualified_symbol")
    if not isinstance(env_name, str) or not env_name:
        raise BaselineError(f"{source}: record {index} has invalid env_name")
    if not isinstance(constant, str) or not constant.startswith("ENV_"):
        raise BaselineError(f"{source}: record {index} has invalid constant")
    if not isinstance(access, str) or access not in ACCESS_KINDS:
        raise BaselineError(f"{source}: record {index} has invalid access")
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        raise BaselineError(f"{source}: record {index} has invalid occurrence")
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {
        "file": file_name,
        "qualified_symbol": qualified_symbol,
        "env_name": env_name,
        "constant": constant,
        "access": access,
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


def _source_lines(path: Path) -> tuple[str, ...]:
    try:
        return tuple(path.read_text(encoding="utf-8").splitlines())
    except OSError:
        return ()


def _collect_all(
    python_dir: Path, *, env_constants: dict[str, str]
) -> tuple[list[Finding], dict[str, tuple[str, ...]]]:
    findings: list[Finding] = []
    source_lines_by_file: dict[str, tuple[str, ...]] = {}
    for path in iter_source_files(python_dir):
        normalized = path.relative_to(python_dir).as_posix()
        source_lines_by_file[normalized] = _source_lines(path)
        findings.extend(scan_file(path, python_dir=python_dir, env_constants=env_constants))
    return findings, source_lines_by_file


def _first_duplicate(
    keys: Iterable[tuple[str, str, str, str, str, int]],
) -> tuple[str, str, str, str, str, int] | None:
    seen: set[tuple[str, str, str, str, str, int]] = set()
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
    return [
        finding
        for finding in findings
        if not any(
            _exemption_matches(finding=finding, exemption=exemption)
            for exemption in exemptions
        )
        and not _has_inline_pragma(finding, source_lines_by_file=source_lines_by_file)
    ]


def format_key(key: tuple[str, str, str, str, str, int]) -> str:
    file_name, qualified_symbol, env_name, constant, access, occurrence = key
    return f"{file_name}:{qualified_symbol} {env_name}/{constant} {access}#{occurrence}"


def _format_relocation_key(key: tuple[str, str, str, str, str, int]) -> str:
    file_name, qualified_symbol, env_name, constant, access, occurrence = key
    return f"{file_name}:{qualified_symbol} {env_name}/{constant} {access}#{occurrence}"


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
    preserved: dict[tuple[str, str, str, str, str, int], str] = {}
    baseline_relocation_counts: Counter[tuple[str, str, str, str, str, int]] = Counter()
    relocation_reasons: dict[tuple[str, str, str, str, str, int], str] = {}
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
                "ambiguous relocation key for live env finding "
                f"{format_key(finding.key())}: {_format_relocation_key(relocation_key)}"
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
                "env_name": finding.env_name,
                "constant": finding.constant,
                "access": finding.access,
                "occurrence": finding.occurrence,
                "reason": reason,
            }
        )
    if missing:
        joined = "\n  ".join(missing)
        raise BaselineError("missing baseline reasons for live env findings:\n  " + joined)
    return records


def _run_write(
    python_dir: Path,
    *,
    baseline_path: Path,
    exemptions: list[Exemption],
    env_constants: dict[str, str],
    initial_reason: str | None,
) -> int:
    try:
        all_findings, source_lines_by_file = _collect_all(python_dir, env_constants=env_constants)
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
        print(f"lint-env-via-config-constant: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    _ = baseline_path.write_text(serialize_baseline(records), encoding="utf-8")
    print(
        f"lint-env-via-config-constant: wrote {len(records)} records to {baseline_path}",
        file=sys.stderr,
    )
    return 0


def _run_check(
    python_dir: Path,
    *,
    baseline_path: Path,
    exemptions: list[Exemption],
    env_constants: dict[str, str],
) -> int:
    try:
        baseline_records = load_baseline(baseline_path)
        all_findings, source_lines_by_file = _collect_all(python_dir, env_constants=env_constants)
        duplicate = _check_duplicate_live(all_findings)
        if duplicate is not None:
            raise BaselineError(duplicate)
    except BaselineError as exc:
        print(f"lint-env-via-config-constant: {exc}", file=sys.stderr)
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
            f"{finding.file}:{finding.qualified_symbol} uses os.environ literal {finding.env_name!r} "
            f"for {finding.constant} access {finding.access} occurrence {finding.occurrence} (baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{finding.file}:{finding.qualified_symbol} uses os.environ literal {finding.env_name!r} "
            f"for {finding.constant} access {finding.access} occurrence {finding.occurrence}; "
            "use the config constant or document an exemption",
            file=sys.stderr,
        )
    return 1 if new_findings else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint env-via-config-constant", description=__doc__
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


def _allow_duplicate_policy(config_path: Path) -> bool:
    """Allow first-sorted-wins only for this checkout's live config.py."""
    try:
        live_config = Path(__file__).resolve().parent.joinpath(*CONFIG_RELPATH.split("/"))
        return config_path.resolve() == live_config.resolve()
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = Path(str(parsed.root)).resolve()
    python_dir = root / "python"
    if not python_dir.is_dir():
        print(
            f"lint-env-via-config-constant: python directory not found: {python_dir}",
            file=sys.stderr,
        )
        return TOOL_FAILURE_EXIT
    baseline_path = python_dir / BASELINE_FILENAME
    exemptions_path = python_dir / EXEMPTIONS_FILENAME
    config_path = python_dir.joinpath(*CONFIG_RELPATH.split("/"))
    initial_reason = cast("str | None", parsed.initial_reason)
    if initial_reason is not None and not initial_reason.strip():
        print("lint-env-via-config-constant: --initial-reason must be non-empty", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    try:
        exemptions = load_exemptions(exemptions_path)
        env_constants = parse_config_constants(
            config_path,
            allow_duplicate_values=_allow_duplicate_policy(config_path),
        )
    except BaselineError as exc:
        print(f"lint-env-via-config-constant: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    if bool(parsed.write):
        return _run_write(
            python_dir,
            baseline_path=baseline_path,
            exemptions=exemptions,
            env_constants=env_constants,
            initial_reason=initial_reason,
        )
    return _run_check(
        python_dir,
        baseline_path=baseline_path,
        exemptions=exemptions,
        env_constants=env_constants,
    )


if __name__ == "__main__":
    raise SystemExit(main())
