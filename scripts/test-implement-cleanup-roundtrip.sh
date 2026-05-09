#!/usr/bin/env bash
# test-implement-cleanup-roundtrip.sh — round-trip integration test for the
# EXPECTED_TMPDIR_BASENAME_PREFIX state-file convention.
#
# Verifies that read_state (awk extraction) + verify_cleanup_target (case-glob)
# work end-to-end when the state file uses the unquoted prefix form.
# Also confirms that the quoted form (the bug fixed by #1572) would fail.
#
# Wired into: make test-implement-cleanup-roundtrip
# Sibling contract: scripts/test-implement-cleanup-roundtrip.md

set -euo pipefail

PASS=0
FAIL=0

fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }
pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }

# Replicate read_state's awk extraction (same logic as implement-finalize.sh::read_state)
read_state_prefix() {
    local state_file=$1
    awk -F= -v k="EXPECTED_TMPDIR_BASENAME_PREFIX" '
        $1 == k {
            print substr($0, index($0, "=") + 1)
            found = 1
            exit
        }
        END { if (!found) print "" }
    ' "$state_file"
}

# Replicate verify_cleanup_target's case-glob (same logic as implement-finalize.sh::verify_cleanup_target)
prefix_matches_basename() {
    local prefix=$1 basename=$2
    case "$basename" in
        "$prefix"*) return 0 ;;
        *) return 1 ;;
    esac
}

SANDBOX=$(mktemp -d /tmp/larch-cleanup-roundtrip.XXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT

# ---------------------------------------------------------------------------
# Test 1: unquoted form — read_state must return value without leading quote
# ---------------------------------------------------------------------------
UNQUOTED_STATE="$SANDBOX/state-unquoted.sh"
printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-larch3-\n' > "$UNQUOTED_STATE"

extracted=$(read_state_prefix "$UNQUOTED_STATE")
if [[ "$extracted" == '"'* ]]; then
    fail "T1: unquoted state-file: read_state returned value with leading quote: '$extracted'"
else
    pass "T1: unquoted state-file: read_state returned '$extracted' (no leading quote)"
fi

# ---------------------------------------------------------------------------
# Test 2: unquoted form — prefix_matches_basename must succeed
# ---------------------------------------------------------------------------
if prefix_matches_basename "$extracted" "claude-implement-larch3-OwWaoN"; then
    pass "T2: unquoted prefix '$extracted' matches basename 'claude-implement-larch3-OwWaoN'"
else
    fail "T2: unquoted prefix '$extracted' did NOT match basename 'claude-implement-larch3-OwWaoN' (verify_cleanup_target would refuse rm-rf)"
fi

# ---------------------------------------------------------------------------
# Test 3: unquoted form — must NOT match a different project's basename
# ---------------------------------------------------------------------------
if prefix_matches_basename "$extracted" "claude-implement-other-AbCdEf"; then
    fail "T3: unquoted prefix '$extracted' wrongly matched 'claude-implement-other-AbCdEf'"
else
    pass "T3: unquoted prefix '$extracted' correctly does not match 'claude-implement-other-AbCdEf'"
fi

# ---------------------------------------------------------------------------
# Test 4 (regression): quoted form — read_state returns value WITH literal quotes
# This confirms the bug that #1572 fixed; the quoted form must NOT be used in SKILL.md.
# ---------------------------------------------------------------------------
QUOTED_STATE="$SANDBOX/state-quoted.sh"
printf 'EXPECTED_TMPDIR_BASENAME_PREFIX="claude-implement-larch3-"\n' > "$QUOTED_STATE"

extracted_quoted=$(read_state_prefix "$QUOTED_STATE")
if [[ "$extracted_quoted" == '"'* ]]; then
    pass "T4 (regression): quoted state-file: read_state returns value with leading quote '$extracted_quoted' — confirms bug"
else
    fail "T4 (regression): quoted state-file: read_state returned '$extracted_quoted' without leading quote (unexpected)"
fi

# ---------------------------------------------------------------------------
# Test 5 (regression): quoted form — prefix_matches_basename must FAIL
# (demonstrates the bug: verify_cleanup_target refuses rm-rf with quoted prefix)
# ---------------------------------------------------------------------------
if prefix_matches_basename "$extracted_quoted" "claude-implement-larch3-OwWaoN"; then
    fail "T5 (regression): quoted prefix '$extracted_quoted' matched 'claude-implement-larch3-OwWaoN' (bug regression)"
else
    pass "T5 (regression): quoted prefix '$extracted_quoted' correctly does NOT match 'claude-implement-larch3-OwWaoN' — confirms the bug behavior"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "Results: $PASS passed, $FAIL failed"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
echo "PASS: test-implement-cleanup-roundtrip.sh — all assertions hold"
