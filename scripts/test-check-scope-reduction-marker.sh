#!/usr/bin/env bash
# test-check-scope-reduction-marker.sh — harness for check-scope-reduction-marker.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
CHECK="$REPO_ROOT/scripts/check-scope-reduction-marker.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-check-scope-reduction-marker.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
FAIL=0

assert_rc() {
    local name="$1" want="$2" body="$3" got
    printf '%s\n' "$body" >"$TMP/block.md"
    if "$CHECK" --file "$TMP/block.md"; then got=0; else got=1; fi
    if [ "$got" = "$want" ]; then
        printf '  ok   %s\n' "$name"
    else
        printf '  FAIL %s — got %s want %s\n' "$name" "$got" "$want" >&2
        FAIL=1
    fi
}

assert_rc "leading Concern marker" 0 $'### FINDING_1:\n- **Concern**: [SCOPE-REDUCTION] remove extra work'
assert_rc "leading what marker" 0 $'what: [SCOPE-REDUCTION] reduce scope'
assert_rc "leading heading marker" 0 $'### FINDING_1: [SCOPE-REDUCTION] reduce scope\n- **Concern**: details'
assert_rc "severity-prefixed Concern marker" 0 $'### FINDING_1:\n- **Concern**: [important] [SCOPE-REDUCTION] remove extra work'
assert_rc "fenced false" 1 $'```\n- **Concern**: [SCOPE-REDUCTION] no\n```'
assert_rc "inline-code false" 1 $'### FINDING_1:\n- **Concern**: `[SCOPE-REDUCTION]` mentioned only as code'
assert_rc "non-leading false" 1 $'### FINDING_1:\n- **Concern**: remove scope [SCOPE-REDUCTION] later'
assert_rc "absent false" 1 $'### FINDING_1:\n- **Concern**: ordinary finding'

if [ "$FAIL" -ne 0 ]; then exit 1; fi
echo "PASS: test-check-scope-reduction-marker.sh"
