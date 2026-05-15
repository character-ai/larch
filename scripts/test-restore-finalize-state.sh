#!/usr/bin/env bash
# test-restore-finalize-state.sh - offline regression harness for restore-finalize-state.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SUBJECT="$REPO_ROOT/scripts/restore-finalize-state.sh"

[ -x "$SUBJECT" ] || { echo "FAIL: $SUBJECT not executable"; exit 1; }

TMP_BASE="$(mktemp -d /tmp/larch-restore-finalize-state.XXXXXX)"
PASS=0
FAIL=0

cleanup() {
    rm -rf "$TMP_BASE"
}
trap cleanup EXIT

ok() {
    echo "PASS: $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "FAIL: $1"
    FAIL=$((FAIL + 1))
}

assert_rc() {
    local actual=$1 expected=$2 label=$3
    if [ "$actual" -eq "$expected" ]; then
        ok "$label"
    else
        fail "$label (expected rc=$expected got rc=$actual)"
    fi
}

assert_file_line() {
    local file=$1 line=$2 label=$3
    if grep -qxF "$line" "$file"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    /' "$file" 2>/dev/null || true
    fi
}

assert_file_absent() {
    local file=$1 label=$2
    if [ ! -e "$file" ]; then
        ok "$label"
    else
        fail "$label"
    fi
}

assert_file_exists() {
    local file=$1 label=$2
    if [ -f "$file" ]; then
        ok "$label"
    else
        fail "$label"
    fi
}

assert_key_count() {
    local file=$1 expected=$2 label=$3 actual
    actual=$(grep -c '^[A-Z_][A-Z0-9_]*=' "$file" 2>/dev/null || true)
    actual=${actual:-0}
    if [ "$actual" -eq "$expected" ]; then
        ok "$label"
    else
        fail "$label (expected $expected got $actual)"
        sed 's/^/    /' "$file" 2>/dev/null || true
    fi
}

make_tmpdir() {
    mktemp -d "$TMP_BASE/case.XXXXXX"
}

run_subject() {
    local tmpdir=$1 stdout=$2 stderr=$3
    set +e
    "$SUBJECT" --implement-tmpdir "$tmpdir" > "$stdout" 2> "$stderr"
    local rc=$?
    set -e
    printf '%s\n' "$rc"
}

write_partial_state() {
    local file=$1
    cat > "$file" <<'STATE'
BRANCH_NAME=feature/finalize
PR_NUMBER=123
PR_TITLE=Restore finalizer
PR_URL=https://example.invalid/pr/123
ISSUE_NUMBER=456
REPO=owner/repo
DRAFT=false
MERGE=true
DEFERRED=false
REPO_UNAVAILABLE=false
PR_CLOSED=false
BAIL_REASON=needs manual verification
STATE
}

write_complete_state() {
    local file=$1
    cat > "$file" <<'STATE'
BRANCH_NAME=feature/finalize
PR_NUMBER=123
PR_TITLE=Restore finalizer
PR_URL=https://example.invalid/pr/123
ISSUE_NUMBER=456
REPO=owner/repo
DRAFT=false
MERGE=true
DEFERRED=false
REPO_UNAVAILABLE=false
PR_CLOSED=true
DESIGN_ONLY_DONE=true
BAIL_NEEDS_USER_INPUT=false
STALL_TRACKING=false
STALL_STEP=12d
DONE_RENAME_APPLIED=true
RUN_ID=run-123
EXPECTED_SESSION_ID=session-123
EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test-
NO_LOGS_COMMIT=true
BAIL_REASON=complete reason
STATE
}

rc=0
set +e
"$SUBJECT" > "$TMP_BASE/stdout-missing-args" 2> "$TMP_BASE/stderr-missing-args"
rc=$?
set -e
assert_rc "$rc" 2 "missing --implement-tmpdir exits 2"
if grep -qF -- "--implement-tmpdir is required" "$TMP_BASE/stderr-missing-args"; then
    ok "missing --implement-tmpdir emits usage error"
else
    fail "missing --implement-tmpdir emits usage error"
    sed 's/^/    /' "$TMP_BASE/stderr-missing-args"
fi

rc=0
set +e
"$SUBJECT" --implement-tmpdir "$TMP_BASE/absent" > "$TMP_BASE/stdout-missing-dir" 2> "$TMP_BASE/stderr-missing-dir"
rc=$?
set -e
assert_rc "$rc" 2 "missing implement tmpdir exits 2"
if grep -qF -- "--implement-tmpdir must exist" "$TMP_BASE/stderr-missing-dir"; then
    ok "missing implement tmpdir emits usage error"
else
    fail "missing implement tmpdir emits usage error"
    sed 's/^/    /' "$TMP_BASE/stderr-missing-dir"
fi

tmp=$(make_tmpdir)
rc=$(run_subject "$tmp" "$tmp/stdout" "$tmp/stderr")
assert_rc "$rc" 1 "missing ship-pr-state exits 1"
if grep -qF "missing ship-pr state file" "$tmp/stderr"; then
    ok "missing ship-pr-state emits warning"
else
    fail "missing ship-pr-state emits warning"
    sed 's/^/    /' "$tmp/stderr"
fi
assert_file_absent "$tmp/finalize-state.sh" "missing ship-pr-state does not write finalize-state"

tmp=$(make_tmpdir)
write_partial_state "$tmp/ship-pr-state.sh"
printf 'stale=true\n' > "$tmp/finalize-state.sh"
rc=$(run_subject "$tmp" "$tmp/stdout" "$tmp/stderr")
assert_rc "$rc" 0 "partial ship-pr-state restores successfully"
assert_file_exists "$tmp/finalize-state.sh" "partial restore writes finalize-state"
assert_key_count "$tmp/finalize-state.sh" 20 "partial restore writes all finalize keys"
assert_file_line "$tmp/finalize-state.sh" "BRANCH_NAME=feature/finalize" "partial restore preserves branch"
assert_file_line "$tmp/finalize-state.sh" "DESIGN_ONLY_DONE=false" "partial restore defaults DESIGN_ONLY_DONE"
assert_file_line "$tmp/finalize-state.sh" "NO_LOGS_COMMIT=" "partial restore leaves absent NO_LOGS_COMMIT empty"
if [ "$(cat "$tmp/final-bail-reason.txt")" = "needs manual verification" ]; then
    ok "partial restore writes final-bail-reason"
else
    fail "partial restore writes final-bail-reason"
fi

tmp=$(make_tmpdir)
write_complete_state "$tmp/ship-pr-state.sh"
rc=$(run_subject "$tmp" "$tmp/stdout1" "$tmp/stderr1")
assert_rc "$rc" 0 "complete ship-pr-state first restore succeeds"
cp "$tmp/finalize-state.sh" "$tmp/finalize-state.first"
rc=$(run_subject "$tmp" "$tmp/stdout2" "$tmp/stderr2")
assert_rc "$rc" 0 "complete ship-pr-state second restore succeeds"
if cmp -s "$tmp/finalize-state.first" "$tmp/finalize-state.sh"; then
    ok "complete restore is idempotent"
else
    fail "complete restore is idempotent"
    diff -u "$tmp/finalize-state.first" "$tmp/finalize-state.sh" || true
fi
assert_key_count "$tmp/finalize-state.sh" 20 "complete restore writes all finalize keys"
assert_file_line "$tmp/finalize-state.sh" "DESIGN_ONLY_DONE=true" "complete restore preserves DESIGN_ONLY_DONE"
assert_file_line "$tmp/finalize-state.sh" "NO_LOGS_COMMIT=true" "complete restore preserves NO_LOGS_COMMIT"
assert_file_exists "$tmp/finalize-state.sh" "atomic rename leaves finalize-state in place"
if [ "$(cat "$tmp/final-bail-reason.txt")" = "complete reason" ]; then
    ok "complete restore writes final-bail-reason"
else
    fail "complete restore writes final-bail-reason"
fi

if [ "$FAIL" -ne 0 ]; then
    echo "FAIL: $FAIL failed, $PASS passed"
    exit 1
fi

echo "OK: $PASS passed"
