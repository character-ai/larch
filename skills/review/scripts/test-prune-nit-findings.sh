#!/usr/bin/env bash
# test-prune-nit-findings.sh — regression harness for prune-nit-findings.sh.

set -euo pipefail

unset LARCH_PRUNE_NITS_DISABLED || true
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PRUNE="$REPO_ROOT/skills/review/scripts/prune-nit-findings.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-prune-nit-findings.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

[[ -x "$PRUNE" ]] || fail "$PRUNE not executable"

kv_get() {
    local file="$1" key="$2"
    awk -F= -v k="$key" '$1==k{sub(/^[^=]*=/,"");print;exit}' "$file" 2>/dev/null || true
}

# Aggregated findings.md format (post-review aggregate-findings) includes Severity lines
make_aggregated_findings() {
    local path="$1"
    cat > "$path" <<'EOF'
### FINDING_1: Important finding about security
- **Reviewer(s)**: claude
- **Severity**: important
- **Concern**: Real security issue.
- **Suggested revision**: Fix it.

### FINDING_2: Nit finding about style
- **Reviewer(s)**: claude
- **Severity**: nit
- **Concern**: Trailing whitespace.
- **Suggested revision**: Remove it.

### FINDING_3: Latent finding about edge case
- **Reviewer(s)**: codex
- **Severity**: latent
- **Concern**: Potential null deref.
- **Suggested revision**: Add nil check.

### FINDING_4: Another nit
- **Reviewer(s)**: claude
- **Severity**: NIT
- **Concern**: Rename variable.
- **Suggested revision**: Use clearer name.
EOF
}

# --- Test 1: code mode — nit blocks get [OUT_OF_SCOPE] prefix added to title ---
(
    FINDINGS="$TMP/t1-findings.md"
    make_aggregated_findings "$FINDINGS"

    "$PRUNE" --findings-file "$FINDINGS" --input-mode code > "$TMP/t1-out.env"

    STATUS=$(kv_get "$TMP/t1-out.env" STATUS)
    PRUNED=$(kv_get "$TMP/t1-out.env" PRUNED_COUNT)
    INSCOPE=$(kv_get "$TMP/t1-out.env" INSCOPE_REMAINING)

    [[ "$STATUS" == "ok" ]] || fail "T1: expected STATUS=ok, got '$STATUS'"
    [[ "$PRUNED" == "2" ]] || fail "T1: expected PRUNED_COUNT=2, got '$PRUNED'"
    [[ "$INSCOPE" == "2" ]] || fail "T1: expected INSCOPE_REMAINING=2, got '$INSCOPE'"

    # Nit blocks must still be in findings.md (not removed) but with [OUT_OF_SCOPE] prefix
    grep -Fq "[OUT_OF_SCOPE]" "$FINDINGS" 2>/dev/null || fail "T1: [OUT_OF_SCOPE] prefix missing from findings.md"
    grep -Fq "Trailing whitespace" "$FINDINGS" 2>/dev/null || fail "T1: nit block content removed from findings.md (should stay)"
    grep -Fq "Rename variable" "$FINDINGS" 2>/dev/null || fail "T1: nit block content removed from findings.md (should stay)"

    # Important and latent must NOT have [OUT_OF_SCOPE] prefix
    ! grep -E "FINDING_1.*\[OUT_OF_SCOPE\]" "$FINDINGS" 2>/dev/null || fail "T1: important block got [OUT_OF_SCOPE] prefix"
    ! grep -E "FINDING_3.*\[OUT_OF_SCOPE\]" "$FINDINGS" 2>/dev/null || fail "T1: latent block got [OUT_OF_SCOPE] prefix"

    pass "T1: code mode — nit blocks marked [OUT_OF_SCOPE] in-place, important/latent untouched"
)

# --- Test 2: code mode — FINDING_N IDs are NOT renumbered (stable for voter reference) ---
(
    FINDINGS="$TMP/t2-findings.md"
    make_aggregated_findings "$FINDINGS"

    "$PRUNE" --findings-file "$FINDINGS" --input-mode code > /dev/null

    # All four FINDING_N headers still present with original IDs
    grep -Fq "### FINDING_1:" "$FINDINGS" 2>/dev/null || fail "T2: FINDING_1 heading missing (should stay, ids not renumbered)"
    grep -Fq "### FINDING_2:" "$FINDINGS" 2>/dev/null || fail "T2: FINDING_2 heading missing"
    grep -Fq "### FINDING_3:" "$FINDINGS" 2>/dev/null || fail "T2: FINDING_3 heading missing"
    grep -Fq "### FINDING_4:" "$FINDINGS" 2>/dev/null || fail "T2: FINDING_4 heading missing"

    pass "T2: code mode — FINDING_N IDs are not renumbered"
)

# --- Test 3: LARCH_PRUNE_NITS_DISABLED=1 is a no-op ---
(
    FINDINGS="$TMP/t3-findings.md"
    make_aggregated_findings "$FINDINGS"
    orig_findings=$(cat "$FINDINGS")

    LARCH_PRUNE_NITS_DISABLED=1 "$PRUNE" --findings-file "$FINDINGS" --input-mode code > "$TMP/t3-out.env"

    STATUS=$(kv_get "$TMP/t3-out.env" STATUS)
    [[ "$STATUS" == "disabled" ]] || fail "T3: expected STATUS=disabled, got '$STATUS'"
    [[ "$(cat "$FINDINGS")" == "$orig_findings" ]] || fail "T3: findings.md was modified (should be no-op)"

    pass "T3: LARCH_PRUNE_NITS_DISABLED=1 is a no-op"
)

# --- Test 4: input with no FINDING_N blocks is handled gracefully ---
(
    FINDINGS="$TMP/t4-findings.md"
    printf 'some random text\nnot a finding block\n' > "$FINDINGS"

    "$PRUNE" --findings-file "$FINDINGS" --input-mode code > "$TMP/t4-out.env"

    STATUS=$(kv_get "$TMP/t4-out.env" STATUS)
    [[ "$STATUS" == "ok" ]] || fail "T4: expected STATUS=ok for no-finding-block input, got '$STATUS'"
    PRUNED=$(kv_get "$TMP/t4-out.env" PRUNED_COUNT)
    [[ "$PRUNED" == "0" ]] || fail "T4: expected PRUNED_COUNT=0, got '$PRUNED'"

    pass "T4: no-finding-block input is handled gracefully"
)

# --- Test 5: important and latent are demonstrably untouched (explicit negative) ---
(
    FINDINGS="$TMP/t5-findings.md"
    cat > "$FINDINGS" <<'EOF'
### FINDING_1: Should stay in-scope
- **Reviewer(s)**: claude
- **Severity**: important
- **Concern**: Important bug.
- **Suggested revision**: Fix.

### FINDING_2: Also stays in-scope
- **Reviewer(s)**: codex
- **Severity**: latent
- **Concern**: Latent risk.
- **Suggested revision**: Handle.
EOF

    "$PRUNE" --findings-file "$FINDINGS" --input-mode code > "$TMP/t5-out.env"

    STATUS=$(kv_get "$TMP/t5-out.env" STATUS)
    PRUNED=$(kv_get "$TMP/t5-out.env" PRUNED_COUNT)

    [[ "$STATUS" == "ok" ]] || fail "T5: expected STATUS=ok, got '$STATUS'"
    [[ "$PRUNED" == "0" ]] || fail "T5: expected PRUNED_COUNT=0 (no nits), got '$PRUNED'"

    ! grep -Fq "[OUT_OF_SCOPE]" "$FINDINGS" 2>/dev/null || fail "T5: [OUT_OF_SCOPE] appeared in findings.md when no nits present"

    pass "T5: important and latent findings untouched"
)

# --- Test 6: plan mode — nit FINDING_N removed and added as OOS_N to findings-oos.md ---
(
    FINDINGS="$TMP/t6-findings-in-scope.md"
    OOS="$TMP/t6-findings-oos.md"
    cat > "$FINDINGS" <<'EOF'
### FINDING_1: Real plan issue
- **Reviewer(s)**: claude
- **Severity**: important
- **Concern**: Missing step.
- **Suggested revision**: Add step.

### FINDING_2: Nit plan finding
- **Reviewer(s)**: codex
- **Severity**: nit
- **Concern**: Typo in plan.
- **Suggested revision**: Fix typo.
EOF
    cat > "$OOS" <<'EOF'
### OOS_1: Pre-existing OOS
- **Reviewer(s)**: claude
- **Severity**: important
- **Concern**: Out of scope concern.
- **Suggested revision**: N/A.
EOF

    "$PRUNE" --findings-file "$FINDINGS" --oos-file "$OOS" --input-mode plan > "$TMP/t6-out.env"

    STATUS=$(kv_get "$TMP/t6-out.env" STATUS)
    PRUNED=$(kv_get "$TMP/t6-out.env" PRUNED_COUNT)

    [[ "$STATUS" == "ok" ]] || fail "T6: expected STATUS=ok, got '$STATUS'"
    [[ "$PRUNED" == "1" ]] || fail "T6: expected PRUNED_COUNT=1, got '$PRUNED'"

    # findings-in-scope.md must not contain nit block
    ! grep -Fq "Typo in plan" "$FINDINGS" 2>/dev/null || fail "T6: nit block still in findings-in-scope.md"

    # findings-oos.md must have OOS_N format for the moved block
    grep -q "^### OOS_" "$OOS" 2>/dev/null || fail "T6: OOS_N block missing from findings-oos.md"
    grep -Fq "Typo in plan" "$OOS" 2>/dev/null || fail "T6: nit content missing from findings-oos.md"
    grep -Fq "Pre-existing OOS" "$OOS" 2>/dev/null || fail "T6: pre-existing OOS block lost"

    # Moved block must use OOS_N heading, not FINDING_N
    ! grep -qE "^### FINDING_[0-9]+:.*Typo" "$OOS" 2>/dev/null || fail "T6: FINDING_N heading leaked into findings-oos.md for moved block"

    pass "T6: plan mode — nit FINDING_N removed and converted to OOS_N in findings-oos.md"
)

# --- Test 7: code mode — [OUT_OF_SCOPE] prefix appears in title after FINDING_N: ---
(
    FINDINGS="$TMP/t7-findings.md"
    cat > "$FINDINGS" <<'EOF'
### FINDING_1: Style nit
- **Reviewer(s)**: claude
- **Severity**: nit
- **Concern**: Minor style issue.
- **Suggested revision**: Fix.
EOF

    "$PRUNE" --findings-file "$FINDINGS" --input-mode code > "$TMP/t7-out.env"

    STATUS=$(kv_get "$TMP/t7-out.env" STATUS)
    [[ "$STATUS" == "ok" ]] || fail "T7: expected STATUS=ok, got '$STATUS'"

    # The heading must be ### FINDING_1: [OUT_OF_SCOPE] Style nit
    grep -q "^### FINDING_1: \[OUT_OF_SCOPE\]" "$FINDINGS" 2>/dev/null || fail "T7: [OUT_OF_SCOPE] not in correct heading position"

    pass "T7: code mode — [OUT_OF_SCOPE] prefix is at title position after FINDING_N:"
)

printf '\nAll prune-nit-findings tests passed.\n'
