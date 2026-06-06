#!/usr/bin/env bash
# Regression harness for emit-tally.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/emit-tally.sh"
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
echo "  ok   count=0 path still runs oos-serialize on oos.md"

echo "# Case: OOS_ACCEPTED_COUNT=0 with oos.md absent truncates to empty"
mkdir -p "$TMP/truncate0"
cp "$TMP/serialize0/tally.env" "$TMP/truncate0/tally.env"
printf 'stale content\n' > "$TMP/truncate0/oos-accepted-review.md"
"$SCRIPT" --tally-file "$TMP/truncate0/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/truncate0/absent-oos.md" --review-tmpdir "$TMP/truncate0" --round 1 --mode diff >/dev/null
[[ ! -s "$TMP/truncate0/oos-accepted-review.md" ]] || { echo "FAIL: count=0 absent-oos.md path must truncate to empty" >&2; exit 1; }
echo "  ok   count=0 absent-oos.md path truncates to empty"

echo "All assertions passed."
