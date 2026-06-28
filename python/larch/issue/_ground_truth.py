# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false, reportGeneralTypeIssues=false
# ruff: noqa: B905, FURB167, PERF401, PLC0415, PLR2004, PTH123, RET504, RUF005, RUF007, RUF100, S108, S607, SLF001, UP006, UP015, UP017, UP035, UP037
# pylint: skip-file
"""Ground-truth voter calibration: row types, corpus scanning, outcome analysis."""

from __future__ import annotations

import collections
import functools
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from larch.issue._oos import (
    _ground_truth_calibration_incentive_shipped,
    _ground_truth_run_dir_key,
    _has_not_planned_signal,
    _merged_issue_index,
    _normalize_oos_title,
    _reviewers_from_label,
    classify_oos_issue_fate,
    extract_issue_number_from_url,
    extract_repo_from_url,
    iter_filed_oos_records,
)
from larch.issue._report import default_category, issue_number, title_tokens
from larch.issue._util import (
    BODY_CAP,
    CATEGORY_PATTERNS,
    GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS,
    GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE,
    GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION,
    _parse_issue_number,
    issue_text,
    parse_iso,
)
from larch.review import voting


@dataclass(frozen=True)
class GroundTruthVoter:
    voter: str
    vote: str
    missing: int
    severity: str = ""


@dataclass
class GroundTruthRow:
    panel_kind: str
    path: Path
    run_dir: Path
    run_id: str
    round_num: int
    started_at: datetime | None
    raw_row: dict[str, str]
    header: list[str]
    reviewer_column: str
    voter_votes: list[tuple[str, str]]
    voters: list[GroundTruthVoter]
    is_oos: bool
    panel_verdict: str = ""
    oos_panel_verdict: str = ""
    weak_reason: str = ""
    prose_text: str = ""
    title: str = ""
    category: str = ""
    issue_number: int | None = None
    issue_url: str = ""
    run_dir_key: str = ""

    @property
    def finding_id(self) -> str:
        return (self.raw_row.get("finding_id") or "").strip()


@dataclass
class GroundTruthOutcome:
    row: GroundTruthRow
    bucket: str
    decisive: bool
    direction: str
    reason: str


@dataclass
class GroundTruthMetric:
    panel: str
    voter: str
    decisive: int = 0
    aligned: int = 0
    misaligned: int = 0
    missing: int = 0
    false_positive_yes: int = 0
    false_negative_no: int = 0


@dataclass
class GroundTruthSeverityMetric:
    panel: str
    voter: str
    severity: str
    decisive_yes: int = 0
    aligned: int = 0
    misaligned: int = 0
    missing_severity: int = 0


@dataclass
class GroundTruthStats:
    files_seen: int = 0
    skipped_files: int = 0
    scanned_rows: int = 0
    eligible_rows: int = 0
    ineligible_rows: int = 0
    prose_rows: int = 0
    gc_slimmed_runs: int = 0
    weak_rows: int = 0
    decisive_rows: int = 0
    timestamp_degraded: int = 0
    verdict_disagreement: int = 0
    rejected_oos_panel: int = 0
    enrichment_degraded_rows: int = 0
    large_corpus_skip: bool = False
    qualifying_runs: int = 0
    excluded_pre_since_runs: int = 0
    excluded_missing_started_at_runs: int = 0
    excluded_below_version_runs: int = 0
    excluded_missing_version_runs: int = 0
    excluded_gc_slimmed_runs: int = 0
    qualifying_run_dirs: set[Path] = field(default_factory=set)
    verdict_mode: bool = False
    since_date: datetime | None = None
    min_larch_version: str | None = None
    min_runs: int = 0
    incentive_era_shipped: bool = False
    incentive_gate_reason: str = ""
    enrichment_degraded: str | None = None
    targeted_fetch_degraded: str | None = None
    gate_result: bool = True
    gate_reason: str = ""
    buckets: collections.Counter[str] = field(default_factory=collections.Counter)


_GROUND_TRUTH_ROW_CACHE: dict[str, tuple[list[GroundTruthRow], GroundTruthStats]] = {}
_GROUND_TRUTH_FILED_CACHE: dict[str, list[dict[str, Any]]] = {}


def _copy_ground_truth_stats(stats: GroundTruthStats) -> GroundTruthStats:
    copied = GroundTruthStats(
        files_seen=stats.files_seen,
        skipped_files=stats.skipped_files,
        scanned_rows=stats.scanned_rows,
        eligible_rows=stats.eligible_rows,
        ineligible_rows=stats.ineligible_rows,
        prose_rows=stats.prose_rows,
        gc_slimmed_runs=stats.gc_slimmed_runs,
        weak_rows=stats.weak_rows,
        decisive_rows=stats.decisive_rows,
        timestamp_degraded=stats.timestamp_degraded,
        verdict_disagreement=stats.verdict_disagreement,
        rejected_oos_panel=stats.rejected_oos_panel,
        enrichment_degraded_rows=stats.enrichment_degraded_rows,
        large_corpus_skip=stats.large_corpus_skip,
        qualifying_runs=stats.qualifying_runs,
        excluded_pre_since_runs=stats.excluded_pre_since_runs,
        excluded_missing_started_at_runs=stats.excluded_missing_started_at_runs,
        excluded_below_version_runs=stats.excluded_below_version_runs,
        excluded_missing_version_runs=stats.excluded_missing_version_runs,
        excluded_gc_slimmed_runs=stats.excluded_gc_slimmed_runs,
        qualifying_run_dirs=set(stats.qualifying_run_dirs),
        verdict_mode=stats.verdict_mode,
        since_date=stats.since_date,
        min_larch_version=stats.min_larch_version,
        min_runs=stats.min_runs,
        incentive_era_shipped=stats.incentive_era_shipped,
        incentive_gate_reason=stats.incentive_gate_reason,
        enrichment_degraded=stats.enrichment_degraded,
        targeted_fetch_degraded=stats.targeted_fetch_degraded,
        gate_result=stats.gate_result,
        gate_reason=stats.gate_reason,
    )
    copied.buckets = collections.Counter(stats.buckets)
    return copied


def _reset_ground_truth_outcome_stats(stats: GroundTruthStats) -> None:
    stats.weak_rows = 0
    stats.decisive_rows = 0
    stats.timestamp_degraded = 0
    stats.verdict_disagreement = 0
    stats.rejected_oos_panel = 0
    stats.enrichment_degraded_rows = 0
    stats.buckets = collections.Counter()


@dataclass(frozen=True)
class GroundTruthEvidence:
    source: str
    run_id: str
    round_num: int
    started_at: datetime | None
    created_at: datetime | None
    title: str
    text: str
    category: str
    issue_number: int | None = None
    not_planned: bool = False
    run_dir_key: str = ""


_GT_HEADING_RE = re.compile(r"^###\s+((?:FINDING|OOS)_\d+):\s*(.*?)\s*$", re.M)
_GT_VOTE_TALLY_RESULT_RE = re.compile(r"\bResult\s*:\s*(accepted|rejected)\b", re.I)
_GT_REVERSAL_RE = re.compile(
    r"\b(revert|reverted|undo|regress|regression|superseded|re-introduce|re-add|closed in favor of)\b",
    re.I,
)


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _ground_truth_discover_classifiers(log_root: Path) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    for path in sorted(log_root.glob("design/*/plan-review/round-*/findings-classification.tsv")):
        paths.append(("design", path))
    for path in sorted(log_root.glob("implement/*/round-*/findings-classification.tsv")):
        paths.append(("code-review", path))
    for path in sorted(log_root.glob("review/*/review-findings-classification-round-*.tsv")):
        text = _safe_read_text(path)
        if voting.classification_tsv_schema_supported(text, panel_kind="code-review"):
            paths.append(("code-review", path))
    return paths


def _ground_truth_run_dir(path: Path, *, panel_kind: str) -> Path:
    parts = list(path.parts)
    if panel_kind == "design" and "plan-review" in parts:
        return path.parents[2]
    if "round-" in path.parent.name:
        return path.parents[1]
    return path.parent


def _ground_truth_round_num(path: Path) -> int:
    for part in reversed(path.parts):
        match = re.fullmatch(r"round-(\d+)", part)
        if match:
            return int(match.group(1))
    match = re.search(r"round-(\d+)", path.name)
    return int(match.group(1)) if match else 0


def _ground_truth_run_started_at(run_dir: Path) -> datetime | None:
    for name in ("manifest.json", "run-manifest.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, Mapping):
            return parse_iso(str(data.get("started_at") or data.get("updated_at") or ""))
    return None


def _ground_truth_run_started_at_strict(run_dir: Path) -> datetime | None:
    for name in ("manifest.json", "run-manifest.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, Mapping):
            started_at = parse_iso(str(data.get("started_at") or ""))
            if started_at is not None:
                return started_at
    return None


def _ground_truth_run_larch_version(run_dir: Path) -> str | None:
    for name in ("manifest.json", "run-manifest.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, Mapping):
            version = data.get("larch_version")
            if not version:
                continue
            text = str(version).strip()
            if _ground_truth_version_tuple(text) is not None:
                return text
    return None


def _ground_truth_version_tuple(version: str | None) -> tuple[int, ...] | None:
    if not version:
        return None
    raw_parts = str(version).strip().lstrip("vV").split(".")
    parts: list[int] = []
    for raw in raw_parts:
        match = re.match(r"(\d+)", raw)
        if not match:
            return None
        parts.append(int(match.group(1)))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _ground_truth_version_meets_floor( *,version: str | None, floor: str) -> bool:
    parsed = _ground_truth_version_tuple(version)
    parsed_floor = _ground_truth_version_tuple(floor)
    return parsed is not None and parsed_floor is not None and parsed >= parsed_floor


def _parse_ground_truth_since_date(value: str) -> datetime:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        raise SystemExit(f"ERROR=invalid --since-date {value!r}; expected YYYY-MM-DD")
    try:
        parsed = datetime.fromisoformat(value + "T00:00:00+00:00")
    except ValueError as exc:
        raise SystemExit(f"ERROR=invalid --since-date {value!r}; expected YYYY-MM-DD") from exc
    return parsed.astimezone(timezone.utc)


def _parse_ground_truth_min_runs(value: str) -> int:
    text = str(value or "").strip()
    if not text.isdigit():
        raise SystemExit(f"ERROR=invalid --min-runs {value!r}; expected a non-negative integer")
    return max(int(text), 0)


def _enforce_ground_truth_verdict_capstone_minima(
    *,
    since_date: datetime,
    min_larch_version: str,
    min_runs: int,
) -> tuple[datetime, str]:
    capstone_since = _parse_ground_truth_since_date(GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE)
    if since_date < capstone_since:
        raise SystemExit(
            f"ERROR=invalid --since-date {since_date.date().isoformat()}; "
            f"verdict mode requires >= {GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE}"
        )
    if not _ground_truth_version_meets_floor(
        version=min_larch_version,
        floor=GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION,
    ):
        raise SystemExit(
            f"ERROR=invalid --min-larch-version {min_larch_version!r}; "
            f"verdict mode requires >= {GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION}"
        )
    if min_runs < GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS:
        raise SystemExit(
            f"ERROR=invalid --min-runs {min_runs}; "
            f"verdict mode requires >= {GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS}"
        )
    return since_date, min_larch_version


def _ground_truth_run_ended_at(run_dir: Path) -> datetime | None:
    for name in ("manifest.json", "run-manifest.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, Mapping):
            ended = parse_iso(str(data.get("ended_at") or data.get("completed_at") or ""))
            if ended:
                return ended
            return parse_iso(str(data.get("updated_at") or ""))
    return None


def _run_has_round_local_jsonl(run_dir: Path) -> bool:
    return bool(
        list(run_dir.glob("round-*/review-findings-full.jsonl"))
        or list(run_dir.glob("plan-review/round-*/review-findings-full.jsonl"))
    )


def _markdown_blocks_by_heading(text: str) -> dict[str, tuple[str, str]]:
    matches = list(_GT_HEADING_RE.finditer(text or ""))
    blocks: dict[str, tuple[str, str]] = {}
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        blocks[match.group(1)] = (match.group(2).strip(), text[start:end].strip())
    return blocks


def _jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in _safe_read_text(path).splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(dict(parsed))
    return records


@functools.lru_cache(maxsize=2048)
def _cached_jsonl_records(path: Path) -> tuple[tuple[tuple[str, Any], ...], ...]:
    return tuple(tuple(record.items()) for record in _jsonl_records(path))


def _cached_jsonl_record_dicts(path: Path) -> list[dict[str, Any]]:
    return [dict(items) for items in _cached_jsonl_records(path)]


@functools.lru_cache(maxsize=512)
def _implement_prose_paths(run_dir: Path) -> tuple[Path, ...]:
    return tuple(sorted(run_dir.glob("review-findings-full.jsonl")) + sorted(run_dir.glob("round-*/review-findings-full.jsonl")))


@functools.lru_cache(maxsize=4096)
def _cached_markdown_blocks(path: Path) -> tuple[tuple[str, str, str], ...]:
    blocks = _markdown_blocks_by_heading(_safe_read_text(path))
    return tuple((key, title, body) for key, (title, body) in blocks.items())


def _cached_markdown_block_dict(path: Path) -> dict[str, tuple[str, str]]:
    return {key: (title, body) for key, title, body in _cached_markdown_blocks(path)}


def _row_finding_tokens(row: GroundTruthRow) -> set[str]:
    tokens = {row.finding_id}
    raw = row.finding_id
    if raw.startswith("FINDING_"):
        tokens.add(raw.replace("FINDING_", "REJ_CR", 1))
    if raw.startswith("OOS_"):
        tokens.add(raw)
    return {token for token in tokens if token}


_GT_FINDING_ID_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _gt_finding_id_pattern(finding_id: str) -> re.Pattern[str]:
    if finding_id not in _GT_FINDING_ID_RE_CACHE:
        _GT_FINDING_ID_RE_CACHE[finding_id] = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(finding_id) + r"(?![A-Za-z0-9_])")
    return _GT_FINDING_ID_RE_CACHE[finding_id]


def _jsonl_record_round_num(record: Mapping[str, Any]) -> int:
    try:
        return int(record.get("round_num") or 0)
    except (TypeError, ValueError):
        return 0


def _jsonl_record_round_matches_row(
    record: Mapping[str, Any],
    *,
    row: GroundTruthRow,
    path_round: int = 0,
    require_explicit_round: bool = False,
    multi_round: bool = False,
) -> bool:
    rec_round = _jsonl_record_round_num(record)
    if require_explicit_round and row.round_num and rec_round != row.round_num:
        return False
    if rec_round and row.round_num and rec_round != row.round_num:
        return False
    if path_round and not rec_round and row.round_num and path_round != row.round_num:
        return False
    return not (multi_round and row.round_num and not rec_round and path_round == 0)


def _jsonl_record_matches_row(
    record: Mapping[str, Any],
    *,
    row: GroundTruthRow,
    path_round: int = 0,
    require_explicit_round: bool = False,
) -> bool:
    if not _jsonl_record_round_matches_row(
        record,
        row=row,
        path_round=path_round,
        require_explicit_round=require_explicit_round,
        multi_round=_run_has_multiple_rounds(row.run_dir),
    ):
        return False
    pattern = _gt_finding_id_pattern(row.finding_id) if row.finding_id else None
    body = str(record.get("prose_body") or record.get("body") or "")
    rec_id = str(record.get("id") or "")
    title = str(record.get("title") or "")
    haystack = f"{rec_id}\n{title}\n{body}"
    return rec_id == row.finding_id or (pattern is not None and bool(pattern.search(haystack)))


def _design_jsonl_verdict_for_row(row: GroundTruthRow) -> str:
    outcomes: list[str] = []
    for record in _cached_jsonl_record_dicts(row.run_dir / "review-findings-full.jsonl"):
        if not _jsonl_record_matches_row(record, row=row):
            continue
        outcome = str(record.get("outcome") or "").strip().lower()
        if outcome in {"accepted", "rejected"}:
            outcomes.append(outcome)
    if not outcomes:
        return ""
    if len(set(outcomes)) == 1:
        return outcomes[0]
    return "ambiguous"


def _run_has_multiple_rounds(run_dir: Path) -> bool:
    implement_rounds = sum(1 for path in run_dir.glob("round-*") if path.is_dir())
    design_rounds = sum(1 for path in run_dir.glob("plan-review/round-*") if path.is_dir())
    return implement_rounds > 1 or design_rounds > 1


def _filed_record_round_num(record: Mapping[str, Any]) -> int:
    identity = record.get("identity")
    if isinstance(identity, tuple) and len(identity) >= 2:
        return _ground_truth_round_num(Path(str(identity[1])))
    artifact = str(record.get("artifact_relpath") or "")
    if artifact:
        return _ground_truth_round_num(Path(artifact))
    return 0


def _row_reviewer_tokens(row: GroundTruthRow) -> set[str]:
    raw = (row.raw_row.get(row.reviewer_column) or row.raw_row.get("finding_reviewers") or "").strip()
    if not raw:
        return set()
    return {token.lower() for token in _reviewers_from_label(label=raw)}


def _filed_record_reviewer_matches(record: Mapping[str, Any], *, row_tokens: set[str]) -> bool:
    if not row_tokens:
        return True
    rec_reviewer = str(record.get("reviewer") or "unknown").strip().lower()
    if rec_reviewer == "unknown":
        return False
    return rec_reviewer in row_tokens or any(token in rec_reviewer or rec_reviewer in token for token in row_tokens)


def _implement_prose_for_row(row: GroundTruthRow) -> dict[str, str]:
    candidates: list[dict[str, str]] = []
    pattern = _gt_finding_id_pattern(row.finding_id) if row.finding_id else None
    tokens = _row_finding_tokens(row)
    multi_round = _run_has_multiple_rounds(row.run_dir)
    require_explicit_round = row.round_num > 0 and row.path.name.startswith("review-findings-classification-round-")
    for path in _implement_prose_paths(row.run_dir):
        path_round = _ground_truth_round_num(path)
        if multi_round and row.round_num and path_round == 0 and _run_has_round_local_jsonl(row.run_dir):
            continue
        for record in _cached_jsonl_record_dicts(path):
            if not _jsonl_record_round_matches_row(
                record,
                row=row,
                path_round=path_round,
                require_explicit_round=require_explicit_round,
                multi_round=multi_round,
            ):
                continue
            body = str(record.get("prose_body") or record.get("body") or "")
            rec_id = str(record.get("id") or "")
            title = str(record.get("title") or "")
            haystack = f"{rec_id}\n{title}\n{body}"
            # F13: use word-boundary / exact matching instead of bare substring containment
            exact_match = rec_id == row.finding_id or (pattern is not None and pattern.search(haystack))
            token_match = any(_gt_finding_id_pattern(t).search(haystack) for t in tokens if t != row.finding_id)
            if exact_match or token_match:
                candidates.append({
                    "outcome": str(record.get("outcome") or ""),
                    "category": str(record.get("category") or ""),
                    "text": body or title,
                    "title": title,
                })
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        same_outcome = {item["outcome"] for item in candidates}
        if len(same_outcome) == 1:
            return candidates[0]
        return {"weak": "cross-round or multi-match ambiguity"}
    return {}


def _standalone_review_prose_for_row(row: GroundTruthRow) -> dict[str, str]:
    candidates: list[dict[str, str]] = []
    path_round = row.round_num or _ground_truth_round_num(row.path)
    require_explicit_round = row.round_num > 0 and row.path.name.startswith("review-findings-classification-round-")
    for name in ("review-findings.ndjson", "review-findings-full.jsonl"):
        record_path = row.path.with_name(name)
        for record in _cached_jsonl_record_dicts(record_path):
            if not _jsonl_record_matches_row(record, row=row, path_round=path_round, require_explicit_round=require_explicit_round):
                continue
            body = str(record.get("prose_body") or record.get("body") or "")
            candidates.append({
                "outcome": str(record.get("outcome") or ""),
                "category": str(record.get("category") or ""),
                "text": body or str(record.get("title") or ""),
                "title": str(record.get("title") or ""),
            })
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        same_outcome = {item["outcome"] for item in candidates}
        if len(same_outcome) == 1:
            return candidates[0]
        return {"weak": "cross-round or multi-match ambiguity"}
    return {}


def _design_markdown_verdict(row: GroundTruthRow) -> dict[str, str]:
    round_dir = row.path.parent
    local_accepted = _cached_markdown_block_dict(round_dir / "accepted-plan-findings.md")
    local_rejected = _cached_markdown_block_dict(round_dir / "rejected-findings.md")
    root_accepted = _cached_markdown_block_dict(row.run_dir / "accepted-plan-findings.md")
    root_rejected = _cached_markdown_block_dict(row.run_dir / "rejected-findings.md")

    def verdict_from(*, accepted: Mapping[str, tuple[str, str]], rejected: Mapping[str, tuple[str, str]]) -> tuple[str, str, str]:
        in_accepted = row.finding_id in accepted
        in_rejected = row.finding_id in rejected
        if in_accepted == in_rejected:
            return "", "", ""
        title, text = accepted[row.finding_id] if in_accepted else rejected[row.finding_id]
        return ("accepted" if in_accepted else "rejected", title, text)

    local = verdict_from(accepted=local_accepted, rejected=local_rejected)
    root = verdict_from(accepted=root_accepted, rejected=root_rejected)
    local_files_exist = (round_dir / "accepted-plan-findings.md").is_file() or (round_dir / "rejected-findings.md").is_file()

    def bind_markdown_verdict(*, outcome: str, title: str, text: str) -> dict[str, str]:
        jsonl_outcome = _design_jsonl_verdict_for_row(row)
        if jsonl_outcome == "ambiguous":
            return {"weak": "design JSONL multi-match ambiguity"}
        if jsonl_outcome and outcome and jsonl_outcome != outcome:
            return {"weak": "design markdown/JSONL verdict disagreement"}
        return {"outcome": outcome, "title": title, "text": text}

    if local[0]:
        if root[0] and root[0] != local[0]:
            return {"weak": "design round-local/run-root verdict disagreement"}
        return bind_markdown_verdict(outcome=local[0], title=local[1], text=local[2])
    if local_files_exist:
        # F12: round-local files exist but finding absent — don't fall back to run-root
        return {"weak": "round-local verdict files present but finding absent"}
    if root[0]:
        return bind_markdown_verdict(outcome=root[0], title=root[1], text=root[2])
    for record in _cached_jsonl_record_dicts(row.run_dir / "review-findings-full.jsonl"):
        if not _jsonl_record_matches_row(record, row=row):
            continue
        body = str(record.get("prose_body") or record.get("body") or "")
        return {
            "outcome": str(record.get("outcome") or ""),
            "category": str(record.get("category") or ""),
            "title": str(record.get("title") or ""),
            "text": body,
        }
    return {}


def _bind_ground_truth_prose(row: GroundTruthRow) -> None:
    prose = _design_markdown_verdict(row) if row.panel_kind == "design" else _implement_prose_for_row(row)
    if not prose and row.path.name.startswith("review-findings-classification-round-"):
        prose = _standalone_review_prose_for_row(row)
    outcome = str(prose.get("outcome") or "").strip().lower()
    row.prose_text = str(prose.get("text") or "")
    row.title = str(prose.get("title") or "") or row.finding_id
    row.category = str(prose.get("category") or "")
    if row.prose_text:
        row.prose_text = row.prose_text[:BODY_CAP]
    if row.is_oos:
        row.oos_panel_verdict = _ground_truth_oos_panel_verdict(row)
    if prose.get("weak") and not (row.is_oos and row.oos_panel_verdict in {"accepted", "rejected"}):
        row.weak_reason = str(prose["weak"])
        return
    if row.is_oos:
        pass
    elif outcome in {"accepted", "rejected"}:
        row.panel_verdict = outcome
        tsv_result = (row.raw_row.get("voting_result") or "").strip().lower()
        if tsv_result in {"accepted", "rejected"} and tsv_result != outcome:
            row.weak_reason = "TSV/prose verdict disagreement"
    elif outcome == "out_of_scope":
        row.weak_reason = "out-of-scope prose is not an in-scope verdict"
    if row.prose_text or row.panel_verdict or row.oos_panel_verdict:
        return
    row.weak_reason = "missing prose verdict"


def _parse_voting_tally_row_result(tally_text: str, *, finding_id: str) -> str:
    if not tally_text or not finding_id:
        return ""
    for line in tally_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [part.strip() for part in stripped.strip("|").split("|")]
        if not parts or parts[0] != finding_id:
            continue
        for part in reversed(parts[1:]):
            lowered = part.lower()
            if lowered in {"accepted", "rejected"}:
                return lowered
    return ""


def _ground_truth_oos_panel_verdict(row: GroundTruthRow) -> str:
    result = (row.raw_row.get("voting_result") or "").strip().lower()
    tally_result = _parse_voting_tally_row_result(_safe_read_text(row.path.with_name("voting-tally.md")), finding_id=row.finding_id)
    if not tally_result:
        tally_text = _safe_read_text(row.path.with_name("vote-tally.md"))
        tally_match = _GT_VOTE_TALLY_RESULT_RE.search(tally_text)
        tally_result = tally_match.group(1).lower() if tally_match else ""
    if result in {"accepted", "rejected"} and tally_result in {"accepted", "rejected"}:
        if result != tally_result:
            return ""  # TSV/tally disagreement → non-decisive (F18)
        return result
    if result in {"accepted", "rejected"}:
        return result
    if tally_result in {"accepted", "rejected"}:
        return tally_result
    prose_tally_match = _GT_VOTE_TALLY_RESULT_RE.search(row.prose_text)
    return prose_tally_match.group(1).lower() if prose_tally_match else ""


def _normalize_diagnostic_path(raw: str) -> str:
    value = (raw or "").strip("`*_#[](){}<>.,;:'\"")
    value = re.sub(r":\d+(?:-\d+)?$", "", value)
    value = value.lstrip("./").lower()
    if not value or ".." in value.split("/") or value.startswith(("/", "~")):
        return ""
    return value


@functools.lru_cache(maxsize=65536)
def _diagnostic_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for regex in (voting.FILE_LINE_REGEXES["any-re"], voting.FILE_LINE_REGEXES["extensionless-re"]):
        for match in re.finditer(regex, text or "", re.I):
            candidate = ""
            groups = [group for group in match.groups() if group]
            if groups:
                candidate = groups[0] if "/" in groups[0] or "." in groups[0] else match.group(0)
            candidate = _normalize_diagnostic_path(candidate or match.group(0))
            if candidate:
                paths.add(candidate)
    return paths


@functools.lru_cache(maxsize=65536)
def _distinctive_tokens(text: str) -> set[str]:
    return set(title_tokens(text))


def _strong_ground_truth_match(row: GroundTruthRow, *, evidence: GroundTruthEvidence) -> bool:
    source_text = f"{row.title}\n{row.prose_text}\n{row.finding_id}"
    source_paths = _diagnostic_paths(source_text)
    evidence_paths = _diagnostic_paths(f"{evidence.title}\n{evidence.text}")
    source_tokens = _distinctive_tokens(source_text)
    evidence_tokens = _distinctive_tokens(f"{evidence.title}\n{evidence.text}")
    overlap = source_tokens & evidence_tokens
    if source_paths & evidence_paths and len(overlap) >= 2:
        return True
    if min(len(source_tokens), len(evidence_tokens)) <= 4:
        return len(overlap) >= max(2, min(len(source_tokens), len(evidence_tokens)))
    return len(overlap) >= max(3, int(min(len(source_tokens), len(evidence_tokens)) * 0.6))


def _ground_truth_panel_root(run_dir_key: str) -> str:
    return run_dir_key.split("/", 1)[0] if run_dir_key else ""


def _evidence_later_than_row(row: GroundTruthRow, *, evidence: GroundTruthEvidence) -> tuple[bool, str]:
    if (
        evidence.source == "accepted-finding"
        and evidence.run_dir_key
        and _ground_truth_panel_root(evidence.run_dir_key) != _ground_truth_panel_root(row.run_dir_key)
    ):
        return False, "accepted-finding panel root mismatch"
    if evidence.run_dir_key and evidence.run_dir_key == row.run_dir_key:
        if evidence.round_num > row.round_num:
            return True, ""
        return False, "same-run round ordering is not later"
    if evidence.source == "issue" and not evidence.run_id:
        if row.started_at and evidence.created_at:
            if evidence.created_at <= row.started_at:
                return False, "not later"
            if _run_has_multiple_rounds(row.run_dir):
                run_ended = _ground_truth_run_ended_at(row.run_dir)
                if run_ended and evidence.created_at > run_ended:
                    return True, ""
                return False, "same-run round ordering unproved"
            return True, ""
        return False, "timestamp-degraded"
    if row.started_at and evidence.started_at:
        return (evidence.started_at > row.started_at), "" if evidence.started_at > row.started_at else "not later"
    if row.started_at and evidence.created_at:
        return (evidence.created_at > row.started_at), "" if evidence.created_at > row.started_at else "not later"
    return False, "timestamp-degraded"


def _ground_truth_issue_evidence(issues: Sequence[Mapping[str, Any]]) -> list[GroundTruthEvidence]:
    evidence: list[GroundTruthEvidence] = []
    for issue in issues:
        title = str(issue.get("title") or "")
        text = issue_text(issue=issue)
        evidence.append(
            GroundTruthEvidence(
                source="issue",
                run_id="",
                run_dir_key="",
                round_num=0,
                started_at=None,
                created_at=parse_iso(str(issue.get("createdAt") or "")),
                title=title,
                text=text,
                category=default_category(issue),
                issue_number=issue_number(issue),
                not_planned=_has_not_planned_signal(issue),  # F3
            )
        )
    return evidence


def _ground_truth_accepted_finding_evidence(rows: Sequence[GroundTruthRow]) -> list[GroundTruthEvidence]:
    out: list[GroundTruthEvidence] = []
    for row in rows:
        if row.is_oos or row.panel_verdict != "accepted" or row.weak_reason:
            continue
        out.append(
            GroundTruthEvidence(
                source="accepted-finding",
                run_id=row.run_id,
                run_dir_key=row.run_dir_key,
                round_num=row.round_num,
                started_at=row.started_at,
                created_at=None,
                title=row.title or row.finding_id,
                text=row.prose_text,
                category=row.category,
            )
        )
    return out


def _ground_truth_evidence_token_index(evidence: Sequence[GroundTruthEvidence]) -> dict[str, list[GroundTruthEvidence]]:
    index: dict[str, list[GroundTruthEvidence]] = collections.defaultdict(list)
    for item in evidence:
        for token in _distinctive_tokens(f"{item.title}\n{item.text}"):
            index[token].append(item)
    return dict(index)


def _candidate_evidence_for_row(
    row: GroundTruthRow,
    *,
    issue_evidence: Sequence[GroundTruthEvidence],
    accepted_evidence: Sequence[GroundTruthEvidence],
    accepted_index: Mapping[str, Sequence[GroundTruthEvidence]],
) -> list[GroundTruthEvidence]:
    source_tokens = _distinctive_tokens(f"{row.title}\n{row.prose_text}\n{row.finding_id}")
    source_paths = _diagnostic_paths(f"{row.title}\n{row.prose_text}")
    # F14: filter issue evidence by token overlap before cap rather than taking all unfiltered
    filtered_issues: list[tuple[int, GroundTruthEvidence]] = []
    for item in issue_evidence:
        item_tokens = _distinctive_tokens(f"{item.title}\n{item.text}")
        overlap = len(source_tokens & item_tokens)
        if overlap == 0:
            item_paths = _diagnostic_paths(f"{item.title}\n{item.text}")
            if not (source_paths & item_paths):
                continue
        filtered_issues.append((overlap, item))
    filtered_issues.sort(key=lambda t: t[0], reverse=True)
    if row.panel_verdict == "rejected":
        accepted_candidates: list[GroundTruthEvidence] = []
        seen: set[tuple[str, str, int]] = set()
        for token in source_tokens:
            for item in accepted_index.get(token, ()):
                if _ground_truth_panel_root(item.run_dir_key) != _ground_truth_panel_root(row.run_dir_key):
                    continue
                key = (item.run_dir_key, item.title, item.round_num)
                if key in seen:
                    continue
                seen.add(key)
                accepted_candidates.append(item)
        issue_candidates = [item for _, item in filtered_issues]
        return accepted_candidates + issue_candidates
    candidates: list[GroundTruthEvidence] = [item for _, item in filtered_issues]
    if len(accepted_evidence) < 50:
        row_panel = _ground_truth_panel_root(row.run_dir_key)
        candidates.extend(
            item for item in accepted_evidence if _ground_truth_panel_root(item.run_dir_key) == row_panel
        )
    return candidates


def _ground_truth_row_title_from_oos_record(record: Mapping[str, Any]) -> str:
    return _normalize_oos_title(str(record.get("title") or ""))


def _filed_record_round_matches(row: GroundTruthRow, *, record: Mapping[str, Any]) -> bool:
    rec_round = _filed_record_round_num(record)
    if not row.round_num:
        return True
    if rec_round == row.round_num:
        return True
    if rec_round and rec_round != row.round_num:
        return False
    artifact = str(record.get("artifact_relpath") or "")
    identity = record.get("identity")
    paths: list[str] = []
    if artifact:
        paths.append(artifact)
    if isinstance(identity, tuple) and len(identity) >= 2:
        paths.append(str(identity[1]))
    return any(f"round-{row.round_num}" in path_str for path_str in paths)


def _match_oos_filed_record(row: GroundTruthRow, *, records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    row_tokens = _distinctive_tokens(f"{row.title}\n{row.prose_text}\n{row.finding_id}")
    reviewer_tokens = _row_reviewer_tokens(row)
    id_matches: list[Mapping[str, Any]] = []
    token_matches: list[Mapping[str, Any]] = []
    for record in records:
        if str(record.get("run_dir_key") or "") != row.run_dir_key:
            continue
        if str(record.get("bucket") or ""):
            continue
        if not _filed_record_round_matches(row, record=record):
            continue
        stable = str(record.get("stable_id") or "")
        identity = " ".join(str(part) for part in (record.get("identity") or ()))
        if row.finding_id and (stable.endswith(":" + row.finding_id) or stable == row.finding_id or _gt_finding_id_pattern(row.finding_id).search(identity)):
            id_matches.append(record)
            continue
        record_tokens = _distinctive_tokens(_ground_truth_row_title_from_oos_record(record))
        if (
            row_tokens
            and record_tokens
            and len(row_tokens & record_tokens) >= min(2, len(row_tokens), len(record_tokens))
            and _filed_record_reviewer_matches(record, row_tokens=reviewer_tokens)
        ):
            token_matches.append(record)
    if len(id_matches) == 1:
        return id_matches[0]
    if len(id_matches) > 1:
        return None
    if len(token_matches) == 1:
        return token_matches[0]
    return None


def _ground_truth_oos_outcome(
    row: GroundTruthRow,
    *,
    filed_records: Sequence[Mapping[str, Any]],
    issue_index: Mapping[int, Mapping[str, Any]],
    enrichment_degraded: str | None,
    stats: GroundTruthStats,
    repo: str | None = None,
) -> GroundTruthOutcome:
    if row.oos_panel_verdict != "accepted":
        if row.oos_panel_verdict == "rejected":
            stats.rejected_oos_panel += 1
            return GroundTruthOutcome(row=row, bucket="rejected_oos_panel", decisive=False, direction="", reason="rejected OOS panel result is non-decisive")
        return GroundTruthOutcome(row=row, bucket="weak_oos_panel_verdict", decisive=False, direction="", reason="missing or weak OOS panel verdict")
    record = _match_oos_filed_record(row, records=filed_records)
    if not record:
        return GroundTruthOutcome(row=row, bucket="missing_filed_oos_join", decisive=False, direction="", reason="no filed OOS issue join")
    issue_url = str(record.get("issue_url") or "")
    if repo and issue_url:
        url_repo = extract_repo_from_url(issue_url)
        if url_repo and url_repo.lower() != repo.lower():
            return GroundTruthOutcome(row=row, bucket="missing_filed_oos_join", decisive=False, direction="", reason="filed OOS issue repo mismatch")
    parsed_number, _reason = _parse_issue_number(record.get("issue_number"))
    if parsed_number is None:
        parsed_number = extract_issue_number_from_url(str(record.get("issue_url") or ""))
    issue = issue_index.get(parsed_number) if parsed_number else None
    if issue is None and enrichment_degraded:
        stats.enrichment_degraded_rows += 1
        return GroundTruthOutcome(row=row, bucket="enrichment unavailable", decisive=False, direction="", reason="GitHub issue enrichment unavailable")
    fate = classify_oos_issue_fate(issue)
    bucket = str(fate.get("bucket") or "provisional unknown")
    if bucket in {"docked closed-unfixed", "docked combined-away"}:
        return GroundTruthOutcome(row=row, bucket=bucket, decisive=True, direction="contradicts_acceptance", reason="accepted OOS filed issue later docked")
    return GroundTruthOutcome(row=row, bucket=bucket, decisive=False, direction="", reason="accepted OOS fate is provisional or kept")


def _ground_truth_in_scope_outcome(
    row: GroundTruthRow,
    *,
    evidence: Sequence[GroundTruthEvidence],
    enrichment_degraded: str | None,
    stats: GroundTruthStats,
) -> GroundTruthOutcome:
    if row.weak_reason:
        if "disagreement" in row.weak_reason:
            stats.verdict_disagreement += 1
        return GroundTruthOutcome(row=row, bucket="weak_prose_verdict", decisive=False, direction="", reason=row.weak_reason)
    if row.panel_verdict not in {"accepted", "rejected"}:
        return GroundTruthOutcome(row=row, bucket="weak_panel_verdict", decisive=False, direction="", reason="missing authoritative panel verdict")
    if enrichment_degraded:
        stats.enrichment_degraded_rows += 1
    for item in evidence:
        later, reason = _evidence_later_than_row(row, evidence=item)
        if not later:
            if reason == "timestamp-degraded":
                stats.timestamp_degraded += 1
            continue
        if not _strong_ground_truth_match(row, evidence=item):
            continue
        text = f"{item.title}\n{item.text}\n{item.category}"
        if row.panel_verdict == "accepted":
            if _GT_REVERSAL_RE.search(text):
                # F15: enrichment_degraded asymmetry fix — suppress issue-backed reversal when degraded
                if enrichment_degraded and item.source == "issue":
                    return GroundTruthOutcome(row=row, bucket="enrichment-degraded-reversal", decisive=False, direction="", reason="issue-backed reversal suppressed by enrichment degradation")
                return GroundTruthOutcome(row=row, bucket="accepted_reverted_or_regressed", decisive=True, direction="contradicts_acceptance", reason="later matching reversal or regression signal")
            continue
        if item.source == "accepted-finding" or item.category in {"Bug fix", "Test coverage", "Hardening/validation/security"} or CATEGORY_PATTERNS[1][1].search(text):
            if enrichment_degraded and item.source == "issue":
                return GroundTruthOutcome(row=row, bucket="enrichment-degraded-resurfacing", decisive=False, direction="", reason="issue-backed resurfacing suppressed by enrichment degradation")
            # F3: NOT_PLANNED closed issues without reversal wording are non-decisive
            if item.source == "issue" and item.not_planned and not _GT_REVERSAL_RE.search(text):
                continue
            return GroundTruthOutcome(row=row, bucket="rejected_resurfaced", decisive=True, direction="supports_acceptance", reason="later matching issue or accepted finding")
    if row.panel_verdict == "accepted":
        return GroundTruthOutcome(row=row, bucket="accepted_no_counterevidence", decisive=False, direction="", reason="no later matching reversal signal")
    return GroundTruthOutcome(row=row, bucket="rejected_not_observed", decisive=False, direction="", reason="no later strong resurfacing match")


def _ground_truth_update_metrics(metrics: dict[tuple[str, str], GroundTruthMetric], *, outcome: GroundTruthOutcome) -> None:
    if not outcome.decisive:
        return
    for voter in outcome.row.voters:
        key = (outcome.row.panel_kind, voter.voter)
        metric = metrics.setdefault(key, GroundTruthMetric(panel=outcome.row.panel_kind, voter=voter.voter))
        vote = voter.vote.strip().upper()
        if voter.missing or vote not in {"YES", "NO"}:
            metric.missing += 1
            continue
        metric.decisive += 1
        yes_aligned = outcome.direction == "supports_acceptance"
        aligned = (vote == "YES" and yes_aligned) or (vote == "NO" and not yes_aligned)
        if aligned:
            metric.aligned += 1
        else:
            metric.misaligned += 1
            if vote == "YES" and outcome.direction == "contradicts_acceptance":
                metric.false_positive_yes += 1
            if vote == "NO" and outcome.direction == "supports_acceptance":
                metric.false_negative_no += 1


def _ground_truth_update_severity_metrics(
    metrics: dict[tuple[str, str, str], GroundTruthSeverityMetric],
    *,
    outcome: GroundTruthOutcome,
) -> None:
    if not outcome.decisive:
        return
    yes_aligned = outcome.direction == "supports_acceptance"
    for voter in outcome.row.voters:
        vote = voter.vote.strip().upper()
        if voter.missing or vote != "YES":
            continue
        severity = voter.severity.strip()
        key = (outcome.row.panel_kind, voter.voter, severity or "(missing)")
        metric = metrics.setdefault(
            key,
            GroundTruthSeverityMetric(
                panel=outcome.row.panel_kind,
                voter=voter.voter,
                severity=severity or "(missing)",
            ),
        )
        metric.decisive_yes += 1
        if not severity:
            metric.missing_severity += 1
        if yes_aligned:
            metric.aligned += 1
        else:
            metric.misaligned += 1


def _ground_truth_rate(aligned: int, *, misaligned: int) -> str:
    denominator = aligned + misaligned
    return "n/a" if denominator == 0 else f"{aligned / denominator:.3f}"


def _render_ground_truth_report(
    *,
    log_root: Path,
    stats: GroundTruthStats,
    outcomes: Sequence[GroundTruthOutcome],
    metrics: Mapping[tuple[str, str], GroundTruthMetric],
    severity_metrics: Mapping[tuple[str, str, str], GroundTruthSeverityMetric],
    enrichment_degraded: str | None,
    top_k: int,
) -> str:
    lines = ["## Ground-truth Verdict for Token Allocation" if stats.verdict_mode else "## Ground-truth Voter Calibration"]
    lines.append("")
    if stats.verdict_mode:
        lines.append("Capstone evidence for token-allocation decision.")
        degraded_reasons = [reason for reason in (stats.enrichment_degraded, stats.targeted_fetch_degraded) if reason]
        if degraded_reasons:
            lines.append(f"- Degraded evidence: {', '.join(degraded_reasons)}.")
        if stats.large_corpus_skip:
            lines.append(
                "- Note: corpus exceeds 5000 rows; accepted-finding index disabled. "
                "OOS filed-issue join still evaluated. Per-voter rates may be incomplete."
            )
        since_text = stats.since_date.date().isoformat() if stats.since_date else "none"
        lines.extend(
            [
                "",
                "Verdict corpus:",
                f"- Log root: `{log_root}`",
                f"- Since date: {since_text}",
                f"- Min larch version: {stats.min_larch_version or 'none'}",
                f"- Required runs: {stats.min_runs}",
                f"- Qualifying runs: {stats.qualifying_runs}",
                f"- Excluded pre-since runs: {stats.excluded_pre_since_runs}",
                f"- Excluded missing `started_at` runs: {stats.excluded_missing_started_at_runs}",
                f"- Excluded below-version runs: {stats.excluded_below_version_runs}",
                f"- Excluded missing-version runs: {stats.excluded_missing_version_runs}",
                f"- Excluded `gc-slimmed` runs: {stats.excluded_gc_slimmed_runs}",
                f"- Classification TSV files scanned: {stats.files_seen}",
                f"- Classification rows scanned: {stats.scanned_rows}",
                f"- Eligible rows with parseable voter ballots: {stats.eligible_rows}",
                f"- Decisive realized rows: {stats.decisive_rows}",
                f"- Weak/provisional/non-decisive rows: {stats.weak_rows}",
                f"- Incentive-era shipped: {'yes' if stats.incentive_era_shipped else 'no'}",
                f"- Incentive gate reason: {stats.incentive_gate_reason}",
                f"- Enrichment degraded: {stats.enrichment_degraded or 'none'}",
                f"- Targeted fetch degraded: {stats.targeted_fetch_degraded or 'none'}",
                f"- Gate result: {'PASS' if stats.gate_result else 'FAIL'}",
                f"- Gate reason: {stats.gate_reason}",
                "",
                "Outcome buckets:",
                "| Bucket | Rows | Decisive |",
                "|---|---:|---:|",
            ]
        )
    else:
        lines.append("Diagnostic only. This section does not change live scoring, thresholds, tokens, or reviewer points.")
        if enrichment_degraded:
            lines.append(
                f"- Note: GitHub issue enrichment unavailable ({enrichment_degraded}); "
                "in-scope realized-outcome buckets may be suppressed or partial."
            )
        if stats.large_corpus_skip:
            lines.append(
                "- Note: corpus exceeds 5000 rows; accepted-finding index disabled. "
                "OOS filed-issue join still evaluated. Per-voter rates may be incomplete."
            )
        lines.extend(
            [
                "",
                "Corpus:",
                f"- Log root: `{log_root}`",
                f"- Classification TSV files scanned: {stats.files_seen}",
                f"- Unsupported TSV files skipped: {stats.skipped_files}",
                f"- Classification rows scanned: {stats.scanned_rows}",
                f"- Eligible rows with parseable voter ballots: {stats.eligible_rows}",
                f"- Ineligible rows: {stats.ineligible_rows}",
                f"- Rows with prose evidence: {stats.prose_rows}",
                f"- GC-slimmed or missing voter TSV runs: {stats.gc_slimmed_runs}",
                f"- Decisive realized rows: {stats.decisive_rows}",
                f"- Weak/provisional/non-decisive rows: {stats.weak_rows}",
                f"- Timestamp-degraded matches: {stats.timestamp_degraded}",
                f"- Verdict-disagreement rows: {stats.verdict_disagreement}",
                f"- Rejected-OOS-panel rows: {stats.rejected_oos_panel}",
                f"- Enrichment-degraded rows: {stats.enrichment_degraded_rows}",
                "",
                "Outcome buckets:",
                "| Bucket | Rows | Decisive |",
                "|---|---:|---:|",
            ]
        )
    bucket_decisive: collections.Counter[str] = collections.Counter()
    for outcome in outcomes:
        if outcome.decisive:
            bucket_decisive[outcome.bucket] += 1
    if stats.buckets:
        for bucket, count in sorted(stats.buckets.items()):
            lines.append(f"| {bucket} | {count} | {bucket_decisive.get(bucket, 0)} |")
    else:
        lines.append("| no-evidence | 0 | 0 |")
    lines.extend(
        [
            "",
            "Per-voter realized alignment:",
            "| Panel | Voter | Decisive | Aligned | Misaligned | Missing | Realized alignment | False positive YES | False negative NO |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    if metrics:
        for (_panel, _voter), metric in sorted(metrics.items()):
            lines.append(
                f"| {metric.panel} | {metric.voter} | {metric.decisive} | {metric.aligned} | "
                f"{metric.misaligned} | {metric.missing} | {_ground_truth_rate(metric.aligned, misaligned=metric.misaligned)} | "
                f"{metric.false_positive_yes} | {metric.false_negative_no} |"
            )
    else:
        lines.append("| n/a | n/a | 0 | 0 | 0 | 0 | n/a | 0 | 0 |")
    lines.extend(
        [
            "",
            "Severity slice for decisive YES votes:",
            "| Panel | Voter | Severity | Decisive YES rows | Aligned | Misaligned | Realized alignment | Missing-severity rows |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    if severity_metrics:
        for (_panel, _voter, _severity), metric in sorted(severity_metrics.items()):
            lines.append(
                f"| {metric.panel} | {metric.voter} | {metric.severity} | {metric.decisive_yes} | "
                f"{metric.aligned} | {metric.misaligned} | {_ground_truth_rate(metric.aligned, misaligned=metric.misaligned)} | "
                f"{metric.missing_severity} |"
            )
    else:
        lines.append("| n/a | n/a | n/a | 0 | 0 | 0 | n/a | 0 |")
    lines.extend(["", "Examples:"])
    examples = list(outcomes)[: max(top_k, 1)]
    if examples:
        for outcome in examples:
            lines.append(
                f"- {outcome.row.run_id} {outcome.row.finding_id}: {outcome.bucket}. {outcome.reason}"
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "Notes:",
            "- Ground-truth alignment is against realized outcomes, not panel self-agreement.",
            "- Conservative matching can undercount resurfacing and reversals.",
            "- Provisional OOS fates and rejected OOS panel results are non-decisive.",
            "- `realized_alignment_rate` uses decisive aligned/misaligned ballots only.",
        ]
    )
    return "\n".join(lines)


def _ground_truth_gc_slimmed_fallback(log_root: Path, *, seen_gc: frozenset[Path]) -> int:
    """Count gc-slimmed runs not already counted during classifier discovery (F4)."""
    if not log_root.exists():
        return 0
    count = 0
    for run_dir in list((log_root / "implement").glob("*")) + list((log_root / "design").glob("*")) + list((log_root / "review").glob("*")):
        if run_dir.is_dir() and run_dir not in seen_gc and (run_dir / "gc-slimmed").exists():
            count += 1
    return count


def _ground_truth_verdict_run_qualifies(
    run_dir: Path,
    *,
    stats: GroundTruthStats,
    seen_excluded: set[Path],
) -> bool:
    if (run_dir / "gc-slimmed").exists():
        if run_dir not in seen_excluded:
            seen_excluded.add(run_dir)
            stats.excluded_gc_slimmed_runs += 1
        return False
    if stats.since_date is not None:
        started_at = _ground_truth_run_started_at_strict(run_dir)
        if started_at is None:
            if run_dir not in seen_excluded:
                seen_excluded.add(run_dir)
                stats.excluded_missing_started_at_runs += 1
            return False
        if started_at < stats.since_date:
            if run_dir not in seen_excluded:
                seen_excluded.add(run_dir)
                stats.excluded_pre_since_runs += 1
            return False
    if stats.min_larch_version:
        version = _ground_truth_run_larch_version(run_dir)
        if not version:
            if run_dir not in seen_excluded:
                seen_excluded.add(run_dir)
                stats.excluded_missing_version_runs += 1
            return False
        if not _ground_truth_version_meets_floor(version=version, floor=stats.min_larch_version):
            if run_dir not in seen_excluded:
                seen_excluded.add(run_dir)
                stats.excluded_below_version_runs += 1
            return False
    if run_dir not in stats.qualifying_run_dirs:
        stats.qualifying_run_dirs.add(run_dir)
        stats.qualifying_runs += 1
    return True


def _ground_truth_apply_gate(stats: GroundTruthStats) -> None:
    stats.gate_result = True
    stats.gate_reason = ""
    if not stats.verdict_mode:
        return
    if not stats.incentive_era_shipped:
        stats.gate_result = False
        stats.gate_reason = stats.incentive_gate_reason or "calibration_incentive_not_shipped"
    elif stats.enrichment_degraded and stats.targeted_fetch_degraded:
        stats.gate_result = False
        stats.gate_reason = "enrichment_degraded,targeted_fetch_degraded"
    elif stats.enrichment_degraded:
        stats.gate_result = False
        stats.gate_reason = "enrichment_degraded"
    elif stats.targeted_fetch_degraded:
        stats.gate_result = False
        stats.gate_reason = "targeted_fetch_degraded"
    elif stats.qualifying_runs < stats.min_runs:
        stats.gate_result = False
        stats.gate_reason = "corpus_below_min_runs"


def ground_truth_voter_calibration(
    issues: Sequence[Mapping[str, Any]],
    *,
    log_root: Path,
    filed_issue_details: dict[int, dict[str, Any]],
    repo: str | None = None,
    enrichment_degraded: str | None = None,
    targeted_fetch_degraded: str | None = None,
    verdict_mode: bool = False,
    since_date: datetime | None = None,
    min_larch_version: str | None = None,
    min_runs: int = 0,
    top_k: int = 10,
) -> tuple[str, dict[str, Any]]:
    cache_key = repr((
        str(log_root),
        since_date.isoformat() if since_date else "",
        min_larch_version or "",
        bool(verdict_mode),
        int(min_runs or 0),
    ))
    cached = _GROUND_TRUTH_ROW_CACHE.get(cache_key)
    if cached:
        rows = cached[0]
        stats = _copy_ground_truth_stats(cached[1])
    else:
        stats = GroundTruthStats()
        stats.verdict_mode = bool(verdict_mode)
        stats.since_date = since_date
        stats.min_larch_version = min_larch_version
        stats.min_runs = int(min_runs or 0)
        stats.enrichment_degraded = enrichment_degraded
        stats.targeted_fetch_degraded = targeted_fetch_degraded
        rows = []
        seen_gc: set[Path] = set()
        seen_excluded: set[Path] = set()
        discovered = _ground_truth_discover_classifiers(log_root)
        for panel_kind, path in discovered:
            run_dir = _ground_truth_run_dir(path, panel_kind=panel_kind)
            if stats.verdict_mode:
                if not _ground_truth_verdict_run_qualifies(run_dir, stats=stats, seen_excluded=seen_excluded):
                    continue
                stats.files_seen += 1
            else:
                stats.files_seen += 1
            if (run_dir / "gc-slimmed").exists():
                if run_dir not in seen_gc:
                    seen_gc.add(run_dir)
                    stats.gc_slimmed_runs += 1
                continue
            text = _safe_read_text(path)
            if not voting.classification_tsv_schema_supported(text, panel_kind=panel_kind):
                stats.skipped_files += 1
                continue
            prep_rows = voting.classification_row_panel_inputs(text, panel_kind=panel_kind)
            stats.scanned_rows += len(prep_rows)
            started_at = _ground_truth_run_started_at_strict(run_dir) if stats.verdict_mode else _ground_truth_run_started_at(run_dir)
            run_dir_key = _ground_truth_run_dir_key(run_dir, log_root=log_root)
            if run_dir_key is None:
                continue
            for prep in prep_rows:
                raw = dict(prep.raw_row)
                is_oos = voting.classification_row_is_oos(raw, header=prep.header)
                agreement = voting.voter_agreement_row_from_panel(
                    voting_result=raw.get("voting_result") or "",
                    voter_votes=prep.voter_votes,
                    panel=prep.panel,
                    voter_severities=prep.voter_severities,
                )
                if agreement is None:
                    stats.ineligible_rows += 1
                    continue
                stats.eligible_rows += 1
                voters: list[GroundTruthVoter] = []
                voters_value = agreement.get("voters")
                voters_list: list[object] = voters_value if isinstance(voters_value, list) else []
                for voter_obj in voters_list:
                    if isinstance(voter_obj, Mapping):
                        voters.append(
                            GroundTruthVoter(
                                voter=str(voter_obj.get("voter") or ""),
                                vote=str(voter_obj.get("vote") or ""),
                                missing=int(voter_obj.get("missing") or 0),
                                severity=str(voter_obj.get("severity") or ""),
                            )
                        )
                row = GroundTruthRow(
                    panel_kind=prep.panel,
                    path=path,
                    run_dir=run_dir,
                    run_dir_key=run_dir_key,
                    run_id=run_dir.name,
                    round_num=_ground_truth_round_num(path),
                    started_at=started_at,
                    raw_row=raw,
                    header=list(prep.header),
                    reviewer_column=prep.reviewer_column,
                    voter_votes=list(prep.voter_votes),
                    voters=voters,
                    is_oos=is_oos,
                )
                _bind_ground_truth_prose(row)
                if row.prose_text or row.panel_verdict or row.oos_panel_verdict:
                    stats.prose_rows += 1
                rows.append(row)

        if stats.verdict_mode:
            stats.gc_slimmed_runs = stats.excluded_gc_slimmed_runs
        else:
            stats.gc_slimmed_runs += _ground_truth_gc_slimmed_fallback(
                log_root, seen_gc=frozenset(seen_gc)
            )
        _GROUND_TRUTH_ROW_CACHE[cache_key] = (rows, _copy_ground_truth_stats(stats))
    stats.enrichment_degraded = enrichment_degraded
    stats.targeted_fetch_degraded = targeted_fetch_degraded
    stats.verdict_mode = bool(verdict_mode)
    stats.since_date = since_date
    stats.min_larch_version = min_larch_version
    stats.min_runs = int(min_runs or 0)

    issue_index = _merged_issue_index(issues=issues, filed_issue_details=filed_issue_details)
    issue_evidence = _ground_truth_issue_evidence(issues)
    large_corpus = len(rows) > 5000
    if large_corpus:
        stats.large_corpus_skip = True
    accepted_evidence = [] if large_corpus else _ground_truth_accepted_finding_evidence(rows)
    accepted_index = _ground_truth_evidence_token_index(accepted_evidence)
    filed_records = _GROUND_TRUTH_FILED_CACHE.get(cache_key)
    if filed_records is None:
        filed_records = iter_filed_oos_records(log_root)
        _GROUND_TRUTH_FILED_CACHE[cache_key] = filed_records
    filed_by_run: dict[str, list[Mapping[str, Any]]] = collections.defaultdict(list)
    for record in filed_records:
        filed_by_run[str(record.get("run_dir_key") or "")].append(record)
    _reset_ground_truth_outcome_stats(stats)
    outcomes: list[GroundTruthOutcome] = []
    metrics: dict[tuple[str, str], GroundTruthMetric] = {}
    severity_metrics: dict[tuple[str, str, str], GroundTruthSeverityMetric] = {}
    for row in rows:
        if row.is_oos:
            outcome = _ground_truth_oos_outcome(
                row,
                filed_records=filed_by_run.get(row.run_dir_key, []),
                issue_index=issue_index,
                enrichment_degraded=enrichment_degraded,
                stats=stats,
                repo=repo,
            )
        else:
            candidates = [] if row.weak_reason or row.panel_verdict not in {"accepted", "rejected"} else _candidate_evidence_for_row(
                row,
                issue_evidence=issue_evidence,
                accepted_evidence=accepted_evidence,
                accepted_index=accepted_index,
            )
            outcome = _ground_truth_in_scope_outcome(
                row,
                evidence=candidates,
                enrichment_degraded=enrichment_degraded,
                stats=stats,
            )
        outcomes.append(outcome)
        stats.buckets[outcome.bucket] += 1
        if outcome.decisive:
            stats.decisive_rows += 1
        else:
            stats.weak_rows += 1
        _ground_truth_update_metrics(metrics, outcome=outcome)
        _ground_truth_update_severity_metrics(severity_metrics, outcome=outcome)

    if stats.verdict_mode:
        shipped, reason = _ground_truth_calibration_incentive_shipped(
            issues=issues,
            filed_issue_details=filed_issue_details,
            repo=repo,
        )
        stats.incentive_era_shipped = shipped
        stats.incentive_gate_reason = reason
    _ground_truth_apply_gate(stats)

    text = _render_ground_truth_report(
        log_root=log_root,
        stats=stats,
        outcomes=outcomes,
        metrics=metrics,
        severity_metrics=severity_metrics,
        enrichment_degraded=enrichment_degraded,
        top_k=top_k,
    )
    return text, {"stats": stats, "outcomes": outcomes, "metrics": metrics, "severity_metrics": severity_metrics}


def _ground_truth_verdict_exit(
    *,
    issues: Sequence[Mapping[str, Any]],
    log_root: Path,
    filed_issue_details: dict[int, dict[str, Any]],
    repo: str | None,
    enrichment_degraded: str | None,
    targeted_fetch_degraded: str | None,
    since_date: datetime | None,
    min_larch_version: str | None,
    min_runs: int,
    top_k: int,
) -> int:
    resolved_since = since_date or _parse_ground_truth_since_date(GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE)
    resolved_version = min_larch_version or GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION
    resolved_min_runs = min_runs or GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS
    resolved_since, resolved_version = _enforce_ground_truth_verdict_capstone_minima(
        since_date=resolved_since,
        min_larch_version=resolved_version,
        min_runs=resolved_min_runs,
    )
    text, payload = ground_truth_voter_calibration(
        issues,
        log_root=log_root,
        filed_issue_details=filed_issue_details,
        repo=repo,
        enrichment_degraded=enrichment_degraded,
        targeted_fetch_degraded=targeted_fetch_degraded,
        verdict_mode=True,
        since_date=resolved_since,
        min_larch_version=resolved_version,
        min_runs=resolved_min_runs,
        top_k=top_k,
    )
    print(text)
    stats = payload["stats"]
    if not stats.gate_result:
        print(
            f"ERROR=ground_truth_verdict_failed reason={stats.gate_reason} "
            f"qualifying_runs={stats.qualifying_runs} required_runs={stats.min_runs}",
            file=sys.stderr,
        )
        return 1
    return 0
