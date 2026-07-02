#!/usr/bin/env bash
# test-cleanup-sessionstart.sh — Regression harness for scripts/cleanup-sessionstart.sh.
# Pins: executable hook precondition, hooks.json registration, always-exit-0
# invariant, python3/cli.py skip-when-missing contract, no-stdout contract, and
# background spawn contract (& + disown).

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/cleanup-sessionstart.sh"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"

if [[ ! -x "$SCRIPT" ]]; then
    echo "FAIL: $SCRIPT does not exist or is not executable" >&2
    exit 1
fi

REAL_PYTHON3=$(command -v python3 || true)
BASH_BIN=$(command -v bash || true)
if [[ -z "$REAL_PYTHON3" || ! -x "$REAL_PYTHON3" ]]; then
    echo "FAIL: harness python3 not on PATH" >&2
    exit 1
fi
if [[ -z "$BASH_BIN" || ! -x "$BASH_BIN" ]]; then
    echo "FAIL: could not resolve bash on ambient PATH" >&2
    exit 1
fi

tmp=$(mktemp -d /tmp/larch-cleanup-sessionstart-test.XXXXXX)
trap 'rm -rf "$tmp"' EXIT

PASS=0
FAIL=0
FAILED_TESTS=()

assert_eq() {
    local got="$1" expected="$2" label="$3"
    if [[ "$got" == "$expected" ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (got '$got', expected '$expected')")
        echo "  FAIL: $label" >&2
        echo "       got:      '$got'" >&2
        echo "       expected: '$expected'" >&2
    fi
}

assert_empty() {
    local got="$1" label="$2"
    if [[ -z "$got" ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label (stdout empty)"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (stdout non-empty)")
        echo "  FAIL: $label" >&2
        echo "       got: '$got'" >&2
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (missing '$needle')")
        echo "  FAIL: $label (missing '$needle')" >&2
    fi
}

build_bin() {
    local dir="$1"
    rm -rf "$dir"
    mkdir -p "$dir"
    local tool resolved
    for tool in cat dirname mkdir basename; do
        resolved=$(command -v "$tool" || true)
        if [[ -n "$resolved" && -x "$resolved" ]]; then
            ln -sf "$resolved" "$dir/$tool"
        fi
    done
}

echo "=== hooks.json SessionStart registration ==="
if jq -e '
    .hooks.SessionStart[]?
    | select(.matcher == "startup|resume|clear|compact")
    | .hooks[]?
    | select(.type == "command" and .command == "${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-sessionstart.sh" and .timeout == 10)
' "$HOOKS_JSON" >/dev/null 2>&1; then
    PASS=$((PASS + 1))
    echo "  ok: hooks.json registers cleanup-sessionstart.sh under SessionStart"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("hooks.json must register cleanup-sessionstart.sh under SessionStart (matcher startup|resume|clear|compact, timeout 10)")
    echo "  FAIL: hooks.json must register cleanup-sessionstart.sh under SessionStart" >&2
fi

echo "=== Case 1: python3 missing → always exits 0 ==="
build_bin "$tmp/c1_bin"
mkdir -p "$tmp/c1-cwd"
rc=0
(cd "$tmp/c1-cwd" && env -i PATH="$tmp/c1_bin" TMPDIR="$tmp" \
    "$BASH_BIN" "$SCRIPT" > "$tmp/c1.out" 2> "$tmp/c1.err") || rc=$?
assert_eq "$rc" "0" "case 1: exit code 0"
assert_empty "$(cat "$tmp/c1.out")" "case 1: no stdout when python3 absent"

echo "=== Case 2: cli.py missing → always exits 0 ==="
build_bin "$tmp/c2_bin"
ln -sf "$REAL_PYTHON3" "$tmp/c2_bin/python3"
mkdir -p "$tmp/c2-empty-root/python"
mkdir -p "$tmp/c2-cwd"
rc=0
(cd "$tmp/c2-cwd" && env -i \
    PATH="$tmp/c2_bin" \
    TMPDIR="$tmp" \
    CLAUDE_PLUGIN_ROOT="$tmp/c2-empty-root" \
    "$BASH_BIN" "$SCRIPT" > "$tmp/c2.out" 2> "$tmp/c2.err") || rc=$?
assert_eq "$rc" "0" "case 2: exit code 0"
assert_empty "$(cat "$tmp/c2.out")" "case 2: no stdout when cli.py absent"

echo "=== Case 3: normal run with stub CLI → exits 0, no stdout ==="
build_bin "$tmp/c3_bin"
ln -sf "$REAL_PYTHON3" "$tmp/c3_bin/python3"
mkdir -p "$tmp/c3-fake-root/python"
SENTINEL="$tmp/c3-sentinel"
# Stub cli.py writes a sentinel file when invoked with the expected verb.
cat > "$tmp/c3-fake-root/python/cli.py" <<'PYEOF'
import os
import sys

if len(sys.argv) >= 3 and sys.argv[1] == "cleanup" and sys.argv[2] == "run":
    sentinel = os.environ.get("LARCH_CLEANUP_TEST_SENTINEL", "")
    if sentinel:
        open(sentinel, "w", encoding="utf-8").close()
sys.exit(0)
PYEOF
mkdir -p "$tmp/c3-cwd"
rc=0
(cd "$tmp/c3-cwd" && env -i \
    PATH="$tmp/c3_bin" \
    TMPDIR="$tmp" \
    CLAUDE_PLUGIN_ROOT="$tmp/c3-fake-root" \
    LARCH_CLEANUP_TEST_SENTINEL="$SENTINEL" \
    "$BASH_BIN" "$SCRIPT" > "$tmp/c3.out" 2> "$tmp/c3.err") || rc=$?
assert_eq "$rc" "0" "case 3: exit code 0"
assert_empty "$(cat "$tmp/c3.out")" "case 3: no stdout on normal run"

echo "=== Case 4: background spawn — CLI is invoked ==="
# The hook exits immediately; the background python3 stub from case 3 writes
# the sentinel asynchronously. Poll for up to 10 seconds.
waited=0
while [[ ! -f "$SENTINEL" && "$waited" -lt 10 ]]; do
    sleep 1
    waited=$((waited + 1))
done
if [[ -f "$SENTINEL" ]]; then
    PASS=$((PASS + 1))
    echo "  ok: case 4: background CLI was invoked (sentinel written within ${waited}s)"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("case 4: background CLI was not invoked within 10s timeout")
    echo "  FAIL: case 4: background CLI was not invoked within 10s timeout" >&2
fi

echo "=== Case 5: source-level spawn contract ==="
script_body=$(cat "$SCRIPT")
assert_contains "$script_body" "cleanup run" "case 5: cleanup CLI verb present"
assert_contains "$script_body" "2>&1 &" "case 5: script launches cleanup in background"
assert_contains "$script_body" "disown" "case 5: script detaches process with disown"

echo "=== Case 6: always-exit-0 source invariant ==="
assert_contains "$script_body" "exit 0" "case 6: unconditional exit 0 present in source"

echo
echo "=== Summary ==="
echo "  passed: $PASS"
echo "  failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
    printf '\nFailed tests:\n' >&2
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t" >&2
    done
    exit 1
fi
echo "all tests passed"
exit 0
