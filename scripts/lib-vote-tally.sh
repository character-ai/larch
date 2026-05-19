# shellcheck shell=bash
# lib-vote-tally.sh — Shared library for /design plan-review and /review code-review vote tally.
# Sourced-only (no shebang). Callers: skills/design/scripts/tally-plan-review.sh,
# skills/review/scripts/tally-code-votes.sh.
#
# Contract documented in scripts/lib-vote-tally.md.

# vote_for_id: prints YES | NO | EXONERATE | JUDGE_ERROR for a (id, voter_file) pair.
# Matches an anchored `<id>:` prefix and the first vote token after the colon to
# avoid substring collisions and prose tokens overriding the actual vote.
# Returns JUDGE_ERROR on missing match (parser fallback — ballot entry absent or unparseable).
vote_for_id() {
    local id="$1" file="$2"
    awk -v id="$id" '
      BEGIN { result="JUDGE_ERROR" }
      {
        line=$0
        upper=toupper(line)
        prefix="^" toupper(id) ":[[:space:]]*"
        if (upper ~ (prefix "(YES|NO|EXONERATE)([[:space:]-]|$)")) {
          rest=upper
          sub(prefix, "", rest)
          if (rest ~ /^YES([[:space:]-]|$)/) result="YES"
          else if (rest ~ /^NO([[:space:]-]|$)/) result="NO"
          else if (rest ~ /^EXONERATE([[:space:]-]|$)/) result="EXONERATE"
        }
      }
      END { print result }
    ' "$file"
}

# reviewer_for_block: extracts the reviewer attribution from a `### FINDING_N:`
# or `### OOS_N:` block file. Tolerates leading `-`/whitespace and `*` emphasis
# wrappers; tolerates both `Reviewer` and `Reviewers` (singular and plural).
reviewer_for_block() {
    local block="$1" reviewer
    reviewer=$(awk -F: '
      /^[[:space:]-]*\*\*Reviewers?\*\*:/ || /^[[:space:]-]*Reviewers?:/ {
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

# is_security_block: 0 (true) when the block has at least one UNFENCED occurrence
# of the canonical `focus-area = security` token (case-insensitive, optional
# whitespace around `=`). Occurrences inside triple-backtick or single-backtick
# regions are stripped before matching.
is_security_block() {
    local block="$1"
    python3 - "$block" <<'PYEOF'
import re, sys
text = open(sys.argv[1]).read()
text_no_fence = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
text_no_backtick = re.sub(r'`[^`\n]*`', '', text_no_fence)
pattern = re.compile(r'focus-area\s*=\s*security', re.IGNORECASE)
sys.exit(0 if pattern.search(text_no_backtick) else 1)
PYEOF
}

# accept_finding: returns 0 (accept) or 1 (reject) given counts of YES/NO/EXONERATE
# votes and the panel-level eligible voter count. The eligible count must be
# the caller's effective quorum for that tally stage, not the per-finding
# non-neutral count. For code review this means non-failed voter files after
# parse-rate-degraded narrative-only slots have been removed.
# Threshold:
#   eligible >= 3 → 2+ YES
#   eligible == 2 → unanimous YES (2/2)
#   eligible == 1 → single YES
#   eligible == 0 → reject; caller escalates to main-agent adjudication
accept_finding() {
    local yes="$1" no="$2" exonerate="$3" eligible="$4"
    : "$no" "$exonerate"
    if (( eligible <= 0 )); then
        return 1
    elif (( eligible == 1 )); then
        (( yes == 1 )) && return 0 || return 1
    elif (( eligible == 2 )); then
        (( yes == 2 )) && return 0 || return 1
    else
        (( yes >= 2 )) && return 0 || return 1
    fi
}

# split_ballot_to_blocks: splits a ballot file into per-ID block files inside
# the supplied output directory. Block file name = "<id>.md" (e.g. FINDING_1.md,
# OOS_2.md). Heading lines are kept in the block; voter-instruction prose before
# the first heading is dropped.
split_ballot_to_blocks() {
    local ballot_file="$1" out_dir="$2"
    mkdir -p "$out_dir"
    awk -v dir="$out_dir" '
      /^### (FINDING_[0-9]+|OOS_[0-9]+):/ {
        id=$2
        sub(/:$/, "", id)
        out=dir "/" id ".md"
        print > out
        next
      }
      out != "" { print >> out }
    ' "$ballot_file"
}

# classify_result: derives a per-finding result label (accepted | rejected |
# neutral | exonerated) from the vote counts. Encapsulates the secondary tie
# rules so callers do not reimplement them. Prints the result to stdout.
classify_result() {
    local yes="$1" no="$2" exonerate="$3" eligible="$4"
    if (( eligible <= 0 )); then
        printf 'rejected'
    elif (( eligible == 1 )); then
        if (( yes > 0 )); then
            printf 'accepted'
        elif (( exonerate > 0 )); then
            printf 'exonerated'
        else
            : "$no"
            printf 'rejected'
        fi
    elif accept_finding "$yes" "$no" "$exonerate" "$eligible"; then
        printf 'accepted'
    elif (( yes > 0 && yes == no )); then
        printf 'neutral'
    elif (( yes > 0 && exonerate > 0 && no == 0 )); then
        printf 'exonerated'
    else
        printf 'rejected'
    fi
}

# panel_tier: prints the human-readable policy tier for a panel-level effective
# voter count.
panel_tier() {
    local eligible="$1"
    if (( eligible >= 3 )); then
        printf 'full-3'
    elif (( eligible == 2 )); then
        printf 'unanimous-2'
    elif (( eligible == 1 )); then
        printf 'single-judge'
    else
        printf 'main-agent-required'
    fi
}
