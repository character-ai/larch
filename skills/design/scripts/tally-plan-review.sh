#!/usr/bin/env bash
# Tally /design plan-review votes and render design-local artifacts.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=skills/design/scripts/lib-findings-classification.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-findings-classification.sh"
# shellcheck source=scripts/lib-vote-tally.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-vote-tally.sh"

DESIGN_TMPDIR=""
BALLOT_FILE=""
FINDINGS_CLASSIFICATION_OUT=""
VOTER_FILES=()
VOTER_SPECS=()
SEEN_VOTER=false
SEEN_VOTER_FILES=false
_tally_status_emitted=false
WORKDIR=""

cleanup() {
    local rc=$?
    set +e
    if [[ -n "${WORKDIR:-}" ]]; then
        rm -rf "$WORKDIR" || true
    fi
    if [[ "$_tally_status_emitted" == false && "$rc" -ne 0 ]]; then
        if [[ -n "${tally_file:-}" && -s "${tally_file:-}" ]]; then
            emit_kv VOTING_TALLY_FILE "$tally_file"
        fi
        emit_kv TALLY_PLAN_REVIEW_STATUS tally-error
    fi
    return "$rc"
}
trap cleanup EXIT

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: tally-plan-review.sh --ballot-file FILE [--voter SLOT:FILE...|POS:TOOL:FILE...] [--voter-files FILE...] --design-tmpdir DIR [--findings-classification-out FILE]
USAGE
}

valid_voter_slot() {
    case "$1" in
        1|2|3|Claude|Codex|Cursor|MainAgent) return 0 ;;
        *) return 1 ;;
    esac
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"
            shift 2
            ;;
        --ballot-file)
            BALLOT_FILE="${2:?--ballot-file requires a value}"
            shift 2
            ;;
        --findings-classification-out)
            FINDINGS_CLASSIFICATION_OUT="${2:?--findings-classification-out requires a value}"
            shift 2
            ;;
        --voter)
            SEEN_VOTER=true
            VOTER_SPECS+=("${2:?--voter requires SLOT:PATH}")
            shift 2
            ;;
        --voter-files)
            SEEN_VOTER_FILES=true
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                VOTER_FILES+=("$1")
                shift
            done
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            larch_err "tally-plan-review.sh: unknown argument: $1"
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" || -z "$BALLOT_FILE" ]]; then
    larch_err "tally-plan-review.sh: --design-tmpdir and --ballot-file are required"
    usage
    exit 2
fi

if [[ -z "$FINDINGS_CLASSIFICATION_OUT" ]]; then
    FINDINGS_CLASSIFICATION_OUT="$DESIGN_TMPDIR/plan-review/round-1/findings-classification.tsv"
fi

mkdir -p "$DESIGN_TMPDIR"
tally_file="$DESIGN_TMPDIR/voting-tally.md"
write_tally_stub() {
    {
        printf '# Plan Review Voting Tally\n\n'
        printf '%s\n' "$1"
    } > "$tally_file"
}

write_findings_classification_stub() {
    mkdir -p "$(dirname "$FINDINGS_CLASSIFICATION_OUT")"
    emit_findings_classification_header > "$FINDINGS_CLASSIFICATION_OUT"
}

tally_error_exit() {
    local stderr_message="$1" stub_message="${2:-}" write_classification_stub="${3:-true}"
    larch_err "$stderr_message"
    if [[ -n "$stub_message" ]]; then
        write_tally_stub "$stub_message"
    fi
    if [[ "$write_classification_stub" == true ]]; then
        write_findings_classification_stub
    fi
    _tally_status_emitted=true
    [[ -s "$tally_file" ]] && emit_kv VOTING_TALLY_FILE "$tally_file"
    emit_kv TALLY_PLAN_REVIEW_STATUS tally-error
    exit 2
}

if [[ "$SEEN_VOTER" == true && "$SEEN_VOTER_FILES" == true ]]; then
    tally_error_exit \
        "error: --voter and --voter-files are mutually exclusive" \
        "**⚠ Tally aborted: --voter and --voter-files are mutually exclusive; no votes tallied.**" \
        false
fi

if [[ ! -r "$BALLOT_FILE" ]]; then
    tally_error_exit \
        "tally-plan-review.sh: ballot file is missing or unreadable: $BALLOT_FILE" \
        "**⚠ Tally aborted: ballot file unreadable: $BALLOT_FILE; no votes tallied.**"
fi

declare -a SLOT_FILE SLOT_TOOL
SLOT_FILE[1]=""; SLOT_FILE[2]=""; SLOT_FILE[3]=""
SLOT_TOOL[1]=""; SLOT_TOOL[2]=""; SLOT_TOOL[3]=""
MAIN_AGENT_VOTER=""
TALLY_VOTER_FILE=""
TALLY_ELIGIBLE_COUNT=0

infer_voter_slot() {
    local path="$1" index="$2" base lower
    base=$(basename "$path")
    lower=$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')
    case "$lower" in
        *claude*) printf 'Claude' ;;
        *codex*) printf 'Codex' ;;
        *cursor*) printf 'Cursor' ;;
        *)
            case "$index" in
                1) printf 'Claude' ;;
                2) printf 'Codex' ;;
                *) printf 'Cursor' ;;
            esac
            ;;
    esac
}

canonical_position_for_slot() {
    case "$1" in
        1|Claude) printf '1' ;;
        2|Codex) printf '2' ;;
        3|Cursor) printf '3' ;;
        *) printf '0' ;;
    esac
}

canonical_tool_for_slot() {
    case "$1" in
        Claude) printf 'Claude' ;;
        Codex) printf 'Codex' ;;
        Cursor) printf 'Cursor' ;;
        1) printf 'Claude' ;;
        2) printf 'Codex' ;;
        3) printf 'Cursor' ;;
        *) printf '%s' "$1" ;;
    esac
}

position_for_voter() {
    local tool="$1" path="$2" base lower
    base=$(basename "$path")
    lower=$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')
    case "$lower" in
        *voter-1*|*voter1*|*slot1*|*slot-1*|*claude-vote-output*) printf '1'; return ;;
        *voter-2*|*voter2*|*slot2*|*slot-2*|*codex-vote-output*) printf '2'; return ;;
        *voter-3*|*voter3*|*slot3*|*slot-3*|*cursor-vote-output*) printf '3'; return ;;
    esac
    case "$tool" in
        Claude)
            [[ -z "${SLOT_FILE[1]}" ]] && { printf '1'; return; }
            ;;
        Codex)
            [[ -z "${SLOT_FILE[2]}" ]] && { printf '2'; return; }
            ;;
        Cursor)
            [[ -z "${SLOT_FILE[3]}" ]] && { printf '3'; return; }
            ;;
    esac
    for _p in 1 2 3; do
        [[ -z "${SLOT_FILE[$_p]}" ]] && { printf '%s' "$_p"; return; }
    done
    printf '0'
}

assign_voter() {
    local tool="$1" path="$2" pos="${3:-}"
    if [[ "$tool" == "MainAgent" ]]; then
        MAIN_AGENT_VOTER="$path"
        return 0
    fi
    if [[ -z "$pos" ]]; then
        pos=$(position_for_voter "$tool" "$path")
    fi
    if [[ "$pos" == "0" ]]; then
        tally_error_exit \
            "tally-plan-review.sh: too many voters; expected at most three non-MainAgent voters" \
            "**⚠ Tally aborted: too many voters; at most three non-MainAgent voters allowed.**"
    fi
    if [[ -n "${SLOT_FILE[$pos]}" ]]; then
        tally_error_exit \
            "error: duplicate voter position $pos" \
            "**⚠ Tally aborted: duplicate voter position $pos.**"
    fi
    SLOT_FILE[pos]="$path"
    SLOT_TOOL[pos]="$tool"
}

tally_votes_for_id() {
    local id="$1"
    TALLY_YES=0
    TALLY_NO=0
    TALLY_EXONERATE=0
    TALLY_JUDGE_ERROR=0
    if [[ -n "$TALLY_VOTER_FILE" ]]; then
        TALLY_VOTE=$(vote_for_id "$id" "$TALLY_VOTER_FILE")
        case "$TALLY_VOTE" in
            YES) TALLY_YES=1 ;;
            NO) TALLY_NO=1 ;;
            EXONERATE) TALLY_EXONERATE=1 ;;
            *) TALLY_JUDGE_ERROR=1 ;;
        esac
    elif (( TALLY_ELIGIBLE_COUNT > 0 )); then
        for p in 1 2 3; do
            voter_file="${SLOT_FILE[$p]}"
            [[ -n "$voter_file" ]] || continue
            TALLY_VOTE=$(vote_for_id "$id" "$voter_file")
            case "$TALLY_VOTE" in
                YES) TALLY_YES=$((TALLY_YES + 1)) ;;
                NO) TALLY_NO=$((TALLY_NO + 1)) ;;
                EXONERATE) TALLY_EXONERATE=$((TALLY_EXONERATE + 1)) ;;
                *) TALLY_JUDGE_ERROR=$((TALLY_JUDGE_ERROR + 1)) ;;
            esac
        done
    fi
    TALLY_RESULT=$(classify_result "$TALLY_YES" "$TALLY_NO" "$TALLY_EXONERATE" "$TALLY_ELIGIBLE_COUNT")
}

if [[ "$SEEN_VOTER" == true ]]; then
    for spec in "${VOTER_SPECS[@]}"; do
        if [[ "$spec" != *:* ]]; then
            tally_error_exit \
                "error: invalid voter slot: $spec (must be 1|2|3|Claude|Codex|Cursor|MainAgent)" \
                "**⚠ Tally aborted: invalid voter slot: $spec; no votes tallied.**" \
                false
        fi
        slot=""
        tool=""
        path=""
        if [[ "$spec" =~ ^([123]):([^:]+):(.*)$ ]]; then
            slot="${BASH_REMATCH[1]}"
            tool="${BASH_REMATCH[2]}"
            path="${BASH_REMATCH[3]}"
        else
            slot="${spec%%:*}"
            path="${spec#*:}"
            tool="$(canonical_tool_for_slot "$slot")"
        fi
        if ! valid_voter_slot "$slot"; then
            tally_error_exit \
                "error: invalid voter slot: $slot (must be 1|2|3|Claude|Codex|Cursor|MainAgent)" \
                "**⚠ Tally aborted: invalid voter slot: $slot; no votes tallied.**" \
                false
        fi
        VOTER_FILES+=("$path")
        if [[ "$slot" == "MainAgent" ]]; then
            assign_voter "$slot" "$path"
            continue
        fi
        assign_voter "$tool" "$path" "$(canonical_position_for_slot "$slot")"
    done
else
    if [[ "$SEEN_VOTER_FILES" == true ]]; then
        larch_err "deprecated: --voter-files; use --voter <SLOT>:<PATH>"
    fi
    _idx=0
    for path in "${VOTER_FILES[@]+"${VOTER_FILES[@]}"}"; do
        _idx=$((_idx + 1))
        assign_voter "$(infer_voter_slot "$path" "$_idx")" "$path"
    done
fi

if [[ -n "$MAIN_AGENT_VOTER" ]]; then
    non_main=0
    for _p in 1 2 3; do
        [[ -n "${SLOT_FILE[$_p]}" ]] && non_main=$((non_main + 1))
    done
    if (( non_main > 0 || ${#VOTER_SPECS[@]} > 1 )); then
        tally_error_exit \
            "error: --voter MainAgent is only valid as the sole voter (0-judge fallback path)" \
            "**⚠ Tally aborted: --voter MainAgent is only valid as the sole voter; no votes tallied.**"
    fi
fi

if [[ -n "$MAIN_AGENT_VOTER" ]]; then
    TALLY_VOTER_FILE="$MAIN_AGENT_VOTER"
    TALLY_ELIGIBLE_COUNT=1
else
    for _p in 1 2 3; do
        [[ -n "${SLOT_FILE[$_p]}" ]] && TALLY_ELIGIBLE_COUNT=$((TALLY_ELIGIBLE_COUNT + 1))
    done
fi

for voter_file in "${VOTER_FILES[@]+"${VOTER_FILES[@]}"}"; do
    if [[ ! -r "$voter_file" ]]; then
        tally_error_exit \
            "tally-plan-review.sh: voter file is missing or unreadable: $voter_file" \
            "**⚠ Tally aborted: voter file unreadable: $voter_file; no votes tallied.**"
    fi
done

WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/larch-tally-plan-review.XXXXXX")

BLOCK_DIR="$WORKDIR/blocks"
if ! split_ballot_to_blocks "$BALLOT_FILE" "$BLOCK_DIR"; then
    tally_error_exit \
        "tally-plan-review.sh: duplicate or malformed FINDING/OOS headings in ballot" \
        "**⚠ Tally aborted: duplicate or malformed FINDING/OOS headings in ballot; no votes tallied.**"
fi

shopt -s nullglob
block_files=("$BLOCK_DIR"/*.md)
shopt -u nullglob

sorted_ids="$WORKDIR/sorted-ids.txt"
for block in "${block_files[@]+"${block_files[@]}"}"; do
    basename "$block" .md
done | awk '
  /^FINDING_[0-9]+$/ { sub(/^FINDING_/, "", $0); printf "1\t%09d\tFINDING_%d\n", $0, $0; next }
  /^OOS_[0-9]+$/ { sub(/^OOS_/, "", $0); printf "2\t%09d\tOOS_%d\n", $0, $0; next }
' | LC_ALL=C sort -t "$(printf '\t')" -k1,1n -k2,2n | cut -f3 > "$sorted_ids"

accepted_plan="$DESIGN_TMPDIR/accepted-plan-findings.md"
rejected_plan="$DESIGN_TMPDIR/rejected-findings.md"
oos_file="$DESIGN_TMPDIR/oos.md"
oos_accepted_local="$DESIGN_TMPDIR/oos-accepted-design.md"
accepted_count=0
rejected_count=0
: > "$accepted_plan"
: > "$rejected_plan"
: > "$oos_file"
: > "$oos_accepted_local"

score_rows="$WORKDIR/score-rows.tsv"
: > "$score_rows"

sanitize_tsv_cell() {
    local cell
    cell=$(printf '%s' "${1:-}" | tr '\t\n' '  ')
    case "$cell" in
        [=+-@]*) printf "'%s" "$cell" ;;
        *) printf '%s' "$cell" ;;
    esac
}

kv_value() {
    local key="$1"
    awk -F= -v k="$key" '$1 == k { print substr($0, length(k) + 2); found=1 } END { if (!found) print "" }'
}

parse_rating_for() {
    local voter_file="$1" id="$2" parsed
    parsed=$("$PLUGIN_ROOT/scripts/parse-judge-vote-and-rating.sh" "$voter_file" "$id" || true)
    printf '%s\n' "$parsed"
}

write_findings_classification() {
    mkdir -p "$(dirname "$FINDINGS_CLASSIFICATION_OUT")"
    local tmp id block reviewer kind result security tsv_result
    local p voter_file parsed vote correctness severity quality uncertain tool
    tmp=$(mktemp "${FINDINGS_CLASSIFICATION_OUT}.XXXXXX")
    emit_findings_classification_header > "$tmp"
    while IFS= read -r id || [[ -n "$id" ]]; do
        [[ -n "$id" ]] || continue
        block="$BLOCK_DIR/$id.md"
        reviewer=$(sanitize_tsv_cell "$(reviewer_for_block "$block")")
        tally_votes_for_id "$id"
        result="$TALLY_RESULT"
        tsv_result="$result"
        if [[ -n "$MAIN_AGENT_VOTER" ]]; then
            tsv_result="rejected"
        fi

        row=("$id" "$reviewer" "$tsv_result")
        for p in 1 2 3; do
            voter_file="${SLOT_FILE[$p]}"
            tool="${SLOT_TOOL[$p]}"
            if [[ -n "$voter_file" && "$TALLY_VOTER_FILE" != "$voter_file" && "$TALLY_ELIGIBLE_COUNT" -gt 0 ]]; then
                parsed=$(parse_rating_for "$voter_file" "$id")
                vote=$(vote_for_id "$id" "$voter_file")
                [[ "$vote" == "JUDGE_ERROR" ]] && vote=""
                correctness=$(printf '%s\n' "$parsed" | kv_value PARSED_CORRECTNESS)
                severity=$(printf '%s\n' "$parsed" | kv_value PARSED_SEVERITY)
                quality=$(printf '%s\n' "$parsed" | kv_value PARSED_QUALITY)
                uncertain=$(printf '%s\n' "$parsed" | kv_value PARSED_UNCERTAIN)
                row+=(
                    "$(sanitize_tsv_cell "$vote")"
                    "$(sanitize_tsv_cell "$correctness")"
                    "$(sanitize_tsv_cell "$severity")"
                    "$(sanitize_tsv_cell "$quality")"
                    "$(sanitize_tsv_cell "$uncertain")"
                    "$(sanitize_tsv_cell "$tool")"
                )
            else
                row+=("" "" "" "" "" "")
            fi
        done
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "${row[@]}" >> "$tmp"
    done < "$sorted_ids"
    mv -f "$tmp" "$FINDINGS_CLASSIFICATION_OUT"
}

if (( TALLY_ELIGIBLE_COUNT == 0 )); then
    printf '# Plan Review Voting Tally\n\n' > "$tally_file"
    printf '**⚠ Degraded plan-review panel: 0 judges available. Panel tier: main-agent-required.**\n\n' >> "$tally_file"
    write_findings_classification
    _tally_status_emitted=true
    emit_kv TALLY_PLAN_REVIEW_STATUS main-agent-vote-required
    emit_kv VOTING_TALLY_FILE "$tally_file"
    exit 0
fi

{
    printf '# Plan Review Voting Tally\n\n'
    if [[ -n "$MAIN_AGENT_VOTER" ]]; then
        printf '**⚠ Degraded plan-review panel: 0 judges available. Panel tier: main-agent-adjudicated.**\n\n'
    elif (( TALLY_ELIGIBLE_COUNT < 3 )); then
        tier_label="$(panel_tier "$TALLY_ELIGIBLE_COUNT")"
        printf '**⚠ Degraded plan-review panel: %s judge(s) available. Panel tier: %s.**\n\n' "$TALLY_ELIGIBLE_COUNT" "$tier_label"
    fi
    printf '## Findings\n\n'
    printf '| Item | YES | NO | Exon | JERR | Result |\n'
    printf '|---|---:|---:|---:|---:|---|\n'

    while IFS= read -r id || [[ -n "$id" ]]; do
        [[ -n "$id" ]] || continue
        block="$BLOCK_DIR/$id.md"
        tally_votes_for_id "$id"
        result="$TALLY_RESULT"
        printf '| %s | %s | %s | %s | %s | %s |\n' "$id" "$TALLY_YES" "$TALLY_NO" "$TALLY_EXONERATE" "$TALLY_JUDGE_ERROR" "$result"

        reviewer=$(reviewer_for_block "$block")
        kind="finding"
        case "$id" in OOS_*) kind="oos" ;; esac
        printf '%s\t%s\t%s\n' "$reviewer" "$kind" "$result" >> "$score_rows"

        security=false
        if is_security_block "$block" 2>/dev/null; then
            security=true
        fi

        if [[ "$kind" == "finding" ]]; then
            if [[ "$result" == "accepted" ]]; then
                accepted_count=$((accepted_count + 1))
                cat "$block" >> "$accepted_plan"
                printf '\n' >> "$accepted_plan"
            else
                rejected_count=$((rejected_count + 1))
                {
                    printf '### [Plan Review] %s\n\n' "$id"
                    cat "$block"
                    printf '\n'
                } >> "$rejected_plan"
            fi
        else
            if [[ "$result" == "accepted" && "$security" == "true" ]]; then
                :
            else
                cat "$block" >> "$oos_file"
                printf '\nVote tally: YES=%s NO=%s EXON=%s JUDGE_ERROR=%s Result=%s\n\n' "$TALLY_YES" "$TALLY_NO" "$TALLY_EXONERATE" "$TALLY_JUDGE_ERROR" "$result" >> "$oos_file"
                if [[ "$result" == "accepted" ]]; then
                    cat "$block" >> "$oos_accepted_local"
                    printf '\n' >> "$oos_accepted_local"
                fi
            fi
        fi
    done < "$sorted_ids"

    printf '\n## Reviewer Competition Scoreboard\n\n'
    printf '| Reviewer | Proposed | Accepted | Exonerated | Rejected | OOS-Proposed | OOS-Accepted | OOS-Exonerated | OOS-Rejected | Score |\n'
    printf '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    awk -F '\t' '
      {
        reviewer=$1
        kind=$2
        result=$3
        seen[reviewer]=1
        if (kind == "finding") {
          proposed[reviewer]++
          if (result == "accepted") accepted[reviewer]++
          else if (result == "neutral" || result == "exonerated") neutral[reviewer]++
          else rejected[reviewer]++
        } else {
          oos_proposed[reviewer]++
          if (result == "accepted") oos_accepted[reviewer]++
          else if (result == "neutral" || result == "exonerated") oos_neutral[reviewer]++
          else oos_rejected[reviewer]++
        }
      }
      END {
        for (reviewer in seen) {
          score=accepted[reviewer]+0 + oos_accepted[reviewer]+0 - rejected[reviewer]+0 - oos_rejected[reviewer]+0
          printf "| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d |\n",
            reviewer, proposed[reviewer]+0, accepted[reviewer]+0, neutral[reviewer]+0,
            rejected[reviewer]+0, oos_proposed[reviewer]+0, oos_accepted[reviewer]+0,
            oos_neutral[reviewer]+0, oos_rejected[reviewer]+0, score
        }
      }
    ' "$score_rows" | sort
} > "$tally_file"

write_findings_classification

_tally_status_emitted=true
emit_kv TALLY_PLAN_REVIEW_STATUS ok
emit_kv VOTING_TALLY_FILE "$tally_file"
