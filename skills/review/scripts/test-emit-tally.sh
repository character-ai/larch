#!/usr/bin/env bash
# Regression harness for emit-tally.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/emit-tally.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-emit-tally.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

printf 'FINDING_1_ACCEPTED=true\nFINDING_2_ACCEPTED=false\n' > "$TMP/tally.env"
cat > "$TMP/accepted.md" <<'EOF'
### FINDING_1: A
- **Concern**: A
EOF
: > "$TMP/oos.md"

out=$("$SCRIPT" --tally-file "$TMP/tally.env" --accepted-findings-file "$TMP/accepted.md" --oos-file "$TMP/oos.md" --review-tmpdir "$TMP" --round 1 --mode diff)
grep -Fq 'EMIT_OK=true' <<< "$out"
jq -e '.schema_version == 1 and .accepted_count == 1 and .rejected_count == 1' "$TMP/review-summary.json" >/dev/null
grep -Fq 'Review Round 1' "$TMP/review-round-summary.md"

echo "All assertions passed."
