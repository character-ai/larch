#!/usr/bin/env bash
# Offline unit tests for scripts/lib-external-launcher-common.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPDIR_ROOT="$(mktemp -d /tmp/larch-test-lib-ext-launcher-XXXXXX)"
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

PASS=0
FAIL=0
FAILURES=()

pass() { PASS=$((PASS + 1)); }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); }

assert_returns() {
    local label="$1" expected="$2"
    shift 2
    local rc=0
    "$@" || rc=$?
    if [[ "$rc" -eq "$expected" ]]; then
        pass
    else
        fail "$label: expected return $expected, got $rc"
    fi
}

# Source the library under test.
# shellcheck source=scripts/lib-external-launcher-common.sh
source "$REPO_ROOT/scripts/lib-external-launcher-common.sh"

EMPTY_OUTPUT="$TMPDIR_ROOT/empty.output"
: > "$EMPTY_OUTPUT"

NONEMPTY_OUTPUT="$TMPDIR_ROOT/nonempty.output"
printf 'some review output\n' > "$NONEMPTY_OUTPUT"

# Absent output file: treated as 0 bytes (tool exited before producing output)
ABSENT_OUTPUT="$TMPDIR_ROOT/absent.output"
assert_returns "absent output file returns 0 for valid exit/elapsed" 0 \
    external_is_transient_infra_failure "codex" "7" "0" "$ABSENT_OUTPUT"

# Wrong tool: must return 1
assert_returns "unknown tool returns 1" 1 \
    external_is_transient_infra_failure "claude" "7" "0" "$EMPTY_OUTPUT"

# Codex exit code not in allowlist: must return 1
assert_returns "codex exit 1 returns 1 (not transient)" 1 \
    external_is_transient_infra_failure "codex" "1" "0" "$EMPTY_OUTPUT"

assert_returns "codex exit 2 returns 1 (not transient)" 1 \
    external_is_transient_infra_failure "codex" "2" "0" "$EMPTY_OUTPUT"

# Cursor exit code not in allowlist: must return 1
assert_returns "cursor exit 1 returns 1 (not transient)" 1 \
    external_is_transient_infra_failure "cursor" "1" "0" "$EMPTY_OUTPUT"

assert_returns "cursor exit 3 returns 1 (not transient)" 1 \
    external_is_transient_infra_failure "cursor" "3" "0" "$EMPTY_OUTPUT"

# Codex exit 7 + empty output: must return 0
assert_returns "codex exit 7 + empty output + 0s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "codex" "7" "0" "$EMPTY_OUTPUT"

assert_returns "codex exit 7 + empty output + 5s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "codex" "7" "5" "$EMPTY_OUTPUT"

# Codex exit 5 + empty output: must return 0
assert_returns "codex exit 5 + empty output + 0s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "codex" "5" "0" "$EMPTY_OUTPUT"

# Cursor exit 8 + empty output: must return 0
assert_returns "cursor exit 8 + empty output + 0s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "cursor" "8" "0" "$EMPTY_OUTPUT"

# Cursor exit 4 + empty output: must return 0
assert_returns "cursor exit 4 + empty output + 0s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "cursor" "4" "0" "$EMPTY_OUTPUT"

# Non-empty output file: must return 1 (even with valid exit code and short elapsed)
assert_returns "codex exit 7 + non-empty output returns 1" 1 \
    external_is_transient_infra_failure "codex" "7" "0" "$NONEMPTY_OUTPUT"

assert_returns "cursor exit 8 + non-empty output returns 1" 1 \
    external_is_transient_infra_failure "cursor" "8" "0" "$NONEMPTY_OUTPUT"

assert_returns "codex exit 7 + elapsed=6 still returns 0 when output is empty" 0 \
    external_is_transient_infra_failure "codex" "7" "6" "$EMPTY_OUTPUT"

assert_returns "cursor exit 8 + elapsed=10 still returns 0 when output is empty" 0 \
    external_is_transient_infra_failure "cursor" "8" "10" "$EMPTY_OUTPUT"

if (( FAIL > 0 )); then
    printf 'FAIL: test-lib-external-launcher-common.sh — %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    for f in "${FAILURES[@]}"; do
        printf '  %s\n' "$f" >&2
    done
    exit 1
fi

printf 'PASS: test-lib-external-launcher-common.sh — %s assertions passed\n' "$PASS"
