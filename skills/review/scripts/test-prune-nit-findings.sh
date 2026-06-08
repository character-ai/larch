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

make_findings() {
    local path="$1"
    cat > "$path" <<'EOF'
### FINDING_1: Important finding about security
- **Reviewer**: claude
- **Concern**: Real security issue.
- **Suggested revision**: Fix it.
- **Severity**: important

### FINDING_2: Nit finding about style
- **Reviewer**: claude
- **Concern**: Trailing whitespace.
- **Suggested revision**: Remove it.
- **Severity**: nit

### FINDING_3: Latent finding about edge case
- **Reviewer**: codex
- **Concern**: Potential null deref.
- **Suggested revision**: Add nil check.
- **Severity**: latent

### FINDING_4: Another nit
- **Reviewer**: claude
- **Concern**: Rename variable.
- **Suggested revision**: Use clearer name.
- **Severity**: NIT
EOF
}

# --- Test 1: nit blocks moved to OOS, important/latent untouched ---
(
    FINDINGS="$TMP/t1-findings.md"
    OOS="$TMP/t1-oos.md"
    : > "$OOS"
    make_findings "$FINDINGS"

    "$PRUNE" --findings-file "$FINDINGS" --oos-file "$OOS" --input-mode code > "$TMP/t1-out.env"

    STATUS=$(kv_get "$TMP/t1-out.env" STATUS)
    PRUNED=$(kv_get "$TMP/t1-out.env" PRUNED_COUNT)
    INSCOPE=$(kv_get "$TMP/t1-out.env" INSCOPE_REMAINING)

    [[ "$STATUS" == "ok" ]] || fail "T1: expected STATUS=ok, got '$STATUS'"
    [[ "$PRUNED" == "2" ]] || fail "T1: expected PRUNED_COUNT=2, got '$PRUNED'"
    [[ "$INSCOPE" == "2" ]] || fail "T1: expected INSCOPE_REMAINING=2, got '$INSCOPE'"

    # findings.md must NOT contain nit blocks
    ! grep -Fq "Trailing whitespace" "$FINDINGS" 2>/dev/null || fail "T1: nit block still in findings.md"
    ! grep -Fq "Rename variable" "$FINDINGS" 2>/dev/null || fail "T1: nit block still in findings.md"

    # findings.md must contain important and latent
    grep -Fq "Real security issue" "$FINDINGS" 2>/dev/null || fail "T1: important block missing from findings.md"
    grep -Fq "Potential null deref" "$FINDINGS" 2>/dev/null || fail "T1: latent block missing from findings.md"

    # oos.md must contain both nit blocks with [OUT_OF_SCOPE] prefix
    grep -Fq "[OUT_OF_SCOPE]" "$OOS" 2>/dev/null || fail "T1: oos.md missing [OUT_OF_SCOPE] prefix"
    grep -Fq "Trailing whitespace" "$OOS" 2>/dev/null || fail "T1: nit block missing from oos.md"
    grep -Fq "Rename variable" "$OOS" 2>/dev/null || fail "T1: nit block missing from oos.md"

    # oos.md must NOT contain important or latent blocks
    ! grep -Fq "Real security issue" "$OOS" 2>/dev/null || fail "T1: important block leaked into oos.md"
    ! grep -Fq "Potential null deref" "$OOS" 2>/dev/null || fail "T1: latent block leaked into oos.md"

    pass "T1: nit blocks moved, important/latent untouched (code mode)"
)

# --- Test 2: renumbering is stable ---
(
    FINDINGS="$TMP/t2-findings.md"
    OOS="$TMP/t2-oos.md"
    : > "$OOS"
    make_findings "$FINDINGS"

    "$PRUNE" --findings-file "$FINDINGS" --oos-file "$OOS" --input-mode code > /dev/null

    # Two in-scope blocks remain; must be FINDING_1 and FINDING_2 after renumber
    grep -Fq "### FINDING_1:" "$FINDINGS" 2>/dev/null || fail "T2: FINDING_1 missing after renumber"
    grep -Fq "### FINDING_2:" "$FINDINGS" 2>/dev/null || fail "T2: FINDING_2 missing after renumber"
    ! grep -Fq "### FINDING_3:" "$FINDINGS" 2>/dev/null || fail "T2: FINDING_3 still present (not renumbered)"
    ! grep -Fq "### FINDING_4:" "$FINDINGS" 2>/dev/null || fail "T2: FINDING_4 still present (not renumbered)"

    pass "T2: renumbering is stable"
)

# --- Test 3: LARCH_PRUNE_NITS_DISABLED=1 is a no-op ---
(
    FINDINGS="$TMP/t3-findings.md"
    OOS="$TMP/t3-oos.md"
    : > "$OOS"
    make_findings "$FINDINGS"
    orig_findings=$(cat "$FINDINGS")
    orig_oos=$(cat "$OOS")

    LARCH_PRUNE_NITS_DISABLED=1 "$PRUNE" --findings-file "$FINDINGS" --oos-file "$OOS" --input-mode code > "$TMP/t3-out.env"

    STATUS=$(kv_get "$TMP/t3-out.env" STATUS)
    [[ "$STATUS" == "disabled" ]] || fail "T3: expected STATUS=disabled, got '$STATUS'"

    [[ "$(cat "$FINDINGS")" == "$orig_findings" ]] || fail "T3: findings.md was modified (should be no-op)"
    [[ "$(cat "$OOS")" == "$orig_oos" ]] || fail "T3: oos.md was modified (should be no-op)"

    pass "T3: LARCH_PRUNE_NITS_DISABLED=1 is a no-op"
)

# --- Test 4: input with no FINDING_N blocks is handled gracefully ---
(
    FINDINGS="$TMP/t4-findings.md"
    OOS="$TMP/t4-oos.md"
    printf 'some random text\nnot a finding block\n' > "$FINDINGS"
    : > "$OOS"

    "$PRUNE" --findings-file "$FINDINGS" --oos-file "$OOS" --input-mode code > "$TMP/t4-out.env"

    STATUS=$(kv_get "$TMP/t4-out.env" STATUS)
    [[ "$STATUS" == "ok" ]] || fail "T4: expected STATUS=ok for no-finding-block input, got '$STATUS'"
    PRUNED=$(kv_get "$TMP/t4-out.env" PRUNED_COUNT)
    [[ "$PRUNED" == "0" ]] || fail "T4: expected PRUNED_COUNT=0, got '$PRUNED'"

    pass "T4: no-finding-block input is handled gracefully"
)

# --- Test 5: important and latent are demonstrably untouched (explicit negative) ---
(
    FINDINGS="$TMP/t5-findings.md"
    OOS="$TMP/t5-oos.md"
    : > "$OOS"
    cat > "$FINDINGS" <<'EOF'
### FINDING_1: Should stay in-scope
- **Reviewer**: claude
- **Concern**: Important bug.
- **Suggested revision**: Fix.
- **Severity**: important

### FINDING_2: Also stays in-scope
- **Reviewer**: codex
- **Concern**: Latent risk.
- **Suggested revision**: Handle.
- **Severity**: latent
EOF

    "$PRUNE" --findings-file "$FINDINGS" --oos-file "$OOS" --input-mode code > "$TMP/t5-out.env"

    STATUS=$(kv_get "$TMP/t5-out.env" STATUS)
    PRUNED=$(kv_get "$TMP/t5-out.env" PRUNED_COUNT)

    [[ "$STATUS" == "ok" ]] || fail "T5: expected STATUS=ok, got '$STATUS'"
    [[ "$PRUNED" == "0" ]] || fail "T5: expected PRUNED_COUNT=0 (no nits), got '$PRUNED'"

    _oos_size=$(wc -c < "$OOS" | tr -d '[:space:]')
    [[ "$_oos_size" == "0" ]] || fail "T5: oos.md should be empty when no nits present (size=$_oos_size)"

    pass "T5: important and latent findings untouched"
)

# --- Test 6: plan mode converts FINDING_N to OOS_N in findings-oos.md ---
(
    FINDINGS="$TMP/t6-findings-in-scope.md"
    OOS="$TMP/t6-findings-oos.md"
    cat > "$FINDINGS" <<'EOF'
### FINDING_1: Real plan issue
- **Reviewer**: claude
- **Concern**: Missing step.
- **Suggested revision**: Add step.
- **Severity**: important

### FINDING_2: Nit plan finding
- **Reviewer**: codex
- **Concern**: Typo in plan.
- **Suggested revision**: Fix typo.
- **Severity**: nit
EOF
    cat > "$OOS" <<'EOF'
### OOS_1: Pre-existing OOS
- **Reviewer**: claude
- **Concern**: Out of scope concern.
- **Suggested revision**: N/A.
- **Severity**: important
EOF

    "$PRUNE" --findings-file "$FINDINGS" --oos-file "$OOS" --input-mode plan > "$TMP/t6-out.env"

    STATUS=$(kv_get "$TMP/t6-out.env" STATUS)
    PRUNED=$(kv_get "$TMP/t6-out.env" PRUNED_COUNT)

    [[ "$STATUS" == "ok" ]] || fail "T6: expected STATUS=ok, got '$STATUS'"
    [[ "$PRUNED" == "1" ]] || fail "T6: expected PRUNED_COUNT=1, got '$PRUNED'"

    # findings-in-scope.md must not contain nit block
    ! grep -Fq "Typo in plan" "$FINDINGS" 2>/dev/null || fail "T6: nit block still in findings-in-scope.md"

    # findings-oos.md must have OOS_N format for the moved block (not FINDING_N heading for moved block)
    grep -q "^### OOS_" "$OOS" 2>/dev/null || fail "T6: OOS_N block missing from findings-oos.md"
    grep -Fq "Typo in plan" "$OOS" 2>/dev/null || fail "T6: nit content missing from findings-oos.md"
    grep -Fq "Pre-existing OOS" "$OOS" 2>/dev/null || fail "T6: pre-existing OOS block lost"

    # The moved block must use OOS_N heading, not FINDING_N for moved content
    ! grep -qE "^### FINDING_[0-9]+:.*Typo" "$OOS" 2>/dev/null || fail "T6: FINDING_N heading leaked into findings-oos.md for moved block"

    pass "T6: plan mode converts nit FINDING_N to OOS_N in findings-oos.md"
)

printf '\nAll prune-nit-findings tests passed.\n'
