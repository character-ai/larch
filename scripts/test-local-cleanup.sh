#!/usr/bin/env bash
# test-local-cleanup.sh — regression harness for post-merge local cleanup.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CLEANUP="$SCRIPT_DIR/local-cleanup.sh"

[ -x "$CLEANUP" ] || { echo "FAIL: $CLEANUP not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-local-cleanup.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

pass() {
    echo "  ok: $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "FAIL: $1" >&2
    FAIL=$((FAIL + 1))
}

assert_contains() {
    local label="$1"
    local haystack="$2"
    local needle="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:400})"
    fi
}

assert_not_contains() {
    local label="$1"
    local haystack="$2"
    local needle="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (unexpected $needle; got ${haystack:0:400})"
    fi
}

assert_equals() {
    local label="$1"
    local got="$2"
    local expected="$3"
    if [ "$got" = "$expected" ]; then
        pass "$label"
    else
        fail "$label (expected $expected; got $got)"
    fi
}

assert_not_equals() {
    local label="$1"
    local got="$2"
    local unexpected="$3"
    if [ "$got" != "$unexpected" ]; then
        pass "$label"
    else
        fail "$label (unexpectedly got $unexpected)"
    fi
}

config_git_identity() {
    local repo="$1"
    git -C "$repo" config user.email "ci@test"
    git -C "$repo" config user.name "Test CI"
}

init_git_repo_main() {
    local repo="$1"
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" symbolic-ref HEAD refs/heads/main
    config_git_identity "$repo"
}

commit_path() {
    local repo="$1"
    local path="$2"
    local content="$3"
    local subject="$4"
    mkdir -p "$(dirname "$repo/$path")"
    printf '%s\n' "$content" > "$repo/$path"
    git -C "$repo" add -- "$path"
    git -C "$repo" commit -q -m "$subject"
}

setup_remote_repo() {
    local label="$1"
    local remote="$TMP/$label-origin.git"
    local seed="$TMP/$label-seed"
    local repo="$TMP/$label-repo"

    git init -q --bare "$remote"
    init_git_repo_main "$seed"
    commit_path "$seed" "README.md" "initial" "init"
    git -C "$seed" remote add origin "$remote"
    git -C "$seed" push -q -u origin main
    git --git-dir="$remote" symbolic-ref HEAD refs/heads/main

    git clone -q "$remote" "$repo"
    git -C "$repo" checkout -q main
    config_git_identity "$repo"
    git -C "$repo" branch feature
    printf '%s\n' "$repo"
}

run_cleanup() {
    local label="$1"
    local repo="$2"
    local out_file="$TMP/$label-cleanup.out"
    local err_file="$TMP/$label-cleanup.err"

    (cd "$repo" && "$CLEANUP" --branch feature > "$out_file" 2> "$err_file")
    LAST_CLEANUP_OUT="$(cat "$out_file")"
    LAST_CLEANUP_ERR="$(cat "$err_file")"
}

flush_repo=$(setup_remote_repo "flush-orphan")
commit_path \
    "$flush_repo" \
    "larch-logs/implement/prior-run/session-transcript.jsonl" \
    '{"type":"message","text":"prior"}' \
    "chore(larch-logs): flush implement run prior-run"
flush_origin=$(git -C "$flush_repo" rev-parse origin/main)
run_cleanup "flush-orphan" "$flush_repo"
assert_contains "flush-orphan success envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=true"
assert_contains "flush-orphan branch deleted" "$LAST_CLEANUP_OUT" "BRANCH_DELETED=true"
assert_contains "flush-orphan drop warning" "$LAST_CLEANUP_ERR" "Dropping 1 prior-run larch-log flush commit(s) before pull"
flush_head=$(git -C "$flush_repo" rev-parse HEAD)
assert_equals "flush-orphan reset to origin/main" "$flush_head" "$flush_origin"

no_orphan_repo=$(setup_remote_repo "no-orphan")
no_orphan_origin=$(git -C "$no_orphan_repo" rev-parse origin/main)
run_cleanup "no-orphan" "$no_orphan_repo"
assert_contains "no-orphan success envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=true"
assert_contains "no-orphan branch deleted" "$LAST_CLEANUP_OUT" "BRANCH_DELETED=true"
assert_not_contains "no-orphan no drop warning" "$LAST_CLEANUP_ERR" "Dropping"
no_orphan_head=$(git -C "$no_orphan_repo" rev-parse HEAD)
assert_equals "no-orphan remains on origin/main" "$no_orphan_head" "$no_orphan_origin"

non_flush_repo=$(setup_remote_repo "non-flush-ahead")
commit_path "$non_flush_repo" "operator-note.txt" "keep me" "operator local note"
non_flush_origin=$(git -C "$non_flush_repo" rev-parse origin/main)
run_cleanup "non-flush-ahead" "$non_flush_repo"
assert_contains "non-flush-ahead success envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=true"
assert_not_contains "non-flush-ahead no drop warning" "$LAST_CLEANUP_ERR" "Dropping"
non_flush_head=$(git -C "$non_flush_repo" rev-parse HEAD)
assert_not_equals "non-flush-ahead keeps local commit" "$non_flush_head" "$non_flush_origin"
if [ -f "$non_flush_repo/operator-note.txt" ]; then
    pass "non-flush-ahead preserves non-flush file"
else
    fail "non-flush-ahead preserves non-flush file"
fi

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
