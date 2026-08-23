#!/usr/bin/env bash
# test-cache-root-validation.sh — regression harness for larch cache session root validators.
# `session cleanup-tmpdir` moved to the Rust owner in issue #8057; its cache-root,
# /tmp, and unrelated-path cases now live in the Rust parity goldens.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
if [ -z "${LARCH_BINARY:-}" ]; then
    if [ -x "$REPO_ROOT/target/debug/larch" ]; then
        export LARCH_BINARY="$REPO_ROOT/target/debug/larch"
    elif [ -x "$REPO_ROOT/target/release/larch" ]; then
        export LARCH_BINARY="$REPO_ROOT/target/release/larch"
    else
        cargo build --quiet --locked --package larch-cli --bin larch
        export LARCH_BINARY="$REPO_ROOT/target/debug/larch"
    fi
fi
FINALIZE=("$REPO_ROOT/scripts/larch.sh" implement-finalize)
TOKEN_CLI=("$REPO_ROOT/scripts/larch.sh" token)

PASS=0
FAIL=0
TMPROOT=$(mktemp -d /tmp/larch-cache-root-test.XXXXXX)
trap 'rm -rf "$TMPROOT"' EXIT

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

write_state() {
    local dir=$1
    {
        printf 'BRANCH_NAME=feature/cache-root\n'
        printf 'PR_NUMBER=\n'
        printf 'PR_TITLE=Cache root validation\n'
        printf 'PR_URL=\n'
        printf 'ISSUE_NUMBER=\n'
        printf 'REPO=owner/repo\n'
        printf 'DRAFT=false\n'
        printf 'MERGE=false\n'
        printf 'DEFERRED=false\n'
        printf 'REPO_UNAVAILABLE=true\n'
        printf 'PR_CLOSED=false\n'
        printf 'DESIGN_ONLY_DONE=false\n'
        printf 'BAIL_NEEDS_USER_INPUT=false\n'
        printf 'STALL_TRACKING=false\n'
        printf 'STALL_STEP=\n'
        printf 'DONE_RENAME_APPLIED=false\n'
        printf 'EXPECTED_SESSION_ID=session-cache-mismatch\n'
        printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=%s\n' "$(basename "$dir")"
    } > "$dir/finalize-state.sh"
    printf 'session-cache\n' > "$dir/session-id"
}

CACHE_ROOT="$TMPROOT/cache/larch/sessions"
mkdir -p "$CACHE_ROOT"

FINALIZE_TARGET="$CACHE_ROOT/claude-implement-cache-finalize"
mkdir -p "$FINALIZE_TARGET"
write_state "$FINALIZE_TARGET"
rc=0
XDG_CACHE_HOME="$TMPROOT/cache" "${FINALIZE[@]}" teardown --state-file "$FINALIZE_TARGET/finalize-state.sh" --implement-tmpdir "$FINALIZE_TARGET" >/dev/null 2>&1 || rc=$?
assert_rc "$rc" 0 "Rust implement-finalize accepts cache sessions root"

TOKEN_DIR="$CACHE_ROOT/larch-research-token-tally"
rc=0
XDG_CACHE_HOME="$TMPROOT/cache" "${TOKEN_CLI[@]}" lane-write --phase research --lane cache --tool claude --total-tokens 10 --dir "$TOKEN_DIR" >/dev/null 2>&1 || rc=$?
assert_rc "$rc" 0 "token-tally accepts cache sessions root"

TMP_TOKEN=$(mktemp -d /tmp/larch-cache-root-token.XXXXXX)
rc=0
"${TOKEN_CLI[@]}" lane-write --phase research --lane tmp --tool claude --total-tokens 10 --dir "$TMP_TOKEN" >/dev/null 2>&1 || rc=$?
assert_rc "$rc" 0 "token-tally still accepts /tmp"
rm -rf "$TMP_TOKEN"

if [ -d /private/tmp ]; then
    PRIVATE_TOKEN=$(mktemp -d /private/tmp/larch-cache-root-token.XXXXXX)
    rc=0
    "${TOKEN_CLI[@]}" lane-report --dir "$PRIVATE_TOKEN" >/dev/null 2>&1 || rc=$?
    assert_rc "$rc" 0 "token-tally still accepts /private/tmp"
    rm -rf "$PRIVATE_TOKEN"
fi

UNRELATED="$REPO_ROOT/not-a-session-root"

rc=0
"${TOKEN_CLI[@]}" lane-report --dir "$UNRELATED" >/dev/null 2>&1 || rc=$?
assert_rc "$rc" 1 "token-tally rejects unrelated path"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
