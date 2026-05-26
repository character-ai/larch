#!/usr/bin/env bash
# Regression harness for findings-classification.tsv and judge rating parsing.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
CLAUDE_PLUGIN_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
export CLAUDE_PLUGIN_ROOT
TALLY="$SCRIPT_DIR/tally-plan-review.sh"
PARSER="$CLAUDE_PLUGIN_ROOT/scripts/parse-judge-vote-and-rating.sh"
VOTE_LIB="$CLAUDE_PLUGIN_ROOT/scripts/lib-vote-tally.sh"
HEADER='finding_id	finding_reviewers	voting_result	v1_vote	v1_correctness	v1_severity	v1_quality	v1_uncertain	v1_tool	v2_vote	v2_correctness	v2_severity	v2_quality	v2_uncertain	v2_tool	v3_vote	v3_correctness	v3_severity	v3_quality	v3_uncertain	v3_tool'

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

assert_parser_vote_matches_vote_for_id() {
    local voter_file="$1" ballot_id="$2" parsed lib_vote
    parsed=$("$PARSER" "$voter_file" "$ballot_id")
    lib_vote=$(bash -c 'source "$1"; vote_for_id "$2" "$3"' _ "$VOTE_LIB" "$ballot_id" "$voter_file")
    [[ "$(parser_value "$parsed" PARSED_VOTE)" == "${lib_vote/JUDGE_ERROR/}" ]] \
        || fail "parser/lib vote mismatch for $ballot_id in $voter_file"
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

echo "=== explicit --voter slot overrides misleading basename markers ==="
W2="$TMPROOT/case2"
mkdir -p "$W2"
write_ballot "$W2/ballot.md"
cp "$CLAUDE" "$W2/slot-2-looking-path.txt"
cp "$CURSOR" "$W2/slot-3-looking-path.txt"
"$TALLY" --ballot-file "$W2/ballot.md" --design-tmpdir "$W2/design" --findings-classification-out "$W2/out.tsv" --voter "Claude:$W2/slot-2-looking-path.txt" --voter "Cursor:$W2/slot-3-looking-path.txt" >/dev/null
assert_cell "$W2/out.tsv" FINDING_1 v1_tool Claude
assert_cell "$W2/out.tsv" FINDING_1 v2_tool ""
assert_cell "$W2/out.tsv" FINDING_1 v3_tool Cursor
assert_all_rows_21_fields "$W2/out.tsv"

echo "=== waterfall fallback preserves slot index and runtime tool ==="
W2W="$TMPROOT/case2-waterfall"
mkdir -p "$W2W"
write_ballot "$W2W/ballot.md"
cp "$CLAUDE" "$W2W/voter-1-claude.txt"
cp "$CLAUDE" "$W2W/voter-2-claude-fallback.txt"
cp "$CURSOR" "$W2W/voter-3-cursor.txt"
"$TALLY" --ballot-file "$W2W/ballot.md" --design-tmpdir "$W2W/design" --findings-classification-out "$W2W/out.tsv" --voter "1:Claude:$W2W/voter-1-claude.txt" --voter "2:Claude:$W2W/voter-2-claude-fallback.txt" --voter "3:Cursor:$W2W/voter-3-cursor.txt" >/dev/null
assert_cell "$W2W/out.tsv" FINDING_1 v1_tool Claude
assert_cell "$W2W/out.tsv" FINDING_1 v2_tool Claude
assert_cell "$W2W/out.tsv" FINDING_1 v3_tool Cursor
assert_cell "$W2W/out.tsv" FINDING_1 v2_vote YES
assert_cell "$W2W/out.tsv" FINDING_10 v2_vote NO
assert_all_rows_21_fields "$W2W/out.tsv"

echo "=== explicit slot beats misleading basename heuristic ==="
W2E="$TMPROOT/case2-explicit"
mkdir -p "$W2E"
write_ballot "$W2E/ballot.md"
cp "$CLAUDE" "$W2E/codex-vote-output.txt"
"$TALLY" --ballot-file "$W2E/ballot.md" --design-tmpdir "$W2E/design" --findings-classification-out "$W2E/out.tsv" --voter "Claude:$W2E/codex-vote-output.txt" >/dev/null
assert_cell "$W2E/out.tsv" FINDING_1 v1_tool Claude
assert_cell "$W2E/out.tsv" FINDING_1 v2_tool ""

echo "=== legacy --voter-files keeps basename fallback ==="
W2L="$TMPROOT/case2-legacy"
mkdir -p "$W2L/design/plan-review"
write_ballot "$W2L/ballot.md"
cp "$CLAUDE" "$W2L/claude-vote-output-phase2.txt"
cp "$CURSOR" "$W2L/cursor-vote-output-phase3.txt"
"$TALLY" --ballot-file "$W2L/ballot.md" --design-tmpdir "$W2L/design" --findings-classification-out "$W2L/out.tsv" --voter-files "$W2L/claude-vote-output-phase2.txt" "$W2L/cursor-vote-output-phase3.txt" >/dev/null 2>"$W2L/legacy.err"
assert_cell "$W2L/out.tsv" FINDING_1 v1_tool Claude
assert_cell "$W2L/out.tsv" FINDING_1 v2_tool ""
assert_cell "$W2L/out.tsv" FINDING_1 v3_tool Cursor
grep -Fq 'deprecated: --voter-files; use --voter <SLOT>:<PATH>' "$W2L/legacy.err" || fail "legacy deprecation warning missing"

echo "=== quiet-mode parser capture and partial-row TSV ==="
W2Q="$TMPROOT/case2-quiet"
mkdir -p "$W2Q/design"
quiet_votes="$W2Q/quiet-votes.txt"
cat > "$quiet_votes" <<'EOF'
FINDING_2: YES SEVERITY=major CORRECTNESS=true UNCERTAIN=false
EOF
quiet_out=$(env -u LARCH_QUIET_DISABLE DESIGN_TMPDIR="$W2Q/design" "$PARSER" "$quiet_votes" FINDING_2)
[[ "$(parser_value "$quiet_out" PARSED_VOTE)" == "YES" ]] || fail "quiet parser vote capture failed"
[[ "$(parser_value "$quiet_out" PARSED_QUALITY)" == "" ]] || fail "quiet parser missing-quality capture failed"
[[ "$(parser_value "$quiet_out" PARSED_UNCERTAIN)" == "true" ]] || fail "quiet parser missing-quality uncertain fallback failed"
"$TALLY" --ballot-file "$BALLOT" --design-tmpdir "$W2Q/design" --findings-classification-out "$W2Q/out.tsv" --voter "Claude:$quiet_votes" >/dev/null
assert_cell "$W2Q/out.tsv" FINDING_2 v1_vote YES
assert_cell "$W2Q/out.tsv" FINDING_2 v1_quality ""
assert_cell "$W2Q/out.tsv" FINDING_2 v1_uncertain true

echo "=== main-agent 0-judge fallback TSV and empty-ballot rows ==="
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

echo "=== default output path and shared header ==="
W3D="$TMPROOT/case3-default"
mkdir -p "$W3D/design"
"$TALLY" --ballot-file "$W3/ballot.md" --design-tmpdir "$W3D/design" --voter "Claude:$CLAUDE" >/dev/null
[[ -f "$W3D/design/plan-review/round-1/findings-classification.tsv" ]] || fail "default findings-classification path missing"
read -r default_header < "$W3D/design/plan-review/round-1/findings-classification.tsv"
[[ "$default_header" == "$HEADER" ]] || fail "default findings-classification header drifted"

echo "=== anchored vote helper remains compatible ==="
vote=$(bash -c 'source "$1"; vote_for_id FINDING_1 "$2"' _ "$VOTE_LIB" "$CLAUDE")
[[ "$vote" == "YES" ]] || fail "vote_for_id did not parse extended vote line"

echo "=== lowercased ballot ids and vote/parser parity ==="
PV2="$TMPROOT/parser-votes-lower.txt"
cat > "$PV2" <<'EOF'
finding_1: yes CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false
finding_2: YES-CORRECTNESS=true SEVERITY=major QUALITY=good UNCERTAIN=false
EOF
p_lower=$("$PARSER" "$PV2" FINDING_1)
[[ "$(parser_value "$p_lower" PARSED_VOTE)" == "YES" ]] || fail "lowercased ballot id did not parse"
[[ "$(parser_value "$p_lower" PARSED_CORRECTNESS)" == "true" ]] || fail "lowercased ballot id correctness missing"
assert_parser_vote_matches_vote_for_id "$PV" FINDING_2
assert_parser_vote_matches_vote_for_id "$PV" FINDING_3
assert_parser_vote_matches_vote_for_id "$PV" FINDING_4
assert_parser_vote_matches_vote_for_id "$PV" FINDING_5
assert_parser_vote_matches_vote_for_id "$PV" FINDING_6
assert_parser_vote_matches_vote_for_id "$PV" FINDING_7
assert_parser_vote_matches_vote_for_id "$PV2" FINDING_1
assert_parser_vote_matches_vote_for_id "$PV2" FINDING_2

echo "=== parser usage and unreadable-file exit matrix ==="
set +e
"$PARSER" >/dev/null 2>"$TMPROOT/parser-usage.err"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "missing parser args should exit 2"
grep -Fq 'usage: parse-judge-vote-and-rating.sh <voter_file> <ballot_id>' "$TMPROOT/parser-usage.err" \
    || fail "parser usage diagnostic missing"

set +e
"$PARSER" "$TMPROOT/no-such-voter.txt" FINDING_1 >/dev/null 2>"$TMPROOT/parser-unreadable.err"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || fail "unreadable parser voter file should exit 2"
grep -Fq 'parse-judge-vote-and-rating.sh: voter file is missing or unreadable:' "$TMPROOT/parser-unreadable.err" \
    || fail "parser unreadable-file diagnostic missing"

echo "=== malicious parser output is TSV-sanitized ==="
STUB_ROOT="$TMPROOT/stub-root"
mkdir -p "$STUB_ROOT/scripts"
cp "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh" "$STUB_ROOT/scripts/lib-quiet.sh"
cp "$CLAUDE_PLUGIN_ROOT/scripts/lib-vote-tally.sh" "$STUB_ROOT/scripts/lib-vote-tally.sh"
cat > "$STUB_ROOT/scripts/parse-judge-vote-and-rating.sh" <<'EOF'
#!/usr/bin/env bash
cat <<'OUT'
PARSED_CORRECTNESS=true
PARSED_SEVERITY=major
PARSED_QUALITY=good	with	tab
PARSED_UNCERTAIN=false
extra
line
OUT
EOF
chmod +x "$STUB_ROOT/scripts/parse-judge-vote-and-rating.sh"
W4S="$TMPROOT/case4-sanitize"
mkdir -p "$W4S/design"
write_ballot "$W4S/ballot.md"
cp "$CLAUDE" "$W4S/claude-vote-output.txt"
CLAUDE_PLUGIN_ROOT="$STUB_ROOT" "$TALLY" --ballot-file "$W4S/ballot.md" --design-tmpdir "$W4S/design" --findings-classification-out "$W4S/out.tsv" --voter "Claude:$W4S/claude-vote-output.txt" >/dev/null
assert_cell "$W4S/out.tsv" FINDING_1 v1_quality "good with tab"
assert_all_rows_21_fields "$W4S/out.tsv"

echo "=== duplicate position rejection and legacy fallback tool identity ==="
W4="$TMPROOT/case4"
mkdir -p "$W4"
write_ballot "$W4/ballot.md"
cp "$CLAUDE" "$W4/claude-vote-output.txt"
cp "$CODEX" "$W4/codex-vote-output.txt"
cp "$CURSOR" "$W4/cursor-vote-output.txt"
set +e
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/design" --findings-classification-out "$W4/out.tsv" --voter "Claude:$W4/claude-vote-output.txt" --voter "Claude:$W4/claude-vote-output.txt" --voter "Cursor:$W4/cursor-vote-output.txt" >/dev/null 2>"$W4/dup.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "duplicate canonical slot should fail"
grep -Fq 'error: duplicate voter position 1' "$W4/dup.err" || fail "duplicate canonical slot diagnostic missing"
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/legacy-design2" --findings-classification-out "$W4/legacy2.tsv" --voter-files "$W4/claude-vote-output.txt" "$W4/codex-vote-output.txt" "$W4/cursor-vote-output.txt" >/dev/null 2>"$W4/legacy2.err"
assert_cell "$W4/legacy2.tsv" FINDING_1 v2_tool Codex
assert_cell "$W4/legacy2.tsv" FINDING_1 v3_tool Cursor

echo "=== middle-slot failure preserves canonical columns ==="
W4M="$TMPROOT/case4-middle-slot"
mkdir -p "$W4M"
write_ballot "$W4M/ballot.md"
cp "$CLAUDE" "$W4M/claude-vote-output.txt"
cp "$CURSOR" "$W4M/cursor-vote-output.txt"
"$TALLY" --ballot-file "$W4M/ballot.md" --design-tmpdir "$W4M/design" --findings-classification-out "$W4M/out.tsv" --voter "Claude:$W4M/claude-vote-output.txt" --voter "Cursor:$W4M/cursor-vote-output.txt" >/dev/null
assert_cell "$W4M/out.tsv" FINDING_1 v1_tool Claude
assert_cell "$W4M/out.tsv" FINDING_1 v2_tool ""
assert_cell "$W4M/out.tsv" FINDING_1 v3_tool Cursor

echo "=== argv diagnostics ==="
set +e
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/bad1" --findings-classification-out "$W4/bad1.tsv" --voter "MainAgent:$W3/voter-main-agent.txt" --voter "Claude:$CLAUDE" 2>"$W4/bad1.err" >/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "MainAgent mixed with other voters should fail"
grep -Fq 'error: --voter MainAgent is only valid as the sole voter (0-judge fallback path)' "$W4/bad1.err" || fail "MainAgent diagnostic missing"
read -r bad1_header < "$W4/bad1.tsv"
[[ "$bad1_header" == "$HEADER" ]] || fail "bad MainAgent invocation should write header-only TSV"
[[ "$(wc -l < "$W4/bad1.tsv" | tr -d ' ')" == "1" ]] || fail "bad MainAgent invocation TSV should contain header only"

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
grep -Fq 'error: invalid voter slot: Robot (must be 1|2|3|Claude|Codex|Cursor|MainAgent)' "$W4/bad3.err" || fail "invalid slot diagnostic missing"
[[ ! -e "$W4/bad3.tsv" ]] || fail "invalid slot invocation wrote TSV"

set +e
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/bad4" --findings-classification-out "$W4/bad4.tsv" --voter-files "$W4/claude-vote-output.txt" "$W4/claude-vote-output.txt" 2>"$W4/bad4.err" >/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "duplicate legacy slot should fail"
grep -Fq 'error: duplicate voter position 1' "$W4/bad4.err" || fail "duplicate position diagnostic missing"

echo "=== legacy deprecation path ==="
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/legacy-design" --findings-classification-out "$W4/legacy.tsv" --voter-files "$CLAUDE" "$CODEX" "$CURSOR" 2>"$W4/legacy.err" >/dev/null
grep -Fq 'deprecated: --voter-files; use --voter <SLOT>:<PATH>' "$W4/legacy.err" || fail "legacy deprecation warning missing"
[[ -s "$W4/legacy.tsv" ]] || fail "legacy classification TSV missing"
assert_all_rows_21_fields "$W4/legacy.tsv"

echo "=== reverse-order main-agent misuse and legacy header ==="
set +e
"$TALLY" --ballot-file "$W4/ballot.md" --design-tmpdir "$W4/bad5" --findings-classification-out "$W4/bad5.tsv" --voter "Claude:$CLAUDE" --voter "MainAgent:$W3/voter-main-agent.txt" 2>"$W4/bad5.err" >/dev/null
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "reverse-order MainAgent mix should fail"
grep -Fq 'error: --voter MainAgent is only valid as the sole voter (0-judge fallback path)' "$W4/bad5.err" || fail "reverse-order MainAgent diagnostic missing"
read -r legacy_header < "$W4/legacy.tsv"
[[ "$legacy_header" == "$HEADER" ]] || fail "legacy findings-classification header drifted"
read -r bad5_header < "$W4/bad5.tsv"
[[ "$bad5_header" == "$HEADER" ]] || fail "reverse-order MainAgent invocation should write header-only TSV"
[[ "$(wc -l < "$W4/bad5.tsv" | tr -d ' ')" == "1" ]] || fail "reverse-order MainAgent invocation TSV should contain header only"

echo "=== aborts overwrite stale findings-classification TSV with header only ==="
W5="$TMPROOT/case5-stale-abort"
mkdir -p "$W5"
write_ballot "$W5/ballot.md"
printf 'stale\nrow\n' > "$W5/out.tsv"
set +e
"$TALLY" --ballot-file "$W5/ballot.md" --design-tmpdir "$W5/design" --findings-classification-out "$W5/out.tsv" --voter "Claude:$W5/missing.txt" >/dev/null 2>"$W5/missing.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "missing voter should fail"
read -r stale_header < "$W5/out.tsv"
[[ "$stale_header" == "$HEADER" ]] || fail "abort path should rewrite TSV header"
[[ "$(wc -l < "$W5/out.tsv" | tr -d ' ')" == "1" ]] || fail "abort path TSV should contain header only"

echo "=== spreadsheet formula prefixes are escaped ==="
W6="$TMPROOT/case6-formula"
mkdir -p "$W6/design"
cat > "$W6/ballot.md" <<'EOF'
### FINDING_1: Formula reviewer
- **Reviewer**: =HYPERLINK("https://evil.example")
- **Severity**: important
- **Focus area**: correctness
- **Location**: src/a
- **Concern**: formula reviewer.
EOF
cp "$CLAUDE" "$W6/claude-vote-output.txt"
"$TALLY" --ballot-file "$W6/ballot.md" --design-tmpdir "$W6/design" --findings-classification-out "$W6/out.tsv" --voter "Claude:$W6/claude-vote-output.txt" >/dev/null
reviewer_cell=$(cell "$W6/out.tsv" FINDING_1 finding_reviewers) || fail "missing formula reviewer row"
[[ "$reviewer_cell" == "'="* ]] || fail "formula-prefixed reviewer cell was not escaped"

echo "PASS: test-findings-classification.sh"
