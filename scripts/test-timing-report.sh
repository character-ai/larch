#!/usr/bin/env bash
# Regression tests for scripts/timing-report.sh.

set -euo pipefail

# Hermetic: clear any caller-supplied timing/session env so the test exercises
# the resolver fallback chain deterministically.
unset LARCH_TIMING_LEDGER LARCH_TIMING_SKILL LARCH_TIMING_TASK_KIND \
      IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR SESSION_ENV_PATH || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_BASE=$(mktemp -d "${TMPDIR:-/tmp}/larch-timing-report-test.XXXXXX")
on_err() {
    echo "test-timing-report.sh: FAIL at line $1 (last cmd exit=$2)" >&2
    rm -rf "$TMP_BASE"
}
trap 'on_err "$LINENO" "$?"' ERR
trap 'rm -rf "$TMP_BASE"' EXIT

LEDGER="$TMP_BASE/timing.tsv"
cat > "$LEDGER" <<'EOF'
v1	mark	0	implement	Step 1 — design plan	-	-	-	-	-	-	-	-
v1	mark	10	design	Step 0	-	-	-	-	-	-	-	-
v1	mark	70	design	Step 2a	-	-	-	-	-	-	-	-
v1	mark	130	implement	Step 2 — implementation	-	-	-	-	-	-	-	-
v1	mark	140	review	Step 1 — gather context	-	-	-	-	-	-	-	-
v1	vendor	150	implement	-	codex	codex-implement	100	220	120	out.txt	0	complete
v1	vendor	180	implement	-	codex	codex-implement	120	300	180	out2.txt	0	complete
v1	vendor	185	implement	-	cursor	cursor-review-generic	100	160	60	/tmp/secret/full.txt	1	signal
v1	workflow	240	implement	-	-	-	-	-	-	-	-	HARD
v1	mark	250	implement	Step 3 — checks first pass	-	-	-	-	-	-	-	-
EOF

OUT="$TMP_BASE/report.md"
LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --full --markdown > "$OUT"
grep -Fq '**Workflow path**: HARD' "$OUT"
grep -Fq '| implement | Step 1 — design plan | 00:02:10 |' "$OUT"
grep -Fq '|   ↳ design | Step 0 | 00:01:00 |' "$OUT"
grep -Fq '|   ↳ design | Step 2a | 00:01:00 |' "$OUT"
grep -Fq '| implement | Step 2 — implementation | 00:02:00 |' "$OUT"
grep -Fq '|   ↳ review | Step 1 — gather context | 00:01:50 |' "$OUT"
grep -Fq '| codex | codex-implement | 2 | 2.5 min | 2.0 min-3.0 min |' "$OUT"
grep -Fq '(Failures: 1 cursor-review-generic not included in averages.)' "$OUT"
if grep -Fq '/tmp/secret/full.txt' "$OUT"; then
    echo "absolute output path leaked into timing report" >&2
    exit 1
fi

TERSE=$(LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --since-last-mark --terse)
# Review FINDING_5: terse mode now counts vendor rows whose --end-s ($9) is
# >= the latest mark timestamp, instead of the row's wall-clock log timestamp.
# Fixture has end_s values 220, 300, 160 with last_terse_ts=250, so exactly the
# end_s=300 codex-implement row qualifies (vendor-tasks=1, codex=1).
EXPECTED_TERSE='Step 3 — checks first pass: elapsed=00:01:00 vendor-tasks=1 (codex=1, cursor=0, gemini=0)'
if [[ "$TERSE" != "$EXPECTED_TERSE" ]]; then
  echo "expected terse output:" >&2
  echo "  $EXPECTED_TERSE" >&2
  echo "got:" >&2
  echo "  $TERSE" >&2
  exit 1
fi

TARGET="$TMP_BASE/anchor.md"
cat > "$TARGET" <<'EOF'
before
<!-- timing-report-begin -->
old
<!-- timing-report-end -->
after
EOF
LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --append-timing-section "$TARGET"
FIRST_SHA=$(shasum -a 256 "$TARGET" | awk '{print $1}')
LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --append-timing-section "$TARGET"
SECOND_SHA=$(shasum -a 256 "$TARGET" | awk '{print $1}')
[[ "$FIRST_SHA" == "$SECOND_SHA" ]]

EMPTY="$TMP_BASE/empty.tsv"
: > "$EMPTY"
"$REPO_ROOT/scripts/timing-report.sh" --ledger "$EMPTY" --full --markdown > "$TMP_BASE/empty.out" 2>&1
grep -Fq 'Timing report unavailable' "$TMP_BASE/empty.out"

# Review FINDING_11: --full --output PATH branch is now tested.
OUT_FILE="$TMP_BASE/full-output.md"
[[ ! -e "$OUT_FILE" ]]
LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --full --markdown --output "$OUT_FILE"
[[ -f "$OUT_FILE" ]]
grep -Fq '**Workflow path**: HARD' "$OUT_FILE"
grep -Fq '## Per-Step Durations' "$OUT_FILE"
grep -Fq '## Vendor Task Averages' "$OUT_FILE"
# No leftover .tmp file from the atomic-write rename.
[[ ! -e "${OUT_FILE}.tmp" ]]

# Review FINDING_1: --ledger PATH should accept paths under the same containment
# roots that timing-ledger.sh accepts (not just TMPDIR). Use IMPLEMENT_TMPDIR.
NONTMP_DIR="$TMP_BASE/impl"
mkdir -p "$NONTMP_DIR"
NONTMP_LEDGER="$NONTMP_DIR/timing-ledger.tsv"
cp "$LEDGER" "$NONTMP_LEDGER"
IMPLEMENT_TMPDIR="$NONTMP_DIR" LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$NONTMP_LEDGER" --full --markdown > "$TMP_BASE/nontmp.out"
grep -Fq '**Workflow path**: HARD' "$TMP_BASE/nontmp.out"

echo "PASS: test-timing-report.sh"
