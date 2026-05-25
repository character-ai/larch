#!/usr/bin/env bash
# Tally /design plan-review votes and render design-local artifacts.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-vote-tally.sh
source "$PLUGIN_ROOT/scripts/lib-vote-tally.sh"

DESIGN_TMPDIR=""
BALLOT_FILE=""
VOTER_FILES=()
VOTER_SLOTS=()
FINDINGS_CLASSIFICATION_OUT=""
LEGACY_VOTER_FILES=false

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: tally-plan-review.sh --ballot-file FILE [--voter SLOT:FILE ...] [--voter-files FILE...] --design-tmpdir DIR [--findings-classification-out FILE]
USAGE
}

add_voter_slot() {
    local slot="$1" file="$2"
    case "$slot" in
        Claude|Codex|Cursor|MainAgent) ;;
        *)
            larch_err "tally-plan-review.sh: invalid --voter slot: $slot"
            exit 2
            ;;
    esac
    local existing
    for existing in "${VOTER_SLOTS[@]+"${VOTER_SLOTS[@]}"}"; do
        if [[ "$existing" == "$slot" ]]; then
            larch_err "tally-plan-review.sh: duplicate --voter slot: $slot"
            exit 2
        fi
        if [[ "$slot" == "MainAgent" || "$existing" == "MainAgent" ]]; then
            larch_err "tally-plan-review.sh: MainAgent cannot be combined with panel voter slots"
            exit 2
        fi
    done
    VOTER_SLOTS+=("$slot")
    VOTER_FILES+=("$file")
}

infer_legacy_voter_slot() {
    local file="$1" index="$2" base
    base=$(basename "$file")
    case "$base" in
        *[Cc]laude*) printf 'Claude' ;;
        *[Cc]odex*) printf 'Codex' ;;
        *[Cc]ursor*) printf 'Cursor' ;;
        *)
            case "$index" in
                0) printf 'Claude' ;;
                1) printf 'Codex' ;;
                2) printf 'Cursor' ;;
                *) printf 'MainAgent' ;;
            esac
            ;;
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
            _voter_spec="${2:?--voter requires SLOT:PATH}"
            case "$_voter_spec" in
                *:*)
                    _slot="${_voter_spec%%:*}"
                    _path="${_voter_spec#*:}"
                    ;;
                *)
                    larch_err "tally-plan-review.sh: --voter requires SLOT:PATH"
                    exit 2
                    ;;
            esac
            add_voter_slot "$_slot" "$_path"
            shift 2
            ;;
        --voter-files)
            LEGACY_VOTER_FILES=true
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                _legacy_slot=$(infer_legacy_voter_slot "$1" "${#VOTER_FILES[@]}")
                add_voter_slot "$_legacy_slot" "$1"
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
mkdir -p "$DESIGN_TMPDIR"
tally_file="$DESIGN_TMPDIR/voting-tally.md"
if [[ -z "$FINDINGS_CLASSIFICATION_OUT" ]]; then
    FINDINGS_CLASSIFICATION_OUT="$DESIGN_TMPDIR/plan-review/round-1/findings-classification.tsv"
fi
if [[ "$LEGACY_VOTER_FILES" == true ]]; then
    larch_err "tally-plan-review.sh: --voter-files is deprecated; use repeated --voter SLOT:PATH"
fi
reset_findings_classification() {
    mkdir -p "$(dirname "$FINDINGS_CLASSIFICATION_OUT")"
    findings_classification_header > "$FINDINGS_CLASSIFICATION_OUT"
}
write_tally_stub() {
    {
        printf '# Plan Review Voting Tally\n\n'
        printf '%s\n' "$1"
    } > "$tally_file"
}
reset_findings_classification
if [[ -L "$BALLOT_FILE" || ! -r "$BALLOT_FILE" ]]; then
    larch_err "tally-plan-review.sh: ballot file is missing or unreadable: $BALLOT_FILE"
    write_tally_stub "**⚠ Tally aborted: ballot file unreadable: $BALLOT_FILE; no votes tallied.**"
    exit 2
fi
for voter_file in "${VOTER_FILES[@]+"${VOTER_FILES[@]}"}"; do
    if [[ -L "$voter_file" || ! -r "$voter_file" ]]; then
        larch_err "tally-plan-review.sh: voter file is missing or unreadable: $voter_file"
        write_tally_stub "**⚠ Tally aborted: voter file unreadable: $voter_file; no votes tallied.**"
        exit 2
    fi
done

WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/larch-tally-plan-review.XXXXXX")
cleanup() {
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

BLOCK_DIR="$WORKDIR/blocks"
if ! split_ballot_to_blocks "$BALLOT_FILE" "$BLOCK_DIR"; then
    larch_err "tally-plan-review.sh: duplicate or malformed FINDING/OOS headings in ballot"
    write_tally_stub "**⚠ Tally aborted: duplicate or malformed FINDING/OOS headings in ballot; no votes tallied.**"
    exit 2
fi

shopt -s nullglob
block_files=("$BLOCK_DIR"/*.md)
shopt -u nullglob

sorted_block_list="$WORKDIR/sorted-blocks.txt"
: > "$sorted_block_list"
for block in "${block_files[@]+"${block_files[@]}"}"; do
    _id=$(basename "$block" .md)
    case "$_id" in
        FINDING_*) _kind=1; _num="${_id#FINDING_}" ;;
        OOS_*) _kind=2; _num="${_id#OOS_}" ;;
        *) _kind=9; _num=0 ;;
    esac
    printf '%s\t%s\t%s\n' "$_kind" "$_num" "$block"
done | LC_ALL=C sort -t "$(printf '\t')" -k1,1n -k2,2n | cut -f3- > "$sorted_block_list"
block_files=()
while IFS= read -r block || [[ -n "$block" ]]; do
    [[ -n "$block" ]] && block_files+=("$block")
done < "$sorted_block_list"

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

# Eligible voter count is the panel-level available voter count, not the
# per-finding non-neutral response count.
eligible_count="${#VOTER_FILES[@]}"

find_voter_file_for_slot() {
    local wanted="$1" i found=""
    for ((i = 0; i < ${#VOTER_FILES[@]}; i++)); do
        if [[ "${VOTER_SLOTS[$i]}" == "$wanted" ]]; then
            found="${VOTER_FILES[$i]}"
        fi
    done
    printf '%s' "$found"
}

sanitize_tsv_cell() {
    printf '%s' "${1:-}" | tr '\t' ' ' | tr -d '\n'
}

parse_rating_cell_values() {
    local voter_file="$1" id="$2" parsed line key value
    PARSED_VOTE=""
    PARSED_CORRECTNESS=""
    PARSED_SEVERITY=""
    PARSED_QUALITY=""
    PARSED_UNCERTAIN=""
    [[ -n "$voter_file" ]] || return 0
    parsed=$("$PLUGIN_ROOT/scripts/parse-judge-vote-and-rating.sh" "$voter_file" "$id" || true)
    while IFS= read -r line || [[ -n "$line" ]]; do
        key="${line%%=*}"
        value="${line#*=}"
        case "$key" in
            PARSED_VOTE) PARSED_VOTE="$value" ;;
            PARSED_CORRECTNESS) PARSED_CORRECTNESS="$value" ;;
            PARSED_SEVERITY) PARSED_SEVERITY="$value" ;;
            PARSED_QUALITY) PARSED_QUALITY="$value" ;;
            PARSED_UNCERTAIN) PARSED_UNCERTAIN="$value" ;;
        esac
    done <<< "$parsed"
}

count_parsed_votes_for_id() {
    local id="$1"
    shift || true
    local voter_file yes=0 no=0 exonerate=0 judge_error=0
    for voter_file in "$@"; do
        parse_rating_cell_values "$voter_file" "$id"
        case "$PARSED_VOTE" in
            YES) yes=$((yes + 1)) ;;
            NO) no=$((no + 1)) ;;
            EXONERATE) exonerate=$((exonerate + 1)) ;;
            *) judge_error=$((judge_error + 1)) ;;
        esac
    done
    printf '%s\t%s\t%s\t%s\n' "$yes" "$no" "$exonerate" "$judge_error"
}

write_findings_classification() {
    local out="$1" out_tmp id block reviewer yes no exonerate judge_error result
    local claude_file codex_file cursor_file slot slot_vote
    mkdir -p "$(dirname "$out")"
    out_tmp="${out}.tmp.$$"
    {
        findings_classification_header
        claude_file=$(find_voter_file_for_slot Claude)
        codex_file=$(find_voter_file_for_slot Codex)
        cursor_file=$(find_voter_file_for_slot Cursor)
        for block in "${block_files[@]+"${block_files[@]}"}"; do
            id=$(basename "$block" .md)
            IFS=$'\t' read -r yes no exonerate judge_error <<< "$(count_parsed_votes_for_id "$id" "${VOTER_FILES[@]+"${VOTER_FILES[@]}"}")"
            : "$judge_error"
            result=$(classify_result "$yes" "$no" "$exonerate" "$eligible_count")
            reviewer=$(sanitize_tsv_cell "$(reviewer_for_block "$block")")
            printf '%s\t%s\t%s' "$id" "$reviewer" "$result"
            for slot in "$claude_file" "$codex_file" "$cursor_file"; do
                parse_rating_cell_values "$slot" "$id"
                slot_vote="$PARSED_VOTE"
                printf '\t%s\t%s\t%s\t%s\t%s' \
                    "$(sanitize_tsv_cell "$slot_vote")" \
                    "$(sanitize_tsv_cell "$PARSED_CORRECTNESS")" \
                    "$(sanitize_tsv_cell "$PARSED_SEVERITY")" \
                    "$(sanitize_tsv_cell "$PARSED_QUALITY")" \
                    "$(sanitize_tsv_cell "$PARSED_UNCERTAIN")"
            done
            printf '\n'
        done
    } > "$out_tmp"
    mv -f "$out_tmp" "$out"
}

if (( eligible_count == 0 )); then
    printf '# Plan Review Voting Tally\n\n' > "$tally_file"
    printf '**⚠ Degraded plan-review panel: 0 judges available. Panel tier: main-agent-required.**\n\n' >> "$tally_file"
    write_findings_classification "$FINDINGS_CLASSIFICATION_OUT"
    emit_kv TALLY_PLAN_REVIEW_STATUS main-agent-vote-required
    emit_kv VOTING_TALLY_FILE "$tally_file"
    exit 0
fi

{
    printf '# Plan Review Voting Tally\n\n'
    if (( eligible_count < 3 )); then
        tier_label="$(panel_tier "$eligible_count")"
        printf '**⚠ Degraded plan-review panel: %s judge(s) available. Panel tier: %s.**\n\n' "$eligible_count" "$tier_label"
    fi
    printf '## Findings\n\n'
    printf '| Item | YES | NO | Exon | JERR | Result |\n'
    printf '|---|---:|---:|---:|---:|---|\n'

    for block in "${block_files[@]+"${block_files[@]}"}"; do
        id=$(basename "$block" .md)
        IFS=$'\t' read -r yes no exonerate judge_error <<< "$(count_parsed_votes_for_id "$id" "${VOTER_FILES[@]}")"
        result=$(classify_result "$yes" "$no" "$exonerate" "$eligible_count")
        printf '| %s | %s | %s | %s | %s | %s |\n' "$id" "$yes" "$no" "$exonerate" "$judge_error" "$result"

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
                # Security-tagged accepted OOS: held locally only, never filed publicly.
                :
            else
                cat "$block" >> "$oos_file"
                printf '\nVote tally: YES=%s NO=%s EXON=%s JUDGE_ERROR=%s Result=%s\n\n' "$yes" "$no" "$exonerate" "$judge_error" "$result" >> "$oos_file"
                if [[ "$result" == "accepted" ]]; then
                    cat "$block" >> "$oos_accepted_local"
                    printf '\n' >> "$oos_accepted_local"
                fi
            fi
        fi
    done

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
          # Score: +1 per accepted item and -1 per rejected item.
          score=accepted[reviewer]+0 + oos_accepted[reviewer]+0 - rejected[reviewer]+0 - oos_rejected[reviewer]+0
          printf "| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d |\n",
            reviewer, proposed[reviewer]+0, accepted[reviewer]+0, neutral[reviewer]+0,
            rejected[reviewer]+0, oos_proposed[reviewer]+0, oos_accepted[reviewer]+0,
            oos_neutral[reviewer]+0, oos_rejected[reviewer]+0, score
        }
      }
    ' "$score_rows" | sort
} > "$tally_file"

write_findings_classification "$FINDINGS_CLASSIFICATION_OUT"

emit_kv TALLY_PLAN_REVIEW_STATUS ok
emit_kv VOTING_TALLY_FILE "$tally_file"
