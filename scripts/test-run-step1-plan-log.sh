#!/usr/bin/env bash
# test-run-step1-plan-log.sh - Regression harness for run-step1-plan-log.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
LAUNCHER="$SCRIPT_DIR/run-step1-plan-log.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-run-step1-plan-log.XXXXXX")"
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
    local dir="$1" session_id="${2:-run-plan}"
    mkdir -p "$dir"
    printf '%s\n' "$session_id" > "$dir/session-id"
    printf '%s\n' "Implementation plan body with enough text for the launcher harness." > "$dir/plan.txt"
    {
        printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT"
    } > "$dir/session-env.sh"
}

COMPOSE_SPY="$TMP/compose-spy.sh"
cat > "$COMPOSE_SPY" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$RUN_STEP1_COMPOSE_ARGV_FILE"
printf '## Goal\nSpy goal\n\n## Implementation Plan\nSpy plan\n\n## Test plan\nSpy test\n'
EOF
chmod +x "$COMPOSE_SPY"

LOG_SPY="$TMP/larch-log-spy.sh"
cat > "$LOG_SPY" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$RUN_STEP1_LOG_ARGV_FILE"
printf 'LOG_WRITTEN=true\n'
EOF
chmod +x "$LOG_SPY"

echo "=== missing required flags ==="
set +e
out="$("$LAUNCHER" --implement-tmpdir "$TMP/nope" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "missing goal-text exits 2"; else fail "missing goal-text rc=$rc"; fi
assert_contains "$out" "--goal-text is required" "missing goal-text error"

echo "=== reject unknown option ==="
set +e
out="$("$LAUNCHER" --implement-tmpdir "$TMP/nope" --goal-text hi --bogus 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "unknown option exits 2"; else fail "unknown option rc=$rc"; fi
assert_contains "$out" "unknown option: --bogus" "unknown option error"

echo "=== compose and larch-log argv derivation ==="
case_dir="$TMP/case"
make_tmpdir "$case_dir"
compose_argv="$TMP/compose.argv"
log_argv="$TMP/log.argv"
out="$(RUN_STEP1_COMPOSE_SH="$COMPOSE_SPY" RUN_STEP1_LARCH_LOG_SH="$LOG_SPY" RUN_STEP1_COMPOSE_ARGV_FILE="$compose_argv" RUN_STEP1_LOG_ARGV_FILE="$log_argv" "$LAUNCHER" --implement-tmpdir "$case_dir" --goal-text "Ship launcher")"
assert_contains "$out" "LOG_WRITTEN=true" "larch-log stdout passes through"
assert_file_equals "$compose_argv" "--plan-file
$case_dir/plan.txt
--goal-text
Ship launcher" "compose argv derived"
assert_file_equals "$case_dir/plan-goals-test.md" "## Goal
Spy goal

## Implementation Plan
Spy plan

## Test plan
Spy test" "composed output written to conventional path"
assert_file_equals "$log_argv" "write
--log-root
$case_dir/larch-logs
--skill
implement
--run-id
run-plan
--batch
plan-goals-test
--input-file
$case_dir/plan-goals-test.md" "larch-log argv derived"

echo "=== canonical RUN_ID prefers sentinel over session-id ==="
case_dir="$TMP/run-id-sentinel"
make_tmpdir "$case_dir" "session-only"
cat > "$case_dir/parent-issue.md" <<'EOF'
ISSUE_NUMBER=123
RUN_ID=custom-run
ADOPTED=false
EOF
compose_argv="$TMP/compose-sentinel.argv"
log_argv="$TMP/log-sentinel.argv"
RUN_STEP1_COMPOSE_SH="$COMPOSE_SPY" RUN_STEP1_LARCH_LOG_SH="$LOG_SPY" RUN_STEP1_COMPOSE_ARGV_FILE="$compose_argv" RUN_STEP1_LOG_ARGV_FILE="$log_argv" "$LAUNCHER" --implement-tmpdir "$case_dir" --goal-text "Ship sentinel" >/dev/null
assert_contains "$(cat "$log_argv")" "custom-run" "sentinel RUN_ID overrides session-id"

echo "=== canonical RUN_ID falls back to manifest when sentinel missing ==="
case_dir="$TMP/run-id-manifest"
make_tmpdir "$case_dir" "session-only"
mkdir -p "$case_dir/larch-logs/implement/manifest-run"
printf '{}\n' > "$case_dir/larch-logs/implement/manifest-run/manifest.json"
compose_argv="$TMP/compose-manifest.argv"
log_argv="$TMP/log-manifest.argv"
RUN_STEP1_COMPOSE_SH="$COMPOSE_SPY" RUN_STEP1_LARCH_LOG_SH="$LOG_SPY" RUN_STEP1_COMPOSE_ARGV_FILE="$compose_argv" RUN_STEP1_LOG_ARGV_FILE="$log_argv" "$LAUNCHER" --implement-tmpdir "$case_dir" --goal-text "Ship manifest" >/dev/null
assert_contains "$(cat "$log_argv")" "manifest-run" "manifest RUN_ID overrides session-id"

echo "=== conventional plan.txt missing: fail closed even when design-export/plan.txt exists ==="
case_dir="$TMP/plan-file-missing"
make_tmpdir "$case_dir"
rm -f "$case_dir/plan.txt"
mkdir -p "$case_dir/design-export"
printf '%s\n' "Stale local export must not substitute for conventional plan.txt." > "$case_dir/design-export/plan.txt"
compose_argv="$TMP/compose-missing.argv"
log_argv="$TMP/log-missing.argv"
set +e
out="$(RUN_STEP1_COMPOSE_SH="$COMPOSE_SPY" RUN_STEP1_LARCH_LOG_SH="$LOG_SPY" RUN_STEP1_COMPOSE_ARGV_FILE="$compose_argv" RUN_STEP1_LOG_ARGV_FILE="$log_argv" "$LAUNCHER" --implement-tmpdir "$case_dir" --goal-text "Should fail" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "conventional plan.txt missing exits 2 even with design-export"; else fail "plan missing rc=$rc"; fi
assert_contains "$out" "plan file not found at conventional path" "step1 emits conventional-path error"
[[ ! -f "$compose_argv" ]] || fail "compose helper should not run when plan.txt missing"

echo "=== issue-anchored Step 1 plan copy contract (SKILL pin) ==="
plan_copy_literal=$'cp "$PREFLIGHT_TMPDIR/plan-from-issue.txt" "$IMPLEMENT_TMPDIR/plan.txt"'
grep -Fq "$plan_copy_literal" "$REPO_ROOT/skills/implement/SKILL.md" \
  || fail "missing Step 1 issue-body plan materialization copy literal in implement SKILL"

echo "=== conventional plan.txt missing AND design-export missing: fail loud ==="
case_dir="$TMP/plan-file-fail"
make_tmpdir "$case_dir"
rm -f "$case_dir/plan.txt"
set +e
out="$("$LAUNCHER" --implement-tmpdir "$case_dir" --goal-text "Should fail" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then pass "no conventional plan.txt exits 2"; else fail "no fallback rc=$rc"; fi
assert_contains "$out" "plan file not found at conventional path" "no-plan error"

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-run-step1-plan-log.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-run-step1-plan-log.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
