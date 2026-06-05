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
awk -F '\t' '$2 == "round" && $6 == 2 && $9 == 5 { found=1 } END { exit found ? 0 : 1 }' "$TMP_BASE/timing-ledger.tsv"
round3_dir="$TMP_BASE/round-3"
mkdir -p "$round3_dir"
cat > "$round3_dir/review-tally.env" <<'F'
ACCEPTED_COUNT=7
REJECTED_COUNT=8
F
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$TMP_BASE" --round 3 --start-s 20 --end-s 21
awk -F '\t' '$2 == "round" && $6 == 3 && $7 == 20 && $10 == 7 && $11 == 8 { found=1 } END { exit found ? 0 : 1 }' "$TMP_BASE/timing-ledger.tsv"
round4_dir="$TMP_BASE/round-4"
mkdir -p "$round4_dir"
cat > "$round4_dir/review-summary.json" <<'F'
{"rejected_count":99}
F
cat > "$round4_dir/review-tally.env" <<'F'
ACCEPTED_COUNT=1
REJECTED_COUNT=0
F
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$TMP_BASE" --round 4 --start-s 30 --end-s 31
awk -F '\t' '$2 == "round" && $6 == 4 && $7 == 30 && $10 == 1 && $11 == 0 { found=1 } END { exit found ? 0 : 1 }' "$TMP_BASE/timing-ledger.tsv"
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$TMP_BASE" --round 4 --start-s 40 --end-s 41
round_rows=$(awk -F '\t' '$2 == "round" && $6 == 4 { c++ } END { print c + 0 }' "$TMP_BASE/timing-ledger.tsv")
[[ "$round_rows" == 1 ]] || { echo "expected idempotent deferred emit (1 round-4 row), got $round_rows" >&2; exit 1; }
echo "PASS: test-record-implement-review-round-timing.sh"
