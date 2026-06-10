#!/usr/bin/env bash
# test-redact-secrets.sh — Regression test for the secret scrubber and its
# integration with python/cli.py issue create-one.
#
# Three sections:
#   1. Unit: feed each covered pattern directly through redact-secrets.sh
#      and assert the placeholder appears and the raw token does not.
#   2. Idempotency: run a multi-pattern body through the helper twice;
#      assert the two outputs are byte-equal.
#   3. Edge cases: PEM blockquote/indentation and fail-closed truncation.
#
# Usage:
#   bash scripts/test-redact-secrets.sh
#
# Exit codes:
#   0 — all assertions passed
#   1 — first failure (message to stderr)

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HELPER="$REPO_ROOT/scripts/redact-secrets.sh"

# Test fixture tokens. Chosen so the shape matches the helper regexes but
# the values are obviously synthetic (safe to appear in logs).
# Split prefix in source to defuse GitHub's sk-* secret-scanner heuristic.
SK_TOKEN='sk-''ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD'
# Cursor CLI API key (crsr_ family, issue #3375). Prefix split in source so the
# synthetic token is not a single literal; runtime value is the full crsr_… key.
CRSR_TOKEN='crsr_''0123456789abcdefghijklmnopqrstuvwxyzABCDEF'
GHP_TOKEN='ghp_abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH'
AKIA_TOKEN='AKIAIOSFODNN7EXAMPLE'
JWT_TOKEN='eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
PEM_BLOCK='-----BEGIN RSA PRIVATE KEY-----
MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Qu
KUpRKfFLfRYC9AIKjbJTWit+CqvjWYzvQwECAwEAAQJAIJLixBy2qpFoS4DSmoEm
-----END RSA PRIVATE KEY-----'

PASS=0
FAIL=0
FAILED_TESTS=()

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label (contains $needle)"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (missing $needle)")
        echo "  FAIL: $label (missing $needle)" >&2
        echo "       haystack (first 500 chars): ${haystack:0:500}" >&2
    fi
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        PASS=$((PASS + 1))
        echo "  ok: $label (does not contain $needle)"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS+=("$label (leaked $needle)")
        echo "  FAIL: $label (leaked $needle)" >&2
        echo "       haystack (first 500 chars): ${haystack:0:500}" >&2
    fi
}

echo "=== Section 1: Unit tests (direct helper) ==="

out=$(printf '%s' "$SK_TOKEN" | "$HELPER")
assert_contains "$out" '<REDACTED-TOKEN>' 'sk-ant key → placeholder'
assert_not_contains "$out" "$SK_TOKEN" 'sk-ant key → raw absent'

out=$(printf '%s' "$CRSR_TOKEN" | "$HELPER")
assert_contains "$out" '<REDACTED-TOKEN>' 'crsr_ key → placeholder'
assert_not_contains "$out" "$CRSR_TOKEN" 'crsr_ key → raw absent'

out=$(printf '%s' "$GHP_TOKEN" | "$HELPER")
assert_contains "$out" '<REDACTED-TOKEN>' 'ghp_ PAT → placeholder'
assert_not_contains "$out" "$GHP_TOKEN" 'ghp_ PAT → raw absent'

out=$(printf '%s' "$AKIA_TOKEN" | "$HELPER")
assert_contains "$out" '<REDACTED-TOKEN>' 'AKIA key → placeholder'
assert_not_contains "$out" "$AKIA_TOKEN" 'AKIA key → raw absent'

out=$(printf '%s' "$JWT_TOKEN" | "$HELPER")
assert_contains "$out" '<REDACTED-TOKEN>' 'JWT → placeholder'
assert_not_contains "$out" "$JWT_TOKEN" 'JWT → raw absent'

out=$(printf '%s\n' "$PEM_BLOCK" | "$HELPER")
assert_contains "$out" '<REDACTED-PRIVATE-KEY>' 'PEM block → placeholder'
assert_not_contains "$out" 'MIIBOgIBAAJB' 'PEM block → key material absent'
assert_not_contains "$out" 'BEGIN RSA PRIVATE KEY' 'PEM block → BEGIN marker absent'

stream_state=$(mktemp "${TMPDIR:-/tmp}/test-redact-stream-state.XXXXXX")
printf 'in_pem=0\n' >"$stream_state"
out=$(printf '%s\n' "$PEM_BLOCK" | "$HELPER" --streaming --state-file "$stream_state")
assert_contains "$out" '<REDACTED-PRIVATE-KEY>' 'streaming PEM block → placeholder'
assert_not_contains "$out" 'MIIBOgIBAAJB' 'streaming PEM block → key material absent'

printf 'in_pem=0\n' >"$stream_state"
part1=$(printf '%s\n%s\n' '-----BEGIN RSA PRIVATE KEY-----' 'MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX' | "$HELPER" --streaming --state-file "$stream_state" 2>/dev/null || true)
part2=$(printf '%s\n%s\n' '6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Qu' '-----END RSA PRIVATE KEY-----' | "$HELPER" --streaming --state-file "$stream_state")
out="${part1}${part2}"
assert_contains "$out" '<REDACTED-PRIVATE-KEY>' 'streaming split PEM → placeholder'
assert_not_contains "$out" 'MIIBOgIBAAJB' 'streaming split PEM → first body absent'
assert_not_contains "$out" '6Ppy1tPf9' 'streaming split PEM → second body absent'

printf 'in_pem=0\n' >"$stream_state"
out=$(printf '%s\n' '-----END RSA PRIVATE KEY-----' | "$HELPER" --streaming --state-file "$stream_state")
assert_contains "$out" '-----END RSA PRIVATE KEY-----' 'streaming fresh mid-PEM tail passes through'

# crsr_ family must also be redacted on the line-oriented --streaming path
# (issue #3375 added the rule to both sed passes).
printf 'in_pem=0\n' >"$stream_state"
out=$(printf '%s\n' "$CRSR_TOKEN" | "$HELPER" --streaming --state-file "$stream_state")
assert_contains "$out" '<REDACTED-TOKEN>' 'streaming crsr_ key → placeholder'
assert_not_contains "$out" "$CRSR_TOKEN" 'streaming crsr_ key → raw absent'
rm -f "$stream_state"

echo ""
echo "=== Section 2: Idempotency ==="

multi_body="prefix $SK_TOKEN middle $GHP_TOKEN suffix $CRSR_TOKEN end"
pass1=$(printf '%s' "$multi_body" | "$HELPER")
pass2=$(printf '%s' "$pass1" | "$HELPER")
if [[ "$pass1" == "$pass2" ]]; then
    PASS=$((PASS + 1))
    echo "  ok: idempotent (single vs double pass byte-equal)"
else
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=('idempotency (single vs double pass differ)')
    echo "  FAIL: idempotency — pass1 != pass2" >&2
    echo "       pass1: $pass1" >&2
    echo "       pass2: $pass2" >&2
fi

echo ""
echo "=== Section 3: Edge cases ==="

# --- 3a: indented / blockquoted PEM blocks (F4) ---
INDENTED_BODY="prefix line
> -----BEGIN RSA PRIVATE KEY-----
> MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Q
> -----END RSA PRIVATE KEY-----
    -----BEGIN OPENSSH PRIVATE KEY-----
    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAA
    -----END OPENSSH PRIVATE KEY-----
suffix line"
indented_out=$(printf '%s' "$INDENTED_BODY" | "$HELPER")
assert_contains "$indented_out" '<REDACTED-PRIVATE-KEY>' '[edge] blockquote PEM → placeholder'
assert_not_contains "$indented_out" 'MIIBOgIBAAJB' '[edge] blockquote PEM → RSA key material absent'
assert_not_contains "$indented_out" 'b3BlbnNzaC1rZXktdjEA' '[edge] indented PEM → OPENSSH key material absent'
assert_contains "$indented_out" 'prefix line' '[edge] non-PEM prefix passes through'
assert_contains "$indented_out" 'suffix line' '[edge] non-PEM suffix passes through'

# --- 3b: unterminated PEM block (F3) ---
UNTERMINATED_BODY="opening text
-----BEGIN RSA PRIVATE KEY-----
MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Q
KUpRKfFLfRYC9AIKjbJTWit+CqvjWYzvQwECAwEAAQJAIJLixBy2qpFoS4DSmoEm
tail-that-should-not-silently-survive"
unterm_out=$(printf '%s
' "$UNTERMINATED_BODY" | "$HELPER" 2>/dev/null)
assert_contains "$unterm_out" '<REDACTED-PRIVATE-KEY>' '[edge] unterminated PEM → placeholder'
assert_contains "$unterm_out" 'opening text' '[edge] unterminated PEM → pre-BEGIN text preserved'
assert_not_contains "$unterm_out" 'MIIBOgIBAAJB' '[edge] unterminated PEM → key material absent'
assert_contains "$unterm_out" 'content truncated' '[edge] unterminated PEM → truncation marker emitted'
assert_not_contains "$unterm_out" 'tail-that-should-not-silently-survive' '[edge] unterminated PEM → tail dropped'

echo ""
echo "=== Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
    echo "Failed tests:" >&2
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t" >&2
    done
    exit 1
fi
echo "All assertions passed."
exit 0
