#!/usr/bin/env bash
# test-redact-tmpdir-paths.sh — regression harness for tmpdir path redaction.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HELPER="$REPO_ROOT/scripts/redact-tmpdir-paths.sh"

[ -x "$HELPER" ] || { echo "FAIL: $HELPER not executable"; exit 1; }

PASS=0
FAIL=0

assert_eq() {
    local actual=$1 expected=$2 label=$3
    if [ "$actual" = "$expected" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        printf '  expected: %s\n  actual:   %s\n' "$expected" "$actual"
    fi
}

run_redactor() {
    printf '%s' "$1" | "$HELPER"
}

assert_eq "$(run_redactor '/tmp/claude-implement-AbC123')" '<TMPDIR>' "/tmp session path redacted"
assert_eq "$(run_redactor '/private/tmp/larch-review-xyz_789')" '<TMPDIR>' "/private/tmp session path redacted"
assert_eq "$(run_redactor '/tmp/claude-implement-larch1-G2GITf')" '<TMPDIR>' "clone-tagged session path redacted"
assert_eq "$(run_redactor '/Users/example/.cache/larch/sessions/claude-design-cache123')" '<TMPDIR>' "cache session path redacted"
assert_eq "$(run_redactor 'see /tmp/claude-research-a_b-C/log.txt now')" 'see <TMPDIR>/log.txt now' "embedded path redacted in prose"
assert_eq "$(run_redactor '/tmp/not-larch-session and /var/tmp/claude-implement-abc')" '/tmp/not-larch-session and /var/tmp/claude-implement-abc' "non-matching paths preserved"

once=$(run_redactor 'see /private/tmp/larch-issue-idempotent')
twice=$(run_redactor "$once")
assert_eq "$twice" "$once" "redaction is idempotent"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
