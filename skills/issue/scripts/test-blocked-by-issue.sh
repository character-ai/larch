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
        echo "  FAIL: $label — expected '$needle' in SKILL.md" >&2
    fi
}

echo "=== test-blocked-by-issue ==="

assert_present "argument-hint" \
    "argument-hint: \"[--input-file FILE] [--intra-batch-deps-file FILE] [--blocked-by-issue N]"

assert_present "validation-no-dedup-mutual-exclusion" \
    "--no-dedup and --blocked-by-issue are mutually exclusive"

assert_present "validation-batch-mode-only" \
    "--blocked-by-issue requires --input-file (batch mode)"

assert_present "validation-positive-integer" \
    "--blocked-by-issue must be a positive integer"

assert_present "step4-probe-gh-api" \
    'gh api "/repos/$REPO/issues/$BLOCKED_BY_ISSUE"'

assert_present "step4-probe-pr-check" \
    "pull_request != null"

assert_present "step4-probe-state-check" \
    '[[ "$BLOCKED_BY_ISSUE_STATE" != "open" ]]'

assert_present "step4-probe-title-sanitize" \
    "tr -d '\\t\\n'"

assert_present "step4-probe-dry-run" \
    "This probe also runs in \`--dry-run\`"

assert_present "step4-snapshot-augmentation" \
    "inject a synthetic open-state row"

assert_present "step5-blocked-by-merge" \
    "Caller-supplied --blocked-by-issue merge"

assert_present "step5-no-external-refs-carve-out" \
    "Carve-out for --blocked-by-issue"

assert_present "step6-skip-path-augmentation" \
    "Step-5-skip-path policy-edge augmentation"

assert_present "step6-cached-blocker-id" \
    '--blocker-id $BLOCKED_BY_ISSUE_ID'

echo "---"
echo "Results: $PASS_COUNT passed, $FAIL_COUNT failed"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    echo "FAILED: test-blocked-by-issue" >&2
    exit 1
fi
echo "PASSED: test-blocked-by-issue"
