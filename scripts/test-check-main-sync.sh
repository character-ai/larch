#!/usr/bin/env bash
# test-check-main-sync.sh — regression harness for check-main-sync.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/check-main-sync.sh"

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d "${TMPDIR:-/tmp}/larch-check-main-sync-test.XXXXXX")
trap 'rm -rf "$SANDBOX"' EXIT

assert_rc() {
    local actual=$1 expected=$2 label=$3
    if [ "$actual" -eq "$expected" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected rc=$expected got rc=$actual)"
    fi
}

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected to contain: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if ! printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected not to contain: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

# Create a bare "remote" and a local clone with origin pointing to it.
make_repo_pair() {
    local name=$1
    local bare="$SANDBOX/${name}-bare"
    local local_repo="$SANDBOX/${name}-local"

    mkdir -p "$bare"
    git -C "$bare" init -q --bare

    mkdir -p "$local_repo"
    git -C "$local_repo" init -q
    git -C "$local_repo" remote add origin "$bare"

    # Seed initial commit on main so origin/main exists.
    git -C "$local_repo" config user.email "test@test"
    git -C "$local_repo" config user.name "Test"
    printf 'init\n' > "$local_repo/README.md"
    git -C "$local_repo" add README.md
    git -C "$local_repo" commit -q -m "init"
    # Normalize default branch name (git's default may be master); check-main-sync
    # only runs its ahead-of-origin logic on a branch literally named main.
    git -C "$local_repo" branch -M main
    git -C "$local_repo" push -q origin HEAD:main

    printf '%s\n' "$local_repo"
}

run_check() {
    local repo=$1; shift
    set +e
    OUT=$(cd "$repo" && "$SCRIPT" "$@" 2>"$SANDBOX/stderr.txt")
    RC=$?
    ERR=$(cat "$SANDBOX/stderr.txt")
    set -e
}

# --- Test 1: in sync (0 ahead) ---
repo=$(make_repo_pair sync)
run_check "$repo"
assert_rc "$RC" 0 "in-sync: exit 0"
assert_contains "SYNC_STATUS=ok" "$OUT" "in-sync: SYNC_STATUS=ok"
assert_contains "AHEAD_COUNT=0" "$OUT" "in-sync: AHEAD_COUNT=0"

# --- Test 2: not on main ---
repo=$(make_repo_pair feature)
git -C "$repo" checkout -q -b feature/foo
run_check "$repo"
assert_rc "$RC" 0 "not-on-main: exit 0"
assert_contains "SYNC_STATUS=not-main" "$OUT" "not-on-main: SYNC_STATUS=not-main"
git -C "$repo" checkout -q main

# --- Test 3: all flush commits ahead — auto-reset ---
repo=$(make_repo_pair flush)
git -C "$repo" config user.email "test@test"
git -C "$repo" config user.name "Test"
# Create a larch-logs flush commit (does not modify larch-logs/ content on
# disk — we only need the commit subject and diff to match the criteria).
mkdir -p "$repo/larch-logs"
printf 'dummy\n' > "$repo/larch-logs/run.md"
git -C "$repo" add larch-logs/run.md
git -C "$repo" commit -q -m "chore(larch-logs): flush implement run abc"
# Verify we are now ahead by 1.
ahead=$(git -C "$repo" rev-list --count origin/main..HEAD)
assert_contains "1" "$ahead" "flush-ahead: setup — 1 ahead commit"
run_check "$repo"
assert_rc "$RC" 0 "flush-ahead: exit 0"
assert_contains "SYNC_STATUS=reset" "$OUT" "flush-ahead: SYNC_STATUS=reset"
assert_contains "AHEAD_COUNT=1" "$OUT" "flush-ahead: AHEAD_COUNT=1"
# After reset, local main should match origin/main.
after_ahead=$(git -C "$repo" rev-list --count origin/main..HEAD)
assert_rc "$after_ahead" 0 "flush-ahead: local main reset to origin/main"

# --- Test 4: non-log commit ahead — blocked ---
repo=$(make_repo_pair nonlog)
git -C "$repo" config user.email "test@test"
git -C "$repo" config user.name "Test"
printf 'change\n' > "$repo/somefile.txt"
git -C "$repo" add somefile.txt
git -C "$repo" commit -q -m "feat: something unrelated"
run_check "$repo"
assert_rc "$RC" 1 "non-log-ahead: exit 1"
assert_contains "SYNC_STATUS=blocked" "$OUT" "non-log-ahead: SYNC_STATUS=blocked"
assert_contains "AHEAD_COUNT=1" "$OUT" "non-log-ahead: AHEAD_COUNT=1"
assert_contains "ERROR=" "$OUT" "non-log-ahead: ERROR present"

# --- Test 5: mixed (flush + non-flush) commits ahead — blocked ---
repo=$(make_repo_pair mixed)
git -C "$repo" config user.email "test@test"
git -C "$repo" config user.name "Test"
mkdir -p "$repo/larch-logs"
printf 'log\n' > "$repo/larch-logs/a.md"
git -C "$repo" add larch-logs/a.md
git -C "$repo" commit -q -m "chore(larch-logs): flush implement run xyz"
printf 'code\n' > "$repo/code.sh"
git -C "$repo" add code.sh
git -C "$repo" commit -q -m "fix: real change"
run_check "$repo"
assert_rc "$RC" 1 "mixed-ahead: exit 1"
assert_contains "SYNC_STATUS=blocked" "$OUT" "mixed-ahead: SYNC_STATUS=blocked"
assert_contains "AHEAD_COUNT=2" "$OUT" "mixed-ahead: AHEAD_COUNT=2"

# --- Test 6: bad argument ---
repo=$(make_repo_pair badarg)
set +e
OUT=$(cd "$repo" && "$SCRIPT" --unknown-flag 2>"$SANDBOX/stderr.txt")
RC=$?
ERR=$(cat "$SANDBOX/stderr.txt")
set -e
assert_rc "$RC" 2 "bad-arg: exit 2"
assert_contains "unknown flag" "$ERR" "bad-arg: stderr diagnostic"

# --- Test 7: missing origin/main ref — rev-list probe fails → probe-error exit 2 ---
repo=$(make_repo_pair missingorigin)
git -C "$repo" config user.email "test@test"
git -C "$repo" config user.name "Test"
mkdir -p "$repo/larch-logs"
printf 'x\n' > "$repo/larch-logs/x.md"
git -C "$repo" add larch-logs/x.md
git -C "$repo" commit -q -m "chore(larch-logs): flush implement run missingorigin"
# Drop the remote-tracking ref so origin/main no longer resolves.
if git -C "$repo" show-ref --verify --quiet refs/remotes/origin/main; then
    git -C "$repo" update-ref -d refs/remotes/origin/main
fi
run_check "$repo"
assert_rc "$RC" 2 "missing-origin-main: exit 2"
assert_contains "SYNC_STATUS=probe-error" "$OUT" "missing-origin-main: SYNC_STATUS=probe-error"
assert_contains "ERROR=" "$OUT" "missing-origin-main: ERROR present"

# --- Test 8: dirty working tree + flush ahead — refuse reset (probe-error exit 2) ---
repo=$(make_repo_pair flushdirty)
git -C "$repo" config user.email "test@test"
git -C "$repo" config user.name "Test"
mkdir -p "$repo/larch-logs"
printf 'y\n' > "$repo/larch-logs/y.md"
git -C "$repo" add larch-logs/y.md
git -C "$repo" commit -q -m "chore(larch-logs): flush implement run flushdirty"
printf 'dirty\n' >> "$repo/README.md"
run_check "$repo"
assert_rc "$RC" 2 "flush-dirty-tree: exit 2"
assert_contains "SYNC_STATUS=probe-error" "$OUT" "flush-dirty-tree: SYNC_STATUS=probe-error"
assert_contains "not clean" "$OUT" "flush-dirty-tree: ERROR mentions dirty tree"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
