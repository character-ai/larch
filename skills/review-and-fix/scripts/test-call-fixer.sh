#!/usr/bin/env bash
# Regression harness skeleton for call-fixer.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review-and-fix/scripts/call-fixer.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-call-fixer.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fixture="$TMP/findings.md"
cat > "$fixture" <<EOF
### FINDING_1: Fix script
- **Reviewer**: stub
- **Location**: skills/review/SKILL.md
- **Concern**: Update wrapper text.
- **Suggested revision**: Keep the contract concise.

### FINDING_2: Unsafe path
- **Reviewer**: stub
- **Location**: ../outside.md
- **Concern**: Bad path.
- **Suggested revision**: Ignore.
EOF

out=$("$SCRIPT" --finding-file "$fixture" --finding-id FINDING_1 --review-tmpdir "$TMP")
grep -Fq 'FIXER_STATUS=ready' <<< "$out"
grep -Fq 'FINDING_ID=FINDING_1' <<< "$out"
grep -Fq 'PATH_VALID=true' <<< "$out"
grep -Fq 'FILE_PATH=skills/review/SKILL.md' <<< "$out"

out=$("$SCRIPT" --finding-file "$fixture" --finding-id FINDING_2 --review-tmpdir "$TMP")
grep -Fq 'PATH_VALID=false' <<< "$out"
grep -Fq 'PATH_REASON=contains-dotdot' <<< "$out"

out=$("$SCRIPT" --finding-file "$fixture" --finding-id FINDING_1 --review-tmpdir "$TMP" --mark-applied)
grep -Fq 'FIXER_STATUS=applied' <<< "$out"
grep -Fq 'FINDING_1=applied' "$TMP/review-and-fix-status.env"

out=$("$SCRIPT" --finding-file "$fixture" --finding-id FINDING_2 --review-tmpdir "$TMP" --mark-skipped unsafe)
grep -Fq 'FIXER_STATUS=skipped' <<< "$out"
grep -Fq 'FINDING_2=skipped:unsafe' "$TMP/review-and-fix-status.env"

echo "All assertions passed."
