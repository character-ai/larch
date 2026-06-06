#!/usr/bin/env bash
# Regression harness for emit-tally.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
SCRIPT="$REPO_ROOT/skills/review/scripts/emit-tally.sh"
LEGACY_OPENER_AWK="$REPO_ROOT/skills/implement/scripts/oos-has-legacy-finding-block-opener.awk"
TALLY_SCRIPT="$REPO_ROOT/skills/review/scripts/tally-code-votes.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-emit-tally.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

assert_stdout_cap() {
    local text="$1" cap="${2:-2048}" bytes
    bytes=${#text}
    [[ "$bytes" -le "$cap" ]] || { echo "FAIL: stdout ${bytes}B > ${cap}B cap" >&2; exit 1; }
}

cat > "$TMP/tally.env" <<'EOF'
FINDING_1_ACCEPTED=true
FINDING_1_OUTCOME=accepted
FINDING_2_ACCEPTED=false
FINDING_2_OUTCOME=rejected
FINDING_2_REJECTED_SUBTYPE=neutral
FINDING_3_ACCEPTED=false
FINDING_3_OUTCOME=rejected
FINDING_3_REJECTED_SUBTYPE=true_rejected
ACCEPTED_COUNT=1
REJECTED_COUNT=2
EXONERATED_COUNT=0
NEUTRAL_COUNT=1
EOF
cat > "$TMP/accepted.md" <<'EOF'
### FINDING_1: A
- **Concern**: A
EOF
cat > "$TMP/rejected-findings.md" <<'EOF'
### [rejected] FINDING_3

### FINDING_3: B
- **Concern**: B
EOF
: > "$TMP/oos.md"

out=$("$SCRIPT" --tally-file "$TMP/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/oos.md" --review-tmpdir "$TMP" --round 1 --mode diff)
assert_stdout_cap "$out"
grep -Fq 'EMIT_OK=true' <<< "$out"
jq -e '.schema_version == 3 and .accepted_count == 1 and .rejected_count == 2 and .exonerated_count == 0 and (has("neutral_count") | not) and (.finding_counts | has("total_neutral") | not) and .finding_counts.total_exonerated == 0 and .finding_counts.total_rejected == 2 and .panel.scout_status == "na" and .panel.static_slot_count == 0 and .panel.dynamic_slot_count == 0 and .panel.total_slot_count == 0' "$TMP/review-summary.json" >/dev/null
grep -Fq 'Review Round 1' "$TMP/review-round-summary.md"
grep -Fq '1 accepted, 2 rejected (0 exonerated)' "$TMP/review-round-summary.md"
grep -Fq 'FINDING_3' "$TMP/rejected-findings-full.md"
grep -Fq 'FINDING_2_OUTCOME=rejected' "$TMP/rejected-findings.md"
grep -Fq 'FINDING_3_OUTCOME=rejected' "$TMP/rejected-findings.md"
if grep -Fq 'FINDING_2_REJECTED_SUBTYPE=neutral' "$TMP/rejected-findings.md"; then
    echo "FAIL: subtype lines should not be copied into rejected-findings.md" >&2
    exit 1
fi

echo "# Case: invariant exonerated_count > rejected_count aborts before JSON write"
mkdir -p "$TMP/bad-out"
cat > "$TMP/bad.env" <<'EOF'
FINDING_1_ACCEPTED=true
FINDING_1_OUTCOME=accepted
ACCEPTED_COUNT=1
REJECTED_COUNT=1
EXONERATED_COUNT=2
NEUTRAL_COUNT=0
EOF
set +e
"$SCRIPT" --tally-file "$TMP/bad.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/oos.md" --review-tmpdir "$TMP/bad-out" --round 1 --mode diff >/dev/null 2>&1
bad_rc=$?
set -e
[[ "$bad_rc" -ne 0 ]] || { echo "FAIL: expected emit-tally to exit non-zero on invariant violation" >&2; exit 1; }
[[ ! -f "$TMP/bad-out/review-summary.json" ]] || { echo "FAIL: review-summary.json must not be written on invariant failure" >&2; exit 1; }

echo "# Case: OOS_ACCEPTED_COUNT>0 preserves tally-written oos-accepted-review.md (oos.md present)"
mkdir -p "$TMP/preserve1"
cat > "$TMP/preserve1/tally.env" <<'EOF'
ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
OOS_ACCEPTED_COUNT=1
EOF
printf '### OOS_1: Normalized by tally\n- **Description**: keep me.\n' > "$TMP/preserve1/oos-accepted-review.md"
cp "$TMP/preserve1/oos-accepted-review.md" "$TMP/preserve1/expected.md"
printf '### FINDING_9: [OUT_OF_SCOPE] raw oos.md content\nVote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted\n' > "$TMP/preserve1/oos.md"
"$SCRIPT" --tally-file "$TMP/preserve1/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/preserve1/oos.md" --review-tmpdir "$TMP/preserve1" --round 1 --mode diff >/dev/null
cmp -s "$TMP/preserve1/oos-accepted-review.md" "$TMP/preserve1/expected.md" || { echo "FAIL: preserve branch (oos.md present) rewrote tally output" >&2; exit 1; }
echo "  ok   tally output preserved with oos.md present (serialize skipped)"

echo "# Case: OOS_ACCEPTED_COUNT>0 with oos.md ABSENT skips the truncate branch"
mkdir -p "$TMP/preserve2"
cp "$TMP/preserve1/tally.env" "$TMP/preserve2/tally.env"
printf '### OOS_1: Normalized by tally\n- **Description**: keep me.\n' > "$TMP/preserve2/oos-accepted-review.md"
cp "$TMP/preserve2/oos-accepted-review.md" "$TMP/preserve2/expected.md"
"$SCRIPT" --tally-file "$TMP/preserve2/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/preserve2/absent-oos.md" --review-tmpdir "$TMP/preserve2" --round 1 --mode diff >/dev/null
cmp -s "$TMP/preserve2/oos-accepted-review.md" "$TMP/preserve2/expected.md" || { echo "FAIL: preserve branch (oos.md absent) truncated tally output" >&2; exit 1; }
echo "  ok   tally output preserved with oos.md absent (truncate skipped)"

echo "# Case: OOS_ACCEPTED_COUNT>0 with empty sink and absent oos.md fails closed"
mkdir -p "$TMP/absent-empty"
cp "$TMP/preserve1/tally.env" "$TMP/absent-empty/tally.env"
: > "$TMP/absent-empty/oos-accepted-review.md"
set +e
"$SCRIPT" --tally-file "$TMP/absent-empty/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/absent-empty/absent-oos.md" --review-tmpdir "$TMP/absent-empty" --round 1 --mode diff >/dev/null 2>&1
absent_empty_rc=$?
set -e
[[ "$absent_empty_rc" -ne 0 ]] || { echo "FAIL: empty sink with missing oos.md must fail closed" >&2; exit 1; }
echo "  ok   empty sink with missing oos.md fails closed"

echo "# Case: OOS_ACCEPTED_COUNT=0 still serializes tagged OOS from oos.md"
mkdir -p "$TMP/serialize0"
cat > "$TMP/serialize0/tally.env" <<'EOF'
ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
OOS_ACCEPTED_COUNT=0
EOF
printf '### FINDING_4: [OUT_OF_SCOPE] serialize me\n- **Description**: from oos.md.\n' > "$TMP/serialize0/oos.md"
"$SCRIPT" --tally-file "$TMP/serialize0/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/serialize0/oos.md" --review-tmpdir "$TMP/serialize0" --round 1 --mode diff >/dev/null
grep -Fq 'serialize me' "$TMP/serialize0/oos-accepted-review.md" || { echo "FAIL: count=0 path no longer serializes oos.md" >&2; exit 1; }
grep -Eq '^### OOS_1:' "$TMP/serialize0/oos-accepted-review.md" || { echo "FAIL: count=0 path must normalize serialized header" >&2; exit 1; }
if awk -f "$LEGACY_OPENER_AWK" "$TMP/serialize0/oos-accepted-review.md"; then
    echo "FAIL: count=0 path emitted legacy FINDING header" >&2
    exit 1
fi
echo "  ok   count=0 path still runs oos-serialize on oos.md"

echo "# Case: OOS_ACCEPTED_COUNT=0 skips rejected tagged OOS from oos.md"
mkdir -p "$TMP/serialize-rejected"
cp "$TMP/serialize0/tally.env" "$TMP/serialize-rejected/tally.env"
printf '### FINDING_5: [OUT_OF_SCOPE] rejected oos\n- **Description**: from oos.md.\nVote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected\n' > "$TMP/serialize-rejected/oos.md"
"$SCRIPT" --tally-file "$TMP/serialize-rejected/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/serialize-rejected/oos.md" --review-tmpdir "$TMP/serialize-rejected" --round 1 --mode diff >/dev/null
[[ ! -s "$TMP/serialize-rejected/oos-accepted-review.md" ]] || { echo "FAIL: rejected serialized OOS must not enter accepted sink" >&2; exit 1; }
echo "  ok   rejected OOS is not serialized into accepted sink"

echo "# Case: OOS_ACCEPTED_COUNT>0 with empty sink falls back to normalized serialize path"
mkdir -p "$TMP/desync-rebuild"
cat > "$TMP/desync-rebuild/tally.env" <<'EOF'
ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
OOS_ACCEPTED_COUNT=1
EOF
: > "$TMP/desync-rebuild/oos-accepted-review.md"
printf '### FINDING_6: title [OUT_OF_SCOPE]\n- **Description**: accepted in oos.md.\nVote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted\n' > "$TMP/desync-rebuild/oos.md"
"$SCRIPT" --tally-file "$TMP/desync-rebuild/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/desync-rebuild/oos.md" --review-tmpdir "$TMP/desync-rebuild" --round 1 --mode diff >/dev/null 2>&1
grep -Eq '^### OOS_1: title \[OUT_OF_SCOPE\]' "$TMP/desync-rebuild/oos-accepted-review.md" || { echo "FAIL: desynced preserve path did not rebuild normalized accepted sink" >&2; exit 1; }
echo "  ok   desynced empty sink rebuilds from oos.md"

echo "# Case: OOS_ACCEPTED_COUNT>0 with partial sink fails closed when rebuild cannot recover"
mkdir -p "$TMP/partial-fail"
cat > "$TMP/partial-fail/tally.env" <<'EOF'
ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
OOS_ACCEPTED_COUNT=2
EOF
printf '### OOS_1: Only one normalized block\n- **Description**: partial sink.\n' > "$TMP/partial-fail/oos-accepted-review.md"
printf '### FINDING_7: bare scope drift\n- **Description**: no OOS tag for serializer.\n' > "$TMP/partial-fail/oos.md"
set +e
"$SCRIPT" --tally-file "$TMP/partial-fail/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/partial-fail/oos.md" --review-tmpdir "$TMP/partial-fail" --round 1 --mode diff >/dev/null 2>&1
partial_rc=$?
set -e
[[ "$partial_rc" -ne 0 ]] || { echo "FAIL: partial accepted sink must fail closed when rebuild count mismatches tally" >&2; exit 1; }
echo "  ok   partial accepted sink fails closed"

echo "# Case: partial accepted sink is not destructively rebuilt"
mkdir -p "$TMP/partial-preserve"
cat > "$TMP/partial-preserve/tally.env" <<'EOF'
ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
OOS_ACCEPTED_COUNT=2
EOF
printf '### OOS_1: Tally-normalized only\n- **Description**: must survive failed emit.\n' > "$TMP/partial-preserve/oos-accepted-review.md"
cp "$TMP/partial-preserve/oos-accepted-review.md" "$TMP/partial-preserve/expected.md"
printf '### FINDING_7: bare scope drift\n- **Description**: no OOS tag for serializer.\n' > "$TMP/partial-preserve/oos.md"
set +e
"$SCRIPT" --tally-file "$TMP/partial-preserve/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/partial-preserve/oos.md" --review-tmpdir "$TMP/partial-preserve" --round 1 --mode diff >/dev/null 2>&1
partial_preserve_rc=$?
set -e
[[ "$partial_preserve_rc" -ne 0 ]] || { echo "FAIL: partial sink mismatch must fail closed" >&2; exit 1; }
cmp -s "$TMP/partial-preserve/oos-accepted-review.md" "$TMP/partial-preserve/expected.md" || { echo "FAIL: partial sink was destructively rebuilt" >&2; exit 1; }
echo "  ok   partial accepted sink preserved on fail-closed"

echo "# Case: OOS_ACCEPTED_COUNT=0 propagates oos-serialize classifier failure"
mkdir -p "$TMP/serialize-fail0"
mkdir -p "$TMP/fail-python-bin"
cat > "$TMP/fail-python-bin/python3" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$TMP/fail-python-bin/python3"
cp "$TMP/serialize0/tally.env" "$TMP/serialize-fail0/tally.env"
printf '### FINDING_4: [OUT_OF_SCOPE] needs classifier\n- **Description**: from oos.md.\n' > "$TMP/serialize-fail0/oos.md"
set +e
PATH="$TMP/fail-python-bin:$PATH" "$SCRIPT" --tally-file "$TMP/serialize-fail0/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/serialize-fail0/oos.md" --review-tmpdir "$TMP/serialize-fail0" --round 1 --mode diff >/dev/null 2>&1
serialize_fail_rc=$?
set -e
[[ "$serialize_fail_rc" -ne 0 ]] || { echo "FAIL: count=0 path must propagate oos-serialize classifier failure" >&2; exit 1; }
[[ ! -s "$TMP/serialize-fail0/oos-accepted-review.md" ]] || { echo "FAIL: classifier failure must not leave partial accepted sink" >&2; exit 1; }
echo "  ok   count=0 path propagates oos-serialize classifier failure"

echo "# Case: security-only accepted OOS count stays zero and emit leaves public sink empty"
mkdir -p "$TMP/security-only"
cat > "$TMP/security-only/tally.env" <<'EOF'
ACCEPTED_COUNT=0
REJECTED_COUNT=0
EXONERATED_COUNT=0
OOS_ACCEPTED_COUNT=0
EOF
: > "$TMP/security-only/oos-accepted-review.md"
printf '### FINDING_8: [OUT_OF_SCOPE] [security] private\n- **Description**: held.\nVote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted\n' > "$TMP/security-only/oos.md"
"$SCRIPT" --tally-file "$TMP/security-only/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/security-only/oos.md" --review-tmpdir "$TMP/security-only" --round 1 --mode diff >/dev/null
[[ ! -s "$TMP/security-only/oos-accepted-review.md" ]] || { echo "FAIL: security-only OOS must not enter public accepted sink" >&2; exit 1; }
echo "  ok   security-only accepted OOS leaves public sink empty"

echo "# Case: tally-code-votes output chains into emit-tally without losing accepted OOS"
mkdir -p "$TMP/chained/round-1"
cat > "$TMP/chained/round-1/ballot.md" <<'EOF'
### FINDING_1: Chained accepted OOS [OUT_OF_SCOPE]
- **Reviewer**: Codex-Plan-fidelity
- **Concern**: Pre-existing thing.
- **Suggested revision**: File it.
EOF
printf 'FINDING_1: YES\n' > "$TMP/chained/round-1/cursor-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/chained/round-1/codex-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/chained/round-1/claude-vote-output.txt"
"$TALLY_SCRIPT" --ballot-file "$TMP/chained/round-1/ballot.md" \
    --voter-files "$TMP/chained/round-1/cursor-vote-output.txt" "$TMP/chained/round-1/codex-vote-output.txt" "$TMP/chained/round-1/claude-vote-output.txt" \
    --review-tmpdir "$TMP/chained/round-1" > "$TMP/chained/round-1/tally.out"
printf -- '- **Tally-only marker**: preserve me.\n' >> "$TMP/chained/round-1/oos-accepted-review.md"
cat > "$TMP/chained/round-1/oos.md" <<'EOF'
### FINDING_9: [OUT_OF_SCOPE] conflicting serialize fallback
- **Concern**: Broken preserve would rebuild this instead.
Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted
EOF
"$SCRIPT" --tally-file "$TMP/chained/round-1/review-tally.env" \
    --accepted-findings-file "$TMP/chained/round-1/accepted-findings.md" \
    --oos-file "$TMP/chained/round-1/oos.md" \
    --review-tmpdir "$TMP/chained/round-1" --round 1 --mode diff >/dev/null
grep -Eq '^### OOS_1: Chained accepted OOS \[OUT_OF_SCOPE\]$' "$TMP/chained/round-1/oos-accepted-review.md" || { echo "FAIL: chained tally→emit path lost normalized OOS header" >&2; exit 1; }
grep -Fq 'Tally-only marker' "$TMP/chained/round-1/oos-accepted-review.md" || { echo "FAIL: chained tally→emit path did not preserve tally-written sink" >&2; exit 1; }
if grep -Fq 'conflicting serialize fallback' "$TMP/chained/round-1/oos-accepted-review.md"; then
    echo "FAIL: chained tally→emit path rebuilt from oos.md instead of preserving sink" >&2
    exit 1
fi
if awk -f "$LEGACY_OPENER_AWK" "$TMP/chained/round-1/oos-accepted-review.md"; then
    echo "FAIL: chained tally→emit path emitted legacy FINDING header" >&2
    exit 1
fi
got=$(awk -f "$REPO_ROOT/skills/implement/scripts/oos-non-security-block-count.awk" "$TMP/chained/round-1/oos-accepted-review.md")
[[ "$got" == "1" ]] || { echo "FAIL: chained tally→emit awk count got $got want 1" >&2; exit 1; }
echo "  ok   chained tally→emit preserves normalized accepted OOS"

echo "# Case: scope-drift tally output chains into emit-tally without losing bare FINDING OOS"
mkdir -p "$TMP/chained-drift/round-1"
cat > "$TMP/chained-drift/round-1/ballot.md" <<'EOF'
### FINDING_1: **Important** - `code-quality` - `docs/linting.md:22`
- **Reviewer**: Codex-Plan-fidelity
- **Concern**: Mentions docs/linting.md outside the changed scope.
- **Suggested revision**: File it.
EOF
printf 'src/main.py\n' > "$TMP/chained-drift/scope.txt"
printf 'FINDING_1: YES\n' > "$TMP/chained-drift/round-1/cursor-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/chained-drift/round-1/codex-vote-output.txt"
printf 'FINDING_1: YES\n' > "$TMP/chained-drift/round-1/claude-vote-output.txt"
"$TALLY_SCRIPT" --ballot-file "$TMP/chained-drift/round-1/ballot.md" \
    --voter-files "$TMP/chained-drift/round-1/cursor-vote-output.txt" "$TMP/chained-drift/round-1/codex-vote-output.txt" "$TMP/chained-drift/round-1/claude-vote-output.txt" \
    --review-tmpdir "$TMP/chained-drift/round-1" --scope-files "$TMP/chained-drift/scope.txt" > "$TMP/chained-drift/round-1/tally.out"
"$SCRIPT" --tally-file "$TMP/chained-drift/round-1/review-tally.env" \
    --accepted-findings-file "$TMP/chained-drift/round-1/accepted-findings.md" \
    --oos-file "$TMP/chained-drift/round-1/oos.md" \
    --review-tmpdir "$TMP/chained-drift/round-1" --round 1 --mode diff >/dev/null
grep -Eq '^### OOS_1: ' "$TMP/chained-drift/round-1/oos-accepted-review.md" || { echo "FAIL: chained scope-drift tally→emit path lost normalized OOS header" >&2; exit 1; }
got=$(awk -f "$REPO_ROOT/skills/implement/scripts/oos-non-security-block-count.awk" "$TMP/chained-drift/round-1/oos-accepted-review.md")
[[ "$got" == "1" ]] || { echo "FAIL: chained scope-drift tally→emit awk count got $got want 1" >&2; exit 1; }
echo "  ok   chained scope-drift tally→emit preserves normalized accepted OOS"

echo "# Case: OOS_ACCEPTED_COUNT=0 with oos.md absent truncates to empty"
mkdir -p "$TMP/truncate0"
cp "$TMP/serialize0/tally.env" "$TMP/truncate0/tally.env"
printf 'stale content\n' > "$TMP/truncate0/oos-accepted-review.md"
"$SCRIPT" --tally-file "$TMP/truncate0/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/truncate0/absent-oos.md" --review-tmpdir "$TMP/truncate0" --round 1 --mode diff >/dev/null
[[ ! -s "$TMP/truncate0/oos-accepted-review.md" ]] || { echo "FAIL: count=0 absent-oos.md path must truncate to empty" >&2; exit 1; }
echo "  ok   count=0 absent-oos.md path truncates to empty"

echo "All assertions passed."
