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
printf 'v1\tround\t1\tdesign\tdesign Step 3 — plan review\t5\t1\t2\t1\t9\t9\t0\t-\n' >> "$TMP_BASE/timing-ledger.tsv"
mkdir -p "$TMP_BASE/round-5"
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$TMP_BASE" --round 5 --start-s 50 --end-s 55
awk -F '\t' '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == 5 && $7 == 50 { found=1 } END { exit found ? 0 : 1 }' "$TMP_BASE/timing-ledger.tsv"
order_tmp=$(mktemp -d "$TMP_BASE/order.XXXXXX")
mkdir -p "$order_tmp/round-6"
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$order_tmp/timing-ledger.tsv" mark "Step 5 — code review"
printf '%s\n' 60 > "$order_tmp/round-6/round-start-s"
"$REPO_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" --implement-tmpdir "$order_tmp" --round 6 --start-s 60 --end-s 70
"$REPO_ROOT/scripts/timing-ledger.sh" --ledger "$order_tmp/timing-ledger.tsv" mark "Step 7 — commit review fixes"
awk -F '\t' '
    $2 == "round" && $6 == 6 { round_line=NR }
    $2 == "mark" && $5 == "Step 7 — commit review fixes" { step7_line=NR }
    END { exit (round_line > 0 && step7_line > round_line) ? 0 : 1 }
' "$order_tmp/timing-ledger.tsv"
echo "PASS: test-record-implement-review-round-timing.sh"
