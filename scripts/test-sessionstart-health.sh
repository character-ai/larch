#!/usr/bin/env bash
# test-sessionstart-health.sh — Regression test for scripts/sessionstart-health.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/sessionstart-health.sh"

if [[ ! -x "$SCRIPT" ]]; then
    echo "FAIL: $SCRIPT does not exist or is not executable" >&2
    exit 1
fi

REAL_JQ=$(command -v jq || true)
REAL_GIT=$(command -v git || true)
BASH_BIN=$(command -v bash || true)
if [[ -z "$REAL_JQ" || ! -x "$REAL_JQ" ]]; then
    echo "FAIL: harness jq not on PATH; cannot validate JSON output" >&2
    exit 1
fi
if [[ -z "$REAL_GIT" || ! -x "$REAL_GIT" ]]; then
    echo "FAIL: harness git not on PATH; cannot create git-state fixtures" >&2
    exit 1
fi
if [[ -z "$BASH_BIN" || ! -x "$BASH_BIN" ]]; then
    echo "FAIL: could not resolve bash on ambient PATH" >&2
    exit 1
fi

tmp=$(mktemp -d /tmp/larch-sessionstart-test.XXXXXX)
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
        echo "  ok: $label (contains '$needle')"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (missing '$needle')")
        echo "  FAIL: $label (missing '$needle')" >&2
        echo "       haystack: '$haystack'" >&2
    fi
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label (does not contain '$needle')"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (leaked '$needle')")
        echo "  FAIL: $label (leaked '$needle')" >&2
    fi
}

link_tool() {
    local dir=$1 tool=$2 resolved
    resolved=$(command -v "$tool" || true)
    if [[ -n "$resolved" && -x "$resolved" ]]; then
        ln -sf "$resolved" "$dir/$tool"
    fi
}

build_bin() {
    local dir=$1
    rm -rf "$dir"
    mkdir -p "$dir"
    link_tool "$dir" grep
    link_tool "$dir" awk
    link_tool "$dir" cat
}

add_real_tool() {
    local dir=$1 tool=$2 path=$3
    ln -sf "$path" "$dir/$tool"
}

add_git_not_worktree_stub() {
    local dir=$1
    cat > "$dir/git" <<STUB
#!$BASH_BIN
if [[ "\$1" == "rev-parse" && "\${2:-}" == "--is-inside-work-tree" ]]; then
    exit 1
fi
exit 0
STUB
    chmod +x "$dir/git"
}

run_from_dir() {
    local bin=$1 cwd=$2 out_file=$3 err_file=$4 rc=0
    (cd "$cwd" && env -i PATH="$bin" "$BASH_BIN" "$SCRIPT" < /dev/null > "$out_file" 2> "$err_file") || rc=$?
    printf '%s\n' "$rc"
}

ctx_from_stdout() {
    local stdout=$1
    printf '%s' "$stdout" | "$REAL_JQ" -r '.hookSpecificOutput.additionalContext // empty'
}

assert_valid_json() {
    local stdout=$1 label=$2 hook_event
    if ! printf '%s' "$stdout" | "$REAL_JQ" -e . >/dev/null 2>&1; then
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label: stdout is not valid JSON")
        echo "  FAIL: $label: stdout is not valid JSON" >&2
        echo "       stdout: '$stdout'" >&2
        return
    fi
    PASS=$((PASS + 1))
    echo "  ok: $label: stdout is valid JSON"
    hook_event=$(printf '%s' "$stdout" | "$REAL_JQ" -r '.hookSpecificOutput.hookEventName // empty')
    assert_eq "$hook_event" "SessionStart" "$label: hookEventName"
}

make_repo() {
    local name=$1 repo
    repo="$tmp/$name"
    git init "$repo" >/dev/null 2>&1
    git -C "$repo" config user.email "larch-test@example.invalid"
    git -C "$repo" config user.name "Larch Test"
    git -C "$repo" checkout -b main >/dev/null 2>&1
    printf 'base\n' > "$repo/file.txt"
    git -C "$repo" add file.txt
    git -C "$repo" commit -m "base" >/dev/null 2>&1
    printf '%s\n' "$repo"
}

echo "=== Case 1: jq + git both present, not a work-tree ==="
build_bin "$tmp/c1_bin"
add_real_tool "$tmp/c1_bin" jq "$REAL_JQ"
add_git_not_worktree_stub "$tmp/c1_bin"
mkdir -p "$tmp/outside"
rc=$(run_from_dir "$tmp/c1_bin" "$tmp/outside" "$tmp/c1.out" "$tmp/c1.err")
assert_eq "$rc" "0" "case 1: exit code 0"
stdout=$(cat "$tmp/c1.out")
assert_empty "$stdout" "case 1: stdout empty"

echo "=== Case 2: jq missing, git present ==="
build_bin "$tmp/c2_bin"
add_git_not_worktree_stub "$tmp/c2_bin"
rc=$(run_from_dir "$tmp/c2_bin" "$tmp/outside" "$tmp/c2.out" "$tmp/c2.err")
assert_eq "$rc" "0" "case 2: exit code 0"
stdout=$(cat "$tmp/c2.out")
assert_valid_json "$stdout" "case 2"
ctx=$(ctx_from_stdout "$stdout")
assert_contains "$ctx" "jq" "case 2: additionalContext mentions jq"
assert_not_contains "$ctx" "git not on PATH" "case 2: additionalContext does not mention git"

echo "=== Case 3: jq present, git missing ==="
build_bin "$tmp/c3_bin"
add_real_tool "$tmp/c3_bin" jq "$REAL_JQ"
rc=$(run_from_dir "$tmp/c3_bin" "$tmp/outside" "$tmp/c3.out" "$tmp/c3.err")
assert_eq "$rc" "0" "case 3: exit code 0"
stdout=$(cat "$tmp/c3.out")
assert_valid_json "$stdout" "case 3"
ctx=$(ctx_from_stdout "$stdout")
assert_contains "$ctx" "git" "case 3: additionalContext mentions git"
assert_not_contains "$ctx" "jq not on PATH" "case 3: additionalContext does not mention jq"

echo "=== Case 4: both missing ==="
build_bin "$tmp/c4_bin"
rc=$(run_from_dir "$tmp/c4_bin" "$tmp/outside" "$tmp/c4.out" "$tmp/c4.err")
assert_eq "$rc" "0" "case 4: exit code 0"
stdout=$(cat "$tmp/c4.out")
assert_valid_json "$stdout" "case 4"
ctx=$(ctx_from_stdout "$stdout")
assert_contains "$ctx" "jq" "case 4: additionalContext mentions jq"
assert_contains "$ctx" "git" "case 4: additionalContext mentions git"

build_bin "$tmp/real_bin"
add_real_tool "$tmp/real_bin" jq "$REAL_JQ"
add_real_tool "$tmp/real_bin" git "$REAL_GIT"

echo "=== Case 5: dirty working tree ==="
repo=$(make_repo dirty)
printf 'dirty\n' >> "$repo/file.txt"
rc=$(run_from_dir "$tmp/real_bin" "$repo" "$tmp/c5.out" "$tmp/c5.err")
assert_eq "$rc" "0" "case 5: exit code 0"
ctx=$(ctx_from_stdout "$(cat "$tmp/c5.out")")
assert_contains "$ctx" "uncommitted changes" "case 5: dirty tree warning"

echo "=== Case 6: larch-managed stash ==="
repo=$(make_repo larch-stash)
printf 'stash\n' > "$repo/stash.txt"
git -C "$repo" stash push -u -m "larch-stalled-42-12d 20260505T000000Z" >/dev/null 2>&1
rc=$(run_from_dir "$tmp/real_bin" "$repo" "$tmp/c6.out" "$tmp/c6.err")
assert_eq "$rc" "0" "case 6: exit code 0"
ctx=$(ctx_from_stdout "$(cat "$tmp/c6.out")")
assert_contains "$ctx" "leftover larch-managed stash" "case 6: larch stash warning"

echo "=== Case 7: non-larch stash is ignored ==="
repo=$(make_repo manual-stash)
printf 'stash\n' > "$repo/stash.txt"
git -C "$repo" stash push -u -m "manual work" >/dev/null 2>&1
rc=$(run_from_dir "$tmp/real_bin" "$repo" "$tmp/c7.out" "$tmp/c7.err")
assert_eq "$rc" "0" "case 7: exit code 0"
ctx=$(ctx_from_stdout "$(cat "$tmp/c7.out")")
assert_not_contains "$ctx" "leftover larch-managed stash" "case 7: non-larch stash ignored"

echo "=== Case 8: interrupted rebase state ==="
repo=$(make_repo interrupted)
rebase_head=$(cd "$repo" && git rev-parse --git-path REBASE_HEAD)
case "$rebase_head" in
    /*) ;;
    *) rebase_head="$repo/$rebase_head" ;;
esac
printf 'abc123\n' > "$rebase_head"
rc=$(run_from_dir "$tmp/real_bin" "$repo" "$tmp/c8.out" "$tmp/c8.err")
assert_eq "$rc" "0" "case 8: exit code 0"
ctx=$(ctx_from_stdout "$(cat "$tmp/c8.out")")
assert_contains "$ctx" "interrupted rebase" "case 8: interrupted state warning"

echo "=== Case 9: unmerged local feature branch ==="
repo=$(make_repo unmerged)
git -C "$repo" checkout -b feature >/dev/null 2>&1
printf 'feature\n' >> "$repo/file.txt"
git -C "$repo" commit -am "feature" >/dev/null 2>&1
git -C "$repo" checkout main >/dev/null 2>&1
rc=$(run_from_dir "$tmp/real_bin" "$repo" "$tmp/c9.out" "$tmp/c9.err")
assert_eq "$rc" "0" "case 9: exit code 0"
ctx=$(ctx_from_stdout "$(cat "$tmp/c9.out")")
assert_contains "$ctx" "not merged into main" "case 9: unmerged branch warning"

echo "=== Case 10: stalled-run sentinel ==="
repo=$(make_repo sentinel)
sentinel=$(cd "$repo" && git rev-parse --git-path larch-stalled-run.txt)
case "$sentinel" in
    /*) ;;
    *) sentinel="$repo/$sentinel" ;;
esac
cat > "$sentinel" <<'SENTINEL'
ISSUE_NUMBER=77
ISSUE_URL=https://github.example/owner/repo/issues/77
STALL_STEP=12d
STASH_REF=stash@{0}
TIMESTAMP=2026-05-05T00:00:00Z
SENTINEL
rc=$(run_from_dir "$tmp/real_bin" "$repo" "$tmp/c10.out" "$tmp/c10.err")
assert_eq "$rc" "0" "case 10: exit code 0"
ctx=$(ctx_from_stdout "$(cat "$tmp/c10.out")")
assert_contains "$ctx" "prior /implement run for #77 stalled at step 12d" "case 10: sentinel warning"
assert_contains "$ctx" "stash@{0}" "case 10: sentinel stash ref"

echo "=== Case 11: not inside a work-tree skips git-state probes ==="
rc=$(run_from_dir "$tmp/real_bin" "$tmp/outside" "$tmp/c11.out" "$tmp/c11.err")
assert_eq "$rc" "0" "case 11: exit code 0"
stdout=$(cat "$tmp/c11.out")
assert_empty "$stdout" "case 11: stdout empty outside work-tree"

echo
echo "=== Summary ==="
echo "  passed: $PASS"
echo "  failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
    echo >&2
    echo "Failed tests:" >&2
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t" >&2
    done
    exit 1
fi

echo "all tests passed"
exit 0
