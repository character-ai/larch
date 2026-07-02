"""Difficulty rating helpers for design, implement, and review run logs."""
# pyright: reportUnusedCallResult=false
# ruff: noqa: PLR0913,PLR2004,TRY004,PERF401,SIM114

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast
from larch import io as larch_io
from larch.core import proc

TRIVIAL = "TRIVIAL"
MODERATE = "MODERATE"
HARD = "HARD"
TIERS = (TRIVIAL, MODERATE, HARD)
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
    escalations: list[str]
    panel_skipped: str | None


def tier_valid(value: str) -> bool:
    return value in _TIER_RANK


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


def plan_difficulty(text: str) -> str:
    lines = text.splitlines()
    for line in reversed(lines):
        match = _PLAN_DIFFICULTY_RE.fullmatch(line.strip())
        if match:
            return match.group(1)
    return ""


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
    escalations: tuple[str, ...] = (),
    override_source: str = "",
) -> DifficultyRecord:
    source = implement_rating or design_rating or fallback_rating
    if source is None:
        raise ValueError("at least one difficulty rating is required")
    model_tier = tier_max(
        design_rating.adjusted_tier if design_rating else None,
        implement_rating.adjusted_tier if implement_rating else None,
        fallback_rating.adjusted_tier if fallback_rating else None,
    )
    floors = match_floors(changed_paths)
    applied = tier_max(model_tier, floors.tier)
    derived_override = "floor" if floors.matches and _TIER_RANK[floors.tier] > _TIER_RANK[model_tier] else "none"
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
    )


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
    parser.add_argument("--fallback-tier", default="MODERATE")
    parser.add_argument("--fallback-rationale", default="fallback rating synthesized for recovery path")
    args = parser.parse_args(argv)
    try:
        record = _record_from_args(args)
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
