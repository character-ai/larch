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

echo "All assertions passed."
