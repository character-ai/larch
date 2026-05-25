#!/usr/bin/env bash
# Regression harness for findings-classification.tsv emission.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
export CLAUDE_PLUGIN_ROOT="$ROOT"
TALLY="$ROOT/skills/design/scripts/tally-plan-review.sh"
PARSER="$ROOT/scripts/parse-judge-vote-and-rating.sh"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-findings-classification-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

cell() {
    local file="$1" id="$2" col="$3"
    awk -F '\t' -v id="$id" -v col="$col" '
      NR == 1 {
        for (i = 1; i <= NF; i++) {
          if ($i == col) c = i
        }
        next
      }
      $1 == id {
        print $c
        found = 1
        exit
      }
      END {
        if (!found) exit 1
      }
    ' "$file"
}

assert_cell() {
    local file="$1" id="$2" col="$3" expected="$4" actual
    actual=$(cell "$file" "$id" "$col") || fail "missing row/cell $id $col"
    [[ "$actual" == "$expected" ]] || fail "$id $col expected '$expected' got '$actual'"
}

assert_parser_cell() {
    local voter="$1" id="$2" key="$3" expected="$4" actual
    actual=$("$PARSER" "$voter" "$id" | awk -F= -v key="$key" '$1 == key { print substr($0, length(key) + 2) }')
    [[ "$actual" == "$expected" ]] || fail "$id $key expected '$expected' got '$actual'"
}

write_base_ballot() {
    local ballot="$1"
    cat > "$ballot" <<'EOF'
### FINDING_1: Parser fix
- **Reviewer**: Claude-Arch
- focus-area = correctness
- Concern: parser misses malformed input.

### FINDING_2: Partial row
- **Reviewer**: Codex-Edge
- focus-area = code-quality
- Concern: fix should be tighter.

### OOS_1: Follow-up docs
- **Reviewer**: Cursor-Pragmatic
- focus-area = documentation
- Concern: docs need follow-up.
EOF
}

run_tally() {
    "$TALLY" "$@" >/dev/null
}

echo "=== complete three-judge ratings + OOS ==="
W1="$TMPROOT/complete"
mkdir -p "$W1"
BALLOT1="$W1/ballot.md"
write_base_ballot "$BALLOT1"
CLAUDE1="$W1/claude-vote-output.txt"
CODEX1="$W1/codex-vote-output.txt"
CURSOR1="$W1/cursor-vote-output.txt"
cat > "$CLAUDE1" <<'EOF'
FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=excellent UNCERTAIN=false
FINDING_2: YES CORRECTNESS=true SEVERITY=major UNCERTAIN=false
OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false
EOF
cat > "$CODEX1" <<'EOF'
FINDING_1: YES SEVERITY=major CORRECTNESS=true QUALITY=good UNCERTAIN=false
FINDING_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=weak UNCERTAIN=false
OOS_1: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false
EOF
cat > "$CURSOR1" <<'EOF'
FINDING_1: EXONERATE CORRECTNESS=partially-true SEVERITY=minor QUALITY=adequate UNCERTAIN=false
FINDING_2: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false
OOS_1: EXONERATE CORRECTNESS=partially-true SEVERITY=minor QUALITY=adequate UNCERTAIN=false
EOF
OUT1="$W1/findings-classification.tsv"
run_tally --ballot-file "$BALLOT1" --design-tmpdir "$W1/design" --findings-classification-out "$OUT1" --voter "Claude:$CLAUDE1" --voter "Codex:$CODEX1" --voter "Cursor:$CURSOR1"
assert_cell "$OUT1" FINDING_1 voting_result accepted
assert_cell "$OUT1" FINDING_1 v1_vote YES
assert_cell "$OUT1" FINDING_1 v1_quality excellent
assert_cell "$OUT1" FINDING_1 v2_vote YES
assert_cell "$OUT1" FINDING_1 v3_vote EXONERATE
assert_cell "$OUT1" OOS_1 v3_quality adequate
assert_parser_cell "$CODEX1" FINDING_1 PARSED_CORRECTNESS true
assert_parser_cell "$CODEX1" FINDING_1 PARSED_SEVERITY major

echo "=== missing judge leaves fixed slot empty ==="
W2="$TMPROOT/missing"
mkdir -p "$W2"
run_tally --ballot-file "$BALLOT1" --design-tmpdir "$W2/design" --findings-classification-out "$W2/out.tsv" --voter "Claude:$CLAUDE1" --voter "Cursor:$CURSOR1"
assert_cell "$W2/out.tsv" FINDING_1 v1_vote YES
assert_cell "$W2/out.tsv" FINDING_1 v2_vote ""
assert_cell "$W2/out.tsv" FINDING_1 v3_vote EXONERATE

echo "=== partial row uncertainty dominates explicit false ==="
assert_cell "$OUT1" FINDING_2 v1_quality ""
assert_cell "$OUT1" FINDING_2 v1_uncertain true
assert_cell "$OUT1" FINDING_2 v1_vote YES

echo "=== zero judges writes main-agent-required rows with empty voter columns ==="
W3="$TMPROOT/zero"
mkdir -p "$W3"
zero_out=$("$TALLY" --ballot-file "$BALLOT1" --design-tmpdir "$W3/design" --findings-classification-out "$W3/out.tsv")
printf '%s\n' "$zero_out" | grep -q '^TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required$' || fail "zero-judge status missing"
assert_cell "$W3/out.tsv" FINDING_1 voting_result main-agent-vote-required
assert_cell "$W3/out.tsv" FINDING_1 v1_vote ""
assert_cell "$W3/out.tsv" OOS_1 v3_uncertain ""

echo "=== empty ballot writes header only ==="
W4="$TMPROOT/empty"
mkdir -p "$W4"
: > "$W4/empty.md"
run_tally --ballot-file "$W4/empty.md" --design-tmpdir "$W4/design" --findings-classification-out "$W4/out.tsv"
[[ "$(wc -l < "$W4/out.tsv" | tr -d ' ')" == "1" ]] || fail "empty ballot should write header only"

echo "=== rerun overwrites previous TSV ==="
run_tally --ballot-file "$BALLOT1" --design-tmpdir "$W4/design2" --findings-classification-out "$W4/rerun.tsv" --voter "Claude:$CLAUDE1"
grep -q 'YES' "$W4/rerun.tsv" || fail "first rerun fixture missing YES"
run_tally --ballot-file "$BALLOT1" --design-tmpdir "$W4/design3" --findings-classification-out "$W4/rerun.tsv"
if grep -q 'YES' "$W4/rerun.tsv"; then
    fail "second rerun did not overwrite stale voter cells"
fi

echo "=== vote_for_id still accepts trailing rating tokens ==="
vote=$(bash -c 'source "$1"; vote_for_id FINDING_1 "$2"' _ "$ROOT/scripts/lib-vote-tally.sh" "$CLAUDE1")
[[ "$vote" == "YES" ]] || fail "vote_for_id did not parse rated line"

echo "=== explicit slot metadata handles phase paths ==="
W5="$TMPROOT/phase"
mkdir -p "$W5"
PHASE_CLAUDE="$W5/claude-vote-output-phase2.txt"
PHASE_CURSOR="$W5/voter-main-agent.txt"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n' > "$PHASE_CLAUDE"
printf 'FINDING_1: NO CORRECTNESS=false-positive SEVERITY=minor QUALITY=weak UNCERTAIN=false\n' > "$PHASE_CURSOR"
run_tally --ballot-file "$BALLOT1" --design-tmpdir "$W5/design" --findings-classification-out "$W5/out.tsv" --voter "Claude:$PHASE_CLAUDE" --voter "Cursor:$PHASE_CURSOR"
assert_cell "$W5/out.tsv" FINDING_1 v1_vote YES
assert_cell "$W5/out.tsv" FINDING_1 v2_vote ""
assert_cell "$W5/out.tsv" FINDING_1 v3_vote NO

echo "=== MainAgent-only retally keeps fixed panel columns empty ==="
W5B="$TMPROOT/main-agent"
mkdir -p "$W5B"
MAIN_AGENT_BALLOT="$W5B/ballot.md"
cat > "$MAIN_AGENT_BALLOT" <<'EOF'
### FINDING_1: Main-agent
- **Reviewer**: Claude-Arch
- focus-area = correctness
EOF
MAIN_AGENT_VOTE="$W5B/voter-main-agent.txt"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n' > "$MAIN_AGENT_VOTE"
run_tally --ballot-file "$MAIN_AGENT_BALLOT" --design-tmpdir "$W5B/design" --findings-classification-out "$W5B/out.tsv" --voter "MainAgent:$MAIN_AGENT_VOTE"
assert_cell "$W5B/out.tsv" FINDING_1 voting_result accepted
assert_cell "$W5B/out.tsv" FINDING_1 v1_vote ""
assert_cell "$W5B/out.tsv" FINDING_1 v2_vote ""
assert_cell "$W5B/out.tsv" FINDING_1 v3_vote ""

echo "=== parser malformed vote, casing, duplicate ids ==="
PARSER_FIX="$TMPROOT/parser.txt"
cat > "$PARSER_FIX" <<'EOF'
FINDING_3: YES SEVERITY=MAJOR
FINDING_4: NO CORRECTNESS=false-positive SEVERITY=major QUALITY=weak UNCERTAIN=false
FINDING_4: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false
FINDING_5: MAYBE CORRECTNESS=true
EOF
assert_parser_cell "$PARSER_FIX" FINDING_5 PARSED_VOTE ""
assert_parser_cell "$PARSER_FIX" FINDING_5 PARSED_CORRECTNESS true
assert_parser_cell "$PARSER_FIX" FINDING_3 PARSED_SEVERITY ""
assert_parser_cell "$PARSER_FIX" FINDING_3 PARSED_UNCERTAIN true
assert_parser_cell "$PARSER_FIX" FINDING_4 PARSED_VOTE YES

echo "=== parser unreadable file and missing id ==="
set +e
"$PARSER" "$TMPROOT/does-not-exist.txt" FINDING_1 >/dev/null 2>&1
parser_missing_rc=$?
set -e
[[ "$parser_missing_rc" -eq 2 ]] || fail "unreadable voter file should exit 2"
assert_parser_cell "$PARSER_FIX" FINDING_999 PARSED_VOTE ""
assert_parser_cell "$PARSER_FIX" FINDING_999 PARSED_CORRECTNESS ""
assert_parser_cell "$PARSER_FIX" FINDING_999 PARSED_UNCERTAIN true

echo "=== voter-sourced TSV cells are sanitized ==="
W7="$TMPROOT/sanitize"
mkdir -p "$W7"
SANITIZE_BALLOT="$W7/ballot.md"
cat > "$SANITIZE_BALLOT" <<'EOF'
### FINDING_1: Sanitized
- **Reviewer**: Reviewer	A
- focus-area = correctness
EOF
SANITIZE_CLAUDE="$W7/claude.txt"
printf 'FINDING_1: YES CORRECTNESS=true\tjunk SEVERITY=major QUALITY=good UNCERTAIN=false\n' > "$SANITIZE_CLAUDE"
run_tally --ballot-file "$SANITIZE_BALLOT" --design-tmpdir "$W7/design" --findings-classification-out "$W7/out.tsv" --voter "Claude:$SANITIZE_CLAUDE"
assert_cell "$W7/out.tsv" FINDING_1 finding_reviewers "Reviewer A"
assert_cell "$W7/out.tsv" FINDING_1 v1_vote YES
assert_cell "$W7/out.tsv" FINDING_1 v1_correctness true
awk -F '\t' 'NR == 2 { exit (NF == 18 ? 0 : 1) }' "$W7/out.tsv" || fail "sanitized row should preserve 18 TSV columns"

echo "=== reviewer tab normalization and sorted row order ==="
W6="$TMPROOT/sort"
mkdir -p "$W6"
SORT_BALLOT="$W6/ballot.md"
cat > "$SORT_BALLOT" <<EOF
### FINDING_2: Two
- **Reviewer**: A	B
- focus-area = correctness

### FINDING_10: Ten
- **Reviewer**: C
- focus-area = correctness

### FINDING_1: One
- **Reviewer**: D
- focus-area = correctness

### OOS_2: Oos two
- **Reviewer**: E
- focus-area = documentation

### OOS_1: Oos one
- **Reviewer**: F
- focus-area = documentation
EOF
SORT_V="$W6/claude.txt"
cat > "$SORT_V" <<'EOF'
FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false
FINDING_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=adequate UNCERTAIN=false
FINDING_10: YES CORRECTNESS=true SEVERITY=nit QUALITY=good UNCERTAIN=false
OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false
OOS_2: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false
EOF
run_tally --ballot-file "$SORT_BALLOT" --design-tmpdir "$W6/design" --findings-classification-out "$W6/out.tsv" --voter "Claude:$SORT_V"
order=$(awk -F '\t' 'NR > 1 { print $1 }' "$W6/out.tsv" | paste -sd ' ' -)
[[ "$order" == "FINDING_1 FINDING_2 FINDING_10 OOS_1 OOS_2" ]] || fail "unexpected row order: $order"
assert_cell "$W6/out.tsv" FINDING_2 finding_reviewers "A B"

echo "PASS: test-findings-classification.sh"
