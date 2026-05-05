#!/usr/bin/env bash
# test-preflight-args.sh — regression harness for preflight.sh flag semantics.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/preflight.sh"

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d /tmp/larch-preflight-test.XXXXXX)
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

assert_not_exists() {
    local path=$1 label=$2
    if [ ! -e "$path" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (path exists: $path)"
    fi
}

run_preflight() {
    local repo=$1
    shift
    set +e
    OUT=$(cd "$repo" && "$SCRIPT" "$@" 2>&1)
    RC=$?
    set -e
}

make_repo() {
    local name=$1 origin work
    origin="$SANDBOX/$name-origin.git"
    work="$SANDBOX/$name-work"
    git init --bare "$origin" >/dev/null 2>&1
    git init "$work" >/dev/null 2>&1
    git -C "$work" config user.email "larch-test@example.invalid"
    git -C "$work" config user.name "Larch Test"
    git -C "$work" checkout -b main >/dev/null 2>&1
    printf 'base\n' > "$work/file.txt"
    git -C "$work" add file.txt
    git -C "$work" commit -m "base" >/dev/null 2>&1
    git -C "$work" remote add origin "$origin"
    git -C "$work" push -u origin main >/dev/null 2>&1
    printf '%s\n' "$work"
}

repo=$(make_repo default-dirty)
printf 'dirty\n' >> "$repo/file.txt"
run_preflight "$repo"
assert_rc "$RC" 2 "default: rejects dirty tree"
assert_contains "Working tree is not clean" "$OUT" "default: dirty diagnostic"

repo=$(make_repo default-nonmain)
git -C "$repo" checkout -b feature >/dev/null 2>&1
run_preflight "$repo"
assert_rc "$RC" 1 "default: rejects non-main"
assert_contains "Not on main branch" "$OUT" "default: non-main diagnostic"

repo=$(make_repo default-clean)
run_preflight "$repo"
assert_rc "$RC" 0 "default: accepts clean main"
assert_contains "PREFLIGHT=ok" "$OUT" "default: emits ok"

repo=$(make_repo skip-branch-dirty)
printf 'dirty\n' >> "$repo/file.txt"
run_preflight "$repo" --skip-branch-check
assert_rc "$RC" 2 "--skip-branch-check: still rejects dirty tree"
assert_contains "Working tree is not clean" "$OUT" "--skip-branch-check: dirty diagnostic"

repo=$(make_repo skip-branch-nonmain)
git -C "$repo" checkout -b feature >/dev/null 2>&1
run_preflight "$repo" --skip-branch-check
assert_rc "$RC" 0 "--skip-branch-check: accepts clean non-main"
assert_contains "PREFLIGHT=ok" "$OUT" "--skip-branch-check: emits ok"

repo=$(make_repo skip-clean-nonmain)
git -C "$repo" checkout -b feature >/dev/null 2>&1
printf 'dirty\n' >> "$repo/file.txt"
run_preflight "$repo" --skip-clean-check
assert_rc "$RC" 1 "--skip-clean-check: still rejects non-main"
assert_contains "Not on main branch" "$OUT" "--skip-clean-check: non-main diagnostic"

repo=$(make_repo skip-clean-dirty-main)
printf 'dirty\n' >> "$repo/file.txt"
run_preflight "$repo" --skip-clean-check
assert_rc "$RC" 0 "--skip-clean-check: accepts dirty main"
assert_contains "PREFLIGHT=ok" "$OUT" "--skip-clean-check: emits ok"

repo=$(make_repo skip-both)
git -C "$repo" checkout -b feature >/dev/null 2>&1
printf 'dirty\n' >> "$repo/file.txt"
run_preflight "$repo" --skip-branch-check --skip-clean-check
assert_rc "$RC" 0 "both flags: accepts dirty non-main"
assert_contains "PREFLIGHT=ok" "$OUT" "both flags: emits ok"

repo=$(make_repo sentinel)
sentinel_path=$(cd "$repo" && git rev-parse --git-path larch-stalled-run.txt)
case "$sentinel_path" in
    /*) ;;
    *) sentinel_path="$repo/$sentinel_path" ;;
esac
printf 'ISSUE_NUMBER=1\n' > "$sentinel_path"
run_preflight "$repo"
assert_rc "$RC" 0 "sentinel: clean main preflight succeeds"
assert_not_exists "$sentinel_path" "sentinel: clean check clears stalled-run sentinel"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
