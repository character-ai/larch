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
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: tally-plan-review.sh --ballot-file FILE --voter-files FILE... --design-tmpdir DIR [--session-env-path FILE]
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
        --session-env-path)
            SESSION_ENV_PATH="${2:?--session-env-path requires a value}"
            shift 2
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

if [[ -z "$DESIGN_TMPDIR" || -z "$BALLOT_FILE" || "${#VOTER_FILES[@]}" -eq 0 ]]; then
    larch_err "tally-plan-review.sh: --design-tmpdir, --ballot-file, and --voter-files are required"
    usage
    exit 2
fi
if [[ ! -r "$BALLOT_FILE" ]]; then
    larch_err "tally-plan-review.sh: ballot file is missing or unreadable: $BALLOT_FILE"
    exit 2
fi
for voter_file in "${VOTER_FILES[@]}"; do
    if [[ ! -r "$voter_file" ]]; then
        larch_err "tally-plan-review.sh: voter file is missing or unreadable: $voter_file"
        exit 2
    fi
done
mkdir -p "$DESIGN_TMPDIR"

WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/larch-tally-plan-review.XXXXXX")
cleanup() {
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

BLOCK_DIR="$WORKDIR/blocks"
split_ballot_to_blocks "$BALLOT_FILE" "$BLOCK_DIR"

shopt -s nullglob
block_files=("$BLOCK_DIR"/*.md)
shopt -u nullglob

accepted_plan="$DESIGN_TMPDIR/accepted-plan-findings.md"
rejected_plan="$DESIGN_TMPDIR/rejected-findings.md"
oos_file="$DESIGN_TMPDIR/oos.md"
oos_accepted_local="$DESIGN_TMPDIR/oos-accepted-design.md"
# When nested under /implement, write accepted non-security OOS to the parent
# tmpdir so ship-pr.sh / Step 9a.1 finds it at $IMPLEMENT_TMPDIR/oos-accepted-design.md.
if [[ -n "$SESSION_ENV_PATH" ]]; then
    oos_accepted_out="$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md"
else
    oos_accepted_out="$oos_accepted_local"
fi
tally_file="$DESIGN_TMPDIR/voting-tally.md"
: > "$accepted_plan"
: > "$rejected_plan"
: > "$oos_file"
: > "$oos_accepted_local"
# Initialize the parent-dir output (may differ from local).
[[ "$oos_accepted_out" != "$oos_accepted_local" ]] && : > "$oos_accepted_out"

score_rows="$WORKDIR/score-rows.tsv"
: > "$score_rows"

# Eligible voter count — used for threshold enforcement.
eligible_count="${#VOTER_FILES[@]}"

# vote_for_id, reviewer_for_block, is_security_block, accept_finding are
# sourced from $PLUGIN_ROOT/scripts/lib-vote-tally.sh above.

{
    printf '# Plan Review Voting Tally\n\n'
    printf '## Findings\n\n'
    printf '| Item | YES | NO | Exon | Neutral | Result |\n'
    printf '|---|---:|---:|---:|---:|---|\n'

    for block in "${block_files[@]+"${block_files[@]}"}"; do
        id=$(basename "$block" .md)
        yes=0
        no=0
        exonerate=0
        neutral=0
        for voter_file in "${VOTER_FILES[@]}"; do
            vote=$(vote_for_id "$id" "$voter_file")
            case "$vote" in
                YES) yes=$((yes + 1)) ;;
                NO) no=$((no + 1)) ;;
                EXONERATE) exonerate=$((exonerate + 1)) ;;
                *) neutral=$((neutral + 1)) ;;
            esac
        done

        # Eligible voters are those that cast YES, NO, or EXONERATE (not absent/NEUTRAL).
        effective_eligible=$(( yes + no + exonerate ))
        # Use the smaller of eligible_count and the actually-responding count.
        use_eligible="$eligible_count"
        (( effective_eligible < use_eligible )) && use_eligible="$effective_eligible"

        result="rejected"
        if accept_finding "$yes" "$no" "$exonerate" "$use_eligible"; then
            result="accepted"
        elif (( yes > 0 && yes == no )); then
            result="neutral"
        elif (( yes > 0 && exonerate > 0 && no == 0 )); then
            result="exonerated"
        fi
        printf '| %s | %s | %s | %s | %s | %s |\n' "$id" "$yes" "$no" "$exonerate" "$neutral" "$result"

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
                cat "$block" >> "$accepted_plan"
                printf '\n' >> "$accepted_plan"
            else
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
                printf '\nVote tally: YES=%s NO=%s NEUTRAL=%s\n\n' "$yes" "$no" "$neutral" >> "$oos_file"
                if [[ "$result" == "accepted" ]]; then
                    cat "$block" >> "$oos_accepted_local"
                    printf '\n' >> "$oos_accepted_local"
                    if [[ "$oos_accepted_out" != "$oos_accepted_local" ]]; then
                        cat "$block" >> "$oos_accepted_out"
                        printf '\n' >> "$oos_accepted_out"
                    fi
                fi
            fi
        fi
    done

    printf '\n## Reviewer Competition Scoreboard\n\n'
    printf '| Reviewer | Proposed | Accepted | Neutral/Exon | Rejected | OOS-Proposed | OOS-Accepted | Score |\n'
    printf '|---|---:|---:|---:|---:|---:|---:|---:|\n'
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
        }
      }
      END {
        for (reviewer in seen) {
          # Score: +1 per accepted in-scope, +1 per accepted OOS, -1 per rejected.
          score=accepted[reviewer]+0 + oos_accepted[reviewer]+0 - rejected[reviewer]+0
          printf "| %s | %d | %d | %d | %d | %d | %d | %d |\n",
            reviewer, proposed[reviewer]+0, accepted[reviewer]+0, neutral[reviewer]+0,
            rejected[reviewer]+0, oos_proposed[reviewer]+0, oos_accepted[reviewer]+0, score
        }
      }
    ' "$score_rows" | sort
} > "$tally_file"

emit_kv TALLY_PLAN_REVIEW_STATUS ok
emit_kv VOTING_TALLY_FILE "$tally_file"
