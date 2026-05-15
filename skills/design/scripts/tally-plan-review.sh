#!/usr/bin/env bash
# Tally /design plan-review votes and render design-local artifacts.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

DESIGN_TMPDIR=""
BALLOT_FILE=""
VOTER_FILES=()
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"

usage() {
    cat >&2 <<'USAGE'
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

# vote_for_id: returns YES, NO, EXONERATE, or NEUTRAL.
# Matches the anchored pattern "FINDING_N: YES" or "OOS_N: YES" at line start.
vote_for_id() {
    local id="$1" file="$2"
    awk -v id="$id" '
      BEGIN { result="NEUTRAL" }
      {
        line=$0
        upper=toupper(line)
        # Require anchored "ID:" prefix to avoid substring collisions
        # e.g. FINDING_10 matching inside FINDING_100.
        if (upper ~ ("^" toupper(id) ":")) {
          if (upper ~ /YES/) result="YES"
          else if (upper ~ /EXONERATE/) result="EXONERATE"
          else if (upper ~ /NO/) result="NO"
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

# is_security_block: returns 0 (true) when the block has at least one
# unfenced occurrence of the canonical "focus-area = security" token.
# Fenced occurrences (inside backtick or triple-backtick regions) are
# excluded per the Match discrimination (false-positive guard) contract.
is_security_block() {
    local block="$1"
    python3 - "$block" <<'PYEOF'
import re, sys
text = open(sys.argv[1]).read()
# Strip triple-backtick fenced code regions.
text_no_fence = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
# Strip inline backtick code spans.
text_no_backtick = re.sub(r'`[^`\n]*`', '', text_no_fence)
pattern = re.compile(r'focus-area\s*=\s*security', re.IGNORECASE)
sys.exit(0 if pattern.search(text_no_backtick) else 1)
PYEOF
}

# accept_finding: returns 0 (accept) or 1 (do not accept).
# Threshold: 2+ YES for 3+ eligible voters; unanimous YES (2/2) for exactly
# 2 eligible voters; skip (do not accept) if fewer than 2 eligible voters.
accept_finding() {
    local yes="$1" no="$2" exonerate="$3" eligible="$4"
    if (( eligible < 2 )); then
        return 1
    elif (( eligible == 2 )); then
        # Unanimous: both must be YES.
        (( yes == 2 )) && return 0 || return 1
    else
        # 3+ voters: require 2+ YES.
        (( yes >= 2 )) && return 0 || return 1
    fi
}

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
