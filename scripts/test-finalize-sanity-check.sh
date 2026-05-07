#!/usr/bin/env bash
# test-finalize-sanity-check.sh — regression harness for Step 18 cleanup sanity checks.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REAL_SCRIPT="$REPO_ROOT/scripts/implement-finalize.sh"

PASS=0
FAIL=0
SANDBOX=$(mktemp -d /tmp/larch-finalize-sanity-test.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT
mkdir -p "$SANDBOX/scripts"
cp "$REAL_SCRIPT" "$SANDBOX/scripts/implement-finalize.sh"
chmod +x "$SANDBOX/scripts/implement-finalize.sh"

cat > "$SANDBOX/scripts/cleanup-tmpdir.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" >> "$SANDBOX/cleanup-argv.txt"
exit 0
STUB
chmod +x "$SANDBOX/scripts/cleanup-tmpdir.sh"

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        printf '  missing: %s\n' "$needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        printf '  unexpected: %s\n' "$needle"
    else
        PASS=$((PASS + 1))
        echo "PASS: $label"
    fi
}

write_state() {
    local dir=$1 prefix=$2 include_expected_session=${3:-true}
    {
        printf 'BRANCH_NAME=feature/finalize-sanity\n'
        printf 'PR_NUMBER=\n'
        printf 'PR_TITLE=Finalize sanity\n'
        printf 'PR_URL=\n'
        printf 'ISSUE_NUMBER=\n'
        printf 'REPO=owner/repo\n'
        printf 'DRAFT=false\n'
        printf 'MERGE=false\n'
        printf 'SLACK_ENABLED=false\n'
        printf 'SLACK_AVAILABLE=false\n'
        printf 'DEFERRED=false\n'
        printf 'REPO_UNAVAILABLE=true\n'
        printf 'PR_CLOSED=false\n'
        printf 'DESIGN_ONLY_DONE=false\n'
        printf 'BAIL_NEEDS_USER_INPUT=false\n'
        printf 'STALL_TRACKING=false\n'
        printf 'STALL_STEP=\n'
        printf 'DONE_RENAME_APPLIED=false\n'
        if [ "$include_expected_session" = "true" ]; then
            printf 'EXPECTED_SESSION_ID=session-ok\n'
        fi
        printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=%s\n' "$prefix"
    } > "$dir/finalize-state.sh"
}

run_teardown() {
    local dir=$1
    "$SANDBOX/scripts/implement-finalize.sh" teardown --state-file "$dir/finalize-state.sh" --implement-tmpdir "$dir" 2>&1
}

HAPPY="/tmp/claude-implement-larch1-happy-$$"
rm -rf "$HAPPY"
mkdir -p "$HAPPY"
printf 'session-ok\n' > "$HAPPY/session-id"
write_state "$HAPPY" "claude-implement-larch1-"
: > "$SANDBOX/cleanup-argv.txt"
OUT=$(run_teardown "$HAPPY")
assert_contains "--dir" "$(cat "$SANDBOX/cleanup-argv.txt")" "happy path invokes cleanup"
assert_not_contains "cleanup target failed sanity check" "$OUT" "happy path has no sanity warning"

FOREIGN="/tmp/claude-implement-foreign-$$"
rm -rf "$FOREIGN"
mkdir -p "$FOREIGN"
printf 'session-ok\n' > "$FOREIGN/session-id"
: > "$FOREIGN/execution-issues.md"
write_state "$FOREIGN" "claude-implement-larch1-"
: > "$SANDBOX/cleanup-argv.txt"
OUT=$(run_teardown "$FOREIGN")
assert_contains "cleanup target failed sanity check" "$OUT" "foreign basename refuses cleanup"
assert_contains "session-id-match=y" "$OUT" "foreign basename reports session match"
assert_not_contains "--dir" "$(cat "$SANDBOX/cleanup-argv.txt")" "foreign basename skips cleanup"
assert_contains "cleanup skipped" "$(cat "$FOREIGN/execution-issues.md")" "foreign basename logs execution issue"

MISSING_ID="/tmp/claude-implement-larch1-missingid-$$"
rm -rf "$MISSING_ID"
mkdir -p "$MISSING_ID"
write_state "$MISSING_ID" "claude-implement-larch1-"
: > "$SANDBOX/cleanup-argv.txt"
OUT=$(run_teardown "$MISSING_ID")
assert_contains "session-id-match=n" "$OUT" "missing session-id refuses cleanup"
assert_not_contains "--dir" "$(cat "$SANDBOX/cleanup-argv.txt")" "missing session-id skips cleanup"

LEGACY="/tmp/claude-implement-larch1-legacy-$$"
rm -rf "$LEGACY"
mkdir -p "$LEGACY"
write_state "$LEGACY" "claude-implement-larch1-" false
: > "$SANDBOX/cleanup-argv.txt"
OUT=$(run_teardown "$LEGACY")
assert_contains "EXPECTED_SESSION_ID missing" "$OUT" "legacy state warns about basename-only validation"
assert_contains "--dir" "$(cat "$SANDBOX/cleanup-argv.txt")" "legacy basename-only path invokes cleanup"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
