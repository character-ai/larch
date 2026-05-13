#!/usr/bin/env bash
# Regression harness for oos-serialize.sh.

set -euo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-serialize.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/findings.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Public cleanup
- **Concern**: Cleanup.
### FINDING_2: [OUT_OF_SCOPE] Secret issue
- **Concern**: focus-area=security secret.
EOF

out=$("$DIR/oos-serialize.sh" --findings-file "$TMP/findings.md" --output-file "$TMP/oos.md")
grep -Fq 'OOS_ACCEPTED=1' <<< "$out"
grep -Fq 'OOS_HELD_SECURITY=1' <<< "$out"
grep -Fq 'Public cleanup' "$TMP/oos.md"
if grep -Fq 'Secret issue' "$TMP/oos.md"; then
    echo "FAIL: security OOS item leaked" >&2
    exit 1
fi

echo "All assertions passed."
