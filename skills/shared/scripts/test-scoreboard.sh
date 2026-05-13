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

# Regression: partial-substring match — "Correctness" must not match "Codex-Correctness"
printf 'REVIEWER=Correctness ACCEPTED=true\nREVIEWER=Codex-Correctness ACCEPTED=true\n' > "$TMP/tally2.env"
"$DIR/scoreboard.sh" --tally-file "$TMP/tally2.env" --reviewer-labels "Correctness,Codex-Correctness" --output-file "$TMP/score2.md" >/dev/null
grep -Fq '| Correctness | 1 |' "$TMP/score2.md"
grep -Fq '| Codex-Correctness | 1 |' "$TMP/score2.md"

echo "All assertions passed."
