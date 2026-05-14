#!/usr/bin/env bash
# Tally /design plan-review votes and render design-local artifacts.

set -euo pipefail

DESIGN_TMPDIR=""
BALLOT_FILE=""
VOTER_FILES=()

usage() {
    cat >&2 <<'USAGE'
usage: tally-plan-review.sh --ballot-file FILE --voter-files FILE... --design-tmpdir DIR
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
            echo "tally-plan-review.sh: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" || -z "$BALLOT_FILE" || "${#VOTER_FILES[@]}" -eq 0 ]]; then
    echo "tally-plan-review.sh: --design-tmpdir, --ballot-file, and --voter-files are required" >&2
    usage
    exit 2
fi
if [[ ! -r "$BALLOT_FILE" ]]; then
    echo "tally-plan-review.sh: ballot file is missing or unreadable: $BALLOT_FILE" >&2
    exit 2
fi
for voter_file in "${VOTER_FILES[@]}"; do
    if [[ ! -r "$voter_file" ]]; then
        echo "tally-plan-review.sh: voter file is missing or unreadable: $voter_file" >&2
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
mkdir -p "$BLOCK_DIR"

awk -v dir="$BLOCK_DIR" '
  /^### (FINDING_[0-9]+|OOS_[0-9]+):/ {
    id=$2
    sub(/:$/, "", id)
    out=dir "/" id ".md"
    print > out
    next
  }
  out != "" { print >> out }
' "$BALLOT_FILE"

shopt -s nullglob
block_files=("$BLOCK_DIR"/*.md)
shopt -u nullglob

accepted_plan="$DESIGN_TMPDIR/accepted-plan-findings.md"
rejected_plan="$DESIGN_TMPDIR/rejected-findings.md"
oos_file="$DESIGN_TMPDIR/oos.md"
oos_accepted="$DESIGN_TMPDIR/oos-accepted-design.md"
tally_file="$DESIGN_TMPDIR/voting-tally.md"
: > "$accepted_plan"
: > "$rejected_plan"
: > "$oos_file"
: > "$oos_accepted"

score_rows="$WORKDIR/score-rows.tsv"
: > "$score_rows"

vote_for_id() {
    local id="$1" file="$2"
    awk -v id="$id" '
      BEGIN { result="NEUTRAL" }
      {
        line=toupper($0)
        if (index(line, id) > 0) {
          if (line ~ /(^|[^A-Z])YES([^A-Z]|$)|ACCEPT/) result="YES"
          else if (line ~ /(^|[^A-Z])NO([^A-Z]|$)|REJECT/) result="NO"
        }
      }
      END { print result }
    ' "$file"
}

reviewer_for_block() {
    local block="$1" reviewer
    reviewer=$(awk -F: '
      /Reviewer/ {
        sub(/^[[:space:]-]*/, "", $1)
        $1=""
        sub(/^:[[:space:]]*/, "", $0)
        gsub(/\*/, "", $0)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
        print $0
        exit
      }
    ' "$block")
    [[ -n "$reviewer" ]] || reviewer="unknown"
    printf '%s' "$reviewer"
}

{
    printf '# Plan Review Voting Tally\n\n'
    printf '## Findings\n\n'
    printf '| Item | YES | NO | Neutral | Result |\n'
    printf '|---|---:|---:|---:|---|\n'

    for block in "${block_files[@]+"${block_files[@]}"}"; do
        id=$(basename "$block" .md)
        yes=0
        no=0
        neutral=0
        for voter_file in "${VOTER_FILES[@]}"; do
            vote=$(vote_for_id "$id" "$voter_file")
            case "$vote" in
                YES) yes=$((yes + 1)) ;;
                NO) no=$((no + 1)) ;;
                *) neutral=$((neutral + 1)) ;;
            esac
        done

        result="rejected"
        if (( yes > no )); then
            result="accepted"
        elif (( yes == no )); then
            result="neutral"
        fi
        printf '| %s | %s | %s | %s | %s |\n' "$id" "$yes" "$no" "$neutral" "$result"

        reviewer=$(reviewer_for_block "$block")
        kind="finding"
        case "$id" in OOS_*) kind="oos" ;; esac
        printf '%s\t%s\t%s\n' "$reviewer" "$kind" "$result" >> "$score_rows"

        security=false
        if grep -Eiq 'focus-area[[:space:]]*=[[:space:]]*security' "$block"; then
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
                :
            else
                cat "$block" >> "$oos_file"
                printf '\nVote tally: YES=%s NO=%s NEUTRAL=%s\n\n' "$yes" "$no" "$neutral" >> "$oos_file"
                if [[ "$result" == "accepted" ]]; then
                    cat "$block" >> "$oos_accepted"
                    printf '\n' >> "$oos_accepted"
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
          else if (result == "neutral") neutral[reviewer]++
          else rejected[reviewer]++
        } else {
          oos_proposed[reviewer]++
          if (result == "accepted") oos_accepted[reviewer]++
        }
      }
      END {
        for (reviewer in seen) {
          score=(accepted[reviewer] * 2) + oos_accepted[reviewer] - rejected[reviewer]
          printf "| %s | %d | %d | %d | %d | %d | %d | %d |\n",
            reviewer, proposed[reviewer]+0, accepted[reviewer]+0, neutral[reviewer]+0,
            rejected[reviewer]+0, oos_proposed[reviewer]+0, oos_accepted[reviewer]+0, score
        }
      }
    ' "$score_rows" | sort
} > "$tally_file"

printf 'TALLY_PLAN_REVIEW_STATUS=ok\n'
printf 'VOTING_TALLY_FILE=%s\n' "$tally_file"
