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
    local dir="$1" workflow="$2" codex="$3" cursor="$4"
    mkdir -p "$dir"
    printf '%s\n' "run-xyz" > "$dir/session-id"
    printf '%s\n' "Feature description" > "$dir/feature-description.txt"
    printf '%s\n' "Plan body with enough content to be a real plan for launcher tests." > "$dir/plan.txt"
    {
        printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT"
        printf 'PLAN_FILE=%s\n' "$dir/plan.txt"
        printf 'POST_PLAN_WORKFLOW_PATH=%s\n' "$workflow"
        printf 'CODEX_PRESENT=%s\n' "$codex"
        printf 'CURSOR_PRESENT=%s\n' "$cursor"
        printf 'LARCH_TOKEN_SESSION_ID=%s\n' "run-xyz"
        printf 'LARCH_TIMING_LEDGER=%s\n' "$dir/timing-ledger.tsv"
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
--panel
simple
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
run-xyz" "SIMPLE workflow resolved argv"

echo "=== HARD workflow argv derivation ==="
case_dir="$TMP/hard"
make_tmpdir "$case_dir" HARD false true
argv_file="$TMP/hard.argv"
RUN_STEP5_REVIEW_SH="$SPY" RUN_STEP5_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --round-num 1 >/dev/null
assert_file_equals "$argv_file" "--implement-tmpdir
$case_dir
--mode
diff
--panel
hard
--round-num
1
--round-cap
7
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
--run-id
run-xyz" "HARD workflow resolved argv"

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-run-step5-review.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-run-step5-review.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
