#!/usr/bin/env bash
# test-implement-anti-polling-rule.sh — Regression harness for issue #1011 /
# issue #2749 (FINDING_24 inversion).
#
# Pins the anti-polling-loop literals in two files:
#   (1) AGENTS.md: the Monitor / Bash-polling-loop bullet must mention BOTH
#       Monitor and Bash run_in_background polling loops.
#   (2) skills/implement/SKILL.md: Step 5 delegates reviewer waiting to
#       scripts/run-step5-review.sh (no ad-hoc polling loops).
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
check "$AGENTS_MD" \
    "AGENTS.md bans per-turn output-file polling while a run_in_background task runs" \
    'poll the task output file once per turn'

check "$IMPL_MD" \
    "SKILL.md Step 5 delegates reviewer waiting to scripts" \
    'Step 5 invokes `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh`'

echo ""
echo "All $PASS assertions passed."
