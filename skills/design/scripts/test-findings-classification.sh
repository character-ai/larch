#!/usr/bin/env bash
# Regression harness for findings-classification.tsv and judge rating parsing.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
CLAUDE_PLUGIN_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
export CLAUDE_PLUGIN_ROOT
TALLY="$SCRIPT_DIR/tally-plan-review.sh"
PARSER="$CLAUDE_PLUGIN_ROOT/scripts/parse-judge-vote-and-rating.sh"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-findings-classification-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

write_ballot() {
    local path="$1"
    cat > "$path" <<'EOF'
### FINDING_1: First finding
- **Reviewer(s)**: Cursor-Edge	Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: src/a
- **Concern**: first concern.

### FINDING_2: Second finding
- **Reviewer**: Claude-Plan
- **Severity**: important
- **Focus area**: correctness
- **Location**: src/b
- **Concern**: second concern.

### FINDING_10: Tenth finding
- **Reviewer**: Cursor-Plan
- **Severity**: important
- **Focus area**: correctness
- **Location**: src/c
- **Concern**: tenth concern.

### OOS_1: First follow-up
- **Description**: follow-up one.
- **Reviewer**: Codex-Plan
- **Severity**: minor
- **Focus area**: docs
- **Location**: docs/a
- **Phase**: design

### OOS_2: Second follow-up
- **Description**: follow-up two.
- **Reviewer**: Cursor-Plan
- **Severity**: minor
- **Focus area**: docs
- **Location**: docs/b
- **Phase**: design

### OOS_3: Third follow-up
- **Description**: follow-up three.
- **Reviewer**: Claude-Plan
- **Severity**: minor
- **Focus area**: docs
- **Location**: docs/c
- **Phase**: design
EOF
}

cell() {
    python3 - "$1" "$2" "$3" <<'PY'
import csv, sys
path, finding_id, column = sys.argv[1:4]
with open(path, newline="", encoding="utf-8") as fh:
    for row in csv.DictReader(fh, delimiter="\t"):
        if row["finding_id"] == finding_id:
            print(row[column])
            raise SystemExit(0)
raise SystemExit(1)
PY
}

assert_cell() {
    local path="$1" id="$2" col="$3" want="$4" got
    got=$(cell "$path" "$id" "$col") || fail "missing row $id in $path"
    [[ "$got" == "$want" ]] || fail "$id $col: expected [$want], got [$got]"
}

assert_all_rows_21_fields() {
    local path="$1" bad
    bad=$(awk -F '\t' 'NR > 1 && NF != 21 { print NR ":" NF }' "$path")
    [[ -z "$bad" ]] || fail "expected 21 fields in every data row for $path, got $bad"
}

parser_value() {
    local output="$1" key="$2"
    awk -F= -v k="$key" '$1 == k { print substr($0, length(k) + 2); exit }' <<< "$output"
}

echo "=== complete three-judge classification ==="
W1="$TMPROOT/case1"
mkdir -p "$W1"
BALLOT="$W1/ballot.md"
write_ballot "$BALLOT"
CLAUDE="$W1/claude-vote-output.txt"
CODEX="$W1/codex-vote-output.txt"
CURSOR="$W1/cursor-vote-output.txt"
for f in "$CLAUDE" "$CODEX" "$CURSOR"; do
    cat > "$f" <<'EOF'
FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=excellent UNCERTAIN=false
FINDING_2: YES CORRECTNESS=true SEVERITY=major UNCERTAIN=false
FINDING_10: NO SEVERITY=minor CORRECTNESS=false-positive QUALITY=weak UNCERTAIN=false -- reason
OOS_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false
OOS_2: NO CORRECTNESS=false-positive SEVERITY=nit QUALITY=no-fix UNCERTAIN=false
OOS_3: EXONERATE CORRECTNESS=partially-true SEVERITY=minor QUALITY=adequate UNCERTAIN=false
EOF
done
OUT="$W1/findings-classification.tsv"
"$TALLY" --ballot-file "$BALLOT" --design-tmpdir "$W1/design" --findings-classification-out "$OUT" --voter "Claude:$CLAUDE" --voter "Codex:$CODEX" --voter "Cursor:$CURSOR" >/dev/null
assert_cell "$OUT" FINDING_1 v1_tool Claude
assert_cell "$OUT" FINDING_1 v2_tool Codex
assert_cell "$OUT" FINDING_1 v3_tool Cursor
assert_cell "$OUT" FINDING_1 v1_quality excellent
assert_cell "$OUT" OOS_3 v2_vote EXONERATE
assert_cell "$OUT" FINDING_1 finding_reviewers "Cursor-Edge Codex-Arch"
assert_all_rows_21_fields "$OUT"

echo "=== parser axis order, partial row, casing, duplicates, delimiter ==="
PV="$TMPROOT/parser-votes.txt"
cat > "$PV" <<'EOF'
FINDING_2: YES SEVERITY=major CORRECTNESS=true UNCERTAIN=false
FINDING_3: YES SEVERITY=MAJOR
FINDING_4: NO CORRECTNESS=false-positive SEVERITY=minor QUALITY=weak UNCERTAIN=false
FINDING_4: yes CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false
FINDING_5: MAYBE CORRECTNESS=true
FINDING_6: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false -- reviewer mentioned QUALITY=weak
FINDING_7: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false reviewer mentioned QUALITY=weak
EOF
p2=$("$PARSER" "$PV" FINDING_2)
[[ "$(parser_value "$p2" PARSED_SEVERITY)" == "major" ]] || fail "position-agnostic SEVERITY did not parse"
[[ "$(parser_value "$p2" PARSED_QUALITY)" == "" ]] || fail "missing QUALITY should emit empty"
[[ "$(parser_value "$p2" PARSED_UNCERTAIN)" == "true" ]] || fail "missing QUALITY should force uncertain=true"
p3=$("$PARSER" "$PV" FINDING_3)
[[ "$(parser_value "$p3" PARSED_SEVERITY)" == "" ]] || fail "uppercase severity should be rejected"
[[ "$(parser_value "$p3" PARSED_UNCERTAIN)" == "true" ]] || fail "bad axis should force uncertain"
p4=$("$PARSER" "$PV" FINDING_4)
[[ "$(parser_value "$p4" PARSED_VOTE)" == "YES" ]] || fail "duplicate ID last-line-wins failed"
p5=$("$PARSER" "$PV" FINDING_5)
[[ "$(parser_value "$p5" PARSED_VOTE)" == "" ]] || fail "unrecognized vote should emit empty vote"
[[ "$(parser_value "$p5" PARSED_CORRECTNESS)" == "true" ]] || fail "axis should parse even with unrecognized vote"
p6=$("$PARSER" "$PV" FINDING_6)
[[ "$(parser_value "$p6" PARSED_QUALITY)" == "good" ]] || fail "post-delimiter QUALITY should be ignored"
p7=$("$PARSER" "$PV" FINDING_7)
[[ "$(parser_value "$p7" PARSED_QUALITY)" == "weak" ]] || fail "without delimiter last axis token should win"

echo "=== missing judge, canonical cursor slot, and phase path metadata ==="
W2="$TMPROOT/case2"
mkdir -p "$W2"
write_ballot "$W2/ballot.md"
cp "$CLAUDE" "$W2/claude-vote-output-phase2.txt"
cp "$CURSOR" "$W2/cursor-vote-output-phase3.txt"
"$TALLY" --ballot-file "$W2/ballot.md" --design-tmpdir "$W2/design" --findings-classification-out "$W2/out.tsv" --voter "Claude:$W2/claude-vote-output-phase2.txt" --voter "Cursor:$W2/cursor-vote-output-phase3.txt" >/dev/null
assert_cell "$W2/out.tsv" FINDING_1 v1_tool Claude
assert_cell "$W2/out.tsv" FINDING_1 v2_tool ""
assert_cell "$W2/out.tsv" FINDING_1 v3_tool Cursor
assert_all_rows_21_fields "$W2/out.tsv"

echo "=== main-agent and empty-ballot fallback rows ==="
W3="$TMPROOT/case3"
mkdir -p "$W3"
write_ballot "$W3/ballot.md"
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false\n' > "$W3/voter-main-agent.txt"
"$TALLY" --ballot-file "$W3/ballot.md" --design-tmpdir "$W3/design" --findings-classification-out "$W3/out.tsv" --voter "MainAgent:$W3/voter-main-agent.txt" >/dev/null
assert_cell "$W3/out.tsv" FINDING_1 voting_result rejected
assert_cell "$W3/out.tsv" FINDING_1 v1_tool ""
assert_all_rows_21_fields "$W3/out.tsv"
: > "$W3/empty-ballot.md"
"$TALLY" --ballot-file "$W3/empty-ballot.md" --design-tmpdir "$W3/empty-design" --findings-classification-out "$W3/empty.tsv" --voter "Claude:$CLAUDE" >/dev/null
[[ "$(wc -l < "$W3/empty.tsv" | tr -d ' ')" == "1" ]] || fail "empty ballot should write header only"

echo "=== rerun overwrite and sorted row order ==="
printf 'stale\n' > "$W3/out.tsv"
"$TALLY" --ballot-file "$W3/ballot.md" --design-tmpdir "$W3/design2" --findings-classification-out "$W3/out.tsv" --voter "Claude:$CLAUDE" >/dev/null
! grep -q stale "$W3/out.tsv" || fail "classification TSV was not overwritten"
order=$(awk -F '\t' 'NR > 1 { print $1 }' "$W3/out.tsv" | paste -sd ' ' -)
[[ "$order" == "FINDING_1 FINDING_2 FINDING_10 OOS_1 OOS_2 OOS_3" ]] || fail "unexpected row order: $order"

echo "=== anchored vote helper remains compatible ==="
vote=$(bash -c 'source "$1"; vote_for_id FINDING_1 "$2"' _ "$CLAUDE_PLUGIN_ROOT/scripts/lib-vote-tally.sh" "$CLAUDE")
[[ "$vote" == "YES" ]] || fail "vote_for_id did not parse extended vote line"

echo "=== waterfall fallback actual tool identity ==="
W4="$TMPROOT/case4"
mkdir -p "$W4"
write_ballot "$W4/ballot.md"
cp "$CLAUDE" "$W4/claude-vote-output.txt"
cp "$CODEX" "$W4/codex-vote-output.txt"
cp "$CURSOR" "$W4/cursor-vote-output.txt"
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/design" --findings-classification-out "$W4/out.tsv" --voter "Claude:$W4/claude-vote-output.txt" --voter "Claude:$W4/codex-vote-output.txt" --voter "Cursor:$W4/cursor-vote-output.txt" >/dev/null
assert_cell "$W4/out.tsv" FINDING_1 v2_tool Claude
assert_cell "$W4/out.tsv" FINDING_1 v2_vote YES

echo "=== argv diagnostics ==="
set +e
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/bad1" --findings-classification-out "$W4/bad1.tsv" --voter "MainAgent:$W3/voter-main-agent.txt" --voter "Claude:$CLAUDE" 2>"$W4/bad1.err" >/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "MainAgent mixed with other voters should fail"
grep -Fq 'error: --voter MainAgent is only valid as the sole voter (0-judge fallback path)' "$W4/bad1.err" || fail "MainAgent diagnostic missing"
[[ ! -e "$W4/bad1.tsv" ]] || fail "bad MainAgent invocation wrote TSV"

set +e
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/bad2" --findings-classification-out "$W4/bad2.tsv" --voter "Claude:$CLAUDE" --voter-files "$CODEX" 2>"$W4/bad2.err" >/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "mixed --voter/--voter-files should fail"
grep -Fq 'error: --voter and --voter-files are mutually exclusive' "$W4/bad2.err" || fail "mutual exclusion diagnostic missing"
[[ ! -e "$W4/bad2.tsv" ]] || fail "mutual exclusion invocation wrote TSV"

set +e
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/bad3" --findings-classification-out "$W4/bad3.tsv" --voter "Robot:$CLAUDE" 2>"$W4/bad3.err" >/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "invalid voter slot should fail"
grep -Fq 'error: invalid voter slot: Robot (must be Claude|Codex|Cursor|MainAgent)' "$W4/bad3.err" || fail "invalid slot diagnostic missing"
[[ ! -e "$W4/bad3.tsv" ]] || fail "invalid slot invocation wrote TSV"

echo "=== legacy deprecation path ==="
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/legacy-design" --findings-classification-out "$W4/legacy.tsv" --voter-files "$CLAUDE" "$CODEX" "$CURSOR" 2>"$W4/legacy.err" >/dev/null
grep -Fq 'deprecated: --voter-files; use --voter <SLOT>:<PATH>' "$W4/legacy.err" || fail "legacy deprecation warning missing"
[[ -s "$W4/legacy.tsv" ]] || fail "legacy classification TSV missing"
assert_all_rows_21_fields "$W4/legacy.tsv"

echo "PASS: test-findings-classification.sh"
