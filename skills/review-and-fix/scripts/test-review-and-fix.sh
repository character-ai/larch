#!/usr/bin/env bash
# Regression harness skeleton for review-and-fix.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-review-and-fix.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

empty="$TMP/empty.md"
: > "$empty"
out=$("$SCRIPT" --findings-file "$empty" --review-tmpdir "$TMP/empty-run")
grep -Fq 'REVIEW_AND_FIX_STATUS=no-findings' <<< "$out"
grep -Fq 'FIX_COUNT=0' <<< "$out"

fixture="$TMP/findings.md"
cat > "$fixture" <<'EOF'
### FINDING_1: First
- **Location**: skills/review/SKILL.md
- **Concern**: First concern.
- **Suggested revision**: First fix.

### FINDING_2: Second
- **Location**: skills/review/scripts/dispatch-panel.sh
- **Concern**: Second concern.
- **Suggested revision**: Second fix.
EOF

out=$("$SCRIPT" --findings-file "$fixture" --review-tmpdir "$TMP/run")
grep -Fq 'FINDING_ID=FINDING_1' <<< "$out"
grep -Fq 'FINDING_ID=FINDING_2' <<< "$out"
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out"
grep -Fq 'FIX_COUNT=2' <<< "$out"
[[ -f "$TMP/run/FINDING_1.fixer.env" ]]
[[ -f "$TMP/run/FINDING_2.fixer.env" ]]
grep -Fq 'PATH_VALID=true' "$TMP/run/FINDING_1.fixer.env"

echo "All assertions passed."
