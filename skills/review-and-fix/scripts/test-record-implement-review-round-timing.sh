#!/usr/bin/env bash
# Regression tests for record-implement-review-round-timing.sh.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
export LARCH_QUIET_DISABLE=1
TMP_BASE=$(mktemp -d "${TMPDIR:-/tmp}/larch-impl-round-timing-test.XXXXXX")
trap 'rm -rf "$TMP_BASE"' EXIT
round_dir="$TMP_BASE/round-2"
mkdir -p "$round_dir"
cat > "$round_dir/accepted-findings.md" <<'F'
### FINDING_1:

### FINDING_2:
F
cat > "$round_dir/rejected-findings.md" <<'F'
FINDING_1_OUTCOME=rejected
9:FINDING_2_OUTCOME=rejected
F
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$TMP_BASE" --round 2 --start-s 10 --end-s 15
awk -F '\t' '$2 == "round" && $6 == 2 && $9 == 5 && $10 == 2 && $11 == 2 { found=1 } END { exit found ? 0 : 1 }' "$TMP_BASE/timing-ledger.tsv"
cat > "$round_dir/review-tally.env" <<'F'
ACCEPTED_COUNT=7
REJECTED_COUNT=8
F
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$TMP_BASE" --round 2 --start-s 20 --end-s 21
awk -F '\t' '$2 == "round" && $7 == 20 && $10 == 7 && $11 == 8 { found=1 } END { exit found ? 0 : 1 }' "$TMP_BASE/timing-ledger.tsv"
echo "PASS: test-record-implement-review-round-timing.sh"
