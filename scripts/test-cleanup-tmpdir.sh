#!/usr/bin/env bash
# test-cleanup-tmpdir.sh - regression harness for cleanup-tmpdir.sh auditing.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/cleanup-tmpdir.sh"

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d /tmp/larch-cleanup-tmpdir-test.XXXXXX)
CLEANUP_TARGET=$(mktemp -d /tmp/cleanup-test-XXXXXX)

cleanup() {
    rm -rf "$SANDBOX"
    if [[ -n "${CLEANUP_TARGET:-}" && -e "$CLEANUP_TARGET" ]]; then
        rm -rf "$CLEANUP_TARGET"
    fi
}
trap cleanup EXIT

assert_eq() {
    local actual=$1 expected=$2 label=$3
    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected $expected got $actual)"
    fi
}

assert_exists() {
    local path=$1 label=$2
    if [[ -e "$path" ]]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (missing: $path)"
    fi
}

assert_not_exists() {
    local path=$1 label=$2
    if [[ ! -e "$path" ]]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (path exists: $path)"
    fi
}

assert_regex() {
    local value=$1 regex=$2 label=$3
    if [[ "$value" =~ $regex ]]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  value: $value"
        echo "  regex: $regex"
    fi
}

AUDIT_DIR="$SANDBOX/audit"
mkdir -p "$AUDIT_DIR"
AUDIT_LOG="$AUDIT_DIR/larch-cleanup-audit.log"

set +e
TMPDIR="$AUDIT_DIR" "$SCRIPT" --dir "$CLEANUP_TARGET"
RC=$?
set -e

assert_eq "$RC" 0 "cleanup exits successfully"
assert_not_exists "$CLEANUP_TARGET" "cleanup removes target directory"
assert_exists "$AUDIT_LOG" "cleanup writes audit log under TMPDIR override"

LINE_COUNT=$(wc -l < "$AUDIT_LOG" | tr -d '[:space:]')
assert_eq "$LINE_COUNT" 1 "audit log contains exactly one line"

AUDIT_LINE=$(sed -n '1p' "$AUDIT_LOG")
TIMESTAMP_RE='([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z|\?)'
AUDIT_RE="^${TIMESTAMP_RE} pid=[0-9]+ ppid=[0-9]+ parent=[^[:space:]]+ dir=/tmp/cleanup-test-[^[:space:]]+$"
assert_regex "$AUDIT_LINE" "$AUDIT_RE" "audit line has timestamp, pid, ppid, parent, and dir fields"

echo
echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]
