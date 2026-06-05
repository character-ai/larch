#!/usr/bin/env bash
# Regression tests for record-plan-review-round-timing.sh.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
export LARCH_QUIET_DISABLE=1
TMP_BASE=$(mktemp -d "${TMPDIR:-/tmp}/larch-plan-round-timing-test.XXXXXX")
trap 'rm -rf "$TMP_BASE"' EXIT
cat > "$TMP_BASE/accepted-plan-findings.md" <<'F'
### FINDING_1:
### FINDING_2:
F
cat > "$TMP_BASE/rejected-findings.md" <<'F'
### [Plan Review] FINDING_1
### FINDING_2:
F
cat > "$TMP_BASE/voting-tally.md" <<'F'
## Findings
| Item | YES | NO | Exon | JERR | Result |
| --- | --- | --- | --- | --- | --- |
| OOS_1 | 3 | 0 | 0 | 0 | accepted |
| OOS_2 | 0 | 3 | 0 | 0 | rejected |
| FINDING_1 | 3 | 0 | 0 | 0 | accepted |
## Reviewer Competition Scoreboard
F
"$REPO_ROOT/skills/design/scripts/record-plan-review-round-timing.sh" --design-tmpdir "$TMP_BASE" --round 1 --start-s 100 --end-s 110
awk -F '\t' '$2 == "round" && $4 == "design" && $6 == 1 && $9 == 10 && $10 == 2 && $11 == 1 && $12 == 1 { found=1 } END { exit found ? 0 : 1 }' "$TMP_BASE/timing-ledger.tsv"
"$REPO_ROOT/skills/design/scripts/record-plan-review-round-timing.sh" --design-tmpdir "$TMP_BASE" --round 1 --start-s 100 --end-s 120
round_rows=$(awk -F '\t' '$2 == "round" && $4 == "design" && $5 == "design Step 3 — plan review" && $6 == 1 { c++ } END { print c + 0 }' "$TMP_BASE/timing-ledger.tsv")
[[ "$round_rows" == 1 ]] || { echo "expected idempotent deferred emit (1 design round-1 row), got $round_rows" >&2; exit 1; }
ZERO_TMP=$(mktemp -d "$TMP_BASE/zero.XXXXXX")
"$REPO_ROOT/skills/design/scripts/record-plan-review-round-timing.sh" --design-tmpdir "$ZERO_TMP" --round 2 --start-s 200 --end-s 200
awk -F '\t' '$2 == "round" && $4 == "design" && $6 == 2 && $9 == 0 && $10 == 0 && $11 == 0 && $12 == 0 { found=1 } END { exit found ? 0 : 1 }' "$ZERO_TMP/timing-ledger.tsv"
echo "PASS: test-record-plan-review-round-timing.sh"
