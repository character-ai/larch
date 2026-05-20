#!/usr/bin/env bash
# test-lib-vote-tally.sh — regression harness for scripts/lib-vote-tally.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LIB="$SCRIPT_DIR/lib-vote-tally.sh"

# shellcheck source=scripts/lib-vote-tally.sh
source "$LIB"

FAIL=0
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/test-lib-vote-tally.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT

assert_eq() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" == "$want" ]]; then
        printf '  ok   %s\n' "$name"
    else
        printf '  FAIL %s — got %q want %q\n' "$name" "$got" "$want"
        FAIL=1
    fi
}

assert_exit() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" == "$want" ]]; then
        printf '  ok   %s\n' "$name"
    else
        printf '  FAIL %s — exit got %s want %s\n' "$name" "$got" "$want"
        FAIL=1
    fi
}

echo "# accept_finding threshold"
accept_finding 2 0 0 3 && got=accept || got=reject
assert_eq "3 voters, 2 YES → accept" "$got" "accept"
accept_finding 1 1 1 3 && got=accept || got=reject
assert_eq "3 voters, 1 YES → reject" "$got" "reject"
accept_finding 2 0 0 2 && got=accept || got=reject
assert_eq "2 voters, 2 YES (unanimous) → accept" "$got" "accept"
accept_finding 1 0 1 2 && got=accept || got=reject
assert_eq "2 voters, 1 YES 1 EXO → reject" "$got" "reject"
accept_finding 1 0 0 1 && got=accept || got=reject
assert_eq "1 voter, 1 YES → accept (single-judge binding)" "$got" "accept"
accept_finding 0 1 0 1 && got=accept || got=reject
assert_eq "1 voter, 1 NO → reject" "$got" "reject"
accept_finding 0 0 1 1 && got=accept || got=reject
assert_eq "1 voter, 1 EXONERATE → reject for implementation" "$got" "reject"
accept_finding 0 0 0 0 && got=accept || got=reject
assert_eq "0 voters → reject" "$got" "reject"
accept_finding 1 0 0 3 && got=accept || got=reject
assert_eq "3 available, 1 YES 2 JUDGE_ERROR → reject" "$got" "reject"
accept_finding 1 0 0 2 && got=accept || got=reject
assert_eq "2 available, 1 YES 1 JUDGE_ERROR → reject" "$got" "reject"

echo "# vote_for_id"
voter_file="$WORKDIR/voter.txt"
cat > "$voter_file" <<'EOF'
FINDING_1: YES
FINDING_2: NO — too risky
FINDING_3: EXONERATE — legit but low priority
FINDING_10: YES
EOF
got=$(vote_for_id FINDING_1 "$voter_file"); assert_eq "FINDING_1 → YES" "$got" "YES"
got=$(vote_for_id FINDING_2 "$voter_file"); assert_eq "FINDING_2 → NO" "$got" "NO"
got=$(vote_for_id FINDING_3 "$voter_file"); assert_eq "FINDING_3 → EXONERATE" "$got" "EXONERATE"
got=$(vote_for_id FINDING_10 "$voter_file"); assert_eq "FINDING_10 → YES" "$got" "YES"
got=$(vote_for_id FINDING_4 "$voter_file"); assert_eq "FINDING_4 absent → JUDGE_ERROR" "$got" "JUDGE_ERROR"
# Substring guard: FINDING_1 must not match FINDING_10's line.
cat > "$voter_file" <<'EOF'
FINDING_10: NO — only the long id
EOF
got=$(vote_for_id FINDING_1 "$voter_file"); assert_eq "FINDING_1 vs only-FINDING_10 → JUDGE_ERROR" "$got" "JUDGE_ERROR"
cat > "$voter_file" <<'EOF'
FINDING_1: NO -- yes this matters
FINDING_2: EXONERATE -- yes but minor
EOF
got=$(vote_for_id FINDING_1 "$voter_file"); assert_eq "FINDING_1 NO with yes prose → NO" "$got" "NO"
got=$(vote_for_id FINDING_2 "$voter_file"); assert_eq "FINDING_2 EXONERATE with yes prose → EXONERATE" "$got" "EXONERATE"
# Regression: voter file with zero parseable FINDING_N: lines must yield JUDGE_ERROR, never NEUTRAL.
cat > "$voter_file" <<'EOF'
This voter produced prose without any structured vote lines.
No findings were addressed.
EOF
got=$(vote_for_id FINDING_1 "$voter_file"); assert_eq "zero-parseable-lines voter → JUDGE_ERROR not NEUTRAL" "$got" "JUDGE_ERROR"

echo "# reviewer_for_block"
block="$WORKDIR/block.md"
cat > "$block" <<'EOF'
### FINDING_1: short title
- **Reviewer**: Codex-Structure
- **Concern**: something
EOF
got=$(reviewer_for_block "$block"); assert_eq "single reviewer" "$got" "Codex-Structure"
cat > "$block" <<'EOF'
### FINDING_1: short title
- **Reviewers**: Codex-Security, Cursor-Structure
EOF
got=$(reviewer_for_block "$block"); assert_eq "plural reviewers" "$got" "Codex-Security, Cursor-Structure"
cat > "$block" <<'EOF'
### FINDING_1: short title
- **Reviewer**: cursor-specialist-correctness-output.txt
EOF
got=$(reviewer_for_block "$block"); assert_eq "canonical bold reviewer filename" "$got" "cursor-specialist-correctness-output.txt"
cat > "$block" <<'EOF'
### FINDING_1: short title
- **Reviewers**: slot-a, slot-b
EOF
got=$(reviewer_for_block "$block"); assert_eq "canonical bold plural slots" "$got" "slot-a, slot-b"
cat > "$block" <<'EOF'
### FINDING_1: short title
Reviewer: codex-output.txt
EOF
got=$(reviewer_for_block "$block"); assert_eq "unbolded line-start reviewer" "$got" "codex-output.txt"
cat > "$block" <<'EOF'
### FINDING_1: short title
- **Concern**: The Reviewer parser should not treat prose as attribution.
EOF
got=$(reviewer_for_block "$block"); assert_eq "reviewer prose body → unknown" "$got" "unknown"
cat > "$block" <<'EOF'
### FINDING_1: short title
- **Concern**: Embedded sentence says Reviewer: not an attribution.
EOF
got=$(reviewer_for_block "$block"); assert_eq "embedded reviewer colon prose → unknown" "$got" "unknown"
cat > "$block" <<'EOF'
### FINDING_1: no attribution
- **Concern**: something
EOF
got=$(reviewer_for_block "$block"); assert_eq "missing reviewer → unknown" "$got" "unknown"

echo "# is_security_block"
cat > "$block" <<'EOF'
### FINDING_1: thing
- **Concern**: focus-area = security check
EOF
if is_security_block "$block"; then sec_rc=0; else sec_rc=1; fi
assert_exit "unfenced security tag" "$sec_rc" "0"

cat > "$block" <<'EOF'
### FINDING_1: thing
- **Concern**: see `focus-area = security` in the docstring
EOF
if is_security_block "$block"; then sec_rc=0; else sec_rc=1; fi
assert_exit "backtick-fenced security tag → not detected" "$sec_rc" "1"

cat > "$block" <<'BLOCK_END'
### FINDING_1: thing
```
focus-area = security
```
BLOCK_END
if is_security_block "$block"; then sec_rc=0; else sec_rc=1; fi
assert_exit "triple-backtick-fenced security tag → not detected" "$sec_rc" "1"

cat > "$block" <<'EOF'
### FINDING_1: thing
- **Concern**: focus-area=security (no spaces)
EOF
if is_security_block "$block"; then sec_rc=0; else sec_rc=1; fi
assert_exit "no-space variant → detected" "$sec_rc" "0"

echo "# split_ballot_to_blocks"
ballot="$WORKDIR/ballot.md"
cat > "$ballot" <<'EOF'
voter instructions here
ignored prose

### FINDING_1: first
- **Concern**: a

### FINDING_2: second
- **Concern**: b

### OOS_1: out-of-scope
- **Concern**: oos
EOF
blocks="$WORKDIR/blocks"
split_ballot_to_blocks "$ballot" "$blocks"
test -f "$blocks/FINDING_1.md" && got=ok || got=missing
assert_eq "FINDING_1.md split" "$got" "ok"
test -f "$blocks/FINDING_2.md" && got=ok || got=missing
assert_eq "FINDING_2.md split" "$got" "ok"
test -f "$blocks/OOS_1.md" && got=ok || got=missing
assert_eq "OOS_1.md split" "$got" "ok"
# Voter instructions before first heading must NOT be in any block.
got=$( (grep -h "voter instructions" "$blocks"/*.md 2>/dev/null || true) | wc -l | tr -d ' ')
assert_eq "voter prose excluded from blocks" "$got" "0"

echo "# classify_result"
got=$(classify_result 2 0 0 3); assert_eq "2Y/3 → accepted" "$got" "accepted"
got=$(classify_result 1 1 0 3); assert_eq "1Y/1N (3 elig) → neutral" "$got" "neutral"
got=$(classify_result 1 0 1 3); assert_eq "1Y/1E (3 elig) → exonerated" "$got" "exonerated"
got=$(classify_result 1 0 1 2); assert_eq "1Y/1E (2 elig) → exonerated" "$got" "exonerated"
got=$(classify_result 0 1 0 3); assert_eq "0Y/1N → rejected" "$got" "rejected"
got=$(classify_result 1 0 0 1); assert_eq "1Y/1 → accepted" "$got" "accepted"
got=$(classify_result 0 1 0 1); assert_eq "1N/1 → rejected" "$got" "rejected"
got=$(classify_result 0 0 1 1); assert_eq "1E/1 → exonerated" "$got" "exonerated"
got=$(classify_result 0 0 0 1); assert_eq "1 neutral abstain → rejected" "$got" "rejected"
got=$(classify_result 0 0 3 3); assert_eq "0Y/0N/3E (3 elig) → exonerated" "$got" "exonerated"
got=$(classify_result 0 1 1 3); assert_eq "0Y/1N/1E (3 elig) → exonerated" "$got" "exonerated"
got=$(classify_result 0 1 2 3); assert_eq "0Y/1N/2E (3 elig) → exonerated" "$got" "exonerated"
got=$(classify_result 0 2 1 3); assert_eq "0Y/2N/1E (3 elig, NO > EXON) → rejected" "$got" "rejected"
got=$(classify_result 1 2 3 3); assert_eq "1Y/2N/3E (3 elig) → exonerated" "$got" "exonerated"

if grep -Fq 'exonerate > 0 && (no == 0 || (exonerate >= no && exonerate > yes))' "$LIB"; then
    got=ok
else
    got=missing
fi
assert_eq "classify_result multi-voter exoneration condition pinned in lib" "$got" "ok"

echo "# panel_tier"
got=$(panel_tier 3); assert_eq "3 → full-3" "$got" "full-3"
got=$(panel_tier 2); assert_eq "2 → unanimous-2" "$got" "unanimous-2"
got=$(panel_tier 1); assert_eq "1 → single-judge" "$got" "single-judge"
got=$(panel_tier 0); assert_eq "0 → main-agent-required" "$got" "main-agent-required"

if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-lib-vote-tally.sh\n'
    exit 0
else
    printf 'FAIL: test-lib-vote-tally.sh\n'
    exit 1
fi
