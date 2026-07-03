"""Retrospective difficulty calibration from committed larch run logs."""
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from larch.calibration import difficulty
from larch.report.report_tokens_cost import display_rates
from larch.report.report_tokens_models import safe_int
from larch.review import voting

SKILLS = ("design", "implement", "review")
TIERS = (difficulty.TRIVIAL, difficulty.MODERATE, difficulty.HARD)
UNKNOWN = "unknown"
PANEL_KIND = {"design": "design", "implement": "code-review", "review": "code-review"}
JSON_PHASES = {"code-review", "code_review"}
SIDECAR_PATH = Path("rejected-analysis-verdicts.tsv")
ACCEPTED_HARD_THRESHOLD = 3


@dataclass(frozen=True)
class FindingIdentity:
    key: str
    round_num: int
    finding_id: str


@dataclass(frozen=True)
class ClassificationOutcome:
    accepted_count: int | None
    accepted_identities: tuple[FindingIdentity, ...]
    parseable_source: bool
    source_label: str
    rows_seen: int = 0


@dataclass(frozen=True)
class TokenTimingSummary:
    token_total: int | None
    cost_usd: float | None
    latency_seconds: int | None


@dataclass(frozen=True)
class RunRecord:
    skill: str
    run_id: str
    run_dir: Path
    rel_link: str
    manifest: Mapping[str, object]
    rating: Mapping[str, object] | None
    classification: ClassificationOutcome
    realized_tier: str
    substantiality_proxy: str
    token_timing: TokenTimingSummary
    sidecar_rows: tuple[Mapping[str, str], ...]
    sidecar_present: bool

    @property
    def applied_tier(self) -> str:
        if self.rating is None:
            return ""
        return difficulty.normalize_tier(self.rating.get("applied_tier"), "")

    @property
    def predicted_tier(self) -> str:
        if self.rating is None:
            return ""
        return difficulty.normalize_tier(self.rating.get("predicted_tier"), "")

    @property
    def rater_key(self) -> str:
        if self.rating is None:
            return UNKNOWN
        rater = _unknown_if_empty(self.rating.get("rater"))
        tool = _unknown_if_empty(self.rating.get("rater_tool"))
        model = _unknown_if_empty(self.rating.get("rater_model"))
        return f"{rater}/{tool}/{model}"

    @property
    def panel_skipped(self) -> str:
        if self.rating is None:
            return ""
        return str(self.rating.get("panel_skipped") or "")

    @property
    def issue_number(self) -> str:
        value = self.manifest.get("issue_number")
        number = safe_int(value=value)
        return str(number) if number > 0 else "n/a"

    @property
    def started_month(self) -> str | None:
        return _started_month(self.manifest.get("started_at"))

    @property
    def audited(self) -> bool:
        if self.rating is None:
            return False
        return _truthy(self.rating.get("audit_evaluated")) or _truthy(self.rating.get("audit_upgrade"))

    @property
    def pre_audit_tier(self) -> str | None:
        if self.rating is None:
            return None
        base_tiers = [
            tier
            for tier in (
                difficulty.normalize_tier(self.rating.get("design_tier"), ""),
                difficulty.normalize_tier(self.rating.get("implement_tier"), ""),
                difficulty.normalize_tier(self.rating.get("predicted_tier"), ""),
            )
            if tier
        ]
        floors = self.rating.get("floors_applied")
        floor_tiers: list[str] = []
        if isinstance(floors, list):
            for item in cast("list[object]", floors):
                if isinstance(item, dict):
                    floor = difficulty.normalize_tier(item.get("floor"), "")
                    if floor:
                        floor_tiers.append(floor)
        if not base_tiers and not floor_tiers:
            return None
        tier = difficulty.tier_max(*base_tiers, *floor_tiers)
        return tier if difficulty.tier_valid(tier) else None


@dataclass(frozen=True)
class Corpus:
    records: tuple[RunRecord, ...]
    degraded: Mapping[str, int]


@dataclass(frozen=True)
class SidecarIndex:
    by_run: Mapping[tuple[str, str], tuple[Mapping[str, str], ...]]
    duplicate_rows: int
    present: bool


@dataclass(frozen=True)
class MutableClassificationRow:
    identity: FindingIdentity
    accepted: bool
    parseable: bool


@dataclass(frozen=True)
class AggregateRow:
    label: str
    runs: int
    tokens: int | None
    cost: float | None
    latency_seconds: int | None


@dataclass
class AnalyzerState:
    counters: Counter[str] = field(default_factory=Counter[str])

    def bump(self, key: str, amount: int = 1) -> None:
        self.counters[key] += amount


def _unknown_if_empty(value: object) -> str:
    text = str(value or "").strip()
    return text or UNKNOWN


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _read_text(path: Path, state: AnalyzerState, counter: str) -> str | None:
    if path.is_symlink() or not path.is_file():
        state.bump(counter)
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        state.bump(counter)
        return None


def _read_json(path: Path, state: AnalyzerState, counter: str) -> object | None:
    text = _read_text(path, state, counter)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        state.bump(counter)
        return None


def _safe_child_run_dirs(log_base: Path, state: AnalyzerState) -> list[Path]:
    dirs: list[Path] = []
    try:
        resolved_base = log_base.resolve(strict=True)
    except OSError:
        state.bump("missing_skill_roots")
        return []
    try:
        children = sorted(log_base.glob("*"))
    except OSError:
        state.bump("unreadable_skill_roots")
        return []
    for path in children:
        if path.is_symlink():
            state.bump("unsafe_run_dirs")
            continue
        if not path.is_dir():
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            state.bump("unsafe_run_dirs")
            continue
        if resolved != resolved_base and resolved_base not in resolved.parents:
            state.bump("unsafe_run_dirs")
            continue
        dirs.append(path)
    return dirs


def _round_num_from_path(path: Path) -> int:
    for part in reversed(path.parts):
        match = re.fullmatch(r"round-(\d+)", part)
        if match:
            return int(match.group(1))
    match = re.search(r"round-(\d+)", path.name)
    return int(match.group(1)) if match else 0


def _classification_paths(skill: str, run_dir: Path) -> tuple[Path, ...]:
    if skill == "implement":
        tsvs = tuple(sorted(run_dir.glob("round-*/findings-classification.tsv"), key=_round_num_from_path))
        return tsvs or ((run_dir / "review-findings-full.jsonl",) if (run_dir / "review-findings-full.jsonl").is_file() else ())
    if skill == "review":
        tsvs = tuple(sorted(run_dir.glob("review-findings-classification-round-*.tsv"), key=_round_num_from_path))
        if tsvs:
            return tsvs
        if (run_dir / "review-findings.ndjson").is_file():
            return (run_dir / "review-findings.ndjson",)
        return ((run_dir / "review-findings-full.jsonl",) if (run_dir / "review-findings-full.jsonl").is_file() else ())
    return tuple(sorted((run_dir / "plan-review").glob("round-*/findings-classification.tsv"), key=_round_num_from_path))


def _has_known_source(skill: str, run_dir: Path) -> bool:
    return bool(_classification_paths(skill, run_dir))


def _rating_object(run_dir: Path, state: AnalyzerState) -> Mapping[str, object] | None:
    path = run_dir / difficulty.DIFFICULTY_RECORD_BASENAME
    if path.is_symlink() or not path.is_file():
        state.bump("unratable_missing_rating")
        return None
    text = _read_text(path, state, "unratable_malformed_rating")
    if text is None:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        state.bump("unratable_malformed_rating")
        return None
    if not isinstance(parsed, dict):
        state.bump("unratable_malformed_rating")
        return None
    data = cast("dict[str, object]", parsed)
    if not difficulty.normalize_tier(data.get("applied_tier"), ""):
        state.bump("unratable_malformed_rating")
        return None
    return data


def _manifest_object(run_dir: Path, state: AnalyzerState) -> Mapping[str, object]:
    path = run_dir / "manifest.json"
    if path.is_symlink() or not path.is_file():
        state.bump("missing_manifests")
        return {}
    parsed = _read_json(path, state, "malformed_manifests")
    if not isinstance(parsed, dict):
        state.bump("malformed_manifests")
        return {}
    return cast("dict[str, object]", parsed)


def _finding_id(value: object) -> str:
    return str(value or "").strip()


def _row_in_scope(row: Mapping[str, str], header: Sequence[str], finding_id: str) -> bool:
    scope = str(row.get("scope") or "").strip().lower()
    if scope in {"oos", "out_of_scope", "out-of-scope"}:
        return False
    if finding_id.upper().startswith("OOS_"):
        return False
    try:
        return not voting.classification_row_is_oos(dict(row), header=list(header))
    except Exception:
        return scope not in {"oos", "out_of_scope", "out-of-scope"}


def _tsv_identity(skill: str, round_num: int, finding_id: str) -> FindingIdentity:
    if skill == "design":
        return FindingIdentity(key=f"design:{finding_id}", round_num=round_num, finding_id=finding_id)
    return FindingIdentity(key=f"{round_num}:{finding_id}", round_num=round_num, finding_id=finding_id)


def _parse_tsv_source(path: Path, *, skill: str, state: AnalyzerState) -> tuple[list[MutableClassificationRow], bool, int]:
    text = _read_text(path, state, "unreadable_classification_sources")
    if text is None:
        return [], False, 0
    panel_kind = PANEL_KIND[skill]
    rows = voting.classification_row_panel_inputs(text, panel_kind=panel_kind)
    if not rows:
        if voting.classification_tsv_schema_supported(text, panel_kind=panel_kind):
            return [], True, 0
        if text.strip():
            state.bump("unsupported_classification_sources")
        return [], False, 0
    round_num = _round_num_from_path(path)
    parsed: list[MutableClassificationRow] = []
    malformed = 0
    for prep in rows:
        row = prep.raw_row
        finding_id = _finding_id(row.get("finding_id"))
        if not finding_id:
            malformed += 1
            continue
        result = str(row.get("voting_result") or "").strip().lower()
        in_scope = _row_in_scope(row, prep.header, finding_id)
        accepted = result == "accepted" and in_scope
        if result not in {"accepted", "rejected", "neutral"}:
            malformed += 1
        parsed.append(MutableClassificationRow(identity=_tsv_identity(skill, round_num, finding_id), accepted=accepted, parseable=True))
    if malformed:
        state.bump("malformed_classification_rows", malformed)
    return parsed, True, len(rows)


def _iter_jsonl_records(path: Path, state: AnalyzerState) -> tuple[list[Mapping[str, object]], int]:
    text = _read_text(path, state, "unreadable_classification_sources")
    if text is None:
        return [], 0
    records: list[Mapping[str, object]] = []
    malformed = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(parsed, dict):
            records.append(cast("dict[str, object]", parsed))
        else:
            malformed += 1
    if malformed:
        state.bump("malformed_classification_rows", malformed)
    return records, malformed


def _json_identity(skill: str, record: Mapping[str, object], round_num: int, fallback_id: str) -> FindingIdentity:
    finding_hash = str(record.get("finding_hash") or "").strip()
    record_id = str(record.get("id") or "").strip()
    if finding_hash:
        key = f"hash:{finding_hash}"
    elif skill == "design" and record_id:
        key = f"id:{record_id}"
    else:
        key = f"{round_num}:{fallback_id}"
    return FindingIdentity(key=key, round_num=round_num, finding_id=fallback_id)


def _parse_jsonl_source(path: Path, *, skill: str, state: AnalyzerState) -> tuple[list[MutableClassificationRow], bool, int]:
    records, iter_malformed = _iter_jsonl_records(path, state)
    parsed: list[MutableClassificationRow] = []
    malformed = 0
    unsupported_phase = 0
    for record in records:
        phase = str(record.get("phase") or "").strip().lower()
        if phase not in JSON_PHASES:
            unsupported_phase += 1
            continue
        raw_round = safe_int(value=record.get("round_num"))
        round_num = max(0, raw_round)
        finding_id = _finding_id(record.get("finding_id") or record.get("id") or record.get("finding_hash"))
        if not finding_id:
            malformed += 1
            continue
        if finding_id.upper().startswith("OOS_"):
            continue
        scope = str(record.get("scope") or "").strip().lower()
        if scope in {"oos", "out_of_scope", "out-of-scope"}:
            continue
        outcome = str(record.get("outcome") or record.get("voting_result") or "").strip().lower()
        accepted = outcome == "accepted"
        if outcome and outcome not in {"accepted", "rejected", "neutral"}:
            malformed += 1
        parsed.append(MutableClassificationRow(identity=_json_identity(skill, record, round_num, finding_id), accepted=accepted, parseable=True))
    if malformed:
        state.bump("malformed_classification_rows", malformed)
    if unsupported_phase:
        state.bump("unsupported_classification_rows", unsupported_phase)
    source_parseable = bool(parsed) or not (iter_malformed or malformed or unsupported_phase)
    return parsed, source_parseable, len(records)


def _classification_outcome(skill: str, run_dir: Path, state: AnalyzerState) -> ClassificationOutcome:
    sources = _classification_paths(skill, run_dir)
    if not sources:
        state.bump("missing_classification_sources")
        return ClassificationOutcome(accepted_count=None, accepted_identities=(), parseable_source=False, source_label="n/a")
    by_identity: dict[str, MutableClassificationRow] = {}
    parseable = False
    rows_seen = 0
    labels: list[str] = []
    for source in sources:
        labels.append(source.relative_to(run_dir).as_posix())
        if source.suffix in {".jsonl", ".ndjson"}:
            rows, source_parseable, count = _parse_jsonl_source(source, skill=skill, state=state)
        else:
            rows, source_parseable, count = _parse_tsv_source(source, skill=skill, state=state)
        parseable = parseable or source_parseable
        rows_seen += count
        for row in rows:
            current = by_identity.get(row.identity.key)
            if current is None or row.identity.round_num >= current.identity.round_num:
                by_identity[row.identity.key] = row
    if not parseable:
        state.bump("unknown_realized_no_parseable_source")
        return ClassificationOutcome(
            accepted_count=None,
            accepted_identities=(),
            parseable_source=False,
            source_label=", ".join(labels) or "n/a",
            rows_seen=rows_seen,
        )
    accepted = tuple(sorted((row.identity for row in by_identity.values() if row.accepted), key=lambda item: (item.round_num, item.finding_id, item.key)))
    return ClassificationOutcome(
        accepted_count=len(accepted),
        accepted_identities=accepted,
        parseable_source=True,
        source_label=", ".join(labels),
        rows_seen=rows_seen,
    )


def _realized_tier(rating: Mapping[str, object] | None, classification: ClassificationOutcome, state: AnalyzerState) -> tuple[str, str]:
    escalations = rating.get("escalations") if rating is not None else None
    if isinstance(escalations, list) and len(escalations) > 0:
        return difficulty.HARD, "escalated"
    if classification.accepted_count is None:
        state.bump("unknown_realized_tiers")
        return UNKNOWN, UNKNOWN
    if classification.accepted_count >= ACCEPTED_HARD_THRESHOLD:
        return difficulty.HARD, UNKNOWN
    if classification.accepted_count == 0:
        return difficulty.TRIVIAL, UNKNOWN
    return difficulty.MODERATE, UNKNOWN


def _vendor_totals(data: Mapping[str, object], vendor: str) -> Mapping[str, object]:
    bucket = data.get(f"BUCKETS_{vendor}")
    if isinstance(bucket, dict):
        return cast("dict[str, object]", bucket)
    vendor_obj = data.get(vendor)
    if isinstance(vendor_obj, dict):
        totals = cast("dict[str, object]", vendor_obj).get("totals")
        if isinstance(totals, dict):
            return cast("dict[str, object]", totals)
    return {}


def _total_tokens_for_vendor(totals: Mapping[str, object], vendor: str) -> int:
    total = safe_int(value=totals.get("total"))
    if total > 0:
        return total
    if vendor == "codex":
        return sum(safe_int(value=totals.get(key)) for key in ("input", "cached_input", "output"))
    return sum(safe_int(value=totals.get(key)) for key in ("input", "cache_read", "cache_create", "cache_create_5m", "cache_create_1h", "output"))


def _cost_for_vendor(totals: Mapping[str, object], vendor: str) -> float:
    rates = display_rates()
    if vendor == "codex":
        return (
            safe_int(value=totals.get("input")) * rates.codex_input
            + safe_int(value=totals.get("cached_input")) * rates.codex_cached_input
            + safe_int(value=totals.get("output")) * rates.codex_output
        ) / 1_000_000
    if vendor == "cursor":
        return (
            safe_int(value=totals.get("input")) * rates.cursor_input
            + safe_int(value=totals.get("cache_read")) * rates.cursor_cache_read
            + safe_int(value=totals.get("output")) * rates.cursor_output
        ) / 1_000_000
    cache_create_5m = safe_int(value=totals.get("cache_create_5m"))
    cache_create_1h = safe_int(value=totals.get("cache_create_1h"))
    cache_create = 0 if cache_create_5m or cache_create_1h else safe_int(value=totals.get("cache_create"))
    return (
        safe_int(value=totals.get("input")) * rates.claude_input
        + safe_int(value=totals.get("cache_read")) * rates.claude_cache_read
        + safe_int(value=totals.get("cache_create_5m")) * rates.claude_cache_create_5m
        + safe_int(value=totals.get("cache_create_1h")) * rates.claude_cache_create_1h
        + cache_create * rates.claude_cache_create_5m
        + safe_int(value=totals.get("output")) * rates.claude_output
    ) / 1_000_000


def _token_timing(skill: str, run_dir: Path, state: AnalyzerState) -> TokenTimingSummary:
    token_name = "token-report-final.json" if skill == "design" else "token-report.json"
    timing_name = "timing-report-final.json" if skill == "design" else "timing-report.json"
    token_obj = _read_json(run_dir / token_name, state, "missing_or_malformed_token_reports")
    token_total: int | None = None
    cost_usd: float | None = None
    if isinstance(token_obj, dict):
        data = cast("dict[str, object]", token_obj)
        total = 0
        cost = 0.0
        for vendor in ("claude", "claude_sub", "codex", "cursor"):
            totals = _vendor_totals(data, vendor)
            total += _total_tokens_for_vendor(totals, vendor)
            if totals:
                cost += _cost_for_vendor(totals, "claude" if vendor == "claude_sub" else vendor)
        token_total = total
        cost_usd = cost
    timing_obj = _read_json(run_dir / timing_name, state, "missing_or_malformed_timing_reports")
    latency: int | None = None
    if isinstance(timing_obj, dict):
        data = cast("dict[str, object]", timing_obj)
        total_seconds = safe_int(value=data.get("total_seconds"))
        per_step = data.get("per_step")
        if total_seconds <= 0 and isinstance(per_step, list):
            total_seconds = sum(safe_int(value=item.get("duration_seconds")) for item in cast("list[object]", per_step) if isinstance(item, dict))
        latency = total_seconds if total_seconds > 0 else None
    return TokenTimingSummary(token_total, cost_usd, latency)


def _read_sidecar(log_root: Path, state: AnalyzerState) -> SidecarIndex:
    path = log_root / SIDECAR_PATH
    if not path.is_file() or path.is_symlink():
        state.bump("missing_rejected_sidecar")
        return SidecarIndex({}, 0, False)
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = [dict(row) for row in csv.DictReader(handle, delimiter="\t")]
    except (OSError, csv.Error):
        state.bump("malformed_rejected_sidecar")
        return SidecarIndex({}, 0, False)
    deduped: dict[str, Mapping[str, str]] = {}
    seen_hashes: set[str] = set()
    seen_rows: set[str] = set()
    duplicates = 0
    for row in rows:
        finding_hash = str(row.get("finding_hash") or "").strip()
        if finding_hash:
            if finding_hash in seen_hashes:
                duplicates += 1
            else:
                seen_hashes.add(finding_hash)
        else:
            row_key = "\0".join(
                (
                    str(row.get("source_skill") or ""),
                    str(row.get("run_id") or ""),
                    str(row.get("round_num") or ""),
                    str(row.get("finding_id") or ""),
                    str(row.get("verdict") or ""),
                    str(row.get("current_location") or ""),
                    str(row.get("evidence") or ""),
                    str(row.get("triaged_at") or ""),
                )
            )
            if row_key in seen_rows:
                duplicates += 1
            else:
                seen_rows.add(row_key)
        row_key = "\0".join(
            (
                finding_hash or "row",
                str(row.get("source_skill") or ""),
                str(row.get("run_id") or ""),
                str(row.get("round_num") or ""),
                str(row.get("finding_id") or ""),
                str(row.get("verdict") or ""),
                str(row.get("current_location") or ""),
                str(row.get("evidence") or ""),
                str(row.get("triaged_at") or ""),
            )
        )
        deduped[row_key] = row
    by_run: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in deduped.values():
        key = (str(row.get("source_skill") or ""), str(row.get("run_id") or ""))
        by_run[key].append(row)
    if duplicates:
        state.bump("duplicate_sidecar_rows", duplicates)
    return SidecarIndex({key: tuple(value) for key, value in by_run.items()}, duplicates, True)


def _sidecar_rows(index: SidecarIndex, *, skill: str, run_id: str) -> tuple[Mapping[str, str], ...]:
    return index.by_run.get((skill, run_id), ())


def _started_month(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m")


def _collect_skill_runs(log_root: Path, skill: str, state: AnalyzerState, sidecar: SidecarIndex) -> list[RunRecord]:
    records: list[RunRecord] = []
    for run_dir in _safe_child_run_dirs(log_root / skill, state):
        has_rating = (run_dir / difficulty.DIFFICULTY_RECORD_BASENAME).is_file()
        if not has_rating and not _has_known_source(skill, run_dir):
            continue
        manifest = _manifest_object(run_dir, state)
        rating = _rating_object(run_dir, state) if has_rating else None
        if not has_rating:
            state.bump("unratable_missing_rating")
        classification = _classification_outcome(skill, run_dir, state)
        realized, substantiality = _realized_tier(rating, classification, state)
        rel_link = run_dir.relative_to(log_root.parent).as_posix() if log_root.parent in run_dir.resolve().parents else run_dir.as_posix()
        records.append(
            RunRecord(
                skill=skill,
                run_id=run_dir.name,
                run_dir=run_dir,
                rel_link=rel_link,
                manifest=manifest,
                rating=rating,
                classification=classification,
                realized_tier=realized,
                substantiality_proxy=substantiality,
                token_timing=_token_timing(skill, run_dir, state),
                sidecar_rows=_sidecar_rows(sidecar, skill=skill, run_id=run_dir.name),
                sidecar_present=sidecar.present,
            )
        )
    return records


def collect_corpus(log_root: Path) -> Corpus:
    state = AnalyzerState()
    sidecar = _read_sidecar(log_root, state)
    records: list[RunRecord] = []
    for skill in SKILLS:
        records.extend(_collect_skill_runs(log_root, skill, state, sidecar))
    return Corpus(tuple(records), dict(sorted(state.counters.items())))


def _ratable(record: RunRecord) -> bool:
    return record.rating is not None and record.realized_tier in TIERS and record.applied_tier in TIERS


def _matrix(records: Sequence[RunRecord]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {applied: dict.fromkeys(TIERS, 0) for applied in TIERS}
    for record in records:
        if _ratable(record):
            matrix[record.applied_tier][record.realized_tier] += 1
    return matrix


def _render_matrix(label: str, records: Sequence[RunRecord]) -> list[str]:
    matrix = _matrix(records)
    lines = [f"### {label}", "", "| Applied \\ Realized | TRIVIAL | MODERATE | HARD |", "|---|---:|---:|---:|"]
    lines.extend(
        f"| {tier} | {matrix[tier][difficulty.TRIVIAL]} | {matrix[tier][difficulty.MODERATE]} | {matrix[tier][difficulty.HARD]} |"
        for tier in TIERS
    )
    lines.append("")
    lines.append(f"Denominator: {sum(sum(row.values()) for row in matrix.values())}")
    lines.append("")
    return lines


def _fmt_int(value: int | None) -> str:
    return "n/a" if value is None else f"{value}"


def _fmt_cost(value: float | None) -> str:
    return "n/a" if value is None else f"${value:.2f}"


def _aggregate_by_tier(records: Sequence[RunRecord]) -> list[AggregateRow]:
    rows: list[AggregateRow] = []
    for tier in TIERS:
        bucket = [record for record in records if record.applied_tier == tier]
        token_values = [record.token_timing.token_total for record in bucket if record.token_timing.token_total is not None]
        cost_values = [record.token_timing.cost_usd for record in bucket if record.token_timing.cost_usd is not None]
        latency_values = [record.token_timing.latency_seconds for record in bucket if record.token_timing.latency_seconds is not None]
        rows.append(
            AggregateRow(
                label=tier,
                runs=len(bucket),
                tokens=sum(token_values) if token_values else None,
                cost=sum(cost_values) if cost_values else None,
                latency_seconds=round(sum(latency_values) / len(latency_values)) if latency_values else None,
            )
        )
    return rows


def _render_under_rating(records: Sequence[RunRecord]) -> list[str]:
    lines = ["## Under-rating Misses", "", "| Skill | Run | Issue | Applied | Predicted | Realized | Accepted | Panel skipped | False-negative burden | Link |", "|---|---|---:|---|---|---|---:|---|---|---|"]
    misses = [
        record
        for record in records
        if _ratable(record) and difficulty.tier_rank(record.realized_tier) > difficulty.tier_rank(record.applied_tier)
    ]
    if not misses:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
    for record in sorted(misses, key=lambda item: (item.skill, item.run_id)):
        sidecar = _sidecar_note(record)
        lines.append(
            f"| {record.skill} | {record.run_id} | {record.issue_number} | {record.applied_tier} | {record.predicted_tier or 'n/a'} | {record.realized_tier} | {_fmt_int(record.classification.accepted_count)} | {record.panel_skipped or 'n/a'} | {sidecar} | {record.rel_link} |"
        )
    lines.append("")
    return lines


def _sidecar_note(record: RunRecord) -> str:
    if not record.sidecar_present:
        return "confirmed=n/a"
    accepted_keys = {identity.key for identity in record.classification.accepted_identities}
    if not accepted_keys:
        return "confirmed=0"
    counts = Counter[str]()
    for row in record.sidecar_rows:
        verdict = str(row.get("verdict") or "").strip().lower().replace("-", "_")
        if not verdict:
            continue
        if not _sidecar_row_matches(row, accepted_keys):
            continue
        counts[verdict] += 1
    confirmed = counts.get("confirmed", 0)
    stale = counts.get("stale", 0)
    already_fixed = counts.get("already_fixed", 0) + counts.get("already-fixed", 0)
    parts = [f"confirmed={confirmed}"]
    if stale:
        parts.append(f"stale={stale}")
    if already_fixed:
        parts.append(f"already-fixed={already_fixed}")
    return "; ".join(parts)


def _sidecar_row_identity_keys(row: Mapping[str, str]) -> tuple[str, ...]:
    keys: list[str] = []
    finding_hash = str(row.get("finding_hash") or "").strip()
    if finding_hash:
        keys.append(f"hash:{finding_hash}")
    round_num = str(row.get("round_num") or "").strip()
    finding_id = str(row.get("finding_id") or "").strip()
    source_skill = str(row.get("source_skill") or "").strip().lower()
    if round_num and finding_id:
        keys.append(f"{round_num}:{finding_id}")
    if source_skill == "design" and finding_id:
        keys.append(f"design:{finding_id}")
    return tuple(dict.fromkeys(keys))


def _sidecar_row_matches(row: Mapping[str, str], accepted_keys: set[str]) -> bool:
    return any(key in accepted_keys for key in _sidecar_row_identity_keys(row))


def _render_corpus_summary(corpus: Corpus) -> list[str]:
    lines = ["# Difficulty Calibration", "", "## Corpus Summary", "", "| Skill | Runs | Ratable | Known realized | Unratable | Unknown realized |", "|---|---:|---:|---:|---:|---:|"]
    for skill in SKILLS:
        records = [record for record in corpus.records if record.skill == skill]
        ratable = sum(1 for record in records if record.rating is not None)
        known = sum(1 for record in records if record.realized_tier in TIERS)
        lines.append(f"| {skill} | {len(records)} | {ratable} | {known} | {len(records) - ratable} | {sum(1 for record in records if record.realized_tier == UNKNOWN)} |")
    lines.extend(["", "## Degraded Inputs", "", "| Counter | Count |", "|---|---:|"])
    if corpus.degraded:
        for key, value in corpus.degraded.items():
            lines.append(f"| {key} | {value} |")
    else:
        lines.append("| none | 0 |")
    lines.append("")
    return lines


def _render_confusion_by_skill(records: Sequence[RunRecord]) -> list[str]:
    lines = ["## Confusion Matrix by Skill", ""]
    for skill in SKILLS:
        lines.extend(_render_matrix(skill, [record for record in records if record.skill == skill]))
    return lines


def _render_confusion_by_rater(records: Sequence[RunRecord]) -> list[str]:
    lines = ["## Confusion Matrix by Rater", ""]
    grouped: dict[str, list[RunRecord]] = defaultdict(list)
    for record in records:
        if record.rating is not None:
            grouped[record.rater_key].append(record)
    if not grouped:
        lines.append("No ratable runs.")
        lines.append("")
        return lines
    for label in sorted(grouped):
        lines.extend(_render_matrix(label, grouped[label]))
    return lines


def _render_tier_cost_latency(records: Sequence[RunRecord]) -> list[str]:
    lines = ["## Per-tier Tokens, Cost, and Latency", "", "| Applied tier | Runs | Tokens total | USD | Avg latency seconds |", "|---|---:|---:|---:|---:|"]
    lines.extend(
        f"| {row.label} | {row.runs} | {_fmt_int(row.tokens)} | {_fmt_cost(row.cost)} | {_fmt_int(row.latency_seconds)} |"
        for row in _aggregate_by_tier(records)
    )
    lines.append("")
    return lines


def _mean(values: Sequence[int]) -> float | None:
    return sum(values) / len(values) if values else None


def _render_audit_deltas(records: Sequence[RunRecord]) -> list[str]:
    lines = ["## Audit-run Deltas", "", "| Skill | Run | Month | Pre-audit tier | Peer count | Token delta | Latency delta seconds |", "|---|---|---|---|---:|---:|---:|"]
    audited = [record for record in records if record.audited]
    if not audited:
        lines.append("| n/a | n/a | n/a | n/a | 0 | n/a | n/a |")
        lines.append("")
        return lines
    for record in sorted(audited, key=lambda item: (item.skill, item.run_id)):
        month = record.started_month
        pre_tier = record.pre_audit_tier
        if month is None or pre_tier is None:
            lines.append(f"| {record.skill} | {record.run_id} | {month or 'n/a'} | {pre_tier or 'n/a'} | 0 | n/a | n/a |")
            continue
        peers = [
            peer
            for peer in records
            if not peer.audited and peer.skill == record.skill and peer.started_month == month and peer.pre_audit_tier == pre_tier
        ]
        if not peers:
            lines.append(f"| {record.skill} | {record.run_id} | {month} | {pre_tier} | 0 | n/a | n/a |")
            continue
        token_peers = [peer.token_timing.token_total for peer in peers if peer.token_timing.token_total is not None]
        latency_peers = [peer.token_timing.latency_seconds for peer in peers if peer.token_timing.latency_seconds is not None]
        token_delta = None
        if record.token_timing.token_total is not None and token_peers:
            token_delta = record.token_timing.token_total - round(cast("float", _mean(token_peers)))
        latency_delta = None
        if record.token_timing.latency_seconds is not None and latency_peers:
            latency_delta = record.token_timing.latency_seconds - round(cast("float", _mean(latency_peers)))
        lines.append(f"| {record.skill} | {record.run_id} | {month} | {pre_tier} | {len(peers)} | {_fmt_int(token_delta)} | {_fmt_int(latency_delta)} |")
    lines.append("")
    return lines


def _render_escalations(records: Sequence[RunRecord]) -> list[str]:
    lines = ["## Escalation Statistics", "", "| Skill | Ratable runs | Escalated runs | Rate |", "|---|---:|---:|---:|"]
    for skill in SKILLS:
        skill_records = [record for record in records if record.skill == skill and record.rating is not None]
        escalated = 0
        for record in skill_records:
            escalations = record.rating.get("escalations") if record.rating is not None else None
            if isinstance(escalations, list) and escalations:
                escalated += 1
        rate = escalated / len(skill_records) if skill_records else 0.0
        lines.append(f"| {skill} | {len(skill_records)} | {escalated} | {rate:.2f} |")
    lines.append("")
    return lines


def _render_drift(records: Sequence[RunRecord]) -> list[str]:
    lines = ["## Tier-distribution Drift", "", "### By Month", "", "| Month | TRIVIAL | MODERATE | HARD |", "|---|---:|---:|---:|"]
    by_month: dict[str, Counter[str]] = defaultdict(Counter)
    by_model: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        if record.rating is None:
            continue
        month = record.started_month
        model = _unknown_if_empty(record.rating.get("rater_model"))
        if month is not None:
            by_month[month][record.applied_tier] += 1
        by_model[model][record.applied_tier] += 1
    if not by_month:
        lines.append("| n/a | 0 | 0 | 0 |")
    for month, counts in sorted(by_month.items()):
        lines.append(f"| {month} | {counts[difficulty.TRIVIAL]} | {counts[difficulty.MODERATE]} | {counts[difficulty.HARD]} |")
    lines.extend(["", "### By Rater Model", "", "| Rater model | TRIVIAL | MODERATE | HARD |", "|---|---:|---:|---:|"])
    if not by_model:
        lines.append("| n/a | 0 | 0 | 0 |")
    for model, counts in sorted(by_model.items()):
        lines.append(f"| {model} | {counts[difficulty.TRIVIAL]} | {counts[difficulty.MODERATE]} | {counts[difficulty.HARD]} |")
    lines.append("")
    return lines


def render_report(corpus: Corpus) -> str:
    lines: list[str] = []
    lines.extend(_render_corpus_summary(corpus))
    lines.extend(_render_confusion_by_skill(corpus.records))
    lines.extend(_render_confusion_by_rater(corpus.records))
    lines.extend(_render_under_rating(corpus.records))
    lines.extend(_render_tier_cost_latency(corpus.records))
    lines.extend(_render_audit_deltas(corpus.records))
    lines.extend(_render_escalations(corpus.records))
    lines.extend(_render_drift(corpus.records))
    return "\n".join(lines).rstrip() + "\n"


def _default_log_root() -> Path:
    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate / "larch-logs"
    return cwd / "larch-logs"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="difficulty-calibration analyze")
    _ = parser.add_argument("--log-root", default=str(_default_log_root()))
    _ = parser.add_argument("--out", default="")
    return parser.parse_args(list(argv))


def analyze_main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    log_root = Path(str(args.log_root))
    if not log_root.is_dir():
        print(f"ERROR: --log-root is missing or not a directory: {log_root}", file=sys.stderr)
        return 2
    corpus = collect_corpus(log_root)
    report = render_report(corpus)
    if args.out:
        out = Path(str(args.out))
        out.parent.mkdir(parents=True, exist_ok=True)
        _ = out.write_text(report, encoding="utf-8")
        print(f"REPORT_FILE={out}")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(analyze_main())
# pyright: reportUnknownVariableType=false, reportUnusedFunction=false
# pyright: reportUnusedCallResult=false
