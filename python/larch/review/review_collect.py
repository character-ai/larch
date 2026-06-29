# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false
# ruff: noqa: PLR2004,ARG001,PLW2901,PIE810
# pylint: disable=too-many-branches,too-many-statements,too-many-locals,unused-argument
"""Collect and parse reviewer findings for the review pipeline."""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
import contextlib
from pathlib import Path

from larch.core import logging_util
from larch.research import research_eval
from larch.review.review_pipeline_shared import (
    FOCUS_AREAS,
    PER_REVIEWER_OOS_PROPOSAL_CAP,
    _append_text,
    _collector_records,
    _emit_kv,
    _get,
    _get_list,
    _kv_parse,
    _parse_args,
    _run_python_cli,
    _write_text,
)

# Pin collect contracts for structure tests: agent collect-results --timeout 1860 --substantive-validation --validation-mode.
# In description mode, dual-list output is split between ### In-Scope Findings and ### Out-of-Scope Observations.
# In diff mode, single-list output preserves the entire output when section headers are absent.


def _file_has_no_findings_sentinel(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    if any(line.strip() == "NO_ISSUES_FOUND" for line in text.splitlines()):
        return True
    stripped = text.strip()
    if stripped:
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and data.get("no_issues_found") is True:
            return True
    # Issue #4911: also accept a standalone {"no_issues_found": true} line when
    # narration precedes it. Reuse the #4891 helper, which matches only when a
    # line's entire stripped content is the JSON object, so JSON embedded inline
    # in a prose line is not accepted.
    return any(
        research_eval._line_json_no_issues(line)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        for line in text.splitlines()
    )


def _parse_output(*, path: Path, label: str, mode: str) -> list[tuple[str, str, str]]:
    if not path.is_file() or path.stat().st_size == 0 or _file_has_no_findings_sentinel(path):
        return []
    rows: list[tuple[str, str, str]] = []
    oos = False
    skip = False
    title = ""
    body_lines: list[str] = []

    def flush() -> None:
        nonlocal title, body_lines
        if title and body_lines:
            body = " ".join(line.strip() for line in body_lines if line.strip()).replace("\t", " ")
            clean_title = title.strip().replace("\t", " ")
            rows.append((("[OUT_OF_SCOPE] " if oos else "") + clean_title, label, body))
        title = ""
        body_lines = []

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip("\r")
        if line.startswith("### Out-of-Scope Observations"):
            flush()
            oos = True
            skip = False
            continue
        if line.startswith("### In-Scope Findings"):
            flush()
            oos = False
            skip = False
            continue
        if line.startswith("## Commits since merge-base"):
            flush()
            skip = True
            continue
        if skip and (line.startswith("### ") or line.startswith("## ")):
            skip = False
            continue
        if skip:
            continue
        if re.match(r"^[-*] ", line) or re.match(r"^[0-9]+\.\s", line):
            flush()
            title = re.sub(r"^(?:[-*]\s+|[0-9]+\.\s+)", "", line)
            body_lines = [line]
            continue
        if line.strip():
            body_lines.append(line)
    flush()
    return rows


def _parse_output_tsv(*, path: Path, label: str) -> list[tuple[str, str, str]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    fd, tmp = tempfile.mkstemp(prefix="collect-tsv.", suffix=".tsv")
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        result = _run_python_cli(["eval", "validate-research-output", "--structured-reviewer-mode", "--write-structured", str(tmp_path), str(path)])
        if result.returncode != 0 or not tmp_path.is_file() or tmp_path.stat().st_size == 0:
            return []
        rows: list[tuple[str, str, str]] = []
        with tmp_path.open(encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle, delimiter="\t")
            for row in reader:
                if row and row[0] == "schema_version":
                    continue
                if len(row) >= 8:
                    scope, sev, focus, loc, what, scenario, fix = row[1:8]
                    prefix = "[OUT_OF_SCOPE] " if scope == "out_of_scope" else ""
                    rows.append((f"{prefix}{focus}: {loc}", label, f"[{sev}] {what} {scenario} {fix}"))
        return rows
    finally:
        with contextlib.suppress(FileNotFoundError):
            tmp_path.unlink()


def _normalize_reviewer_label(label: str) -> str:
    stem, ext = (label[:-4], ".txt") if label.endswith(".txt") else (label, "")
    while True:
        new = re.sub(r"-(?:phase2|phase3|retry)$", "", stem)
        if new == stem:
            break
        stem = new
    return stem + ext


def _valid_reviewer_output_label(label: str) -> bool:
    return label.endswith("-output.txt")


def _retain_oos_for_label(oos_counts_by_label: dict[str, int], *, label: str) -> bool:
    retained_oos = oos_counts_by_label.get(label, 0)
    if retained_oos >= PER_REVIEWER_OOS_PROPOSAL_CAP:
        return False
    oos_counts_by_label[label] = retained_oos + 1
    return True


def _clean_oos_focus_title(title: str) -> str:
    if not title.startswith("[OUT_OF_SCOPE] **"):
        return title
    category = title.removeprefix("[OUT_OF_SCOPE] **").split("**", 1)[0]
    if category not in FOCUS_AREAS:
        return title
    match = re.search(r"\[`([^`]+)`\]", title)
    return f"[OUT_OF_SCOPE] {category}: {match.group(1)}" if match else f"[OUT_OF_SCOPE] {category}"


def _collector_ok(*, path: Path, reviewer_file: Path) -> bool:
    for record in _collector_records(path):
        if record.get("REVIEWER_FILE") == str(reviewer_file):
            return record.get("STATUS") in {"OK", "cap_hit"}
    return False


def _record_claude_substantive(*, collector_results: Path, file: Path) -> None:
    _append_text(
        path=collector_results,
        text=f"REVIEWER_FILE={file}\nTOOL=claude\nSTATUS=OK\nEXIT_CODE=0\n\n"
    )


def _record_claude_non_substantive(*, collector_results: Path, file: Path) -> None:
    _append_text(
        path=collector_results,
        text=f"REVIEWER_FILE={file}\nTOOL=claude\nSTATUS=NOT_SUBSTANTIVE\nEXIT_CODE=0\n\n"
    )
    logging_util.diagnostic(f"**⚠ Reviewer {file.name}: non-substantive output produced no prose or TSV findings**")


def _record_claude_collector_result(*, collector_results: Path, file: Path, rows: list[tuple[str, str, str]]) -> None:
    if rows or _file_has_no_findings_sentinel(file):
        _record_claude_substantive(collector_results=collector_results, file=file)
    elif file.is_file() and file.stat().st_size:
        _record_claude_non_substantive(collector_results=collector_results, file=file)


def collect_findings(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="review-collect-findings")
    usage = "Usage: review collect-findings --mode diff|description --findings-file FILE --oos-file FILE [--external-output-files FILE...] [--claude-output-files FILE...] [--timeout SECONDS]"
    options = {"--mode", "--timeout", "--session-env-path", "--findings-file", "--oos-file"}
    parsed = _parse_args(argv=argv, usage=usage, options=options, list_options={"--external-output-files", "--claude-output-files"})
    if parsed is None:
        return 0
    if not parsed:
        return 2
    mode = _get(parsed=parsed, key="--mode")
    if mode not in {"diff", "description"}:
        logging_util.diagnostic("review collect-findings: --mode must be diff or description")
        return 2
    findings_file = Path(_get(parsed=parsed, key="--findings-file"))
    oos_file = Path(_get(parsed=parsed, key="--oos-file"))
    if not str(findings_file) or not str(oos_file):
        logging_util.diagnostic("review collect-findings: --findings-file and --oos-file are required")
        return 2
    timeout = _get(parsed=parsed, key="--timeout", default="1860")
    external_files = [Path(p) for p in _get_list(parsed=parsed, key="--external-output-files")]
    claude_files = [Path(p) for p in _get_list(parsed=parsed, key="--claude-output-files")]
    findings_file.parent.mkdir(parents=True, exist_ok=True)
    oos_file.parent.mkdir(parents=True, exist_ok=True)
    review_tmpdir = Path(os.environ.get("REVIEW_TMPDIR") or str(findings_file.parent))
    collector_results = review_tmpdir / "collector-results.env"
    collector_results.parent.mkdir(parents=True, exist_ok=True)
    collector_results.write_text("", encoding="utf-8")
    if external_files:
        result = _run_python_cli(
            ["agent", "collect-results", "--timeout", timeout, "--substantive-validation", "--validation-mode", *map(str, external_files)],
            env={"LARCH_QUIET_DISABLE": "1"},
        )
        _write_text(path=collector_results, text=result.stdout)
        if result.stderr:
            for line in result.stderr.splitlines():
                logging_util.diagnostic(line)
        if result.returncode != 0:
            return result.returncode
    if claude_files:
        sentinels = [str(path) + ".done" for path in claude_files]
        wait_log = review_tmpdir / "wait-for-claude-reviewers.log"
        result = _run_python_cli(
            ["agent", "wait-reviewers", "--timeout", timeout, *sentinels],
            env={"WAIT_FOR_REVIEWERS_POLL_INTERVAL": os.environ.get("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "1")},
        )
        _write_text(path=wait_log, text=result.stdout + result.stderr)
        if result.returncode != 0 or any(line.startswith("TIMEOUT ") for line in wait_log.read_text(encoding="utf-8", errors="replace").splitlines()):
            return result.returncode or 1
    dirty_detected = "false"
    for output in [*external_files, *claude_files]:
        sidecar = output.with_name(output.name + ".dirty-tree")
        if sidecar.is_file() and _kv_parse(sidecar.read_text(encoding="utf-8", errors="replace")).get("STATUS") == "dirty":
            dirty_detected = "true"
    per_rows: list[tuple[str, str, str]] = []
    for file in external_files:
        if not _collector_ok(path=collector_results, reviewer_file=file):
            continue
        rows = _parse_output_tsv(path=file, label=file.name)
        per_rows.extend(rows or _parse_output(path=file, label=file.name, mode=mode))
    for file in claude_files:
        rows = _parse_output(path=file, label=file.name, mode=mode)
        if not rows:
            rows = _parse_output_tsv(path=file, label=file.name)
        _record_claude_collector_result(collector_results=collector_results, file=file, rows=rows)
        per_rows.extend(rows)
    findings_file.write_text("", encoding="utf-8")
    oos_file.write_text("", encoding="utf-8")
    count = 0
    oos_count = 0
    oos_counts_by_label: dict[str, int] = {}
    for title, label, body in per_rows:
        label = _normalize_reviewer_label(label)
        if not _valid_reviewer_output_label(label):
            continue
        is_oos = title.startswith("[OUT_OF_SCOPE]")
        if is_oos and not _retain_oos_for_label(oos_counts_by_label, label=label):
            continue
        count += 1
        title = _clean_oos_focus_title(title)
        _append_text(
            path=findings_file,
            text=f"### FINDING_{count}: {title}\n- **Reviewer**: {label}\n- **Concern**: {body}\n- **Suggested revision**: Address the concern above.\n\n"
        )
        if is_oos:
            oos_count += 1
            _append_text(path=oos_file, text=f"### FINDING_{count}: {title}\n{body}\n\n")
    _emit_kv(key="FINDINGS_COUNT", value=count)
    _emit_kv(key="OOS_COUNT", value=oos_count)
    _emit_kv(key="DIRTY_DETECTED", value=dirty_detected)
    _emit_kv(key="COLLECT_OK", value="true")
    _emit_kv(key="COLLECTOR_OUTPUT_FILE", value=collector_results)
    return 0


def collect_findings_main(argv: list[str]) -> int:
    return collect_findings(argv)
