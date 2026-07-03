"""Difficulty rating helpers for design, implement, and review run logs."""
# pyright: reportUnusedCallResult=false
# ruff: noqa: PLR0913,PLR2004,TRY004,PERF401,SIM114

from __future__ import annotations

import argparse
import fnmatch
import json
import random
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast
from larch import io as larch_io
from larch.core import config
from larch.core import proc

TRIVIAL = config.DIFFICULTY_TIER_TRIVIAL
MODERATE = config.DIFFICULTY_TIER_MODERATE
HARD = config.DIFFICULTY_TIER_HARD
TIERS = config.DIFFICULTY_TIERS
CONFIDENCES = ("low", "medium", "high")
SCHEMA_VERSION = 1
RATIONALE_MAX_CHARS = 500
DESIGN_RAW_RATING_BASENAME = "design-difficulty-rating.raw.json"
IMPLEMENT_RAW_RATING_BASENAME = "implement-difficulty-rating.raw.json"
SCOUT_RAW_RATING_BASENAME = "scout-difficulty-rating.raw.json"
DIFFICULTY_RECORD_BASENAME = "difficulty-rating.json"
FLOOR_MANIFEST = Path(__file__).resolve().parents[3] / "docs" / "difficulty-floor-globs.tsv"

_TIER_RANK = {tier: rank for rank, tier in enumerate(TIERS)}
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_PLAN_DIFFICULTY_RE = re.compile(r"^difficulty: (TRIVIAL|MODERATE|HARD)$")
_PLAN_TRAILER_LINE_RE = re.compile(
    r"^(review_status: .+|rounds_completed: [0-9]+|difficulty: (TRIVIAL|MODERATE|HARD)|diff_added: [0-9]+|diff_deleted: [0-9]+|mechanical_churn: .+|diff_lines: [0-9]+)$"
)


@dataclass(frozen=True)
class DifficultyRating:
    predicted_tier: str
    confidence: str
    rationale: str
    adjusted_tier: str


@dataclass(frozen=True)
class DifficultyFloor:
    glob: str
    floor: str
    reason: str


@dataclass(frozen=True)
class FloorMatch:
    path: str
    glob: str
    floor: str
    reason: str


@dataclass(frozen=True)
class FloorResult:
    tier: str
    matches: tuple[FloorMatch, ...]


@dataclass(frozen=True)
class TierPolicy:
    tier: str
    round_cap: int
    codex_model_role: str
    panel_shape: str
    threshold_panel: str


@dataclass(frozen=True)
class TierResolution:
    panel_tier: str
    round_cap: int
    codex_model_role: str
    audit_evaluated: bool
    audit_upgrade: bool
    override_source: str
    escalated_round: bool = False
    escalations: tuple[object, ...] = ()


@dataclass(frozen=True)
class PanelComposition:
    tier: str
    shape: str
    codex_model_role: str
    threshold_panel: str


@dataclass(frozen=True)
class AuditDecision:
    evaluated: bool
    upgrade: bool
    roll: int | None
    denominator: int


@dataclass(frozen=True)
class DifficultyRecord:
    schema_version: int
    rater: str
    rater_tool: str
    rater_model: str
    predicted_tier: str
    confidence: str
    rationale: str
    design_tier: str | None
    implement_tier: str | None
    applied_tier: str
    override_source: str
    floors_applied: list[dict[str, str]]
    audit_upgrade: str | None
    escalations: list[object]
    panel_skipped: str | None
    panel_tier: str | None = None
    round_cap: int | None = None
    codex_model_role: str | None = None
    audit_evaluated: bool | None = None
    escalated_round: bool | None = None


def tier_valid(value: str) -> bool:
    return value in _TIER_RANK


def normalize_tier(value: object, default: str = "") -> str:
    tier = str(value or "").strip().upper()
    return tier if tier_valid(tier) else default


def tier_rank(tier: str) -> int:
    normalized = normalize_tier(tier)
    if not normalized:
        raise ValueError(f"invalid difficulty tier: {tier}")
    return _TIER_RANK[normalized]


def next_tier(tier: str) -> str:
    normalized = normalize_tier(tier, MODERATE)
    if normalized == HARD:
        return HARD
    return TIERS[_TIER_RANK[normalized] + 1]


def tier_ceiling(tier: str) -> int:
    return int(config.DIFFICULTY_TIER_CEILINGS[normalize_tier(tier, MODERATE)])


def codex_review_model_role(tier: str) -> str:
    return config.DIFFICULTY_CODEX_MODEL_ROLES[normalize_tier(tier, MODERATE)]


def panel_shape_for_tier(tier: str) -> str:
    return "singles" if normalize_tier(tier, MODERATE) == TRIVIAL else "pairs"


def threshold_panel_for_tier(tier: str) -> str:
    return config.DIFFICULTY_THRESHOLD_PANEL_TOKENS[normalize_tier(tier, MODERATE)]


def panel_policy(tier: str) -> TierPolicy:
    normalized = normalize_tier(tier, MODERATE)
    return TierPolicy(
        tier=normalized,
        round_cap=tier_ceiling(normalized),
        codex_model_role=codex_review_model_role(normalized),
        panel_shape=panel_shape_for_tier(normalized),
        threshold_panel=threshold_panel_for_tier(normalized),
    )


def confidence_valid(value: str) -> bool:
    return value in CONFIDENCES


def tier_max(*tiers: str | None) -> str:
    present = [tier for tier in tiers if tier is not None and tier_valid(tier)]
    if not present:
        return TRIVIAL
    return max(present, key=lambda tier: _TIER_RANK[tier])


def bump_for_confidence(tier: str, confidence: str) -> str:
    if confidence != "low" or tier == HARD:
        return tier
    return TIERS[_TIER_RANK[tier] + 1]


def sanitize_rationale(value: object, *, max_chars: int = RATIONALE_MAX_CHARS) -> str:
    text = value if isinstance(value, str) else ""
    cleaned = _CONTROL_RE.sub(" ", text.replace("\r", " ").replace("\n", " "))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_chars:
        return cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned


def validate_rating_object(obj: object) -> DifficultyRating:
    if not isinstance(obj, dict):
        raise ValueError("rating must be a JSON object")
    data = cast("dict[str, object]", obj)
    predicted = str(data.get("predicted_tier") or "").upper()
    confidence = str(data.get("confidence") or "").lower()
    if not tier_valid(predicted):
        raise ValueError("predicted_tier must be TRIVIAL, MODERATE, or HARD")
    if not confidence_valid(confidence):
        raise ValueError("confidence must be low, medium, or high")
    rationale = sanitize_rationale(data.get("rationale"))
    if not rationale:
        raise ValueError("rationale must be non-empty after sanitization")
    return DifficultyRating(
        predicted_tier=predicted,
        confidence=confidence,
        rationale=rationale,
        adjusted_tier=bump_for_confidence(predicted, confidence),
    )


def read_rating_file(path: Path) -> DifficultyRating | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        data: object = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return validate_rating_object(data)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def load_floor_manifest(path: Path = FLOOR_MANIFEST) -> tuple[DifficultyFloor, ...]:
    rows: list[DifficultyFloor] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ValueError(f"difficulty floor manifest not readable: {path}") from exc
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if parts[:3] == ["glob", "floor", "reason"]:
            continue
        if len(parts) < 3:
            raise ValueError(f"difficulty floor manifest row {line_no} must have glob, floor, reason")
        glob, floor, reason = parts[0].strip(), parts[1].strip().upper(), parts[2].strip()
        if not glob or not tier_valid(floor) or not reason:
            raise ValueError(f"difficulty floor manifest row {line_no} is invalid")
        rows.append(DifficultyFloor(glob=glob, floor=floor, reason=reason))
    return tuple(rows)


def _read_changed_paths(path: Path | None) -> tuple[str, ...]:
    if path is None or not path.is_file() or path.is_symlink():
        return ()
    raw = path.read_bytes()
    if b"\0" in raw:
        values = [part.decode("utf-8", errors="surrogateescape") for part in raw.split(b"\0")]
    else:
        values = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return tuple(value.strip() for value in values if value.strip())


def match_floors(paths: tuple[str, ...], floors: tuple[DifficultyFloor, ...] | None = None) -> FloorResult:
    floor_rows = floors if floors is not None else load_floor_manifest()
    matches: list[FloorMatch] = []
    for changed in paths:
        for row in floor_rows:
            if fnmatch.fnmatchcase(changed, row.glob):
                matches.append(FloorMatch(path=changed, glob=row.glob, floor=row.floor, reason=row.reason))
    return FloorResult(tier=tier_max(*(match.floor for match in matches)), matches=tuple(matches)) if matches else FloorResult(tier=TRIVIAL, matches=())


def _coerce_record_mapping(record_or_rating: object) -> dict[str, object]:
    if isinstance(record_or_rating, DifficultyRecord):
        return cast("dict[str, object]", asdict(record_or_rating))
    if isinstance(record_or_rating, DifficultyRating):
        return {
            "predicted_tier": record_or_rating.predicted_tier,
            "applied_tier": record_or_rating.adjusted_tier,
        }
    if isinstance(record_or_rating, dict):
        return cast("dict[str, object]", record_or_rating)
    return {}


def resolve_applied_tier(
    record_or_rating: object,
    floors: tuple[str, ...] | list[str] | str | None = None,
    override: str = "",
    fallback_tier: str = MODERATE,
) -> str:
    override_tier = normalize_tier(override)
    if override_tier:
        return override_tier
    data = _coerce_record_mapping(record_or_rating)
    base = normalize_tier(data.get("applied_tier")) or normalize_tier(data.get("adjusted_tier")) or normalize_tier(data.get("predicted_tier")) or normalize_tier(fallback_tier, MODERATE)
    floor_values = (floors,) if isinstance(floors, str) else tuple(floors or ())
    return tier_max(base, *(normalize_tier(value) for value in floor_values))


def _rng_roll(rng: object, denominator: int) -> int:
    if rng is None:
        return random.SystemRandom().randint(1, denominator)
    if isinstance(rng, int):
        return rng
    if callable(rng):
        value = rng()
        return int(cast("int", value))
    randrange = getattr(rng, "randrange", None)
    if callable(randrange):
        return int(cast("int", randrange(1, denominator + 1)))
    randint = getattr(rng, "randint", None)
    if callable(randint):
        return int(cast("int", randint(1, denominator)))
    return denominator


def maybe_audit_upgrade(tier: str, rng: object, *, override_source: str = "") -> AuditDecision:
    del override_source
    denominator = config.DIFFICULTY_AUDIT_DENOMINATOR
    normalized = normalize_tier(tier, MODERATE)
    if normalized == HARD:
        return AuditDecision(evaluated=False, upgrade=False, roll=None, denominator=denominator)
    roll = _rng_roll(rng, denominator)
    return AuditDecision(evaluated=True, upgrade=roll == 1, roll=roll, denominator=denominator)


def _load_record_data(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        data: object = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    return cast("dict[str, object]", data) if isinstance(data, dict) else {}


def _record_escalations_for_round(data: dict[str, object], round_num: int | None = None) -> tuple[object, ...]:
    raw = data.get("escalations")
    if not isinstance(raw, list):
        return ()
    items = cast("list[object]", raw)
    if round_num is None:
        return tuple(items)
    result: list[object] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        item = cast("dict[str, object]", raw_item)
        try:
            item_round = int(str(item.get("round") or 0) or 0)
        except ValueError:
            continue
        if item_round == round_num:
            result.append(item)
    return tuple(result)


def _write_record_data(path: Path, data: dict[str, object]) -> None:
    larch_io.atomic_write(path=path, text=json.dumps(data, indent=2, sort_keys=True) + "\n", prefix=f".{path.name}.")


def _resolution_from_data(data: dict[str, object], *, round_num: int | None = None) -> TierResolution | None:
    panel_tier = normalize_tier(data.get("panel_tier"))
    if not panel_tier:
        return None
    round_escalations = _record_escalations_for_round(data, round_num) if round_num is not None else ()
    raw_round_cap = data.get("round_cap")
    round_cap = raw_round_cap if isinstance(raw_round_cap, int) else tier_ceiling(panel_tier)
    return TierResolution(
        panel_tier=panel_tier,
        round_cap=round_cap,
        codex_model_role=str(data.get("codex_model_role") or codex_review_model_role(panel_tier)),
        audit_evaluated=bool(data.get("audit_evaluated")),
        audit_upgrade=str(data.get("audit_upgrade") or "").lower() == "true" or data.get("audit_upgrade") is True,
        override_source=str(data.get("override_source") or "none"),
        escalated_round=bool(round_escalations) if round_num is not None else bool(data.get("escalated_round")),
        escalations=_record_escalations_for_round(data),
    )


def resolve_panel_tier(
    record_path: Path,
    override: str = "",
    rng: object = None,
    *,
    audit_enabled: bool = True,
    round_num: int | None = None,
) -> TierResolution:
    data = _load_record_data(record_path)
    override_tier = normalize_tier(override)
    existing = _resolution_from_data(data, round_num=round_num)
    if existing is not None:
        has_escalations = bool(_record_escalations_for_round(data))
        resolved_once = data.get("audit_evaluated") is not None or data.get("audit_upgrade") is not None
        existing_operator_override = data.get("override_source") == "operator"
        if not override_tier or not audit_enabled or has_escalations or (resolved_once and existing_operator_override):
            return existing
    override_source = "operator" if override_tier else str(data.get("override_source") or "none")
    starting = override_tier or resolve_applied_tier(data, override="", fallback_tier=MODERATE)
    audit_evaluated = bool(data.get("audit_evaluated"))
    audit_upgrade = str(data.get("audit_upgrade") or "").lower() == "true" or data.get("audit_upgrade") is True
    if not audit_evaluated and audit_enabled:
        # Missing records synthesize MODERATE without sampling. Normal bootstraps
        # create a record before panel resolution, so production runs still take
        # the 1:30 audit path while recordless recovery paths stay stable.
        audit_rng = rng if rng is not None else (None if data else config.DIFFICULTY_AUDIT_DENOMINATOR)
        decision = maybe_audit_upgrade(starting, audit_rng, override_source=override_source)
        audit_evaluated = decision.evaluated
        audit_upgrade = decision.upgrade
    panel_tier = HARD if audit_upgrade and starting != HARD else starting
    resolution = TierResolution(
        panel_tier=panel_tier,
        round_cap=tier_ceiling(panel_tier),
        codex_model_role=codex_review_model_role(panel_tier),
        audit_evaluated=audit_evaluated,
        audit_upgrade=audit_upgrade,
        override_source=override_source,
        escalated_round=bool(data.get("escalated_round")),
        escalations=_record_escalations_for_round(data),
    )
    if not data:
        data = cast("dict[str, object]", {
            "schema_version": SCHEMA_VERSION,
            "rater": "fallback",
            "rater_tool": "unknown",
            "rater_model": "unknown",
            "predicted_tier": starting,
            "confidence": "medium",
            "rationale": "fallback rating synthesized for panel resolution",
            "design_tier": None,
            "implement_tier": None,
            "floors_applied": [],
            "panel_skipped": None,
            "escalations": [],
        })
    data.update(
        {
            "applied_tier": panel_tier,
            "panel_tier": resolution.panel_tier,
            "round_cap": resolution.round_cap,
            "codex_model_role": resolution.codex_model_role,
            "audit_evaluated": resolution.audit_evaluated,
            "audit_upgrade": "true" if resolution.audit_upgrade else None,
            "override_source": resolution.override_source,
            "escalated_round": resolution.escalated_round,
        }
    )
    _write_record_data(record_path, data)
    return resolution


def append_escalation(record_path: Path, round_num: int, from_tier: str, to_tier: str, trigger: str) -> None:
    data = _load_record_data(record_path)
    if not data:
        data = cast("dict[str, object]", {
            "schema_version": SCHEMA_VERSION,
            "rater": "fallback",
            "rater_tool": "unknown",
            "rater_model": "unknown",
            "predicted_tier": normalize_tier(from_tier, MODERATE),
            "confidence": "medium",
            "rationale": "escalation record",
            "design_tier": None,
            "implement_tier": None,
            "floors_applied": [],
            "override_source": "none",
            "audit_upgrade": None,
            "panel_skipped": None,
        })
    raw_escalations = data.get("escalations")
    escalations = cast("list[object]", raw_escalations) if isinstance(raw_escalations, list) else []
    entry = {
        "round": round_num,
        "from_tier": normalize_tier(from_tier, MODERATE),
        "to_tier": normalize_tier(to_tier, HARD),
        "trigger": trigger,
    }
    escalations.append(entry)
    to_normalized = normalize_tier(to_tier, HARD)
    data.update(
        {
            "escalations": escalations,
            "applied_tier": to_normalized,
            "panel_tier": to_normalized,
            "round_cap": tier_ceiling(to_normalized),
            "codex_model_role": codex_review_model_role(to_normalized),
            "escalated_round": True,
        }
    )
    _write_record_data(record_path, data)


def plan_difficulty(text: str) -> str:
    for line in reversed(trailing_plan_metadata_lines(text)):
        match = _PLAN_DIFFICULTY_RE.fullmatch(line.strip())
        if match:
            return match.group(1)
    return ""


def rewrite_plan_difficulty(text: str, tier: str) -> str:
    if not tier_valid(tier):
        return text
    lines = text.splitlines(keepends=True)
    span = _trailing_metadata_span(text.splitlines())
    if span is None:
        return text
    start, end = span
    replacement = f"difficulty: {tier}\n"
    for idx in range(start, end):
        if lines[idx].startswith("difficulty:"):
            newline = "\n" if lines[idx].endswith("\n") else ""
            lines[idx] = f"difficulty: {tier}{newline}"
            return "".join(lines)
    insert_at = end
    while insert_at > start and lines[insert_at - 1].startswith("diff_lines:"):
        insert_at -= 1
    lines.insert(insert_at, replacement)
    return "".join(lines)


def label_for_tier(tier: str) -> str:
    if not tier_valid(tier):
        raise ValueError(f"invalid difficulty tier: {tier}")
    return f"difficulty:{tier.lower()}"


def known_labels() -> tuple[str, ...]:
    return tuple(label_for_tier(tier) for tier in TIERS)


def _rating_from_tier(tier: str, *, rationale: str) -> DifficultyRating | None:
    if not tier_valid(tier):
        return None
    return DifficultyRating(predicted_tier=tier, confidence="medium", rationale=sanitize_rationale(rationale) or "wire metadata", adjusted_tier=tier)


def _trailing_metadata_span(lines: list[str]) -> tuple[int, int] | None:
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    if end == 0:
        return None
    start = end
    while start > 0 and _PLAN_TRAILER_LINE_RE.fullmatch(lines[start - 1].rstrip("\n")):
        start -= 1
    if start == end:
        return None
    return start, end


def trailing_plan_metadata_lines(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    span = _trailing_metadata_span(lines)
    if span is None:
        return ()
    start, end = span
    return tuple(lines[start:end])


def build_record(
    *,
    rater: str,
    rater_tool: str = "",
    rater_model: str = "",
    design_rating: DifficultyRating | None = None,
    implement_rating: DifficultyRating | None = None,
    fallback_rating: DifficultyRating | None = None,
    changed_paths: tuple[str, ...] = (),
    panel_skipped: str = "",
    audit_upgrade: str = "",
    escalations: tuple[object, ...] = (),
    override_source: str = "",
    override_tier: str = "",
    panel_tier: str = "",
    round_cap: int | None = None,
    codex_model_role: str = "",
    audit_evaluated: bool | None = None,
    escalated_round: bool | None = None,
) -> DifficultyRecord:
    source = implement_rating or design_rating or fallback_rating
    if source is None:
        raise ValueError("at least one difficulty rating is required")
    model_tier = tier_max(
        design_rating.adjusted_tier if design_rating else None,
        implement_rating.adjusted_tier if implement_rating else None,
    )
    if model_tier == TRIVIAL and design_rating is None and implement_rating is None and fallback_rating is not None:
        model_tier = fallback_rating.adjusted_tier
    floors = match_floors(changed_paths)
    explicit_override = normalize_tier(override_tier)
    applied = explicit_override or tier_max(model_tier, floors.tier)
    audit_upgrade_bool = str(audit_upgrade).lower() == "true"
    if audit_upgrade_bool and applied != HARD:
        applied = HARD
    derived_override = "operator" if explicit_override else "floor" if floors.matches and _TIER_RANK[floors.tier] > _TIER_RANK[model_tier] else "none"
    effective_panel_tier = normalize_tier(panel_tier) or applied
    effective_round_cap = round_cap if round_cap is not None else tier_ceiling(effective_panel_tier)
    effective_codex_role = codex_model_role or codex_review_model_role(effective_panel_tier)
    return DifficultyRecord(
        schema_version=SCHEMA_VERSION,
        rater=rater or "unknown",
        rater_tool=rater_tool or "unknown",
        rater_model=rater_model or "unknown",
        predicted_tier=source.adjusted_tier,
        confidence=source.confidence,
        rationale=source.rationale,
        design_tier=design_rating.adjusted_tier if design_rating else None,
        implement_tier=implement_rating.adjusted_tier if implement_rating else None,
        applied_tier=applied,
        override_source=override_source or derived_override,
        floors_applied=[asdict(match) for match in floors.matches],
        audit_upgrade=audit_upgrade or None,
        escalations=list(escalations),
        panel_skipped=panel_skipped or None,
        panel_tier=effective_panel_tier,
        round_cap=effective_round_cap,
        codex_model_role=effective_codex_role,
        audit_evaluated=audit_evaluated,
        escalated_round=escalated_round,
    )


def write_record(path: Path, record: DifficultyRecord) -> None:
    data = asdict(record)
    larch_io.atomic_write(path=path, text=json.dumps(data, indent=2, sort_keys=True) + "\n", prefix=f".{path.name}.")


def render_rubric() -> str:
    return """Difficulty rating rubric (model judgment, not a computed complexity score):
- TRIVIAL: localized, low-risk edits with obvious tests or documentation-only wording updates.
- MODERATE: multi-file or workflow-affecting changes where integration, state, or reviewer interpretation can fail.
- HARD: cross-cutting lifecycle, security-sensitive, concurrency, CI/merge, or prompt-contract changes with high blast radius.
Confidence: use high when evidence is direct, medium when ordinary uncertainty remains, and low when scope or risk is unclear. Low confidence bumps the recorded tier by one level, capped at HARD.
Floors: hooks, redaction/secret handling, ship/merge drivers, session-env writers, and CI workflows force at least MODERATE. Floors raise only.
Seeded examples:
TRIVIAL: run-2026-06-27-doc-typo corrected a doc-only stale phrase; run-2026-06-29-test-pin refreshed a single harness literal; run-2026-07-01-small-cli added one bounded flag parser test.
MODERATE: run-2026-06-28-review-prune touched review loop metadata; run-2026-06-30-design-trailer changed plan trailer validation; run-2026-07-01-run-log-batch added a persisted run-log batch.
HARD: run-2026-06-26-ship-merge changed merge routing; run-2026-06-30-redaction updated secret handling; run-2026-07-02-session-bootstrap altered session-env materialization.
"""


def difficulty_line(record: DifficultyRecord | dict[str, object]) -> str:
    data = asdict(record) if isinstance(record, DifficultyRecord) else record
    predicted = str(data.get("predicted_tier") or "unknown")
    applied = str(data.get("applied_tier") or predicted)
    parts = [f"predicted {predicted}", f"applied {applied}"]
    floors = data.get("floors_applied")
    if isinstance(floors, list) and floors:
        parts.append("floor raised" if applied != predicted else "floor checked")
    audit = data.get("audit_upgrade")
    if audit:
        parts.append(f"audit {audit}")
    if data.get("override_source") == "operator":
        parts.append("override operator")
    escalations = data.get("escalations")
    if isinstance(escalations, list) and escalations:
        rendered: list[str] = []
        for raw_item in cast("list[object]", escalations):
            if isinstance(raw_item, dict):
                item = cast("dict[str, object]", raw_item)
                from_tier = item.get("from_tier", "?")
                to_tier = item.get("to_tier", "?")
                round_num = item.get("round", "?")
                trigger = item.get("trigger", "")
                suffix = f" {trigger}" if trigger else ""
                rendered.append(f"r{round_num} {from_tier}->{to_tier}{suffix}")
            else:
                rendered.append(str(raw_item))
        parts.append("escalated " + ", ".join(rendered))
    skipped = data.get("panel_skipped")
    if skipped:
        parts.append(f"panel skipped: {skipped}")
    return "; ".join(parts)


def _record_from_args(args: argparse.Namespace) -> DifficultyRecord:
    design_rating = read_rating_file(Path(args.design_raw_rating_file)) if args.design_raw_rating_file else None
    if design_rating is None and args.design_tier:
        design_rating = _rating_from_tier(str(args.design_tier).upper(), rationale="design wire metadata")
    implement_rating = read_rating_file(Path(args.implement_raw_rating_file)) if args.implement_raw_rating_file else None
    raw_rating = read_rating_file(Path(args.raw_rating_file)) if args.raw_rating_file else None
    if args.rater == "design" and design_rating is None:
        design_rating = raw_rating
    elif args.rater == "implement" and implement_rating is None:
        implement_rating = raw_rating
    elif args.rater == "review" and raw_rating is not None:
        implement_rating = raw_rating
    fallback = None
    if args.fallback_tier:
        fallback = _rating_from_tier(str(args.fallback_tier).upper(), rationale=args.fallback_rationale)
    changed_paths = _read_changed_paths(Path(args.changed_paths_file) if args.changed_paths_file else None)
    return build_record(
        rater=args.rater,
        rater_tool=args.rater_tool,
        rater_model=args.rater_model,
        design_rating=design_rating,
        implement_rating=implement_rating,
        fallback_rating=fallback,
        changed_paths=changed_paths,
        panel_skipped=args.panel_skipped,
        audit_upgrade=args.audit_upgrade,
        escalations=tuple(args.escalation or ()),
        override_source=args.override_source,
        override_tier=args.override_tier,
        panel_tier=args.panel_tier,
        round_cap=int(args.round_cap) if str(args.round_cap).isdigit() else None,
        codex_model_role=args.codex_model_role,
        audit_evaluated=True if args.audit_evaluated == "true" else False if args.audit_evaluated == "false" else None,
        escalated_round=True if args.escalated_round == "true" else False if args.escalated_round == "false" else None,
    )


def _merge_existing_record_fields(record: DifficultyRecord, existing: dict[str, object], explicit_args: argparse.Namespace) -> DifficultyRecord:
    if not existing:
        return record
    data = asdict(record)
    preserve = (
        "override_source",
        "audit_upgrade",
        "escalations",
        "applied_tier",
        "panel_tier",
        "round_cap",
        "codex_model_role",
        "audit_evaluated",
        "escalated_round",
    )
    explicit = {
        key
        for key, value in {
            "override_source": explicit_args.override_source,
            "audit_upgrade": explicit_args.audit_upgrade,
            "escalations": explicit_args.escalation,
            "round_cap": explicit_args.round_cap,
            "codex_model_role": explicit_args.codex_model_role,
            "audit_evaluated": explicit_args.audit_evaluated,
            "escalated_round": explicit_args.escalated_round,
        }.items()
        if value
    }
    if explicit_args.override_tier or explicit_args.panel_tier:
        explicit.update({"applied_tier", "panel_tier"})
    for key in preserve:
        if key in explicit:
            continue
        if key == "override_source" and existing.get(key) == "operator":
            data[key] = "operator"
            continue
        value = existing.get(key)
        if value not in (None, "", []):
            data[key] = value
    if data.get("override_source") == "operator":
        # Floor logic must not replace an operator override on refresh.
        existing_applied = normalize_tier(existing.get("applied_tier"))
        if existing_applied and not explicit_args.override_tier:
            data["applied_tier"] = existing_applied
    return DifficultyRecord(**data)


def validate_rating_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty validate-rating")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file")
    args = parser.parse_args(argv)
    try:
        data: object = json.loads(Path(args.input_file).read_text(encoding="utf-8", errors="replace"))
        rating = validate_rating_object(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"STATUS=invalid\nERROR={exc}")
        return 1
    out = asdict(rating)
    if args.output_file:
        larch_io.atomic_write(Path(args.output_file), json.dumps(out, indent=2, sort_keys=True) + "\n", prefix=".difficulty-rating.")
    print("STATUS=ok")
    print(f"PREDICTED_TIER={rating.predicted_tier}")
    print(f"CONFIDENCE={rating.confidence}")
    print(f"ADJUSTED_TIER={rating.adjusted_tier}")
    return 0


def extract_plan_metadata_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty extract-plan-metadata")
    parser.add_argument("--plan-file", required=True)
    args = parser.parse_args(argv)
    try:
        text = Path(args.plan_file).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"STATUS=error\nERROR={exc}")
        return 2
    tier = plan_difficulty(text)
    print("STATUS=ok")
    print(f"DESIGN_DIFFICULTY={tier}")
    return 0


def write_record_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty write-record")
    parser.add_argument("--output", required=True)
    parser.add_argument("--rater", choices=("design", "implement", "review", "fallback"), default="fallback")
    parser.add_argument("--rater-tool", default="")
    parser.add_argument("--rater-model", default="")
    parser.add_argument("--raw-rating-file", default="")
    parser.add_argument("--design-raw-rating-file", default="")
    parser.add_argument("--implement-raw-rating-file", default="")
    parser.add_argument("--design-tier", default="")
    parser.add_argument("--changed-paths-file", default="")
    parser.add_argument("--panel-skipped", default="")
    parser.add_argument("--audit-upgrade", default="")
    parser.add_argument("--escalation", action="append")
    parser.add_argument("--override-source", default="")
    parser.add_argument("--override-tier", default="")
    parser.add_argument("--panel-tier", default="")
    parser.add_argument("--round-cap", default="")
    parser.add_argument("--codex-model-role", default="")
    parser.add_argument("--audit-evaluated", choices=("", "true", "false"), default="")
    parser.add_argument("--escalated-round", choices=("", "true", "false"), default="")
    parser.add_argument("--fallback-tier", default="MODERATE")
    parser.add_argument("--fallback-rationale", default="fallback rating synthesized for recovery path")
    args = parser.parse_args(argv)
    try:
        record = _record_from_args(args)
        record = _merge_existing_record_fields(record, _load_record_data(Path(args.output)), args)
        write_record(Path(args.output), record)
    except (OSError, ValueError) as exc:
        print(f"STATUS=error\nERROR={exc}")
        return 1
    print("STATUS=ok")
    print(f"OUTPUT={args.output}")
    print(f"PREDICTED_TIER={record.predicted_tier}")
    print(f"APPLIED_TIER={record.applied_tier}")
    print(f"OVERRIDE_SOURCE={record.override_source}")
    return 0


def render_rubric_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty render-rubric")
    parser.parse_args(argv)
    sys.stdout.write(render_rubric())
    return 0


def render_line_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty render-line")
    parser.add_argument("--record-file", required=True)
    args = parser.parse_args(argv)
    try:
        data: object = json.loads(Path(args.record_file).read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"STATUS=error\nERROR={exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("STATUS=error\nERROR=record must be object", file=sys.stderr)
        return 1
    print(difficulty_line(cast("dict[str, object]", data)))
    return 0


def resolve_panel_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty resolve-panel")
    parser.add_argument("--record-file", required=True)
    parser.add_argument("--override", default="")
    parser.add_argument("--audit-roll", default="")
    parser.add_argument("--no-audit", action="store_true")
    args = parser.parse_args(argv)
    override = normalize_tier(args.override)
    if args.override and not override:
        print("STATUS=error\nERROR=invalid-override")
        return 2
    rng: object = None
    if args.audit_roll:
        try:
            rng = int(args.audit_roll)
        except ValueError:
            print("STATUS=error\nERROR=invalid-audit-roll")
            return 2
    try:
        resolution = resolve_panel_tier(Path(args.record_file), override=override, rng=rng, audit_enabled=not args.no_audit)
    except (OSError, ValueError) as exc:
        print(f"STATUS=error\nERROR={exc}")
        return 1
    print("STATUS=ok")
    print(f"PANEL_TIER={resolution.panel_tier}")
    print(f"ROUND_CAP={resolution.round_cap}")
    print(f"CODEX_MODEL_ROLE={resolution.codex_model_role}")
    print(f"AUDIT_EVALUATED={'true' if resolution.audit_evaluated else 'false'}")
    print(f"AUDIT_UPGRADE={'true' if resolution.audit_upgrade else 'false'}")
    print(f"OVERRIDE_SOURCE={resolution.override_source}")
    print(f"ESCALATED_ROUND={'true' if resolution.escalated_round else 'false'}")
    return 0


def sync_labels_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py difficulty sync-labels")
    parser.add_argument("--issue", required=True)
    parser.add_argument("--tier", required=True)
    parser.add_argument("--repo", default="")
    args = parser.parse_args(argv)
    tier = args.tier.upper()
    if not tier_valid(tier):
        print("STATUS=error\nERROR=invalid-tier")
        return 2
    repo_args = ["--repo", args.repo] if args.repo else []
    for label in known_labels():
        proc.run(["gh", "issue", "edit", str(args.issue), *repo_args, "--remove-label", label], check=False)
    label = label_for_tier(tier)
    create = proc.run(["gh", "label", "create", label, *repo_args, "--color", "ededed", "--description", "larch difficulty rating"], check=False)
    if create.returncode != 0 and "already exists" not in (create.stderr + create.stdout).lower():
        print("STATUS=warning")
        print("WARNING=label-create-failed")
    add = proc.run(["gh", "issue", "edit", str(args.issue), *repo_args, "--add-label", label], check=False)
    if add.returncode != 0:
        print("STATUS=error")
        print("ERROR=label-add-failed")
        return 1
    print("STATUS=ok")
    print(f"LABEL={label}")
    return 0
