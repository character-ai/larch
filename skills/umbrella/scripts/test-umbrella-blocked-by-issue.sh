#!/usr/bin/env bash
# shellcheck disable=SC2016
# Single-quoted needles intentionally contain literal $VAR text — they are
# grep-fixed-string fingerprints of SKILL.md content, not shell expressions.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL="$SCRIPT_DIR/../SKILL.md"

if [[ ! -f "$SKILL" ]]; then
    echo "ERROR: SKILL.md not found: $SKILL" >&2
    exit 1
fi

PASS_COUNT=0
FAIL_COUNT=0

assert_present() {
    local label="$1" needle="$2"
    if grep -qF -- "$needle" "$SKILL"; then
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "  PASS: $label"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "  FAIL: $label — expected needle in SKILL.md" >&2
    fi
}

# extract_block prints the SKILL.md content between two markdown headings
# (inclusive of the start, exclusive of the next). Matches the awk pattern
# used by test-umbrella-emit-output-contract.sh.
extract_block() {
    local start_marker="$1" end_marker="$2"
    awk -v start="$start_marker" -v end="$end_marker" '
        $0 ~ start { in_block=1; next }
        $0 ~ end && in_block { exit }
        in_block { print }
    ' "$SKILL"
}

assert_in_block() {
    local label="$1" block_content="$2" needle="$3"
    if printf '%s\n' "$block_content" | grep -qF -- "$needle"; then
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "  PASS: $label"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "  FAIL: $label — expected needle in extracted block" >&2
    fi
}

assert_absent_in_block() {
    local label="$1" block_content="$2" needle="$3"
    if printf '%s\n' "$block_content" | grep -qF -- "$needle"; then
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "  FAIL: $label — needle unexpectedly present in extracted block" >&2
    else
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "  PASS: $label"
    fi
}

echo "=== test-umbrella-blocked-by-issue ==="

# 1. Frontmatter advertises the flag.
assert_present "argument-hint advertises --blocked-by-issue" \
    '[--blocked-by-issue N]'

# 2. Flags table row exists. Use a backtick-free fragment of the row.
assert_present "flag-table row" \
    'Caller-supplied policy blocker. `N` is a positive integer issue number.'

# 3. Step 3A block: must include --blocked-by-issue in args grammar AND
#    the diagnostic note about /issue rejection. Extract the Step 3A block
#    (from Step 3A anchor to Step 3B anchor).
STEP_3A_BLOCK=$(extract_block '^<!-- step:3A' '^<!-- step:3B')

assert_in_block "step-3A args grammar lists --blocked-by-issue" \
    "$STEP_3A_BLOCK" \
    '[--closed-window-days N] [--blocked-by-issue N]'

assert_in_block "step-3A note about /issue rejection" \
    "$STEP_3A_BLOCK" \
    'requires --input-file (batch mode); single-mode is not supported in this release.'

# 4. Step 3B.2 block: must include --blocked-by-issue in args grammar AND
#    the conditional-forward sentence.
STEP_3B2_BLOCK=$(extract_block '^### 3B\.2' '^### 3B\.3')

assert_in_block "step-3B.2 args grammar lists --blocked-by-issue" \
    "$STEP_3B2_BLOCK" \
    '[--closed-window-days N] [--blocked-by-issue N]'

assert_in_block "step-3B.2 conditional forward sentence" \
    "$STEP_3B2_BLOCK" \
    'include `--blocked-by-issue $BLOCKED_BY_ISSUE` in the `/issue` invocation'

# 5. Step 3B.3 block: must NOT include --blocked-by-issue in the args
#    grammar but MUST include the explicit non-forwarding sentence.
STEP_3B3_BLOCK=$(extract_block '^### 3B\.3' '^### 3B\.4')

assert_absent_in_block "step-3B.3 args grammar does NOT list --blocked-by-issue" \
    "$STEP_3B3_BLOCK" \
    '[--blocked-by-issue N]'

assert_in_block "step-3B.3 explicit non-forwarding sentence" \
    "$STEP_3B3_BLOCK" \
    'is **not** forwarded here'

echo "---"
echo "Results: $PASS_COUNT passed, $FAIL_COUNT failed"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    echo "FAILED: test-umbrella-blocked-by-issue" >&2
    exit 1
fi
echo "PASSED: test-umbrella-blocked-by-issue"
