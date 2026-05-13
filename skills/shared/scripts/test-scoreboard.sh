#!/usr/bin/env bash
# Regression harness for scoreboard.sh.

set -euo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-scoreboard.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

printf 'REVIEWER=Structure ACCEPTED=true\n' > "$TMP/tally.env"
out=$("$DIR/scoreboard.sh" --tally-file "$TMP/tally.env" --reviewer-labels "Structure,Testing" --output-file "$TMP/score.md")
grep -Fq 'SCOREBOARD_FILE=' <<< "$out"
grep -Fq '| Structure | 1 |' "$TMP/score.md"
grep -Fq '| Testing | 0 |' "$TMP/score.md"

echo "All assertions passed."
