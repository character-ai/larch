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
assert_eq "$(run_redactor '/var/folders/kf/abc123/T/claude-implement-larch5-XyZ')" '<TMPDIR>' "/var/folders macOS session path redacted"
assert_eq "$(run_redactor '/private/var/folders/kf/abc123/T/larch-fix-issue-XyZ')" '<TMPDIR>' "/private/var/folders canonical macOS session path redacted"

once=$(run_redactor 'see /private/tmp/larch-issue-idempotent')
twice=$(run_redactor "$once")
assert_eq "$twice" "$once" "redaction is idempotent"

# E1: numeric exit code must not be consumed by larch/sessions match
# \n here is two literal chars (backslash + n), as in JSONL-encoded content
assert_eq \
    "$(run_redactor 'Error: Exit code 1\nFoo /Users/example/.cache/larch/sessions/claude-implement-XYZ/step3.log')" \
    'Error: Exit code 1\nFoo <TMPDIR>/step3.log' \
    "E1: exit code number not consumed by larch/sessions match"

# E2: variable-assignment prefix must be preserved
assert_eq \
    "$(run_redactor 'export IMPLEMENT_TMPDIR=/Users/example/.cache/larch/sessions/claude-implement-XYZ/foo')" \
    'export IMPLEMENT_TMPDIR=<TMPDIR>/foo' \
    "E2: variable-assignment prefix preserved by boundary anchor"

# Happy path: space-delimited path is redacted normally
assert_eq \
    "$(run_redactor 'Some text /Users/example/.cache/larch/sessions/claude-implement-XYZ/foo')" \
    'Some text <TMPDIR>/foo' \
    "larch/sessions path with space boundary redacted"

# No-match: input without /larch/sessions/ passes through unchanged
assert_eq \
    "$(run_redactor 'plain text no larch path here')" \
    'plain text no larch path here' \
    "non-larch/sessions input passes through unchanged"

# Expression 4: \n (two chars: backslash + n) immediately before larch/sessions path
assert_eq \
    "$(run_redactor 'foo\n/Users/example/.cache/larch/sessions/claude-implement-XYZ')" \
    'foo\n<TMPDIR>' \
    "E4: \\n immediately before larch/sessions path redacted, \\n preserved"

assert_eq \
    "$(run_redactor '\n/Users/example/.cache/larch/sessions/larch-design-ABC123/bar.log')" \
    '\n<TMPDIR>/bar.log' \
    "E4: \\n-prefixed larch/sessions path with suffix redacted, \\n preserved"

# Expressions 5-6: \n immediately before /tmp and /var/folders paths
assert_eq \
    "$(run_redactor '\n/tmp/claude-implement-XYZ123')" \
    '\n<TMPDIR>' \
    "E5: \\n immediately before /tmp session path redacted, \\n preserved"

assert_eq \
    "$(run_redactor '\n/private/var/folders/kf/abc/T/larch-fix-issue-XyZ')" \
    '\n<TMPDIR>' \
    "E6: \\n immediately before /var/folders session path redacted, \\n preserved"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
