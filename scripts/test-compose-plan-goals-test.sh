#!/usr/bin/env bash
# test-compose-plan-goals-test.sh — regression tests for compose-plan-goals-test.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
COMPOSER="$SCRIPT_DIR/compose-plan-goals-test.sh"

[ -x "$COMPOSER" ] || { echo "FAIL: $COMPOSER not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-compose-plan-goals-test.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

fail() {
    echo "FAIL: $1" >&2
    FAIL=$((FAIL + 1))
}

pass() {
    echo "  ok: $1"
    PASS=$((PASS + 1))
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:400})"
    fi
}

assert_occurrences() {
    local haystack="$1" needle="$2" expected="$3" label="$4"
    local count
    count="$(printf '%s' "$haystack" | grep -F -c "$needle" || true)"
    if [ "$count" -eq "$expected" ]; then
        pass "$label"
    else
        fail "$label (expected $expected occurrences of $needle; got $count)"
    fi
}

assert_fails() {
    local label="$1"
    shift
    set +e
    "$@" >/dev/null 2>&1
    local rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        pass "$label"
    else
        fail "$label"
    fi
}

echo "=== normal plan with test-plan section ==="
plan="$TMP/plan-with-test.md"
cat > "$plan" <<'EOF'
Update the larch log plan-goals composition path so the implementation plan is
materialized from the file-backed design export instead of being summarized as a
pointer. Add a composer script, wire the sanitizer, and update the harnesses.

## Test plan
Run scripts/test-compose-plan-goals-test.sh and scripts/test-larch-logs-batches.sh.
EOF
out="$("$COMPOSER" --plan-file "$plan" --goal-text "Prevent pointer-only plans")"
assert_contains "$out" "## Goal" "goal heading present"
assert_contains "$out" "Prevent pointer-only plans" "goal text present"
assert_contains "$out" "## Implementation Plan" "implementation heading present"
assert_contains "$out" "## Test plan" "test heading present"
assert_contains "$out" "Run scripts/test-compose-plan-goals-test.sh" "test plan extracted"

echo "=== normal plan without test-plan section ==="
plan="$TMP/plan-without-test.md"
cat > "$plan" <<'EOF'
Add a focused helper for composing the plan-goals-test batch. The helper validates
that the plan artifact exists and is substantive, then emits the expected
section structure for downstream larch-log validation.
EOF
out="$("$COMPOSER" --plan-file "$plan")"
assert_contains "$out" "(no test plan section in plan-file)" "fallback test plan emitted"

echo "=== plan with implementation-plan header does not duplicate heading ==="
plan="$TMP/plan-with-implementation-heading.md"
cat > "$plan" <<'EOF'
## Implementation Plan
Update the composer so it normalizes the file-backed design export under the
single wrapper heading emitted by the larch-log batch payload.

## Test plan
Run scripts/test-compose-plan-goals-test.sh.
EOF
out="$("$COMPOSER" --plan-file "$plan")"
assert_occurrences "$out" "## Implementation Plan" 1 "implementation heading emitted once"

echo "=== verification heading extracts test plan and stops at next heading ==="
plan="$TMP/plan-with-verification.md"
cat > "$plan" <<'EOF'
Update the composer so plans that use verification terminology still populate
the larch-log test-plan section with concrete operator checks.

### Verification
Run scripts/test-compose-plan-goals-test.sh.

### Follow-up
This section belongs to the implementation body, not the test-plan extraction.
EOF
out="$("$COMPOSER" --plan-file "$plan")"
assert_contains "$out" "Run scripts/test-compose-plan-goals-test.sh." "verification section extracted"
if [[ "$out" == *"## Test plan"* && "${out##*## Test plan}" != *"This section belongs"* ]]; then
    pass "verification extraction stops at next heading"
else
    fail "verification extraction stops at next heading"
fi

echo "=== testing heading extracts test plan ==="
plan="$TMP/plan-with-testing.md"
cat > "$plan" <<'EOF'
Update the composer so plans that use alternate test section headings still
produce a normalized larch-log payload for downstream validation.

## Testing
Run make test-compose-plan-goals-test.
EOF
out="$("$COMPOSER" --plan-file "$plan")"
assert_contains "$out" "Run make test-compose-plan-goals-test." "testing section extracted"

echo "=== verification without implementation heading emits one wrapper heading ==="
plan="$TMP/plan-verification-no-implementation-heading.md"
cat > "$plan" <<'EOF'
Update the composer while leaving source plans free to omit an explicit
implementation-plan heading, because the batch payload supplies that wrapper.

### Verification
Run scripts/test-compose-plan-goals-test.sh.
EOF
out="$("$COMPOSER" --plan-file "$plan")"
assert_occurrences "$out" "## Implementation Plan" 1 "wrapper heading emitted once without source heading"

echo "=== test-strategy heading extracts test plan ==="
plan="$TMP/plan-with-test-strategy.md"
cat > "$plan" <<'EOF'
Update the composer so plans that use test-strategy terminology still populate
the larch-log test-plan section with concrete operator checks.

## Test strategy
Run make test-compose-plan-goals-test and verify output structure.
EOF
out="$("$COMPOSER" --plan-file "$plan")"
assert_contains "$out" "Run make test-compose-plan-goals-test and verify output structure." "test strategy section extracted"

echo "=== verification-strategy heading extracts test plan ==="
plan="$TMP/plan-with-verification-strategy.md"
cat > "$plan" <<'EOF'
Update the composer so plans that use verification-strategy terminology still
populate the larch-log test-plan section with concrete operator checks.

### Verification strategy
Run bash scripts/test-compose-plan-goals-test.sh and confirm all assertions pass.
EOF
out="$("$COMPOSER" --plan-file "$plan")"
assert_contains "$out" "Run bash scripts/test-compose-plan-goals-test.sh and confirm all assertions pass." "verification strategy section extracted"

echo "=== short plan fails ==="
plan="$TMP/short.md"
printf 'short plan body\n' > "$plan"
assert_fails "short plan exits non-zero" "$COMPOSER" --plan-file "$plan"

echo "=== pointer-only plan fails ==="
plan="$TMP/pointer.md"
printf 'See plan.txt\n' > "$plan"
assert_fails "pointer-only plan exits non-zero" "$COMPOSER" --plan-file "$plan"

echo "=== empty plan fails ==="
plan="$TMP/empty.md"
: > "$plan"
assert_fails "empty plan exits non-zero" "$COMPOSER" --plan-file "$plan"

echo "=== missing plan fails ==="
assert_fails "missing plan exits non-zero" "$COMPOSER" --plan-file "$TMP/missing.md"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
