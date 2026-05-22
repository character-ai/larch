#!/usr/bin/env bash
# test-fix-issue-step-order.sh — Regression harness pinning the
# /fix-issue setup → read → triage → classify → find-lock ordering
# (setup and classify before lock; PR plan probe inside find-lock-issue.sh).
#
# Asserts that skills/fix-issue/SKILL.md and the companion
# skills/fix-issue/scripts/step-name-registry.tsv carry the load-bearing
# literals the step ordering depends on. The skill is prose;
# this harness is a CI guard against accidental reversion of the
# ordering or stale renumbering.
#
# Assertions (1), (2), (7), and (8) target the TSV; the rest target SKILL.md
# or find-lock-issue.sh:
#   (1) step-name-registry.tsv has step=0, name="setup".
#   (2) step-name-registry.tsv has step=4, name="find & lock".
#   (3) Section anchor "<!-- step:0 — Setup -->" present in SKILL.md.
#   (4) Section anchor "<!-- step:4 — Find and Lock -->" present in SKILL.md.
#   (5) Anti-pattern #1 contains "Step 4 — find & lock".
#   (6) Find & lock failure breadcrumb literal "⚠ 4: find & lock" present.
#   (7) No stale step=1, name="lock" row in step-name-registry.tsv.
#   (8) No stale step=2, name="lock" row in step-name-registry.tsv.
#   (9) Step 0 (Setup) block contains session-setup.sh.
#  (10) Step 0 block does NOT contain find-lock-issue.sh.
#  (11) Step 4 (Find and Lock) block contains find-lock-issue.sh.
#  (12) Step 4 block does NOT contain session-setup.sh.
#  (13) File-preamble Anti-halt rule covers Bash tool calls (#530).
#  (14) Step 5 execute block does NOT contain plan-block-read.sh.
#  (15) find-lock-issue.sh runs plan probe before comment --lock.
#
# Wired into `make lint` via the `test-fix-issue-step-order` target.
#
# Run manually:
#   bash skills/fix-issue/scripts/test-fix-issue-step-order.sh

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SKILL_MD="$REPO_ROOT/skills/fix-issue/SKILL.md"
REGISTRY_TSV="$REPO_ROOT/skills/fix-issue/scripts/step-name-registry.tsv"
FIND_LOCK_SH="$REPO_ROOT/skills/fix-issue/scripts/find-lock-issue.sh"

if [[ ! -f "$SKILL_MD" ]]; then
    echo "FAIL: SKILL.md not found at $SKILL_MD" >&2
    exit 1
fi

if [[ ! -f "$REGISTRY_TSV" ]]; then
    echo "FAIL: step-name-registry.tsv not found at $REGISTRY_TSV" >&2
    exit 1
fi

if [[ ! -f "$FIND_LOCK_SH" ]]; then
    echo "FAIL: find-lock-issue.sh not found at $FIND_LOCK_SH" >&2
    exit 1
fi

fail=0

assert_contains() {
    local pattern="$1"
    local description="$2"
    if ! grep -qF -- "$pattern" "$SKILL_MD"; then
        echo "FAIL: $description (pattern not found: $pattern)" >&2
        fail=1
    fi
}

assert_not_contains() {
    local pattern="$1"
    local description="$2"
    if grep -qF -- "$pattern" "$SKILL_MD"; then
        echo "FAIL: $description (pattern unexpectedly found: $pattern)" >&2
        fail=1
    fi
}

assert_tsv_row() {
    local step="$1"
    local name="$2"
    local description="$3"
    if ! awk -F'\t' -v s="$step" -v n="$name" 'NR>1 && $1==s && $2==n {found=1} END {exit !found}' "$REGISTRY_TSV"; then
        echo "FAIL: $description (TSV row step=$step name=$name not found)" >&2
        fail=1
    fi
}

assert_tsv_no_row() {
    local step="$1"
    local name="$2"
    local description="$3"
    if awk -F'\t' -v s="$step" -v n="$name" 'NR>1 && $1==s && $2==n {found=1} END {exit !found}' "$REGISTRY_TSV"; then
        echo "FAIL: $description (TSV row step=$step name=$name unexpectedly found)" >&2
        fail=1
    fi
}

assert_tsv_row '0' 'setup' '(1) step-name-registry.tsv has "0 -> setup"'
assert_tsv_row '4' 'find & lock' '(2) step-name-registry.tsv has "4 -> find & lock"'

assert_contains '<!-- step:0 — Setup -->' '(3) section anchor "step:0 — Setup" present'
assert_contains '<!-- step:4 — Find and Lock -->' '(4) section anchor "step:4 — Find and Lock" present'

assert_contains 'Step 4 — find & lock' '(5) anti-pattern #1 references Step 4 find & lock'

assert_contains '⚠ 4: find & lock' '(6) find & lock warning breadcrumb uses "4: find & lock"'

assert_tsv_no_row '1' 'lock' '(7) no stale "1 -> lock" registry row in TSV'
assert_tsv_no_row '2' 'lock' '(8) no stale "2 -> lock" registry row in TSV'

STEP0_BLOCK=$(awk '
    /^<!-- step:0 — Setup -->/ { in_block=1; next }
    /^<!-- step:1/            { in_block=0 }
    in_block { print }
' "$SKILL_MD")

STEP4_BLOCK=$(awk '
    /^<!-- step:4 — Find and Lock -->/ { in_block=1; next }
    /^<!-- step:5/            { in_block=0 }
    in_block { print }
' "$SKILL_MD")

if [[ -z "$STEP0_BLOCK" ]]; then
    echo "FAIL: Step 0 block extraction produced empty output (heading boundary missing?)" >&2
    fail=1
fi
if [[ -z "$STEP4_BLOCK" ]]; then
    echo "FAIL: Step 4 block extraction produced empty output (heading boundary missing?)" >&2
    fail=1
fi

if ! grep -qF -- 'session-setup.sh --prefix claude-fix-issue --skip-branch-check' <<<"$STEP0_BLOCK"; then
    echo 'FAIL: (9) Step 0 block does not contain `session-setup.sh --prefix claude-fix-issue --skip-branch-check`' >&2
    fail=1
fi

if grep -qF -- 'find-lock-issue.sh' <<<"$STEP0_BLOCK"; then
    echo 'FAIL: (10) Step 0 block unexpectedly contains `find-lock-issue.sh`' >&2
    fail=1
fi

if ! grep -qF -- 'find-lock-issue.sh' <<<"$STEP4_BLOCK"; then
    echo 'FAIL: (11) Step 4 block does not contain `find-lock-issue.sh`' >&2
    fail=1
fi

if grep -qF -- 'session-setup.sh' <<<"$STEP4_BLOCK"; then
    echo 'FAIL: (12) Step 4 block unexpectedly contains `session-setup.sh`' >&2
    fail=1
fi

if ! grep -qF '<!-- step:' "$SKILL_MD"; then
    echo 'FAIL: (13) no `<!-- step:` anchor found anywhere in SKILL.md' >&2
    fail=1
else
    PREAMBLE_BLOCK=$(awk '
        /^<!-- step:/ { exit }
        { print }
    ' "$SKILL_MD")
    if [[ -z "$PREAMBLE_BLOCK" ]]; then
        echo 'FAIL: (13) preamble is empty' >&2
        fail=1
    elif ! grep -qF -- 'child Bash tool calls into the canonical' <<<"$PREAMBLE_BLOCK"; then
        echo 'FAIL: (13) anti-halt preamble missing Bash broadening token' >&2
        fail=1
    fi
fi

STEP5_BLOCK=$(awk '
    /^<!-- step:5 / { in_block=1; next }
    /^<!-- step:6 / { in_block=0 }
    in_block { print }
' "$SKILL_MD")

if [[ -n "$STEP5_BLOCK" ]] && grep -qF -- 'plan-block-read.sh' <<<"$STEP5_BLOCK"; then
    echo 'FAIL: (14) Step 5 block unexpectedly contains `plan-block-read.sh`' >&2
    fail=1
fi

probe_line=$(grep -nF 'plan_read="${SCRIPT_DIR}/../../../scripts/plan-block-read.sh"' "$FIND_LOCK_SH" | head -1 | cut -d: -f1 || true)
lock_line=$(grep -nF 'lock_out=$("$lock_script" comment' "$FIND_LOCK_SH" | head -1 | cut -d: -f1 || true)
if [[ -z "$probe_line" || -z "$lock_line" ]]; then
    echo "FAIL: (15) could not locate plan-block-read.sh or comment --lock in find-lock-issue.sh" >&2
    fail=1
elif ! [[ "$probe_line" -lt "$lock_line" ]]; then
    echo "FAIL: (15) plan-block-read.sh reference must appear before first comment --lock (probe_line=$probe_line lock_line=$lock_line)" >&2
    fail=1
fi

if [[ $fail -ne 0 ]]; then
    echo "test-fix-issue-step-order: FAILED" >&2
    exit 1
fi

echo "test-fix-issue-step-order: 15 assertions passed."
