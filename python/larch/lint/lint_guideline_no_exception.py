"""Flag no-exception guideline entries that should be promoted or baselined."""
# pylint: disable=no-member

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from larch.core.architectural_guidelines import (
    GUIDELINE_HEADING_RE,
    GUIDELINES_FILENAME,
    _MARKDOWN_HEADING_RE,  # pyright: ignore[reportPrivateUsage]  # plan requires the shared parser boundary regex.
)
from larch.lint.engine import (
    GuidelineNoExceptionBaselineRow,
    IdentityLintCli,
    ScanError,
    compare_identity_baseline,
    load_identity_baseline,
    parse_identity_lint_argv,
)

TOOL_FAILURE_EXIT = 2
BASELINE_FILENAME = "guideline-no-exception-baseline.json"
GUIDELINE_ID_RE = re.compile(r"^G-[A-Za-z0-9-]+-\d+$")
NO_EXCEPTION_DEVIATE_RE = re.compile(r"^- Deviate when:\s*(n/a|never)\b")


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


def _run_check(*, root: Path, guidelines_path: Path, baseline_path: Path) -> int:
    try:
        baseline_records = load_identity_baseline(
            baseline_path, root=root, kind="guideline_no_exception"
        )
        findings: list[Finding] = scan_guidelines(guidelines_path)
    except (BaselineError, ScanError) as exc:
        print(f"lint-guideline-no-exception: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    live_rows = [GuidelineNoExceptionBaselineRow(finding.guideline_id, "") for finding in findings]
    new_rows, stale_rows, warned_rows = compare_identity_baseline(live_rows, baseline_records)
    new_ids = {row.guideline_id for row in new_rows if isinstance(row, GuidelineNoExceptionBaselineRow)}
    warned_ids = {row.guideline_id for row in warned_rows if isinstance(row, GuidelineNoExceptionBaselineRow)}
    for finding in sorted(findings, key=_finding_sort_key):
        if finding.guideline_id not in warned_ids:
            continue
        print(
            f"warning: {finding.guideline_id} line {finding.deviate_line} "
            "has a no-exception deviate clause (baselined)",
            file=sys.stderr,
        )
    for finding in sorted(findings, key=_finding_sort_key):
        if finding.guideline_id not in new_ids:
            continue
        print(
            f"{GUIDELINES_FILENAME}:{finding.deviate_line}: {finding.guideline_id} "
            "has a no-exception deviate clause; promote it, add a real deviate clause, "
            f"or add a reason to {BASELINE_FILENAME}",
            file=sys.stderr,
        )
    for row in stale_rows:
        if isinstance(row, GuidelineNoExceptionBaselineRow):
            print(f"stale baseline row: {_format_record_id(row.guideline_id)}", file=sys.stderr)
    return 1 if new_rows or stale_rows else 0


CLI = IdentityLintCli(
    prog="cli.py lint guideline-no-exception", description=__doc__ or "",
    baseline_filename=BASELINE_FILENAME,
)


def main(argv: list[str] | None = None) -> int:
    parsed = parse_identity_lint_argv(
        argv if argv is not None else sys.argv[1:], cli=CLI,
        default_root=Path(__file__).resolve().parents[3],
    )
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = parsed.root
    if not root.is_dir():
        print(f"lint-guideline-no-exception: --root is not a directory: {root}", file=sys.stderr)
        return TOOL_FAILURE_EXIT
    return _run_check(
        root=root, guidelines_path=root / GUIDELINES_FILENAME,
        baseline_path=root / "python" / BASELINE_FILENAME,
    )


if __name__ == "__main__":
    raise SystemExit(main())
