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
FINDING_2_OUTCOME=neutral
FINDING_3_ACCEPTED=false
FINDING_3_OUTCOME=rejected
ACCEPTED_COUNT=1
REJECTED_COUNT=1
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
jq -e '.schema_version == 1 and .accepted_count == 1 and .rejected_count == 1' "$TMP/review-summary.json" >/dev/null
grep -Fq 'Review Round 1' "$TMP/review-round-summary.md"
grep -Fq 'Rejected findings: 1' "$TMP/review-round-summary.md"
grep -Fq 'FINDING_3' "$TMP/rejected-findings-full.md"
grep -Fq '_OUTCOME=rejected' "$TMP/rejected-findings.md"
if grep -Fq 'FINDING_2_OUTCOME=neutral' "$TMP/rejected-findings.md"; then
    echo "FAIL: neutral finding leaked into rejected-findings.md" >&2
    exit 1
fi

echo "All assertions passed."
