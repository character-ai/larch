"""Calibration replay fixture and ballot reconstruction helpers."""

from __future__ import annotations

# pyright: reportUnusedCallResult=false

import argparse
import csv
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import voting

JSONL_TRUNCATION_SENTINEL = 2000
DEFAULT_MANIFEST = Path("python/test_fixtures/plan-fidelity-calibration/manifest.tsv")
_BALLOT_HEADING_RE = re.compile(r"^###[ \t]+(?P<id>(?:FINDING|OOS)_[A-Za-z0-9_]+):")
_ANY_BALLOT_HEADING_RE = re.compile(r"^###[ \t]+(?:FINDING|OOS)_[A-Za-z0-9_]+:")
_MARKDOWN_TITLE_RE = re.compile(r"^##[ \t]+(?P<title>.+?)[ \t]*$")
_POINTER_ONLY_RE = re.compile(r"^(?:see\s+)?(?:the\s+)?(?:implementation\s+)?plan(?:\.txt)?\.?$|^(?:tbd|todo|n/?a|none)$", re.IGNORECASE)


class CalibrationReplayError(RuntimeError):
    """Raised when calibration replay inputs are incomplete or non-parity."""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CalibrationReplayError(f"unable to read {path}") from exc


def _normalize_title(value: str) -> str:
    title = re.sub(r"^[#\s]*(?:FINDING|OOS)_[A-Za-z0-9_]+:[ \t]*", "", value.strip(), flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _is_redundant_title(*, line: str, title: str) -> bool:
    match = _MARKDOWN_TITLE_RE.match(line.strip())
    return bool(match and _normalize_title(match.group("title")) == _normalize_title(title))


def _first_markdown_title(text: str) -> str:
    for line in text.splitlines():
        match = _MARKDOWN_TITLE_RE.match(line.strip())
        if match:
            return re.sub(r"^(?:FINDING|OOS)_[A-Za-z0-9_]+:[ \t]*", "", match.group("title").strip(), flags=re.IGNORECASE)
    return ""


def _strip_redundant_lead_title(*, body: str, title: str) -> str:
    lines = body.splitlines()
    if lines and _is_redundant_title(line=lines[0], title=title):
        lines = lines[1:]
        if lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip("\n")


def _round_matches(*, value: object, round_num: int) -> bool:
    return str(value or "").strip() == str(round_num)


def _round_findings_path(*, run_root: Path, round_num: int) -> Path:
    return run_root / f"round-{round_num}" / "findings.md"


def _extract_findings_block(*, text: str, finding_id: str) -> str:
    lines = text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        match = _BALLOT_HEADING_RE.match(line)
        if match and match.group("id") == finding_id:
            start = index
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if _ANY_BALLOT_HEADING_RE.match(lines[index]):
            end = index
            break
    return "\n".join(lines[start:end]).strip() + "\n"


def _jsonl_record(*, run_root: Path, finding_id: str, round_num: int) -> Mapping[str, object] | None:
    jsonl = run_root / "review-findings-full.jsonl"
    if not jsonl.is_file():
        return None
    for line in _read_text(jsonl).splitlines():
        if not line.strip():
            continue
        try:
            data: Any = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        record = cast("dict[str, object]", data)
        if record.get("id") == finding_id and _round_matches(value=record.get("round_num"), round_num=round_num):
            return record
    return None


def _ballot_from_jsonl_record(*, record: Mapping[str, object], finding_id: str) -> str:
    body = str(record.get("prose_body") or "")
    if len(body) == JSONL_TRUNCATION_SENTINEL:
        raise CalibrationReplayError(
            f"{finding_id} jsonl prose_body is exactly {JSONL_TRUNCATION_SENTINEL} characters; "
            "jsonl alone is not production-parity for truncated bodies, so commit a fixture_ballot"
        )
    title = str(record.get("category") or "").strip() or _first_markdown_title(body) or finding_id
    stripped = _strip_redundant_lead_title(body=body, title=title)
    suffix = f"\n\n{stripped.strip()}" if stripped.strip() else ""
    return f"### {finding_id}: {title}{suffix}\n"


def rebuild_single_item_ballot(
    *,
    finding_id: str,
    run_root: Path,
    round_num: int,
    fixture_ballot_path: Path | None = None,
) -> tuple[str, str]:
    """Return a neutralized single-item ballot and its source kind."""
    if fixture_ballot_path is not None:
        if not fixture_ballot_path.is_file():
            raise CalibrationReplayError(f"fixture_ballot is not readable: {fixture_ballot_path}")
        return _read_text(fixture_ballot_path), "fixture_ballot"

    findings = _round_findings_path(run_root=run_root, round_num=round_num)
    if findings.is_file():
        block = _extract_findings_block(text=_read_text(findings), finding_id=finding_id)
        if block:
            return voting.neutralize_reviewer_attribution(text=block), "round_findings"

    record = _jsonl_record(run_root=run_root, finding_id=finding_id, round_num=round_num)
    if record is not None:
        return voting.neutralize_reviewer_attribution(text=_ballot_from_jsonl_record(record=record, finding_id=finding_id)), "review_findings_jsonl"

    raise CalibrationReplayError(f"no ballot source found for {finding_id} round {round_num} under {run_root}")


def load_fixture_plan(path: Path) -> str:
    """Load the committed production-shaped plan fixture used by dispatch-voters."""
    text = _read_text(path)
    if not text.strip():
        raise CalibrationReplayError(f"fixture_plan is empty: {path}")
    return text


def extract_implementation_plan_from_plan_goals_test(source: Path) -> str:
    """Extract the Implementation Plan body from a committed plan-goals-test artifact."""
    lines = _read_text(source).splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == "## Implementation Plan":
            start = index + 1
            break
    if start is None:
        raise CalibrationReplayError("plan-goals-test artifact is missing ## Implementation Plan")
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].strip().lower() == "## test plan":
            end = index
            break
    body = "\n".join(lines[start:end]).strip()
    if not body:
        raise CalibrationReplayError("Implementation Plan body is empty")
    if _POINTER_ONLY_RE.match(body):
        raise CalibrationReplayError("Implementation Plan body is pointer-only, not a replay fixture")
    return body + "\n"


def _parse_bool(value: str, *, field: str) -> bool:
    normalized = (value or "").strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise CalibrationReplayError(f"{field} must be true or false")


def _resolve_repo_path(*, repo_root: Path, raw: str, field: str, required: bool) -> Path | None:
    value = (raw or "").strip()
    if not value:
        if required:
            raise CalibrationReplayError(f"{field} is required")
        return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise CalibrationReplayError(f"{field} must be a repo-relative path")
    return repo_root / candidate


def validate_manifest_row(row: Mapping[str, str], *, repo_root: Path | None = None) -> None:
    """Validate one plan-fidelity calibration manifest row."""
    root = repo_root or Path.cwd()
    finding_id = (row.get("finding_id") or "").strip()
    if not finding_id:
        raise CalibrationReplayError("finding_id is required")
    fixture_plan = _resolve_repo_path(repo_root=root, raw=row.get("fixture_plan", ""), field="fixture_plan", required=True)
    if fixture_plan is None or not fixture_plan.is_file() or not load_fixture_plan(fixture_plan).strip():
        raise CalibrationReplayError(f"fixture_plan is not readable: {row.get('fixture_plan', '')}")
    diff_required = _parse_bool(row.get("diff_required", ""), field="diff_required")
    fixture_diff = _resolve_repo_path(repo_root=root, raw=row.get("fixture_diff", ""), field="fixture_diff", required=diff_required)
    if diff_required and (fixture_diff is None or not fixture_diff.is_file()):
        raise CalibrationReplayError(f"fixture_diff is required and must be readable for {finding_id}")
    fixture_ballot = _resolve_repo_path(repo_root=root, raw=row.get("fixture_ballot", ""), field="fixture_ballot", required=False)
    if fixture_ballot is not None:
        if not fixture_ballot.is_file():
            raise CalibrationReplayError(f"fixture_ballot is not readable: {row.get('fixture_ballot', '')}")
        return
    run_id = (row.get("run_id") or "").strip()
    round_raw = (row.get("round_num") or "").strip()
    if not run_id or not round_raw.isdigit():
        return
    record = _jsonl_record(run_root=root / "larch-logs" / "implement" / run_id, finding_id=finding_id, round_num=int(round_raw))
    if record is not None and len(str(record.get("prose_body") or "")) == JSONL_TRUNCATION_SENTINEL:
        raise CalibrationReplayError(f"fixture_ballot is required for truncated jsonl body on {finding_id}")


def validate_manifest(path: Path = DEFAULT_MANIFEST, *, repo_root: Path | None = None) -> list[str]:
    root = repo_root or Path.cwd()
    if not path.is_file():
        return [f"manifest not found: {path}"]
    errors: list[str] = []
    rows = list(csv.DictReader(_read_text(path).splitlines(), delimiter="\t"))
    for index, row in enumerate(rows, start=2):
        try:
            validate_manifest_row(row, repo_root=root)
        except CalibrationReplayError as exc:
            errors.append(f"row {index}: {exc}")
    return errors


def _write_ballot_output(*, ballot_text: str, output_path: Path | None) -> str:
    if output_path is None:
        output_path = Path.cwd() / "calibration-replay-ballot.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ballot_text, encoding="utf-8")
    return str(output_path)


def rebuild_ballot_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="calibration-replay rebuild-ballot")
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--round-num", required=True)
    parser.add_argument("--fixture-ballot", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    if not str(args.round_num).isdigit() or int(str(args.round_num)) <= 0:
        print("REBUILD_STATUS=failed")
        print("ERROR=--round-num must be a positive integer")
        return 2
    try:
        ballot, source = rebuild_single_item_ballot(
            finding_id=str(args.finding_id),
            run_root=Path(str(args.run_root)),
            round_num=int(str(args.round_num)),
            fixture_ballot_path=Path(str(args.fixture_ballot)) if str(args.fixture_ballot) else None,
        )
        ballot_path = _write_ballot_output(ballot_text=ballot, output_path=Path(str(args.output)) if str(args.output) else None)
    except CalibrationReplayError as exc:
        print("REBUILD_STATUS=failed")
        print(f"ERROR={exc}")
        return 1
    print("REBUILD_STATUS=ok")
    print(f"BALLOT_SOURCE={source}")
    print(f"BALLOT_PATH={ballot_path}")
    return 0


def validate_manifest_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="calibration-replay validate-manifest")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args(argv)
    try:
        errors = validate_manifest(Path(str(args.manifest)), repo_root=Path.cwd())
    except CalibrationReplayError as exc:
        errors = [str(exc)]
    if errors:
        print("MANIFEST_STATUS=failed")
        for error in errors:
            print(f"ERROR={error}")
        return 1
    print("MANIFEST_STATUS=ok")
    return 0
