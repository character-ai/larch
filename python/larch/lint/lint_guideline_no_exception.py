"""Flag no-exception guideline entries that should be promoted or baselined."""
# pylint: disable=no-member

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from larch.core.architectural_guidelines import (
    GUIDELINE_HEADING_RE,
    GUIDELINES_FILENAME,
    _MARKDOWN_HEADING_RE,  # pyright: ignore[reportPrivateUsage]  # plan requires the shared parser boundary regex.
)

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "guideline-no-exception-baseline.json"
BASELINE_KEYS = frozenset({"guideline_id", "reason"})
GUIDELINE_ID_RE = re.compile(r"^G-[A-Za-z0-9-]+-\d+$")
NO_EXCEPTION_DEVIATE_RE = re.compile(r"^- Deviate when:\s*(n/a|never)\b")


class Record(TypedDict):
    guideline_id: str
    reason: str


class BaselineError(ValueError):
    """Raised when guideline or baseline data cannot be trusted."""


@dataclass(frozen=True)
class CurrentEntry:
    guideline_id: str
    title: str
    start_line: int
    deviate_line: int | None = None
    saw_body_line: bool = False


@dataclass(frozen=True)
class Finding:
    guideline_id: str
    title: str
    start_line: int
    deviate_line: int

    def key(self) -> str:
        return self.guideline_id


def _format_record_id(record_id: str) -> str:
    return record_id


def _validate_guideline_id(value: object, *, source: Path, index: int) -> str:
    if not isinstance(value, str) or GUIDELINE_ID_RE.fullmatch(value) is None:
        raise BaselineError(f"{source}: record {index} has invalid guideline_id")
    return value


def _validate_record(item: object, *, index: int, source: Path) -> Record:
    if not isinstance(item, dict):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    record = cast("dict[str, object]", item)
    if set(record) != set(BASELINE_KEYS):
        raise BaselineError(f"{source}: record {index} must have exactly {sorted(BASELINE_KEYS)}")
    guideline_id: str = _validate_guideline_id(record["guideline_id"], source=source, index=index)
    reason: object = record["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise BaselineError(f"{source}: record {index} has invalid reason")
    return {"guideline_id": guideline_id, "reason": reason}


def _first_duplicate(values: list[str]) -> str | None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


def load_baseline(path: Path) -> list[Record]:
    """Load and validate the committed no-exception baseline."""
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BaselineError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise BaselineError(f"{path}: baseline must be a top-level JSON array")
    records: list[Record] = [
        _validate_record(item, index=index, source=path)
        for index, item in enumerate(cast("list[object]", data))
    ]
    duplicate: str | None = _first_duplicate([record["guideline_id"] for record in records])
    if duplicate is not None:
        raise BaselineError(f"{path}: duplicate baseline identity {_format_record_id(duplicate)}")
    return records


def _read_guidelines(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BaselineError(f"{path}: cannot read guidelines: {exc}") from exc


def _finish_entry(
    *,
    current: CurrentEntry | None,
    seen_ids: set[str],
    findings: list[Finding],
    path: Path,
) -> None:
    if current is None:
        return
    if not current.saw_body_line:
        raise BaselineError(f"{path}: guideline entry {current.guideline_id} is missing body content")
    if current.guideline_id in seen_ids:
        raise BaselineError(f"{path}: duplicate guideline id {current.guideline_id}")
    seen_ids.add(current.guideline_id)
    if current.deviate_line is None:
        return
    findings.append(
        Finding(
            guideline_id=current.guideline_id,
            title=current.title,
            start_line=current.start_line,
            deviate_line=current.deviate_line,
        )
    )


def _updated_entry_for_deviate(current: CurrentEntry, *, line_number: int) -> CurrentEntry:
    if current.deviate_line is not None:
        return current
    return CurrentEntry(
        guideline_id=current.guideline_id,
        title=current.title,
        start_line=current.start_line,
        deviate_line=line_number,
        saw_body_line=current.saw_body_line,
    )


def _updated_entry_for_body(current: CurrentEntry) -> CurrentEntry:
    if current.saw_body_line:
        return current
    return CurrentEntry(
        guideline_id=current.guideline_id,
        title=current.title,
        start_line=current.start_line,
        deviate_line=current.deviate_line,
        saw_body_line=True,
    )


def scan_guidelines(path: Path) -> list[Finding]:
    """Return guideline entries whose deviate clause starts with n/a or never."""
    if not path.is_file():
        raise BaselineError(f"{path}: guidelines file is missing")
    raw_text: str = _read_guidelines(path)
    findings: list[Finding] = []
    seen_ids: set[str] = set()
    current: CurrentEntry | None = None
    saw_guideline_heading = False
    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        heading = GUIDELINE_HEADING_RE.match(raw_line)
        if heading is not None:
            saw_guideline_heading = True
            _finish_entry(current=current, seen_ids=seen_ids, findings=findings, path=path)
            current = CurrentEntry(
                guideline_id=heading.group(1),
                title=heading.group(2).strip(),
                start_line=line_number,
            )
            continue
        if _MARKDOWN_HEADING_RE.match(raw_line):
            _finish_entry(current=current, seen_ids=seen_ids, findings=findings, path=path)
            current = None
            continue
        if current is None:
            continue
        if raw_line.strip():
            current = _updated_entry_for_body(current)
        if NO_EXCEPTION_DEVIATE_RE.match(raw_line) is None:
            continue
        current = _updated_entry_for_deviate(current, line_number=line_number)
    _finish_entry(current=current, seen_ids=seen_ids, findings=findings, path=path)
    if not saw_guideline_heading and raw_text.strip():
        raise BaselineError(f"{path}: no recognized guideline entries")
    return findings


def _finding_sort_key(finding: Finding) -> tuple[str, int]:
    return (finding.guideline_id, finding.deviate_line)


def _run_check(*, guidelines_path: Path, baseline_path: Path) -> int:
    try:
        baseline_records: list[Record] = load_baseline(baseline_path)
        findings: list[Finding] = scan_guidelines(guidelines_path)
    except BaselineError as exc:
        print(f"lint-guideline-no-exception: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    baseline_keys: frozenset[str] = frozenset(record["guideline_id"] for record in baseline_records)
    live_keys: frozenset[str] = frozenset(finding.key() for finding in findings)
    new_findings: list[Finding] = []
    warned: list[Finding] = []
    for finding in sorted(findings, key=_finding_sort_key):
        if finding.key() in baseline_keys:
            warned.append(finding)
        else:
            new_findings.append(finding)
    stale_keys: list[str] = sorted(baseline_keys - live_keys)
    for finding in warned:
        print(
            f"warning: {finding.guideline_id} line {finding.deviate_line} "
            "has a no-exception deviate clause (baselined)",
            file=sys.stderr,
        )
    for finding in new_findings:
        print(
            f"{GUIDELINES_FILENAME}:{finding.deviate_line}: {finding.guideline_id} "
            "has a no-exception deviate clause; promote it, add a real deviate clause, "
            f"or add a reason to {BASELINE_FILENAME}",
            file=sys.stderr,
        )
    for key in stale_keys:
        print(f"stale baseline row: {_format_record_id(key)}", file=sys.stderr)
    return 1 if new_findings or stale_keys else 0


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint guideline-no-exception",
        description=__doc__,
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def main(argv: list[str] | None = None) -> int:
    parsed: argparse.Namespace | None = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root: Path = Path(str(parsed.root)).resolve()
    if not root.is_dir():
        print(f"lint-guideline-no-exception: --root is not a directory: {root}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    return _run_check(
        guidelines_path=root / GUIDELINES_FILENAME,
        baseline_path=root / "python" / BASELINE_FILENAME,
    )


if __name__ == "__main__":
    raise SystemExit(main())
