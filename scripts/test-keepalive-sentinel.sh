#!/usr/bin/env bash
# test-keepalive-sentinel.sh — regression harness for session-setup keepalive metadata.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/session-setup.sh"

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
TMPROOT=$(mktemp -d /tmp/larch-keepalive-test.XXXXXX)
trap 'rm -rf "$TMPROOT"' EXIT

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        printf '  missing: %s\n' "$needle"
    fi
}

assert_file_exists() {
    local path=$1 label=$2
    if [ -f "$path" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (missing $path)"
    fi
}

OUT=$(XDG_CACHE_HOME="$TMPROOT/cache" "$SCRIPT" --prefix claude-implement --skip-preflight --skip-repo-check)
SESSION_TMPDIR=$(printf '%s\n' "$OUT" | awk -F= '$1 == "SESSION_TMPDIR" {print substr($0, index($0, "=") + 1); exit}')
SESSION_ID=$(printf '%s\n' "$OUT" | awk -F= '$1 == "SESSION_ID" {print substr($0, index($0, "=") + 1); exit}')

assert_contains "SESSION_TMPDIR=$TMPROOT/cache/larch/sessions/claude-implement-" "$OUT" "session tmpdir uses cache sessions root"
assert_contains "SESSION_ID=" "$OUT" "session setup emits SESSION_ID"
assert_file_exists "$SESSION_TMPDIR/session-id" "session-id file written"
assert_file_exists "$SESSION_TMPDIR/.larch-keepalive" "keepalive sentinel written"

FILE_SESSION_ID=$(tr -d '\r\n' < "$SESSION_TMPDIR/session-id")
if [ "$FILE_SESSION_ID" = "$SESSION_ID" ]; then
    PASS=$((PASS + 1))
    echo "PASS: emitted session id matches file"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: emitted session id does not match file"
fi

SENTINEL=$(cat "$SESSION_TMPDIR/.larch-keepalive")
assert_contains "larch session keepalive" "$SENTINEL" "sentinel header present"
assert_contains "PID=" "$SENTINEL" "sentinel records PID"
assert_contains "PPID=" "$SENTINEL" "sentinel records PPID"
assert_contains "CLONE_PATH=$REPO_ROOT" "$SENTINEL" "sentinel records clone path"
assert_contains "SESSION_ID=$SESSION_ID" "$SENTINEL" "sentinel records session id"
assert_contains "PREFIX=claude-implement" "$SENTINEL" "sentinel records prefix"
assert_contains "CREATED=" "$SENTINEL" "sentinel records creation time"
assert_contains "NOTE=ext-cleaners-please-skip" "$SENTINEL" "sentinel records cleaner hint"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
