#!/usr/bin/env bash
# test-compose-architecture-sketch.sh — regression tests for compose-architecture-sketch.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
COMPOSER="$SCRIPT_DIR/compose-architecture-sketch.sh"

[ -x "$COMPOSER" ] || { echo "FAIL: $COMPOSER not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-compose-architecture-sketch.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

fail() {
    echo "FAIL: $1" >&2
    FAIL=$((FAIL + 1))
}

pass() {
    echo "  ok: $1"
    PASS=$((PASS + 1))
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing '$needle'; got '${haystack:0:400}')"
    fi
}

assert_fails() {
    local label="$1"
    shift
    set +e
    "$@" >/dev/null 2>&1
    local rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        pass "$label"
    else
        fail "$label (expected non-zero exit)"
    fi
}

# Build a minimal git repo.
REPO="$TMP/repo"
git init -q -b main "$REPO"
git -C "$REPO" config user.email "test@example.com"
git -C "$REPO" config user.name "Test"
git -C "$REPO" commit -q --allow-empty -m "initial"
git -C "$REPO" branch -f "origin/main" HEAD 2>/dev/null || true

git -C "$REPO" checkout -q -b feature

echo "=== (a) single-file change → single-box ==="
mkdir -p "$REPO/scripts"
printf 'x\n' > "$REPO/scripts/foo.sh"
git -C "$REPO" add .
git -C "$REPO" commit -q -m "add foo"

cd "$REPO"
out=$("$COMPOSER")
assert_contains "$out" "flowchart LR" "(a) flowchart directive present"
assert_contains "$out" "foo.sh" "(a) single file name in box"
assert_contains "$out" '## Architecture Sketch' "(a) heading present"
assert_contains "$out" '```mermaid' "(a) mermaid fence present"

echo "=== (b) multi-directory change → grouped boxes ==="
mkdir -p "$REPO/skills/foo"
printf 'y\n' > "$REPO/skills/foo/bar.sh"
mkdir -p "$REPO/agents"
printf 'z\n' > "$REPO/agents/baz.md"
git -C "$REPO" add .
git -C "$REPO" commit -q -m "add multi-dir files"

out_b=$("$COMPOSER")
assert_contains "$out_b" "flowchart LR" "(b) flowchart present"
assert_contains "$out_b" "scripts/" "(b) scripts dir box"
assert_contains "$out_b" "skills/" "(b) skills dir box"

echo "=== (c) no changed files relative to origin/main → non-zero exit ==="
# Create a branch from origin/main (no additional commits vs origin/main).
git -C "$REPO" checkout -q -b empty-branch "origin/main"
assert_fails "(c) no diff exits non-zero" "$COMPOSER"

cd "$OLDPWD"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
