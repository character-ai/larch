#!/usr/bin/env bash
# test-run-step5-review.sh - Regression harness for run-step5-review.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
LAUNCHER="$SCRIPT_DIR/run-step5-review.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-run-step5-review.XXXXXX")"
TMP="$(cd "$TMP" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

pass() {
    printf '  ok: %s\n' "$1"
    PASS=$((PASS + 1))
}

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    FAIL=$((FAIL + 1))
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:400})"
    fi
}

assert_file_equals() {
    local file="$1" expected="$2" label="$3"
    local actual
    actual="$(cat "$file")"
    if [[ "$actual" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label"$'\n'"expected:"$'\n'"$expected"$'\n'"actual:"$'\n'"$actual"
    fi
}

make_tmpdir() {
    local dir="$1" _workflow="$2" codex="$3" cursor="$4" session_id="${5:-run-xyz}" dynamic_archetypes="${6:-}"
    mkdir -p "$dir"
    printf '%s\n' "$session_id" > "$dir/session-id"
    printf '%s\n' "Feature description" > "$dir/feature-description.txt"
    printf '%s\n' "Plan body with enough content to be a real plan for launcher tests." > "$dir/plan.txt"
    {
        printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT"
        printf 'CODEX_PRESENT=%s\n' "$codex"
        printf 'CURSOR_PRESENT=%s\n' "$cursor"
        printf 'LARCH_TOKEN_SESSION_ID=%s\n' "run-xyz"
        printf 'LARCH_TIMING_LEDGER=%s\n' "$dir/timing-ledger.tsv"
        if [[ -n "$dynamic_archetypes" ]]; then
            printf 'LARCH_DYNAMIC_ARCHETYPES_MAX=%s\n' "$dynamic_archetypes"
        fi
    } > "$dir/session-env.sh"
}

SPY="$TMP/review-spy.sh"
cat > "$SPY" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$RUN_STEP5_ARGV_FILE"
printf 'REVIEW_AND_FIX_STATUS=complete\n'
EOF
chmod +x "$SPY"

echo "=== missing required flags ==="
set +e
out="$("$LAUNCHER" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing implement tmpdir exits 2"; else fail "missing implement tmpdir rc=$rc"; fi
assert_contains "$out" "--implement-tmpdir is required" "missing implement tmpdir error"

echo "=== reject invalid round number ==="
case_dir="$TMP/invalid-round"
make_tmpdir "$case_dir" SIMPLE true false
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 0 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "round-num zero exits 2"; else fail "round-num zero rc=$rc"; fi
assert_contains "$out" "--round-num must be a positive integer" "round-num zero error"

echo "=== reject invalid reviewer booleans ==="
case_dir="$TMP/bad-bool"
make_tmpdir "$case_dir" SIMPLE maybe false
set +e
out="$(RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$TMP/bad-bool.argv" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "bad CODEX_PRESENT exits 2"; else fail "bad CODEX_PRESENT rc=$rc"; fi
assert_contains "$out" "CODEX_PRESENT must be true or false" "bad CODEX_PRESENT error"

echo "=== SIMPLE workflow argv derivation ==="
case_dir="$TMP/simple"
make_tmpdir "$case_dir" SIMPLE true false
argv_file="$TMP/simple.argv"
out="$(RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 3)"
assert_contains "$out" "REVIEW_AND_FIX_STATUS=complete" "downstream stdout passes through"
assert_file_equals "$argv_file" "--implement-tmpdir
$case_dir
--mode
diff
--round-num
3
--round-cap
5
--session-env-path
$case_dir/session-env.sh
--codex-available
true
--cursor-available
false
--plan-file
$case_dir/plan.txt
--feature-file
$case_dir/feature-description.txt
--run-id
run-xyz" "conventional plan path resolved argv"

echo "=== HARD workflow argv derivation ==="
case_dir="$TMP/hard"
make_tmpdir "$case_dir" HARD false true "run-xyz" 2
argv_file="$TMP/hard.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 >/dev/null
assert_file_equals "$argv_file" "--implement-tmpdir
$case_dir
--mode
diff
--round-num
1
--round-cap
5
--session-env-path
$case_dir/session-env.sh
--codex-available
false
--cursor-available
true
--plan-file
$case_dir/plan.txt
--feature-file
$case_dir/feature-description.txt
--dynamic-archetypes
2
--run-id
run-xyz" "HARD workflow resolved argv"

echo "=== degraded prior rounds extend effective round cap ==="
case_dir="$TMP/degraded-cap"
make_tmpdir "$case_dir" SIMPLE true false
mkdir -p "$case_dir/round-1" "$case_dir/round-2"
printf 'DEGRADED_ROUND=true\n' > "$case_dir/round-1/review-and-fix.env"
printf 'DEGRADED_ROUND=false\n' > "$case_dir/round-2/review-and-fix.env"
argv_file="$TMP/degraded-cap.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 3 >/dev/null
assert_contains "$(cat "$argv_file")" "--round-cap
6" "degraded prior rounds add back onto unified base round cap"

echo "=== canonical RUN_ID prefers sentinel over session-id ==="
case_dir="$TMP/run-id-sentinel"
make_tmpdir "$case_dir" SIMPLE true false "session-only"
cat > "$case_dir/parent-issue.md" <<'EOF'
ISSUE_NUMBER=456
RUN_ID=review-custom-run
ADOPTED=true
EOF
argv_file="$TMP/run-id-sentinel.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 2 >/dev/null
assert_contains "$(cat "$argv_file")" "review-custom-run" "sentinel RUN_ID overrides session-id"

echo "=== canonical RUN_ID falls back to manifest when sentinel missing ==="
case_dir="$TMP/run-id-manifest"
make_tmpdir "$case_dir" SIMPLE true false "session-only"
mkdir -p "$case_dir/larch-logs/implement/review-manifest-run"
printf '{}\n' > "$case_dir/larch-logs/implement/review-manifest-run/manifest.json"
argv_file="$TMP/run-id-manifest.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 2 >/dev/null
assert_contains "$(cat "$argv_file")" "review-manifest-run" "manifest RUN_ID overrides session-id"

echo "=== conventional plan.txt missing: fail closed even when design-export/plan.txt exists ==="
case_dir="$TMP/plan-file-missing"
make_tmpdir "$case_dir" SIMPLE true false
rm -f "$case_dir/plan.txt"
mkdir -p "$case_dir/design-export"
printf '%s\n' "Stale local export must not substitute for conventional plan.txt." > "$case_dir/design-export/plan.txt"
argv_file="$TMP/missing-plan.argv"
set +e
out="$(RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "step5: conventional plan.txt missing exits 2 even with design-export"; else fail "step5 plan missing rc=$rc"; fi
assert_contains "$out" "plan file not found at conventional path" "step5 emits conventional-path error"
[[ ! -f "$argv_file" ]] || fail "review helper should not run when plan.txt missing"

echo "=== conventional plan.txt missing AND design-export missing: fail loud ==="
case_dir="$TMP/plan-file-fail"
make_tmpdir "$case_dir" SIMPLE true false
rm -f "$case_dir/plan.txt"
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "step5: no conventional plan.txt exits 2"; else fail "step5 no-plan rc=$rc"; fi
assert_contains "$out" "plan file not found at conventional path" "step5 no-plan error"

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-run-step5-review.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-run-step5-review.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
