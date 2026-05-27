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
    local needle=$1 file=$2 label=$3
    if grep -qxF "$needle" "$file"; then
        pass "$label"
    else
        fail "$label (missing $needle)"
        sed 's/^/    /' "$file" >&2 || true
    fi
}

run_case() {
    local name=$1 expected=$2
    shift 2
    local dir="$TMP_ROOT/$name"
    mkdir -p "$dir"
    "$HELPER" --implement-tmpdir "$dir" --no-issues false --workflow-path HARD "$@" >/dev/null
    assert_file_contains "EMERGENCY_REQUESTED=$expected" "$dir/run-flags.sh" "$name emergency persisted"
}

run_case true true --emergency-requested true
run_case false false --emergency-requested false
run_case omitted false

bad_dir="$TMP_ROOT/bad"
mkdir -p "$bad_dir"
set +e
"$HELPER" --implement-tmpdir "$bad_dir" --no-issues false --workflow-path HARD --emergency-requested maybe >/dev/null 2>/dev/null
rc=$?
set -e
if [ "$rc" -eq 2 ]; then
    pass "invalid emergency value exits 2"
else
    fail "invalid emergency value exits 2 (got $rc)"
fi

printf -- '---\nPASS=%s FAIL=%s\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
