#!/usr/bin/env bash
# test-run-step2-dispatch.sh - Regression harness for run-step2-dispatch.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
LAUNCHER="$SCRIPT_DIR/run-step2-dispatch.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-run-step2-dispatch.XXXXXX")"
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
    local dir="$1" workflow="$2" cursor="$3"
    mkdir -p "$dir"
    printf '%s\n' "Feature description" > "$dir/feature-description.txt"
    printf '%s\n' "Plan body with enough text for the Step 2 launcher harness." > "$dir/plan.txt"
    {
        printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT"
        printf 'PLAN_FILE=%s\n' "$dir/plan.txt"
        printf 'POST_PLAN_WORKFLOW_PATH=%s\n' "$workflow"
        printf 'CURSOR_PRESENT=%s\n' "$cursor"
    } > "$dir/session-env.sh"
}

SPY="$TMP/step2-spy.sh"
cat > "$SPY" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$RUN_STEP2_ARGV_FILE"
printf 'STATUS=claude_fallback\n'
printf 'ORCHESTRATOR_EDIT_AUTHORITY=allowed\n'
EOF
chmod +x "$SPY"

echo "=== missing required flags ==="
set +e
out="$("$LAUNCHER" --coder codex 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing implement tmpdir exits 2"; else fail "missing implement tmpdir rc=$rc"; fi
assert_contains "$out" "--implement-tmpdir is required" "missing implement tmpdir error"

echo "=== reject invalid workflow enum ==="
case_dir="$TMP/bad-workflow"
make_tmpdir "$case_dir" BROKEN false
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --coder codex 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "bad workflow exits 2"; else fail "bad workflow rc=$rc"; fi
assert_contains "$out" "POST_PLAN_WORKFLOW_PATH must be SIMPLE or HARD" "bad workflow error"

echo "=== reject missing answers path ==="
case_dir="$TMP/missing-answers"
make_tmpdir "$case_dir" HARD false
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --coder codex --answers "$case_dir/nope.json" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing answers exits 2"; else fail "missing answers rc=$rc"; fi
assert_contains "$out" "--answers path does not exist" "missing answers error"

echo "=== first dispatch argv derivation ==="
case_dir="$TMP/case"
make_tmpdir "$case_dir" HARD false
argv_file="$TMP/step2.argv"
out="$(RUN_STEP2_IMPLEMENT_SH="$SPY" RUN_STEP2_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --coder cursor)"
assert_contains "$out" "STATUS=claude_fallback" "downstream stdout passes through"
assert_file_equals "$argv_file" "--tmpdir
$case_dir
--plan-file
$case_dir/plan.txt
--feature-file
$case_dir/feature-description.txt
--coder
cursor
--cursor-present
false
--workflow
HARD" "first dispatch argv derived"

echo "=== answers pass-through exception ==="
answers="$case_dir/codex-answers-1.json"
printf '{"answers":[]}\n' > "$answers"
RUN_STEP2_IMPLEMENT_SH="$SPY" RUN_STEP2_ARGV_FILE="$argv_file" "$LAUNCHER" --implement-tmpdir "$case_dir" --coder codex --answers "$answers" >/dev/null
assert_file_equals "$argv_file" "--tmpdir
$case_dir
--plan-file
$case_dir/plan.txt
--feature-file
$case_dir/feature-description.txt
--coder
codex
--cursor-present
false
--workflow
HARD
--answers
$answers" "answers argv passed explicitly"

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-run-step2-dispatch.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-run-step2-dispatch.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
