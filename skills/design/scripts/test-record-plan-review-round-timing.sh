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
| Item | Description | Votes | Result |
| --- | --- | --- | --- |
| OOS_1 | A | y/y/y | accepted |
| OOS_2 | B | n/n/n | rejected |
| FINDING_1 | C | y/y/y | accepted |
F
"$REPO_ROOT/skills/design/scripts/record-plan-review-round-timing.sh" --design-tmpdir "$TMP_BASE" --round 1 --start-s 100 --end-s 90
awk -F '\t' '$2 == "round" && $4 == "design" && $6 == 1 && $9 == 0 && $10 == 2 && $11 == 1 && $12 == 1 { found=1 } END { exit found ? 0 : 1 }' "$TMP_BASE/timing-ledger.tsv"
echo "PASS: test-record-plan-review-round-timing.sh"
