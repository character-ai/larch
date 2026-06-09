#!/usr/bin/env bash
# write-design-round-meta.sh — synthesize /design plan-review round renderer metadata.

set -euo pipefail

usage() {
    printf '%s\n' 'Usage: write-design-round-meta.sh --round-dir DIR' >&2
}

ROUND_DIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --round-dir) ROUND_DIR="${2:?--round-dir requires a value}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

[[ -n "$ROUND_DIR" ]] || { usage; exit 2; }
[[ -d "$ROUND_DIR" ]] || exit 0

ACCEPTED_COUNT=0
REJECTED_COUNT=0
NEUTRAL_COUNT=0
EXONERATED_COUNT=0
OOS_ACCEPTED_COUNT=0
OOS_REJECTED_COUNT=0

_parse_tally_md() {
    local file="$1"
    awk -F'|' '
        function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
        /^## Findings/ { in_findings=1; next }
        /^## / && in_findings { in_findings=0 }
        in_findings && NF >= 4 {
            item=trim($2)
            result=trim($(NF-1))
            if (result == "" || result ~ /^-+$/) {
                result=trim($(NF-2))
            }
            if (item == "" || item == "Item" || item ~ /^-+$/ || result == "" || result == "Result" || result ~ /^-+$/) {
                next
            }
            if (item ~ /^FINDING_[0-9A-Za-z_]+$/) {
                if (result == "accepted") accepted++
                else if (result == "rejected") rejected++
                else if (result == "neutral") neutral++
                else if (result == "exonerated") exonerated++
            } else if (item ~ /^OOS_[0-9A-Za-z_]+$/) {
                if (result == "accepted") oos_accepted++
                else oos_rejected++
            }
        }
        END { printf "%d\t%d\t%d\t%d\t%d\t%d\n", accepted+0, rejected+0, neutral+0, exonerated+0, oos_accepted+0, oos_rejected+0 }
    ' "$file" 2>/dev/null || printf '0\t0\t0\t0\t0\t0\n'
}

_parse_classification_tsv() {
    local file="$1"
    awk -F'\t' '
        NR == 1 { next }
        function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
        {
            item=trim($1)
            result=trim($3)
            if (item == "" || result == "") next
            if (item ~ /^FINDING_[0-9A-Za-z_]+$/) {
                if (result == "accepted") accepted++
                else if (result == "rejected") rejected++
                else if (result == "neutral") neutral++
                else if (result == "exonerated") exonerated++
            } else if (item ~ /^OOS_[0-9A-Za-z_]+$/) {
                if (result == "accepted") oos_accepted++
                else oos_rejected++
            }
        }
        END { printf "%d\t%d\t%d\t%d\t%d\t%d\n", accepted+0, rejected+0, neutral+0, exonerated+0, oos_accepted+0, oos_rejected+0 }
    ' "$file" 2>/dev/null || printf '0\t0\t0\t0\t0\t0\n'
}

_counts=""
if [[ -f "$ROUND_DIR/voting-tally.md" ]]; then
    _counts="$(_parse_tally_md "$ROUND_DIR/voting-tally.md")"
elif [[ -f "$ROUND_DIR/findings-classification.tsv" ]]; then
    _counts="$(_parse_classification_tsv "$ROUND_DIR/findings-classification.tsv")"
else
    _counts=$'0\t0\t0\t0\t0\t0'
fi
IFS=$'\t' read -r ACCEPTED_COUNT REJECTED_COUNT NEUTRAL_COUNT EXONERATED_COUNT OOS_ACCEPTED_COUNT OOS_REJECTED_COUNT <<EOF_COUNTS
$_counts
EOF_COUNTS
for _v in ACCEPTED_COUNT REJECTED_COUNT NEUTRAL_COUNT EXONERATED_COUNT OOS_ACCEPTED_COUNT OOS_REJECTED_COUNT; do
    case "${!_v:-}" in ''|*[!0-9]*) printf -v "$_v" '%s' 0 ;; esac
done

_panel_tmp="$ROUND_DIR/panel-manifest.ndjson.tmp"
_meta_tmp="$ROUND_DIR/round-meta.json.tmp"
_panel_count=0
if command -v python3 >/dev/null 2>&1; then
    _panel_count=$(python3 - "$ROUND_DIR/plan-review-slots.ndjson" "$_panel_tmp" <<'PY' || printf '0'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
out = Path(sys.argv[2])
count = 0
with out.open("w", encoding="utf-8") as dst:
    try:
        lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        slot = str(obj.get("slot") or "")
        tool = str(obj.get("tool") or "")
        output = str(obj.get("output") or "")
        if not (slot or tool or output):
            continue
        dst.write(json.dumps({"slot": slot, "tool": tool, "output": output}, separators=(",", ":")) + "\n")
        count += 1
print(count)
PY
)
else
    : >"$_panel_tmp"
fi
case "$_panel_count" in ''|*[!0-9]*) _panel_count=0 ;; esac
mv -f "$_panel_tmp" "$ROUND_DIR/panel-manifest.ndjson" 2>/dev/null || true

_collect_failures=0
if [[ -f "$ROUND_DIR/round-summary.env" ]]; then
    _collect_failures=$(awk -F= '$1 == "COLLECT_FAILURE_COUNT" { print $2; exit }' "$ROUND_DIR/round-summary.env" 2>/dev/null || printf '0')
fi
case "$_collect_failures" in ''|*[!0-9]*) _collect_failures=0 ;; esac
_collector=""
_i=1
while [[ "$_i" -le "$_collect_failures" ]]; do
    _record=$(printf 'TOOL=unknown\nSTATUS=FAILED\nREVIEWER_FILE=collector-failure-%s.txt\n' "$_i")
    if [[ -n "$_collector" ]]; then
        _collector="$_collector"$'\n\n'"$_record"
    else
        _collector="$_record"
    fi
    _i=$((_i + 1))
done

if command -v jq >/dev/null 2>&1; then
    jq -n \
        --arg accepted "$ACCEPTED_COUNT" \
        --arg rejected "$REJECTED_COUNT" \
        --arg exonerated "$EXONERATED_COUNT" \
        --arg neutral "$NEUTRAL_COUNT" \
        --arg oos_accepted "$OOS_ACCEPTED_COUNT" \
        --arg oos_rejected "$OOS_REJECTED_COUNT" \
        --arg panel_count "$_panel_count" \
        --arg collector "$_collector" \
        '{tally:{ACCEPTED_COUNT:$accepted,REJECTED_COUNT:$rejected,EXONERATED_COUNT:$exonerated,NEUTRAL_COUNT:$neutral,OOS_ACCEPTED_COUNT:$oos_accepted,OOS_REJECTED_COUNT:$oos_rejected},summary:{panel:{total_slot_count:($panel_count|tonumber)}},collector:$collector}' \
        >"$_meta_tmp" 2>/dev/null || : >"$_meta_tmp"
fi

if [[ ! -s "$_meta_tmp" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        python3 - "$ACCEPTED_COUNT" "$REJECTED_COUNT" "$EXONERATED_COUNT" "$NEUTRAL_COUNT" "$OOS_ACCEPTED_COUNT" "$OOS_REJECTED_COUNT" "$_panel_count" "$_collector" "$_meta_tmp" <<'PY' || : >"$_meta_tmp"
import json
import sys
accepted, rejected, exonerated, neutral, oos_accepted, oos_rejected, panel_count, collector, out = sys.argv[1:10]
obj = {
    "tally": {
        "ACCEPTED_COUNT": accepted,
        "REJECTED_COUNT": rejected,
        "EXONERATED_COUNT": exonerated,
        "NEUTRAL_COUNT": neutral,
        "OOS_ACCEPTED_COUNT": oos_accepted,
        "OOS_REJECTED_COUNT": oos_rejected,
    },
    "summary": {"panel": {"total_slot_count": int(panel_count or 0)}},
    "collector": collector,
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(obj, fh, indent=2)
    fh.write("\n")
PY
    fi
fi

if [[ -s "$_meta_tmp" ]]; then
    mv -f "$_meta_tmp" "$ROUND_DIR/round-meta.json" 2>/dev/null || true
else
    rm -f "$_meta_tmp" 2>/dev/null || true
fi
exit 0
