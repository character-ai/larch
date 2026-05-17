#!/usr/bin/env bash
# test-implement-anti-polling-rule.sh — Regression harness for issue #1011.
#
# Pins the anti-polling-loop literals in two files:
#   (1) AGENTS.md: the Monitor / Bash-polling-loop bullet must mention BOTH
#       Monitor and Bash run_in_background polling loops.
#   (2) skills/implement/SKILL.md: Step 5 uses one foreground
#       review-and-fix.sh call per round. Contributors must not reintroduce
#       background reviewer launch + polling prose in the orchestrator prompt.
#
# Wired into `make lint` via the `test-implement-anti-polling-rule` target.
# Runtime enforcement is the model-level reading of the prose; this harness
# is a CI guard against accidental literal removal.

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
AGENTS_MD="$REPO_ROOT/AGENTS.md"
IMPL_MD="$REPO_ROOT/skills/implement/SKILL.md"

PASS=0
fail() { echo "  FAIL: $1" >&2; echo "    missing literal: $2" >&2; exit 1; }
check() {
    local file="$1" label="$2" literal="$3"
    if grep -qF -- "$literal" "$file"; then
        PASS=$((PASS + 1))
        echo "  PASS: $label"
    else
        fail "$label" "$literal"
    fi
}

[[ -f "$AGENTS_MD" ]] || { echo "ERROR: AGENTS.md not found: $AGENTS_MD" >&2; exit 1; }
[[ -f "$IMPL_MD"   ]] || { echo "ERROR: SKILL.md not found: $IMPL_MD" >&2; exit 1; }

echo "Asserting anti-polling-rule literals (issue #1011)..."

# (1) AGENTS.md: extended bullet covers both forms.
check "$AGENTS_MD" \
    "AGENTS.md mentions Monitor in the rule" \
    "Don't spawn a Monitor or a Bash"
check "$AGENTS_MD" \
    "AGENTS.md cites Bash run_in_background polling loop" \
    'Bash `run_in_background` polling loop'
check "$AGENTS_MD" \
    "AGENTS.md cites the for/while/until + sleep pattern" \
    '`for`/`while`/`until` + `sleep`'

check "$IMPL_MD" \
    "SKILL.md Step 5 uses foreground review-and-fix call" \
    'For each round, run one foreground Bash call'
check "$IMPL_MD" \
    "SKILL.md Step 5 delegates reviewer waiting to scripts" \
    'Step 5 invokes `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh`'

STEP5_BLOCK=$(awk '
    /^<!-- step:5 / { in_block=1 }
    /^<!-- step:6 / { in_block=0 }
    in_block { print }
' "$IMPL_MD")
if grep -Fq 'run_in_background: true' <<<"$STEP5_BLOCK"; then
    fail "SKILL.md must not reintroduce background Step 5 reviewer launches" 'run_in_background: true'
fi

echo ""
echo "All $PASS assertions passed."
