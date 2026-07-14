"""Review phase detail and round metadata helpers."""
# pylint: disable=unused-import
# Shared private helpers are invoked from sibling final-report modules and tests.
# pyright: reportUnknownVariableType=false, reportUnusedCallResult=false, reportPrivateUsage=false, reportUnusedImport=false, reportUnusedFunction=false

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from larch.agents import collect_results
from larch.calibration import difficulty
from larch.rendering.gantt import GanttRow, format_mss, render_gantt
from larch import io as larch_io
from larch.core import config
from larch.core import logging_util
from larch.report.timing import TIMING_VENDOR_MIN_COLS
from larch.review import plan_review_round
from larch.report import report_tokens_cost
from larch.review import voting
from larch.review.review_types import is_security_block_text, parse_blocks

TIMING_ROUND_MIN_COLS = 8
TIMING_ROUND_SKILL_COL = 3
TIMING_ROUND_ROUND_NUM_COL = 5
TIMING_ROUND_END_COL = 7
# Issue #5504: reserved trailing column repurposed as the 1-based round attempt index
# (written by timing.TimingLedger.record_round). Rows predating it carry "-" -> attempt 1.
TIMING_ROUND_ATTEMPT_COL = 12
TIMING_VENDOR_VENDOR_COL = 5
TIMING_VENDOR_KIND_COL = 6
TIMING_VENDOR_START_COL = 7
TIMING_VENDOR_END_COL = 8
TIMING_VENDOR_OUTPUT_COL = 10
TIMING_VENDOR_STATUS_COL = 12
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
RENDER_PHASE_DETAIL_TIMEOUT_SECONDS = 15
PROGRESS_GANTT_ROW_CAP = 25
MIN_MARKDOWN_TABLE_PARTS = 4
MIN_TSV_RESULT_COLS = 3
LABEL_MAP_MIN_COLS = 2
MD_RESULT_COL_FROM_END = 2
MD_FALLBACK_RESULT_COL_FROM_END = 3
OOS_FILEABLE_COUNT_INDEX = 6
CLASSIFICATION_VOTE_RE = re.compile(r"^v([0-9]+)_vote$")




def _round_number(path: Path) -> int | None:
    match = re.match(r"^round-([1-9][0-9]*)$", path.name)
    if not match:
        return None
    return int(match.group(1))


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict):
        return cast("dict[str, object]", parsed)
    return {}


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _nested_dict(*, data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return {}


def _add_round_vendor_cost_row(
    *,
    data: dict[str, object],
    sums: dict[str, dict[str, int]],
    claude_sub_by_model: dict[str, dict[str, int]],
) -> None:
    vendor = str(data.get("vendor") or "")
    if vendor not in {"codex", "cursor", "claude_sub"}:
        return
    model = str(data.get("model") or "")
    if vendor == "claude_sub":
        model = model or config.claude_sub_default_model(str(data.get("raw") or ""))
        bucket = claude_sub_by_model.setdefault(model, {"input": 0, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 0})
        bucket["input"] += _as_int(data.get("input"))
        bucket["cache_read"] += _as_int(data.get("cache_read"))
        bucket["cache_create_5m"] += _as_int(data.get("cache_create"))
        bucket["output"] += _as_int(data.get("output"))
        return
    bucket_key = vendor
    if vendor == "codex" and model in report_tokens_cost.CODEX_MINI_MODELS:
        bucket_key = "codex_mini"
    elif vendor == "cursor" and model in report_tokens_cost.CURSOR_GROK_MODELS:
        bucket_key = "cursor_grok"
    bucket = sums.setdefault(bucket_key, {"input": 0, "cache_read": 0, "cache_create": 0, "output": 0})
    bucket["input"] += _as_int(data.get("input"))
    bucket["cache_read"] += _as_int(data.get("cache_read"))
    bucket["cache_create"] += _as_int(data.get("cache_create"))
    bucket["output"] += _as_int(data.get("output"))


def _round_vendor_cost_argv(
    *,
    sums: dict[str, dict[str, int]],
    claude_sub_by_model: dict[str, dict[str, int]],
) -> list[str]:
    argv: list[str] = []
    for vendor, bucket in sums.items():
        if vendor == "codex":
            argv.extend(["--codex-input-tokens", str(bucket["input"]), "--codex-cached-input-tokens", str(bucket["cache_read"]), "--codex-output-tokens", str(bucket["output"])])
        elif vendor == "codex_mini":
            argv.extend(["--codex-mini-input-tokens", str(bucket["input"]), "--codex-mini-cached-input-tokens", str(bucket["cache_read"]), "--codex-mini-output-tokens", str(bucket["output"])])
        elif vendor == "cursor":
            argv.extend(["--cursor-input-tokens", str(bucket["input"]), "--cursor-cache-read-tokens", str(bucket["cache_read"]), "--cursor-output-tokens", str(bucket["output"])])
        elif vendor == "cursor_grok":
            argv.extend(["--cursor-grok-input-tokens", str(bucket["input"]), "--cursor-grok-cache-read-tokens", str(bucket["cache_read"]), "--cursor-grok-output-tokens", str(bucket["output"])])
    if claude_sub_by_model:
        argv.extend(report_tokens_cost.claude_sub_argv_from_buckets(by_model=claude_sub_by_model, bucket={}))
    return argv


def _fmt_hms(seconds: int | None) -> str:
    if seconds is None or seconds <= 0:
        return "N/A"
    hours = seconds // SECONDS_PER_HOUR
    minutes = (seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
    secs = seconds % SECONDS_PER_MINUTE
    if hours > 0:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes > 0:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _read_lines_best_effort(path: Path | None) -> list[str]:
    if path is None:
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _timing_round_windows(
    timing_ledger: Path | None,
    *,
    skill: str,
    round_num: int,
    skill_filtered: bool,
) -> tuple[int, int] | None:
    starts: list[int] = []
    ends: list[int] = []
    round_s = str(round_num)
    for line in _read_lines_best_effort(timing_ledger):
        cols = line.split("\t")
        if len(cols) < TIMING_ROUND_MIN_COLS or cols[0] != "v1" or cols[1] != "round":
            continue
        if skill_filtered and cols[TIMING_ROUND_SKILL_COL] != skill:
            continue
        if cols[TIMING_ROUND_ROUND_NUM_COL] != round_s:
            continue
        try:
            starts.append(int(cols[6]))
            ends.append(int(cols[TIMING_ROUND_END_COL]))
        except ValueError:
            continue
    if not starts or not ends:
        return None
    return min(starts), max(ends)


def _timing_round_attempt_windows(
    timing_ledger: Path | None,
    *,
    round_num: int,
    skill_filtered: bool = False,
    skill: str = "",
) -> list[tuple[int, int, int]]:
    """Per-attempt ``(attempt, start, end)`` windows for a round number, ordered by attempt.

    Issue #5504: a stall recovery can rerun the same round in one session, writing multiple
    ``v1 round`` rows for the same round number. Grouping by the explicit attempt column
    (``TIMING_ROUND_ATTEMPT_COL``) keeps each attempt's reviewer and post-aggregation probe
    rows inside their own window instead of collapsing them into one merged span. Rows that
    predate the attempt column (trailing ``-``) default to attempt 1, so legacy ledgers render
    exactly as before.
    """
    by_attempt: dict[int, tuple[int, int]] = {}
    round_s = str(round_num)
    for line in _read_lines_best_effort(timing_ledger):
        cols = line.split("\t")
        if len(cols) < TIMING_ROUND_MIN_COLS or cols[0] != "v1" or cols[1] != "round":
            continue
        if skill_filtered and cols[TIMING_ROUND_SKILL_COL] != skill:
            continue
        if cols[TIMING_ROUND_ROUND_NUM_COL] != round_s:
            continue
        try:
            start_s = int(cols[6])
            end_s = int(cols[TIMING_ROUND_END_COL])
        except ValueError:
            continue
        attempt = 1
        if len(cols) > TIMING_ROUND_ATTEMPT_COL and cols[TIMING_ROUND_ATTEMPT_COL].isdigit():
            attempt = int(cols[TIMING_ROUND_ATTEMPT_COL])
        if attempt in by_attempt:
            prev_start, prev_end = by_attempt[attempt]
            by_attempt[attempt] = (min(prev_start, start_s), max(prev_end, end_s))
        else:
            by_attempt[attempt] = (start_s, end_s)
    return [(attempt, window[0], window[1]) for attempt, window in sorted(by_attempt.items())]


def _round_vendor_cost(*, token_ledger: Path | None, start_s: int | None, end_s: int | None) -> str:
    if token_ledger is None or not token_ledger.is_file() or start_s is None or end_s is None:
        return "N/A"
    sums: dict[str, dict[str, int]] = {}
    claude_sub_by_model: dict[str, dict[str, int]] = {}
    for line in _read_lines_best_effort(token_ledger):
        if not line.strip():
            continue
        try:
            row: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        data = cast("dict[str, object]", row)
        if data.get("type") != "vendor":
            continue
        ts_raw = data.get("ts")
        if not isinstance(ts_raw, str):
            continue
        try:
            ts = int(datetime.fromisoformat(ts_raw).timestamp())
        except ValueError:
            continue
        if ts < start_s or ts > end_s:
            continue
        _add_round_vendor_cost_row(data=data, sums=sums, claude_sub_by_model=claude_sub_by_model)
    if not sums and not claude_sub_by_model:
        return "$0.00"
    argv = _round_vendor_cost_argv(sums=sums, claude_sub_by_model=claude_sub_by_model)
    try:
        out = report_tokens_cost.token_cost_from_args(argv)
    except Exception:  # pylint: disable=broad-except
        return "N/A"
    for line in out.splitlines():
        key, sep, value = line.partition("=")
        if sep and key == "TOTAL_COST" and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            return f"${value}"
    return "N/A"


@dataclass(frozen=True)
class _PhaseRound:
    number: int
    suggestions: int
    accepted: int
    oos_proposed: int
    oos_accepted: int
    reviewers: int
    seconds: int | None
    cost: str
    gantt_window: tuple[int, int] | None
    # Issue #4882: canonical scope-aware decomposition (None when round-meta predates the field or
    # has no classification data, e.g. design plan-review rounds).
    inscope: int | None = None
    oos_total: int | None = None
    nit_pruned: int = 0




def _completed_round_dirs(rounds_root: Path) -> list[Path]:
    if not rounds_root.is_dir() or not os.access(rounds_root, os.R_OK | os.X_OK):
        return []
    try:
        candidates = [p for p in rounds_root.iterdir() if p.is_dir() and (p / "round-meta.json").is_file()]
    except OSError:
        return []
    return sorted([p for p in candidates if _round_number(p) is not None], key=lambda p: _round_number(p) or 0)


def _review_tally_fileable_count(round_dir: Path) -> int | None:
    env = _read_simple_env(round_dir / "review-tally.env")
    if "OOS_ACCEPTED_COUNT" not in env:
        return None
    raw = env.get("OOS_ACCEPTED_COUNT", "")
    return _as_int(raw)


def _classification_vote_columns(header: list[str]) -> list[int]:
    indexes: list[int] = []
    for column in header:
        match = CLASSIFICATION_VOTE_RE.fullmatch(column)
        if match:
            indexes.append(int(match.group(1)))
    return sorted(indexes)


def _classification_row_fileable(*, cols: dict[str, str], header: list[str]) -> bool:
    vote_indexes = _classification_vote_columns(header)
    votes = [cols.get(f"v{index}_vote", "") for index in vote_indexes]
    severities = [cols.get(f"v{index}_severity", "") for index in vote_indexes]
    return voting.oos_fileable_from_votes(
        cols.get("voting_result", ""),
        yes_votes=votes,
        severities=severities,
    )


def _classification_row_is_security(*, round_dir: Path, item: str) -> bool:
    block = _extract_oos_block(round_dir=round_dir, oos_id=item)
    return bool(block and voting.is_security_block_text(block))


def _classification_oos_split(round_dir: Path) -> tuple[int, int, int] | None:
    path = round_dir / "findings-classification.tsv"
    lines = _read_lines_best_effort(path)
    if not lines:
        return None
    header = [col.strip() for col in lines[0].split("\t")]
    proposed = rejected = fileable = 0
    saw_oos = False
    for line in lines[1:]:
        raw_cols = [col.strip() for col in line.split("\t")]
        if len(raw_cols) < MIN_TSV_RESULT_COLS:
            continue
        cols = {name: raw_cols[idx] if idx < len(raw_cols) else "" for idx, name in enumerate(header)}
        item = cols.get("finding_id", raw_cols[0])
        result = cols.get("voting_result", raw_cols[2] if len(raw_cols) >= MIN_TSV_RESULT_COLS else "")
        if not result or _classification_row_in_scope(cols=cols, header=header):
            continue
        saw_oos = True
        if _classification_row_is_security(round_dir=round_dir, item=item):
            continue
        if result == "accepted":
            proposed += 1
            if _classification_row_fileable(cols=cols, header=header):
                fileable += 1
        else:
            rejected += 1
    return (proposed, rejected, fileable) if saw_oos else None


def _artifact_oos_split(round_dir: Path) -> tuple[int, int, int] | None:
    counts, source = _round_counts(round_dir)
    if not source:
        return None
    classification = _classification_oos_split(round_dir)
    env_fileable = _review_tally_fileable_count(round_dir)
    if classification is not None:
        proposed, rejected, class_fileable = classification
        return proposed, rejected, env_fileable if env_fileable is not None else class_fileable
    adjusted = _adjust_design_security_oos(round_dir=round_dir, counts=counts, source=source)
    proposed = adjusted[4]
    rejected = adjusted[5]
    return proposed, rejected, env_fileable if env_fileable is not None else 0


def _meta_oos_counts(*, round_dir: Path, tally: dict[str, object]) -> tuple[int, int, int]:
    artifact = _artifact_oos_split(round_dir)
    env_fileable = _review_tally_fileable_count(round_dir)
    if "OOS_PROPOSED_COUNT" in tally:
        proposed = _as_int(tally.get("OOS_PROPOSED_COUNT"))
        fileable = env_fileable if env_fileable is not None else _as_int(tally.get("OOS_ACCEPTED_COUNT"))
        rejected = _as_int(tally.get("OOS_REJECTED_COUNT"))
        return proposed, fileable, rejected
    if artifact is not None:
        proposed, rejected, artifact_fileable = artifact
        fileable = env_fileable if env_fileable is not None else artifact_fileable
        return proposed, fileable, rejected
    proposed = _as_int(tally.get("OOS_ACCEPTED_COUNT"))
    rejected = _as_int(tally.get("OOS_REJECTED_COUNT"))
    return proposed, env_fileable or 0, rejected


def _phase_round_from_meta(
    round_dir: Path,
    *,
    skill: str,
    timing_ledger: Path | None,
    token_ledger: Path | None,
) -> _PhaseRound:
    meta = _read_json_object(round_dir / "round-meta.json")
    tally = _nested_dict(data=meta, key="tally")
    summary = _nested_dict(data=meta, key="summary")
    counts = _nested_dict(data=summary, key="finding_counts")
    panel = _nested_dict(data=summary, key="panel")
    accepted = _as_int(tally.get("ACCEPTED_COUNT", counts.get("total_accepted")))
    rejected = _as_int(tally.get("REJECTED_COUNT", counts.get("total_rejected")))
    exonerated = _as_int(tally.get("EXONERATED_COUNT", counts.get("total_exonerated")))
    neutral = _as_int(tally.get("NEUTRAL_COUNT", counts.get("total_neutral")))
    oos_proposed, oos_fileable, _oos_rejected = _meta_oos_counts(round_dir=round_dir, tally=tally)
    reviewers = _as_int(panel.get("total_slot_count"))
    if reviewers == 0:
        reviewers = _as_int(panel.get("static_slot_count")) + _as_int(panel.get("dynamic_slot_count"))
    round_num = _round_number(round_dir) or 0
    table_window = _timing_round_windows(timing_ledger, skill=skill, round_num=round_num, skill_filtered=True)
    gantt_window = _timing_round_windows(timing_ledger, skill=skill, round_num=round_num, skill_filtered=False)
    seconds = None
    if table_window is not None and table_window[1] > table_window[0]:
        seconds = table_window[1] - table_window[0]
    cost = _round_vendor_cost(
        token_ledger=token_ledger,
        start_s=table_window[0] if table_window else None,
        end_s=table_window[1] if table_window else None,
    )
    canonical = _nested_dict(data=meta, key="tally_canonical")
    inscope: int | None = None
    oos_total: int | None = None
    if canonical:
        inscope = (
            _as_int(canonical.get("ACCEPTED_COUNT"))
            + _as_int(canonical.get("REJECTED_COUNT"))
            + _as_int(canonical.get("NEUTRAL_COUNT"))
            + _as_int(canonical.get("EXONERATED_COUNT"))
        )
        canonical_oos_proposed = _as_int(canonical.get("OOS_PROPOSED_COUNT", canonical.get("OOS_ACCEPTED_COUNT")))
        oos_total = canonical_oos_proposed + _as_int(canonical.get("OOS_REJECTED_COUNT"))
    return _PhaseRound(
        number=round_num,
        suggestions=accepted + rejected + exonerated + neutral,
        accepted=accepted,
        oos_proposed=oos_proposed,
        oos_accepted=oos_fileable,
        reviewers=reviewers,
        seconds=seconds,
        cost=cost,
        gantt_window=gantt_window if gantt_window is not None and gantt_window[1] > gantt_window[0] else None,
        inscope=inscope,
        oos_total=oos_total,
        nit_pruned=_as_int(meta.get("nit_pruned_count")),
    )


def _accepted_reviewer_basenames(findings_file: Path | None) -> list[str]:
    names: list[str] = []
    for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(findings_file)):
        if row.get("outcome") != "accepted":
            continue
        slots = row.get("reviewer_slots")
        if isinstance(slots, list):
            names.extend(Path(item).name for item in slots if isinstance(item, str) and item)
        else:
            reviewer = row.get("reviewer")
            if isinstance(reviewer, str) and reviewer:
                names.append(Path(reviewer).name)
    return names


def _top_reviewers(
    findings_file: Path | None,
    *,
    label_map: dict[str, str],
    top_n: int,
) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for basename in _accepted_reviewer_basenames(findings_file):
        label = label_map.get(basename) or _progress_derived_label(basename)
        counts[label] = counts.get(label, 0) + 1
    return list(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n])


def _classification_tsv_available(round_dirs: list[Path]) -> bool:
    return any(_tsv_has_data_rows(round_dir / "findings-classification.tsv") for round_dir in round_dirs)


def _human_attribution_labels(round_dirs: list[Path], *, reviewer_column: str) -> list[str]:
    if reviewer_column != "finding_reviewers":
        return []
    labels: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        clean = label.strip()
        if clean and clean not in seen:
            labels.append(clean)
            seen.add(clean)

    for round_dir in round_dirs:
        for label_map in (
            round_dir / "plan-review-prune-label-map.tsv",
            round_dir.parent.parent / "plan-review-prune-label-map.tsv",
        ):
            if not label_map.is_file():
                continue
            for line in _read_lines_best_effort(label_map):
                parts = line.split("\t")
                if len(parts) >= LABEL_MAP_MIN_COLS:
                    add(parts[1])
        for manifest in (round_dir / "panel-manifest.ndjson", round_dir / "plan-review-slots.ndjson"):
            for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(manifest)):
                slot = row.get("slot")
                if isinstance(slot, str):
                    add(plan_review_round._slot_human_label(slot))  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        lines = _read_lines_best_effort(round_dir / "findings-classification.tsv")
        if not lines:
            continue
        header = [col.strip() for col in lines[0].split("\t")]
        if reviewer_column not in header:
            continue
        reviewer_idx = header.index(reviewer_column)
        for line in lines[1:]:
            cols = line.split("\t")
            if len(cols) <= reviewer_idx:
                continue
            voting.grow_attribution_labels(labels, seen, cols[reviewer_idx])
    return labels


def _classification_row_in_scope(*, cols: dict[str, str], header: list[str]) -> bool:
    if "scope" in header:
        return cols.get("scope", "").strip() == "in_scope"
    return not cols.get("finding_id", "").strip().startswith("OOS_")


def _accepted_reviewers_from_classification(
    classification: Path,
    *,
    round_dirs: list[Path],
    label_map: dict[str, str] | None = None,
    active_bonus: float = 0.0,
) -> list[tuple[str, float]]:
    """Weighted in-scope accepted-finding reviewer attribution from classification TSV."""
    lines = _read_lines_best_effort(classification)
    if not lines:
        return []
    header = [col.strip() for col in lines[0].split("\t")]
    reviewer_column = "finding_reviewers" if "finding_reviewers" in header else "reviewer_slots" if "reviewer_slots" in header else ""
    if not reviewer_column or "voting_result" not in header:
        return []
    labels = _human_attribution_labels(round_dirs, reviewer_column=reviewer_column)
    rows: list[tuple[str, float]] = []
    for line in lines[1:]:
        raw_cols = line.split("\t")
        cols = {name: raw_cols[idx].strip() if idx < len(raw_cols) else "" for idx, name in enumerate(header)}
        if cols.get("voting_result") != "accepted" or not _classification_row_in_scope(cols=cols, header=header):
            continue
        reviewer_cell = cols.get(reviewer_column, "")
        raw_reviewers = voting.raw_sole_finder_attribution(
            reviewer_cell,
            column=reviewer_column,
            corpus_labels=labels,
        )
        reviewers = voting.split_classification_attribution(
            reviewer_cell,
            column=reviewer_column,
            labels=labels if reviewer_column == "finding_reviewers" else None,
        )
        if not reviewers and reviewer_column == "finding_reviewers":
            cell = reviewer_cell.strip()
            if cell:
                reviewers = [part.strip() for part in cell.split(",") if part.strip()]
        points = float(voting.accepted_points_from_classification_row(cols=cols, header=header))
        if active_bonus > 0 and len(raw_reviewers) == 1:
            points += active_bonus
        for reviewer in reviewers:
            label = reviewer
            if reviewer_column == "reviewer_slots":
                maps = label_map or {}
                label = maps.get(reviewer) or _progress_derived_label(reviewer)
            rows.append((label, points))
    return rows


def _top_reviewers_from_classification(
    round_dirs: list[Path],
    *,
    top_n: int,
    label_map: dict[str, str] | None = None,
) -> list[tuple[str, float]]:
    """Whole-run Top-reviewers aggregated from per-round findings-classification.tsv."""
    counts: dict[str, float] = {}
    active_bonus = voting.unique_finder_bonus_from_env()
    for round_dir in round_dirs:
        for reviewer, points in _accepted_reviewers_from_classification(
            round_dir / "findings-classification.tsv",
            round_dirs=round_dirs,
            label_map=label_map,
            active_bonus=active_bonus,
        ):
            counts[reviewer] = counts.get(reviewer, 0) + points
    return list(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n])


def _executing_tool_by_norm_basename(collector_env: Path) -> dict[str, str]:
    """Map normalized reviewer basename -> executing tool from ``collector-results.env``.

    ``collect_results.derive_tool`` records the tool that actually produced each
    reviewer output (``TOOL=``); on vendor fallback this differs from the slot's
    nominal vendor. Keyed by ``voting.normalize_reviewer_basename`` so manifest
    ``output`` paths line up with collector ``REVIEWER_FILE`` entries. ``unknown``
    provenance is dropped so it never displaces a real tool.
    """
    if not collector_env.is_file() or collector_env.is_symlink():
        return {}
    result: dict[str, str] = {}
    for record in collect_results.parse_collector_records("\n".join(_read_lines_best_effort(collector_env))):
        reviewer_file = record.get("REVIEWER_FILE", "")
        tool = record.get("TOOL", "")
        if reviewer_file and tool and tool != "unknown":
            result[voting.normalize_reviewer_basename(reviewer_file)] = tool
    return result


def _round_collector_tool_by_norm_basename(round_dir: Path) -> dict[str, str]:
    for collector_env in _collector_env_paths_for_round(round_dir):
        try:
            if not collector_env.is_file() or collector_env.is_symlink() or collector_env.stat().st_size <= 0:
                continue
        except OSError:
            continue
        return _executing_tool_by_norm_basename(collector_env)
    return {}


def _manifest_fallback_base_label(*, slot: str, tool: str) -> str:
    human_label = plan_review_round._slot_human_label(slot)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
    if human_label != slot:
        return human_label
    return f"{tool}/{slot}"


def _fallback_reconciled_manifest_label(
    *,
    slot: str,
    nominal_tool: str,
    executing_tool: str,
) -> tuple[str, str] | None:
    tool = executing_tool.strip().lower()
    if not tool or tool == "unknown":
        return None
    nominal = nominal_tool.strip().lower()
    base = _manifest_fallback_base_label(slot=slot, tool=nominal)
    if nominal and nominal != tool:
        return base, f"{base} (via {tool.title()})"
    return base, base


def _fallback_label_remap(round_dirs: list[Path]) -> dict[str, str]:
    """Map slot human label -> reconciled ``(via <Tool>)`` label for fallback slots.

    Reconciles the panel-assigned slot label with the executing tool recorded in
    ``collector-results.env`` so Top-reviewers attribution does not credit a vendor
    whose slots actually fell back to another tool (issue #5838). Only slots whose
    executing tool differs from their nominal vendor produce an entry.
    """
    remap: dict[str, str] = {}
    for round_dir in round_dirs:
        tool_by_norm = _round_collector_tool_by_norm_basename(round_dir)
        if not tool_by_norm:
            continue
        manifests = [round_dir / "panel-manifest.ndjson"]
        if "plan-review" in round_dir.parts:
            manifests.append(round_dir.parent.parent / "plan-review-slots.ndjson")
        for manifest in manifests:
            for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(manifest)):
                slot = row.get("slot")
                nominal_tool = row.get("tool")
                output = row.get("output")
                if not (
                    isinstance(slot, str)
                    and slot
                    and isinstance(nominal_tool, str)
                    and nominal_tool
                    and isinstance(output, str)
                    and output
                ):
                    continue
                tool = tool_by_norm.get(voting.normalize_reviewer_basename(output), "")
                if not tool:
                    continue
                labels = _fallback_reconciled_manifest_label(
                    slot=slot,
                    nominal_tool=nominal_tool,
                    executing_tool=tool,
                )
                if labels is None:
                    continue
                base, reconciled = labels
                if reconciled != base:
                    remap[base] = reconciled
    return remap


def _apply_fallback_remap(
    top_reviewers: Sequence[tuple[str, float]], round_dirs: list[Path]
) -> list[tuple[str, float]]:
    """Relabel Top-reviewers entries for vendor-fallback slots (issue #5838).

    Slots whose executing tool differs from their nominal vendor are annotated
    ``(via <Tool>)``; all other labels pass through unchanged.
    """
    remap = _fallback_label_remap(round_dirs)
    return [(remap.get(label, label), score) for label, score in top_reviewers]


def _collector_substantive_failure_records(text: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    parsed = collect_results.parse_collector_records(text)
    if not parsed or not any(record.get("STATUS") for record in parsed):
        for block in re.split(r"\n\s*\n", text):
            current: dict[str, str] = {}
            for line in block.splitlines():
                key, sep, value = line.partition("=")
                if sep:
                    current[key] = value
            if current:
                parsed = [*parsed, current]
    for record in parsed:
        status = record.get("STATUS", "")
        if status and status not in {"OK", "cap_hit"}:
            records.append((record.get("TOOL", ""), Path(record.get("REVIEWER_FILE", "")).name))
    return records


def _progress_normalize_output_base(base: str) -> str:
    base = Path(base).name
    stem, ext = (base[:-4], ".txt") if base.endswith(".txt") else (base, "")
    while True:
        new = re.sub(r"-(?:phase2|phase3|retry)$", "", stem)
        if new == stem:
            break
        stem = new
    return stem + ext


def _is_chart_vendor_fallback_output(base: str) -> bool:
    basename = Path(base).name
    if not basename.endswith(".txt"):
        return False
    stem = basename.removesuffix(".txt")
    return stem.endswith(("-phase2", "-phase3"))


def _manifest_lookup_by_slot_tool(manifest: Path) -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(manifest)):
        slot = row.get("slot")
        tool = row.get("tool")
        output = row.get("output")
        if isinstance(slot, str) and isinstance(tool, str) and isinstance(output, str):
            mapping[(slot, tool)] = _progress_normalize_output_base(output)
    return mapping


def _dropped_progress_base(*, slot: str, tool: str, manifest_map: dict[tuple[str, str], str]) -> str:
    mapped = manifest_map.get((slot, tool))
    if mapped:
        return mapped
    if slot.startswith("dyn-"):
        archetype = slot
        if tool == "codex" and archetype.endswith("-codex"):
            archetype = archetype.removesuffix("-codex")
        return f"dyn-{archetype.removeprefix('dyn-')}{'-codex' if tool == 'codex' else ''}-output.txt"
    if slot == "generalist" and tool == "codex":
        return "codex-generalist-output.txt"
    if tool in {"codex", "cursor"} and slot:
        return f"{tool}-specialist-{slot}-output.txt"
    return f"slot:{slot}:{tool}"


def _dropped_slot_failure_records(round_dir: Path) -> list[tuple[str, str, str]]:
    manifest_map = _manifest_lookup_by_slot_tool(round_dir / "panel-manifest.ndjson")
    files = sorted(round_dir.glob("*.dropped-slots"))
    files.sort(key=lambda path: (not path.name.endswith(".output-files.dropped-slots"), path.name))
    seen: set[str] = set()
    records: list[tuple[str, str, str]] = []
    for dropped in files:
        for line in _read_lines_best_effort(dropped):
            slot, tool, reason, *_rest = [*line.split("\t"), "", "", ""]
            if not slot or tool not in {"codex", "cursor"}:
                continue
            if reason == "straggler-dropped" and not slot.startswith("dyn-"):
                continue
            base = _progress_normalize_output_base(_dropped_progress_base(slot=slot, tool=tool, manifest_map=manifest_map))
            key = base if base.endswith("-output.txt") else f"{slot}:{tool}"
            if key in seen:
                continue
            seen.add(key)
            records.append((tool, slot, base))
    return records


def _collector_env_paths_for_round(round_dir: Path) -> list[Path]:
    paths = [
        round_dir / "collector-results.env",
        round_dir.parent / "collector-results.env",
    ]
    if "plan-review" in round_dir.parts:
        paths.append(round_dir.parent.parent / "collector-results.env")
    return paths


def _collector_seen_bases(text: str) -> set[str]:
    seen: set[str] = set()
    for record in collect_results.parse_collector_records(text):
        reviewer_file = record.get("REVIEWER_FILE", "")
        if reviewer_file:
            seen.add(_progress_normalize_output_base(Path(reviewer_file).name))
    return seen


def _failed_reviewers(round_dirs: list[Path], *, label_map: dict[str, str]) -> tuple[int, list[tuple[str, int]]]:
    counts: dict[str, int] = {}
    total = 0
    for round_dir in round_dirs:
        collector_text = ""
        for path in _collector_env_paths_for_round(round_dir):
            if path.is_file():
                collector_text = "\n".join(_read_lines_best_effort(path))
                break
        seen_bases = _collector_seen_bases(collector_text)
        collector_records = _collector_substantive_failure_records(collector_text)
        if not collector_records:
            collector = str(_read_json_object(round_dir / "round-meta.json").get("collector") or "")
            collector_records = _collector_substantive_failure_records(collector)
        for tool, basename in collector_records:
            normalized = _progress_normalize_output_base(basename)
            seen_bases.add(normalized)
            label = label_map.get(normalized) or label_map.get(basename)
            if not label:
                label = _progress_derived_label(normalized)
                if tool and "/" in label:
                    label = tool + label[label.index("/") :]
            counts[label] = counts.get(label, 0) + 1
            total += 1
        for tool, slot, basename in _dropped_slot_failure_records(round_dir):
            normalized = _progress_normalize_output_base(basename)
            if normalized in seen_bases:
                continue
            label = label_map.get(normalized)
            if not label:
                label = f"{tool}/{slot}" if slot.startswith("dyn-") else _progress_derived_label(normalized)
            counts[label] = counts.get(label, 0) + 1
            total += 1
    return total, sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _render_phase_gantt(
    round_dirs: list[Path],
    *,
    timing_ledger: Path | None,
    rounds: list[_PhaseRound],
    label_map: dict[str, str],
) -> str:
    if timing_ledger is None or not timing_ledger.is_file():
        return ""
    sections: list[str] = []
    round_by_num = {row.number: row for row in rounds}
    for round_dir in round_dirs:
        round_num = _round_number(round_dir) or 0
        phase_round = round_by_num.get(round_num)
        if phase_round is None or phase_round.gantt_window is None:
            continue
        # Issue #5504: when a stall recovery reruns the same round number in one session, the
        # ledger holds multiple round rows for it. Render one Gantt section per attempt (each
        # with its own tight window) instead of merging both into phase_round.gantt_window, which
        # spans the whole session and scatters each attempt's probes across the chart.
        attempt_windows = _timing_round_attempt_windows(timing_ledger, round_num=round_num)
        if not attempt_windows:
            attempt_windows = [(1, phase_round.gantt_window[0], phase_round.gantt_window[1])]
        multi = len(attempt_windows) > 1
        for attempt, start_s, end_s in attempt_windows:
            suffix = f" (attempt {attempt})" if multi else ""
            sections.append(f"### Round {round_num} reviewer timing{suffix}\n")
            rows = _progress_vendor_rows(
                timing_ledger=timing_ledger,
                window_start_s=start_s,
                window_end_s=end_s,
                label_map=label_map,
                skip_ci=True,
                require_complete_status=False,
                cap=None,
            )
            chart = render_gantt(window_start_s=start_s, window_end_s=end_s, rows=rows) if rows else ""
            if chart:
                span = end_s - start_s
                sections.append(
                    "```\n"
                    f"Round {round_num} reviewer timing{suffix}  ·  window 0:00-{format_mss(span)} ({span}s)\n"
                    f"{chart}\n"
                    "```\n"
                )
            else:
                sections.append("No reviewer timing tasks overlapped this round.\n")
    return "\n".join(sections).strip("\n") + ("\n\n" if sections else "")


def render_phase_detail(
    *, rounds_root: Path,
    skill: str,
    timing_ledger: Path | None = None,
    token_ledger: Path | None = None,
    findings_file: Path | None = None,
    top_n: int = 7,
    gantt_enabled: bool = True,
) -> str:
    if skill not in {"implement", "design"}:
        raise ValueError("skill must be implement or design")
    if not rounds_root.is_dir() or not os.access(rounds_root, os.R_OK | os.X_OK):
        return ""
    top_n = top_n if top_n > 0 else 7
    round_dirs = _completed_round_dirs(rounds_root)
    if not round_dirs:
        return "## Review Phase Detail\n\nNo review rounds completed.\n"
    label_map = _progress_label_map(round_dirs)
    phase_rounds = [
        _phase_round_from_meta(
            round_dir,
            skill=skill,
            timing_ledger=timing_ledger if timing_ledger is not None and timing_ledger.is_file() else None,
            token_ledger=token_ledger if token_ledger is not None and token_ledger.is_file() else None,
        )
        for round_dir in round_dirs
    ]
    total_time = sum(row.seconds or 0 for row in phase_rounds)
    any_time = any(row.seconds is not None for row in phase_rounds)
    costs = [float(row.cost[1:]) for row in phase_rounds if row.cost.startswith("$")]
    if _classification_tsv_available(round_dirs):
        top_reviewers = _top_reviewers_from_classification(round_dirs, top_n=top_n, label_map=label_map)
    else:
        top_reviewers = _top_reviewers(findings_file, label_map=label_map, top_n=top_n)
    top_reviewers = _apply_fallback_remap(top_reviewers, round_dirs)
    fail_total, failures = _failed_reviewers(round_dirs, label_map=label_map)
    lines = [
        "## Review Phase Detail",
        "",
        "| Round | Suggestions | Accepted | OOS proposed | OOS fileable | Time | Cost | Reviewers |",
        "|--:|--:|--:|--:|--:|:--|--:|--:|",
    ]
    lines.extend(
        (
            f"| {row.number} | {row.suggestions} | {row.accepted} | {row.oos_proposed} | "
            f"{row.oos_accepted} | {_fmt_hms(row.seconds)} | {row.cost} | {row.reviewers} |"
        )
        for row in phase_rounds
    )
    total_cost = f"${sum(costs):.2f}" if costs else "N/A"
    lines.append(
        f"| **Total (round-sum)** | **{sum(row.suggestions for row in phase_rounds)}** | "
        f"**{sum(row.accepted for row in phase_rounds)}** | "
        f"**{sum(row.oos_proposed for row in phase_rounds)}** | "
        f"**{sum(row.oos_accepted for row in phase_rounds)}** | "
        f"**{_fmt_hms(total_time if any_time else None)}** | **{total_cost}** | "
        f"**{sum(row.reviewers for row in phase_rounds)}** |"
    )
    lines.append("")
    lines.append(
        "_The Total (round-sum) row adds up the per-round Suggestions and Accepted: when the "
        "review loop re-raises the same finding across rounds, that finding is counted once per "
        "round, so the round-sum can exceed the number of distinct findings. Top reviewers counts "
        "per-round accepted-point scores the same way._"
    )
    lines.append("")
    # Issue #4882: decompose the raw per-finding "Suggestions" count into the canonical scope-aware
    # split so "18 suggestions" reconciles with the headline "X/Y accepted" (in-scope only).
    decomp_segments: list[str] = []
    for row in phase_rounds:
        if row.inscope is None:
            continue
        oos = row.oos_total or 0
        seg = (
            f"round {row.number}: {row.inscope + oos} finding(s) = {row.inscope} in-scope "
            f"(voted; matches the headline X/Y accepted) + {oos} out-of-scope"
        )
        if row.oos_proposed or row.oos_accepted:
            seg += f" ({row.oos_proposed} OOS proposed, {row.oos_accepted} OOS fileable)"
        if row.nit_pruned:
            seg += f" (incl. {row.nit_pruned} nit-pruned)"
        decomp_segments.append(seg)
    if decomp_segments:
        lines.append(
            "_Finding decomposition (canonical, scope-aware): "
            + "; ".join(decomp_segments)
            + ". The Suggestions and OOS columns above count findings by finding id (raw per-finding) "
            "and can disagree with this scope-aware split when findings are reclassified out-of-scope "
            "after voting; round-meta.json records both raw (`tally`) and canonical (`tally_canonical`) "
            "counts so downstream joins do not contradict._"
        )
        lines.append("")
    if gantt_enabled:
        gantt = _render_phase_gantt(
            round_dirs,
            timing_ledger=timing_ledger if timing_ledger is not None and timing_ledger.is_file() else None,
            rounds=phase_rounds,
            label_map=label_map,
        )
        if gantt:
            lines.extend(gantt.rstrip("\n").splitlines())
            lines.append("")
    lines.append("**Top reviewers** (by per-round accepted-point score, whole run):")
    if top_reviewers:
        for index, (label, count) in enumerate(top_reviewers, start=1):
            lines.append(f"{index}. {label}: {voting.format_score(count)}")
    else:
        lines.append("- (no accepted-point score attributed to a reviewer slot)")
    lines.append("")
    lines.append(f"**Reviewer slot failures**: {fail_total}")
    for label, count in failures:
        lines.append(f"- {label}: {count}")
    return "\n".join(lines) + "\n"


def _render_phase_detail_best_effort(
    rounds_root: Path,
    *,
    skill: str,
    timing_ledger: Path | None = None,
    token_ledger: Path | None = None,
    findings_file: Path | None = None,
    top_n: int = 7,
    gantt_enabled: bool = True,
) -> str:
    # In-process render under a 15s wall-clock guard for final-summary and wrapper callers;
    # explicit CLI rendering (render_phase_detail_main) calls render_phase_detail unbounded.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            render_phase_detail,
            rounds_root=rounds_root,
            skill=skill,
            timing_ledger=timing_ledger,
            token_ledger=token_ledger,
            findings_file=findings_file,
            top_n=top_n,
            gantt_enabled=gantt_enabled,
        )
        return future.result(timeout=RENDER_PHASE_DETAIL_TIMEOUT_SECONDS)
    except Exception:  # pylint: disable=broad-except
        return ""
    finally:
        executor.shutdown(wait=False)


def _progress_label_map_from_manifests(manifest_paths: list[Path]) -> dict[str, str]:
    label_map: dict[str, str] = {}
    for manifest in manifest_paths:
        try:
            lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for row in logging_util.iter_jsonl_dicts(lines):
            output = row.get("output")
            tool = row.get("tool")
            slot = row.get("slot")
            if not all(isinstance(value, str) and value for value in (output, tool, slot)):
                continue
            output_s = cast("str", output)
            tool_s = cast("str", tool)
            slot_s = cast("str", slot)
            label_map[Path(output_s).name] = f"{tool_s}/{slot_s}"
    return label_map


def _progress_label_map(round_dirs: list[Path]) -> dict[str, str]:
    return _progress_label_map_from_manifests([round_dir / "panel-manifest.ndjson" for round_dir in round_dirs])


def _progress_core_from_output(output: str) -> str:
    core = Path(output).name
    core = core.removesuffix(".txt")
    for suffix in ("-output-ns-retry", "-output", "-ns-retry"):
        if core.endswith(suffix):
            core = core[: -len(suffix)]
            break
    return core.lower()


def _progress_derived_label(output: str) -> str:
    core = _progress_core_from_output(output)
    vendor_match = r"cursor|codex|claude_sub|claude"
    if core == "aggregator":
        return "aggregator"
    if core == "scout-plan-manifest" or core.startswith("scout-plan-manifest."):
        return "scout"
    if core in {"codex", "cursor", "claude", "claude_sub"}:
        return core
    match = re.match(rf"^({vendor_match})-specialist-(.+)$", core)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    match = re.match(rf"^({vendor_match})-generalist$", core)
    if match:
        return f"{match.group(1)}/generalist"
    if core.startswith("dyn-"):
        return f"dynamic/{core[4:]}"
    match = re.match(rf"^({vendor_match})-(.*)$", core)
    if match:
        arch = match.group(2) or "panel"
        return f"{match.group(1)}/{arch}"
    if core in {"", "panel"}:
        return "panel/panel"
    return f"unknown/{core}"


def _chart_fallback_label_for_vendor(*, label: str, vendor: str) -> str:
    executing_tool = vendor.strip().lower()
    if executing_tool not in {"codex", "cursor", "claude", "claude_sub"}:
        return label
    nominal_tool, sep, slot = label.partition("/")
    if not sep or nominal_tool.strip().lower() == executing_tool:
        return label
    if nominal_tool.strip().lower() not in {"codex", "cursor", "claude", "claude_sub"}:
        return label
    return _manifest_fallback_base_label(slot=slot, tool=executing_tool)


def _derive_progress_label(
    *, output: str,
    vendor: str = "",
    kind: str = "",
    label_map: dict[str, str] | None = None,
) -> str:
    kind_labels = {
        "codex-review-fix": "codex/apply",
        "codex-plan-autofix": "codex/apply",
        "cursor-review-fix": "cursor/apply",
        "cursor-plan-autofix": "cursor/apply",
        "gate-b-apply": "gate-b/apply",
        "voter-dispatch-prep": "voter-dispatch-prep",
        "reviewer-collect": "reviewer-collect",
    }
    if kind in kind_labels:
        return kind_labels[kind]
    raw_base = Path(output).name if output and output != "-" else ""
    labels = label_map or {}
    if raw_base and raw_base in labels:
        return labels[raw_base]
    is_chart_fallback = _is_chart_vendor_fallback_output(raw_base)
    normalized_base = _progress_normalize_output_base(raw_base) if raw_base else ""
    resolved = labels.get(normalized_base, "") if normalized_base else ""
    if not resolved:
        derived_base = normalized_base if is_chart_fallback and normalized_base else raw_base
        resolved = _progress_derived_label(derived_base) if derived_base else ""
        if resolved in {"codex", "cursor", "claude", "claude_sub"} and kind and kind != "-":
            resolved = f"{resolved}/{kind}"
    if is_chart_fallback and resolved and resolved != "unknown/-":
        resolved = _chart_fallback_label_for_vendor(label=resolved, vendor=vendor)
        return f"{resolved} (via fallback)"
    derived = resolved
    if derived in {"codex", "cursor", "claude", "claude_sub"} and kind and kind != "-":
        return f"{derived}/{kind}"
    if derived and derived != "unknown/-":
        return derived
    if vendor and kind:
        return f"{vendor}/{kind}"
    if vendor:
        return vendor
    return kind or "unknown"


def _is_ci_gantt_row(*, kind: str, output: str) -> bool:
    kind_l = (kind or "").lower()
    bn = Path(output).name.lower() if output else ""
    if kind_l in {"codex-ci", "cursor-ci", "claude-ci", "codex-ci-fix", "cursor-ci-fix", "claude-ci-fix"}:
        return True
    if kind_l.endswith(("-ci", "-ci-fix", "-ci-test")):
        return True
    if bn == "ci.out" or bn.endswith("-ci.out") or re.fullmatch(r"ci-fix-.*\.out", bn):
        return True
    return bn in {"claude.out", "codex.out", "cursor.out"}


# Coder fix-application task kinds, rendered as `*/apply` lanes. These rows
# start after the reviewer, aggregator, and voter slots, so a start-sorted
# truncation at PROGRESS_GANTT_ROW_CAP drops them; the cap helper reserves
# them so the chart always shows the coder applying review fixes (issue #5264).
_CODER_APPLY_TASK_KINDS: frozenset[str] = frozenset({
    "codex-review-fix", "cursor-review-fix", "claude-review-fix",
    "codex-plan-autofix", "cursor-plan-autofix", "gate-b-apply",
})


def _cap_gantt_rows_reserving_apply(
    rows: list[tuple[int, int, str, bool, bool]],
    *,
    cap: int,
) -> list[tuple[int, int, str, bool, bool]]:
    """Cap rows to `cap` without dropping reserved reviewer-timing lanes.

    Reviewer, aggregator, and voter rows all start before the coder applies
    accepted fixes, so truncating the start-sorted list at `cap` silently
    drops the late-starting `*/apply` lane (issue #5264). Keep every apply
    row. Also reserve phase2/phase3 vendor-fallback rows, because they can
    start after a saturated primary panel and otherwise disappear from the
    chart. Fill the remaining budget with the earliest non-reserved rows, and
    return the kept rows in chronological order. `rows` must already be sorted
    by (start_s, end_s, label).
    """
    if len(rows) <= cap:
        return rows
    reserved_rows = [row for row in rows if row[3] or row[4]]
    non_reserved = [row for row in rows if not row[3] and not row[4]]
    budget = max(0, cap - len(reserved_rows))
    kept = non_reserved[:budget] + reserved_rows
    kept.sort(key=lambda row: (row[0], row[1], row[2]))
    return kept


def _progress_vendor_rows(
    *, timing_ledger: Path,
    window_start_s: int,
    window_end_s: int,
    label_map: dict[str, str] | None = None,
    skip_ci: bool = False,
    require_complete_status: bool = True,
    cap: int | None = PROGRESS_GANTT_ROW_CAP,
) -> list[GanttRow]:
    if window_end_s <= window_start_s:
        return []
    try:
        lines = timing_ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[tuple[int, int, str, bool, bool]] = []
    for line in lines:
        cols = line.split("\t")
        if len(cols) < TIMING_VENDOR_MIN_COLS or cols[0] != "v1" or cols[1] != "vendor":
            continue
        status = cols[TIMING_VENDOR_STATUS_COL]
        if require_complete_status and status not in {"complete", "OK"}:
            continue
        try:
            start_s = int(cols[TIMING_VENDOR_START_COL])
            end_s = int(cols[TIMING_VENDOR_END_COL])
        except ValueError:
            continue
        if end_s <= window_start_s or start_s >= window_end_s:
            continue
        clamped_start = max(start_s, window_start_s)
        clamped_end = min(end_s, window_end_s)
        if clamped_end <= clamped_start:
            continue
        output = cols[TIMING_VENDOR_OUTPUT_COL] if len(cols) > TIMING_VENDOR_OUTPUT_COL else ""
        kind = cols[TIMING_VENDOR_KIND_COL]
        if skip_ci and _is_ci_gantt_row(kind=kind, output=output):
            continue
        label = _derive_progress_label(output=output, vendor=cols[TIMING_VENDOR_VENDOR_COL], kind=kind, label_map=label_map)
        rows.append((
            clamped_start,
            clamped_end,
            label,
            kind in _CODER_APPLY_TASK_KINDS,
            _is_chart_vendor_fallback_output(output),
        ))
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    capped = rows if cap is None else _cap_gantt_rows_reserving_apply(rows, cap=cap)
    return [GanttRow(label, start_s, end_s) for start_s, end_s, label, _, _ in capped]


def _parse_tally_md(path: Path) -> tuple[int, int, int, int, int, int]:
    accepted = rejected = neutral = exonerated = oos_accepted = oos_rejected = 0
    in_findings = False
    for line in _read_lines_best_effort(path):
        if line.startswith("## Findings"):
            in_findings = True
            continue
        if in_findings and line.startswith("## "):
            in_findings = False
        if not in_findings or "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < MIN_MARKDOWN_TABLE_PARTS:
            continue
        item = parts[1] if len(parts) > 1 else ""
        result = parts[-2] if len(parts) >= MD_RESULT_COL_FROM_END else ""
        if not result or set(result) <= {"-"}:
            result = parts[-3] if len(parts) >= MD_FALLBACK_RESULT_COL_FROM_END else ""
        invalid_item = not item or item == "Item" or set(item) <= {"-"}
        invalid_result = not result or result == "Result" or set(result) <= {"-"}
        if invalid_item or invalid_result:
            continue
        if re.fullmatch(r"FINDING_[0-9A-Za-z_]+", item):
            if result == "accepted":
                accepted += 1
            elif result == "rejected":
                rejected += 1
            elif result == "neutral":
                neutral += 1
            elif result == "exonerated":
                exonerated += 1
        elif re.fullmatch(r"OOS_[0-9A-Za-z_]+", item):
            if result == "accepted":
                oos_accepted += 1
            else:
                oos_rejected += 1
    return accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected


def _parse_classification_tsv(path: Path) -> tuple[int, int, int, int, int, int]:
    accepted = rejected = neutral = exonerated = oos_accepted = oos_rejected = 0
    lines = _read_lines_best_effort(path)
    if not lines:
        return accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected
    header = [col.strip() for col in lines[0].split("\t")]
    for line in lines[1:]:
        raw_cols = [col.strip() for col in line.split("\t")]
        if len(raw_cols) < MIN_TSV_RESULT_COLS:
            continue
        cols = {name: raw_cols[idx] if idx < len(raw_cols) else "" for idx, name in enumerate(header)}
        item = cols.get("finding_id", raw_cols[0])
        result = cols.get("voting_result", raw_cols[2] if len(raw_cols) >= MIN_TSV_RESULT_COLS else "")
        in_scope = _classification_row_in_scope(cols=cols, header=header)
        if in_scope and re.fullmatch(r"FINDING_[0-9A-Za-z_]+", item):
            if result == "accepted":
                accepted += 1
            elif result == "rejected":
                rejected += 1
            elif result == "neutral":
                neutral += 1
            elif result == "exonerated":
                exonerated += 1
        elif result:
            if result == "accepted":
                oos_accepted += 1
            else:
                oos_rejected += 1
    return accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected

def _tsv_has_data_rows(path: Path) -> bool:
    return any(line.strip() for line in _read_lines_best_effort(path)[1:])


def _round_counts(round_dir: Path) -> tuple[tuple[int, int, int, int, int, int], str]:
    counts: tuple[int, int, int, int, int, int] | None = None
    source = ""
    tally = round_dir / "voting-tally.md"
    classification = round_dir / "findings-classification.tsv"
    md_counts = (0, 0, 0, 0, 0, 0)
    if tally.is_file():
        md_counts = _parse_tally_md(tally)
        counts = md_counts
        source = "md"
    if classification.is_file():
        tsv_counts = _parse_classification_tsv(classification)
        if counts is None or (md_counts == (0, 0, 0, 0, 0, 0) and _tsv_has_data_rows(classification)):
            counts = tsv_counts
            source = "tsv"
    return counts or (0, 0, 0, 0, 0, 0), source


def _oos_result_rows(*, round_dir: Path, source: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if source == "md":
        in_findings = False
        for line in _read_lines_best_effort(round_dir / "voting-tally.md"):
            if line.startswith("## Findings"):
                in_findings = True
                continue
            if in_findings and line.startswith("## "):
                in_findings = False
            if not in_findings or "|" not in line:
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < MIN_MARKDOWN_TABLE_PARTS:
                continue
            item = parts[1]
            result = parts[-2] if parts[-2] and set(parts[-2]) != {"-"} else parts[-3]
            if re.fullmatch(r"OOS_[0-9A-Za-z_]+", item) and result:
                rows.append((item, result))
    elif source == "tsv":
        for line in _read_lines_best_effort(round_dir / "findings-classification.tsv")[1:]:
            cols = [col.strip() for col in line.split("\t")]
            if len(cols) >= MIN_TSV_RESULT_COLS and re.fullmatch(r"OOS_[0-9A-Za-z_]+", cols[0]) and cols[2]:
                rows.append((cols[0], cols[2]))
    return rows


def _extract_oos_block(*, round_dir: Path, oos_id: str) -> str:
    for name in ("findings-oos.md", "findings.md", "oos.md", "findings-in-scope.md"):
        path = round_dir / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for parsed_block in parse_blocks(text, boundary="level-three-heading"):
            if parsed_block.item_id == oos_id:
                return parsed_block.block
    return ""


def _adjust_design_security_oos(
    *, round_dir: Path,
    counts: tuple[int, int, int, int, int, int],
    source: str,
) -> tuple[int, int, int, int, int, int]:
    accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected = counts
    for oos_id, result in _oos_result_rows(round_dir=round_dir, source=source):
        block = _extract_oos_block(round_dir=round_dir, oos_id=oos_id)
        if not block:
            continue
        is_security = is_security_block_text(block)
        if not is_security:
            continue
        if result == "accepted":
            oos_accepted = max(0, oos_accepted - 1)
        else:
            oos_rejected = max(0, oos_rejected - 1)
    return accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected


def _materialize_design_panel_manifest(round_dir: Path) -> int:
    slots_src = round_dir / "plan-review-slots.ndjson"
    if not slots_src.is_file():
        slots_src = round_dir.parent.parent / "plan-review-slots.ndjson"
    panel_tmp = round_dir / "panel-manifest.ndjson.tmp"
    count = 0
    try:
        with panel_tmp.open("w", encoding="utf-8") as dst:
            for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(slots_src)):
                slot = str(row.get("slot") or "")
                tool = str(row.get("tool") or "")
                output = str(row.get("output") or "")
                if not (slot or tool or output):
                    continue
                out_row = {"slot": slot, "tool": tool, "output": output}
                for key in ("vendor", "resolved_model", "model_role", "focus_area"):
                    if row.get(key):
                        out_row[key] = str(row.get(key))
                dst.write(json.dumps(out_row, separators=(",", ":")) + "\n")
                count += 1
        panel_tmp.replace(round_dir / "panel-manifest.ndjson")
    except OSError:
        with contextlib.suppress(OSError):
            panel_tmp.unlink()
        return 0
    return count


def _count_panel_manifest(path: Path) -> int:
    count = 0
    for row in logging_util.iter_jsonl_dicts(_read_lines_best_effort(path)):
        if any(row.get(k) for k in ("slot", "tool", "output")):
            count += 1
    return count


def _read_simple_env(path: Path) -> dict[str, str]:
    try:
        text = larch_io.read_text(path, errors="replace", default="")
    except OSError:
        return {}
    return larch_io.parse_kv(text)



def _round_difficulty_object(round_dir: Path) -> dict[str, object]:
    raw = round_dir / difficulty.SCOUT_RAW_RATING_BASENAME
    rating = difficulty.read_rating_file(raw)
    record = _read_json_object(round_dir / difficulty.DIFFICULTY_RECORD_BASENAME)
    if not isinstance(record, dict):  # type: ignore[reportUnnecessaryIsInstance]
        record = {}
    if rating is None and not record:
        return {
            "tier_in_effect": None,
            "ceiling_in_effect": None,
            "escalations": [],
            "scout": {"status": "absent"},
        }
    object_data: dict[str, object] = {
        "tier_in_effect": None,
        "ceiling_in_effect": None,
        "escalations": [],
        "scout": {"status": "absent"},
    }
    if rating is not None:
        object_data.update(  # type: ignore[reportUnknownArgumentType]
            {
                "tier_in_effect": rating.adjusted_tier,
                "ceiling_in_effect": rating.adjusted_tier,
                "scout": {
                    "status": "ok",
                    "predicted_tier": rating.predicted_tier,
                    "confidence": rating.confidence,
                    "source": str(raw),
                },
            }
        )
    if record:
        panel_tier = str(record.get("panel_tier") or record.get("applied_tier") or object_data.get("tier_in_effect") or "")
        round_cap = record.get("round_cap")
        if not isinstance(round_cap, int):
            round_cap = difficulty.tier_ceiling(panel_tier) if panel_tier else None
        elif panel_tier:
            round_cap = min(round_cap, difficulty.tier_ceiling(panel_tier))
        escalations = record.get("escalations")
        object_data.update(
            {  # type: ignore[reportUnknownArgumentType]
                "tier_in_effect": panel_tier or object_data.get("tier_in_effect"),
                "ceiling_in_effect": round_cap if round_cap is not None else object_data.get("ceiling_in_effect"),
                "applied_tier": str(record.get("applied_tier") or ""),
                "panel_tier": str(record.get("panel_tier") or ""),
                "round_cap": round_cap,
                "codex_model_role": str(record.get("codex_model_role") or ""),
                "override_source": str(record.get("override_source") or ""),
                "audit_evaluated": record.get("audit_evaluated"),
                "audit_upgrade": str(record.get("audit_upgrade") or "") or None,
                "escalated_round": record.get("escalated_round"),
                "escalations": escalations if isinstance(escalations, list) else object_data.get("escalations", []),
            }
        )
    return object_data

def _round_meta_object(
    *, counts: tuple[int, ...],
    panel_count: int,
    collector: str = "",
    revise: dict[str, str | None] | None = None,
    canonical: tuple[int, ...] | None = None,
    nit_pruned: int = 0,
    difficulty_obj: dict[str, object] | None = None,
) -> dict[str, object]:
    accepted, rejected, neutral, exonerated, oos_accepted, oos_rejected = counts[:6]
    tally_oos_proposed = oos_accepted
    tally_oos_fileable = (
        counts[OOS_FILEABLE_COUNT_INDEX] if len(counts) > OOS_FILEABLE_COUNT_INDEX else oos_accepted
    )
    obj: dict[str, object] = {
        "tally": {
            "ACCEPTED_COUNT": str(accepted),
            "REJECTED_COUNT": str(rejected),
            "EXONERATED_COUNT": str(exonerated),
            "NEUTRAL_COUNT": str(neutral),
            "OOS_PROPOSED_COUNT": str(tally_oos_proposed),
            "OOS_ACCEPTED_COUNT": str(tally_oos_fileable),
            "OOS_REJECTED_COUNT": str(oos_rejected),
        },
        "summary": {"panel": {"total_slot_count": panel_count}},
        "collector": collector,
        "difficulty": difficulty_obj or {
            "tier_in_effect": None,
            "ceiling_in_effect": None,
            "escalations": [],
            "scout": {"status": "absent"},
        },
    }
    # Issue #4882: the raw `tally` above counts findings by id-prefix (FINDING_/OOS_), so a
    # nit-pruned [OUT_OF_SCOPE] FINDING_N is miscounted as in-scope rejected. Record the canonical,
    # scope-aware decomposition alongside it (matching code-review-tally.json) so the run-summary can
    # reconcile the two and downstream joins do not see a contradiction.
    if canonical is not None:
        c_accepted, c_rejected, c_neutral, c_exonerated, c_oos_accepted, c_oos_rejected = canonical[:6]
        c_oos_proposed = c_oos_accepted
        c_oos_fileable = (
            canonical[OOS_FILEABLE_COUNT_INDEX]
            if len(canonical) > OOS_FILEABLE_COUNT_INDEX
            else c_oos_accepted
        )
        obj["tally_canonical"] = {
            "ACCEPTED_COUNT": str(c_accepted),
            "REJECTED_COUNT": str(c_rejected),
            "EXONERATED_COUNT": str(c_exonerated),
            "NEUTRAL_COUNT": str(c_neutral),
            "OOS_PROPOSED_COUNT": str(c_oos_proposed),
            "OOS_ACCEPTED_COUNT": str(c_oos_fileable),
            "OOS_REJECTED_COUNT": str(c_oos_rejected),
        }
        obj["nit_pruned_count"] = str(nit_pruned)
    if revise is not None:
        obj["revise"] = revise
    return obj


def _canonical_decomposition(round_dir: Path) -> tuple[tuple[int, int, int, int, int, int] | None, int]:
    """Issue #4882: scope-aware in-scope/OOS counts from the classification TSV, plus nit-pruned.

    The classification TSV carries the authoritative ``scope`` column, so it separates in-scope
    findings from out-of-scope ones (including nit-pruned ``[OUT_OF_SCOPE] FINDING_N`` blocks that
    keep a ``FINDING_`` id). Returns ``(None, 0)`` when no classification data is available (e.g.
    design plan-review rounds), leaving the raw tally as the only recorded view.
    """
    tsv = round_dir / "findings-classification.tsv"
    if not tsv.is_file() or not _tsv_has_data_rows(tsv):
        return None, 0
    canonical = _parse_classification_tsv(tsv)
    oos_split = _classification_oos_split(round_dir)
    if oos_split is not None:
        oos_proposed, oos_rejected, _oos_fileable = oos_split
        canonical = (*canonical[:4], oos_proposed, oos_rejected)
    nit_pruned = 0
    prune_env = round_dir / "prune-nit.env"
    if prune_env.is_file():
        raw = _read_simple_env(prune_env).get("PRUNED_COUNT", "")
        if raw.isdigit():
            nit_pruned = int(raw)
    return canonical, nit_pruned


def _design_collector_field(*, round_dir: Path, failure_count: int) -> str:
    """Build round-meta.json's ``collector`` field from real per-slot collector records.

    The collector writes ``collector-results.env`` (blank-line-separated
    ``KEY=VALUE`` records: ``REVIEWER_FILE``/``TOOL``/``STATUS``/...) at the design
    tmpdir root; mirror
    ``_materialize_design_panel_manifest`` by checking the round dir first, then the
    design root. Each non-OK record becomes a ``TOOL``/``STATUS``/``REVIEWER_FILE``
    block carrying the real failing slot's tool and output basename, so the renderer
    resolves the true vendor/archetype instead of ``unknown/collector-failure-N``.
    Falls back to count-based placeholders only when no per-slot records are available.
    """
    if failure_count <= 0:
        return ""
    collector_env = round_dir / "collector-results.env"
    if not collector_env.is_file():
        collector_env = round_dir.parent.parent / "collector-results.env"
    records: list[str] = []
    collector_text = "\n".join(_read_lines_best_effort(collector_env))
    for record in collect_results.parse_collector_records(collector_text):
        status = record.get("STATUS", "")
        if status and status != "OK":
            tool = record.get("TOOL", "")
            reviewer_file = record.get("REVIEWER_FILE", "")
            records.append(f"TOOL={tool}\nSTATUS={status}\nREVIEWER_FILE={Path(reviewer_file).name}")
    if records:
        return "\n\n".join(records)
    return "\n\n".join(
        f"TOOL=unknown\nSTATUS=FAILED\nREVIEWER_FILE=collector-failure-{index}.txt"
        for index in range(1, failure_count + 1)
    )


def write_design_round_meta(round_dir: Path) -> int:
    if not round_dir.is_dir():
        return 0
    try:
        counts, source = _round_counts(round_dir)
        if source:
            counts = _adjust_design_security_oos(round_dir=round_dir, counts=counts, source=source)
        oos_split = _artifact_oos_split(round_dir) or (counts[4], counts[5], 0)
        meta_counts = (*counts[:4], oos_split[0], oos_split[1], oos_split[2])
        panel_count = _materialize_design_panel_manifest(round_dir)
        env = _read_simple_env(round_dir / "round-summary.env")
        failures = _as_int(env.get("COLLECT_FAILURE_COUNT"))
        collector = _design_collector_field(round_dir=round_dir, failure_count=failures)
        revise_env = _read_simple_env(round_dir / "revise" / "revise.env")
        meta = _round_meta_object(
            counts=meta_counts,
            panel_count=panel_count,
            collector=collector,
            revise={
                "status": revise_env.get("REVISE_STATUS") or None,
                "tier": revise_env.get("REVISE_TIER") or None,
            },
            difficulty_obj=_round_difficulty_object(round_dir),
        )
        tmp = round_dir / "round-meta.json.tmp"
        tmp.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        tmp.replace(round_dir / "round-meta.json")
    except Exception:  # pylint: disable=broad-except
        return 1
    return 0


def write_implement_round_meta(round_dir: Path) -> int:
    if not round_dir.is_dir():
        return 0
    try:
        counts, _source = _round_counts(round_dir)
        oos_split = _artifact_oos_split(round_dir) or (counts[4], counts[5], 0)
        meta_counts = (*counts[:4], oos_split[0], oos_split[1], oos_split[2])
        panel_count = _count_panel_manifest(round_dir / "panel-manifest.ndjson")
        canonical, nit_pruned = _canonical_decomposition(round_dir)
        canonical_oos_split = _classification_oos_split(round_dir)
        env_fileable = _review_tally_fileable_count(round_dir)
        canonical_meta = canonical
        if canonical_oos_split is not None:
            canonical_fileable = env_fileable if env_fileable is not None else canonical_oos_split[2]
            canonical_meta = (
                *(canonical or (0, 0, 0, 0, 0, 0))[:4],
                canonical_oos_split[0],
                canonical_oos_split[1],
                canonical_fileable,
            )
        meta = _round_meta_object(
            counts=meta_counts,
            panel_count=panel_count,
            canonical=canonical_meta,
            nit_pruned=nit_pruned,
            difficulty_obj=_round_difficulty_object(round_dir),
        )
        tmp = round_dir / "round-meta.json.tmp"
        tmp.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        tmp.replace(round_dir / "round-meta.json")
    except Exception:  # pylint: disable=broad-except
        return 1
    return 0


def render_phase_detail_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress render-phase-detail")
    parser.add_argument("--rounds-root", required=True)
    parser.add_argument("--findings-file")
    parser.add_argument("--timing-ledger")
    parser.add_argument("--token-ledger")
    parser.add_argument("--skill", choices=("implement", "design"), default="implement")
    parser.add_argument("--top-n", default="7")
    parser.add_argument("--no-gantt", action="store_true")
    parser.add_argument("--output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    top_n = int(args.top_n) if str(args.top_n).isdigit() else 7
    text = render_phase_detail(
        rounds_root=Path(args.rounds_root),
        skill=args.skill,
        timing_ledger=Path(args.timing_ledger) if args.timing_ledger else None,
        token_ledger=Path(args.token_ledger) if args.token_ledger else None,
        findings_file=Path(args.findings_file) if args.findings_file else None,
        top_n=top_n,
        gantt_enabled=not args.no_gantt,
    )
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def write_design_round_meta_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress write-design-round-meta")
    parser.add_argument("--round-dir", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    return write_design_round_meta(Path(args.round_dir))


def write_implement_round_meta_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress write-implement-round-meta")
    parser.add_argument("--round-dir", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    return write_implement_round_meta(Path(args.round_dir))
