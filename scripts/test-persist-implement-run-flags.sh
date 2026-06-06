#!/usr/bin/env bash
# test-persist-implement-run-flags.sh — offline harness for persist-implement-run-flags.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/persist-implement-run-flags.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-persist-implement-run-flags.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }

assert_file_contains() {
    local needle file label
    needle=$1
    file=$2
    label=$3
    if /usr/bin/grep -qxF "$needle" "$file"; then
        pass "$label"
    else
        fail "$label (missing $needle)"
        sed 's/^/    /' "$file" >&2 || true
    fi
}

run_case() {
    local name exp_em exp_sr
    name=$1
    exp_em=$2
    exp_sr=$3
    shift 3
    local dir="$TMP_ROOT/$name"
    mkdir -p "$dir"
    "$HELPER" --implement-tmpdir "$dir" --no-issues false "$@" >/dev/null
    assert_file_contains "EMERGENCY_REQUESTED=$exp_em" "$dir/run-flags.sh" "$name emergency persisted"
    assert_file_contains "SELF_REVIEW_REQUESTED=$exp_sr" "$dir/run-flags.sh" "$name self-review persisted"
    if /usr/bin/grep -q '^WORKFLOW_PATH=' "$dir/run-flags.sh"; then
        fail "$name workflow path omitted"
    else
        pass "$name workflow path omitted"
    fi
}

run_case true true false --emergency-requested true
run_case false false false --emergency-requested false
run_case omitted false false
run_case self_review false true --self-review-requested true
run_case both true true --emergency-requested true --self-review-requested true

bad_dir="$TMP_ROOT/bad"
mkdir -p "$bad_dir"
set +e
"$HELPER" --implement-tmpdir "$bad_dir" --no-issues false --emergency-requested maybe >/dev/null 2>/dev/null
rc=$?
set -e
if [ "$rc" -eq 2 ]; then
    pass "invalid emergency value exits 2"
else
    fail "invalid emergency value exits 2 (got $rc)"
fi

bad_sr_dir="$TMP_ROOT/bad_sr"
mkdir -p "$bad_sr_dir"
set +e
"$HELPER" --implement-tmpdir "$bad_sr_dir" --no-issues false --self-review-requested maybe >/dev/null 2>/dev/null
rc=$?
set -e
if [ "$rc" -eq 2 ]; then
    pass "invalid self-review value exits 2"
else
    fail "invalid self-review value exits 2 (got $rc)"
fi

printf -- '---\nPASS=%s FAIL=%s\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
