#!/usr/bin/env bash
# write-implement-round-meta.sh — synthesize /implement code-review round
# renderer metadata (round-meta.json) from available new-format artifacts.
#
# Analogous to write-design-round-meta.sh but adapted for /implement rounds,
# which carry findings-classification.tsv + voting-tally.md + panel-manifest.ndjson
# instead of the old-format sidecar files. Called from review-and-fix.sh before
# flush_round_log_after_coder so the file is present when write-round copies it
# to the larch-log directory (round-meta.json is included in _ROUND_ARTIFACT_ALLOW
# in python/run_logs.py).
#
# render-review-phase-detail.sh gates each round on the presence of round-meta.json
# (line 80); without it the Review Phase Detail table is never emitted in the
# final report (issue #4038).

set -euo pipefail

usage() {
    printf '%s\n' 'Usage: write-implement-round-meta.sh --round-dir DIR' >&2
}

ROUND_DIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --round-dir) [ $# -ge 2 ] || { usage; exit 2; }; ROUND_DIR="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

[ -n "$ROUND_DIR" ] || { usage; exit 2; }
[ -d "$ROUND_DIR" ] || exit 0

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

_counts_all_zero() {
    [ "${1:-}" = "$(printf '0\t0\t0\t0\t0\t0')" ]
}

_tsv_has_data_rows() {
    local file="$1"
    awk 'NR > 1 && NF > 0 { found = 1; exit } END { exit(found ? 0 : 1) }' "$file" 2>/dev/null
}

_counts=""
_count_source=""
_md_counts=""
_tsv_counts=""
if [ -f "$ROUND_DIR/voting-tally.md" ]; then
    _md_counts="$(_parse_tally_md "$ROUND_DIR/voting-tally.md")"
    _counts="$_md_counts"
    _count_source=md
fi
if [ -f "$ROUND_DIR/findings-classification.tsv" ]; then
    _tsv_counts="$(_parse_classification_tsv "$ROUND_DIR/findings-classification.tsv")"
    if [ -z "$_counts" ]; then
        _counts="$_tsv_counts"
        _count_source=tsv
    elif _counts_all_zero "$_md_counts" && _tsv_has_data_rows "$ROUND_DIR/findings-classification.tsv"; then
        _counts="$_tsv_counts"
        _count_source=tsv
    fi
fi
[ -n "$_counts" ] || _counts=$(printf '0\t0\t0\t0\t0\t0')

IFS=$'\t' read -r ACCEPTED_COUNT REJECTED_COUNT NEUTRAL_COUNT EXONERATED_COUNT OOS_ACCEPTED_COUNT OOS_REJECTED_COUNT <<EOF_COUNTS
$_counts
EOF_COUNTS
for _v in ACCEPTED_COUNT REJECTED_COUNT NEUTRAL_COUNT EXONERATED_COUNT OOS_ACCEPTED_COUNT OOS_REJECTED_COUNT; do
    case "${!_v:-}" in ''|*[!0-9]*) printf -v "$_v" '%s' 0 ;; esac
done

_panel_count=0
if [ -f "$ROUND_DIR/panel-manifest.ndjson" ] && command -v python3 >/dev/null 2>&1; then
    _panel_count=$(python3 - "$ROUND_DIR/panel-manifest.ndjson" <<'PY' || printf '0'
import json
import sys
count = 0
try:
    with open(sys.argv[1], encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and any(obj.get(k) for k in ('slot', 'tool', 'output')):
                count += 1
except OSError:
    pass
print(count)
PY
)
fi
case "$_panel_count" in ''|*[!0-9]*) _panel_count=0 ;; esac

_meta_tmp="$ROUND_DIR/round-meta.json.tmp"
trap 'rm -f "$_meta_tmp"' EXIT

if command -v jq >/dev/null 2>&1; then
    jq -n \
        --arg accepted "$ACCEPTED_COUNT" \
        --arg rejected "$REJECTED_COUNT" \
        --arg exonerated "$EXONERATED_COUNT" \
        --arg neutral "$NEUTRAL_COUNT" \
        --arg oos_accepted "$OOS_ACCEPTED_COUNT" \
        --arg oos_rejected "$OOS_REJECTED_COUNT" \
        --arg panel_count "$_panel_count" \
        '{tally:{ACCEPTED_COUNT:$accepted,REJECTED_COUNT:$rejected,EXONERATED_COUNT:$exonerated,NEUTRAL_COUNT:$neutral,OOS_ACCEPTED_COUNT:$oos_accepted,OOS_REJECTED_COUNT:$oos_rejected},summary:{panel:{total_slot_count:($panel_count|tonumber)}},collector:""}' \
        >"$_meta_tmp" 2>/dev/null || : >"$_meta_tmp"
fi

if [ ! -s "$_meta_tmp" ] && command -v python3 >/dev/null 2>&1; then
    python3 - "$ACCEPTED_COUNT" "$REJECTED_COUNT" "$EXONERATED_COUNT" "$NEUTRAL_COUNT" "$OOS_ACCEPTED_COUNT" "$OOS_REJECTED_COUNT" "$_panel_count" "$_meta_tmp" <<'PY' || : >"$_meta_tmp"
import json
import sys
accepted, rejected, exonerated, neutral, oos_accepted, oos_rejected, panel_count, out = sys.argv[1:9]
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
    "collector": "",
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(obj, fh, indent=2)
    fh.write("\n")
PY
fi

if [ -s "$_meta_tmp" ]; then
    mv -f "$_meta_tmp" "$ROUND_DIR/round-meta.json" 2>/dev/null || true
else
    rm -f "$_meta_tmp" 2>/dev/null || true
fi
exit 0
