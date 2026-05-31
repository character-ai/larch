#!/usr/bin/env bash
# test-lib-phase-driver.sh - Unit harness for lib-phase-driver.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-lib-phase-driver.XXXXXX")"
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
        fail "$label (missing $needle)"
    fi
}

assert_file_equals() {
    local file="$1" expected="$2" label="$3"
    local actual
    actual="$(cat "$file")"
    if [[ "$actual" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label"
    fi
}

echo "=== session_get ==="
kv_file="$TMP/session.env"
printf 'FOO=bar\nBAZ=qux\n' >"$kv_file"
if [[ "$(phase_driver_session_get "$kv_file" FOO "")" == bar ]]; then
    pass 'session_get hit'
else
    fail 'session_get hit'
fi
if [[ "$(phase_driver_session_get "$kv_file" MISSING dflt)" == dflt ]]; then
    pass 'session_get default'
else
    fail 'session_get default'
fi

echo "=== resolve_plugin_root ==="
session="$TMP/plugin-session.env"
printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT" >"$session"
if (
    unset CLAUDE_PLUGIN_ROOT
    [[ "$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$session")" == "$REPO_ROOT" ]]
); then
    pass 'resolve from session-env'
else
    fail 'resolve from session-env'
fi
if (
    unset CLAUDE_PLUGIN_ROOT
    [[ "$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "")" == "$REPO_ROOT" ]]
); then
    pass 'resolve tree-walk fallback'
else
    fail 'resolve tree-walk fallback'
fi
other_root="$TMP/other-plugin-root"
mkdir -p "$other_root"
if (
    export CLAUDE_PLUGIN_ROOT="$other_root"
    [[ "$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$session")" == "$other_root" ]]
); then
    pass 'CLAUDE_PLUGIN_ROOT overrides session-env'
else
    fail 'CLAUDE_PLUGIN_ROOT overrides session-env'
fi

echo "=== write_result_env ==="
result="$TMP/out.env"
phase_driver_write_result_env "$result" 'A=1' 'B=two'
assert_file_equals "$result" $'A=1\nB=two' 'write_result_env atomic write'
ln -sf "$result" "$TMP/symlink.env"
if phase_driver_write_result_env "$TMP/symlink.env" 'X=1' 2>/dev/null; then
    fail 'write_result_env should refuse symlink target'
else
    pass 'write_result_env refuses symlink target'
fi

echo "=== read_result_env ==="
phase_driver_read_result_env "$result" A B >"$TMP/read.out"
assert_contains "$(cat "$TMP/read.out")" 'A=1' 'read_result_env allowlist A'
assert_contains "$(cat "$TMP/read.out")" 'B=two' 'read_result_env allowlist B'
if phase_driver_read_result_env "$TMP/symlink.env" A 2>/dev/null; then
    fail 'read_result_env should refuse symlink source'
else
    pass 'read_result_env refuses symlink source'
fi

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-lib-phase-driver.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-lib-phase-driver.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
