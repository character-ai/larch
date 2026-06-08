#!/usr/bin/env bash
# reviewer-prune.sh — Per-run reviewer slot pruning ledger helper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: reviewer-prune.sh record --ledger FILE --round N --manifest FILE --classification FILE [--label-map FILE] | reviewer-prune.sh filter --ledger FILE --round N --manifest FILE --out FILE"
}

cmd="${1:-}"
[[ -n "$cmd" ]] || { usage; exit 2; }
shift

LEDGER=""
ROUND=""
MANIFEST=""
CLASSIFICATION=""
LABEL_MAP=""
OUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ledger) LEDGER="${2:?--ledger requires a value}"; shift 2 ;;
        --round) ROUND="${2:?--round requires a value}"; shift 2 ;;
        --manifest) MANIFEST="${2:?--manifest requires a value}"; shift 2 ;;
        --classification) CLASSIFICATION="${2:?--classification requires a value}"; shift 2 ;;
        --label-map) LABEL_MAP="${2:?--label-map requires a value}"; shift 2 ;;
        --out) OUT="${2:?--out requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "reviewer-prune.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

case "$ROUND" in ''|*[!0-9]*) larch_err "reviewer-prune.sh: --round must be a positive integer"; exit 2 ;; esac
ROUND=$((10#$ROUND))
(( ROUND > 0 )) || { larch_err "reviewer-prune.sh: --round must be a positive integer"; exit 2; }
[[ -n "$LEDGER" ]] || { larch_err "reviewer-prune.sh: --ledger is required"; exit 2; }
[[ -n "$MANIFEST" && -f "$MANIFEST" ]] || { larch_err "reviewer-prune.sh: --manifest must name a file"; exit 2; }

case "$cmd" in
    record)
        [[ -n "$CLASSIFICATION" && -f "$CLASSIFICATION" ]] || { larch_err "reviewer-prune.sh: record requires --classification FILE"; exit 2; }
        ;;
    filter)
        [[ -n "$OUT" ]] || { larch_err "reviewer-prune.sh: filter requires --out FILE"; exit 2; }
        ;;
    *)
        larch_err "reviewer-prune.sh: first argument must be record or filter"
        usage
        exit 2
        ;;
esac

python3 - "$cmd" "$LEDGER" "$ROUND" "$MANIFEST" "$CLASSIFICATION" "$LABEL_MAP" "$OUT" <<'PY'
import csv
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

cmd, ledger, round_s, manifest, classification, label_map, out = sys.argv[1:8]
round_num = int(round_s)


def emit(k: str, v: str) -> None:
    print(f"{k}={v}")


def warn(v: str) -> None:
    emit("WARN", v)


def manifest_rows(path: str):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append(obj)
    return rows


def combo(row):
    return f"{row.get('tool','')}:{row.get('slot','')}"


def output_label(row):
    return os.path.basename(str(row.get("output") or "")) or str(row.get("slot") or "")


def normalize_code_label(label: str) -> str:
    label = (label or "").strip()
    # One trailing parenthetical strip, matching aggregate-findings label cleanup.
    label = re.sub(r"\s*\([^()]*\)\s*$", "", label).strip()
    base = os.path.basename(label)
    stem, ext = (base[:-4], ".txt") if base.endswith(".txt") else (base, "")
    while True:
        new = re.sub(r"-(?:phase2|phase3|retry)$", "", stem)
        if new == stem:
            break
        stem = new
    return stem + ext


def split_plan_tokens(cell: str):
    return [t.strip() for t in re.split(r"[,\s]+", cell.strip()) if t.strip()]


def split_code_tokens(cell: str):
    return [normalize_code_label(t) for t in cell.split("|") if t.strip()]


def read_label_map(path: str):
    mp = {}
    if not path:
        return mp
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2 and parts[0]:
                mp[parts[0]] = parts[1]
    return mp


def read_classification_counts(path: str, labels, plan_mode: bool):
    counts = {label: 0 for label in labels}
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not reader.fieldnames:
            return counts
        attr_col = "finding_reviewers" if "finding_reviewers" in reader.fieldnames else "reviewer_slots"
        for row in reader:
            if (row.get("voting_result") or "").strip() != "accepted":
                continue
            cell = row.get(attr_col) or ""
            tokens = split_plan_tokens(cell) if plan_mode else split_code_tokens(cell)
            token_set = set(tokens)
            for label in labels:
                key = label if plan_mode else normalize_code_label(label)
                if key in token_set:
                    counts[label] += 1
    return counts


def rewrite_ledger(path: str, round_num: int, new_rows):
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    old_rows = []
    if dest.exists():
        with dest.open(encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.reader(fh, delimiter="\t")
            for row in reader:
                if not row:
                    continue
                if row[0] == "round":
                    continue
                try:
                    if int(row[0]) == round_num:
                        continue
                except ValueError:
                    continue
                if len(row) >= 5:
                    old_rows.append(row[:5])
    fd, tmp = tempfile.mkstemp(prefix=dest.name + ".", suffix=".tmp", dir=str(dest.parent))
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
            writer.writerow(["round", "tool", "slot", "label", "accepted_count"])
            for row in old_rows:
                writer.writerow(row)
            for row in new_rows:
                writer.writerow(row)
        os.replace(tmp, dest)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def record():
    rows = manifest_rows(manifest)
    label_mp = read_label_map(label_map)
    plan_mode = bool(label_mp)
    labels = []
    slot_labels = []
    for row in rows:
        slot = str(row.get("slot") or "")
        label = label_mp.get(slot, output_label(row))
        labels.append(label)
        slot_labels.append((row, label))
    counts = read_classification_counts(classification, labels, plan_mode)
    ledger_rows = []
    for row, label in slot_labels:
        ledger_rows.append([
            str(round_num),
            str(row.get("tool") or ""),
            str(row.get("slot") or ""),
            label,
            str(counts.get(label, 0)),
        ])
    rewrite_ledger(ledger, round_num, ledger_rows)


def ledger_history(path: str):
    hist = {}
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        required = {"round", "tool", "slot", "accepted_count"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("missing ledger columns")
        for row in reader:
            r = int((row.get("round") or "").strip())
            cnt = int((row.get("accepted_count") or "").strip())
            key = f"{row.get('tool','')}:{row.get('slot','')}"
            if r >= round_num:
                continue
            per = hist.setdefault(key, {})
            # idempotent/dedup defensive: keep max count for duplicate round rows.
            per[r] = max(per.get(r, cnt), cnt)
    return hist


def filter_rows():
    rows = manifest_rows(manifest)
    prune_active = "true"
    env_override = os.environ.get("LARCH_REVIEWER_PRUNE", "")
    pruned = []
    eligible = list(rows)
    if env_override == "off":
        prune_active = "false"
    elif env_override:
        warn("reviewer-prune: ignoring LARCH_REVIEWER_PRUNE value; set it exactly to off to disable")
    if prune_active == "false" or round_num <= 2 or round_num >= 5:
        shutil.copyfile(manifest, out)
        emit("PRUNE_ACTIVE", prune_active)
        emit("ELIGIBLE_COUNT", str(len(rows)))
        emit("PRUNED_COUNT", "0")
        emit("PRUNED_COMBOS", "")
        emit("PANEL_PRUNED_EMPTY", "false")
        return
    try:
        hist = ledger_history(ledger)
    except Exception as exc:
        shutil.copyfile(manifest, out)
        emit("PRUNE_ACTIVE", "false")
        emit("ELIGIBLE_COUNT", str(len(rows)))
        emit("PRUNED_COUNT", "0")
        emit("PRUNED_COMBOS", "")
        emit("PANEL_PRUNED_EMPTY", "false")
        warn(f"reviewer-prune: fail-open ledger read failed: {exc}")
        return
    eligible = []
    for row in rows:
        key = combo(row)
        rounds = sorted(hist.get(key, {}).items(), key=lambda kv: kv[0])
        recent = rounds[-2:]
        if len(recent) >= 2 and all(cnt == 0 for _, cnt in recent):
            pruned.append(key)
        else:
            eligible.append(row)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        for row in eligible:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    emit("PRUNE_ACTIVE", "true")
    emit("ELIGIBLE_COUNT", str(len(eligible)))
    emit("PRUNED_COUNT", str(len(pruned)))
    emit("PRUNED_COMBOS", ",".join(pruned))
    emit("PANEL_PRUNED_EMPTY", "true" if not eligible and rows else "false")
    if pruned:
        print(f"→ review prune: round {round_num} drops {','.join(pruned)}", file=sys.stderr)


if cmd == "record":
    record()
elif cmd == "filter":
    filter_rows()
else:
    raise SystemExit(2)
PY
