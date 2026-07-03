# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
# ruff: noqa: PLR2004,PTH105,PTH108
# pylint: disable=too-many-branches,too-many-statements,too-many-locals,too-many-arguments
"""Reviewer pruning logic for the review pipeline."""

from __future__ import annotations

import contextlib
import csv
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

from larch.core import logging_util
from larch.review.review_pipeline_shared import (
    PruneFilterResult,
    PruneRoundCounts,
    REVIEWER_PRUNE_ACCEPTANCE_FLOOR_DENOMINATOR,
    REVIEWER_PRUNE_ACCEPTANCE_FLOOR_NUMERATOR,
    _atomic_write,
    _emit_kv,
    _get,
    _manifest_rows,
    _parse_args,
    _usage,
)
from larch.review import voting


def _manifest_combo(row: dict[str, object]) -> str:
    return f"{row.get('tool', '')}:{row.get('slot', '')}"


def _output_label(row: dict[str, object]) -> str:
    output = str(row.get("output") or "")
    return Path(output).name or str(row.get("slot") or "")


def _normalize_code_label(label: str) -> str:
    import re  # noqa: PLC0415
    label = re.sub(r"\s*\([^()]*\)\s*$", "", label.strip()).strip()
    base = Path(label).name
    stem, ext = (base[:-4], ".txt") if base.endswith(".txt") else (base, "")
    # Reviewer output labels are "<slot>-output[-phase2|-phase3|-retry|...][.txt]"
    # filenames, while the aggregator now emits the bare "<slot>" token
    # (issue #5733). Drop the rightmost "-output" segment and everything after it
    # (decoration plus the ".txt" that belongs to the output filename) so both
    # forms canonicalize to "<slot>" and the reviewer-prune join populates
    # non-zero counts instead of pruning the whole panel at round 2. The
    # rightmost split matches the greedy "(.+)-output" slot convention used by
    # _slot_tool_from_reviewer_basename.
    if "-output" in stem:
        return stem.rpartition("-output")[0]
    while True:
        new = re.sub(r"-(?:phase2|phase3|retry)$", "", stem)
        if new == stem:
            break
        stem = new
    return stem + ext


def _read_label_map(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[0]:
            mapping[parts[0]] = parts[1]
    return mapping


def _tokenize_plan_finding_reviewers(*, cell: str, labels: Iterable[str]) -> set[str]:
    return set(voting.tokenize_finding_reviewers(cell=cell, labels=labels))


def _read_classification_counts(*, path: Path, labels: Iterable[str], plan_mode: bool) -> dict[str, PruneRoundCounts]:
    label_list = list(labels)
    mutable_counts: dict[str, dict[str, int]] = {
        label: {"accepted": 0, "weighted_accepted": 0, "rejected": 0, "total": 0} for label in label_list
    }
    label_keys: dict[str, str] = {label: label if plan_mode else _normalize_code_label(label) for label in label_list}
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            return {label: PruneRoundCounts() for label in label_list}
        header = list(reader.fieldnames)
        attr_col = "finding_reviewers" if "finding_reviewers" in header else "reviewer_slots"
        for row in reader:
            voting_result = (row.get("voting_result") or "").strip()
            if voting_result not in {"accepted", "rejected", "neutral"}:
                continue
            accepted_points = voting.accepted_points_from_classification_row(cols=row, header=header)
            cell = row.get(attr_col) or ""
            if plan_mode:
                tokens = _tokenize_plan_finding_reviewers(cell=cell, labels=label_list)
            else:
                tokens = {_normalize_code_label(token) for token in cell.split("|") if token.strip()}
            for label, key in label_keys.items():
                if key not in tokens:
                    continue
                mutable_counts[label]["total"] += 1
                if voting_result == "accepted":
                    mutable_counts[label]["accepted"] += 1
                    mutable_counts[label]["weighted_accepted"] += accepted_points
                elif voting_result == "rejected":
                    mutable_counts[label]["rejected"] += 1
    return {
        label: PruneRoundCounts(
            accepted=counts["accepted"],
            weighted_accepted=counts["weighted_accepted"],
            rejected=counts["rejected"],
            total=counts["total"],
        )
        for label, counts in mutable_counts.items()
    }


def _prune_ledger_header() -> list[str]:
    return ["round", "tool", "slot", "label", "accepted_count", "weighted_accepted_count", "rejected_count", "total_count"]


def _legacy_prune_ledger_header() -> list[str]:
    return ["round", "tool", "slot", "label", "accepted_count", "rejected_count", "total_count"]


def _normalize_prune_ledger_row(row: list[str]) -> list[str] | None:
    if len(row) == len(_legacy_prune_ledger_header()):
        normalized = [*row[:5], row[4], *row[5:]]
    elif len(row) == len(_prune_ledger_header()):
        normalized = list(row)
    else:
        return None
    try:
        int(normalized[0])
        int(normalized[4])
        int(normalized[5])
        int(normalized[6])
        int(normalized[7])
    except ValueError:
        return None
    return normalized


def _well_formed_prune_ledger_row(row: list[str]) -> bool:
    return _normalize_prune_ledger_row(row) is not None


def _rewrite_prune_ledger(*, path: Path, round_num: int, new_rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old_rows: list[list[str]] = []
    if path.exists():
        with path.open(encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t")
            for row in reader:
                if not row or row[0] == "round":
                    continue
                if not _well_formed_prune_ledger_row(row):
                    continue
                if int(row[0]) == round_num:
                    continue
                normalized = _normalize_prune_ledger_row(row)
                if normalized is not None:
                    old_rows.append(normalized)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(_prune_ledger_header())
            writer.writerows(old_rows)
            writer.writerows(new_rows)
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)


def reviewer_prune_record(*, ledger: Path, round_num: int, manifest: Path, classification: Path, label_map: Path | None = None) -> None:
    rows = _manifest_rows(manifest)
    label_mp = _read_label_map(label_map)
    plan_mode = bool(label_mp)
    slot_labels = [(row, label_mp.get(str(row.get("slot") or ""), _output_label(row))) for row in rows]
    counts = _read_classification_counts(path=classification, labels=[label for _, label in slot_labels], plan_mode=plan_mode)
    ledger_rows: list[list[str]] = []
    for row, label in slot_labels:
        count = counts.get(label, PruneRoundCounts())
        ledger_rows.append(
            [
                str(round_num),
                str(row.get("tool") or ""),
                str(row.get("slot") or ""),
                label,
                str(count.accepted),
                str(count.weighted_accepted),
                str(count.rejected),
                str(count.total),
            ]
        )
    _rewrite_prune_ledger(path=ledger, round_num=round_num, new_rows=ledger_rows)


def _ledger_history(*, path: Path, round_num: int) -> dict[str, dict[int, PruneRoundCounts]]:
    hist: dict[str, dict[int, PruneRoundCounts]] = {}
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader, None)
        if header not in (_prune_ledger_header(), _legacy_prune_ledger_header()):
            raise ValueError("missing ledger columns")
        for row in reader:
            normalized = _normalize_prune_ledger_row(row)
            if normalized is None:
                raise ValueError("malformed ledger row")
            r = int(normalized[0])
            counts = PruneRoundCounts(
                accepted=int(normalized[4]),
                weighted_accepted=int(normalized[5]),
                rejected=int(normalized[6]),
                total=int(normalized[7]),
            )
            if r >= round_num:
                continue
            key = f"{normalized[1]}:{normalized[2]}"
            per = hist.setdefault(key, {})
            existing = per.get(r)
            if existing is None:
                per[r] = counts
            else:
                per[r] = PruneRoundCounts(
                    accepted=max(existing.accepted, counts.accepted),
                    weighted_accepted=max(existing.weighted_accepted, counts.weighted_accepted),
                    rejected=max(existing.rejected, counts.rejected),
                    total=max(existing.total, counts.total),
                )
    return hist


def reviewer_prune_filter(*, ledger: Path, round_num: int, manifest: Path, out: Path) -> PruneFilterResult:
    import shutil  # noqa: PLC0415
    rows = _manifest_rows(manifest)
    env_override = os.environ.get("LARCH_REVIEWER_PRUNE", "")
    prune_active = "true"
    warn = ""
    if env_override == "off":
        prune_active = "false"
    elif env_override:
        warn = "reviewer-prune: ignoring LARCH_REVIEWER_PRUNE value; set it exactly to off to disable"
    if prune_active == "false" or round_num < 2:
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(manifest, out)
        return PruneFilterResult(prune_active, len(rows), 0, "", "false", warn=warn)
    try:
        hist = _ledger_history(path=ledger, round_num=round_num)
    except Exception as exc:  # fail open by contract
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(manifest, out)
        fail_warn = f"reviewer-prune: fail-open ledger read failed: {exc}"
        return PruneFilterResult("false", len(rows), 0, "", "false", "true", fail_warn)
    eligible: list[dict[str, object]] = []
    pruned: list[str] = []
    for row in rows:
        key = _manifest_combo(row)
        prior_counts = hist.get(key, {})
        if not prior_counts:
            pruned.append(key)
            continue
        accepted_sum = sum(counts.accepted for counts in prior_counts.values())
        weighted_accepted_sum = sum(counts.weighted_accepted for counts in prior_counts.values())
        rejected_sum = sum(counts.rejected for counts in prior_counts.values())
        total_sum = sum(counts.total for counts in prior_counts.values())
        net_prunable = total_sum <= 0 or weighted_accepted_sum - rejected_sum <= 0
        floor_prunable = (
            total_sum > 0
            and accepted_sum * REVIEWER_PRUNE_ACCEPTANCE_FLOOR_DENOMINATOR
            < total_sum * REVIEWER_PRUNE_ACCEPTANCE_FLOOR_NUMERATOR
        )
        if net_prunable or floor_prunable:
            pruned.append(key)
            continue
        eligible.append(row)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for row in eligible:
            import json  # noqa: PLC0415
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    if pruned:
        logging_util.diagnostic(f"→ review prune: round {round_num} drops {','.join(pruned)}")
    return PruneFilterResult("true", len(eligible), len(pruned), ",".join(pruned), "true" if not eligible else "false", warn=warn)


def _prune_nonneg_int(value: object) -> int:
    try:
        result = int(str(value))
    except ValueError:
        return 0
    return max(result, 0)


def derive_prune_status(*,
    prune_active: str,
    filter_rc: int | str,
    prune_fail_open: str,
    pruned_count: int | str,
    panel_pruned_empty: str,
    prune_evaluated: str,
) -> str:
    try:
        rc = int(str(filter_rc))
    except ValueError:
        rc = 1
    count = _prune_nonneg_int(pruned_count)
    if rc != 0 or prune_fail_open == "true":
        return "failed"
    if panel_pruned_empty == "true":
        return "pruned-empty"
    if prune_active != "true" or prune_evaluated != "true":
        return "skipped"
    if count > 0:
        return "active-dropped"
    return "active-kept-all"


def normalize_prune_eligible(*, prune_active: str, eligible_count: int | str) -> int:
    return 0 if prune_active != "true" else _prune_nonneg_int(eligible_count)


def prune_window_evaluated(round_num: int | str) -> str:
    try:
        return "true" if int(str(round_num)) >= 2 else "false"
    except ValueError:
        return "false"


def ensure_reviewer_prune_ledger(ledger: Path) -> None:
    if not str(ledger):
        return
    header = "\t".join(_prune_ledger_header())
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if not ledger.exists() or ledger.stat().st_size == 0:
        ledger.write_text(header + "\n", encoding="utf-8")
        return
    preserved: list[str] = []
    lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[1:]:
        row = line.split("\t")
        normalized = _normalize_prune_ledger_row(row)
        if normalized is not None:
            preserved.append("\t".join(normalized))
    ledger.write_text(header + "\n" + "".join(f"{line}\n" for line in preserved), encoding="utf-8")


def write_prune_decision_env(*,
    dest: Path,
    round_num: int | str,
    prune_active: str,
    prune_status: str,
    panel_full: int | str,
    eligible: int | str,
    pruned_count: int | str,
    pruned_combos: str,
    panel_pruned_empty: str,
) -> None:
    text = (
        f"ROUND={round_num}\n"
        f"PRUNE_ACTIVE={prune_active}\n"
        f"PRUNE_STATUS={prune_status}\n"
        f"PANEL_FULL={_prune_nonneg_int(panel_full)}\n"
        f"ELIGIBLE={_prune_nonneg_int(eligible)}\n"
        f"PRUNED_COUNT={_prune_nonneg_int(pruned_count)}\n"
        f"PRUNED_COMBOS={pruned_combos}\n"
        f"PANEL_PRUNED_EMPTY={panel_pruned_empty}\n"
    )
    _atomic_write(path=dest, text=text)


def reviewer_prune(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="review-reviewer-prune")
    usage = "Usage: review reviewer-prune record --ledger FILE --round N --manifest FILE --classification FILE [--label-map FILE] | review reviewer-prune filter --ledger FILE --round N --manifest FILE --out FILE"
    if not argv or "--help" in argv:
        _usage(usage)
        return 0 if argv and "--help" in argv else 2
    command, rest = argv[0], argv[1:]
    parsed = _parse_args(argv=rest, usage=usage, options={"--ledger", "--round", "--manifest", "--classification", "--label-map", "--out"})
    if parsed is None:
        return 0
    if not parsed or command not in {"record", "filter"}:
        _usage(usage)
        return 2
    round_raw = _get(parsed=parsed, key="--round")
    if not round_raw.isdigit() or int(round_raw) <= 0:
        _usage("review reviewer-prune: --round must be a positive integer")
        return 2
    round_num = int(round_raw)
    ledger = Path(_get(parsed=parsed, key="--ledger"))
    manifest = Path(_get(parsed=parsed, key="--manifest"))
    if not str(ledger):
        _usage("review reviewer-prune: --ledger is required")
        return 2
    if not manifest.is_file():
        _usage("review reviewer-prune: --manifest must name a file")
        return 2
    if command == "record":
        classification = Path(_get(parsed=parsed, key="--classification"))
        if not classification.is_file():
            _usage("review reviewer-prune: record requires --classification FILE")
            return 2
        label_map_raw = _get(parsed=parsed, key="--label-map")
        reviewer_prune_record(ledger=ledger, round_num=round_num, manifest=manifest, classification=classification, label_map=Path(label_map_raw) if label_map_raw else None)
        return 0
    out = Path(_get(parsed=parsed, key="--out"))
    if not str(out):
        _usage("review reviewer-prune: filter requires --out FILE")
        return 2
    result = reviewer_prune_filter(ledger=ledger, round_num=round_num, manifest=manifest, out=out)
    if result.warn:
        _emit_kv(key="WARN", value=result.warn)
    _emit_kv(key="PRUNE_ACTIVE", value=result.prune_active)
    _emit_kv(key="ELIGIBLE_COUNT", value=result.eligible_count)
    _emit_kv(key="PRUNED_COUNT", value=result.pruned_count)
    _emit_kv(key="PRUNED_COMBOS", value=result.pruned_combos)
    _emit_kv(key="PANEL_PRUNED_EMPTY", value=result.panel_pruned_empty)
    if result.prune_fail_open == "true":
        _emit_kv(key="PRUNE_FAIL_OPEN", value="true")
    return 0


def reviewer_prune_main(argv: list[str]) -> int:
    return reviewer_prune(argv)
