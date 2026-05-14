#!/usr/bin/env bash
# Regression harness for tally-votes.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/tally-votes.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-tally-votes.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

assert_stdout_cap() {
    local text="$1" cap="${2:-2048}" bytes
    bytes=${#text}
    [[ "$bytes" -le "$cap" ]] || { echo "FAIL: stdout ${bytes}B > ${cap}B cap" >&2; exit 1; }
}

cat > "$TMP/findings.md" <<'EOF'
### FINDING_1: A
- **Concern**: A
- **Suggested revision**: A
### FINDING_2: B
- **Concern**: B
- **Suggested revision**: B
EOF

out=$("$SCRIPT" --findings-file "$TMP/findings.md" --review-tmpdir "$TMP" --cursor-available false --codex-available false --both-down true)
assert_stdout_cap "$out"
grep -Fq 'ACCEPTED_COUNT=2' <<< "$out"
grep -Fq 'FINDING_1_ACCEPTED=true' "$TMP/review-tally.env"

printf 'FINDING_1 YES\nFINDING_2 NO\n' > "$TMP/cursor-votes.txt"
printf 'FINDING_1 YES\nFINDING_2 NO\n' > "$TMP/codex-votes.txt"
out=$("$SCRIPT" --findings-file "$TMP/findings.md" --review-tmpdir "$TMP" --cursor-available true --codex-available true --both-down false)
assert_stdout_cap "$out"
grep -Fq 'ACCEPTED_COUNT=1' <<< "$out"
grep -Fq 'REJECTED_COUNT=1' <<< "$out"

echo "All assertions passed."
