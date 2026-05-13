#!/usr/bin/env bash
# Regression harness for ballot-parse.sh.

set -euo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-ballot-parse.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: Missing test
- **Concern**: The change lacks a regression test.
- **Suggested revision**: Add one.

### FINDING_2: [OUT_OF_SCOPE] Follow-up
- **Concern**: Later cleanup.
- **Suggested revision**: File it.
EOF

out=$("$DIR/ballot-parse.sh" --ballot-file "$TMP/ballot.md")
grep -Fq 'FINDING_COUNT=2' <<< "$out"
grep -Fq 'FINDING_1_TITLE=Missing test' <<< "$out"
grep -Fq 'FINDING_2_OOS=true' <<< "$out"

echo "All assertions passed."
