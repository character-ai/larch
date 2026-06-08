#!/usr/bin/env bash
# render-review-phase-detail.sh — per-review-round detail section for the
# /implement final report (issue #3774).
#
# Reads the live/committed review-phase artifacts of an /implement run and
# renders a markdown "Review Phase Detail" section:
#   - one table row per review round (suggestions made/accepted, OOS
#     proposed/accepted, time, cost, reviewers launched)
#   - a Total row summing the whole run
#   - the top-N reviewers (vendor/archetype) by suggestions accepted
#   - a count of reviewer slots that failed, broken down by vendor/archetype
#
# The dollar-primary cost line is owned exclusively by render-run-summary.sh
# (single-source dollar-line invariant), so the Cost column here is an em-dash
# placeholder with a footnote pointing at the run Cost line. Per-round token
# attribution is not currently instrumented (the token ledger has no per-round
# delimiters), so the placeholder is also the honest value.
#
# Best-effort / observability-only: on missing inputs, missing jq, or partially
# unreadable artifacts it renders what it can (or nothing) and exits 0, so it
# can never break the final report. Usage errors exit 2.
set -euo pipefail

ROUNDS_ROOT=""
FINDINGS_FILE=""
TIMING_LEDGER=""
SKILL="implement"
OUTPUT=""
TOP_N=7

usage() {
    printf '%s\n' \
        "Usage: render-review-phase-detail.sh --rounds-root DIR [--findings-file F] [--timing-ledger F] [--skill implement|design] [--top-n N] [--output F]" >&2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --rounds-root) [ $# -ge 2 ] || { usage; exit 2; }; ROUNDS_ROOT=$2; shift 2 ;;
        --findings-file) [ $# -ge 2 ] || { usage; exit 2; }; FINDINGS_FILE=$2; shift 2 ;;
        --timing-ledger) [ $# -ge 2 ] || { usage; exit 2; }; TIMING_LEDGER=$2; shift 2 ;;
        --skill) [ $# -ge 2 ] || { usage; exit 2; }; SKILL=$2; shift 2 ;;
        --top-n) [ $# -ge 2 ] || { usage; exit 2; }; TOP_N=$2; shift 2 ;;
        --output) [ $# -ge 2 ] || { usage; exit 2; }; OUTPUT=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

[ -n "$ROUNDS_ROOT" ] || { usage; exit 2; }
case "$SKILL" in implement|design) ;; *) usage; exit 2 ;; esac
case "$TOP_N" in ''|*[!0-9]*) TOP_N=7 ;; esac

finalize_empty() {
    # No review-phase detail to render: leave OUTPUT empty (truncate) / print nothing.
    [ -n "$OUTPUT" ] && : >"$OUTPUT"
    exit 0
}

# Without jq we cannot parse the JSON artifacts; degrade to no section.
command -v jq >/dev/null 2>&1 || finalize_empty
[ -d "$ROUNDS_ROOT" ] || finalize_empty

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/review-phase-detail.XXXXXX")" || finalize_empty
trap 'rm -rf "$WORK_DIR"' EXIT

# ---- discover review rounds (numeric round-N dirs with a round-meta.json) ----
rounds_list="$WORK_DIR/rounds.txt"
: >"$rounds_list"
for d in "$ROUNDS_ROOT"/round-*/; do
    [ -d "$d" ] || continue
    rn="$(basename "$d")"
    rn="${rn#round-}"
    case "$rn" in ''|*[!0-9]*) continue ;; esac
    [ -f "$d/round-meta.json" ] || continue
    printf '%s\n' "$rn"
done | sort -n >"$rounds_list"

[ -s "$rounds_list" ] || finalize_empty

# ---- awk library: derive "vendor/archetype" from a reviewer output basename ----
# Used only as a fallback when the panel-manifest map has no entry (older logs
# or dynamic slots whose vendor is unknown from the basename alone).
derive_awk="$WORK_DIR/derive.awk"
cat >"$derive_awk" <<'AWK'
function derive(b,    core, rest, vendor, arch) {
    core = b
    sub(/\.txt$/, "", core)
    sub(/-output-ns-retry$/, "", core)
    sub(/-output$/, "", core)
    sub(/-ns-retry$/, "", core)
    if (core ~ /^(cursor|codex|claude_sub|claude)-specialist-/) {
        vendor = core; sub(/-specialist-.*$/, "", vendor)
        arch = core;   sub(/^(cursor|codex|claude_sub|claude)-specialist-/, "", arch)
        return vendor "/" arch
    }
    if (core ~ /^(cursor|codex|claude_sub|claude)-generalist$/) {
        vendor = core; sub(/-generalist$/, "", vendor)
        return vendor "/generalist"
    }
    if (core ~ /^dyn-/) {
        arch = core; sub(/^dyn-/, "", arch)
        return "dynamic/" arch
    }
    if (core ~ /^(cursor|codex|claude_sub|claude)-/) {
        vendor = core; sub(/-.*$/, "", vendor)
        rest = core;   sub(/^(cursor|codex|claude_sub|claude)-/, "", rest)
        if (rest == "") rest = "panel"
        return vendor "/" rest
    }
    if (core == "" || core == "panel") return "panel/panel"
    return "unknown/" core
}
AWK

# ---- vendor/archetype map: output-basename -> "tool/slot" (panel manifests) ----
slot_map="$WORK_DIR/slot-map.tsv"
: >"$slot_map"
while IFS= read -r rn; do
    pm="$ROUNDS_ROOT/round-$rn/panel-manifest.ndjson"
    [ -f "$pm" ] || continue
    jq -r '
        select((.output // "") != "" and (.slot // "") != "" and (.tool // "") != "")
        | [ (.output | split("/") | last), (.tool + "/" + .slot) ] | @tsv
    ' "$pm" 2>/dev/null || true
done <"$rounds_list" | sort -u >"$slot_map"

fmt_hms() {
    local s="$1" h m sec
    case "$s" in ''|*[!0-9]*) printf -- '—'; return ;; esac
    [ "$s" -gt 0 ] || { printf -- '—'; return ; }
    h=$((s / 3600)); m=$(((s % 3600) / 60)); sec=$((s % 60))
    if [ "$h" -gt 0 ]; then
        printf '%dh %02dm %02ds' "$h" "$m" "$sec"
    elif [ "$m" -gt 0 ]; then
        printf '%dm %02ds' "$m" "$sec"
    else
        printf '%ds' "$sec"
    fi
}

# ---- per-round rows + running totals ----
rows_file="$WORK_DIR/rows.txt"
: >"$rows_file"
t_sug=0 t_acc=0 t_oosp=0 t_oosa=0 t_rev=0 t_secs=0 any_time=0
while IFS= read -r rn; do
    meta="$ROUNDS_ROOT/round-$rn/round-meta.json"
    counts="$(jq -r '
        def num(x): (x // 0) | (tostring | tonumber? // 0);
        (.tally // {}) as $t
        | (.summary.finding_counts // {}) as $fc
        | (.summary.panel // {}) as $p
        | [ num($t.ACCEPTED_COUNT // $fc.total_accepted),
            num($t.REJECTED_COUNT // $fc.total_rejected),
            num($t.EXONERATED_COUNT // $fc.total_exonerated),
            num($t.NEUTRAL_COUNT // $fc.total_neutral),
            num($t.OOS_ACCEPTED_COUNT),
            num($t.OOS_REJECTED_COUNT),
            num($p.total_slot_count // ((num($p.static_slot_count)) + (num($p.dynamic_slot_count)))) ]
        | @tsv
    ' "$meta" 2>/dev/null || printf '0\t0\t0\t0\t0\t0\t0')"
    acc=$(printf '%s' "$counts" | cut -f1); case "$acc" in ''|*[!0-9]*) acc=0 ;; esac
    rej=$(printf '%s' "$counts" | cut -f2); case "$rej" in ''|*[!0-9]*) rej=0 ;; esac
    exo=$(printf '%s' "$counts" | cut -f3); case "$exo" in ''|*[!0-9]*) exo=0 ;; esac
    neu=$(printf '%s' "$counts" | cut -f4); case "$neu" in ''|*[!0-9]*) neu=0 ;; esac
    oosa=$(printf '%s' "$counts" | cut -f5); case "$oosa" in ''|*[!0-9]*) oosa=0 ;; esac
    oosr=$(printf '%s' "$counts" | cut -f6); case "$oosr" in ''|*[!0-9]*) oosr=0 ;; esac
    rev=$(printf '%s' "$counts" | cut -f7); case "$rev" in ''|*[!0-9]*) rev=0 ;; esac
    sug=$((acc + rej + exo + neu))
    oosp=$((oosa + oosr))

    secs=""
    if [ -n "$TIMING_LEDGER" ] && [ -f "$TIMING_LEDGER" ]; then
        secs="$(awk -F'\t' -v r="$rn" '
            $2=="round" && $6==r {
                if (start=="" || ($7+0) < start) start=$7+0
                if (end=="" || ($8+0) > end) end=$8+0
            }
            END { if (start!="" && end!="" && end > start) print end-start }
        ' "$TIMING_LEDGER" 2>/dev/null || true)"
    fi
    case "$secs" in ''|*[!0-9]*) secs="" ;; esac

    t_sug=$((t_sug + sug)); t_acc=$((t_acc + acc))
    t_oosp=$((t_oosp + oosp)); t_oosa=$((t_oosa + oosa))
    t_rev=$((t_rev + rev))
    if [ -n "$secs" ]; then t_secs=$((t_secs + secs)); any_time=1; fi

    if [ -n "$secs" ]; then time_disp="$(fmt_hms "$secs")"; else time_disp="—"; fi
    printf '| %s | %s | %s | %s | %s | %s | — | %s |\n' \
        "$rn" "$sug" "$acc" "$oosp" "$oosa" "$time_disp" "$rev" >>"$rows_file"
done <"$rounds_list"

if [ "$any_time" -eq 1 ]; then total_time="$(fmt_hms "$t_secs")"; else total_time="—"; fi

# ---- top-N reviewers by suggestions accepted (whole run) ----
top_file="$WORK_DIR/top.txt"
: >"$top_file"
if [ -n "$FINDINGS_FILE" ] && [ -f "$FINDINGS_FILE" ]; then
    accepted_bn="$WORK_DIR/accepted-basenames.txt"
    jq -r '
        select((.outcome // "") == "accepted")
        | (.reviewer_slots // (if (.reviewer // "") != "" then [.reviewer] else [] end))
        | .[]?
        | split("/") | last
    ' "$FINDINGS_FILE" 2>/dev/null >"$accepted_bn" || : >"$accepted_bn"
    if [ -s "$accepted_bn" ]; then
        top_awk="$WORK_DIR/top.awk"
        cat >"$top_awk" <<'AWK'
FILENAME==mapfile { m[$1]=$2; next }
{
    bn=$0
    if (bn in m) va=m[bn]; else va=derive(bn)
    cnt[va]++
}
END { for (k in cnt) printf "%d\t%s\n", cnt[k], k }
AWK
        awk -F'\t' -v mapfile="$slot_map" -f "$derive_awk" -f "$top_awk" "$slot_map" "$accepted_bn" 2>/dev/null \
            | sort -k1,1nr -k2,2 | head -n "$TOP_N" >"$top_file" || : >"$top_file"
    fi
fi

# ---- failed reviewer slots by vendor/archetype (from round-meta collector) ----
fail_raw="$WORK_DIR/fail-raw.txt"
: >"$fail_raw"
collector_awk="$WORK_DIR/collector.awk"
cat >"$collector_awk" <<'AWK'
BEGIN { RS=""; FS="\n" }
{
    tool=""; status=""; rf=""
    for (i=1; i<=NF; i++) {
        if ($i ~ /^TOOL=/) tool=substr($i, 6)
        else if ($i ~ /^STATUS=/) status=substr($i, 8)
        else if ($i ~ /^REVIEWER_FILE=/) rf=substr($i, 15)
    }
    if (status != "" && status != "OK") {
        n=split(rf, a, "/"); base=a[n]
        print tool "\t" base
    }
}
AWK
while IFS= read -r rn; do
    meta="$ROUNDS_ROOT/round-$rn/round-meta.json"
    jq -r '.collector // ""' "$meta" 2>/dev/null | awk -f "$collector_awk" 2>/dev/null || true
done <"$rounds_list" >>"$fail_raw"

fail_total=0
fail_file="$WORK_DIR/fail.txt"
: >"$fail_file"
if [ -s "$fail_raw" ]; then
    fail_awk="$WORK_DIR/fail.awk"
    cat >"$fail_awk" <<'AWK'
FILENAME==mapfile { m[$1]=$2; next }
{
    tool=$1; bn=$2
    if (bn in m) {
        va=m[bn]
    } else {
        va=derive(bn)
        if (tool != "") { slash=index(va, "/"); va=tool substr(va, slash) }
    }
    cnt[va]++
}
END { for (k in cnt) printf "%d\t%s\n", cnt[k], k }
AWK
    awk -F'\t' -v mapfile="$slot_map" -f "$derive_awk" -f "$fail_awk" "$slot_map" "$fail_raw" 2>/dev/null \
        | sort -k1,1nr -k2,2 >"$fail_file" || : >"$fail_file"
    fail_total="$(wc -l <"$fail_raw" | tr -d ' ')"
    case "$fail_total" in ''|*[!0-9]*) fail_total=0 ;; esac
fi

# ---- render the section ----
out="$WORK_DIR/section.md"
{
    printf '## Review Phase Detail\n\n'
    printf '| Round | Suggestions | Accepted | OOS proposed | OOS accepted | Time | Cost | Reviewers |\n'
    printf '|--:|--:|--:|--:|--:|:--|:--|--:|\n'
    cat "$rows_file"
    printf '| **Total** | **%s** | **%s** | **%s** | **%s** | **%s** | — | **%s** |\n' \
        "$t_sug" "$t_acc" "$t_oosp" "$t_oosa" "$total_time" "$t_rev"
    printf '\n'

    printf '**Top reviewers** (by suggestions accepted, whole run):\n'
    if [ -s "$top_file" ]; then
        i=0
        while IFS=$'\t' read -r c va; do
            i=$((i + 1))
            printf '%s. %s — %s\n' "$i" "$va" "$c"
        done <"$top_file"
    else
        printf -- '- (no accepted suggestions attributed to a reviewer slot)\n'
    fi
    printf '\n'

    printf '**Reviewer slot failures**: %s\n' "$fail_total"
    if [ -s "$fail_file" ]; then
        while IFS=$'\t' read -r c va; do
            printf -- '- %s: %s\n' "$va" "$c"
        done <"$fail_file"
    fi
    printf '\n'

    printf '_Per-round and per-phase cost is not separately instrumented; see the **Cost** line above for the run total._\n'
} >"$out"

if [ -n "$OUTPUT" ]; then
    cp "$out" "$OUTPUT"
else
    cat "$out"
fi
exit 0
