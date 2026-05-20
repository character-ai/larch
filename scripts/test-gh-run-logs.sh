#!/usr/bin/env bash
# test-gh-run-logs.sh — Regression tests for scripts/gh-run-logs.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/gh-run-logs.sh"
TMPDIR_BASE="$(mktemp -d "${TMPDIR:-/tmp}/test-gh-run-logs.XXXXXX")"
PASS_COUNT=0
FAIL_COUNT=0

cleanup() {
    rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

ok() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

assert_rc() {
    local label=$1 actual=$2 expected=$3
    if [ "$actual" = "$expected" ]; then
        ok "$label"
    else
        fail "$label (expected exit $expected, got $actual)"
    fi
}

assert_contains() {
    local label=$1 file=$2 needle=$3
    if grep -Fq -- "$needle" "$file"; then
        ok "$label"
    else
        fail "$label (needle not found: $needle)"
        sed 's/^/    /' "$file" || true
    fi
}

# --------------------------------------------------------------------------
# Helpers

write_subject() {
    local root=$1
    mkdir -p "$root/scripts"
    cp "$SCRIPT" "$root/scripts/gh-run-logs.sh"
    chmod +x "$root/scripts/gh-run-logs.sh"
}

write_gh_stub() {
    local root=$1 output=$2 exit_code=$3
    cat > "$root/scripts/gh" << SH
#!/usr/bin/env bash
printf '%s\n' "$output"
exit $exit_code
SH
    chmod +x "$root/scripts/gh"
}

run_script() {
    local root=$1 run_id=$2 repo=$3 out_file=$4 rc_var=$5
    local script_rc=0
    PATH="$root/scripts:$PATH" "$root/scripts/gh-run-logs.sh" \
        --run-id "$run_id" --repo "$repo" > "$out_file" 2>&1 || script_rc=$?
    printf -v "$rc_var" '%s' "$script_rc"
}

# --------------------------------------------------------------------------
# Test 1: in-progress response → exit 3

echo "--- Test 1: in-progress response → exit 3 ---"
T1="$TMPDIR_BASE/t1"
mkdir -p "$T1"
write_subject "$T1"
write_gh_stub "$T1" "run 12345 is still in progress; logs will be available when it is complete" 1

rc=0
run_script "$T1" "12345" "owner/repo" "$T1/out.txt" rc
assert_rc "in-progress exits 3" "$rc" "3"
assert_contains "output contains in-progress message" "$T1/out.txt" "is still in progress"
assert_contains "output contains header comment" "$T1/out.txt" "CI log (run 12345"

# --------------------------------------------------------------------------
# Test 2: successful gh run view → exit 0

echo "--- Test 2: successful response → exit 0 ---"
T2="$TMPDIR_BASE/t2"
mkdir -p "$T2"
write_subject "$T2"
write_gh_stub "$T2" "Error: some step failed with code 1" 0

rc=0
run_script "$T2" "99999" "owner/repo" "$T2/out.txt" rc
assert_rc "successful gh exits 0" "$rc" "0"
assert_contains "output contains log line" "$T2/out.txt" "some step failed"

# --------------------------------------------------------------------------
# Test 3: non-in-progress gh failure → exit 1

echo "--- Test 3: non-in-progress gh failure → exit 1 ---"
T3="$TMPDIR_BASE/t3"
mkdir -p "$T3"
write_subject "$T3"
write_gh_stub "$T3" "HTTP 404: not found" 1

rc=0
run_script "$T3" "55555" "owner/repo" "$T3/out.txt" rc
assert_rc "non-in-progress failure exits 1" "$rc" "1"
assert_contains "output contains error message" "$T3/out.txt" "HTTP 404"

# --------------------------------------------------------------------------
# Test 4: in-progress substring must be exact (different message → exit 1)

echo "--- Test 4: partial match does not trigger exit 3 ---"
T4="$TMPDIR_BASE/t4"
mkdir -p "$T4"
write_subject "$T4"
write_gh_stub "$T4" "logs will be available once the run completes" 2

rc=0
run_script "$T4" "11111" "owner/repo" "$T4/out.txt" rc
assert_rc "non-matching message does not exit 3" "$rc" "1"

# --------------------------------------------------------------------------
# Summary

echo ""
echo "Results: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
