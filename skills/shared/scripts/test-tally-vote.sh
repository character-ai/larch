#!/usr/bin/env bash
# Regression harness for tally-vote.sh.

set -euo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-tally-vote.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/ballot.md" <<'EOF'
### FINDING_1: A
- **Concern**: A
- **Suggested revision**: A
### FINDING_2: B
- **Concern**: B
- **Suggested revision**: B
EOF
printf 'FINDING_1 YES\nFINDING_2 NO\n' > "$TMP/v1.txt"
printf 'FINDING_1 YES\nFINDING_2 EXONERATE\n' > "$TMP/v2.txt"

out=$("$DIR/tally-vote.sh" --ballot-file "$TMP/ballot.md" --voter-files "$TMP/v1.txt" "$TMP/v2.txt")
grep -Fq 'FINDING_1_ACCEPTED=true' <<< "$out"
grep -Fq 'FINDING_2_ACCEPTED=false' <<< "$out"
grep -Fq 'FINDING_2_VOTES_EXONERATE=1' <<< "$out"

echo "All assertions passed."
