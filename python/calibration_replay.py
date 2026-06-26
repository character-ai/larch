"""Calibration replay fixture and ballot reconstruction helpers."""

from __future__ import annotations

# pyright: reportUnusedCallResult=false

import argparse
import csv
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from larch.core import proc
import external_defaults
import voting

JSONL_TRUNCATION_SENTINEL = 2000
DEFAULT_MANIFEST = Path("python/test_fixtures/plan-fidelity-calibration/manifest.tsv")
DEFAULT_COHORT = Path("python/test_fixtures/plan-fidelity-calibration/cohort.tsv")
_BALLOT_HEADING_RE = re.compile(r"^###[ \t]+(?P<id>(?:FINDING|OOS)_[A-Za-z0-9_]+):")
_ANY_BALLOT_HEADING_RE = re.compile(r"^###[ \t]+(?:FINDING|OOS)_[A-Za-z0-9_]+:")
_MARKDOWN_TITLE_RE = re.compile(r"^##[ \t]+(?P<title>.+?)[ \t]*$")
_POINTER_FIRST_LINE_RE = re.compile(r"(?:see plan\.txt|see attached|see linked|tbd|todo)\.?", re.IGNORECASE)
_VOTE_TALLY_LINE_RE = re.compile(r"^Vote tally:", re.IGNORECASE | re.MULTILINE)
_REJECTED_SUBTYPE_LINE_RE = re.compile(r"^\*\*Rejected subtype:\*\*")
_FULL_DOCUMENT_PLAN_MARKERS = (
    re.compile(r"^##[ \t]+Goal\s*$", re.MULTILINE),
    re.compile(r"^##[ \t]+Implementation Plan\s*$", re.MULTILINE),
    re.compile(r"^##[ \t]+Test plan\s*$", re.MULTILINE),
)


class CalibrationReplayError(RuntimeError):
    """Raised when calibration replay inputs are incomplete or non-parity."""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CalibrationReplayError(f"unable to read {path}") from exc


def cohort_fixture_stem(*, run_id: str, finding_id: str) -> str:
    """Stable fixture basename for a labeled cohort row."""
    return f"{run_id}_{finding_id}"


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


def _strip_historical_vote_artifacts(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and _VOTE_TALLY_LINE_RE.match(lines[-1].strip()):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    return "\n".join(lines).strip("\n") + ("\n" if lines else "")


def _strip_rejected_subtype_wrapper(text: str) -> str:
    lines = text.splitlines()
    if not lines or not _REJECTED_SUBTYPE_LINE_RE.match(lines[0].strip()):
        return text
    for index, line in enumerate(lines):
        if _BALLOT_HEADING_RE.match(line):
            return "\n".join(lines[index:]).strip("\n") + "\n"
    return text


def _validate_fixture_ballot_purity(text: str, *, path: Path) -> None:
    if _VOTE_TALLY_LINE_RE.search(text):
        raise CalibrationReplayError(f"fixture_ballot contains historical vote tally: {path}")


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
        if record.get("id") != finding_id:
            continue
        if not _round_matches(value=record.get("round_num"), round_num=round_num):
            continue
        return record
    return None


def _ballot_from_jsonl_record(*, record: Mapping[str, object], finding_id: str) -> str:
    raw_body = str(record.get("prose_body") or "")
    if len(raw_body) == JSONL_TRUNCATION_SENTINEL:
        raise CalibrationReplayError(
            f"{finding_id} jsonl prose_body is exactly {JSONL_TRUNCATION_SENTINEL} characters; "
            "jsonl alone is not production-parity for truncated bodies, so commit a fixture_ballot"
        )
    body = _strip_historical_vote_artifacts(_strip_rejected_subtype_wrapper(raw_body))
    block = _extract_findings_block(text=body, finding_id=finding_id)
    if block:
        return block
    title = str(record.get("category") or "").strip() or _first_markdown_title(body) or finding_id
    stripped = _strip_redundant_lead_title(body=body, title=title)
    suffix = f"\n\n{stripped.strip()}" if stripped.strip() else ""
    return f"### {finding_id}: {title}{suffix}\n"


def _extract_implementation_plan_body(lines: Sequence[str]) -> str:
    """Mirror run_logs._validate_plan_goals_payload section and first-line rules."""
    in_section = False
    saw = False
    body_lines: list[str] = []
    last_test_plan = 0
    for line in lines:
        if line == "## Implementation Plan":
            if not saw:
                in_section = True
            saw = True
            continue
        if in_section:
            body_lines.append(line)
            if line == "## Test plan":
                last_test_plan = len(body_lines)
    if not saw:
        raise CalibrationReplayError("plan-goals-test artifact is missing ## Implementation Plan")
    limit = last_test_plan - 1 if last_test_plan > 0 else len(body_lines)
    impl_body = [line for line in body_lines[:limit] if line.strip()]
    if not impl_body:
        raise CalibrationReplayError("Implementation Plan body is empty")
    first = impl_body[0].strip().lower()
    if _POINTER_FIRST_LINE_RE.fullmatch(first):
        raise CalibrationReplayError("Implementation Plan body is pointer-only, not a replay fixture")
    return "\n".join(body_lines[:limit]).rstrip() + "\n"


def _validate_fixture_plan_shape(text: str, *, path: Path) -> None:
    if any(marker.search(text) for marker in _FULL_DOCUMENT_PLAN_MARKERS):
        raise CalibrationReplayError(
            f"fixture_plan must be an extracted Implementation Plan body, not a full plan-goals document: {path}"
        )


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
        ballot_text = _strip_historical_vote_artifacts(_read_text(fixture_ballot_path))
        return voting.neutralize_reviewer_attribution(text=ballot_text), "fixture_ballot"

    findings = _round_findings_path(run_root=run_root, round_num=round_num)
    if findings.is_file():
        block = _strip_historical_vote_artifacts(_extract_findings_block(text=_read_text(findings), finding_id=finding_id))
        if block.strip():
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
    _validate_fixture_plan_shape(text, path=path)
    return text


def extract_implementation_plan_from_plan_goals_test(source: Path) -> str:
    """Extract the Implementation Plan body from a committed plan-goals-test artifact."""
    return _extract_implementation_plan_body(_read_text(source).splitlines())


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


def _cohort_row_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (
        (row.get("finding_id") or "").strip(),
        (row.get("run_id") or "").strip(),
        (row.get("round_num") or "").strip(),
    )


def _load_tsv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise CalibrationReplayError(f"tsv not found: {path}")
    return list(csv.DictReader(_read_text(path).splitlines(), delimiter="\t"))


def _validate_cohort_binding(*, manifest_rows: list[dict[str, str]], cohort_rows: list[dict[str, str]]) -> None:
    if not cohort_rows:
        raise CalibrationReplayError("cohort denominator is empty")
    cohort_counts = Counter(_cohort_row_key(row) for row in cohort_rows)
    manifest_counts = Counter(_cohort_row_key(row) for row in manifest_rows)
    duplicate_keys = sorted(
        key
        for key in cohort_counts.keys() | manifest_counts.keys()
        if cohort_counts.get(key, 0) > 1 or manifest_counts.get(key, 0) > 1
    )
    if duplicate_keys:
        duplicate_text = ", ".join(f"{finding_id}@{run_id}/round-{round_num}" for finding_id, run_id, round_num in duplicate_keys)
        raise CalibrationReplayError(f"duplicate labeled cohort keys: {duplicate_text}")
    cohort_keys = set(cohort_counts)
    manifest_keys = set(manifest_counts)
    missing = sorted(cohort_keys - manifest_keys)
    extra = sorted(manifest_keys - cohort_keys)
    if missing:
        missing_text = ", ".join(f"{finding_id}@{run_id}/round-{round_num}" for finding_id, run_id, round_num in missing)
        raise CalibrationReplayError(f"manifest is missing labeled cohort rows: {missing_text}")
    if extra:
        extra_text = ", ".join(f"{finding_id}@{run_id}/round-{round_num}" for finding_id, run_id, round_num in extra)
        raise CalibrationReplayError(f"manifest has rows outside the labeled cohort: {extra_text}")
    for manifest_row in manifest_rows:
        key = _cohort_row_key(manifest_row)
        cohort_row = next(row for row in cohort_rows if _cohort_row_key(row) == key)
        for field in ("v2_tool", "v1_tool"):
            expected = (cohort_row.get(field) or "").strip()
            actual = (manifest_row.get(field) or "").strip()
            if expected and actual != expected:
                raise CalibrationReplayError(f"{key[0]} manifest {field}={actual!r} does not match cohort {field}={expected!r}")


def _availability_flags(*, v2_tool: str, v1_tool: str) -> tuple[bool, bool]:
    if v2_tool == "cursor-plan-fidelity":
        return False, True
    if v2_tool == "codex-plan-fidelity":
        return True, v1_tool != "claude"
    raise CalibrationReplayError(f"unsupported v2_tool for replay: {v2_tool}")


def _expected_voter_2_output_name(v2_tool: str) -> str:
    for policy in external_defaults.voter_policies("review.voters"):
        if policy.slot_name != "voter-2":
            continue
        if policy.default_label == v2_tool:
            return policy.output_name
        if v2_tool in dict(policy.semantic_labels).values():
            return policy.output_name
    raise CalibrationReplayError(f"unsupported v2_tool for replay: {v2_tool}")


def _resolve_voter_path(*, repo_root: Path, raw_path: str, ballot_parent: Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    relative = ballot_parent / candidate
    if relative.is_file():
        return relative
    return repo_root / candidate


def _parse_slot_v2_vote(*, voter_path: Path, finding_id: str) -> str:
    if not voter_path.is_file():
        raise CalibrationReplayError(f"voter output missing: {voter_path}")
    if not voter_path.read_text(encoding="utf-8", errors="replace").strip():
        raise CalibrationReplayError(f"voter output empty: {voter_path}")
    vote = voting.parse_judge_vote(voter_file=voter_path, ballot_id=finding_id)[0].upper()
    if vote not in {"YES", "NO"}:
        raise CalibrationReplayError(f"unparseable vote for {finding_id} in {voter_path}: {vote!r}")
    return vote


def _yes_rate_label(votes: Sequence[str]) -> str:
    if not votes:
        return "0/0"
    yes_count = sum(1 for vote in votes if vote == "YES")
    return f"{yes_count}/{len(votes)}"


def _classification_tsv_path(*, repo_root: Path, run_id: str, round_num: int) -> Path:
    return repo_root / "larch-logs" / "implement" / run_id / f"round-{round_num}" / "findings-classification.tsv"


def _before_vote(*, repo_root: Path, row: Mapping[str, str]) -> str:
    run_id = (row.get("run_id") or "").strip()
    round_raw = (row.get("round_num") or "").strip()
    finding_id = (row.get("finding_id") or "").strip()
    if not run_id or not round_raw.isdigit() or not finding_id:
        raise CalibrationReplayError(f"missing run metadata for {finding_id}")
    tsv = _classification_tsv_path(repo_root=repo_root, run_id=run_id, round_num=int(round_raw))
    if not tsv.is_file():
        raise CalibrationReplayError(f"findings-classification.tsv not found for {finding_id}: {tsv}")
    for classification_row in _load_tsv_rows(tsv):
        if (classification_row.get("finding_id") or "").strip() == finding_id:
            return (classification_row.get("v2_vote") or "").strip().upper()
    raise CalibrationReplayError(f"finding_id {finding_id} missing from {tsv}")


def validate_manifest_row(row: Mapping[str, str], *, repo_root: Path | None = None) -> None:
    """Validate one plan-fidelity calibration manifest row."""
    root = repo_root or Path.cwd()
    finding_id = (row.get("finding_id") or "").strip()
    if not finding_id:
        raise CalibrationReplayError("finding_id is required")
    run_id = (row.get("run_id") or "").strip()
    round_raw = (row.get("round_num") or "").strip()
    if not run_id or not round_raw.isdigit() or int(round_raw) <= 0:
        raise CalibrationReplayError(f"run_id and positive numeric round_num are required for {finding_id}")
    fixture_plan = _resolve_repo_path(repo_root=root, raw=row.get("fixture_plan", ""), field="fixture_plan", required=True)
    if fixture_plan is None or not fixture_plan.is_file():
        raise CalibrationReplayError(f"fixture_plan is not readable: {row.get('fixture_plan', '')}")
    plan_source = _read_text(fixture_plan)
    if not plan_source.strip():
        raise CalibrationReplayError(f"fixture_plan is empty: {fixture_plan}")
    _validate_fixture_plan_shape(plan_source, path=fixture_plan)
    diff_required = _parse_bool(row.get("diff_required", ""), field="diff_required")
    fixture_diff_raw = (row.get("fixture_diff") or "").strip()
    if not diff_required and fixture_diff_raw:
        raise CalibrationReplayError(f"fixture_diff must be empty when diff_required=false for {finding_id}")
    fixture_diff = _resolve_repo_path(repo_root=root, raw=fixture_diff_raw, field="fixture_diff", required=diff_required)
    if diff_required and (fixture_diff is None or not fixture_diff.is_file()):
        raise CalibrationReplayError(f"fixture_diff is required and must be readable for {finding_id}")
    run_root = root / "larch-logs" / "implement" / run_id
    fixture_ballot_raw = (row.get("fixture_ballot") or "").strip()
    fixture_ballot_path: Path | None
    if fixture_ballot_raw:
        fixture_ballot = _resolve_repo_path(repo_root=root, raw=fixture_ballot_raw, field="fixture_ballot", required=True)
        if fixture_ballot is None or not fixture_ballot.is_file():
            raise CalibrationReplayError(f"fixture_ballot is not readable: {fixture_ballot_raw}")
        ballot_text = _read_text(fixture_ballot)
        _validate_fixture_ballot_purity(ballot_text, path=fixture_ballot)
        fixture_ballot_path = fixture_ballot
    else:
        fixture_ballot_path = None
    rebuild_single_item_ballot(
        finding_id=finding_id,
        run_root=run_root,
        round_num=int(round_raw),
        fixture_ballot_path=fixture_ballot_path,
    )


def validate_manifest(
    path: Path = DEFAULT_MANIFEST,
    *,
    repo_root: Path | None = None,
    cohort_path: Path = DEFAULT_COHORT,
) -> list[str]:
    root = repo_root or Path.cwd()
    if not path.is_file():
        return [f"manifest not found: {path}"]
    errors: list[str] = []
    rows = _load_tsv_rows(path)
    if not rows:
        errors.append("manifest has no data rows")
    try:
        _validate_cohort_binding(manifest_rows=rows, cohort_rows=_load_tsv_rows(cohort_path))
    except CalibrationReplayError as exc:
        errors.append(str(exc))
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


def _cli_path(repo_root: Path) -> Path:
    return repo_root / "python" / "cli.py"


def _dispatch_voters_for_row(
    *,
    repo_root: Path,
    row: Mapping[str, str],
    ballot_path: Path,
    plan_path: Path,
    diff_path: Path | None,
) -> dict[str, str]:
    v2_tool = (row.get("v2_tool") or "").strip()
    v1_tool = (row.get("v1_tool") or "").strip()
    codex_available, cursor_available = _availability_flags(v2_tool=v2_tool, v1_tool=v1_tool)
    argv = [
        sys.executable,
        str(_cli_path(repo_root)),
        "agent",
        "dispatch-voters",
        "--ballot-file",
        str(ballot_path),
        "--review-tmpdir",
        str(ballot_path.parent),
        "--plan-file",
        str(plan_path),
        "--codex-available",
        "true" if codex_available else "false",
        "--cursor-available",
        "true" if cursor_available else "false",
        "--round-num",
        "1",
        "--site",
        "calibration-replay",
    ]
    if diff_path is not None:
        argv.extend(["--diff-file", str(diff_path)])
    result = proc.run(argv, cwd=str(repo_root))
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    kv = {key: value for line in output.splitlines() if "=" in line for key, value in [line.split("=", 1)]}
    if result.returncode != 0:
        raise CalibrationReplayError(f"dispatch-voters failed for {(row.get('finding_id') or '').strip()}: {output.strip()}")
    finding_id = (row.get("finding_id") or "").strip()
    if kv.get("VOTER_2_STATUS") != "launched":
        raise CalibrationReplayError(
            f"dispatch-voters did not launch slot v2 for {finding_id}: "
            f"VOTER_2_STATUS={kv.get('VOTER_2_STATUS', '')}"
        )
    if kv.get("VOTER_2_PARSE_RATE_STATUS") != "OK":
        raise CalibrationReplayError(
            f"dispatch-voters parse guard failed for {finding_id}: "
            f"VOTER_2_PARSE_RATE_STATUS={kv.get('VOTER_2_PARSE_RATE_STATUS', '')}"
        )
    voter_2_tool = (kv.get("VOTER_2_TOOL") or "").strip()
    if not voter_2_tool:
        raise CalibrationReplayError(f"missing VOTER_2_TOOL for {finding_id}")
    if voter_2_tool != v2_tool:
        raise CalibrationReplayError(
            f"VOTER_2_TOOL mismatch for {finding_id}: expected {v2_tool}, got {voter_2_tool}"
        )
    voter_path = (kv.get("VOTER_2_PATH") or "").strip()
    if not voter_path:
        raise CalibrationReplayError(f"missing VOTER_2_PATH for {finding_id}")
    expected_basename = _expected_voter_2_output_name(v2_tool)
    if Path(voter_path).name != expected_basename:
        raise CalibrationReplayError(
            f"VOTER_2_PATH basename mismatch for {finding_id}: expected {expected_basename}, got {Path(voter_path).name}"
        )
    return kv


def run_replay(
    *,
    repo_root: Path,
    work_dir: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
    cohort_path: Path = DEFAULT_COHORT,
    dry_run: bool = False,
) -> list[dict[str, str]]:
    errors = validate_manifest(manifest_path, repo_root=repo_root, cohort_path=cohort_path)
    if errors:
        raise CalibrationReplayError("; ".join(errors))
    work_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []
    for row in _load_tsv_rows(manifest_path):
        finding_id = (row.get("finding_id") or "").strip()
        run_id = (row.get("run_id") or "").strip()
        round_num = int((row.get("round_num") or "0").strip())
        run_root = repo_root / "larch-logs" / "implement" / run_id
        fixture_ballot_raw = (row.get("fixture_ballot") or "").strip()
        fixture_ballot_path: Path | None
        if fixture_ballot_raw:
            fixture_ballot = _resolve_repo_path(repo_root=repo_root, raw=fixture_ballot_raw, field="fixture_ballot", required=True)
            if fixture_ballot is None or not fixture_ballot.is_file():
                raise CalibrationReplayError(f"fixture_ballot is not readable: {fixture_ballot_raw}")
            fixture_ballot_path = fixture_ballot
        else:
            fixture_ballot_path = None
        ballot, ballot_source = rebuild_single_item_ballot(
            finding_id=finding_id,
            run_root=run_root,
            round_num=round_num,
            fixture_ballot_path=fixture_ballot_path,
        )
        row_dir = work_dir / cohort_fixture_stem(run_id=run_id, finding_id=finding_id)
        row_dir.mkdir(parents=True, exist_ok=True)
        ballot_path = row_dir / "ballot.txt"
        ballot_path.write_text(ballot, encoding="utf-8")
        plan_path = _resolve_repo_path(repo_root=repo_root, raw=row.get("fixture_plan", ""), field="fixture_plan", required=True)
        if plan_path is None:
            raise CalibrationReplayError(f"fixture_plan missing for {finding_id}")
        diff_required = _parse_bool(row.get("diff_required", ""), field="diff_required")
        diff_path = _resolve_repo_path(repo_root=repo_root, raw=row.get("fixture_diff", ""), field="fixture_diff", required=diff_required)
        before_vote = _before_vote(repo_root=repo_root, row=row)
        result = {
            "finding_id": finding_id,
            "run_id": run_id,
            "round_num": str(round_num),
            "ballot_source": ballot_source,
            "before_vote": before_vote,
            "v2_tool": (row.get("v2_tool") or "").strip(),
            "fixture_plan": str(plan_path.relative_to(repo_root)),
            "fixture_diff": str(diff_path.relative_to(repo_root)) if diff_path is not None else "",
        }
        if not dry_run:
            dispatch_kv = _dispatch_voters_for_row(
                repo_root=repo_root,
                row=row,
                ballot_path=ballot_path,
                plan_path=plan_path,
                diff_path=diff_path,
            )
            voter_path = _resolve_voter_path(
                repo_root=repo_root,
                raw_path=dispatch_kv.get("VOTER_2_PATH", ""),
                ballot_parent=ballot_path.parent,
            )
            after_vote = _parse_slot_v2_vote(voter_path=voter_path, finding_id=finding_id)
            result["voter_2_path"] = dispatch_kv.get("VOTER_2_PATH", "")
            result["voter_2_status"] = dispatch_kv.get("VOTER_2_STATUS", "")
            result["voter_2_tool"] = dispatch_kv.get("VOTER_2_TOOL", "")
            result["voter_2_parse_rate_status"] = dispatch_kv.get("VOTER_2_PARSE_RATE_STATUS", "")
            result["after_vote"] = after_vote
        results.append(result)
    return results


def rebuild_ballot_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="calibration-replay rebuild-ballot")
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--round-num", required=True)
    parser.add_argument("--fixture-ballot", default="")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    if not str(args.round_num).isdigit() or int(str(args.round_num)) <= 0:
        print("REBUILD_STATUS=failed")
        print("ERROR=--round-num must be a positive integer")
        return 2
    repo_root = Path(str(args.repo_root)) if str(args.repo_root) else Path.cwd()
    fixture_raw = str(args.fixture_ballot)
    fixture_path: Path | None = None
    if fixture_raw:
        candidate = Path(fixture_raw)
        fixture_path = candidate if candidate.is_absolute() else repo_root / candidate
    try:
        ballot, source = rebuild_single_item_ballot(
            finding_id=str(args.finding_id),
            run_root=Path(str(args.run_root)),
            round_num=int(str(args.round_num)),
            fixture_ballot_path=fixture_path,
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
    parser.add_argument("--cohort", default=str(DEFAULT_COHORT))
    args = parser.parse_args(argv)
    try:
        errors = validate_manifest(
            Path(str(args.manifest)),
            repo_root=Path.cwd(),
            cohort_path=Path(str(args.cohort)),
        )
    except CalibrationReplayError as exc:
        errors = [str(exc)]
    if errors:
        print("MANIFEST_STATUS=failed")
        for error in errors:
            print(f"ERROR={error}")
        return 1
    print("MANIFEST_STATUS=ok")
    return 0


def run_replay_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="calibration-replay run-replay")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--cohort", default=str(DEFAULT_COHORT))
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        results = run_replay(
            repo_root=Path.cwd(),
            work_dir=Path(str(args.work_dir)),
            manifest_path=Path(str(args.manifest)),
            cohort_path=Path(str(args.cohort)),
            dry_run=bool(args.dry_run),
        )
    except CalibrationReplayError as exc:
        print("REPLAY_STATUS=failed")
        print(f"ERROR={exc}")
        return 1
    print("REPLAY_STATUS=ok")
    print(f"ROW_COUNT={len(results)}")
    before_votes = [row["before_vote"] for row in results]
    after_votes = [row["after_vote"] for row in results if row.get("after_vote")]
    print(f"YES_RATE_BEFORE={_yes_rate_label(before_votes)}")
    if after_votes:
        print(f"YES_RATE_AFTER={_yes_rate_label(after_votes)}")
    for index, row in enumerate(results, start=1):
        print(f"ROW_{index}_FINDING_ID={row['finding_id']}")
        print(f"ROW_{index}_RUN_ID={row['run_id']}")
        print(f"ROW_{index}_ROUND_NUM={row['round_num']}")
        print(f"ROW_{index}_BALLOT_SOURCE={row['ballot_source']}")
        print(f"ROW_{index}_BEFORE_VOTE={row['before_vote']}")
        if row.get("after_vote"):
            print(f"ROW_{index}_AFTER_VOTE={row['after_vote']}")
        print(f"ROW_{index}_V2_TOOL={row['v2_tool']}")
        print(f"ROW_{index}_FIXTURE_PLAN={row['fixture_plan']}")
        if row.get("fixture_diff"):
            print(f"ROW_{index}_FIXTURE_DIFF={row['fixture_diff']}")
        if row.get("voter_2_path"):
            print(f"ROW_{index}_VOTER_2_PATH={row['voter_2_path']}")
            print(f"ROW_{index}_VOTER_2_STATUS={row.get('voter_2_status', '')}")
            print(f"ROW_{index}_VOTER_2_TOOL={row.get('voter_2_tool', '')}")
            print(f"ROW_{index}_VOTER_2_PARSE_RATE_STATUS={row.get('voter_2_parse_rate_status', '')}")
    return 0
