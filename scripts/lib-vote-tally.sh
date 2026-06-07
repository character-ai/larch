# shellcheck shell=bash
# lib-vote-tally.sh — Shared library for /design plan-review and /review code-review vote tally.
# Sourced-only (no shebang). Callers: skills/design/scripts/tally-plan-review.sh,
# skills/review/scripts/tally-code-votes.sh.
#
# Contract documented in scripts/lib-vote-tally.md.

# vote_for_id: prints YES | NO | JUDGE_ERROR for a (id, voter_file) pair.
# Matches an anchored `<id>:` prefix and the first vote token after the colon to
# avoid substring collisions and prose tokens overriding the actual vote.
# Stray EXONERATE tokens from old voter output are tolerated and mapped to NO.
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
          else if (rest ~ /^EXONERATE([[:space:]-]|$)/) result="NO"
        }
      }
      END { print result }
    ' "$file"
}

# reviewer_for_block: extracts the reviewer attribution from a `### FINDING_N:`
# or `### OOS_N:` block file. Matches lines anchored at the start after optional
# leading `-`/whitespace, with optional `**Reviewer**:` / `**Reviewers**:` or
# plain `Reviewer:` / `Reviewers:` labels.
reviewer_for_block() {
    local block="$1" reviewer
    reviewer=$(awk -F: '
      /^[[:space:]-]*\*\*Reviewer\(s\)\*\*:/ ||
      /^[[:space:]-]*\*\*Reviewers?\*\*:/ ||
      /^[[:space:]-]*Reviewer\(s\):/ ||
      /^[[:space:]-]*Reviewers?:/ {
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

# is_security_block: 0 (true) when the block has at least one security routing
# token outside triple-backtick fences. Prose/code examples inside inline
# backticks are ignored, while dedicated focus-area fields may backtick-wrap
# their label or value.
is_security_block() {
    local block="$1"
    command -v python3 >/dev/null 2>&1 || return 2
    python3 -c 'import re, sys' >/dev/null 2>&1 || return 2
    python3 - "$block" <<'PYEOF'
import re, sys
try:
    text = open(sys.argv[1], encoding="utf-8").read()
except OSError as exc:
    print(f"is_security_block: {exc}", file=sys.stderr)
    sys.exit(2)
text_no_fence = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
text_no_backtick = re.sub(r'`[^`\n]*`', '', text_no_fence)
canonical_token = re.compile(r'focus-area\s*=\s*security', re.IGNORECASE)
explicit_header = re.compile(
    r'^###\s+(?:OOS_\d+:|FINDING_\d+:)\s*(?:\[(?:OUT_OF_SCOPE|OOS)\]\s*)?'
    r'`?(?:\[security\]|<security>)`?(?:\s|$|[:-])',
    re.IGNORECASE,
)
field_value = re.compile(
    r'^[ \t-]*focus-area[ \t]*[:=][ \t]*security(?:[-a-z0-9 _]*)(?:[ \t]|$|\(|#|\.|,)',
    re.IGNORECASE,
)
lines = text_no_fence.splitlines()
found = bool(canonical_token.search(text_no_backtick))
if not found and lines and explicit_header.search(lines[0]):
    found = True
if not found:
    for line in lines:
        normalized = line.replace('`', '').replace('*', '').strip()
        if field_value.search(normalized):
            found = True
            break
sys.exit(0 if found else 1)
PYEOF
}


# is_scope_reduction_block: 0 (true) when the block file has a leading
# [SCOPE-REDUCTION] marker in its normalized problem field. The canonical
# detector strips fenced code, inline code, and one leading severity bracket.
is_scope_reduction_block() {
    local block="$1"
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
    "$script_dir/check-scope-reduction-marker.sh" --file "$block"
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
# the first heading is dropped. Duplicate FINDING_/OOS_ headings exit 1 (stderr).
split_ballot_to_blocks() {
    local ballot_file="$1" out_dir="$2"
    mkdir -p "$out_dir"
    awk -v dir="$out_dir" '
      /^### (FINDING_[0-9]+|OOS_[0-9]+):/ {
        id=$2
        sub(/:$/, "", id)
        if (id in seen) {
          printf("duplicate ballot heading %s\n", id) > "/dev/stderr"
          dup = 1
          exit 1
        }
        seen[id] = 1
        out=dir "/" id ".md"
        print > out
        next
      }
      out != "" { print >> out }
    ' "$ballot_file" || return 1
}

# classify_result: derives a per-finding result label (accepted | rejected |
# neutral) from the vote counts. Prints the result to stdout.
# neutral: not accepted but at least one YES vote (0 points to proposing reviewer).
# rejected: not accepted and zero YES votes (-1 point to proposing reviewer).
# The exonerate parameter is accepted for backward compatibility but is ignored;
# vote_for_id maps stray EXONERATE tokens to NO so exonerate is always 0 in practice.
classify_result() {
    local yes="$1" no="$2" exonerate="$3" eligible="$4"
    : "$no" "$exonerate"
    if (( eligible <= 0 )); then
        printf 'rejected'
    elif accept_finding "$yes" "$no" "$exonerate" "$eligible"; then
        printf 'accepted'
    elif (( yes > 0 )); then
        printf 'neutral'
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
