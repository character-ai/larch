#!/usr/bin/env bash
# Regression tests for scripts/timing-report.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

# Hermetic: clear any caller-supplied timing/session env so the test exercises
# the resolver fallback chain deterministically.
unset LARCH_TIMING_LEDGER LARCH_TIMING_SKILL LARCH_TIMING_TASK_KIND \
      IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR SESSION_ENV_PATH \
      LARCH_TIMING_OUTLIER_THRESHOLD_S || true

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

JSON_OUT="$TMP_BASE/report.json"
LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --full --format json --output "$JSON_OUT"
jq -e '
  .workflow_path == "HARD" and
  .total_seconds == 250 and
  .total_hms == "00:04:10" and
  (.per_step | length) == 6 and
  (.per_step[] | select(.skill == "implement" and .step == "Step 2 — implementation" and .duration_seconds == 120)) and
  (.vendor_task_averages[] | select(.vendor == "codex" and .task_kind == "codex-implement" and .samples == 2 and .min_seconds == 120 and .max_seconds == 180))
' "$JSON_OUT" >/dev/null


ROUND_LEDGER="$TMP_BASE/rounds.tsv"
cat > "$ROUND_LEDGER" <<'EOF'
v1	mark	0	implement	Step 4 — preflight	-	-	-	-	-	-	-	-
v1	mark	10	implement	Step 5 — code review	-	-	-	-	-	-	-	-
v1	round	15	implement	Step 5 — code review	2	15	20	5	4	1	-	-
v1	round	12	implement	Step 5 — code review	1	12	14	2	2	3	-	-
v1	round	25	implement	Step 6 — checks	3	25	26	1	9	9	-	-
v1	mark	30	implement	Step 7 — commit	-	-	-	-	-	-	-	-
v1	round	35	implement	Step 5 — code review	4	35	40	5	8	8	-	-
v1	mark	45	implement	Step 5 — code review	-	-	-	-	-	-	-	-
v1	round	46	implement	Step 5 — code review	5	46	49	3	1	0	-	-
v1	mark	60	implement	Step 8 — ship	-	-	-	-	-	-	-	-
v1	mark	70	design	design Step 3 — plan review	-	-	-	-	-	-	-	-
v1	round	72	design	design Step 3 — plan review	1	72	80	8	3	2	1	-
v1	mark	90	design	design Step 3.5 — gate B	-	-	-	-	-	-	-	-
EOF
ROUND_JSON="$TMP_BASE/rounds.json"
LARCH_TEST_TIMING_NOW=100 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$ROUND_LEDGER" --full --format json --output "$ROUND_JSON"
jq -e '
  (.per_step[] | select(.skill == "implement" and .step == "Step 5 — code review" and .duration_seconds == 20) | .rounds == [
    {"round":1,"duration_seconds":2,"accepted":2,"rejected":3},
    {"round":2,"duration_seconds":5,"accepted":4,"rejected":1}
  ]) and
  (.per_step[] | select(.skill == "implement" and .step == "Step 5 — code review" and .duration_seconds == 15) | .rounds == [
    {"round":5,"duration_seconds":3,"accepted":1,"rejected":0}
  ]) and
  (.per_step[] | select(.skill == "implement" and .step == "Step 7 — commit") | has("rounds") | not) and
  (.per_step[] | select(.skill == "design" and .step == "design Step 3 — plan review") | .rounds == [
    {"round":1,"duration_seconds":8,"accepted":3,"rejected":2,"oos":1}
  ])
' "$ROUND_JSON" >/dev/null
ROUND_MD="$TMP_BASE/rounds.md"
LARCH_TEST_TIMING_NOW=100 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$ROUND_LEDGER" --full --markdown > "$ROUND_MD"
if grep -Fq 'rounds' "$ROUND_MD"; then
    echo "round rows leaked into markdown timing report" >&2
    exit 1
fi
NO_PARENT_LEDGER="$TMP_BASE/no-parent-round.tsv"
cat > "$NO_PARENT_LEDGER" <<'EOF'
v1	round	10	implement	Step 5 — code review	1	10	12	2	1	0	-	-
v1	mark	20	implement	Step 6 — checks	-	-	-	-	-	-	-	-
EOF
NO_PARENT_JSON="$TMP_BASE/no-parent-round.json"
LARCH_TEST_TIMING_NOW=30 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$NO_PARENT_LEDGER" --full --format json --output "$NO_PARENT_JSON"
jq -e '(.per_step[] | has("rounds") | not)' "$NO_PARENT_JSON" >/dev/null

NESTED_LEDGER="$TMP_BASE/nested-child.tsv"
cat > "$NESTED_LEDGER" <<'EOF'
v1	mark	0	implement	Step 2 — implementation	-	-	-	-	-	-	-	-
v1	mark	20	design	design Step 3 — plan review	-	-	-	-	-	-	-	-
v1	round	25	design	design Step 3 — plan review	1	22	30	8	3	2	1	-
v1	mark	100	implement	Step 3 — checks	-	-	-	-	-	-	-	-
EOF
NESTED_JSON="$TMP_BASE/nested-child.json"
LARCH_TEST_TIMING_NOW=110 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$NESTED_LEDGER" --full --format json --output "$NESTED_JSON"
jq -e '
  (.per_step[] | select(.skill == "design" and .step == "design Step 3 — plan review") | .rounds == [
    {"round":1,"duration_seconds":8,"accepted":3,"rejected":2,"oos":1}
  ]) and
  (.per_step[] | select(.skill == "implement" and .step == "Step 2 — implementation") | has("rounds") | not)
' "$NESTED_JSON" >/dev/null

V2_DIR="$TMP_BASE/design-v2"
mkdir -p "$V2_DIR"
V2_LEDGER="$V2_DIR/timing.tsv"
cat > "$V2_LEDGER" <<'EOF'
v1	mark	10	design	Step 0	-	-	-	-	-	-	-	-
v1	mark	70	design	Step 2a	-	-	-	-	-	-	-	-
EOF
cat > "$V2_DIR/run-params.json" <<'EOF'
{"schema_version":2,"design_classification":"SIMPLE","partition_requested":false,"brainstorm_requested":false}
EOF
LARCH_TEST_TIMING_NOW=130 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$V2_LEDGER" --full --markdown > "$TMP_BASE/v2.out"
grep -Fq '**Workflow path**: SIMPLE' "$TMP_BASE/v2.out"
V2_JSON="$TMP_BASE/v2.json"
LARCH_TEST_TIMING_NOW=130 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$V2_LEDGER" --full --format json --output "$V2_JSON"
jq -e '.workflow_path == "SIMPLE"' "$V2_JSON" >/dev/null

V1_PATH_DIR="$TMP_BASE/design-v1-path"
mkdir -p "$V1_PATH_DIR"
V1_PATH_LEDGER="$V1_PATH_DIR/timing.tsv"
cat > "$V1_PATH_LEDGER" <<'EOF'
v1	mark	10	design	Step 0	-	-	-	-	-	-	-	-
v1	mark	70	design	Step 2a	-	-	-	-	-	-	-	-
EOF
cat > "$V1_PATH_DIR/run-params.json" <<'EOF'
{"schema_version":1,"design_classification":"SIMPLE","workflow_path":"SIMPLE","partition_requested":false}
EOF
LARCH_TEST_TIMING_NOW=130 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$V1_PATH_LEDGER" --full --markdown > "$TMP_BASE/v1-path.out"
grep -Fq '**Workflow path**: SIMPLE' "$TMP_BASE/v1-path.out"
V1_PATH_JSON="$TMP_BASE/v1-path.json"
LARCH_TEST_TIMING_NOW=130 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$V1_PATH_LEDGER" --full --format json --output "$V1_PATH_JSON"
jq -e '.workflow_path == "SIMPLE"' "$V1_PATH_JSON" >/dev/null

TERSE=$(LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --since-last-mark --terse)
# Review FINDING_5: terse mode now counts vendor rows whose --end-s ($9) is
# >= the latest mark timestamp, instead of the row's wall-clock log timestamp.
# Fixture has end_s values 220, 300, 160 with last_terse_ts=250, so exactly the
# end_s=300 codex-implement row qualifies (vendor-tasks=1, codex=1).
EXPECTED_TERSE='Step 3 — checks first pass: elapsed=00:01:00 vendor-tasks=1 (codex=1, cursor=0)'
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

# --- --summary mode ---

# Case 1: normal summary — Total: prefix + correct elapsed + vendor-tasks parenthetical.
# Fixture: LEDGER (2 codex + 1 cursor tasks, all end_s >= mark_ts[1]=0), now=310.
# elapsed = 310 - 0 = 310 s = 00:05:10; codex=2, cursor=1 → vendor-tasks=3.
SUMMARY_OUT=$(LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --summary)
expected_summary="Total: elapsed=00:05:10 vendor-tasks=3 (codex=2, cursor=1)"
if [[ "$SUMMARY_OUT" == "$expected_summary" ]]; then
    echo "PASS: summary normal"
else
    echo "FAIL: summary normal: expected '$expected_summary' got '$SUMMARY_OUT'" >&2
    exit 1
fi

# Case 2: zero-vendor summary — parenthetical shows all zeros.
# Build a mark-only ledger (no vendor rows); now=150 gives elapsed=00:02:30.
SUMMARY_NO_VENDOR_LEDGER="$TMP_BASE/summary-no-vendor.tsv"
cat > "$SUMMARY_NO_VENDOR_LEDGER" <<'EOF'
v1	mark	0	implement	Step 1 — design plan	-	-	-	-	-	-	-	-
v1	mark	100	implement	Step 2 — implementation	-	-	-	-	-	-	-	-
EOF
SUMMARY_NO_VENDOR_OUT=$(LARCH_TEST_TIMING_NOW=150 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$SUMMARY_NO_VENDOR_LEDGER" --summary)
expected_summary_no_vendor="Total: elapsed=00:02:30 vendor-tasks=0 (codex=0, cursor=0)"
if [[ "$SUMMARY_NO_VENDOR_OUT" == "$expected_summary_no_vendor" ]]; then
    echo "PASS: summary zero-vendor"
else
    echo "FAIL: summary zero-vendor: expected '$expected_summary_no_vendor' got '$SUMMARY_NO_VENDOR_OUT'" >&2
    exit 1
fi

# Case 3: no-marks ledger — prints unavailable warning to stderr and exits 0.
NO_MARKS_SUMMARY_ERR=$("$REPO_ROOT/scripts/timing-report.sh" --ledger "$EMPTY" --summary 2>&1)
if [[ "$NO_MARKS_SUMMARY_ERR" == "Timing report unavailable: no step marks in ledger" ]]; then
    echo "PASS: summary no-marks unavailable"
else
    echo "FAIL: summary no-marks unavailable: got '$NO_MARKS_SUMMARY_ERR'" >&2
    exit 1
fi

# --- Outlier detection ---

# Case 1: step duration exceeds default 4h threshold (14400 s).
# Build a ledger with one normal step (10 s) and one outlier step (50000 s ~= 13h 53m).
OUTLIER_LEDGER="$TMP_BASE/outlier.tsv"
cat > "$OUTLIER_LEDGER" <<'EOF'
v1	mark	0	implement	Step 1 — design plan	-	-	-	-	-	-	-	-
v1	mark	10	implement	Step 2 — implementation	-	-	-	-	-	-	-	-
v1	mark	50010	implement	Step 3 — checks first pass	-	-	-	-	-	-	-	-
EOF
OUTLIER_OUT="$TMP_BASE/outlier.md"
LARCH_TEST_TIMING_NOW=50020 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$OUTLIER_LEDGER" --full --markdown > "$OUTLIER_OUT"
# Normal step must NOT be tagged
if grep -q 'Step 1 — design plan.*\[OUTLIER\]' "$OUTLIER_OUT"; then
    echo "FAIL: outlier: normal step tagged as OUTLIER" >&2
    exit 1
fi
echo "PASS: outlier normal step not tagged"
# Outlier step must be tagged
grep -q 'Step 2 — implementation.*\[OUTLIER\]' "$OUTLIER_OUT" || { echo "FAIL: outlier step not tagged" >&2; exit 1; }
echo "PASS: outlier step tagged"
# Outlier note line must appear
grep -q '\*Outlier steps:' "$OUTLIER_OUT" || { echo "FAIL: outlier note line missing" >&2; exit 1; }
echo "PASS: outlier note present"

# Case 2: custom threshold via LARCH_TIMING_OUTLIER_THRESHOLD_S — 100 s makes
# the 10-second first step non-outlier and the 50000-second second step an outlier.
OUTLIER_CUSTOM_OUT="$TMP_BASE/outlier-custom.md"
LARCH_TEST_TIMING_NOW=50020 LARCH_TIMING_OUTLIER_THRESHOLD_S=100 \
  "$REPO_ROOT/scripts/timing-report.sh" --ledger "$OUTLIER_LEDGER" --full --markdown > "$OUTLIER_CUSTOM_OUT"
grep -q 'Step 2 — implementation.*\[OUTLIER\]' "$OUTLIER_CUSTOM_OUT" || { echo "FAIL: outlier custom threshold: step not tagged" >&2; exit 1; }
echo "PASS: outlier custom threshold"

# Case 2b: child row (design) whose duration exceeds threshold is also tagged.
CHILD_OUTLIER_LEDGER="$TMP_BASE/child-outlier.tsv"
cat > "$CHILD_OUTLIER_LEDGER" <<'EOF'
v1	mark	0	implement	Step 1 — design plan	-	-	-	-	-	-	-	-
v1	mark	20	design	Step 0 sketch	-	-	-	-	-	-	-	-
v1	mark	50020	implement	Step 2 — implementation	-	-	-	-	-	-	-	-
EOF
CHILD_OUTLIER_OUT="$TMP_BASE/child-outlier.md"
LARCH_TEST_TIMING_NOW=50030 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$CHILD_OUTLIER_LEDGER" --full --markdown > "$CHILD_OUTLIER_OUT"
grep -q 'Step 0 sketch.*\[OUTLIER\]' "$CHILD_OUTLIER_OUT" || { echo "FAIL: child outlier step not tagged" >&2; exit 1; }
echo "PASS: child row outlier tagged"

# Case 3: no steps exceed threshold — no outlier note.
LARCH_TEST_TIMING_NOW=310 "$REPO_ROOT/scripts/timing-report.sh" --ledger "$LEDGER" --full --markdown > "$TMP_BASE/no-outlier.md"
if grep -q '\*Outlier steps:' "$TMP_BASE/no-outlier.md"; then
    echo "FAIL: outlier note present when no outliers" >&2
    exit 1
fi
echo "PASS: no outlier note when no outliers"

echo "PASS: test-timing-report.sh"
