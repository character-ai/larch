"""Voter calibration, agreement, and scoreboard helpers for larch."""
# pylint: skip-file
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportUnusedImport=false, reportUnusedFunction=false

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from collections.abc import Iterable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple, cast

from larch import io as larch_io
from larch.core import config
from larch.core import logging_util
from larch.core import proc
from larch.git import repo_roots
from larch.review.review_types import JudgeSeverity, ReviewVote

# ---------------------------------------------------------------------------
# Calibration-only constants (private; not re-exported to voting.py callers).

_SEVERITY_VALUES = {severity.value for severity in JudgeSeverity}
_LEGACY_SEVERITY_MAP = {"blocker": JudgeSeverity.major.value, "uncertain": ""}

_CODE_REVIEW_COMPACT_CLASSIFICATION_HEADER = (
    "finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain"
)

_DESIGN_CLASSIFICATION_REQUIRED = frozenset(
    {"finding_id", "finding_reviewers", "voting_result", "v1_vote", "v2_vote", "v3_vote"}
)
_CODE_REVIEW_COMPACT_REQUIRED = frozenset(_CODE_REVIEW_COMPACT_CLASSIFICATION_HEADER.split("\t"))
# Keep in sync with CODE_REVIEW_FINDINGS_CLASSIFICATION_HEADER in voting.py.
_CODE_REVIEW_TOOL_REQUIRED = frozenset({
    "finding_id",
    "reviewer_slots",
    "voting_result",
    "v1_vote",
    "v1_correctness",
    "v1_severity",
    "v1_quality",
    "v1_uncertain",
    "v1_tool",
    "v2_vote",
    "v2_correctness",
    "v2_severity",
    "v2_quality",
    "v2_uncertain",
    "v2_tool",
    "v3_vote",
    "v3_correctness",
    "v3_severity",
    "v3_quality",
    "v3_uncertain",
    "v3_tool",
    "scope",
})

_DESIGN_VOTER_FALLBACKS = {
    1: "codex-validity",
    2: "codex-plan-fidelity",
    3: "codex-pragmatism",
}
_CODE_REVIEW_VOTER_FALLBACKS = {
    1: "codex-validity",
    2: "codex-plan-fidelity",
    3: "codex-pragmatism",
}
_YES_NO = {ReviewVote.yes.value, ReviewVote.no.value}
_BASE_VOTER_TOOLS = frozenset({"claude", "codex", "cursor"})
_CALIBRATION_PANEL = "global"
_CALIBRATION_SNAPSHOT_HEADER = (
    "tool",
    "yes_votes",
    "valid_yes_severity_count",
    "major",
    "minor",
    "nit",
    "missing_severity",
    "high_rate",
    "calibration_score",
    "uncalibrated",
)


# ---------------------------------------------------------------------------
# Helpers used by both calibration and tally code (re-exported by voting.py).


def valid_panel_severity(token: str) -> str | None:
    normalized = token.strip().lower()
    normalized = _LEGACY_SEVERITY_MAP.get(normalized, normalized)
    return normalized if normalized in _SEVERITY_VALUES else None


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Data types.


@dataclass(frozen=True)
class VoterCalibrationStat:
    tool: str
    yes_votes: int
    valid_yes_severity_count: int
    major: int
    minor: int
    nit: int
    missing_severity: int
    high_rate: float | None
    calibration_score: float | None
    uncalibrated: bool


@dataclass(frozen=True)
class VoterCalibrationDiscoveryRow:
    panel_kind: str
    path: Path
    run_dir: Path


class VoterAgreementTsvParse(NamedTuple):
    rows: list[dict[str, object]]
    malformed_rows: int
    ineligible_rows: int


class ClassificationRowPrep(NamedTuple):
    raw_row: dict[str, str]
    header: list[str]
    panel: str
    compact: bool
    label_compact: bool
    reviewer_column: str
    voter_votes: list[tuple[str, str]]
    voter_severities: list[str]


# ---------------------------------------------------------------------------
# Panel / TSV parsing helpers.


def _normalize_panel_kind(panel_kind: str) -> str:
    value = (panel_kind or "").strip().lower()
    if value in {"design", "plan-review", "plan_review"}:
        return "design"
    if value in {"code-review", "code_review", "implement", "review"}:
        return "code-review"
    return value or "unknown"


def _normalize_vote_cell(value: str) -> str:
    vote = (value or "").strip().upper()
    if vote == "EXONERATE":
        return "NO"
    return vote if vote in _YES_NO else ""


def voter_agreement_row_from_panel(
    *,
    voting_result: str,
    voter_votes: list[tuple[str, str]],
    panel: str = "",
    voter_severities: list[str] | None = None,
) -> dict[str, object] | None:
    if voter_severities is not None and len(voter_severities) != len(voter_votes):
        raise ValueError("voter_severities must align with voter_votes")
    result = (voting_result or "").strip().lower()
    if result not in {"accepted", "rejected"}:
        return None
    parseable: list[tuple[str, str]] = [(label, vote) for label, vote in voter_votes if _normalize_vote_cell(vote)]
    if len(parseable) < 2:  # noqa: PLR2004
        return None
    voters: list[dict[str, object]] = []
    for idx, (raw_label, raw_vote) in enumerate(voter_votes):
        label = (raw_label or "").strip()
        if not label:
            continue
        vote = _normalize_vote_cell(raw_vote)
        agrees = (result == "accepted" and vote == "YES") or (result == "rejected" and vote == "NO")
        voter_row: dict[str, object] = {
            "voter": label,
            "vote": vote,
            "agree": 1 if vote and agrees else 0,
            "disagree": 1 if vote and not agrees else 0,
            "missing": 0 if vote else 1,
        }
        if voter_severities is not None:
            voter_row["severity"] = voter_severities[idx]
        voters.append(voter_row)
    if not voters:
        return None
    return {"panel": _normalize_panel_kind(panel), "voting_result": result, "voters": voters}


def _dict_rows_from_tsv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return [], []
    reader = csv.DictReader(lines, delimiter="\t")
    return list(reader.fieldnames or []), [dict(row) for row in reader]


def _legacy_compact_rows_from_tsv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return [], []
    header = lines[0].split("\t")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        cells = line.split("\t")
        row = {name: cells[idx] if idx < len(cells) else "" for idx, name in enumerate(header)}
        rows.append(row)
    return header, rows


def _voter_label(*, row: dict[str, str], pos: int, panel: str, compact: bool = False) -> str:
    if not compact:
        tool = (row.get(f"v{pos}_tool") or "").strip()
        if tool:
            return tool
    if panel == "design":
        return _DESIGN_VOTER_FALLBACKS[pos]
    if compact:
        return f"v{pos}"
    return _CODE_REVIEW_VOTER_FALLBACKS[pos]


def classification_tsv_schema_supported(text: str, *, panel_kind: str) -> bool:
    panel = _normalize_panel_kind(panel_kind)
    header, _ = _dict_rows_from_tsv(text)
    if not header:
        return False
    header_set = set(header)
    if panel == "design":
        return header_set >= _DESIGN_CLASSIFICATION_REQUIRED
    if panel == "code-review":
        return header_set >= _CODE_REVIEW_COMPACT_REQUIRED or header_set >= _CODE_REVIEW_TOOL_REQUIRED
    return False


def _classification_tsv_rows_for_panel(text: str, *, panel_kind: str) -> tuple[str, list[str], list[dict[str, str]], bool]:
    panel = _normalize_panel_kind(panel_kind)
    if not classification_tsv_schema_supported(text, panel_kind=panel):
        return panel, [], [], False
    header, rows = _dict_rows_from_tsv(text)
    if not header:
        return panel, [], [], False
    header_set = set(header)
    compact = False
    if panel == "design":
        compact = False
    elif panel == "code-review":
        compact = not all(f"v{pos}_severity" in header_set for pos in (1, 2, 3))
        if compact:
            header, rows = _legacy_compact_rows_from_tsv(text)
    else:
        return panel, [], [], False
    return panel, header, rows, compact


def classification_row_panel_inputs(text: str, *, panel_kind: str) -> list[ClassificationRowPrep]:
    """Return raw classification-row inputs for ground-truth diagnostics.

    `voter_agreement_rows_from_tsv()` remains panel-self-agreement only; do not
    use its agreement-shaped rows for ground-truth row materialization.
    """
    panel, header, rows, compact = _classification_tsv_rows_for_panel(text, panel_kind=panel_kind)
    if not header:
        return []
    header_set = set(header)
    label_compact = compact or (
        panel == "code-review" and not any(f"v{pos}_tool" in header_set for pos in (1, 2, 3))
    )
    reviewer_column = "finding_reviewers" if "finding_reviewers" in header_set else "reviewer_slots"
    out: list[ClassificationRowPrep] = []
    for row in rows:
        voter_votes = [
            (_voter_label(row=row, pos=pos, panel=panel, compact=label_compact), row.get(f"v{pos}_vote") or "")
            for pos in (1, 2, 3)
        ]
        voter_severities = [row.get(f"v{pos}_severity") or "" for pos in (1, 2, 3)]
        out.append(
            ClassificationRowPrep(
                raw_row=dict(row),
                header=list(header),
                panel=panel,
                compact=compact,
                label_compact=label_compact,
                reviewer_column=reviewer_column,
                voter_votes=voter_votes,
                voter_severities=voter_severities,
            )
        )
    return out


def voter_agreement_rows_from_tsv(text: str, *, panel_kind: str) -> VoterAgreementTsvParse:
    panel, header, rows, compact = _classification_tsv_rows_for_panel(text, panel_kind=panel_kind)
    if not header:
        return VoterAgreementTsvParse([], 0, 0)
    header_set = set(header)

    out: list[dict[str, object]] = []
    malformed_rows = 0
    ineligible_rows = 0
    label_compact = compact or (
        panel == "code-review" and not any(f"v{pos}_tool" in header_set for pos in (1, 2, 3))
    )
    for row in rows:
        voter_votes = [
            (_voter_label(row=row, pos=pos, panel=panel, compact=label_compact), row.get(f"v{pos}_vote") or "")
            for pos in (1, 2, 3)
        ]
        voter_severities = [row.get(f"v{pos}_severity") or "" for pos in (1, 2, 3)]
        result = (row.get("voting_result") or "").strip().lower()
        agreement_row = voter_agreement_row_from_panel(
            voting_result=row.get("voting_result") or "",
            voter_votes=voter_votes,
            panel=panel,
            voter_severities=voter_severities,
        )
        if agreement_row is not None:
            out.append(agreement_row)
            continue
        parseable: list[tuple[str, str]] = [(label, vote) for label, vote in voter_votes if _normalize_vote_cell(vote)]
        if result == "neutral" or (
            result in {"accepted", "rejected"} and len(parseable) < 2  # noqa: PLR2004
        ):
            ineligible_rows += 1
        else:
            malformed_rows += 1
    return VoterAgreementTsvParse(out, malformed_rows, ineligible_rows)


# ---------------------------------------------------------------------------
# Agreement and severity distribution computation.


def compute_voter_agreement(
    rows: Iterable[dict[str, object]],
    *,
    min_votes: int = 20,
    outlier_threshold: float = 0.50,
) -> list[dict[str, object]]:
    aggregate: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        panel = str(row.get("panel") or "unknown")
        voters_obj = row.get("voters")
        if not isinstance(voters_obj, list):
            continue
        voters = cast("list[object]", voters_obj)
        for voter_obj in voters:
            if not isinstance(voter_obj, dict):
                continue
            voter_row = cast("dict[str, object]", voter_obj)
            voter = str(voter_row.get("voter") or "").strip()
            if not voter:
                continue
            key: tuple[str, str] = (panel, voter)
            record = aggregate.setdefault(
                key,
                {
                    "voter": voter,
                    "panel": panel,
                    "eligible": 0,
                    "agree": 0,
                    "disagree": 0,
                    "missing": 0,
                    "agreement_rate": None,
                    "outlier": False,
                },
            )
            agree = int(voter_row.get("agree") or 0)
            disagree = int(voter_row.get("disagree") or 0)
            missing = int(voter_row.get("missing") or 0)
            record["agree"] = int(record["agree"]) + agree
            record["disagree"] = int(record["disagree"]) + disagree
            record["missing"] = int(record["missing"]) + missing
            if agree or disagree:
                record["eligible"] = int(record["eligible"]) + 1

    records = list(aggregate.values())
    for record in records:
        denominator = int(record["agree"]) + int(record["disagree"])
        rate = (int(record["agree"]) / denominator) if denominator else None
        record["agreement_rate"] = rate
        record["outlier"] = bool(
            int(record["eligible"]) >= min_votes
            and rate is not None
            and rate < outlier_threshold
        )
    return sorted(records, key=lambda r: (str(r["panel"]), str(r["voter"])))


def compute_voter_severity_distribution(
    rows: Iterable[dict[str, object]],
    *,
    high_severity_threshold: float = 0.90,
) -> list[dict[str, object]]:
    aggregate: dict[tuple[str, str], dict[str, object]] = {}
    severity_buckets = tuple(severity.value for severity in JudgeSeverity)
    for row in rows:
        panel = str(row.get("panel") or "unknown")
        voters_obj = row.get("voters")
        if not isinstance(voters_obj, list):
            continue
        voters = cast("list[object]", voters_obj)
        for voter_obj in voters:
            if not isinstance(voter_obj, dict):
                continue
            voter_row = cast("dict[str, object]", voter_obj)
            voter = str(voter_row.get("voter") or "").strip()
            if not voter:
                continue
            key = (panel, voter)
            record = aggregate.setdefault(
                key,
                {
                    "voter": voter,
                    "panel": panel,
                    "yes_votes": 0,
                    "major": 0,
                    "minor": 0,
                    "nit": 0,
                    "missing_severity": 0,
                    "valid_yes_severity_count": 0,
                    "high_rate": None,
                    "calibration_score": None,
                    "uncalibrated": False,
                },
            )
            if str(voter_row.get("vote") or "").strip().upper() != ReviewVote.yes.value:
                continue
            record["yes_votes"] = int(record["yes_votes"]) + 1
            severity = valid_panel_severity(str(voter_row.get("severity") or ""))
            if severity in severity_buckets:
                record[severity] = int(record[severity]) + 1
                record["valid_yes_severity_count"] = int(record["valid_yes_severity_count"]) + 1
            else:
                record["missing_severity"] = int(record["missing_severity"]) + 1

    records = list(aggregate.values())
    for record in records:
        valid_count = int(record["valid_yes_severity_count"])
        if valid_count:
            high = int(record["major"])
            high_rate = high / valid_count
            record["high_rate"] = high_rate
            record["calibration_score"] = severity_calibration_score(
                high_rate,
                high_severity_threshold=high_severity_threshold,
            )
            record["uncalibrated"] = high_rate > high_severity_threshold
    return sorted(records, key=lambda r: (str(r["panel"]), str(r["voter"])))


def _format_rate(value: object) -> str:
    return "n/a" if value is None else f"{float(value):.3f}"


def severity_calibration_score(high_rate: object, *, high_severity_threshold: float) -> float | None:
    if high_rate is None:
        return None
    if high_severity_threshold >= 1.0:
        return 1.0
    threshold = max(high_severity_threshold, 0.0)
    rate = float(high_rate)
    if rate <= threshold:
        return 1.0
    score = 1 - ((rate - threshold) / (1 - threshold))
    return max(0.0, min(1.0, score))


def normalize_voter_label_to_base_tool(label: str) -> str | None:
    normalized = (label or "").strip().casefold()
    if normalized == "claude":
        return "claude"
    if normalized.startswith("codex"):
        return "codex"
    if normalized.startswith("cursor"):
        return "cursor"
    if normalized == "v1":
        return "cursor"
    if normalized in {"v2", "v3"}:
        return "codex"
    return None


# ---------------------------------------------------------------------------
# Calibration log discovery and stats.


def _voter_calibration_run_dir(path: Path, *, panel_kind: str) -> Path:
    parts = list(path.parts)
    if panel_kind == "design" and "plan-review" in parts:
        return path.parents[2]
    if "round-" in path.parent.name:
        return path.parents[1]
    return path.parent


def _parse_iso_datetime(raw: str) -> datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _voter_calibration_run_started_at(run_dir: Path) -> datetime | None:
    for name in ("manifest.json", "run-manifest.json"):
        path = run_dir / name
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, Mapping):
            return _parse_iso_datetime(str(data.get("started_at") or data.get("updated_at") or ""))
    return None


def discover_voter_calibration_logs(log_root: Path) -> list[VoterCalibrationDiscoveryRow]:
    root = Path(log_root)
    rows: list[VoterCalibrationDiscoveryRow] = []
    for panel_kind, pattern in (
        ("design", "design/*/plan-review/round-*/findings-classification.tsv"),
        ("code-review", "implement/*/round-*/findings-classification.tsv"),
        ("code-review", "review/*/review-findings-classification-round-*.tsv"),
    ):
        rows.extend(
            VoterCalibrationDiscoveryRow(
                panel_kind=panel_kind,
                path=path,
                run_dir=_voter_calibration_run_dir(path, panel_kind=panel_kind),
            )
            for path in sorted(root.glob(pattern))
        )
    return rows


def _recent_voter_calibration_logs(*, log_root: Path, window: int) -> list[VoterCalibrationDiscoveryRow]:
    by_run: dict[Path, list[VoterCalibrationDiscoveryRow]] = {}
    for row in discover_voter_calibration_logs(log_root):
        by_run.setdefault(row.run_dir, []).append(row)
    run_dirs = sorted(
        by_run,
        key=lambda run_dir: (
            _voter_calibration_run_started_at(run_dir) or datetime.min.replace(tzinfo=UTC),
            run_dir.as_posix(),
        ),
        reverse=True,
    )
    selected: list[VoterCalibrationDiscoveryRow] = []
    for run_dir in run_dirs[:window]:
        selected.extend(sorted(by_run[run_dir], key=lambda row: row.path.as_posix()))
    return selected


def _globalized_voter_agreement_row(row: Mapping[str, object]) -> dict[str, object] | None:
    voters_obj = row.get("voters")
    if not isinstance(voters_obj, list):
        return None
    voters: list[dict[str, object]] = []
    for voter_obj in cast("list[object]", voters_obj):
        if not isinstance(voter_obj, dict):
            continue
        voter_row = cast("dict[str, object]", voter_obj)
        base_tool = normalize_voter_label_to_base_tool(str(voter_row.get("voter") or ""))
        if base_tool is None:
            continue
        rewritten = dict(voter_row)
        rewritten["voter"] = base_tool
        voters.append(rewritten)
    if not voters:
        return None
    out = dict(row)
    out["panel"] = _CALIBRATION_PANEL
    out["voters"] = voters
    return out


def voter_calibration_stats_from_logs(*, log_root: Path, window: int) -> list[VoterCalibrationStat]:
    rows: list[dict[str, object]] = []
    for discovered in _recent_voter_calibration_logs(log_root=log_root, window=max(window, 1)):
        try:
            text = discovered.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not classification_tsv_schema_supported(text, panel_kind=discovered.panel_kind):
            continue
        try:
            parsed = voter_agreement_rows_from_tsv(text, panel_kind=discovered.panel_kind)
        except (csv.Error, ValueError):
            continue
        for row in parsed.rows:
            global_row = _globalized_voter_agreement_row(row)
            if global_row is not None:
                rows.append(global_row)
    stats: list[VoterCalibrationStat] = []
    for record in compute_voter_severity_distribution(rows):
        tool = normalize_voter_label_to_base_tool(str(record.get("voter") or ""))
        if tool is None:
            continue
        valid_count = int(record.get("valid_yes_severity_count") or 0)
        if valid_count <= 0:
            continue
        high_rate_obj = record.get("high_rate")
        score_obj = record.get("calibration_score")
        stats.append(
            VoterCalibrationStat(
                tool=tool,
                yes_votes=int(record.get("yes_votes") or 0),
                valid_yes_severity_count=valid_count,
                major=int(record.get("major") or 0),
                minor=int(record.get("minor") or 0),
                nit=int(record.get("nit") or 0),
                missing_severity=int(record.get("missing_severity") or 0),
                high_rate=float(high_rate_obj) if high_rate_obj is not None else None,
                calibration_score=float(score_obj) if score_obj is not None else None,
                uncalibrated=bool(record.get("uncalibrated")),
            )
        )
    return sorted(stats, key=lambda stat: stat.tool)


def _format_snapshot_float(value: float | None) -> str:
    return "" if value is None else f"{value:.3f}"


def write_voter_calibration_stats(*, path: Path, stats: Iterable[VoterCalibrationStat]) -> bool:
    rows = list(stats)
    if not rows:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(_CALIBRATION_SNAPSHOT_HEADER)
            for stat in rows:
                writer.writerow(
                    [
                        stat.tool,
                        stat.yes_votes,
                        stat.valid_yes_severity_count,
                        stat.major,
                        stat.minor,
                        stat.nit,
                        stat.missing_severity,
                        _format_snapshot_float(stat.high_rate),
                        _format_snapshot_float(stat.calibration_score),
                        str(stat.uncalibrated).lower(),
                    ]
                )
        Path(tmp).replace(path)
    except OSError:
        with suppress(OSError):
            Path(tmp).unlink()
        raise
    return True


def _int_cell(*, row: Mapping[str, str], key: str) -> int | None:
    try:
        return int((row.get(key) or "").strip())
    except ValueError:
        return None


def _float_cell(*, row: Mapping[str, str], key: str) -> float | None:
    value = (row.get(key) or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_voter_calibration_stats(path: Path) -> dict[str, VoterCalibrationStat]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size <= 0:
        return {}
    try:
        reader = csv.DictReader(path.read_text(encoding="utf-8", errors="replace").splitlines(), delimiter="\t")
        if tuple(reader.fieldnames or ()) != _CALIBRATION_SNAPSHOT_HEADER:
            return {}
        stats: dict[str, VoterCalibrationStat] = {}
        for row in reader:
            tool = normalize_voter_label_to_base_tool(row.get("tool") or "")
            if tool is None:
                continue
            ints = {
                key: _int_cell(row=row, key=key)
                for key in (
                    "yes_votes",
                    "valid_yes_severity_count",
                    "major",
                    "minor",
                    "nit",
                    "missing_severity",
                )
            }
            if any(value is None for value in ints.values()):
                continue
            valid_count = ints["valid_yes_severity_count"] or 0
            if valid_count <= 0:
                continue
            stats[tool] = VoterCalibrationStat(
                tool=tool,
                yes_votes=ints["yes_votes"] or 0,
                valid_yes_severity_count=valid_count,
                major=ints["major"] or 0,
                minor=ints["minor"] or 0,
                nit=ints["nit"] or 0,
                missing_severity=ints["missing_severity"] or 0,
                high_rate=_float_cell(row=row, key="high_rate"),
                calibration_score=_float_cell(row=row, key="calibration_score"),
                uncalibrated=(row.get("uncalibrated") or "").strip().lower() == "true",
            )
        return stats
    except OSError:
        return {}


# ---------------------------------------------------------------------------
# Environment-based log-root resolution.


def _env_repo_root(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    path = Path(raw)
    root = repo_roots.consumer_repo_root(path)
    if root is not None:
        return root
    try:
        return path.resolve()
    except OSError:
        return path


def _implement_tmpdir_from_review_tmpdir(review_tmpdir: Path) -> Path:
    parent = review_tmpdir.parent
    if (parent / "session-env.sh").is_file() or (parent / ".larch-keepalive").is_file():
        return parent
    return review_tmpdir


def _session_env_value(*, session: Path, key: str) -> str:
    if not session.is_file() or session.is_symlink():
        return ""
    for line in session.read_text(encoding="utf-8", errors="replace").splitlines():
        field, sep, value = line.partition("=")
        if sep and field == key:
            return value.strip().strip("'\"")
    return ""


def _reject_plugin_calibration_root(root: Path) -> Path | None:
    try:
        resolved = root.resolve()
    except OSError:
        return root
    plugin = os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, "").strip()
    if plugin:
        with suppress(OSError):
            if resolved == Path(plugin).resolve():
                return None
    with suppress(OSError):
        if resolved == _plugin_root().resolve():
            return None
    return root


def _repo_root_from_anchor(raw: str) -> Path | None:
    cleaned = (raw or "").strip()
    if not cleaned:
        return None
    root = repo_roots.consumer_repo_root(Path(cleaned))
    if root is not None:
        return root
    with suppress(OSError):
        return Path(cleaned).resolve()
    return None


def _implement_session_repo_root(implement_tmpdir: Path) -> Path | None:
    session = implement_tmpdir / "session-env.sh"
    for key in ("CLAUDE_PROJECT_DIR", "REPO_CWD"):
        root = _repo_root_from_anchor(_session_env_value(session=session, key=key))
        if root is not None:
            return root
    keepalive = implement_tmpdir / ".larch-keepalive"
    if keepalive.is_file() and not keepalive.is_symlink():
        clone = larch_io.read_kv(path=keepalive, key="CLONE_PATH", default="", first_match=True)
        if clone:
            root = _repo_root_from_anchor(clone)
            if root is not None:
                return root
    return None


def _implement_repo_root_from_review_tmpdir(review_tmpdir: Path) -> Path | None:
    implement_tmpdir = _implement_tmpdir_from_review_tmpdir(review_tmpdir)
    root = _implement_session_repo_root(implement_tmpdir)
    if root is not None:
        return root
    keepalive = review_tmpdir / ".larch-keepalive"
    if not keepalive.is_file() or keepalive.is_symlink():
        return None
    clone = larch_io.read_kv(path=keepalive, key="CLONE_PATH", default="", first_match=True)
    if not clone:
        return None
    return _repo_root_from_anchor(clone)


def _resolve_design_calibration_repo_root(design_tmpdir: Path) -> Path | None:
    # Inline design_lifecycle._resolve_working_tree_root to avoid cyclic import.
    resolved = _session_env_value(session=design_tmpdir / "source-env.sh", key="REPO_ROOT")
    if not resolved:
        _r = proc.run(["git", "rev-parse", "--show-toplevel"])
        if _r.returncode == 0:
            resolved = _r.stdout.strip()
    if not resolved:
        return None
    root = _repo_root_from_anchor(resolved)
    if root is None:
        return None
    return _reject_plugin_calibration_root(root)


def _resolve_voter_calibration_log_root(
    *,
    design_tmpdir: Path | None = None,
    review_tmpdir: Path | None = None,
) -> Path:
    for env_name in ("LARCH_CONSUMER_REPO", "CLAUDE_PROJECT_DIR", "REPO_ROOT"):
        root = _env_repo_root(env_name)
        if root is not None:
            root = _reject_plugin_calibration_root(root)
            if root is not None:
                return (root / "larch-logs").resolve()
    if design_tmpdir is not None:
        root = _resolve_design_calibration_repo_root(Path(design_tmpdir))
        if root is not None:
            return (root / "larch-logs").resolve()
        msg = "design calibration log root unresolved"
        raise ValueError(msg)
    if review_tmpdir is not None:
        root = _implement_repo_root_from_review_tmpdir(Path(review_tmpdir))
        if root is not None:
            root = _reject_plugin_calibration_root(root)
            if root is not None:
                return (root / "larch-logs").resolve()
        msg = "review calibration log root unresolved"
        raise ValueError(msg)
    root = repo_roots.consumer_repo_root()
    if root is not None:
        root = _reject_plugin_calibration_root(root)
        if root is not None:
            return (root / "larch-logs").resolve()
    msg = "voter calibration log root unresolved"
    raise ValueError(msg)


def _default_voter_calibration_log_root(*, review_tmpdir: Path | None = None) -> Path:
    return _resolve_voter_calibration_log_root(design_tmpdir=None, review_tmpdir=review_tmpdir)


def _resolve_voter_calibration_window(raw: str | None) -> int:
    value = (raw or "").strip()
    try:
        parsed = int(value)
    except ValueError:
        return config.VOTER_CALIBRATION_WINDOW_DEFAULT
    if parsed <= 0:
        return config.VOTER_CALIBRATION_WINDOW_DEFAULT
    return parsed


def voter_calibration_snapshot_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py voter-calibration snapshot")
    parser.add_argument(
        "--log-root",
        default="",
        help="larch-logs root; default resolves consumer repo from LARCH_CONSUMER_REPO, CLAUDE_PROJECT_DIR, or session anchors",
    )
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--window",
        default="",
        help="recent run-directory window; default reads LARCH_VOTER_CALIBRATION_WINDOW, then falls back to 100",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        log_root = Path(args.log_root).resolve() if args.log_root else _default_voter_calibration_log_root()
    except ValueError as exc:
        _ = sys.stderr.write(f"voter-calibration snapshot: {exc}\n")
        return 1
    window_raw = str(args.window) if args.window else os.environ.get(config.ENV_LARCH_VOTER_CALIBRATION_WINDOW)
    window = _resolve_voter_calibration_window(window_raw)
    out = Path(str(args.out))
    try:
        stats = voter_calibration_stats_from_logs(log_root=log_root, window=window)
        if write_voter_calibration_stats(path=out, stats=stats):
            logging_util.emit_kv(key="CALIBRATION_STATS_FILE", value=str(out))
        else:
            with suppress(FileNotFoundError):
                out.unlink()
            logging_util.emit_kv(key="CALIBRATION_STATS_FILE", value="")
            logging_util.emit_kv(key="CALIBRATION_STATS_STATUS", value="no-data")
    except OSError as exc:
        _ = sys.stderr.write(f"voter-calibration snapshot: {exc}\n")
        return 1
    return 0


# ---------------------------------------------------------------------------
# Scoreboard renderers.


def render_voter_scoreboard(records: Iterable[dict[str, object]]) -> str:
    rows = list(records)
    buf = "## Voter Agreement Scoreboard\n\n"
    buf += "| Panel | Voter | Eligible | Agree | Disagree | Missing | Agreement | Outlier |\n"
    buf += "|---|---|---:|---:|---:|---:|---:|---|\n"
    if not rows:
        buf += "| undefined | n/a | 0 | 0 | 0 | 0 | n/a | false |\n"
        buf += "\nAgreement is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n"
        return buf
    for record in rows:
        buf += (
            f"| {record['panel']} | {record['voter']} | {record['eligible']} | "
            f"{record['agree']} | {record['disagree']} | {record['missing']} | "
            f"{_format_rate(record['agreement_rate'])} | {str(bool(record['outlier'])).lower()} |\n"
        )
    return buf


def render_voter_severity_scoreboard(records: Iterable[dict[str, object]]) -> str:
    rows = list(records)
    buf = "## Voter Severity Scoreboard\n\n"
    buf += "| Panel | Voter | YES Votes | Major | Minor | Nit | Missing Severity | High Rate | Calibration Score | Uncalibrated |\n"
    buf += "|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n"
    if not rows:
        buf += "| undefined | n/a | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |\n"
        buf += "\nSeverity calibration is undefined when no accepted or rejected finding has at least two parseable YES/NO voter cells.\n"
        return buf
    for record in rows:
        buf += (
            f"| {record['panel']} | {record['voter']} | {record['yes_votes']} | "
            f"{record['major']} | {record['minor']} | {record['nit']} | "
            f"{record['missing_severity']} | {_format_rate(record['high_rate'])} | {_format_rate(record['calibration_score'])} | "
            f"{str(bool(record['uncalibrated'])).lower()} |\n"
        )
    return buf


def render_voter_agreement_and_severity_scoreboards(
    agreement_rows: Iterable[dict[str, object]],
    *,
    high_severity_threshold: float = 0.90,
) -> str:
    rows = list(agreement_rows)
    agreement = render_voter_scoreboard(compute_voter_agreement(rows))
    severity = render_voter_severity_scoreboard(
        compute_voter_severity_distribution(rows, high_severity_threshold=high_severity_threshold)
    )
    return agreement.rstrip() + "\n\n" + severity
