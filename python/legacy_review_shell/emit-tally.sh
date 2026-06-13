#!/usr/bin/env bash
# emit-tally.sh — Emit review round summaries and structured review summary.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { larch_err "Usage: emit-tally.sh --tally-file FILE --accepted-findings-file FILE --oos-file FILE --review-tmpdir DIR --round N --mode diff|description [--session-env-path FILE] [--implement-tmpdir DIR] [--scout-status STR] [--dynamic-slots N] [--static-slot-count N]"; }

TALLY_FILE=""
ACCEPTED_FINDINGS_FILE=""
OOS_FILE=""
REVIEW_TMPDIR=""
SESSION_ENV_PATH=""
ROUND="1"
MODE=""
IMPLEMENT_TMPDIR=""
SCOUT_STATUS="na"
DYNAMIC_SLOTS="0"
STATIC_SLOT_COUNT="0"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tally-file) TALLY_FILE="${2:?--tally-file requires a value}"; shift 2 ;;
        --accepted-findings-file) ACCEPTED_FINDINGS_FILE="${2:?--accepted-findings-file requires a value}"; shift 2 ;;
        --oos-file) OOS_FILE="${2:?--oos-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --round) ROUND="${2:?--round requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --implement-tmpdir) IMPLEMENT_TMPDIR="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        --scout-status) SCOUT_STATUS="${2:?--scout-status requires a value}"; shift 2 ;;
        --dynamic-slots) DYNAMIC_SLOTS="${2:?--dynamic-slots requires a value}"; shift 2 ;;
        --static-slot-count) STATIC_SLOT_COUNT="${2:?--static-slot-count requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "emit-tally.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "emit-tally.sh: --review-tmpdir is required"; exit 2; }
[[ -n "$TALLY_FILE" && -f "$TALLY_FILE" ]] || { larch_err "emit-tally.sh: --tally-file must name a file"; exit 2; }
[[ -n "$ACCEPTED_FINDINGS_FILE" && -f "$ACCEPTED_FINDINGS_FILE" ]] || { larch_err "emit-tally.sh: --accepted-findings-file must name a file"; exit 2; }
case "$DYNAMIC_SLOTS" in ''|*[!0-9]*) larch_err "emit-tally.sh: --dynamic-slots must be a non-negative integer"; exit 2 ;; esac
case "$STATIC_SLOT_COUNT" in ''|*[!0-9]*) larch_err "emit-tally.sh: --static-slot-count must be a non-negative integer"; exit 2 ;; esac
mkdir -p "$REVIEW_TMPDIR"

ROUND_SUMMARY_FILE="$REVIEW_TMPDIR/review-round-summary.md"
REVIEW_SUMMARY_FILE="$REVIEW_TMPDIR/review-summary.json"
REJECTED_FINDINGS_FILE="$REVIEW_TMPDIR/rejected-findings.md"
FULL_REJECTED_FINDINGS_FILE="$REVIEW_TMPDIR/rejected-findings-full.md"
OOS_ACCEPTED_FILE="$REVIEW_TMPDIR/oos-accepted-review.md"

count_from_tally() {
    local key="$1" value
    value=$(awk -F= -v key="$key" '$1==key { print $2; found=1; exit } END { if (!found) print "" }' "$TALLY_FILE")
    printf '%s' "$value"
}

accepted=$(count_from_tally ACCEPTED_COUNT)
rejected=$(count_from_tally REJECTED_COUNT)
neutral=$(count_from_tally NEUTRAL_COUNT)
[[ -n "$accepted" ]] || accepted=$(grep -c 'ACCEPTED=true' "$TALLY_FILE" || true)
if [[ -z "$rejected" ]]; then
    if grep -q 'REJECTED_SUBTYPE=' "$TALLY_FILE"; then
        rejected=$(grep -cE '^FINDING_[0-9]+_OUTCOME=rejected$' "$TALLY_FILE" || true)
    elif grep -q '_OUTCOME=' "$TALLY_FILE"; then
        rejected=$(grep -c '_OUTCOME=rejected$' "$TALLY_FILE" || true)
    else
        rejected=$(grep -c 'ACCEPTED=false' "$TALLY_FILE" || true)
    fi
fi

case "$accepted" in ''|*[!0-9]*) accepted=0 ;; esac
case "$rejected" in ''|*[!0-9]*) rejected=0 ;; esac
case "$neutral" in ''|*[!0-9]*) neutral=0 ;; esac
oos_accepted_count=$(count_from_tally OOS_ACCEPTED_COUNT)
case "$oos_accepted_count" in ''|*[!0-9]*) oos_accepted_count=0 ;; esac

{
    printf '# Review Round %s\n\n' "$ROUND"
    printf '%s\n' "- Mode: \`$MODE\`"
    printf '%s\n\n' "- ${accepted} accepted, ${rejected} rejected (${neutral} neutral)"
    if [[ -s "$ACCEPTED_FINDINGS_FILE" ]]; then
        printf '## Accepted Findings\n\n'
        cat "$ACCEPTED_FINDINGS_FILE"
    fi
} > "$ROUND_SUMMARY_FILE"

# Preserve the full rejected finding prose before the summary view rewrites
# rejected-findings.md to its compact ACCEPTED=false form.
if [[ -f "$REJECTED_FINDINGS_FILE" ]]; then
    cp "$REJECTED_FINDINGS_FILE" "$FULL_REJECTED_FINDINGS_FILE" 2>/dev/null || true
else
    : > "$FULL_REJECTED_FINDINGS_FILE"
fi

{
    printf '# Rejected Findings\n\n'
    if grep -q '_OUTCOME=' "$TALLY_FILE"; then
        grep -n '_OUTCOME=rejected$' "$TALLY_FILE" || true
    else
        grep -n 'ACCEPTED=false' "$TALLY_FILE" || true
    fi
} > "$REJECTED_FINDINGS_FILE"

# Collect reviewer output paths from the review tmpdir for the JSON schema.
reviewer_paths=()
while IFS= read -r f; do
    reviewer_paths+=("$f")
done < <(find "$REVIEW_TMPDIR" -maxdepth 1 -name '*-output.txt' 2>/dev/null | sort)
reviewer_paths_json=$(printf '%s\n' "${reviewer_paths[@]+"${reviewer_paths[@]}"}" | jq -R . | jq -s .)

# Emit schema matching emit-tally.md and the current dispatch-panel harness:
# schema_version 3 — accepted/rejected/neutral counts. exonerated_count retained
# as 0 for backward compatibility with consumers that read the JSON schema.
jq -n \
    --argjson round "$ROUND" \
    --argjson accepted "$accepted" \
    --argjson rejected "$rejected" \
    --argjson neutral "$neutral" \
    --argjson paths "$reviewer_paths_json" \
    --arg scout_status "$SCOUT_STATUS" \
    --argjson dynamic_slots "$DYNAMIC_SLOTS" \
    --argjson static_slot_count "$STATIC_SLOT_COUNT" \
    '{
        schema_version: 3,
        rounds_completed: $round,
        reviewer_output_paths: $paths,
        panel: {
            scout_status: $scout_status,
            static_slot_count: $static_slot_count,
            dynamic_slot_count: $dynamic_slots,
            total_slot_count: (($static_slot_count + $dynamic_slots) | floor)
        },
        finding_counts: {
            total_accepted: $accepted,
            total_rejected: $rejected,
            total_neutral: $neutral,
            total_exonerated: 0
        },
        accepted_count: $accepted,
        rejected_count: $rejected,
        neutral_count: $neutral,
        exonerated_count: 0
    }' \
    > "$REVIEW_SUMMARY_FILE"

oos_sink_count=0
if [[ -s "$OOS_ACCEPTED_FILE" ]]; then
    oos_sink_count=$(awk -f "$PLUGIN_ROOT/skills/implement/scripts/oos-non-security-block-count.awk" "$OOS_ACCEPTED_FILE" 2>/dev/null || printf '0')
    case "$oos_sink_count" in ''|*[!0-9]*) oos_sink_count=0 ;; esac
fi

if (( oos_accepted_count > 0 && oos_sink_count == oos_accepted_count )); then
    # #3550: tally-code-votes.sh already wrote normalized accepted OOS to
    # $OOS_ACCEPTED_FILE — preserve it. The Python oos serialize CLI rebuilds
    # oos.md and cannot recover scope-drift blocks (bare ### FINDING_N:
    # without [OUT_OF_SCOPE]/[OOS] tags), and the missing-oos.md truncate
    # would wipe tally output; both branches are skipped.
    :
elif (( oos_sink_count > 0 && oos_sink_count != oos_accepted_count )); then
    larch_err "emit-tally.sh: OOS_ACCEPTED_COUNT=$oos_accepted_count but accepted sink has $oos_sink_count non-security block(s); refusing destructive rebuild"
    exit 1
elif [[ -n "$OOS_FILE" && -f "$OOS_FILE" ]]; then
    if (( oos_accepted_count > 0 )); then
        larch_err "emit-tally.sh: warning: OOS_ACCEPTED_COUNT=$oos_accepted_count but accepted sink has $oos_sink_count non-security block(s); rebuilding from oos.md"
    fi
    oos_args=(--findings-file "$OOS_FILE" --output-file "$OOS_ACCEPTED_FILE")
    [[ -n "$SESSION_ENV_PATH" ]] && oos_args+=(--session-env-path "$SESSION_ENV_PATH")
    python3 "${PLUGIN_ROOT}/python/cli.py" oos serialize "${oos_args[@]}" >/dev/null
    rebuilt_count=0
    if [[ -s "$OOS_ACCEPTED_FILE" ]]; then
        rebuilt_count=$(awk -f "$PLUGIN_ROOT/skills/implement/scripts/oos-non-security-block-count.awk" "$OOS_ACCEPTED_FILE" 2>/dev/null || printf '0')
        case "$rebuilt_count" in ''|*[!0-9]*) rebuilt_count=0 ;; esac
    fi
    if (( oos_accepted_count > 0 && rebuilt_count != oos_accepted_count )); then
        larch_err "emit-tally.sh: OOS_ACCEPTED_COUNT=$oos_accepted_count but rebuild produced $rebuilt_count non-security block(s)"
        exit 1
    fi
else
    if (( oos_accepted_count > 0 )); then
        larch_err "emit-tally.sh: OOS_ACCEPTED_COUNT=$oos_accepted_count but accepted sink has no non-security blocks and oos.md is absent"
        exit 1
    fi
    : > "$OOS_ACCEPTED_FILE"
fi

if [[ -n "$SESSION_ENV_PATH" ]]; then
    parent_dir=$(dirname "$SESSION_ENV_PATH")
    cp "$ROUND_SUMMARY_FILE" "$parent_dir/review-round-summary.md" 2>/dev/null || true
    cp "$REVIEW_SUMMARY_FILE" "$parent_dir/review-summary.json" 2>/dev/null || true
    cp "$FULL_REJECTED_FINDINGS_FILE" "$parent_dir/rejected-findings-full.md" 2>/dev/null || true
fi
if [[ -n "$IMPLEMENT_TMPDIR" && -d "$IMPLEMENT_TMPDIR" ]]; then
    cp "$ROUND_SUMMARY_FILE" "$IMPLEMENT_TMPDIR/review-round-summary.md" 2>/dev/null || true
    cp "$REVIEW_SUMMARY_FILE" "$IMPLEMENT_TMPDIR/review-summary.json" 2>/dev/null || true
    cp "$FULL_REJECTED_FINDINGS_FILE" "$IMPLEMENT_TMPDIR/rejected-findings-full.md" 2>/dev/null || true
fi

emit_kv EMIT_OK true
emit_kv ROUND_SUMMARY_FILE "$ROUND_SUMMARY_FILE"
emit_kv REVIEW_SUMMARY_FILE "$REVIEW_SUMMARY_FILE"
