#!/usr/bin/env bash
# test-scrub-log-secrets.sh — regression test for scripts/scrub-log-secrets.sh,
# the pre-flush secret gate run before every larch run-log commit.
#
# Sections:
#   1. Cursor incident class: crsr_ and key_ keys are scrubbed; clean files are
#      left byte-for-byte untouched; the loud warning fires; exit 0; the
#      LARCH_SECRET_SCRUB_* contract is emitted on stdout.
#   2. Backstop + extra families: base families (ghp_/PEM) and the extra
#      prefixed families (Slack/Google) are scrubbed.
#   3. No-violation, idempotency, recursion, and argument-validation behavior.
#
# Usage: bash scripts/test-scrub-log-secrets.sh
# Exit codes: 0 all assertions passed; 1 first failure (message on stderr).

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GATE="$REPO_ROOT/scripts/scrub-log-secrets.sh"

# Synthetic fixtures. Each prefix is split across a '' boundary so the full
# token literal never appears in this file (so the file is not itself a
# secret-scanner hit); bash concatenates the halves at runtime.
CRSR='crsr_''1620abcdefghijklmnopqrstuvwxyz0123456789'
KEYU='key_''abcdefghijklmnopqrstuvwxyz0123456789ABCDEF'
GHP='ghp_''abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH'
SLACK='xoxb''-1234567890-abcdefghijklmnopqrst'
GOOGLE='AIza''abcdefghijklmnopqrstuvwxyz0123456789'
PEM_BEGIN='-----BEGIN RSA PRIVATE KEY-----'
PEM_BODY='MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9'
PEM_END='-----END RSA PRIVATE KEY-----'

PASS=0
FAIL=0
FAILED_TESTS=()

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        PASS=$((PASS + 1)); echo "  ok: $label"
    else
        FAIL=$((FAIL + 1)); FAILED_TESTS+=("$label (missing $needle)")
        echo "  FAIL: $label (missing $needle)" >&2
    fi
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        PASS=$((PASS + 1)); echo "  ok: $label"
    else
        FAIL=$((FAIL + 1)); FAILED_TESTS+=("$label (leaked $needle)")
        echo "  FAIL: $label (leaked $needle)" >&2
    fi
}

assert_eq() {
    local got="$1" want="$2" label="$3"
    if [[ "$got" == "$want" ]]; then
        PASS=$((PASS + 1)); echo "  ok: $label"
    else
        FAIL=$((FAIL + 1)); FAILED_TESTS+=("$label (got '$got' want '$want')")
        echo "  FAIL: $label (got '$got' want '$want')" >&2
    fi
}

# run_gate DIR -> sets RC, OUT (stdout/contract), ERR (stderr/banner)
run_gate() {
    local dir="$1" errfile
    errfile=$(mktemp "${TMPDIR:-/tmp}/scrub-test-err.XXXXXX")
    set +e
    OUT=$(bash "$GATE" "$dir" 2>"$errfile")
    RC=$?
    set -e
    ERR=$(cat "$errfile")
    rm -f "$errfile"
}

kv() { printf '%s\n' "$OUT" | sed -n "s/^$1=//p" | tail -1; }

echo "=== Section 1: Cursor incident class ==="
WORK=$(mktemp -d "${TMPDIR:-/tmp}/scrub-test.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/round-1/revise" "$WORK/sub"
printf 'cmd --api-key %s --workspace /x\n' "$CRSR" > "$WORK/round-1/findings.md"
printf 'admin %s end\n' "$KEYU" > "$WORK/round-1/revise/notes.md"
printf 'no secrets here\njust prose\n' > "$WORK/clean.md"
printf 'no-trailing-newline-clean' > "$WORK/sub/clean-nonl.txt"
CLEAN_SHA_BEFORE=$(shasum "$WORK/clean.md" "$WORK/sub/clean-nonl.txt")

run_gate "$WORK"
assert_eq "$RC" "0" "exit 0 after scrub"
assert_eq "$(kv LARCH_SECRET_SCRUB_VIOLATIONS)" "2" "contract: 2 violations"
assert_eq "$(kv LARCH_SECRET_SCRUB_FILES)" "2" "contract: 2 files scrubbed"
assert_contains "$ERR" 'SECRETS DETECTED AND SCRUBBED' "loud banner on stderr"
assert_contains "$ERR" 'cursor-api-key' "banner names the cursor family"
assert_not_contains "$(cat "$WORK/round-1/findings.md")" "$CRSR" "crsr_ key raw absent"
assert_contains "$(cat "$WORK/round-1/findings.md")" '<REDACTED-TOKEN>' "crsr_ replaced with placeholder"
assert_not_contains "$(cat "$WORK/round-1/revise/notes.md")" "$KEYU" "key_ raw absent (recursion 2 deep)"
CLEAN_SHA_AFTER=$(shasum "$WORK/clean.md" "$WORK/sub/clean-nonl.txt")
assert_eq "$CLEAN_SHA_AFTER" "$CLEAN_SHA_BEFORE" "clean files byte-identical (incl. no trailing newline)"

echo ""
echo "=== Section 2: backstop + extra families ==="
WORK2=$(mktemp -d "${TMPDIR:-/tmp}/scrub-test2.XXXXXX")
mkdir -p "$WORK2"
printf 'token %s here\n' "$GHP" > "$WORK2/gh.log"
printf 'slack %s and google %s\n' "$SLACK" "$GOOGLE" > "$WORK2/vendors.log"
printf '%s\n%s\n%s\n' "$PEM_BEGIN" "$PEM_BODY" "$PEM_END" > "$WORK2/key.pem"
run_gate "$WORK2"
assert_eq "$RC" "0" "exit 0"
assert_not_contains "$(cat "$WORK2/gh.log")" "$GHP" "ghp_ backstop scrubbed"
assert_not_contains "$(cat "$WORK2/vendors.log")" "$SLACK" "slack token scrubbed"
assert_not_contains "$(cat "$WORK2/vendors.log")" "$GOOGLE" "google key scrubbed"
assert_not_contains "$(cat "$WORK2/key.pem")" "$PEM_BODY" "PEM key material scrubbed"
assert_contains "$(cat "$WORK2/key.pem")" '<REDACTED-PRIVATE-KEY>' "PEM placeholder present"
rm -rf "$WORK2"

echo ""
echo "=== Section 3: no-violation, idempotency, args ==="
# Idempotency: re-running the gate on the already-scrubbed Section 1 tree finds
# nothing and leaves the tree unchanged.
TREE_SHA_BEFORE=$(find "$WORK" -type f | LC_ALL=C sort | xargs shasum | shasum)
run_gate "$WORK"
assert_eq "$RC" "0" "idempotent re-run: exit 0"
assert_eq "$(kv LARCH_SECRET_SCRUB_VIOLATIONS)" "0" "idempotent re-run: 0 violations"
assert_eq "$ERR" "" "idempotent re-run: no banner"
TREE_SHA_AFTER=$(find "$WORK" -type f | LC_ALL=C sort | xargs shasum | shasum)
assert_eq "$TREE_SHA_AFTER" "$TREE_SHA_BEFORE" "idempotent re-run: tree unchanged"

# Clean-only tree: quiet success, zero counts.
WORK3=$(mktemp -d "${TMPDIR:-/tmp}/scrub-test3.XXXXXX")
printf 'just docs\nrun_id AAAAAAAA-1111-2222-3333-444444444444\n' > "$WORK3/manifest-ish.json"
run_gate "$WORK3"
assert_eq "$RC" "0" "clean tree: exit 0"
assert_eq "$(kv LARCH_SECRET_SCRUB_VIOLATIONS)" "0" "clean tree: 0 violations (UUID not a secret)"
assert_eq "$ERR" "" "clean tree: no banner"
rm -rf "$WORK3"

# Argument validation: missing arg and non-directory both exit 2.
set +e
bash "$GATE" >/dev/null 2>&1; rc_noarg=$?
bash "$GATE" "$WORK/round-1/findings.md" >/dev/null 2>&1; rc_notdir=$?
set -e
assert_eq "$rc_noarg" "2" "missing argument exits 2"
assert_eq "$rc_notdir" "2" "non-directory argument exits 2"

echo ""
echo "=== Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
    echo "Failed tests:" >&2
    for t in "${FAILED_TESTS[@]}"; do echo "  - $t" >&2; done
    exit 1
fi
echo "All assertions passed."
exit 0
