#!/usr/bin/env bash
# test-implement-anti-polling-rule.sh — Regression harness for issue #1011.
#
# Pins the anti-polling-loop literals in two files:
#   (1) AGENTS.md: the Monitor / Bash-polling-loop bullet must mention BOTH
#       Monitor and Bash run_in_background polling loops.
#   (2) skills/implement/SKILL.md: Step 5 uses one foreground
#       review-and-fix.sh call per round. Contributors must not reintroduce
#       background reviewer launch + polling prose in the orchestrator prompt.
#       Canonical "Foreground required" banners (BASH_AUTHORING.md §4) quote
#       `run_in_background: true` as the forbidden literal — those lines are
#       excluded from the Step-5 substring scan.
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
    'Step 5 invokes **one** foreground'
check "$IMPL_MD" \
    "SKILL.md Step 5 delegates reviewer waiting to scripts" \
    'Step 5 invokes `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh`'

STEP5_BLOCK=$(awk '
    /^<!-- step:5 / { in_block=1 }
    /^<!-- step:6 / { in_block=0 }
    in_block { print }
' "$IMPL_MD")
# Flag `run_in_background: true` only outside canonical foreground banners
# (those lines intentionally contain the substring inside backticks).
BAD_STEP5_LINES=$(
    printf '%s\n' "$STEP5_BLOCK" |
        grep -F 'run_in_background: true' |
        grep -Fv 'Foreground required' || true
)
if [[ -n "$BAD_STEP5_LINES" ]]; then
    echo "  FAIL: SKILL.md must not reintroduce background Step 5 reviewer launches" >&2
    echo "    disallowed run_in_background: true outside Foreground-required banners:" >&2
    printf '%s\n' "$BAD_STEP5_LINES" | sed 's/^/      /' >&2
    exit 1
fi

echo ""
echo "All $PASS assertions passed."
