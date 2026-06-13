#!/usr/bin/env bash
# render-review-phase-detail.sh — per-review-round detail section for the
# /implement final report and /design final summary (issue #3774).
#
# Reads the live/committed review-phase artifacts of an /implement run and
# renders a markdown "Review Phase Detail" section:
#   - one table row per review round (suggestions made/accepted, OOS
#     proposed/accepted, time, cost, reviewers launched)
#   - a Total row summing the whole run
#   - the top-N reviewers (vendor/archetype) by suggestions accepted
#   - a count of reviewer slots that failed, broken down by vendor/archetype
#
# The Cost column is the per-round VENDOR cost (Codex + Cursor + Claude
# subprocess): vendor token records from the token ledger are attributed to a
# round by timestamp window ([round.start_s, round.end_s]) and priced via
# python token cost. It excludes main-agent Claude, so it is strictly the vendor
# spend for that round and is therefore less than the run-total Cost line in the
# summary (which additionally includes main-agent Claude). It renders as an em
# dash when per-round timing or the token ledger is unavailable.
#
# Best-effort / observability-only: on missing inputs, missing jq, or partially
# unreadable artifacts it renders what it can (or nothing) and exits 0, so it
# can never break the final report. Usage errors exit 2.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

ROUNDS_ROOT=""
FINDINGS_FILE=""
TIMING_LEDGER=""
TOKEN_LEDGER=""
SKILL="implement"
OUTPUT=""
TOP_N=7
GANTT_ENABLED=1

usage() {
    printf '%s\n' \
        "Usage: render-review-phase-detail.sh --rounds-root DIR [--findings-file F] [--timing-ledger F] [--token-ledger F] [--skill implement|design] [--top-n N] [--no-gantt] [--output F]" >&2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --rounds-root) [ $# -ge 2 ] || { usage; exit 2; }; ROUNDS_ROOT=$2; shift 2 ;;
        --findings-file) [ $# -ge 2 ] || { usage; exit 2; }; FINDINGS_FILE=$2; shift 2 ;;
        --timing-ledger) [ $# -ge 2 ] || { usage; exit 2; }; TIMING_LEDGER=$2; shift 2 ;;
        --token-ledger) [ $# -ge 2 ] || { usage; exit 2; }; TOKEN_LEDGER=$2; shift 2 ;;
        --skill) [ $# -ge 2 ] || { usage; exit 2; }; SKILL=$2; shift 2 ;;
        --top-n) [ $# -ge 2 ] || { usage; exit 2; }; TOP_N=$2; shift 2 ;;
        --no-gantt) GANTT_ENABLED=0; shift ;;
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
[ -d "$ROUNDS_ROOT" ] && [ -r "$ROUNDS_ROOT" ] && [ -x "$ROUNDS_ROOT" ] || finalize_empty

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

if [ ! -s "$rounds_list" ]; then
    no_rounds_out="$WORK_DIR/no-rounds.md"
    {
        printf '## Review Phase Detail\n\n'
        printf 'No review rounds completed.\n'
    } >"$no_rounds_out"
    if [ -n "$OUTPUT" ]; then
        cp "$no_rounds_out" "$OUTPUT"
    else
        cat "$no_rounds_out"
    fi
    exit 0
fi

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
    core = tolower(core)
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
    if (core == "aggregator") return "aggregator"
    if (core == "scout-plan-manifest" || core ~ /^scout-plan-manifest\./) return "scout"
    if (core ~ /^(cursor|codex|claude_sub|claude)$/) return core
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

# Per-round vendor cost: window the token ledger by [start,end] (epoch), sum
# per-vendor token buckets, and price via python token cost. Prints "$N.NN" on
# success, else "—". Runs in a command substitution (subshell), so it MUST NOT
# mutate the cost accumulators — the caller parses the returned string instead.
t_cost_acc=""
any_cost=0
round_vendor_cost() {
    local start="$1" end="$2"
    [ -n "$TOKEN_LEDGER" ] && [ -f "$TOKEN_LEDGER" ] || { printf -- '—'; return; }
    [ -n "$start" ] && [ -n "$end" ] || { printf -- '—'; return; }
    local sums="$WORK_DIR/cost-sums.tsv"
    jq -r --argjson start "$start" --argjson end "$end" '
        select(.type == "vendor")
        | (try (.ts | fromdateiso8601) catch null) as $e
        | select($e != null and $e >= $start and $e <= $end)
        | [ (.vendor // ""), (.input // 0), (.cache_read // 0), (.cache_create // 0), (.output // 0) ]
        | @tsv
    ' "$TOKEN_LEDGER" 2>/dev/null \
        | awk -F'\t' '
            { cin[$1]+=$2; ccr[$1]+=$3; ccc[$1]+=$4; cout[$1]+=$5 }
            END { for (v in cin) printf "%s\t%d\t%d\t%d\t%d\n", v, cin[v], ccr[v], ccc[v], cout[v] }
        ' >"$sums" 2>/dev/null || : >"$sums"
    local cost_args=()
    local v cin ccr ccc cout
    while IFS=$'\t' read -r v cin ccr ccc cout; do
        [ -n "$v" ] || continue
        case "$v" in
            codex) cost_args+=(--codex-input-tokens "$cin" --codex-cached-input-tokens "$ccr" --codex-output-tokens "$cout") ;;
            cursor) cost_args+=(--cursor-input-tokens "$cin" --cursor-cache-read-tokens "$ccr" --cursor-output-tokens "$cout") ;;
            claude_sub) cost_args+=(--claude-sub-input-tokens "$cin" --claude-sub-cache-read-tokens "$ccr" --claude-sub-cache-write-5m-tokens "$ccc" --claude-sub-output-tokens "$cout") ;;
        esac
    done <"$sums"
    local rc_val=""
    if [ "${#cost_args[@]}" -gt 0 ]; then
        local rc_out
        rc_out="$(python3 "$SCRIPT_DIR/../python/cli.py" token cost "${cost_args[@]}" 2>/dev/null || true)"
        rc_val="$(printf '%s\n' "$rc_out" | awk -F= '$1=="TOTAL_COST"{print $2; exit}')"
    else
        rc_val="0.00"
    fi
    case "$rc_val" in
        ''|*[!0-9.]*) printf -- '—' ;;
        *) printf '$%s' "$rc_val" ;;
    esac
}

# ---- per-round rows + running totals ----
rows_file="$WORK_DIR/rows.txt"
: >"$rows_file"
round_windows_file="$WORK_DIR/round-windows.tsv"
: >"$round_windows_file"
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

    rstart=""; rend=""
    gantt_start=""; gantt_end=""
    if [ -n "$TIMING_LEDGER" ] && [ -f "$TIMING_LEDGER" ]; then
        table_rrange="$(awk -F'\t' -v r="$rn" -v SKILL="$SKILL" '
            $2=="round" && $4==SKILL && $6==r {
                if (s=="" || ($7+0) < s) s=$7+0
                if (e=="" || ($8+0) > e) e=$8+0
            }
            END { if (s != "" && e != "") printf "%d %d", s, e }
        ' "$TIMING_LEDGER" 2>/dev/null || true)"
        if [ -n "$table_rrange" ]; then
            rstart="${table_rrange%% *}"
            rend="${table_rrange##* }"
        fi
        gantt_rrange="$(awk -F'\t' -v r="$rn" '
            $2=="round" && $6==r {
                if (s=="" || ($7+0) < s) s=$7+0
                if (e=="" || ($8+0) > e) e=$8+0
            }
            END { if (s != "" && e != "") printf "%d %d", s, e }
        ' "$TIMING_LEDGER" 2>/dev/null || true)"
        if [ -n "$gantt_rrange" ]; then
            gantt_start="${gantt_rrange%% *}"
            gantt_end="${gantt_rrange##* }"
        fi
    fi
    secs=""
    if [ -n "$rstart" ] && [ -n "$rend" ] && [ "$rend" -gt "$rstart" ]; then
        secs=$((rend - rstart))
    fi
    if [ -n "$gantt_start" ] && [ -n "$gantt_end" ] && [ "$gantt_end" -gt "$gantt_start" ]; then
        printf '%s\t%s\t%s\n' "$rn" "$gantt_start" "$gantt_end" >>"$round_windows_file"
    fi

    cost_disp="$(round_vendor_cost "$rstart" "$rend")"
    # Accumulate in the parent shell (round_vendor_cost ran in a subshell).
    case "$cost_disp" in
        \$*) t_cost_acc="$t_cost_acc ${cost_disp#\$}"; any_cost=1 ;;
    esac

    t_sug=$((t_sug + sug)); t_acc=$((t_acc + acc))
    t_oosp=$((t_oosp + oosp)); t_oosa=$((t_oosa + oosa))
    t_rev=$((t_rev + rev))
    if [ -n "$secs" ]; then t_secs=$((t_secs + secs)); any_time=1; fi

    if [ -n "$secs" ]; then time_disp="$(fmt_hms "$secs")"; else time_disp="—"; fi
    printf '| %s | %s | %s | %s | %s | %s | %s | %s |\n' \
        "$rn" "$sug" "$acc" "$oosp" "$oosa" "$time_disp" "$cost_disp" "$rev" >>"$rows_file"
done <"$rounds_list"

if [ "$any_time" -eq 1 ]; then total_time="$(fmt_hms "$t_secs")"; else total_time="—"; fi
if [ "$any_cost" -eq 1 ]; then
    total_cost="\$$(printf '%s' "$t_cost_acc" | awk '{ for (i=1;i<=NF;i++) s+=$i } END { printf "%.2f", s+0 }')"
else
    total_cost="—"
fi

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
FILENAME==mapf { m[$1]=$2; next }
{
    bn=$0
    if (bn in m) va=m[bn]; else va=derive(bn)
    cnt[va]++
}
END { for (k in cnt) printf "%d\t%s\n", cnt[k], k }
AWK
        awk -F'\t' -v mapf="$slot_map" -f "$derive_awk" -f "$top_awk" "$slot_map" "$accepted_bn" 2>/dev/null \
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
FILENAME==mapf { m[$1]=$2; next }
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
    awk -F'\t' -v mapf="$slot_map" -f "$derive_awk" -f "$fail_awk" "$slot_map" "$fail_raw" 2>/dev/null \
        | sort -k1,1nr -k2,2 >"$fail_file" || : >"$fail_file"
    fail_total="$(wc -l <"$fail_raw" | tr -d ' ')"
    case "$fail_total" in ''|*[!0-9]*) fail_total=0 ;; esac
fi

fmt_mss() {
    local s="$1" m sec
    case "$s" in ''|*[!0-9]*) s=0 ;; esac
    [ "$s" -ge 0 ] || s=0
    m=$((s / 60)); sec=$((s % 60))
    printf '%d:%02d' "$m" "$sec"
}

# ---- reviewer timing charts (best-effort ASCII Gantt) ----
gantt_file="$WORK_DIR/gantt.md"
: >"$gantt_file"
if [ "$GANTT_ENABLED" -eq 1 ] && [ -n "$TIMING_LEDGER" ] && [ -f "$TIMING_LEDGER" ] && [ -s "$round_windows_file" ]; then
    gantt_awk="$WORK_DIR/gantt.awk"
    cat >"$gantt_awk" <<'AWK'
function isint(v) { return v ~ /^[0-9]+$/ }
function base(path,    n, parts) {
    n = split(path, parts, "/")
    return parts[n]
}
function label_for(out, vendor, kind,    bn, val) {
    bn = base(out)
    if (bn in m) return m[bn]
    if (bn != "" && bn != "-") {
        val = derive(bn)
        if (val ~ /^(cursor|codex|claude_sub|claude)$/ && kind != "" && kind != "-") return val "/" kind
        if (val != "" && val != "unknown/-") return val
    }
    return vendor "/" kind
}
FILENAME==mapf { m[$1]=$2; next }
$2=="vendor" && NF >= 9 && isint($8) && isint($9) {
    vs = $8 + 0
    ve = $9 + 0
    if (ve <= rstart || vs >= rend) next
    cs = (vs < rstart ? rstart : vs)
    ce = (ve > rend ? rend : ve)
    if (ce <= cs) next
    label = label_for((NF >= 11 ? $11 : ""), $6, $7)
    printf "%s\t%d\t%d\n", label, cs, ce
}
AWK
    while IFS=$'\t' read -r gw_rn gw_start gw_end; do
        case "$gw_rn" in ''|*[!0-9]*) continue ;; esac
        case "$gw_start" in ''|*[!0-9]*) continue ;; esac
        case "$gw_end" in ''|*[!0-9]*) continue ;; esac
        tasks_file="$WORK_DIR/gantt-round-$gw_rn.tsv"
        sorted_file="$WORK_DIR/gantt-round-$gw_rn-sorted.tsv"
        extraction_failed=0
        if ! awk -F'\t' -v mapf="$slot_map" -v rstart="$gw_start" -v rend="$gw_end" \
            -f "$derive_awk" -f "$gantt_awk" "$slot_map" "$TIMING_LEDGER" 2>/dev/null \
            | LC_ALL=C sort -t $'\t' -k2,2n -k3,3n -k1,1 >"$sorted_file"; then
            extraction_failed=1
            : >"$sorted_file"
        fi
        if ! head -n 25 "$sorted_file" >"$tasks_file"; then
            extraction_failed=1
            : >"$tasks_file"
        fi
        {
            printf '### Round %s reviewer timing\n\n' "$gw_rn"
            if [ -s "$tasks_file" ]; then
                chart=""
                if chart="$(python3 "$SCRIPT_DIR/../python/cli.py" gantt render \
                    --window-start-s "$gw_start" \
                    --window-end-s "$gw_end" \
                    --rows-tsv "$tasks_file" 2>/dev/null)"; then
                    if [ -n "$chart" ]; then
                        span=$((gw_end - gw_start))
                        printf '```\n'
                        printf 'Round %s reviewer timing  ·  window 0:00-%s (%ss)\n' "$gw_rn" "$(fmt_mss "$span")" "$span"
                        printf '%s\n' "$chart"
                        printf '```\n\n'
                    else
                        printf 'No reviewer timing tasks overlapped this round.\n\n'
                    fi
                else
                    printf 'Reviewer timing chart unavailable.\n\n'
                fi
            elif [ "$extraction_failed" -eq 1 ]; then
                printf 'Reviewer timing chart unavailable.\n\n'
            else
                printf 'No reviewer timing tasks overlapped this round.\n\n'
            fi
        } >>"$gantt_file"
    done <"$round_windows_file"
fi

# ---- render the section ----
out="$WORK_DIR/section.md"
{
    printf '## Review Phase Detail\n\n'
    printf '| Round | Suggestions | Accepted | OOS proposed | OOS accepted | Time | Cost | Reviewers |\n'
    printf '|--:|--:|--:|--:|--:|:--|--:|--:|\n'
    cat "$rows_file"
    printf '| **Total** | **%s** | **%s** | **%s** | **%s** | **%s** | **%s** | **%s** |\n' \
        "$t_sug" "$t_acc" "$t_oosp" "$t_oosa" "$total_time" "$total_cost" "$t_rev"
    printf '\n'

    if [ -s "$gantt_file" ]; then
        cat "$gantt_file"
    fi

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

    printf '_Cost is the per-round vendor cost (Codex + Cursor + Claude subprocess), attributed by token-ledger timestamp window; it excludes main-agent Claude, so it is less than the run Cost line above. Rendered as an em dash when per-round timing or the token ledger is unavailable._\n'
} >"$out"

if [ -n "$OUTPUT" ]; then
    cp "$out" "$OUTPUT"
else
    cat "$out"
fi
exit 0
