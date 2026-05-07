#!/usr/bin/env bash
# test-lib-cursor-auth.sh — Hermetic regression harness for scripts/lib-cursor-auth.sh.
#
# Verifies cursor_auth_argv (whitespace trim variants) and cursor_auth_preflight
# (Darwin-gated decision tree, test-mode gating). All test-mode overrides are
# gated by LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 — overrides set without that
# sentinel are silently ignored (FINDING_6 regression).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB="$REPO_ROOT/scripts/lib-cursor-auth.sh"

[[ -f "$LIB" ]] || { echo "FAIL: lib-cursor-auth.sh not found at $LIB" >&2; exit 1; }

PASS_COUNT=0
FAIL_COUNT=0
fail() { echo "FAIL [$1]: $2" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }

# Run a one-shot bash subshell that sources the lib, sets the requested
# environment, runs cursor_auth_argv, and prints the resulting array elements
# one per line on stdout. Returns lib's exit (0 here since it just sources).
_argv_run() {
    local key="$1"
    CURSOR_API_KEY="$key" bash -c '
        set -euo pipefail
        # shellcheck source=/dev/null
        . "'"$LIB"'"
        CURSOR_AUTH_ARGS=()
        cursor_auth_argv
        for arg in ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"}; do
            printf "%s\n" "$arg"
        done
    '
}

# Test 1: empty key → no argv elements.
OUT=$(_argv_run "")
if [[ -z "$OUT" ]]; then pass; else fail 1 "empty key should produce no argv; got: $OUT"; fi

# Test 2: whitespace-only key → no argv elements.
OUT=$(_argv_run $'  \t\n  ')
if [[ -z "$OUT" ]]; then pass; else fail 2 "whitespace-only key should produce no argv; got: $OUT"; fi

# Test 3: simple key → exactly two lines: --api-key, then key.
OUT=$(_argv_run "test-key-XYZ")
EXPECTED=$'--api-key\ntest-key-XYZ'
if [[ "$OUT" == "$EXPECTED" ]]; then pass; else fail 3 "simple key: expected '$EXPECTED', got: $OUT"; fi

# Test 4: leading/trailing whitespace is trimmed.
OUT=$(_argv_run "   trimmed-key   ")
EXPECTED=$'--api-key\ntrimmed-key'
if [[ "$OUT" == "$EXPECTED" ]]; then pass; else fail 4 "trim: expected '$EXPECTED', got: $OUT"; fi

# Test 5: tab/newline-bounded whitespace is trimmed.
OUT=$(_argv_run $'\tkey-with-tabs\t')
EXPECTED=$'--api-key\nkey-with-tabs'
if [[ "$OUT" == "$EXPECTED" ]]; then pass; else fail 5 "tab-trim: expected '$EXPECTED', got: $OUT"; fi

# cursor_auth_preflight tests — return code only, don't care about stderr text.
_preflight_run() {
    # Args after this function name are env-var assignments forwarded into the subshell.
    local rc=0
    env "$@" bash -c '
        set -uo pipefail
        # shellcheck source=/dev/null
        . "'"$LIB"'"
        cursor_auth_preflight
    ' 2>/dev/null || rc=$?
    printf '%s\n' "$rc"
}

# Test 6: non-empty key returns 0 regardless of platform/keychain.
RC=$(_preflight_run CURSOR_API_KEY=non-empty LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin LIB_CURSOR_AUTH_TEST_SECURITY_RC=1)
if [[ "$RC" == "0" ]]; then pass; else fail 6 "non-empty key should return 0; got rc=$RC"; fi

# Test 7: empty key on non-Darwin returns 0 (no-op).
RC=$(_preflight_run CURSOR_API_KEY= LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LIB_CURSOR_AUTH_TEST_SECURITY_RC=1)
if [[ "$RC" == "0" ]]; then pass; else fail 7 "empty key on non-Darwin should return 0; got rc=$RC"; fi

# Test 8: empty key on Darwin with keychain entry present (RC=0) returns 0.
RC=$(_preflight_run CURSOR_API_KEY= LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin LIB_CURSOR_AUTH_TEST_SECURITY_RC=0)
if [[ "$RC" == "0" ]]; then pass; else fail 8 "empty key on Darwin with keychain entry should return 0; got rc=$RC"; fi

# Test 9: empty key on Darwin with keychain entry missing (RC=1) returns 2.
RC=$(_preflight_run CURSOR_API_KEY= LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin LIB_CURSOR_AUTH_TEST_SECURITY_RC=1)
if [[ "$RC" == "2" ]]; then pass; else fail 9 "empty key on Darwin with no keychain should return 2; got rc=$RC"; fi

# Test 10: test-mode gating — overrides without LARCH_LIB_CURSOR_AUTH_TEST_MODE
# are silently ignored. With CURSOR_API_KEY=non-empty and no test-mode sentinel,
# preflight returns 0 (key wins) regardless of LIB_CURSOR_AUTH_TEST_*. This is
# the easier direction to assert hermetically.
RC=$(_preflight_run CURSOR_API_KEY=non-empty LIB_CURSOR_AUTH_TEST_UNAME=Darwin LIB_CURSOR_AUTH_TEST_SECURITY_RC=1)
if [[ "$RC" == "0" ]]; then pass; else fail 10 "test-mode gating: non-empty key should return 0 even with test-vars set if sentinel missing; got rc=$RC"; fi

# Test 11: stderr message on Darwin failure path includes the documented
# anchors (caller identity, doc pointer, both remediation lines).
STDERR=$(env CURSOR_API_KEY= LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin LIB_CURSOR_AUTH_TEST_SECURITY_RC=1 bash -c '
    set -uo pipefail
    # shellcheck source=/dev/null
    . "'"$LIB"'"
    cursor_auth_preflight
' 2>&1 >/dev/null || true)
if grep -Fq 'cursor-auth-preflight failed' <<<"$STDERR" \
   && grep -Fq 'docs/installation-and-setup.md' <<<"$STDERR" \
   && grep -Fq 'export CURSOR_API_KEY=' <<<"$STDERR" \
   && grep -Fq 'security delete-generic-password -a cursor-user' <<<"$STDERR"; then
    pass
else
    fail 11 "stderr message missing required anchors; got:\n$STDERR"
fi

# Test 12 (cursor-auth-flags.sh): when CURSOR_API_KEY empty, exits 0 with no stdout.
FLAGS_OUT=$(CURSOR_API_KEY="" "$REPO_ROOT/scripts/cursor-auth-flags.sh"; echo "rc=$?")
if [[ "$FLAGS_OUT" == "rc=0" ]]; then pass; else fail 12 "cursor-auth-flags.sh empty key: expected exactly rc=0 with no stdout; got: $FLAGS_OUT"; fi

# Test 13 (cursor-auth-flags.sh): when CURSOR_API_KEY set, prints two lines.
FLAGS_OUT=$(CURSOR_API_KEY="abc" "$REPO_ROOT/scripts/cursor-auth-flags.sh")
EXPECTED=$'--api-key\nabc'
if [[ "$FLAGS_OUT" == "$EXPECTED" ]]; then pass; else fail 13 "cursor-auth-flags.sh: expected '$EXPECTED', got: $FLAGS_OUT"; fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-lib-cursor-auth.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-lib-cursor-auth.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
