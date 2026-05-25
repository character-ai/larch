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

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: tally-plan-review.sh --ballot-file FILE [--voter-files FILE...] --design-tmpdir DIR
USAGE
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
        --voter-files)
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
mkdir -p "$DESIGN_TMPDIR"
tally_file="$DESIGN_TMPDIR/voting-tally.md"
write_tally_stub() {
    {
        printf '# Plan Review Voting Tally\n\n'
        printf '%s\n' "$1"
    } > "$tally_file"
}
if [[ ! -r "$BALLOT_FILE" ]]; then
    larch_err "tally-plan-review.sh: ballot file is missing or unreadable: $BALLOT_FILE"
    write_tally_stub "**⚠ Tally aborted: ballot file unreadable: $BALLOT_FILE; no votes tallied.**"
    exit 2
fi
for voter_file in "${VOTER_FILES[@]+"${VOTER_FILES[@]}"}"; do
    if [[ ! -r "$voter_file" ]]; then
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

if (( eligible_count == 0 )); then
    printf '# Plan Review Voting Tally\n\n' > "$tally_file"
    printf '**⚠ Degraded plan-review panel: 0 judges available. Panel tier: main-agent-required.**\n\n' >> "$tally_file"
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
        yes=0
        no=0
        exonerate=0
        judge_error=0
        for voter_file in "${VOTER_FILES[@]}"; do
            vote=$(vote_for_id "$id" "$voter_file")
            case "$vote" in
                YES) yes=$((yes + 1)) ;;
                NO) no=$((no + 1)) ;;
                EXONERATE) exonerate=$((exonerate + 1)) ;;
                *) judge_error=$((judge_error + 1)) ;;
            esac
        done

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

emit_kv TALLY_PLAN_REVIEW_STATUS ok
emit_kv VOTING_TALLY_FILE "$tally_file"
