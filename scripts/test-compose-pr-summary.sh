#!/usr/bin/env bash
# test-compose-pr-summary.sh — regression tests for compose-pr-summary.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
COMPOSER="$SCRIPT_DIR/compose-pr-summary.sh"

[ -x "$COMPOSER" ] || { echo "FAIL: $COMPOSER not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-compose-pr-summary.XXXXXX")"
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

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (unexpected '$needle' found)"
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

# Build a minimal git repo so git diff/merge-base work.
REPO="$TMP/repo"
git init -q -b main "$REPO"
git -C "$REPO" config user.email "test@example.com"
git -C "$REPO" config user.name "Test"
git -C "$REPO" commit -q --allow-empty -m "initial"
# Simulate origin/main remote ref.
git -C "$REPO" branch -f "origin/main" main 2>/dev/null || true

# Switch to a feature branch with some commits.
git -C "$REPO" checkout -q -b feature
mkdir -p "$REPO/scripts"
printf 'content\n' > "$REPO/scripts/foo.sh"
printf 'test content\n' > "$REPO/scripts/test-foo.sh"
git -C "$REPO" add .
git -C "$REPO" commit -q -m "add foo"
cd "$REPO"

echo "=== (a) full inputs: real plan-goals + diff with test file ==="
plan_goals="$TMP/plan-goals-test.md"
cat > "$plan_goals" <<'EOF'
## Goal
Add compose-pr-summary.sh to replace placeholder text on SIMPLE path.

## Implementation Plan
Create scripts/compose-pr-summary.sh and wire into ship-pr.sh.

## Test plan
Run scripts/test-compose-pr-summary.sh.
EOF

out=$("$COMPOSER" --plan-goals-file "$plan_goals")
assert_contains "$out" "Add compose-pr-summary.sh" "(a) first bullet from Goal line"
assert_contains "$out" "test file" "(a) second bullet for test files"

echo "=== (b) missing plan-goals file → non-zero exit ==="
assert_fails "(b) missing plan-goals exits non-zero" "$COMPOSER" --plan-goals-file "$TMP/nonexistent.md"

echo "=== (c) plan-goals present, no test files in diff ==="
# Remove the test file from the repo and re-commit.
git -C "$REPO" rm -q scripts/test-foo.sh
git -C "$REPO" commit -q -m "remove test file"

plan_goals_c="$TMP/plan-goals-c.md"
cat > "$plan_goals_c" <<'EOF'
## Goal
Remove the test file to verify no test bullet.

## Implementation Plan
git rm scripts/test-foo.sh

## Test plan
n/a
EOF

out_c=$("$COMPOSER" --plan-goals-file "$plan_goals_c")
assert_contains "$out_c" "Remove the test file" "(c) first bullet present"
assert_not_contains "$out_c" "test file(s)" "(c) no test bullet when no test files changed"

echo "=== (d) plan-goals with no Goal section → non-zero exit ==="
plan_goals_d="$TMP/plan-goals-d.md"
cat > "$plan_goals_d" <<'EOF'
## Implementation Plan
Only an implementation plan, no Goal section.

## Test plan
n/a
EOF
assert_fails "(d) no Goal section exits non-zero" "$COMPOSER" --plan-goals-file "$plan_goals_d"

cd "$OLDPWD"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
